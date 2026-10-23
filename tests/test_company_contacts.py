import httpx
import pytest

from harvey.collectors import company_contacts as C
from harvey.collectors.discover import Business, DiscoveryQuery, _upsert
from harvey.models import Company
from harvey.state import StateManager


def test_only_public_visible_addresses_are_extracted():
    html = '''<script>const x="fake@vendor.test";</script>
    <p>Info@practice.test</p><a href="mailto:team%2Bhelp@practice.test?subject=Test">Mail</a>
    <img src="logo@2x.png"><span>info@example.com</span>'''
    assert C.extract_public_emails(html) == ['info@practice.test', 'team+help@practice.test']
    assert C.relevant_company_emails(['info@practice.test', 'designer@agency.test'], 'practice.test') == ['info@practice.test']


@pytest.mark.asyncio
async def test_private_hosts_and_external_redirects_are_not_allowed(monkeypatch):
    monkeypatch.setattr(C.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('127.0.0.1', 0))])
    assert not await C._public_company_url('http://practice.test', 'practice.test')
    assert not await C._public_company_url('https://other.test/contact', 'practice.test')
    assert not await C._public_company_url('file:///etc/passwd', 'practice.test')


@pytest.mark.asyncio
async def test_bounded_website_lookup_keeps_source_and_creates_no_people(tmp_path, monkeypatch):
    state = StateManager(str(tmp_path / 'contacts.db'))
    await state.init_db()
    company = Company(name='Practice', domain='practice.test', website='https://practice.test')
    company.id = await state.add_company(company)
    async def allowed(*args):
        return True
    monkeypatch.setattr(C, '_public_company_url', allowed)
    requests = []
    def respond(request):
        requests.append(str(request.url))
        body = '<a href="/kontakt">Kontakt</a><a href="/impressum">Impressum</a><a href="/contact-other">Other</a>'
        if request.url.path == '/kontakt':
            body = '<a href="mailto:info@practice.test">Kontakt</a><p>designer@agency.test</p>'
        return httpx.Response(200, text=body, headers={'content-type': 'text/html'})
    original_client = httpx.AsyncClient
    monkeypatch.setattr(C.httpx, 'AsyncClient', lambda **kw: original_client(transport=httpx.MockTransport(respond), **kw))
    result = await C.lookup_company_emails(company, state)
    assert result['status']=='found' and result['found']==1
    assert result['diagnostics'][-1]['code']=='found'
    assert len(requests) == 2
    async with state._connect() as db:
        row = await (await db.execute('SELECT email, source_url FROM company_public_emails')).fetchone()
    assert tuple(row) == ('info@practice.test', 'https://practice.test/kontakt')
    assert await state.get_contacts_for_company(company.id) == []


@pytest.mark.asyncio
async def test_discovery_saves_public_mail_on_existing_company_without_marking_verified(tmp_path):
    state = StateManager(str(tmp_path / 'discovery.db'))
    await state.init_db()
    business = Business(name='Practice', domain='practice.test', public_email='info@practice.test',
                        provider='geoapify', source_url='https://practice.test/kontakt')
    first_id, created = await _upsert(state, business, DiscoveryQuery('Arztpraxis'))
    second_id, created_again = await _upsert(state, business, DiscoveryQuery('Arztpraxis'))
    assert first_id == second_id and created and not created_again
    async with state._connect() as db:
        assert (await (await db.execute('SELECT COUNT(*) FROM company_public_emails')).fetchone())[0] == 1
    assert await state.get_contacts_for_company(first_id) == []


def test_structured_emails_and_obfuscated_text_are_extracted_without_arbitrary_scripts():
    html = '''<script>var ignored = "fake@practice.test"</script>
    <script type="application/ld+json">{"@context":"https://schema.org","@graph":[
      {"@type":"Organization","email":"INFO@practice.test",
       "contactPoint":{"@type":"ContactPoint","email":"mailto:team%2Bhelp@practice.test"}}
    ]}</script>
    <div itemscope itemtype="https://schema.org/Organization">
      <meta itemprop="email" content="micro@practice.test"></div>
    <p>kontakt [at] practice [dot] test</p><p>office (at) practice (punkt) test</p>'''
    assert set(C.extract_public_emails(html, 'https://practice.test')) == {
        'info@practice.test', 'team+help@practice.test', 'micro@practice.test',
        'kontakt@practice.test', 'office@practice.test'}


