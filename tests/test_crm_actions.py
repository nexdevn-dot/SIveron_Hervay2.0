"""Contact notes/edits, suppression and held campaign drafts. No live mail."""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import harvey.dashboard as dashboard
from harvey.crm import set_contact_block, save_campaign_draft, ContactError
from harvey.gate import pre_send_check
from harvey.models import Prospect, Company
from harvey.state import StateManager


@pytest.fixture
def crm_client(tmp_path,monkeypatch):
    path=tmp_path/'crm.db'
    monkeypatch.setattr(dashboard,'DB_PATH',path)
    monkeypatch.setattr(dashboard,'ENV_FILE',tmp_path/'empty.env')
    monkeypatch.setattr(dashboard,'_read_env_file',lambda:{})
    monkeypatch.delenv('INSTANTLY_API_KEY',raising=False)
    sm=StateManager(str(path))
    async def seed():
        await sm.init_db()
        await sm.add_company(Company(id='firm',name='Firma',domain='firm.test'))
        for i in range(36):
            await sm.add_prospect(Prospect(id=f'p{i}',company_id='firm',first_name='Anna',last_name=f'Test{i}',title='Leiterin',company='Firma',email=f'anna{i}@firm.test',email_verified=True,email_status='verified'))
        await sm.add_feedback('contact','p0','Bisheriger Kommentar')
    asyncio.run(seed())
    with TestClient(dashboard.app) as client:
        yield client,sm


def test_notes_show_legacy_feedback_and_new_notes(crm_client):
    client,sm=crm_client
    assert client.get('/api/contacts/p0/notes').json()[0]['comment']=='Bisheriger Kommentar'
    assert client.post('/api/contacts/p0/notes',json={'comment':'Rückruf am Freitag'}).status_code==200
    notes=client.get('/api/contacts/p0/notes').json()
    assert len(notes)==2 and notes[0]['comment']=='Rückruf am Freitag'
    assert client.post('/api/contacts/p0/notes',json={'comment':' '}).status_code==422
    assert client.post('/api/contacts/missing/notes',json={'comment':'Test'}).status_code==422


def test_contacts_paginate_and_filter_blocks(crm_client):
    client,sm=crm_client
    first=client.get('/api/contacts/page').json()
    assert first['total']==36 and len(first['items'])==30
    assert len(client.get('/api/contacts/page?page=2').json()['items'])==6
    assert client.post('/api/contacts/p0/block',json={'blocked':True,'reason':'Kein Kontakt gewünscht'}).status_code==200
    assert client.get('/api/contacts/page?blocked=yes').json()['total']==1
    assert client.get('/api/contacts/page?blocked=no').json()['total']==35
    assert client.get('/api/contacts/page?q=anna0@firm.test').json()['items'][0]['suppressed']


def test_edits_reset_email_verification_cancel_queue_and_detect_conflicts(crm_client):
    client,sm=crm_client
    asyncio.run(sm.add_outbox_item(prospect_id='p0',to_email='anna0@firm.test',subject='Test',body='Hallo',send_at='2020-01-01',status='approved'))
    payload=dict(company_id='firm',contact_type='person',first_name='Anna',last_name='Korrigiert',title='Leiterin',email='new@firm.test',phone='',revision=0)
    result=client.patch('/api/contacts/p0',json=payload)
    assert result.status_code==200,result.text
    assert result.json()['cancelled']==1
    person=asyncio.run(sm.get_prospect('p0'))
    assert person.email=='new@firm.test' and not person.email_verified and person.email_status=='' and person.revision==1
    assert client.patch('/api/contacts/p0',json=payload).status_code==422
    payload.update(revision=1,email='anna1@firm.test')
    assert client.patch('/api/contacts/p0',json=payload).status_code==422


