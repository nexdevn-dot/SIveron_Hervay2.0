import asyncio
import json
from tests.test_crm_actions import crm_client
from tests.test_campaign_workflow import make_draft
from tests.test_campaign_results import convo
from tests.test_outreach_history import sql


def test_reply_review_stale_and_new_receipt_reopens_task(crm_client):
    client,sm=crm_client;convo(sm)
    tasks=client.get('/api/work-items').json()['items'];assert len(tasks)==1 and tasks[0]['kind']=='reply'
    key=tasks[0]['key'];detail=client.get('/api/conversations/c/review').json()
    assert client.post('/api/conversations/c/review',json={'fingerprint':'stale'}).status_code==409
    assert client.post('/api/conversations/c/review',json={'fingerprint':detail['fingerprint']}).status_code==200
    assert client.get('/api/work-items').json()['total']==0
    assert client.get('/api/work-items/'+key).status_code==410
    thread=detail['thread']+[{'sender':'prospect','provider_id':'new','content':'Another question','timestamp':'2026-02-01T00:00:00Z'}]
    sql(sm,"UPDATE conversations SET thread_json=? WHERE id='c'",(json.dumps(thread),))
    assert client.get('/api/work-items').json()['total']==1
    assert client.post('/api/conversations/c/review',json={'fingerprint':detail['fingerprint']}).status_code==409
    assert asyncio.run(sm.get_prospect('p0')).status=='new'


def test_outgoing_only_closed_and_answered_threads_are_not_actionable(crm_client):
    client,sm=crm_client
    convo(sm,cid='empty',thread=[])
    convo(sm,cid='sent',thread=[{'sender':'harvey','content':'Hello'}])
    convo(sm,cid='closed',status='closed')
    convo(sm,cid='answered',thread=[{'sender':'prospect','content':'Hi'},{'sender':'harvey','content':'Answered'}])
    assert client.get('/api/work-items').json()['total']==0


def test_approval_tasks_are_grouped_and_resolve_without_duplicates(crm_client):
    client,sm=crm_client
    cid=make_draft(client,'Tasks','p0');client.post(f'/api/campaign-drafts/{cid}/prepare',json={'revision':0})
    tasks=client.get('/api/work-items').json()['items']
    task=next(t for t in tasks if t['kind']=='approval');assert task['count']==1
    assert 'outbox' not in {i['key'] for i in client.get('/api/today').json()['items']}
    mid=task['message_id']
    exact=client.get('/api/outbox',params={'item_id':mid,'campaign_id':cid}).json();assert len(exact['pending'])==1
    assert not client.get('/api/outbox',params={'item_id':mid,'campaign_id':'wrong'}).json()['pending']
    client.post('/api/outbox/'+mid+'/approve')
    tasks=client.get('/api/work-items').json()['items']
    assert not any(t['kind']=='approval' for t in tasks)
    assert any(t['kind']=='blocked' and t['message_id']==mid for t in tasks)
    sql(sm,"UPDATE outbox SET status='cancelled' WHERE id=?",(mid,))
    assert client.get('/api/work-items').json()['total']==0


def test_task_count_is_uncapped_and_pagination_is_explicit(crm_client):
    client,sm=crm_client
    for n in range(35):convo(sm,cid=str(n))
    data=client.get('/api/work-items').json();assert data['total']==35 and len(data['items'])==30 and data['pages']==2
    assert len(client.get('/api/work-items?page=2').json()['items'])==5


def test_ordinary_waits_are_not_actionable_blockers(crm_client,monkeypatch):
    from unittest.mock import AsyncMock
    from types import SimpleNamespace
    from harvey.work_items import work_items
    client,sm=crm_client
    sql(sm,"INSERT INTO outbox(id,prospect_id,status) VALUES ('scheduled','p0','approved')")
    monkeypatch.setattr('harvey.work_items.assess_message',AsyncMock(return_value={'state':'waiting','reasons':[{'code':'scheduled'}]}))
    data=asyncio.run(work_items(sm,(SimpleNamespace(),{},[])))
    assert data['total']==0
