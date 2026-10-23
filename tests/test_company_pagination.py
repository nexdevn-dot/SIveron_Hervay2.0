"""The company inventory filters the entire database before paging."""

import asyncio

import pytest
from fastapi.testclient import TestClient

import harvey.dashboard as dashboard
from harvey.models import Prospect
from harvey.state import StateManager


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / 'companies.db'
    monkeypatch.setattr(dashboard, 'DB_PATH', db_path)
    state = StateManager(str(db_path))

    async def seed():
        await state.init_db()
        async with state._connect() as db:
            await db.executemany(
                'INSERT INTO companies (id, name, domain, industry, location, phone, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                [(f'fixture{i:03}', 'Müller & Söhne 100%' if i == 0 else f'Company {i:03}',
                  f'company{i}.test' if i % 3 else '',
                  'Elektro' if i % 2 == 0 else 'Praxis',
                  'Bielefeld' if i % 2 == 0 else 'Berlin', '+49 12345' if i == 4 else '',
                  '2026-01-01T00:00:00') for i in range(211)],
            )
            await db.commit()
        await state.save_public_company_emails('fixture002', ['info@public.test'], 'https://public.test/contact')
        await state.save_public_company_emails('fixture006', ['not-an-address'], '')
        await state.add_prospect(Prospect(company_id='fixture004', first_name='Ben', last_name='Fixture',
                                         title='Owner', email='ben@personal.test', email_status='verified'))
        await state.add_prospect(Prospect(company_id='fixture005', first_name='Sue', last_name='Fixture',
                                         title='Owner', email='invalid@personal.test', email_status='invalid'))

    asyncio.run(seed())
    with TestClient(dashboard.app) as test_client:
        yield test_client


def test_pages_cover_the_full_inventory_without_duplicates_or_a_200_row_cap(client):
    pages = [client.get('/api/companies/page', params={'page': page}).json() for page in range(1, 9)]
    assert pages[0]['total'] == 211
    assert pages[0]['page_size'] == 30
    assert pages[0]['pages'] == 8
    assert [len(page['items']) for page in pages] == [30] * 7 + [1]
    ids = [item['id'] for page in pages for item in page['items']]
    assert len(set(ids)) == len(ids) == 211
    assert 'fixture210' in ids
    assert client.get('/api/companies/page?page=999').json()['page'] == 8


def test_email_filters_include_public_and_personal_mail_but_not_invalid_addresses(client):
    result = client.get('/api/companies/page?email=with').json()
    assert result['total'] == 2
    rows = {row['id']: row for row in result['items']}
    assert set(rows) == {'fixture002', 'fixture004'}
    assert rows['fixture002']['contact_emails'][0]['status'] == 'unverified'
    assert rows['fixture004']['contact_emails'][0]['status'] == 'verified'
    assert rows['fixture004']['contact_count'] == 1
    assert rows['fixture004']['contact_phones'] == ['+49 12345']
    assert client.get('/api/companies/page?email=without').json()['total'] == 209


def test_combined_filters_and_filter_choices_use_the_full_inventory(client):
    result = client.get('/api/companies/page', params={
        'location': 'Bielefeld', 'industry': 'Elektro', 'email': 'with', 'website': 'with',
    }).json()
    assert result['total'] == 2
    assert result['filters'] == {'location': ['Berlin', 'Bielefeld'], 'industry': ['Elektro', 'Praxis']}
    assert client.get('/api/companies/page?website=without').json()['total'] == 71
    assert client.get('/api/companies/page?website=with').json()['total'] == 140


@pytest.mark.parametrize(('query', 'total'), [
    ('MÜLLER', 1), ('100%', 1), ('info@public.test', 1), ('ben@personal.test', 1),
    ('+49 12345', 1), ('invalid@personal.test', 0), ("' OR 1=1 --", 0), ('_', 0),
])
def test_search_handles_unicode_email_phone_and_literal_sql_characters(client, query, total):
    result = client.get('/api/companies/page', params={'q': query}).json()
    assert result['total'] == total


def test_an_empty_filter_result_has_consistent_page_metadata(client):
    result = client.get('/api/companies/page', params={'location': 'No such location', 'page': 7}).json()
    assert result['items'] == []
    assert result['total'] == 0
    assert result['page'] == result['pages'] == 1


@pytest.mark.parametrize('query', ['page=0', 'page=bad', 'email=unknown', 'website=unknown', 'q=' + 'x' * 201])
def test_invalid_filter_parameters_are_rejected(client, query):
    assert client.get('/api/companies/page?' + query).status_code == 422


def test_paginated_reads_never_start_contact_lookup(client, monkeypatch):
    import harvey.collectors.company_contacts as contacts

    async def forbidden(*args, **kwargs):
        pytest.fail('Filtering or paging must never crawl a site')

    monkeypatch.setattr(contacts, 'lookup_company_emails', forbidden)
    assert client.get('/api/companies/page?email=without').status_code == 200


def test_public_email_validation_is_exposed_without_marking_verified(client):
    state = StateManager(str(dashboard.DB_PATH))
    asyncio.run(state.save_public_company_emails('fixture002', ['info@public.test'],
        'https://public.test/contact', {'info@public.test': {
            'syntax': 'valid', 'domain': 'mail_domain_present', 'kind': 'role'}}))
    rows = client.get('/api/companies/page?email=with').json()['items']
    entry = next(row for row in rows if row['id'] == 'fixture002')['contact_emails'][0]
    assert entry['status'] == 'unverified'
    assert entry['validation']['domain'] == 'mail_domain_present'
    assert entry['checked_at'] and entry['found_at']


def test_email_job_api_rejects_invalid_selection(client):
    assert client.post('/api/company-email-jobs', json={'company_ids': []}).status_code == 422
    assert client.post('/api/company-email-jobs', json={'company_ids': ['missing']}).status_code == 404
    assert client.get('/api/company-email-jobs/latest').json() is None


def test_email_job_api_runs_and_restores_results(client, monkeypatch):
    from harvey.collectors import company_contacts
    import time
    async def lookup(company, state):
        return {'status': 'found', 'found': 1}
    monkeypatch.setattr(company_contacts, 'lookup_company_emails', lookup)
    response = client.post('/api/company-email-jobs', json={
        'company_ids': ['fixture001', 'fixture002', 'fixture001']})
    assert response.status_code == 200
    job_id = response.json()['id']
    for _ in range(30):
        result = client.get('/api/company-email-jobs/latest').json()
        if result['status'] == 'completed':
            break
        time.sleep(0.01)
    assert result['id'] == job_id and result['total'] == result['done'] == 2
    assert result['counts']['found'] == 2
