from types import SimpleNamespace
import dns.message
import dns.query
import dns.rrset
import pytest

from harvey.email_checks import email_checks, normalize_public_email, send_address_valid
from tests.test_crm_actions import crm_client
from harvey.collectors import company_contacts as contacts


def test_syntax_transport_and_public_discovery_are_distinct():
    assert email_checks('info@bücher.de')['syntax_valid']
    assert not send_address_valid('info@bücher.de')  # No implicit SMTP/IDN transport expansion.
    assert normalize_public_email('INFO@BÜCHER.DE')=='info@bücher.de'
    assert not send_address_valid('first..last@business.org')
    assert send_address_valid('known@business.org')
    assert email_checks('')['reason']=='empty'
    assert email_checks('broken')['reason']=='syntax_invalid'
    assert email_checks('known@bücher.de')['reason']=='transport_unsupported'
    assert normalize_public_email('someone@example.com') is None


@pytest.mark.asyncio
async def test_dns_resolver_is_reused_across_mailboxes_and_honors_expiry(monkeypatch):
    contacts.domain_dns_resolver.cache_clear()
    resolver=contacts.domain_dns_resolver()
    calls=[]
    def answer(query, *args, **kwargs):
        calls.append(str(query.question[0].name))
        response=dns.message.make_response(query)
        response.index=None
        response.answer.append(dns.rrset.from_text('cache-company.org.',60,'IN','MX','10 mx.cache-company.org.'))
        return response
    monkeypatch.setattr(dns.query,'udp',answer)
    assert await contacts.check_email_domain('one@cache-company.org')=='mail_domain_present'
    assert await contacts.check_email_domain('two@cache-company.org')=='mail_domain_present'
    assert len(calls)==1
    # Force the cached DNS answer to expire without waiting or performing live DNS.
    for node in list(resolver.cache.data.values()):node.value.expiration=0
    assert await contacts.check_email_domain('three@cache-company.org')=='mail_domain_present'
    assert len(calls)==2
    resolver.cache.flush()


@pytest.mark.asyncio
async def test_temporary_unknown_does_not_turn_into_no_mail_domain(monkeypatch):
    values=iter([SimpleNamespace(mx=None), SimpleNamespace(mx=[(10,'mx.business.org')])])
    monkeypatch.setattr(contacts,'validate_email',lambda *a,**kw:next(values))
    assert await contacts.check_email_domain('info@business.org')=='unknown'
    assert await contacts.check_email_domain('info@business.org')=='mail_domain_present'


def test_contact_and_campaign_reads_expose_checks_without_dns(crm_client, monkeypatch):
    import asyncio
    client,state=crm_client
    def no_dns(*a,**kw):raise AssertionError('No DNS during read')
    monkeypatch.setattr(contacts,'domain_dns_resolver',no_dns)
    row=client.get('/api/contacts/page').json()['items'][0]
    assert row['email_checks']['send_supported']
    async def legacy_address():
        async with state._connect() as db:
            await db.execute("UPDATE prospects SET email='first..last@firm.test' WHERE id='p0'")
            await db.commit()
    asyncio.run(legacy_address())
    data=client.get('/api/contacts/page?q=first..last').json()
    assert data['items'][0]['email_checks']['reason']=='syntax_invalid'
    cid=client.post('/api/campaign-drafts',json={'name':'Checks','prospect_ids':['p0'],'sequence':[{'subject':'Question','body':'Hello.'}]}).json()['id']
    detail=client.get('/api/campaign-drafts/'+cid).json()
    assert not detail['contacts'][0]['email_checks']['send_supported']
    assert asyncio.run(state.get_outbox())==[]
