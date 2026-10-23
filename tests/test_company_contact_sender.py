"""Firm inboxes are eligible only through the existing verification/approval gates."""
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from harvey.agents.sender import has_sendable_status
from harvey.models import Prospect
from harvey.models.campaign import Campaign, EmailStep
from harvey.state import StateManager
from tests.test_outbox_native import FakeProvider, make_sender


@pytest_asyncio.fixture
async def company_campaign(tmp_path):
    state=StateManager(str(tmp_path/'company-sender.db'))
    await state.init_db()
    pid=await state.add_prospect(Prospect(id='firm',contact_type='company',company='Test Firm',
        email='info@firm.test',email_status='verified',email_verified=True,status='company_contact'))
    campaign=Campaign(id='campaign',name='Firm campaign',status='draft',prospect_ids=[pid],
        sequence=[EmailStep(step=1,subject='Frage an {{company}}',body='Guten Tag, eine kurze Frage an Ihr Team.')])
    await state.add_campaign(campaign)
    return state,pid,campaign


@pytest.mark.parametrize('kind,status,expected',[
    ('company','company_contact',True),('person','company_contact',False),
    ('company','new',True),('company','queued',True),('company','contacted',False),
    ('company','replied',False),('company','opted_out',False),('company','lost',False),
    ('company','meeting',False),('company','closed',False),
])
def test_company_type_does_not_override_terminal_statuses(kind,status,expected):
    assert has_sendable_status(Prospect(contact_type=kind,status=status)) is expected


@pytest.mark.asyncio
async def test_verified_firm_is_staged_for_approval_without_a_person_name(company_campaign):
    state,pid,campaign=company_campaign
    provider=FakeProvider();sender=make_sender(state,provider,require_approval=True)
    await sender._run_native()
    pending=await state.get_outbox(status='pending_review')
    assert len(pending)==1 and pending[0]['to_email']=='info@firm.test'
    assert pending[0]['subject']=='Frage an Test Firm'
    assert not provider.sent
    firm=await state.get_prospect(pid)
    assert firm.status=='queued' and firm.contact_type=='company'
    assert not firm.first_name and not firm.last_name
    await sender._run_native()
    assert len(await state.get_outbox(status='pending_review'))==1
    assert not provider.sent


@pytest.mark.asyncio
@pytest.mark.parametrize('estatus',['','guess','invalid','risky'])
async def test_firm_inbox_keeps_existing_deliverability_filter(company_campaign,estatus):
    state,pid,campaign=company_campaign
    async with state._connect() as db:
        await db.execute('UPDATE prospects SET email_status=? WHERE id=?',(estatus,pid));await db.commit()
    provider=FakeProvider();sender=make_sender(state,provider,require_approval=True)
    await sender._stage_campaign_native(campaign)
    assert not await state.get_outbox(status='pending_review')
    assert not provider.sent


@pytest.mark.asyncio
async def test_blocked_firm_cannot_be_staged(company_campaign):
    from harvey.crm import set_contact_block
    state,pid,campaign=company_campaign
    await set_contact_block(state,pid,True,'No contact')
    provider=FakeProvider();sender=make_sender(state,provider)
    await sender._stage_campaign_native(campaign)
    assert not await state.get_outbox(status='pending_review')
    assert not provider.sent


@pytest.mark.asyncio
@pytest.mark.parametrize('guard',['manual_draft','disabled','paused','zero_cap'])
async def test_status_fix_does_not_bypass_operating_controls(company_campaign,monkeypatch,guard):
    state,pid,campaign=company_campaign
    provider=FakeProvider();sender=make_sender(state,provider,require_approval=True)
    if guard=='manual_draft':
        campaign.status='manual_draft';await state.update_campaign(campaign.id,status='manual_draft')
    if guard=='disabled':monkeypatch.setattr(sender.config.channels.email,'enabled',False)
    if guard=='paused':await state.set_setting('sending_paused','test pause')
    if guard=='zero_cap':monkeypatch.setattr(sender.config.channels.email,'max_daily_sends',0)
    await sender.run()
    assert not provider.sent and not await state.get_outbox(status='sent')
    if guard!='zero_cap':assert not await state.get_outbox(status='pending_review')


@pytest.mark.asyncio
async def test_firm_is_marked_contacted_after_mock_send(company_campaign):
    state,pid,campaign=company_campaign
    # A pre-existing approved row must also update a firm's lifecycle correctly.
    await state.add_outbox_item(prospect_id=pid,campaign_id=campaign.id,to_email='info@firm.test',
        subject='Frage',body='Guten Tag, eine kurze Frage.',send_at='2020-01-01',status='approved')
    provider=FakeProvider();sender=make_sender(state,provider)
    await sender._drain_due()
    assert len(provider.sent)==1
    firm=await state.get_prospect(pid)
    assert firm.status=='contacted' and firm.contact_type=='company'
    assert not firm.first_name and not firm.last_name


@pytest.mark.asyncio
async def test_instantly_path_includes_verified_firm(company_campaign):
    state,pid,campaign=company_campaign
    sender=make_sender(state,FakeProvider())
    sender.instantly=AsyncMock()
    sender.instantly.create_campaign.return_value={'id':'remote'}
    sender.instantly.set_campaign_emails.return_value={}
    sender.instantly.add_leads.return_value={}
    sender.instantly.activate_campaign.return_value={}
    await sender._deploy_campaign(campaign)
    sender.instantly.add_leads.assert_awaited_once()
    remote_id,leads=sender.instantly.add_leads.call_args.args
    assert remote_id=='remote' and len(leads)==1 and leads[0]['email']=='info@firm.test'
    assert leads[0]['first_name']=='' and leads[0]['last_name']==''
    assert (await state.get_prospect(pid)).status=='contacted'
