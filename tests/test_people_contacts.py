"""Explicit contact flows: evidence first, no guessed people or verified emails."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

import harvey.dashboard as dashboard
from harvey.collectors.people import extract_people
from harvey.models import Company, Prospect
from harvey.state import StateManager


@pytest.fixture
def setup_contacts(tmp_path, monkeypatch):
    path = tmp_path / 'people.db'
    monkeypatch.setattr(dashboard, 'DB_PATH', path)
    monkeypatch.setattr(dashboard, '_people_jobs', None)
    state = StateManager(str(path))
    async def seed():
        await state.init_db()
        await state.add_company(Company(id='acme', name='Acme', domain='acme.test', website='https://acme.test'))
        async with state._connect() as db:
            await db.execute("INSERT INTO person_candidates(id,company_id,first_name,last_name,title,email,source_url) VALUES ('candidate','acme','Julia','Müller','Geschäftsführerin','julia@acme.test','https://acme.test/team')")
            await db.commit()
    asyncio.run(seed())
    with TestClient(dashboard.app) as client:
        yield client, state


def test_structured_people_microdata_and_no_mailbox_invention():
    html = '<script type="application/ld+json">' + json.dumps({'@type':'Organization','employee':[{'@type':'Person','name':'Julia Müller','jobTitle':'Geschäftsführerin','email':'Julia@acme.test'},{'@type':'Person','name':'Ben Becker','jobTitle':'Leiter'}]}) + '</script><footer>info@acme.test</footer>'
    rows = {p['first_name']:p for p in extract_people(html,'https://acme.test','acme.test')}
    assert rows['Julia']['email'] == 'julia@acme.test'
    assert rows['Ben']['email'] == ''
    micro = '<div itemscope itemtype="https://schema.org/Person"><span itemprop="name">Änne Weiß</span><span itemprop="jobTitle">Leiterin</span></div>'
    assert extract_people(micro,'https://acme.test/team','acme.test')[0]['last_name'] == 'Weiß'


def test_german_team_cards_preserve_person_boundary():
    html = '<article><h3>Dr. Julia Müller</h3><p>Geschäftsführerin</p><a href="mailto:julia@acme.test">E-Mail</a></article><article><h3>Ben Becker</h3><p>Vertriebsleiter</p></article><footer>info@acme.test</footer>'
    rows = {p['first_name']:p for p in extract_people(html,'https://acme.test/team','acme.test')}
    assert rows['Julia']['email'] == 'julia@acme.test'
    assert rows['Ben']['email'] == ''
    assert not extract_people('<h2>Unser Team</h2><p>Willkommen</p>', 'https://acme.test','acme.test')


def test_manual_person_optional_role_normalizes_and_deduplicates(setup_contacts):
    client, state = setup_contacts
    payload = dict(company_id='acme',first_name='Anna',last_name='Test',email='ANNA@acme.test')
    first = client.post('/api/contacts',json=payload)
    assert first.status_code == 200, first.text
    again = client.post('/api/contacts',json=payload).json()
    assert again['id'] == first.json()['id'] and again['duplicate']
    person = asyncio.run(state.get_prospect(again['id']))
    assert person.contact_type == 'person' and person.email == 'anna@acme.test'
    assert not person.email_verified and person.title == ''
    assert client.post('/api/contacts',json=dict(first_name='Anna')).status_code == 422
    assert client.post('/api/contacts',json=dict(payload,email='broken')).status_code == 422


def test_firm_contact_keeps_company_and_is_not_a_person(setup_contacts):
    client, state = setup_contacts
    payload = dict(company_id='acme', contact_type='company', email='info@acme.test')
    result = client.post('/api/contacts',json=payload)
    assert result.status_code == 200, result.text
    person = asyncio.run(state.get_prospect(result.json()['id']))
    assert person.full_name() == 'Acme' and not person.first_name and not person.is_valid()
    assert person.status == 'company_contact'
    assert asyncio.run(state.get_company('acme'))
    assert client.post('/api/contacts',json=payload).json()['duplicate']
    assert client.post('/api/contacts',json=dict(company_id='acme',first_name='Info',last_name='Person',email='info@acme.test')).status_code == 422


def test_new_company_manual_and_standalone_person(setup_contacts):
    client, state = setup_contacts
    payload = dict(contact_type='company',company_name='New Firm',website='https://newfirm.test',phone='+49 123')
    result = client.post('/api/contacts',json=payload)
    assert result.status_code == 200, result.text
    person = asyncio.run(state.get_prospect(result.json()['id']))
    assert person.company == 'New Firm' and person.company_id
    assert client.post('/api/contacts',json=payload).json()['duplicate']
    result = client.post('/api/contacts',json=dict(first_name='Nora',last_name='Test'))
    assert result.status_code == 200, result.text
    assert asyncio.run(state.get_prospect(result.json()['id'])).company_id == ''


def test_candidates_explicit_adoption_is_idempotent_and_has_source(setup_contacts):
    client, state = setup_contacts
    assert len(client.get('/api/person-candidates').json()) == 1
    assert client.get('/api/prospects').json() == []
    payload = dict(company_id='acme',first_name='Julia',last_name='Müller',title='Geschäftsführerin',email='julia@acme.test')
    result = client.post('/api/person-candidates/candidate/accept',json=payload)
    assert result.status_code == 200, result.text
    assert client.post('/api/person-candidates/candidate/accept',json=payload).json()['duplicate']
    assert client.get('/api/person-candidates').json() == []
    person = asyncio.run(state.get_prospect(result.json()['id']))
    assert person.source_url == 'https://acme.test/team' and not person.email_verified


def test_jobs_validate_queue_and_store_suggestions_without_prospects(setup_contacts, monkeypatch):
    client, state = setup_contacts
    async def lookup(company,state):
        return {'status':'found','found':1}
    monkeypatch.setattr('harvey.collectors.people.lookup_company_people',lookup)
    assert client.post('/api/company-people-jobs',json={'company_ids':[]}).status_code == 422
    assert client.post('/api/company-people-jobs',json={'company_ids':['missing']}).status_code == 404
    result = client.post('/api/company-people-jobs',json={'company_ids':['acme']})
    assert result.status_code == 200
    for _ in range(50):
        job = client.get('/api/company-people-jobs/latest').json()
        if job['status'] == 'completed': break
    assert job['done'] == 1 and job['counts']['found'] == 1
    assert client.get('/api/prospects').json() == []


def test_dismiss_and_removed_company_guard(setup_contacts):
    client, state = setup_contacts
    assert client.post('/api/person-candidates/candidate/dismiss').json()['dismissed']
    assert not client.get('/api/person-candidates').json()
    async def remove():
        async with state._connect() as db:
            await db.execute("UPDATE companies SET removed_at=CURRENT_TIMESTAMP WHERE id='acme'")
            await db.commit()
    asyncio.run(remove())
    assert client.post('/api/contacts',json=dict(company_id='acme',first_name='A',last_name='B')).status_code == 422


@pytest.mark.asyncio
async def test_people_queue_survives_stop_and_restart_without_creating_contacts(tmp_path, monkeypatch):
    from harvey.collectors.contact_jobs import ContactJobs
    state = StateManager(str(tmp_path / 'queue.db'))
    await state.init_db()
    for i in range(4):
        await state.add_company(Company(id=f'c{i}',name=f'Company {i}',domain=f'c{i}.test'))
    jobs = ContactJobs(state, 'people')
    calls = []
    async def lookup(company,state):
        calls.append(company.id)
        await jobs.stop(job_id)
        return {'status':'no_website','found':0}
    monkeypatch.setattr('harvey.collectors.people.lookup_company_people',lookup)
    # Creation may be persisted before the runner starts (e.g. server restart).
    monkeypatch.setattr(jobs,'start',lambda:None)
    job_id = await jobs.create([f'c{i}' for i in range(4)])
    restarted = ContactJobs(state,'people')
    await restarted.run()
    result = await restarted.snapshot(job_id)
    assert result['status'] == 'stopped' and 1 <= result['done'] <= 2
    assert len(calls) == result['done']
    assert await state.count_prospects_by_status() == {}


@pytest.mark.asyncio
async def test_official_page_fetch_is_bounded_and_keeps_evidence(tmp_path, monkeypatch):
    import httpx
    import harvey.collectors.people as people
    state = StateManager(str(tmp_path / 'fetch.db'))
    await state.init_db()
    company = Company(id='firm',name='Firm',domain='firm.test',website='https://firm.test')
    await state.add_company(company)
    calls = []
    async def guard(url,domain):
        from urllib.parse import urlparse
        return urlparse(url).hostname == domain
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/':
            return httpx.Response(200,headers={'content-type':'text/html'},text='<a href="/team">Team</a><a href="https://external.test/team">Team</a>')
        if request.url.path == '/team':
            return httpx.Response(200,headers={'content-type':'text/html'},text='<article><h3>Julia Müller</h3><p>Geschäftsführerin</p></article>')
        return httpx.Response(404)
    original = httpx.AsyncClient
    monkeypatch.setattr(people,'_public_company_url',guard)
    monkeypatch.setattr(people.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    result = await people.lookup_company_people(company,state)
    assert result == {'status':'found','found':1}
    assert not any('external.test' in url for url in calls)
    assert len(calls) <= 5
    async with state._connect() as db:
        row = await (await db.execute('SELECT email,source_url,status FROM person_candidates')).fetchone()
        assert row == ('','https://firm.test/team','pending')
        assert not await (await db.execute('SELECT id FROM prospects')).fetchall()


@pytest.mark.parametrize('heading,body', [('Unser Team','Unsere Geschäftsführer beraten Sie.'), ('Kontakt Aufnehmen','Ihr Ansprechpartner hilft Ihnen.'), ('Request Service','Our manager is available.')])
def test_headings_are_not_people(heading, body):
    assert not extract_people(f'<div><h2>{heading}</h2><p>{body}</p></div>', 'https://acme.test/team','acme.test')


def test_unicode_names_and_phone_duplicates_keep_existing_data(setup_contacts):
    client,state = setup_contacts
    first = client.post('/api/contacts',json=dict(company_id='acme',first_name='Julia',last_name='Müller',phone='+49 (123) 456')).json()
    again = client.post('/api/contacts',json=dict(company_id='acme',first_name='JULIA',last_name='MÜLLER',email='julia@acme.test')).json()
    assert again['duplicate'] and again['id'] == first['id']
    assert not asyncio.run(state.get_prospect(first['id'])).email
    third = client.post('/api/contacts',json=dict(company_id='acme',first_name='J.',last_name='Müller',phone='0049 123456')).json()
    assert third['duplicate'] and third['id'] == first['id']


def test_distinct_company_emails_can_be_adopted_with_same_phone(setup_contacts):
    client,state=setup_contacts
    async def evidence():
        await state.save_public_company_emails('acme',['sales@acme.test','office@acme.test'],'https://acme.test/contact')
    asyncio.run(evidence())
    ids=[]
    for email in ['sales@acme.test','office@acme.test']:
        payload={'company_id':'acme','contact_type':'company','email':email,'phone':'+49 12345678'}
        response=client.post('/api/contacts',json=payload)
        assert response.status_code==200,response.text
        ids.append(response.json()['id'])
        assert client.post('/api/contacts',json=payload).json()['duplicate']
    assert ids[0]!=ids[1]
    for pid in ids:
        person=asyncio.run(state.get_prospect(pid))
        assert person.company_id=='acme' and person.contact_type=='company'
        assert not person.email_verified and person.source_url=='https://acme.test/contact'
    assert asyncio.run(state.get_outbox())==[]


def test_company_email_adoption_does_not_convert_existing_person(setup_contacts):
    client,state=setup_contacts
    person=client.post('/api/contacts',json={'company_id':'acme','contact_type':'person','first_name':'Known','last_name':'Person','email':'known@acme.test'})
    assert person.status_code==200
    assert client.post('/api/contacts',json={'company_id':'acme','contact_type':'company','email':'known@acme.test'}).status_code==422
    assert asyncio.run(state.get_prospect(person.json()['id'])).contact_type=='person'


def test_wordpress_person_paragraphs_and_plaintext_email_stay_with_person():
    html='''<section><div class="wp-block-column"><p><strong>Rene Walter</strong></p>
    <p>Geschäftsführer</p><p>+49 5251 1571-0</p><p>rene.walter@example.test</p></div>
    <div class="wp-block-column"><p><strong>Rüdiger Schumacher</strong></p>
    <p>Geschäftsführer</p><p>ruediger.schumacher@example.test</p></div>
    <div><p><strong>Ben Becker</strong></p><p>Projektleiter</p></div></section>'''
    rows={p['first_name']:p for p in extract_people(html,'https://example.test','example.test')}
    assert rows['Rene']['email']=='rene.walter@example.test'
    assert rows['Rüdiger']['email']=='ruediger.schumacher@example.test'
    assert rows['Ben']['email']==''
    assert rows['Rene']['title']=='Geschäftsführer'


def test_wrapped_names_do_not_borrow_other_persons_role_or_mail():
    html='''<section><div><p><strong>Ben Becker</strong></p></div>
    <div><p><strong>Julia Müller</strong></p><p>Geschäftsführerin</p>
    <p>julia@example.test</p></div></section>'''
    rows=extract_people(html,'https://example.test','example.test')
    assert not any(p['first_name']=='Ben' and (p['email'] or p['title']) for p in rows)
    assert next(p for p in rows if p['first_name']=='Julia')['email']=='julia@example.test'
