"""Contact-scoped research: evidence, explicit handoff and provider budgets."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from harvey import contact_research as research
from tests.test_people_contacts import setup_contacts


def person(client, email=''):
    result=client.post('/api/contacts',json={'company_id':'acme','first_name':'Julia','last_name':'Müller','email':email})
    assert result.status_code==200,result.text
    return result.json()['id']


async def seed(sm,cid,kind='person_explicit',email='julia@acme.test'):
    contact=await research.get_contact(sm,cid)
    async with sm._connect() as db:
        await db.execute("INSERT INTO contact_email_research(id,contact_id,status,config_json,snapshot_json) VALUES ('job',?,'completed','{}',?)",(cid,json.dumps(contact)))
        await db.execute("INSERT INTO contact_email_findings(id,job_id,email,kind,source_url,method) VALUES ('finding','job',?,?, 'https://acme.test/team','published_page')",(email,kind))
        await db.commit()
    return contact


def adopt(client,cid,**extra):
    return client.post(f'/api/contacts/{cid}/email-research/job/adopt',json=dict(finding_id='finding',reviewed=True,revision=0,**extra))


def test_classification_requires_published_person_entity_and_company_context():
    contact={'domain':'acme.test','company':'Acme','contact_type':'person','first_name':'Julia','last_name':'Müller'}
    html='<article><h3>Julia Müller</h3><p>Geschäftsführerin</p><a href="mailto:julia@acme.test">E-Mail</a></article><footer>info@acme.test</footer>'
    found={x['email']:x['kind'] for x in research.classify_page(html,'https://acme.test/team',contact)}
    assert found=={'julia@acme.test':'person_explicit','info@acme.test':'company_mailbox'}
    unrelated=html.replace('acme.test','other.test')
    assert {x['kind'] for x in research.classify_page(unrelated,'https://other.test',contact)}=={'unclear'}
    assert research.classify_page('<p>Julia Müller, contact our team</p>','https://acme.test',contact)==[]


def test_url_preserves_profile_identity_not_tracking():
    assert research.clean_url('https://www.facebook.com/profile.php?id=123&utm_source=x')=='https://www.facebook.com/profile.php?id=123'
    assert research.clean_url('https://example.test/a?api_key=secret#fragment')=='https://example.test/a'
    assert not research.clean_url('https://user:secret@example.test')
    assert not research.clean_url('javascript:alert(1)')


def test_settings_strict_and_only_key_presence(setup_contacts,monkeypatch):
    client,sm=setup_contacts
    monkeypatch.setenv('HUNTER_API_KEY','secret-test-value')
    result=client.get('/api/settings/contact-research')
    assert result.json()['configured']['hunter'] and 'secret-test-value' not in result.text
    assert result.json()['settings']['hunter'] is False
    for data in [{'enabled':'yes'},{'max_pages':99},{'monthly_searches':-1},{'auto_send':True}]:
        assert client.post('/api/settings/contact-research',json=data).status_code==422


def test_explicit_adoption_and_stale_finding(setup_contacts):
    client,sm=setup_contacts;cid=person(client)
    contact=asyncio.run(seed(sm,cid));revision=contact['revision']
    endpoint=f'/api/contacts/{cid}/email-research/job/adopt'
    assert client.post(endpoint,json={'finding_id':'finding','revision':revision}).status_code==422
    assert client.post(endpoint,json={'finding_id':[],'revision':revision,'reviewed':True}).status_code==422
    assert asyncio.run(sm.get_prospect(cid)).email==''
    result=client.post(endpoint,json={'finding_id':'finding','revision':revision,'reviewed':True})
    assert result.status_code==200,result.text
    current=asyncio.run(sm.get_prospect(cid));assert current.email=='julia@acme.test' and not current.email_verified
    assert client.get(f'/api/contacts/{cid}/email-research/job').json()['stale']
    assert client.post(endpoint,json={'finding_id':'finding','revision':current.revision,'reviewed':True}).status_code==409
    async def notes():
        async with sm._connect() as db:return await (await db.execute("SELECT comment FROM feedback WHERE entity_id=?",(cid,))).fetchall()
    assert 'https://acme.test/team' in str(asyncio.run(notes()))
    assert asyncio.run(sm.get_outbox())==[]


@pytest.mark.parametrize('kind',['company_mailbox','unclear'])
def test_generic_address_requires_acknowledgment_and_replace(setup_contacts,kind):
    client,sm=setup_contacts;cid=person(client,'old@acme.test')
    contact=asyncio.run(seed(sm,cid,kind,'info@acme.test'))
    url=f'/api/contacts/{cid}/email-research/job/adopt'
    body={'finding_id':'finding','reviewed':True,'revision':contact['revision']}
    assert client.post(url,json=body).json()['error']=='replacement_required'
    body['replace']=True
    assert client.post(url,json=body).json()['error']=='unclear_acknowledgment_required'
    body['acknowledge_unclear']=True
    assert client.post(url,json=body).status_code==200
    assert asyncio.run(sm.get_prospect(cid)).email=='info@acme.test'


def test_exact_contact_scope_and_blocking(setup_contacts):
    client,sm=setup_contacts;cid=person(client);contact=asyncio.run(seed(sm,cid))
    other=client.post('/api/contacts',json={'first_name':'Ben','last_name':'Other'}).json()['id']
    assert adopt(client,other).status_code==422
    async def block():
        async with sm._connect() as db:
            await db.execute('UPDATE prospects SET do_not_contact=1 WHERE id=?',(cid,));await db.commit()
    asyncio.run(block())
    assert adopt(client,cid).json()['error']=='contact_blocked'
    assert client.post(f'/api/contacts/{cid}/email-research',json={'sources':['website']}).json()['error']=='contact_blocked'
    assert asyncio.run(sm.get_prospect(cid)).email==''


def test_disabled_and_duplicate_adoption_preserve_record(setup_contacts):
    client,sm=setup_contacts;cid=person(client);asyncio.run(seed(sm,cid))
    client.post('/api/contacts',json={'first_name':'Ben','last_name':'Other','email':'julia@acme.test'})
    assert adopt(client,cid).status_code==422
    assert asyncio.run(sm.get_prospect(cid)).email==''
    assert not client.get(f'/api/contacts/{cid}/email-research/job').json()['items'][0]['adopted_at']
    client.post('/api/settings/contact-research',json={'enabled':False})
    assert adopt(client,cid).json()['error']=='research_disabled'


def test_bounded_website_run_persists_evidence_without_changing_contact(setup_contacts,monkeypatch):
    client,sm=setup_contacts;cid=person(client);seen=[]
    class Reader:
        def __init__(self,*args,**kwargs):pass
        async def read(self,url):
            seen.append(url)
            return SimpleNamespace(url=url,html='<article><h3>Julia Müller</h3><p>Geschäftsführerin</p><a href="mailto:julia@acme.test">Mail</a></article>')
    monkeypatch.setattr(research,'PublicPageReader',Reader)
    async def run():
        service=research.ResearchService(sm)
        with pytest.raises(ValueError):await service.create(cid,{'sources':[['website']]})
        jid=await service.create(cid,{'sources':['website'],'mode':'quick'})
        task=service.tasks[jid];await task
        return await service.snapshot(jid,cid)
    job=asyncio.run(run())
    assert job['status']=='completed' and len(job['items'])==1 and len(seen)==1
    assert job['items'][0]['kind']=='person_explicit'
    assert asyncio.run(sm.get_prospect(cid)).email==''


def test_hunter_uses_found_only_header_and_local_budget(setup_contacts,monkeypatch):
    client,sm=setup_contacts;cid=person(client);contact=asyncio.run(research.get_contact(sm,cid))
    prefs=research.ResearchSettings(hunter=True,hunter_monthly=1)
    asyncio.run(sm.set_setting('contact_research_settings',prefs.model_dump_json()))
    monkeypatch.setenv('HUNTER_API_KEY','private-test')
    requests=[];real_client=httpx.AsyncClient
    def handler(request):
        requests.append(request)
        assert request.url.path=='/v2/email-finder/found'
        assert request.headers['X-API-KEY']=='private-test' and 'private-test' not in str(request.url)
        return httpx.Response(200,json={'data':{'email':'julia@acme.test','sources':[{'uri':'https://acme.test/team'}],'verification':{'status':'valid'}}})
    monkeypatch.setattr(research.httpx,'AsyncClient',lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw))
    result=asyncio.run(research.hunter_search(sm,prefs,contact))
    assert result[0]['kind']=='provider_suggestion' and 'verification' not in result[0]
    with pytest.raises(ValueError,match='hunter_budget_exhausted'):asyncio.run(research.hunter_search(sm,prefs,contact))
    assert len(requests)==1


def test_search_budget_prevents_provider_call(setup_contacts,monkeypatch):
    client,sm=setup_contacts
    monkeypatch.setenv('SERPER_API_KEY','private-test')
    prefs=research.ResearchSettings(provider='serper',monthly_searches=0)
    with pytest.raises(ValueError,match='search_budget_exhausted'):asyncio.run(research.web_search(sm,prefs,'Julia Acme'))


def test_web_adapter_reads_organic_links_and_does_not_extract_snippets(setup_contacts,monkeypatch):
    client,sm=setup_contacts
    monkeypatch.setenv('SERPER_API_KEY','private-test')
    real_client=httpx.AsyncClient;requests=[]
    def handler(request):
        requests.append(request)
        assert request.url.host=='google.serper.dev'
        assert request.headers['X-API-KEY']=='private-test'
        assert 'Julia' in json.loads(request.content)['q']
        return httpx.Response(200,json={'organic':[{'title':'Team','link':'https://acme.test/team','snippet':'guessed@acme.test'}]})
    monkeypatch.setattr(research.httpx,'AsyncClient',lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw))
    result=asyncio.run(research.web_search(sm,research.ResearchSettings(provider='serper'),'Julia Acme'))
    assert result==['https://acme.test/team'] and len(requests)==1


def test_restart_marks_job_interrupted_without_resuming(setup_contacts):
    client,sm=setup_contacts;cid=person(client);asyncio.run(seed(sm,cid))
    async def mark():
        async with sm._connect() as db:
            await db.execute("UPDATE contact_email_research SET status='running' WHERE id='job'");await db.commit()
    asyncio.run(mark())
    data=client.get(f'/api/contacts/{cid}/email-research/job').json()
    assert data['status']=='interrupted' and len(data['items'])==1


def test_queued_messages_cancel_on_adopt_and_verification_resets(setup_contacts):
    client,sm=setup_contacts;cid=person(client,'old@acme.test')
    async def prepare():
        async with sm._connect() as db:
            await db.execute('UPDATE prospects SET email_verified=1 WHERE id=?',(cid,))
            await db.execute("INSERT INTO outbox(id,prospect_id,status,subject,body) VALUES ('research-queued',?,'approved','Test','Test')",(cid,))
            await db.commit()
    asyncio.run(prepare());contact=asyncio.run(seed(sm,cid))
    response=client.post(f'/api/contacts/{cid}/email-research/job/adopt',json={'finding_id':'finding','reviewed':True,'replace':True,'revision':contact['revision']})
    assert response.status_code==200,response.text
    assert not asyncio.run(sm.get_prospect(cid)).email_verified
    async def status():
        async with sm._connect() as db:return (await (await db.execute("SELECT status FROM outbox WHERE id='research-queued'")).fetchone())[0]
    assert asyncio.run(status())=='cancelled'
