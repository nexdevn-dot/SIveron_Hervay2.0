"""Sequence dependencies, tested only against a temporary DB and fake mail provider."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.test_outbox_native import (state, seed_prospect, seed_campaign,
                                     make_sender, FakeProvider, Cfg)
from tests.test_crm_actions import crm_client


def utc(days=0):
    return (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)).isoformat()


async def staged(state):
    pid = await seed_prospect(state)
    campaign = await seed_campaign(state, [pid])
    sender = make_sender(state, FakeProvider())
    await sender._stage_campaign_native(campaign)
    # Reproduce approving an old, already fully due sequence, not fresh timestamps.
    async with state._connect() as db:
        await db.execute("UPDATE outbox SET send_at=CASE step WHEN 1 THEN ? ELSE ? END",
                         (utc(-8), utc(-5)))
        await db.commit()
    return sender, pid, campaign


@pytest.mark.asyncio
async def test_late_approval_does_not_send_followup_in_same_batch(state):
    sender, _, _ = await staged(state)
    await state.approve_outbox()
    await sender._drain_due()
    assert len(sender.provider.sent) == 1
    assert len(await state.get_outbox(status='approved')) == 1
    first = (await state.get_outbox(status='sent'))[0]
    follow = (await state.get_outbox(status='approved'))[0]
    assert datetime.fromisoformat(follow['send_at']) >= datetime.fromisoformat(first['sent_at']) + timedelta(days=3)


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['pending_review', 'approved', 'rejected', 'failed', 'cancelled'])
async def test_followup_waits_for_successful_predecessor(state, status):
    sender, _, _ = await staged(state)
    rows = await state.get_outbox()
    first = next(r for r in rows if r['step'] == 1)
    follow = next(r for r in rows if r['step'] == 2)
    await state.update_outbox_item(first['id'], status=status, send_at=utc(1))
    await state.update_outbox_item(follow['id'], status='approved')
    await sender._drain_due()
    assert sender.provider.sent == []
    assert (await state.get_outbox_item(follow['id']))['status'] == 'approved'


@pytest.mark.asyncio
@pytest.mark.parametrize('sent_days, expected', [(-1, 0), (-4, 1)])
async def test_delay_is_measured_from_actual_success(state, sent_days, expected):
    sender, _, _ = await staged(state)
    rows = await state.get_outbox()
    first = next(r for r in rows if r['step'] == 1)
    follow = next(r for r in rows if r['step'] == 2)
    await state.update_outbox_item(first['id'], status='sent', sent_at=utc(sent_days))
    await state.update_outbox_item(follow['id'], status='approved', send_at=utc(-5))
    await sender._drain_due()
    assert len(sender.provider.sent) == expected


@pytest.mark.asyncio
async def test_daily_cap_deferral_does_not_shorten_followup_delay(state, monkeypatch):
    monkeypatch.setattr(Cfg.channels.email, 'max_daily_sends', 1)
    sender, _, _ = await staged(state)
    await state.approve_outbox()
    await sender._drain_due()
    assert len(sender.provider.sent) == 1
    await sender._drain_due()  # exhausted for today
    assert len(sender.provider.sent) == 1
    first = (await state.get_outbox(status='sent'))[0]
    follow = (await state.get_outbox(status='approved'))[0]
    # A new daily allowance is not itself permission to skip the three-day wait.
    await state.update_outbox_item(first['id'], sent_at=utc(-1))
    await state.update_outbox_item(follow['id'], send_at=utc(-5))
    await sender._drain_due()
    assert len(sender.provider.sent) == 1
    await state.update_outbox_item(first['id'], sent_at=utc(-4))
    await sender._drain_due()
    assert len(sender.provider.sent) == 2


@pytest.mark.asyncio
async def test_blocked_followups_do_not_starve_other_contacts(state, monkeypatch):
    monkeypatch.setattr(Cfg.channels.email, 'max_daily_sends', 1)
    sender = make_sender(state, FakeProvider())
    pid = await seed_prospect(state)
    for index in range(6):
        await state.add_outbox_item(prospect_id=pid, campaign_id=f'missing-{index}', step=2,
                                   to_email='jane@acme.com', subject='Follow', body='Waiting.',
                                   send_at=utc(-10), status='approved')
    await state.add_outbox_item(prospect_id=pid, campaign_id='first', step=1,
                               to_email='jane@acme.com', subject='First', body='Ready.',
                               send_at=utc(-1), status='approved')
    await sender._drain_due()
    assert [r['subject'] for r in sender.provider.sent] == ['First']


@pytest.mark.asyncio
async def test_zero_delay_still_requires_success_not_approval(state):
    pid = await seed_prospect(state)
    sender = make_sender(state, FakeProvider())
    first = await state.add_outbox_item(prospect_id=pid, campaign_id='zero', step=1,
        to_email='jane@acme.com', subject='First', body='First.', send_at=utc(-1), status='pending_review')
    await state.add_outbox_item(prospect_id=pid, campaign_id='zero', step=2,
        to_email='jane@acme.com', subject='Second', body='Second.', send_at=utc(-1), status='approved', delay_days=0)
    await sender._drain_due()
    assert not sender.provider.sent
    await state.approve_outbox(first)
    await sender._drain_due()
    assert [r['subject'] for r in sender.provider.sent] == ['First']
    await sender._drain_due()
    assert [r['subject'] for r in sender.provider.sent] == ['First', 'Second']


@pytest.mark.asyncio
async def test_reply_is_not_a_sequence_followup(state):
    pid = await seed_prospect(state)
    sender = make_sender(state, FakeProvider())
    await state.add_outbox_item(prospect_id=pid, kind='reply', step=2,
        to_email='jane@acme.com', subject='Reply', body='Answer.', send_at=utc(-1), status='approved')
    await sender._drain_due()
    assert len(sender.provider.sent) == 1


@pytest.mark.asyncio
async def test_missing_success_timestamp_and_other_campaign_do_not_unlock(state):
    pid = await seed_prospect(state)
    sender = make_sender(state, FakeProvider())
    await state.add_outbox_item(prospect_id=pid, campaign_id='wrong', step=1,
        to_email='jane@acme.com', subject='Wrong', body='Wrong.', send_at=utc(-8), status='sent')
    first = await state.add_outbox_item(prospect_id=pid, campaign_id='right', step=1,
        to_email='jane@acme.com', subject='First', body='First.', send_at=utc(-8), status='sent')
    await state.add_outbox_item(prospect_id=pid, campaign_id='right', step=2,
        to_email='jane@acme.com', subject='Second', body='Second.', send_at=utc(-5), status='approved', delay_days=3)
    await sender._drain_due()
    assert not sender.provider.sent
    await state.update_outbox_item(first, sent_at=utc(-4))
    await sender._drain_due()
    assert len(sender.provider.sent) == 1


@pytest.mark.asyncio
async def test_legacy_queue_migration_preserves_approval_and_holds_unknown_spacing(tmp_path):
    import sqlite3
    from harvey.state import MIGRATIONS, StateManager
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        sequence_index=next(i for i,migration in enumerate(MIGRATIONS) if 'ALTER TABLE outbox ADD COLUMN delay_days' in migration)
        for migration in MIGRATIONS[:sequence_index]:
            db.executescript(migration)
        db.execute(f'PRAGMA user_version={sequence_index}')
        for id, campaign, step, at, status in [
            ('a','old',1,'2026-01-01T00:00:00','sent'),
            ('b','old',2,'2026-01-04T00:00:00','approved'),
            ('c','missing',2,'2026-01-04T00:00:00','approved'),
            ('d','invalid',1,'bad date','sent'),
            ('e','invalid',2,'2026-01-04T00:00:00','approved'),
            ('f','fractional',1,'2026-01-01T00:00:00','sent'),
            ('g','fractional',2,'2026-01-01T12:00:00','pending_review')]:
            db.execute('INSERT INTO outbox(id,campaign_id,prospect_id,step,send_at,status) VALUES (?,?,?,?,?,?)',
                       (id,campaign,'p',step,at,status))
        db.execute("UPDATE outbox SET sent_at='2026-01-01T00:00:00' WHERE id='a'")
    sm = StateManager(str(path))
    await sm.init_db()
    await sm.init_db()  # restart is idempotent
    rows = {r['id']: r for r in await sm.get_outbox()}
    assert rows['a']['delay_days'] == 0 and rows['b']['delay_days'] == 3
    assert all(rows[id]['delay_days'] is None for id in ['c','e','g'])
    assert rows['b']['status'] == 'approved' and rows['g']['status'] == 'pending_review'
    assert rows['b']['send_at'] == '2026-01-04T00:00:00'
    ready = await sm.get_outbox(status='approved', due_before='2026-02-01', sequence_ready=True)
    assert [r['id'] for r in ready] == ['b']


def test_manual_preparation_snapshots_spacing(crm_client):
    import asyncio
    client, sm = crm_client
    result = client.post('/api/campaign-drafts', json={'name':'Spacing', 'prospect_ids':['p0'],
        'sequence':[{'subject':'First','body':'Hello.','delay_days':0},
                    {'subject':'Second','body':'Following up.','delay_days':3}]}).json()
    assert client.post('/api/campaign-drafts/'+result['id']+'/prepare',json={'revision':0}).status_code == 200
    rows = asyncio.run(sm.get_outbox())
    assert {r['step']:r['delay_days'] for r in rows} == {1:0,2:3}
    assert all(r['status']=='pending_review' for r in rows)



@pytest.mark.asyncio
async def test_provider_failure_cannot_release_followup(state):
    sender, _, _ = await staged(state)
    sender.provider.fail_next = True
    await state.approve_outbox()
    await sender._drain_due()
    assert not sender.provider.sent
    assert len(await state.get_outbox(status='failed')) == 1
    await sender._drain_due()
    assert not sender.provider.sent
    assert len(await state.get_outbox(status='approved')) == 1


@pytest.mark.asyncio
async def test_restart_preserves_snapshot_and_future_explicit_schedule(state):
    from harvey.state import StateManager
    sender, _, campaign = await staged(state)
    rows = await state.get_outbox()
    first = next(r for r in rows if r['step'] == 1)
    follow = next(r for r in rows if r['step'] == 2)
    # Changing campaign data after staging must not change the queued contract.
    async with state._connect() as db:
        await db.execute("UPDATE campaigns SET sequence_json='[]' WHERE id=?", (campaign.id,))
        await db.commit()
    later = utc(10)
    await state.update_outbox_item(follow['id'], send_at=later)
    await state.update_outbox_item(first['id'], status='sent', sent_at=utc())
    restarted = StateManager(state.db_path)
    await restarted.init_db()
    row = await restarted.get_outbox_item(follow['id'])
    assert row['delay_days'] == 3 and row['send_at'] == later