def test_block_cancels_all_kinds_and_persists_after_status_and_address_change(crm_client):
    client,sm=crm_client
    async def seed():
        for step,kind in enumerate(('sequence','reply'),1):
            await sm.add_outbox_item(prospect_id='p0',to_email='anna0@firm.test',subject='Test',body='Hallo',send_at='2020-01-01',status='approved',kind=kind,step=step)
    asyncio.run(seed())
    result=client.post('/api/contacts/p0/block',json={'blocked':True,'reason':'Manuelle Sperre'})
    assert result.json()['cancelled']==2
    asyncio.run(sm.update_prospect_status('p0','replied'))
    assert asyncio.run(sm.is_contact_suppressed('p0'))
    payload=dict(company_id='firm',contact_type='person',first_name='Anna',last_name='Test0',title='Leiterin',email='changed@firm.test',phone='',revision=1)
    assert client.patch('/api/contacts/p0',json=payload).status_code==200
    assert asyncio.run(sm.is_contact_suppressed('missing','anna0@firm.test'))
    assert asyncio.run(sm.is_contact_suppressed('missing','changed@firm.test'))
    assert asyncio.run(sm.add_outbox_item(prospect_id='p0',to_email='changed@firm.test',subject='Test',body='Hallo',send_at='2020-01-01',kind='reply')) is None
    assert client.post('/api/contacts/p0/block',json={'blocked':False,'reason':''}).status_code==200
    assert not asyncio.run(sm.is_contact_suppressed('p0'))
    assert not asyncio.run(sm.get_outbox(status='approved'))


def test_opt_out_cannot_be_removed_and_gate_blocks_replies(crm_client):
    client,sm=crm_client
    asyncio.run(set_contact_block(sm,'p0',True,'Abgemeldet',source='opt_out'))
    asyncio.run(sm.update_prospect_status('p0','replied'))
    assert client.post('/api/contacts/p0/block',json={'blocked':False,'reason':''}).status_code==422
    person=asyncio.run(sm.get_prospect('p0'))
    assert not pre_send_check(person.email,'Frage','Hallo',person,kind='reply')


def test_draft_saves_brief_steps_members_without_activation_or_outbox(crm_client):
    client,sm=crm_client
    payload={'name':'Entwurf','prospect_ids':['p0','p1'],'sequence':[{'subject':'Hallo {{first_name}}','body':'Text','delay_days':90}],'brief':{'offer':'Angebot','sender':'Bekannter Absender'}}
    result=client.post('/api/campaign-drafts',json=payload)
    assert result.status_code==200,result.text
    cid=result.json()['id']
    detail=client.get('/api/campaign-drafts/'+cid).json()
    assert detail['status']=='manual_draft' and detail['editable'] and detail['sequence'][0]['delay_days']==0
    assert detail['brief']['offer']=='Angebot' and len(detail['contacts'])==2
    assert not asyncio.run(sm.get_campaigns_by_status('draft')) and not asyncio.run(sm.get_outbox(status='pending_review'))
    payload.update(revision=detail['revision'],prospect_ids=['p1'])
    assert client.patch('/api/campaign-drafts/'+cid,json=payload).status_code==200
    assert client.patch('/api/campaign-drafts/'+cid,json=payload).status_code==422
    client.post('/api/contacts/p0/block',json={'blocked':True,'reason':'Sperre'})
    assert client.post('/api/campaign-drafts',json=dict(payload,prospect_ids=['p0'])).status_code==422
    assert client.post('/api/campaign-drafts',json=dict(payload,prospect_ids=['missing'])).status_code==422


def test_existing_staged_campaign_is_read_only(crm_client):
    client,sm=crm_client
    from harvey.models.campaign import Campaign
    asyncio.run(sm.add_campaign(Campaign(id='staged',name='Staged',status='active',prospect_ids=['p0'])))
    assert not client.get('/api/campaign-drafts/staged').json()['editable']
    assert client.patch('/api/campaign-drafts/staged',json={'name':'Edit','revision':0}).status_code==422


