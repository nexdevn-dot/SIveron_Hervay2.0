"""Cleanup removes only records without any usable contact channel, with undo."""
import asyncio

import pytest
from fastapi.testclient import TestClient

import harvey.dashboard as dashboard
from harvey.models import Company, Prospect
from harvey.state import StateManager


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    path = tmp_path / 'cleanup.db'
    monkeypatch.setattr(dashboard, 'DB_PATH', path)
    monkeypatch.setattr(dashboard, '_company_contact_lookups', set())
    state = StateManager(str(path))
    ids = {}
    async def seed():
        await state.init_db()
        for index in range(37):
            ids[f'empty{index}'] = await state.add_company(Company(name=f'Empty {index}', location='Emptyville'))
        for key, fields in {
            'phone': {'phone': '+49 123'}, 'website': {'website': 'https://practice.test'},
            'domain': {'domain': 'practice.test'}, 'public': {}, 'person_email': {}, 'person_phone': {},
        }.items():
            ids[key] = await state.add_company(Company(name=key, location='Contactville', **fields))
        await state.save_public_company_emails(ids['public'], ['info@practice.test'], 'https://practice.test')
        await state.add_prospect(Prospect(company_id=ids['person_email'], first_name='Ada', email='ada@practice.test'))
        await state.add_prospect(Prospect(company_id=ids['person_phone'], first_name='Ben', phone='+49 456'))
        # Invalid addresses and people without contact channels do not protect a company.
        await state.save_public_company_emails(ids['empty0'], ['broken'], '')
        await state.add_prospect(Prospect(company_id=ids['empty1'], first_name='No channel', email='bad@practice.test', email_status='invalid'))
    asyncio.run(seed())
    with TestClient(dashboard.app) as client:
        yield client, state, ids


def test_cleanup_covers_all_pages_and_preserves_every_contact_channel(fixture):
    client, state, ids = fixture
    assert client.get('/api/companies/page').json()['total'] == 43
    result = client.post('/api/companies/cleanup').json()
    assert result['removed'] == 37
    page = client.get('/api/companies/page').json()
    assert page['total'] == 6 and page['pages'] == 1
    assert {row['id'] for row in page['items']} == {ids[key] for key in (
        'phone', 'website', 'domain', 'public', 'person_email', 'person_phone')}
    assert page['filters']['location'] == ['Contactville']
    assert len(client.get('/api/companies').json()) == 6
    # History/people remain intact; the removal is reversible rather than cascading.
    assert len(asyncio.run(state.get_contacts_for_company(ids['empty1']))) == 1
    assert client.post('/api/companies/cleanup').json()['removed'] == 0
    restored = client.post('/api/companies/cleanup/' + result['batch_id'] + '/restore').json()
    assert restored == {'restored': 37}
    assert client.get('/api/companies/page').json()['total'] == 43
    assert client.post('/api/companies/cleanup/' + result['batch_id'] + '/restore').json() == {'restored': 0}


def test_cleanup_waits_for_running_email_jobs(fixture):
    client, state, ids = fixture
    async def queue():
        async with state._connect() as db:
            await db.execute("INSERT INTO company_email_jobs(id, status) VALUES ('pending', 'queued')")
            await db.commit()
    asyncio.run(queue())
    response = client.post('/api/companies/cleanup')
    assert response.status_code == 409 and response.json()['status'] == 'busy'
    assert client.get('/api/companies/page').json()['total'] == 43


def test_cleanup_waits_for_single_lookup_and_rejects_invalid_restore(fixture, monkeypatch):
    client, state, ids = fixture
    monkeypatch.setattr(dashboard, '_company_contact_lookups', {ids['phone']})
    assert client.post('/api/companies/cleanup').status_code == 409
    assert client.post('/api/companies/cleanup/not-a-batch/restore').status_code == 422


def test_cleanup_only_restores_its_own_batch(fixture):
    client, state, ids = fixture
    first = client.post('/api/companies/cleanup').json()
    new_id = asyncio.run(state.add_company(Company(name='Later record')))
    second = client.post('/api/companies/cleanup').json()
    assert second['removed'] == 1
    assert client.post('/api/companies/cleanup/' + first['batch_id'] + '/restore').json()['restored'] == 37
    remaining = client.get('/api/companies/page').json()['total']
    assert remaining == 43
    assert client.post('/api/companies/cleanup/' + second['batch_id'] + '/restore').json()['restored'] == 1


def test_scoped_cleanup_only_removes_requested_contactless_company(fixture):
    client,state,ids=fixture
    result=client.post('/api/companies/cleanup',json={'company_ids':[ids['empty0'],ids['phone']]}).json()
    assert result['removed']==1
    async def removed(cid):
        async with state._connect() as db:return (await (await db.execute('SELECT removed_at FROM companies WHERE id=?',(cid,))).fetchone())[0]
    assert asyncio.run(removed(ids['empty0']))
    assert not asyncio.run(removed(ids['empty2']))
    assert not asyncio.run(removed(ids['phone']))
    assert client.post('/api/companies/cleanup/'+result['batch_id']+'/restore').json()['restored']==1


@pytest.mark.parametrize('body',[{}, {'company_ids':[]},{'company_ids':None},{'company_ids':[[]]},{'company_ids':['x'],'all':True}])
def test_bad_scoped_cleanup_never_falls_back_to_inventory(fixture,body):
    client,state,ids=fixture
    assert client.post('/api/companies/cleanup',json=body).status_code==422
    assert client.get('/api/companies/page').json()['total']==43