def test_malformed_structured_data_does_not_discard_visible_email():
    assert C.extract_public_emails('<script type="application/ld+json">{broken</script>'
                                   '<p>info@practice.test</p>') == ['info@practice.test']


def test_normalization_and_invalid_email_filter():
    assert C.normalize_email('INFO@BÜCHER.DE') == 'info@bücher.de'
    assert C.extract_public_emails('<p>müller@bücher.de</p>') == ['müller@bücher.de']
    for value in ['a..b@practice.test', 'invalid', 'info@example.com', 'logo@2x.png']:
        assert not C.valid_email(value)


def test_contact_link_ranking_text_and_internal_fallbacks():
    html = '''<a href="https://agency.test/kontakt">Kontakt</a>
    <a href="/legal#imprint">Impressum</a><a href="/page?id=4">Kontakt</a>'''
    assert C.contact_page_links(html, 'https://practice.test', 'practice.test') == [
        'https://practice.test/page?id=4', 'https://practice.test/legal']
    assert C.contact_page_links('<a href="/contact">Contact</a>', 'https://practice.test',
                                'practice.test') == ['https://practice.test/contact',
                                                     'https://practice.test/kontakt']


@pytest.mark.asyncio
async def test_dns_evidence_is_not_mailbox_verification(monkeypatch):
    from types import SimpleNamespace
    from email_validator import EmailUndeliverableError
    calls = []
    def valid(value, **kw):
        calls.append(kw)
        return SimpleNamespace(mx=[(10, "mx.practice.test")])
    monkeypatch.setattr(C, 'validate_email', valid)
    assert await C.check_email_domain('info@practice.test') == 'mail_domain_present'
    assert calls == [{'check_deliverability': True, 'dns_resolver': C.domain_dns_resolver()}]
    def unknown(value, **kw):
        return SimpleNamespace(unknown_deliverability='timeout')
    monkeypatch.setattr(C, 'validate_email', unknown)
    assert await C.check_email_domain('info@practice.test') == 'unknown'
    def no_mail(value, **kw):
        raise EmailUndeliverableError('null MX')
    monkeypatch.setattr(C, 'validate_email', no_mail)
    assert await C.check_email_domain('info@practice.test') == 'no_mail_domain'


@pytest.mark.asyncio
async def test_validation_metadata_survives_rediscovery_and_no_prospects_created(tmp_path):
    import json
    state = StateManager(str(tmp_path / 'evidence.db'))
    await state.init_db()
    company = Company(name='Practice', domain='practice.test')
    company.id = await state.add_company(company)
    checks = {'info@practice.test': {'syntax': 'valid', 'domain': 'mail_domain_present', 'kind': 'role'}}
    await state.save_public_company_emails(company.id, ['info@practice.test'], 'https://practice.test', checks)
    await state.save_public_company_emails(company.id, ['info@practice.test'], 'https://practice.test/kontakt')
    async with state._connect() as db:
        rows = await (await db.execute('SELECT * FROM company_public_emails')).fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0][4]) == checks['info@practice.test']
    assert rows[0][5] and rows[0][3]
    assert await state.get_contacts_for_company(company.id) == []