@pytest.mark.asyncio
async def test_native_sender_checks_database_after_fetch_and_gate(tmp_path,monkeypatch):
    from tests.test_outbox_native import FakeProvider, make_sender, seed_prospect
    import harvey.agents.sender as sender_module
    sm=StateManager(str(tmp_path/'sender.db'));await sm.init_db()
    pid=await seed_prospect(sm)
    await sm.add_outbox_item(prospect_id=pid,to_email='jane@acme.com',subject='Hallo',body='Kurze Frage.',send_at='2020-01-01',status='approved',kind='reply')
    original=sender_module.pre_send_check
    def gate(*args,**kwargs):
        # Simulate an already fetched prospect being stale by the send boundary.
        return original(*args,**kwargs)
    monkeypatch.setattr(sender_module,'pre_send_check',gate)
    check=AsyncMock(return_value=True);monkeypatch.setattr(sm,'is_contact_suppressed',check)
    provider=FakeProvider();sender=make_sender(sm,provider)
    await sender._drain_due()
    assert not provider.sent and (await sm.get_outbox(status='cancelled'))


@pytest.mark.asyncio
async def test_instantly_campaign_is_paused_before_deploy_and_drafts_never_send(tmp_path):
    from tests.test_outbox_native import FakeProvider,make_sender,seed_prospect
    from harvey.models.campaign import Campaign,EmailStep
    sm=StateManager(str(tmp_path/'remote.db'));await sm.init_db();pid=await seed_prospect(sm)
    c=Campaign(id='remote',name='Remote',status='draft',instantly_campaign_id='hosted',prospect_ids=[pid],sequence=[EmailStep(step=1,subject='Hallo',body='Frage')]);await sm.add_campaign(c)
    await set_contact_block(sm,pid,True,'Sperre')
    sender=make_sender(sm,FakeProvider());sender.instantly=AsyncMock();sender.instantly.pause_campaign.return_value={}
    await sender._deploy_campaign(c)
    sender.instantly.pause_campaign.assert_awaited_once_with('hosted')
    sender.instantly.add_leads.assert_not_awaited();sender.instantly.activate_campaign.assert_not_awaited()
    held=Campaign(id='held',status='manual_draft',name='Entwurf',prospect_ids=[pid],sequence=c.sequence);await sm.add_campaign(held)
    await sender._stage_campaign_native(held)
    assert not await sm.get_outbox(status='pending_review')


def test_live_contact_status_and_export_honor_suppression(crm_client):
    client,sm=crm_client
    client.post('/api/contacts/p0/block',json={'blocked':True,'reason':'Sperre'})
    rows=client.post('/api/contacts/status',json={'ids':['p0','p1']}).json()
    assert {r['id']:r['suppressed'] for r in rows}=={'p0':1,'p1':0}
    from harvey.export import collect_prospects
    assert 'p0' not in [r.get('id') for r in asyncio.run(collect_prospects(sm))]
    assert 'anna0@firm.test' not in [r['email'] for r in asyncio.run(collect_prospects(sm))]
    assert 'anna0@firm.test' in [r['email'] for r in asyncio.run(collect_prospects(sm,include_all=True))]


@pytest.mark.asyncio
async def test_legacy_opt_out_migrates_to_durable_address_suppression(tmp_path):
    import aiosqlite
    from harvey.state import MIGRATIONS
    path=tmp_path/'legacy.db'
    async with aiosqlite.connect(path) as db:
        suppression_version=next(i for i,sql in enumerate(MIGRATIONS) if 'CREATE TABLE contact_suppressions' in sql)
        for migration in MIGRATIONS[:suppression_version]:
            await db.executescript(migration)
        await db.execute(f'PRAGMA user_version={suppression_version}')
        await db.execute("INSERT INTO prospects(id,first_name,last_name,email,status) VALUES ('old','Old','Person','old@firm.test','opted_out')")
        await db.commit()
    sm=StateManager(str(path));await sm.init_db()
    assert (await sm.get_prospect('old')).do_not_contact
    assert await sm.is_contact_suppressed('any','old@firm.test')
    with pytest.raises(ContactError):
        await set_contact_block(sm,'old',False,'')


