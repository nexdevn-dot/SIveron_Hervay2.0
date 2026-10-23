import asyncio
import json
from datetime import datetime,timezone,timedelta
from tests.test_crm_actions import crm_client
from tests.test_campaign_workflow import make_draft
from tests.test_campaign_results import convo
from tests.test_outreach_history import sql


def opportunity_payload(**kw):
    return {'title':'Reviewed interest','stage':'new','owner':'Test owner','next_action':'Prepare proposal',
        'next_due':datetime.now(timezone.utc).date().isoformat(),'interest_confirmed':True,**kw}


def test_template_excludes_recipients_sender_approvals_and_unknown_fields(crm_client):
    client,sm=crm_client
    cid=client.post('/api/campaign-drafts',json={'name':'Original','prospect_ids':['p0'],
        'brief':{'audience':'Teams','offer':'Advice','goal':'Conversation','sender':'PRIVATE SENDER','signature':'PRIVATE SIGNATURE'},
        'sequence':[{'subject':'Hello {{company}}','body':'Hello {{first_name}}','delay_days':0}]}).json()['id']
    # Simulate private/source metadata that must never travel into a template.
    sql(sm,"UPDATE campaigns SET brief_json=json_set(brief_json,'$.email_verification_optional',1,'$.token','SECRET') WHERE id=?",(cid,))
    response=client.post('/api/workflow-templates',json={'name':'Reusable','campaign_id':cid,'revision':0,
        'search':{'terms':['Bauunternehmen'],'cities':['Mainz'],'provider':'osm','credential':'SECRET','max_spend':999,'email_search':True}})
    assert response.status_code==200,response.text
    tid=response.json()['id'];templates=client.get('/api/workflow-templates').json();template=templates[0]
    assert set(template)=={'id','name','brief','search','sequence','target_profile_id'}
    assert set(template['brief'])=={'audience','offer','goal'}
    assert 'PRIVATE' not in json.dumps(template) and 'SECRET' not in json.dumps(template)
    assert 'max_spend' not in template['search'] and 'email_search' not in template['search']
    created=client.post(f'/api/workflow-templates/{tid}/instantiate',json={'name':'New draft'}).json()
    draft=client.get('/api/campaign-drafts/'+created['id']).json()
    assert draft['prospect_ids']==[] and draft['contacts']==[] and draft['status']=='manual_draft'
    assert draft['sequence'][0]['subject']=='Hello {{company}}'
    assert draft['brief']['sender']==draft['brief']['signature']=='' and not draft['outbox_summary']
    assert asyncio.run(sm.get_outbox())==[]
    assert client.delete('/api/workflow-templates/'+tid).status_code==200
    assert client.get('/api/campaign-drafts/'+created['id']).status_code==200


def test_template_rejects_stale_revision_invalid_recipe_and_reports_missing_profile(crm_client):
    client,sm=crm_client;client.get('/api/signals')
    pid=client.post('/api/target-profiles',json={'name':'Fit','require':['NO_WEBSITE']}).json()['id']
    cid=make_draft(client,'Original','p0')
    payload={'name':'Recipe','campaign_id':cid,'revision':0,'target_profile_id':pid,'search':{'maps_filter':'phone','provider':'google_maps'}}
    for bad in [{'revision':99},{'revision':False},{'search':{'radius_km':True}},{'search':{'provider':'arbitrary-service'}},{'search':{'terms':'wrong'}}]:
        assert client.post('/api/workflow-templates',json={**payload,**bad}).status_code==422
    tid=client.post('/api/workflow-templates',json=payload).json()['id']
    client.delete('/api/target-profiles/'+pid)
    response=client.post(f'/api/workflow-templates/{tid}/instantiate',json={'name':'Review missing profile'})
    assert response.json()['target_profile_missing'] is True


