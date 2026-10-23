"""Manual workflow persistence and campaign-scoped review. No real mail."""
import asyncio
from tests.test_crm_actions import crm_client


def make_draft(client, name, pid):
    response=client.post('/api/campaign-drafts',json={'name':name,'prospect_ids':[pid],
        'sequence':[{'subject':'Question','body':'Hello.'}]})
    assert response.status_code==200,response.text
    return response.json()['id']


def test_saved_draft_can_be_reloaded_without_preparing_or_approving(crm_client):
    client,sm=crm_client
    cid=make_draft(client,'Resume','p0')
    detail=client.get('/api/campaign-drafts/'+cid).json()
    assert detail['name']=='Resume' and detail['prospect_ids']==['p0']
    assert detail['editable'] and detail['outbox_summary']=={}
    assert asyncio.run(sm.get_outbox())==[]


def test_scoped_review_and_bulk_approval_cannot_touch_other_campaign(crm_client):
    client,sm=crm_client
    first=make_draft(client,'First','p0');second=make_draft(client,'Second','p1')
    for cid in [first,second]:
        assert client.post('/api/campaign-drafts/'+cid+'/prepare',json={'revision':0,'outreach_acknowledgment':client.get('/api/campaign-drafts/'+cid).json()['outreach_history']['acknowledgment']}).status_code==200
    detail=client.get('/api/campaign-drafts/'+first).json()
    assert not detail['editable'] and detail['outbox_summary']=={'pending_review':1}
    data=client.get('/api/outbox',params={'campaign_id':first}).json()
    assert data['campaign_id']==first and data['campaign_name']=='First'
    assert len(data['pending'])==1 and data['pending'][0]['campaign_id']==first
    approved=client.post('/api/outbox/approve-all',params={'campaign_id':first}).json()
    assert approved['approved']==1
    assert client.get('/api/campaign-drafts/'+first).json()['outbox_summary']=={'approved':1}
    assert client.get('/api/campaign-drafts/'+second).json()['outbox_summary']=={'pending_review':1}
    assert client.post('/api/campaign-drafts/'+first+'/prepare',json={'revision':0}).json()['already_prepared']
    assert len(asyncio.run(sm.get_outbox()))==2
    assert not asyncio.run(sm.get_outbox(status='sent'))


def test_unknown_or_injected_scope_never_becomes_global(crm_client):
    client,sm=crm_client
    cid=make_draft(client,'Hold','p0')
    client.post('/api/campaign-drafts/'+cid+'/prepare',json={'revision':0})
    scope="missing' OR 1=1 --"
    assert not client.get('/api/outbox',params={'campaign_id':scope}).json()['pending']
    assert client.post('/api/outbox/approve-all',params={'campaign_id':scope}).json()['approved']==0
    assert len(asyncio.run(sm.get_outbox(status='pending_review')))==1
