"""Explicit selection removes only those companies and remains reversible."""
import asyncio
from tests.test_crm_actions import crm_client


def test_selected_removal_is_exact_idempotent_and_reversible(crm_client):
    client, state = crm_client
    async def seed():
        async with state._connect() as db:
            await db.executemany('INSERT INTO companies(id,name) VALUES (?,?)', [('selected-a','A'),('selected-b','B')])
            await db.execute("UPDATE prospects SET company_id='selected-a' WHERE id='p0'")
            await db.commit()
    asyncio.run(seed())
    data=client.post('/api/companies/remove-selected',json={'company_ids':['selected-a','selected-a','missing']}).json()
    assert data['removed']==1 and data['batch_id']
    assert client.get('/api/companies/selected-a/profile').status_code==404
    assert client.get('/api/companies/selected-b/profile').status_code==200
    assert len(client.get('/api/companies/selected-a/contacts').json())==1
    assert client.post('/api/companies/remove-selected',json={'company_ids':['selected-a']}).json()['removed']==0
    assert client.post('/api/companies/cleanup/'+data['batch_id']+'/restore').json()['restored']==1
    assert client.get('/api/companies/selected-a/profile').status_code==200
    assert asyncio.run(state.get_outbox())==[]


def test_invalid_selection_and_active_lookup_are_rejected(crm_client, monkeypatch):
    client, state = crm_client
    for data in [{},[],{'company_ids':[]},{'company_ids':'x'},{'company_ids':[1]},{'company_ids':['x']*1001}]:
        assert client.post('/api/companies/remove-selected',json=data).status_code==422
    import harvey.dashboard as dashboard
    monkeypatch.setattr(dashboard,'_company_contact_lookups',{'busy'})
    assert client.post('/api/companies/remove-selected',json={'company_ids':['x']}).status_code==409