@pytest.mark.asyncio
async def test_lookup_uses_browser_only_when_html_has_no_relevant_email(tmp_path, monkeypatch):
    state = StateManager(str(tmp_path / 'browser.db'))
    await state.init_db()
    company = Company(name='Practice', domain='practice.test', website='https://practice.test')
    company.id = await state.add_company(company)
    calls = []
    async def allowed(*args):
        return True
    async def render(url, domain):
        calls.append((url, domain))
        return '<p>info [at] practice [dot] test</p>', url
    async def check(email):
        return 'mail_domain_present'
    monkeypatch.setattr(C, '_public_company_url', allowed)
    monkeypatch.setattr(C, 'render_contact_page', render)
    monkeypatch.setattr(C, 'check_email_domain', check)
    original = httpx.AsyncClient
    body = ['<p>JS required</p>']
    monkeypatch.setattr(C.httpx, 'AsyncClient', lambda **kw: original(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body[0],
            headers={'content-type': 'text/html'})), **kw))
    assert (await C.lookup_company_emails(company, state))['found'] == 1
    assert len(calls) == 1
    calls.clear()
    body[0] = '<p>info@practice.test</p>'
    assert (await C.lookup_company_emails(company, state))['found'] == 1
    assert calls == []


def test_idn_company_domain_matches_published_unicode_address():
    assert C.relevant_company_emails(['info@bücher.de', 'web@agency.de'], 'xn--bcher-kva.de') == ['info@bücher.de']


def test_different_mail_domain_requires_visible_owner_contact_evidence():
    html='''<section><h2>Kontakt</h2><address>Ernst Aulbach Bau-GmbH
    Tel.: 06021 424021 Mail: <a href="mailto:info@e-aulbach-bau.de">E-Mail</a></address></section>
    <p>Website von Webdesign Example: designer@agency.test</p>'''
    found=C.relevant_company_emails(C.extract_public_emails(html),'aulbach-bau.de',html=html,source='https://www.aulbach-bau.de/',company_name='Ernst Aulbach GmbH')
    assert found==['info@e-aulbach-bau.de']
    assert C.relevant_company_emails(['info@e-aulbach-bau.de'],'aulbach-bau.de')==[]


@pytest.mark.parametrize('html,source',[
    ('<p>Mail: info@e-aulbach-bau.de</p>','https://aulbach-bau.de/'),
    ('<p>Kontakt: Ernst Aulbach GmbH, Website von Agency, designer@agency.test</p>','https://aulbach-bau.de/impressum'),
    ('<p>Kontakt: Ernst Aulbach GmbH, info@e-aulbach-bau.de</p>','https://third-party.test/kontakt'),
    ('<script>Ernst Aulbach GmbH Kontakt info@e-aulbach-bau.de</script>','https://aulbach-bau.de/'),
    ('<p>Ernst Aulbach GmbH</p><p>Datenschutzbeauftragter: external@privacy.test</p>','https://aulbach-bau.de/impressum'),
])
def test_contact_evidence_does_not_accept_agencies_or_address_as_company_name(html,source):
    assert not C.official_contact_emails(html,source,'aulbach-bau.de','Ernst Aulbach GmbH')


@pytest.mark.asyncio
async def test_alternate_domain_lookup_saves_source_and_association_without_verifying(tmp_path,monkeypatch):
    import json
    state=StateManager(str(tmp_path/'alternate.db'));await state.init_db()
    company=Company(name='Ernst Aulbach GmbH',domain='aulbach-bau.de',website='https://www.aulbach-bau.de/')
    company.id=await state.add_company(company)
    async def allowed(*args): return True
    async def dns(*args): return 'mail_domain_present'
    monkeypatch.setattr(C,'_public_company_url',allowed)
    monkeypatch.setattr(C,'check_email_domain',dns)
    original=httpx.AsyncClient
    def respond(request):
        return httpx.Response(200,text='<div>Ernst Aulbach Bau-GmbH Tel.: 123 Mail: info@e-aulbach-bau.de</div><p>Website von Agentur: designer@agency.test</p>',headers={'content-type':'text/html'})
    monkeypatch.setattr(C.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    result=await C.lookup_company_emails(company,state)
    assert result['status']=='found' and result['found']==1
    assert result['diagnostics'][-1]['code']=='found'
    async with state._connect() as db:
        row=await (await db.execute('SELECT email,source_url,validation_json FROM company_public_emails LIMIT 1')).fetchone()
    assert row[0]=='info@e-aulbach-bau.de' and row[1].startswith('https://www.aulbach-bau.de/')
    assert json.loads(row[2])['association']=='official_contact_block'
    assert await state.get_contacts_for_company(company.id)==[]
