"""Read-only inbox retrieval and receipt capture independent of AI quota."""
import asyncio
from unittest.mock import MagicMock

import pytest

from harvey.agents.handler import Handler
from harvey.config import EnvConfig, load_config
from harvey.integrations.mail_provider import InboundMessage
from harvey.integrations.smtp_mail import SmtpImapProvider
from harvey.models.prospect import Prospect
from harvey.state import StateManager


def test_imap_reads_already_seen_messages_without_changing_flags(monkeypatch):
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    raw = (b"From: person@example.test\r\nMessage-ID: <reply@example.test>\r\n"
           b"Subject: Re: Hello\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nA reply")
    conn.uid.side_effect = [
        ("OK", [b"1 2"]),
        ("OK", [(b"2 (UID 2 BODY[] {120}", raw), b")"]),
    ]
    monkeypatch.setattr("harvey.integrations.smtp_mail.imaplib.IMAP4_SSL", lambda *a, **k: conn)
    provider = SmtpImapProvider(load_config(), EnvConfig())
    messages = provider._fetch_recent(1)
    conn.select.assert_called_once_with("INBOX", readonly=True)
    assert conn.uid.call_args_list[0].args == ("search", None, "ALL")
    assert conn.uid.call_args_list[1].args == ("fetch", b"2", "(BODY.PEEK[])")
    conn.store.assert_not_called()
    conn.logout.assert_called_once()
    assert len(messages) == 1 and messages[0].body == "A reply"


@pytest.mark.asyncio
async def test_imap_failure_is_not_reported_as_an_empty_inbox(monkeypatch):
    provider = SmtpImapProvider(load_config(), EnvConfig())
    def failed(_limit):
        raise RuntimeError("server error with private details")
    monkeypatch.setattr(provider, "_fetch_recent", failed)
    with pytest.raises(RuntimeError, match="IMAP mailbox could not be read") as error:
        await provider.get_replies()
    assert "private" not in str(error.value)


@pytest.mark.asyncio
async def test_concurrent_receipt_capture_is_idempotent(tmp_path):
    state = StateManager(str(tmp_path / "inbox.db"))
    await state.init_db()
    contact = await state.add_prospect(Prospect(id="", email="person@example.test"))
    ids = await asyncio.gather(*[
        state.record_inbound_reply(contact, "<reply@x>", "Message") for _ in range(2)
    ])
    assert ids[0] == ids[1]
    convo = await state.get_conversation(ids[0])
    assert len(convo.thread) == 1
    assert convo.thread[0].provider_id == "<reply@x>"
    assert not await state.is_reply_processed("<reply@x>")


@pytest.mark.asyncio
async def test_budget_safety_captures_reply_without_ai_and_normal_processing_does_not_duplicate(tmp_path):
    state = StateManager(str(tmp_path / "inbox.db"))
    await state.init_db()
    contact = await state.add_prospect(Prospect(id="", email="person@example.test"))
    config = load_config()
    config.channels.email.provider = "smtp"
    config.channels.email.enabled = True
    config.channels.email.require_approval = True
    msg = InboundMessage(provider_id="<reply@x>", from_email="person@example.test",
                         body="Could you share details?", date="Sun, 18 Oct 2026 11:21:52 +0200")
    class Provider:
        def is_configured(self): return True
        async def get_replies(self): return [msg]
        async def send_email(self, *args, **kwargs): raise AssertionError("must not send")
    handler = Handler(brain=None, state=state, config=config, env=EnvConfig())
    handler.provider = Provider()
    assert await handler.check_reply_safety() is True
    assert await handler.check_reply_safety() is True
    conversations = await state.get_conversations_by_status("open")
    assert len(conversations) == 1 and len(conversations[0].thread) == 1
    assert conversations[0].thread[0].timestamp.isoformat() == "2026-10-18T09:21:52"
    assert not await state.is_reply_processed("<reply@x>")
    async def classify(*args): return "question"
    async def generate(*args): return ""
    handler._classify_intent = classify
    handler._generate_response = generate
    assert await handler._run_native() is True
    convo = await state.get_conversation(conversations[0].id)
    assert len(convo.thread) == 1
    assert convo.status == "needs_human"
    assert await state.is_reply_processed("<reply@x>")


@pytest.mark.asyncio
async def test_failed_processing_can_be_retried(tmp_path):
    state = StateManager(str(tmp_path / "inbox.db"))
    await state.init_db()
    config = load_config()
    config.channels.email.provider = "smtp"
    handler = Handler(brain=None, state=state, config=config, env=EnvConfig())
    msg = InboundMessage(provider_id="<retry@x>", from_email="person@example.test", body="Hello")
    class Provider:
        def is_configured(self): return True
        async def get_replies(self): return [msg]
    handler.provider = Provider()
    async def broken(*args, **kwargs): raise RuntimeError("temporary storage failure")
    handler._process_reply = broken
    assert await handler._run_native() is False
    assert not await state.is_reply_processed("<retry@x>")