@pytest.mark.asyncio
async def test_remote_pause_failure_stays_pending_for_retry(tmp_path):
    from harvey.crm import flush_remote_pauses
    from harvey.models.campaign import Campaign
    sm=StateManager(str(tmp_path/'pause.db'));await sm.init_db()
    pid=await sm.add_prospect(Prospect(first_name='A',last_name='B',email='a@firm.test'))
    await sm.add_campaign(Campaign(id='c',status='active',instantly_campaign_id='remote',prospect_ids=[pid]))
    await set_contact_block(sm,pid,True,'Sperre')
    client=AsyncMock();client.pause_campaign.return_value=None
    assert await flush_remote_pauses(sm,client)==1
    client.pause_campaign.return_value={}
    assert await flush_remote_pauses(sm,client)==0
    assert (await sm.get_prospect(pid)).do_not_contact


def test_prepare_unverified_person_and_company_requires_explicit_outbox_approval(crm_client):
    client,sm=crm_client
    async def change():
        async with sm._connect() as db:
            await db.execute("UPDATE prospects SET email_verified=0,email_status='' WHERE id IN ('p0','p1')")
            await db.execute("UPDATE prospects SET contact_type='company',status='company_contact',first_name='',last_name='' WHERE id='p1'")
            await db.commit()
    asyncio.run(change())
    result=client.post('/api/campaign-drafts',json={'name':'Einfach','prospect_ids':['p0','p1'],'sequence':[{'subject':'Frage an {{   company  }}','body':'Guten Tag, eine kurze Frage.'}]}).json()
    cid=result['id']
    response=client.post(f'/api/campaign-drafts/{cid}/prepare',json={'revision':0,'outreach_acknowledgment':client.get(f'/api/campaign-drafts/{cid}').json()['outreach_history']['acknowledgment']})
    assert response.status_code==200,response.text
    assert response.json()['messages']==2
    assert len(asyncio.run(sm.get_outbox(status='pending_review')))==2
    assert not asyncio.run(sm.get_outbox(status='approved'))
    assert not asyncio.run(sm.get_prospect('p0')).email_verified
    assert client.post(f'/api/campaign-drafts/{cid}/prepare',json={'revision':0}).status_code==200
    assert len(asyncio.run(sm.get_outbox(status='pending_review')))==2
    assert not client.get('/api/campaign-drafts/'+cid).json()['editable']
    from tests.test_outbox_native import FakeProvider,make_sender
    provider=FakeProvider()
    async def drain():
        sender=make_sender(sm,provider)
        await sender._drain_due()
        assert not provider.sent
        await sm.approve_outbox()
        await sender._drain_due()
    asyncio.run(drain())
    assert len(provider.sent)==2
    assert all(m['subject']=='Frage an Firma' for m in provider.sent)


@pytest.mark.parametrize('problem',['blocked','missing_email','empty_body','unknown_variable','stale'])
def test_prepare_invalid_draft_is_atomic(crm_client,problem):
    client,sm=crm_client
    payload={'name':'Entwurf','prospect_ids':['p0','p1'],'sequence':[{'subject':'Frage','body':'Guten Tag.'}]}
    if problem=='empty_body': payload['sequence'][0]['body']=''
    if problem=='unknown_variable': payload['sequence'][0]['body']='Hallo {{unknown}}'
    cid=client.post('/api/campaign-drafts',json=payload).json()['id']
    if problem=='blocked': client.post('/api/contacts/p1/block',json={'blocked':True,'reason':'Sperre'})
    if problem=='missing_email':
        async def clear():
            async with sm._connect() as db:
                await db.execute("UPDATE prospects SET email='' WHERE id='p1'"); await db.commit()
        asyncio.run(clear())
    result=client.post(f'/api/campaign-drafts/{cid}/prepare',json={'revision':99 if problem=='stale' else 0})
    assert result.status_code==422,result.text
    assert not asyncio.run(sm.get_outbox())
    assert client.get('/api/campaign-drafts/'+cid).json()['status']=='manual_draft'


