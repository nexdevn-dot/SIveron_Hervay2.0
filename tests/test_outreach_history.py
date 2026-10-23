"""Repeated outreach requires review; suppressions and sequence gates remain binding."""
import asyncio

from tests.test_crm_actions import crm_client
from tests.test_campaign_workflow import make_draft


def sql(sm, query, args=()):
    async def run():
        async with sm._connect() as db:
            await db.execute(query,args)
            await db.commit()
    asyncio.run(run())


def history(client, cid):
    return client.get('/api/campaign-drafts/'+cid).json()['outreach_history']


def prepare(client,cid,ack=None):
    revision=client.get('/api/campaign-drafts/'+cid).json()['revision']
    return client.post('/api/campaign-drafts/'+cid+'/prepare',json={'revision':revision,'outreach_acknowledgment':ack})


def test_other_person_at_established_company_requires_explicit_review(crm_client):
    client,sm=crm_client
    first=make_draft(client,'Existing draft','p0')
    second=make_draft(client,'Second','p1')
    report=history(client,second)
    finding=report['findings'][0]
    assert finding['reasons']==['same_company']
    assert finding['kind']=='membership' and finding['campaign_id']==first
    assert finding['campaign_status']=='manual_draft'
    assert prepare(client,second).json()['error']=='OUTREACH_REVIEW_REQUIRED'
    assert not asyncio.run(sm.get_outbox())
    assert prepare(client,second,report['acknowledgment']).status_code==200
    assert not asyncio.run(sm.get_outbox(status='sent'))


def test_address_snapshot_matches_after_original_contact_address_changed(crm_client):
    client,sm=crm_client
    sql(sm,"UPDATE prospects SET email=' Shared@Example.com ',company_id='',company='' WHERE id='p1'")
    sql(sm,"INSERT INTO outbox(id,campaign_id,prospect_id,to_email,status,sent_at) VALUES ('past','old','p0','shared@example.com','sent','2026-01-01 09:00:00')")
    cid=make_draft(client,'Exact','p1')
    finding=history(client,cid)['findings'][0]
    assert finding['reasons']==['same_email'] and finding['status']=='sent'
    assert finding['sent_at']=='2026-01-01 09:00:00'


def test_same_name_is_uncertain_and_shared_domain_does_not_prove_company(crm_client):
    client,sm=crm_client
    make_draft(client,'Other','p0')
    sql(sm,"UPDATE prospects SET company_id='' WHERE id='p1'")
    cid=make_draft(client,'Unknown identity','p1')
    assert history(client,cid)['findings'][0]['reasons']==['uncertain_company_name']
    sql(sm,"UPDATE prospects SET company='Different' WHERE id='p1'")
    assert history(client,cid)['findings']==[]  # same mail domain alone is not identity


def test_changed_evidence_invalidates_acknowledgment_atomically(crm_client):
    client,sm=crm_client
    first=make_draft(client,'Other','p0');cid=make_draft(client,'Review','p1')
    old=history(client,cid)['acknowledgment']
    sql(sm,"UPDATE campaigns SET status='paused' WHERE id=?",(first,))
    assert prepare(client,cid,old).json()['error']=='OUTREACH_REVIEW_REQUIRED'
    assert not asyncio.run(sm.get_outbox())
    assert prepare(client,cid,history(client,cid)['acknowledgment']).status_code==200


def test_acknowledgment_never_overrides_suppression(crm_client):
    client,sm=crm_client
    make_draft(client,'Other','p0');cid=make_draft(client,'Review','p1')
    ack=history(client,cid)['acknowledgment']
    sql(sm,"INSERT INTO contact_suppressions(email,prospect_id,reason,source) VALUES ('anna1@firm.test','p1','Opt out','opt_out')")
    result=prepare(client,cid,ack)
    assert result.status_code==422 and 'gesperrt' in result.json()['error']
    assert not asyncio.run(sm.get_outbox())


def test_same_sequence_followups_and_repeated_preparation_are_not_duplicates(crm_client):
    client,sm=crm_client
    response=client.post('/api/campaign-drafts',json={'name':'Sequence','prospect_ids':['p0'],
        'sequence':[{'subject':'First','body':'Hello.'},{'subject':'Follow up','body':'Hello again.','delay_days':3}]})
    cid=response.json()['id']
    assert history(client,cid)['findings']==[]
    assert prepare(client,cid).status_code==200
    assert history(client,cid)['findings']==[]
    assert prepare(client,cid).json()['already_prepared']
    assert len(asyncio.run(sm.get_outbox(status='pending_review')))==2


def test_selected_colleagues_and_duplicate_address_are_reviewable(crm_client):
    client,sm=crm_client
    sql(sm,"UPDATE prospects SET email='ANNA0@firm.test' WHERE id='p1'")
    cid=client.post('/api/campaign-drafts',json={'name':'Selection','prospect_ids':['p0','p1'],
        'sequence':[{'subject':'Question','body':'Hello.'}]}).json()['id']
    report=history(client,cid)
    assert len(report['findings'])==2
    assert all(x['kind']=='selection' and 'same_email' in x['reasons'] for x in report['findings'])
    assert prepare(client,cid).status_code==422
    assert prepare(client,cid,report['acknowledgment']).status_code==200
    assert len(asyncio.run(sm.get_outbox(status='pending_review')))==1  # existing exact-address dedup


def test_historical_cancelled_campaign_is_not_reported_as_sent(crm_client):
    client,sm=crm_client
    old=make_draft(client,'Historical','p0')
    sql(sm,"UPDATE campaigns SET status='completed' WHERE id=?",(old,))
    sql(sm,"INSERT INTO outbox(id,campaign_id,prospect_id,to_email,status) VALUES ('cancelled',?,'p0','anna0@firm.test','cancelled')",(old,))
    cid=make_draft(client,'New','p1')
    report=history(client,cid)
    assert {x['status'] for x in report['findings']}=={'completed','cancelled'}
    assert all(x['campaign_status']=='completed' for x in report['findings'])


def test_unassigned_legacy_message_and_contact_membership_survive_address_change(crm_client):
    client,sm=crm_client
    old=make_draft(client,'Old membership','p0')
    sql(sm,"UPDATE prospects SET email='new@firm.test' WHERE id='p0'")
    sql(sm,"INSERT INTO outbox(id,campaign_id,prospect_id,to_email,status) VALUES ('legacy',NULL,'p0','old@firm.test','failed')")
    cid=make_draft(client,'Again','p0')
    report=history(client,cid)
    assert any(x['campaign_id']==old and 'same_contact' in x['reasons'] for x in report['findings'])
    assert any(x['id']=='legacy' and x['status']=='failed' for x in report['findings'])
    assert prepare(client,cid).status_code==422
