"""Reproduce audit findings using synthetic data and disposable databases.

Run with the project's .venv/bin/python from the checkout. No real mail,
model calls, credentials or discovery services are used. JSON records the
observed behavior; a zero exit status does not mean the application is safe.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from harvey.agents.handler import Handler
from harvey.agents.sender import Sender
from harvey.agents.writer import Writer
from harvey.agents.scout import Scout
from harvey.config import EnvConfig, HarveyConfig
from harvey.integrations.gmail import GmailProvider
from harvey.integrations.smtp_mail import SmtpImapProvider
from harvey.integrations.mail_provider import InboundMessage, SendResult
from harvey.main import decide_next_action
from harvey.models.campaign import Campaign, EmailStep
from harvey.models.prospect import Prospect
from harvey.state import StateManager
from harvey.trainer import Trainer
from harvey.config import BrainConfig
from harvey.models.company import Company
from harvey.collectors.profile import ProfileCollector
from harvey.signals import seed_signal_catalog


def cfg(provider='smtp'):
    return HarveyConfig(**{
        'persona': {'name': 'Audit', 'company': 'Fixture', 'role': 'BD', 'email': 'audit@example.invalid', 'linkedin': '', 'tone': 'direct'},
        'product': {'name': 'Fixture', 'description': 'Fixture', 'pricing': '', 'key_benefits': [], 'objection_responses': {}},
        'icp': {'industries': [], 'company_size': '', 'titles': [], 'geography': []},
        'channels': {'email': {'enabled': True, 'provider': provider, 'require_approval': True}, 'linkedin': {'enabled': False}},
    })


class Brain:
    paused_reason = ''
    def load_skills_for_agent(self, *args): return ''
    def load_prompt(self, *args, **kwargs): return ''
    async def think(self, *args, **kwargs): return 'question' if kwargs.get('task') == 'classify_intent' else 'Please share more details.'


class Mail:
    name = 'audit'
    def __init__(self, state=None, pause=False, barrier=False):
        self.sent = []
        self.state, self.pause, self.barrier = state, pause, barrier
        self.event = asyncio.Event()
    def is_configured(self): return True
    async def get_replies(self, limit=50): return []
    async def send_email(self, to_email, subject, body, **kwargs):
        self.sent.append(to_email)
        if self.pause and len(self.sent) == 1:
            await self.state.set_setting('sending_paused', 'audit mid-batch pause')
        if self.barrier:
            if len(self.sent) >= 2: self.event.set()
            await asyncio.wait_for(self.event.wait(), 3)
        return SendResult(ok=True, message_id=f'<audit-{len(self.sent)}@example.invalid>')


def sender(state, mail, config=None):
    s = Sender(Brain(), state, config or cfg(), EnvConfig())
    s.provider, s.send_pacing = mail, False
    return s


async def prospect(state, name='One', verified=True):
    return await state.add_prospect(Prospect(first_name=name, last_name='Fixture', title='Owner', email=f'{name.lower()}@example.invalid', email_status='verified' if verified else 'guess'))


async def queued(state, pid):
    p = await state.get_prospect(pid)
    return await state.add_outbox_item(prospect_id=pid, to_email=p.email, subject='Question', body='Please share more details.', send_at='2000-01-01T00:00:00', status='approved')


async def main(root):
    result = {}
    async def db(name):
        s = StateManager(str(root / f'{name}.db'))
        await s.init_db()
        return s

    state = await db('mailerrors')
    gmail = GmailProvider(cfg('gmail'), EnvConfig())
    gmail.is_configured = lambda: True
    gmail._request = AsyncMock(return_value=None)
    h = Handler(Brain(), state, cfg('gmail'), EnvConfig())
    h.provider = gmail
    result['gmail_failed_fetch_reported_complete'] = await h.run()

    smtp = SmtpImapProvider(cfg(), EnvConfig())
    smtp.is_configured = lambda: True
    smtp._fetch_unseen = lambda limit: (_ for _ in ()).throw(OSError('simulated IMAP outage'))
    h.provider = smtp
    result['smtp_failed_fetch_reported_complete'] = await h.run()

    state = await db('pause')
    for name in ['One', 'Two']: await queued(state, await prospect(state, name))
    mail = Mail(state, pause=True)
    await sender(state, mail).run()
    result['emails_sent_despite_pause_after_first'] = len(mail.sent)

    state = await db('concurrent')
    await queued(state, await prospect(state))
    mail = Mail(barrier=True)
    await asyncio.gather(sender(state, mail)._drain_due(), sender(state, mail)._drain_due())
    result['concurrent_sends_of_single_outbox_row'] = len(mail.sent)

    state = await db('legacy')
    pid = await prospect(state)
    await state.add_campaign(Campaign(id='', name='Audit legacy', prospect_ids=[pid], sequence=[EmailStep(step=1, subject='Act now', body='Buy now {{unrendered}}')]))
    await state.set_setting('sending_paused', 'audit pause')
    s = sender(state, None, cfg('instantly'))
    fake = SimpleNamespace(**{name: AsyncMock(return_value={'id': 'fake-campaign'}) for name in ['create_campaign', 'set_campaign_emails', 'add_leads', 'activate_campaign']})
    s.instantly = fake
    await s.run()
    result['legacy_activated_despite_pause_approval_and_bad_content'] = fake.activate_campaign.await_count
    result['legacy_outbox_rows'] = len(await state.get_outbox())

    state = await db('decision')
    await prospect(state, verified=False)
    before = await decide_next_action(Brain(), state, cfg())
    await Writer(Brain(), state, cfg()).run()
    after = await decide_next_action(Brain(), state, cfg())
    result['unverified_new_prospect_actions_before_after_writer'] = [before, after]
    result['draft_campaigns_after_writer'] = (await state.get_state_summary())['draft_campaigns']

    state = await db('processing')
    mail = Mail()
    async def inbound(limit=50):
        return [InboundMessage(provider_id='audit-reply', from_email='one@example.invalid', body='Fixture')]
    mail.get_replies = inbound
    h = Handler(Brain(), state, cfg(), EnvConfig())
    h.provider = mail
    h._process_reply = AsyncMock(side_effect=RuntimeError('simulated state write failure'))
    result['handler_success_on_processing_failure'] = await h.run()
    result['failed_message_marked_processed'] = await state.is_reply_processed('audit-reply')

    state = await db('attribution')
    pid = await prospect(state)
    campaign_id = await state.add_campaign(Campaign(id='', name='Audit native', prospect_ids=[pid], status='active', sequence=[EmailStep(step=1, subject='Question', body='Fixture')]))
    sent_id = await state.add_outbox_item(prospect_id=pid, campaign_id=campaign_id, to_email='one@example.invalid', subject='Question', body='Fixture', send_at='2000-01-01T00:00:00', status='sent')
    await state.update_outbox_item(sent_id, message_id='<original-fixture>', sent_at='2000-01-01T00:00:00')
    h = Handler(Brain(), state, cfg(), EnvConfig())
    mail = Mail()
    async def campaign_reply(limit=50):
        return [InboundMessage(provider_id='campaign-reply', from_email='one@example.invalid', subject='Re: Question', body='Please share details', message_id='<fixture>', in_reply_to='<original-fixture>')]
    mail.get_replies = campaign_reply
    h.provider = mail
    await h.run()
    convos = await state.get_conversations_by_status('open')
    result['native_reply_campaign_id'] = convos[0].campaign_id
    result['native_campaign_reported_reply_count'] = (await state.get_campaign_stats())[0]['reply_count']

    trainer = Trainer.__new__(Trainer)
    trainer.brain_config = BrainConfig(provider='codex', model='gpt-6-luna', codex_restricted_text=True)
    built = trainer._build_config({'company_name': 'Fixture', 'product_name': 'Fixture'}, {}, {}, 'fixture.example.invalid')
    result['trainer_generated_email_settings'] = built['channels']['email']
    result['trainer_generated_linkedin_enabled'] = built['channels']['linkedin']['enabled']

    state = await db('signals')
    await seed_signal_catalog(state)
    cid = await state.add_company(Company(name='Fixture', domain='fixture.example.invalid'))
    scout = Scout(Brain(), state, cfg(), EnvConfig())
    scout._scrape_hiring_signals = AsyncMock(return_value=['Fixture Director'])
    await scout._enrich_company_signals(cid, 'fixture.example.invalid', homepage_html='<html><meta name="generator" content="WordPress 6.0"></html>')
    comp = await state.get_company(cid)
    result['confirmed_signals_during_scout_enrichment'] = len(await state.confirmed_signal_codes())
    result['scout_unconfirmed_tech_entries'] = len(comp.tech_stack)
    result['scout_unconfirmed_hiring_entries'] = len(comp.signals)

    await state.set_signal_status('INCUMBENT_AGENCY', 'confirmed')
    await state.add_observation('INCUMBENT_AGENCY', company_id=cid, collector='profile', value_text='Old fixture agency', observed_at='2020-01-01T00:00:00')
    collector = ProfileCollector(state, confirmed={'INCUMBENT_AGENCY'})
    collector._resolve_site = AsyncMock(return_value=('https://fixture.example.invalid', '<html><body>Simple site without agency credit</body></html>'))
    rows = await collector.profile_company(cid, 'fixture.example.invalid')
    if rows: await state.add_observations(rows)
    result['old_agency_remains_in_cohort_after_new_negative_scan'] = cid in await state.cohort(['INCUMBENT_AGENCY'])

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='harvey-audit-') as tmp:
        asyncio.run(main(Path(tmp)))
