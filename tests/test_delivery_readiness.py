"""Shared readiness, with isolated DB, fake transport and no credential/model calls."""
import asyncio
import json
import os
from datetime import timedelta
from types import SimpleNamespace

import pytest

from tests.test_outbox_native import state, seed_prospect, make_sender, FakeProvider, Cfg
from tests.test_crm_actions import crm_client
from harvey.delivery_readiness import (global_context, assess_message, utcnow,
                                      runtime_codes, record_runtime, config_signature)


async def item(state, **changes):
    pid = await seed_prospect(state)
    values = dict(prospect_id=pid,to_email='jane@acme.com',subject='Question',body='Hello.',
                  send_at=utcnow().isoformat(),status='approved',campaign_id='ready',step=1)
    values.update(changes)
    iid = await state.add_outbox_item(**values)
    return await state.get_outbox_item(iid)


def codes(value):
    return {r['code'] for r in value['reasons']}


@pytest.mark.asyncio
async def test_ready_and_multiple_blockers_are_read_only(state, monkeypatch):
    row = await item(state, status='pending_review')
    await state.set_setting('sending_paused','private reason')
    monkeypatch.setattr(Cfg.channels.email,'max_daily_sends',0)
    context = await global_context(state,Cfg(),FakeProvider())
    result = await assess_message(state,row,Cfg(),context,runtime=['agent_stopped'])
    assert {'approval','paused','cap','agent_stopped'} <= codes(result)
    assert result['state']=='blocked' and result['remaining_today']==0
    assert 'private reason' not in json.dumps(result)
    assert (await state.get_outbox_item(row['id']))['status']=='pending_review'
    assert all(r['de'] and r['en'] and r['next_de'] and r['next_en'] for r in result['reasons'])


@pytest.mark.asyncio
async def test_sender_and_assessment_share_content_blocker(state):
    row = await item(state,body='Hello {{unknown}}.')
    provider = FakeProvider()
    sender = make_sender(state,provider)
    value = await assess_message(state,row,Cfg(),await global_context(state,Cfg(),provider))
    assert {'content','placeholders'} <= codes(value)
    await sender._drain_due()
    assert not provider.sent
    assert 'placeholders' in (await state.get_outbox_item(row['id']))['error']


@pytest.mark.asyncio
async def test_sequence_matches_shared_sql_and_explains_unknown(state):
    row = await item(state,step=2,delay_days=3)
    context = await global_context(state,Cfg(),FakeProvider())
    value = await assess_message(state,row,Cfg(),context)
    assert 'spacing_unknown' in codes(value)
    assert not await state.get_outbox(status='approved',due_before=utcnow().isoformat(),sequence_ready=True)
    prior = await state.add_outbox_item(prospect_id=row['prospect_id'],to_email=row['to_email'],
        subject='First',body='Hello.',send_at=(utcnow()-timedelta(days=5)).isoformat(),
        status='sent',campaign_id='ready',step=1)
    await state.update_outbox_item(prior,sent_at=(utcnow()-timedelta(days=1)).isoformat())
    row = await state.get_outbox_item(row['id'])
    assert 'spacing' in codes(await assess_message(state,row,Cfg(),context))
    await state.update_outbox_item(prior,sent_at=(utcnow()-timedelta(days=4)).isoformat())
    # Preserve a later explicit minimum; clear it only in this fixture to simulate elapsed time.
    await state.update_outbox_item(row['id'],send_at=(utcnow()-timedelta(days=1)).isoformat())
    row = await state.get_outbox_item(row['id'])
    assert (await assess_message(state,row,Cfg(),context))['state']=='ready'
    assert (await state.get_outbox(status='approved',due_before=utcnow().isoformat(),sequence_ready=True))[0]['id']==row['id']


@pytest.mark.asyncio
async def test_actual_daily_count_and_configured_provider(state, monkeypatch):
    row = await item(state)
    monkeypatch.setattr(Cfg.channels.email,'max_daily_sends',1)
    await state.update_outbox_item(row['id'],status='sent',sent_at=utcnow().isoformat())
    context = await global_context(state,Cfg(),FakeProvider())
    assert context['remaining']==0 and 'cap' in context['codes']
    provider=FakeProvider();provider.is_configured=lambda:False
    assert 'provider' in (await global_context(state,Cfg(),provider))['codes']


