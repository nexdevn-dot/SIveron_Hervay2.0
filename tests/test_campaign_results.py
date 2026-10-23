import asyncio
import json
from datetime import datetime,timezone
from tests.test_crm_actions import crm_client
from tests.test_campaign_workflow import make_draft
from tests.test_outreach_history import sql


def convo(sm,cid='c',campaign='',pid='p0',thread=None,status='open'):
    if thread is None:thread=[{'sender':'prospect','content':'Hello','provider_id':'receipt','timestamp':'2026-01-15T12:00:00Z'}]
    sql(sm,"INSERT INTO conversations(id,campaign_id,prospect_id,thread_json,status) VALUES (?,?,?,?,?)",(cid,campaign,pid,json.dumps(thread),status))


def test_results_count_contacts_messages_windows_and_unknown_research(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Results','p0')
    for mid,step,status,sent in [('m1',1,'sent','2026-01-10'),('m2',2,'sent','2026-01-11'),('m3',3,'approved',None)]:
        sql(sm,"INSERT INTO outbox(id,campaign_id,prospect_id,step,status,sent_at) VALUES (?,?, 'p0',?,?,?)",(mid,cid,step,status,sent))
    sql(sm,"UPDATE outbox SET approved_at='2026-01-09' WHERE campaign_id=?",(cid,))
    convo(sm,campaign=cid,thread=[{'sender':'prospect','content':'Hi','provider_id':'receipt','timestamp':'2026-01-15T00:00:00Z'}]*2)
    convo(sm,cid='copy',campaign=cid,thread=[{'sender':'prospect','content':'Hi','provider_id':'receipt','timestamp':'2026-01-15T00:00:00Z'}])
    data=client.get(f'/api/campaigns/{cid}/results?start=2026-01-01&end=2026-01-31').json()
    assert data['participants']==1 and data['contactable_current']==1
    assert data['approved']['contacts']==1 and data['approved']['messages']==3
    assert data['sent']['contacts']==1 and data['sent']['messages']==2
    assert data['replied']['contacts']==1 and data['replied']['messages']==1
    assert data['researched'] is None and data['external_delivery'] is None
    assert data['qualified']['contacts']==0 and data['meeting']['unassessed_conversations']==2
    narrow=client.get(f'/api/campaigns/{cid}/results?start=2026-01-11&end=2026-01-11').json()
    assert narrow['sent']['messages']==1 and narrow['replied']['messages']==0
    assert client.get(f'/api/campaigns/{cid}/results?end=9999-12-31').status_code==422
    assert client.get(f'/api/campaigns/{cid}/results?start=2026-02-01&end=2026-01-01').status_code==422


def test_explicit_outcomes_and_corrections_never_change_contact_or_send_state(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Outcomes','p0');convo(sm,campaign=cid)
    detail=client.get('/api/conversations/c/review').json()
    assert detail['outcome']['qualified'] is None
    payload={'qualified':True,'meeting':True,'note':'Confirmed manually','revision':0}
    assert client.post('/api/conversations/c/outcome',json=payload).status_code==200
    assert client.post('/api/conversations/c/outcome',json=payload).status_code==409
    data=client.get(f'/api/campaigns/{cid}/results').json()
    assert data['qualified']['contacts']==1 and data['meeting']['contacts']==1
    assert data['sent']['messages']==0
    detail=client.get('/api/conversations/c/review').json()
    assert client.post('/api/conversations/c/outcome',json={**payload,'qualified':False,'meeting':None,'revision':detail['outcome']['revision']}).status_code==200
    data=client.get(f'/api/campaigns/{cid}/results').json()
    assert data['qualified']['contacts']==0 and data['meeting']['unassessed_conversations']==1
    assert asyncio.run(sm.get_prospect('p0')).status=='new'
    assert asyncio.run(sm.get_outbox())==[]


def test_legacy_approval_times_are_not_invented(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Legacy','p0')
    sql(sm,"INSERT INTO outbox(id,campaign_id,prospect_id,status,sent_at) VALUES ('legacy',?,'p0','sent','2020-01-01')",(cid,))
    data=client.get(f'/api/campaigns/{cid}/results').json()
    assert data['approved']['messages']==0 and data['unknown_approval_dates']==1
    assert data['sent']['messages']==1


def test_approval_trigger_records_future_approvals_once(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Approval','p0')
    client.post(f'/api/campaign-drafts/{cid}/prepare',json={'revision':0})
    item=asyncio.run(sm.get_outbox())[0]
    assert not item['approved_at']
    client.post('/api/outbox/'+item['id']+'/approve')
    stamp=asyncio.run(sm.get_outbox(status='approved'))[0]['approved_at'];assert stamp
    assert client.get(f'/api/campaigns/{cid}/results').json()['approved']['messages']==1
    client.post('/api/outbox/'+item['id']+'/approve')
    assert asyncio.run(sm.get_outbox(status='approved'))[0]['approved_at']==stamp


def test_latest_explicit_contact_outcome_wins_across_threads_and_note_keeps_dates(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Latest outcome','p0')
    convo(sm,cid='older',campaign=cid);convo(sm,cid='newer',campaign=cid)
    for con,value in [('older',True),('newer',False)]:
        assert client.post(f'/api/conversations/{con}/outcome',json={'revision':0,'qualified':value,'meeting':None,'note':''}).status_code==200
    data=client.get(f'/api/campaigns/{cid}/results').json();assert data['qualified']['contacts']==0
    old=client.get('/api/conversations/newer/review').json()['outcome']
    client.post('/api/conversations/newer/outcome',json={'revision':1,'qualified':False,'meeting':None,'note':'Clarified'})
    changed=client.get('/api/conversations/newer/review').json()['outcome']
    assert changed['qualified_at']==old['qualified_at']