def test_template_drops_attachments_and_validation_metadata(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Attachments','p0')
    sql(sm,"UPDATE campaigns SET sequence_json=? WHERE id=?",(json.dumps([{'step':1,'subject':'Hello','body':'Plain','delay_days':0,'attachment_ids':['private-file'],'attachments':[{'path':'private-file'}],'readiness':'approved'}]),cid))
    tid=client.post('/api/workflow-templates',json={'name':'Safe','campaign_id':cid,'revision':0}).json()['id']
    template=client.get('/api/workflow-templates').json()[0]
    assert 'attachment' not in json.dumps(template) and 'readiness' not in json.dumps(template)


def test_opportunity_requires_review_and_reply_and_never_alters_outcomes(crm_client):
    client,sm=crm_client;cid=make_draft(client,'Source','p0');convo(sm,campaign=cid)
    assert client.post('/api/conversations/c/opportunity',json=opportunity_payload(interest_confirmed=False)).status_code==422
    convo(sm,cid='outgoing',thread=[{'sender':'harvey','content':'Hello'}])
    assert client.post('/api/conversations/outgoing/opportunity',json=opportunity_payload()).status_code==422
    response=client.post('/api/conversations/c/opportunity',json=opportunity_payload());assert response.status_code==200,response.text
    oid=response.json()['id']
    repeated=client.post('/api/conversations/c/opportunity',json=opportunity_payload()).json()
    assert repeated['id']==oid and repeated['already_linked']
    detail=client.get('/api/opportunities/'+oid).json()
    assert detail['prospect_id']=='p0' and detail['campaign_id']==cid and detail['sources'][0]['conversation_id']=='c'
    assert client.get('/api/conversations/c/review').json()['outcome']['qualified'] is None
    assert client.get(f'/api/campaigns/{cid}/results').json()['qualified']['contacts']==0
    assert asyncio.run(sm.get_outbox())==[] and asyncio.run(sm.get_prospect('p0')).status=='new'


def test_due_tasks_resolve_with_future_date_or_closed_stage_and_revisions_protect(crm_client):
    client,sm=crm_client;convo(sm)
    oid=client.post('/api/conversations/c/opportunity',json=opportunity_payload()).json()['id']
    task=next(x for x in client.get('/api/work-items').json()['items'] if x['kind']=='opportunity')
    assert task['opportunity_id']==oid and task['next_action']=='Prepare proposal'
    future=(datetime.now(timezone.utc).date()+timedelta(days=2)).isoformat()
    update=opportunity_payload(revision=0,next_due=future,stage='proposal')
    assert client.patch('/api/opportunities/'+oid,json=update).status_code==200
    assert client.patch('/api/opportunities/'+oid,json=update).status_code==409
    assert not any(x['kind']=='opportunity' for x in client.get('/api/work-items').json()['items'])
    assert client.get('/api/work-items/'+task['key']).status_code==410
    assert client.patch('/api/opportunities/'+oid,json=opportunity_payload(revision=1,stage='won',next_action='',next_due='')).status_code==200
    assert client.get('/api/opportunities?stage=won').json()['total']==1


def test_link_sources_preserves_campaigns_and_rejects_other_contacts(crm_client):
    client,sm=crm_client
    first=make_draft(client,'First','p0');second=make_draft(client,'Second','p0')
    convo(sm,cid='a',campaign=first);convo(sm,cid='b',campaign=second);convo(sm,cid='wrong',pid='p1')
    oid=client.post('/api/conversations/a/opportunity',json=opportunity_payload()).json()['id']
    assert client.post('/api/conversations/b/opportunity',json={'interest_confirmed':True,'link_id':oid}).status_code==200
    assert client.post('/api/conversations/wrong/opportunity',json={'interest_confirmed':True,'link_id':oid}).status_code==422
    detail=client.get('/api/opportunities/'+oid).json()
    assert detail['campaign_id']==first and {s['campaign_id'] for s in detail['sources']}=={first,second}
    assert detail['revision']==0


def test_open_opportunity_needs_next_task_date_and_stage_is_validated(crm_client):
    client,sm=crm_client;convo(sm)
    for bad in [{'next_action':''},{'next_due':''},{'next_due':'2026-02-30'},{'stage':'auto-send'}]:
        assert client.post('/api/conversations/c/opportunity',json=opportunity_payload(**bad)).status_code==422
    sql(sm,"UPDATE prospects SET do_not_contact=1 WHERE id='p0'")
    oid=client.post('/api/conversations/c/opportunity',json=opportunity_payload(stage='lost',next_action='',next_due='')).json()['id']
    assert client.get('/api/opportunities/'+oid).json()['do_not_contact']==1
    assert asyncio.run(sm.get_prospect('p0')).do_not_contact
