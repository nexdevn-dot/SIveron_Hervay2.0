"""Read-only exact company profile shared by cohort and company views."""
import asyncio
from tests.test_crm_actions import crm_client


def test_company_profile_is_exact_and_excludes_removed_records(crm_client):
    client, state = crm_client
    async def seed():
        async with state._connect() as db:
            await db.execute("INSERT INTO companies(id,name,domain) VALUES ('profile-company','Example <Company>','example.com')")
            await db.execute("UPDATE prospects SET company_id='profile-company' WHERE id='p0'")
            await db.commit()
    asyncio.run(seed())
    response = client.get('/api/companies/profile-company/profile')
    assert response.status_code == 200
    data = response.json()
    assert data['company']['name'] == 'Example <Company>'
    assert [p['id'] for p in data['contacts']] == ['p0']
    assert client.get('/api/companies/missing/profile').status_code == 404
    assert client.get('/api/companies/missing%27%20OR%201=1/profile').status_code == 404
    assert asyncio.run(state.get_outbox()) == []
    async def remove():
        async with state._connect() as db:
            await db.execute("UPDATE companies SET removed_at=CURRENT_TIMESTAMP WHERE id='profile-company'")
            await db.commit()
    asyncio.run(remove())
    assert client.get('/api/companies/profile-company/profile').status_code == 404