def test_optional_ai_suggestion_uses_brief_and_never_saves_or_sends(crm_client,monkeypatch):
    from harvey.brain import Brain
    client,sm=crm_client
    think=AsyncMock(return_value={'subject':'Kurze Frage','body':'Guten Tag, können wir einen Termin vereinbaren?'})
    monkeypatch.setattr(Brain,'think_json',think)
    response=client.post('/api/campaign-drafts/suggest-text',json={'brief':{'offer':'Schulungen','goal':'Termin'}})
    assert response.status_code==200,response.text
    assert response.json()['sequence'][0]['subject']=='Kurze Frage'
    assert 'Schulungen' in think.call_args.args[0]
    assert not asyncio.run(sm.get_outbox())
    assert not asyncio.run(sm.get_campaigns_by_status('manual_draft'))
    assert client.post('/api/campaign-drafts/suggest-text',json={'brief':{}}).status_code==422
    assert think.await_count==1
    think.return_value={'subject':'Frage','body':'Hallo {{invented}}'}
    assert client.post('/api/campaign-drafts/suggest-text',json={'brief':{'offer':'Schulungen','goal':'Termin'}}).status_code==422


def test_reversible_delete_cancels_queue_retains_history_and_excludes_exports(crm_client):
    from harvey.export import collect_prospects
    client,sm=crm_client
    asyncio.run(sm.add_outbox_item(prospect_id='p0',to_email='anna0@firm.test',subject='Test',body='Hallo',send_at='2020-01-01',status='approved'))
    result=client.post('/api/contacts/p0/trash',json={'revision':0})
    assert result.status_code==200,result.text
    assert result.json()['cancelled']==1
    assert client.get('/api/contacts/page').json()['total']==35
    trash=client.get('/api/contacts/page?deleted=yes').json()
    assert trash['total']==1 and trash['items'][0]['id']=='p0'
    assert client.post('/api/contacts/status',json={'ids':['p0']}).json()==[]
    assert asyncio.run(sm.is_contact_suppressed('p0'))
    assert all(p['email']!='anna0@firm.test' for p in asyncio.run(collect_prospects(sm,include_all=True)))
    assert len(client.get('/api/contacts/p0/notes').json())==2
    assert client.post('/api/contacts/p0/block',json={'blocked':False,'reason':''}).status_code==422
    assert client.post('/api/campaign-drafts',json={'name':'Test','prospect_ids':['p0'],'sequence':[]}).status_code==422
    assert client.post('/api/contacts/p0/trash',json={'revision':0,'restore':True}).status_code==422
    assert client.post('/api/contacts/p0/trash',json={'revision':1,'restore':True}).status_code==200
    assert client.get('/api/contacts/page').json()['total']==36
    assert not asyncio.run(sm.is_contact_suppressed('p0'))
    async def check():
        async with sm._connect() as db:
            assert (await (await db.execute("SELECT status FROM outbox WHERE prospect_id='p0'")).fetchone())[0]=='cancelled'
    asyncio.run(check())


def test_delete_restore_preserves_opt_out_and_manual_block(crm_client):
    client,sm=crm_client
    for source,pid in [('opt_out','p0'),('manual','p1')]:
        asyncio.run(set_contact_block(sm,pid,True,'Kein Kontakt',source=source))
        assert client.post(f'/api/contacts/{pid}/trash',json={'revision':1}).status_code==200
        assert client.post(f'/api/contacts/{pid}/trash',json={'revision':2,'restore':True}).status_code==200
        assert asyncio.run(sm.is_contact_suppressed(pid))
        if source=='opt_out':
            assert client.post(f'/api/contacts/{pid}/block',json={'blocked':False,'reason':''}).status_code==422