@pytest.mark.asyncio
async def test_runtime_unknown_stale_changed_config_and_approved_only(state):
    now=utcnow();pid=os.getpid()
    assert runtime_codes('',pid,now,60)==['runtime_unknown']
    assert runtime_codes('',None,now,60)==['agent_stopped']
    await record_runtime(state,model_ok=True,reply_safe=True,approved_only=True,config=Cfg())
    raw=await state.get_setting('delivery_runtime')
    assert not runtime_codes(raw,pid,utcnow(),60,config_signature(Cfg()))
    assert runtime_codes(raw,pid,now+timedelta(hours=1),60)==['runtime_unknown']
    assert runtime_codes(raw,pid+1,utcnow(),60)==['runtime_unknown']
    assert runtime_codes(raw,pid,utcnow(),60,'different')==['runtime_config']
    await record_runtime(state,model_ok=False,reply_safe=False,config=Cfg())
    assert set(runtime_codes(await state.get_setting('delivery_runtime'),pid,utcnow(),60))=={'model','mailbox'}


@pytest.mark.asyncio
async def test_missing_attachment_and_terminal_states(state):
    row=await item(state)
    async with state._connect() as db:
        await db.execute('UPDATE outbox SET attachment_ids_json=? WHERE id=?',(json.dumps(['a'*32]),row['id']))
        await db.commit()
    row=await state.get_outbox_item(row['id'])
    context=await global_context(state,Cfg(),FakeProvider())
    assert 'attachments' in codes(await assess_message(state,row,Cfg(),context))
    for status,expected in [('sent','sent'),('failed','failed'),('rejected','blocked'),('cancelled','blocked')]:
        assert (await assess_message(state,dict(row,status=status),Cfg(),context))['state']==expected


def test_api_never_connects_or_sends_and_exposes_readiness(crm_client,monkeypatch):
    import harvey.config as config
    import harvey.dashboard as dashboard
    import harvey.integrations.mail_provider as mail
    client,sm=crm_client
    provider=FakeProvider()
    monkeypatch.setattr(config,'load_config',lambda *a:SimpleNamespace(channels=Cfg.channels,usage=SimpleNamespace(heartbeat_interval_minutes=15)))
    monkeypatch.setattr(config,'load_env',lambda:None)
    monkeypatch.setattr(mail,'get_mail_provider',lambda *a:provider)
    monkeypatch.setattr(dashboard,'_check_harvey_pid',lambda:None)
    iid=asyncio.run(sm.add_outbox_item(prospect_id='p0',to_email='anna0@firm.test',subject='Hello',body='Hello.',send_at='2020-01-01',status='approved'))
    result=client.get('/api/outbox')
    assert result.status_code==200
    row=next(r for r in result.json()['approved'] if r['id']==iid)
    assert 'agent_stopped' in codes(row['readiness'])
    assert provider.sent==[]
    assert asyncio.run(sm.get_outbox_item(iid))['status']=='approved'
    assert result.json()['readiness_checked_at'].endswith('Z')


@pytest.mark.asyncio
async def test_quiet_hours_and_suppression_block_sender_and_display(state, monkeypatch):
    import harvey.main as main
    config=SimpleNamespace(channels=Cfg.channels,usage=SimpleNamespace(quiet_hours=object()))
    monkeypatch.setattr(main,'in_quiet_hours',lambda cfg:True)
    row=await item(state)
    provider=FakeProvider()
    context=await global_context(state,config,provider)
    assert 'quiet' in codes(await assess_message(state,row,config,context))
    sender=make_sender(state,provider);sender.config=config
    await sender._drain_due()
    assert provider.sent==[]
    await state.update_prospect_status(row['prospect_id'],'opted_out')
    value=await assess_message(state,row,config,await global_context(state,config,provider))
    assert {'suppressed','stop'} <= codes(value)


def test_api_config_failure_never_claims_ready(crm_client,monkeypatch):
    import harvey.config as config
    client,sm=crm_client
    monkeypatch.setattr(config,'load_config',lambda *a:(_ for _ in ()).throw(ValueError('private configuration text')))
    asyncio.run(sm.add_outbox_item(prospect_id='p0',to_email='anna0@firm.test',subject='Hello',body='Hello.',send_at='2020-01-01',status='approved'))
    data=client.get('/api/outbox').json()
    assert data['approved'][0]['readiness']['state']=='unknown'
    assert 'config' in codes(data['approved'][0]['readiness'])
    assert 'private configuration text' not in json.dumps(data)