def test_delete_is_revision_checked_and_external_pause_is_persisted(crm_client):
    client,sm=crm_client
    async def seed():
        async with sm._connect() as db:
            await db.execute("INSERT INTO campaigns(id,name,status,prospect_ids_json,instantly_campaign_id) VALUES ('external','External','active','[\"p0\"]','remote')")
            await db.commit()
    asyncio.run(seed())
    assert client.post('/api/contacts/p0/trash',json={'revision':False}).status_code==422
    assert client.post('/api/contacts/p0/trash',json={'revision':0,'restore':'yes'}).status_code==422
    assert client.post('/api/contacts/missing/trash',json={'revision':0}).status_code==422
    result=client.post('/api/contacts/p0/trash',json={'revision':0})
    assert result.status_code==200 and result.json()['warning']
    assert client.post('/api/contacts/p0/trash',json={'revision':1}).status_code==422
    async def check():
        async with sm._connect() as db:
            assert (await (await db.execute("SELECT status FROM campaigns WHERE id='external'")).fetchone())[0]=='paused'
            assert (await (await db.execute('SELECT COUNT(*) FROM campaign_pause_requests')).fetchone())[0]==1
    asyncio.run(check())


def test_rich_campaign_upload_save_prepare_and_outbox_snapshot(crm_client):
    client,sm=crm_client
    uploaded=client.post('/api/campaign-attachments?filename=Angebot.pdf',content=b'%PDF-1.4\nexample',headers={'Content-Type':'application/octet-stream'})
    assert uploaded.status_code==200,uploaded.text
    aid=uploaded.json()['id']
    assert client.get('/api/campaign-attachments/'+aid).content==b'%PDF-1.4\nexample'
    doc={'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Hallo {{first_name}}','marks':[{'type':'bold'}]}]}]}
    saved=client.post('/api/campaign-drafts',json={'name':'Formatiert','prospect_ids':['p0'],'sequence':[{'subject':'Hallo','body':'IGNORED stale body','body_doc':doc,'attachment_ids':[aid]}]})
    assert saved.status_code==200,saved.text
    cid=saved.json()['id']
    detail=client.get('/api/campaign-drafts/'+cid).json()
    step=detail['sequence'][0]
    assert step['body']=='Hallo {{first_name}}' and step['body_doc']==doc
    assert step['attachments'][0]['filename']=='Angebot.pdf'
    response=client.post('/api/campaign-drafts/'+cid+'/prepare',json={'revision':detail['revision']})
    assert response.status_code==200,response.text
    item=asyncio.run(sm.get_outbox())[0]
    assert item['status']=='pending_review' and item['body']=='Hallo Anna'
    assert item['body_html']=='<p><strong>Hallo Anna</strong></p>'
    assert aid in item['attachment_ids_json'] and 'Angebot.pdf' in item['attachment_metadata_json']
    assert asyncio.run(sm.get_outbox(status='sent'))==[]


def test_attachment_limits_and_missing_files_do_not_prepare(crm_client):
    client,sm=crm_client
    assert client.post('/api/campaign-attachments?filename=script.exe',content=b'MZ').status_code==422
    assert client.post('/api/campaign-attachments?filename=empty.txt',content=b'').status_code==422
    assert client.post('/api/campaign-attachments?filename=large.txt',content=b'x'*(10*1024*1024+1)).status_code==413
    bad=client.post('/api/campaign-drafts',json={'name':'Bad','prospect_ids':['p0'],'sequence':[{'subject':'Test','body':'Text','attachment_ids':['a'*32]}]})
    assert bad.status_code==422
    assert asyncio.run(sm.get_outbox())==[]
