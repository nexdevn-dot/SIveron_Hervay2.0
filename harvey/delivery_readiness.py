"""Read-only delivery assessment shared by native Sender and dashboard.

No provider connection checks, model calls, approvals or sends occur here.
"""
import json
import hashlib
import os
from datetime import datetime, timedelta, timezone

from harvey.gate import pre_send_check

STOP_STATUSES = {'replied', 'opted_out', 'lost', 'meeting', 'closed'}
SEQUENCE_READY_SQL = """(kind != 'sequence' OR step=1 OR (
    campaign_id!='' AND step>1 AND delay_days IS NOT NULL AND EXISTS (
        SELECT 1 FROM outbox p WHERE p.campaign_id=outbox.campaign_id
          AND p.prospect_id=outbox.prospect_id AND p.kind='sequence'
          AND p.step=outbox.step-1 AND p.status='sent'
          AND julianday(p.sent_at)+outbox.delay_days<=julianday(?)
    )))"""

# Stable reason codes; UI translations are kept with their next action.
REASONS = {
 'approval': ('Freigabe fehlt', 'Approval required', 'Nachricht prüfen und freigeben.', 'Review and approve this message.', 'outbox'),
 'paused': ('Versand pausiert', 'Sending paused', 'Versandpause im Postausgang prüfen.', 'Review the sending pause in Outbox.', 'outbox'),
 'disabled': ('E-Mail-Versand deaktiviert', 'Email sending disabled', 'Versandeinstellungen prüfen.', 'Review sending settings.', 'settings'),
 'provider': ('Versandweg nicht eingerichtet', 'Mail provider not configured', 'SMTP oder Gmail in den Einstellungen prüfen.', 'Review SMTP or Gmail settings.', 'settings'),
 'config': ('Einstellungen nicht prüfbar', 'Settings could not be checked', 'Konfiguration in den Einstellungen prüfen.', 'Review configuration in Settings.', 'settings'),
 'cap': ('Tageslimit erreicht', 'Daily allowance exhausted', 'Nächstes UTC-Tageskontingent abwarten oder Limit prüfen.', 'Wait for the next UTC daily allowance or review the limit.', 'settings'),
 'quiet': ('Ruhezeit aktiv', 'Quiet hours active', 'Ende der konfigurierten Ruhezeit abwarten.', 'Wait until configured quiet hours end.', 'settings'),
 'scheduled': ('Versandzeit noch nicht erreicht', 'Scheduled time is in the future', 'Den angezeigten frühesten Termin abwarten.', 'Wait until the displayed earliest time.', 'outbox'),
 'schedule_unknown': ('Versandzeit nicht lesbar', 'Scheduled time is unreadable', 'Nachricht und Planung prüfen; keine automatische Freigabe.', 'Review the message and schedule; no automatic approval.', 'outbox'),
 'predecessor': ('Vorgänger noch nicht erfolgreich versendet', 'Predecessor has not been sent successfully', 'Vorherigen Kampagnenschritt prüfen.', 'Review the previous campaign step.', 'outbox'),
 'spacing_unknown': ('Abstand oder Vorgänger nicht eindeutig', 'Spacing or predecessor is unknown', 'Alte Nachrichtenfolge prüfen; sie bleibt zurückgehalten.', 'Review this legacy sequence; it remains held.', 'outbox'),
 'spacing': ('Mindestabstand läuft noch', 'Follow-up delay has not elapsed', 'Abstand nach dem tatsächlichen Versand des Vorgängers abwarten.', 'Wait for the delay after the predecessor was actually sent.', 'outbox'),
 'missing_contact': ('Kontakt fehlt', 'Contact missing', 'Kontaktzuordnung prüfen.', 'Review the contact association.', 'prospects'),
 'suppressed': ('Kontakt ist gesperrt', 'Contact is suppressed', 'Kontaktsperre prüfen; keine automatische Aufhebung.', 'Review the contact block; it is not lifted automatically.', 'prospects'),
 'stop': ('Nachrichtenfolge für diesen Kontakt beendet', 'Sequence stopped for this contact', 'Antwort oder Kontaktstatus prüfen.', 'Review the reply or contact status.', 'conversations'),
 'content': ('Empfänger oder Nachrichteninhalt nicht versandfähig', 'Recipient or content failed validation', 'Adresse, Verifizierung, Platzhalter und Inhalt prüfen.', 'Review address, verification, placeholders and content.', 'outbox'),
 'address': ('E-Mail-Adresse ungültig', 'Invalid email address', 'Adresse des Kontakts korrigieren.', 'Correct the contact email address.', 'prospects'),
 'unverified': ('Technische E-Mail-Prüfung für diesen Versandweg erforderlich', 'Email verification required for this sending path', 'Kontaktprüfung und Kampagnenweg prüfen.', 'Review contact verification and campaign path.', 'prospects'),
 'recipient_changed': ('Empfänger stimmt nicht mehr mit dem Kontakt überein', 'Recipient no longer matches contact', 'Kontakt und vorbereitete Nachricht prüfen.', 'Review the contact and prepared message.', 'prospects'),
 'placeholders': ('Nicht aufgelöste Platzhalter', 'Unresolved placeholders', 'Nachricht vor erneuter Vorbereitung korrigieren.', 'Correct the message before preparing it again.', 'outbox'),
 'subject': ('Betreff fehlt oder ist zu lang', 'Subject missing or too long', 'Betreff im Entwurf korrigieren.', 'Correct the subject in the draft.', 'outbox'),
 'body': ('Nachrichtentext fehlt oder ist zu lang', 'Message body missing or too long', 'Nachrichtentext im Entwurf korrigieren.', 'Correct the message body in the draft.', 'outbox'),
 'attachments': ('Anhang fehlt oder ist ungültig', 'Attachment missing or invalid', 'Gespeicherte Anhänge prüfen.', 'Review the saved attachments.', 'outbox'),
 'agent_stopped': ('Agent ist gestoppt', 'Agent is stopped', 'Agent bei gewünschtem Versand bewusst starten.', 'Start the agent deliberately when sending is intended.', 'control'),
 'runtime_unknown': ('Aktuelle Laufzeitprüfung fehlt', 'Current runtime assessment unavailable', 'Agentenstatus und Protokoll prüfen; Bereitschaft ist ungeklärt.', 'Review agent status and logs; readiness is unconfirmed.', 'control'),
 'model': ('Agent durch KI-Verfügbarkeitsprüfung angehalten', 'Agent held by model availability check', 'Anmeldung und Agentenprotokoll prüfen.', 'Review authentication and agent logs.', 'control'),
 'mailbox': ('Antwortprüfung nicht erfolgreich', 'Reply safety check did not succeed', 'Postfachverbindung und Agentenprotokoll prüfen.', 'Review mailbox connection and agent logs.', 'control'),
 'runtime_config': ('Agent verwendet einen anderen Einstellungsstand', 'Agent configuration differs', 'Agentenprotokoll prüfen und Konfiguration regulär neu laden.', 'Review agent logs and reload configuration through the normal restart.', 'control'),
 'failed': ('Versand fehlgeschlagen', 'Sending failed', 'Fehler im Nachrichtenverlauf prüfen; kein automatischer Neuversand.', 'Review the recorded error; no automatic retry.', 'outbox'),
 'rejected': ('Nachricht abgelehnt', 'Message rejected', 'Entscheidung prüfen; keine automatische Reaktivierung.', 'Review the decision; no automatic reactivation.', 'outbox'),
 'cancelled': ('Nachricht abgebrochen', 'Message cancelled', 'Kontaktstatus und Verlauf prüfen; kein automatischer Neustart.', 'Review contact status and history; no automatic restart.', 'outbox'),
}
WAIT_CODES = {'approval', 'cap', 'quiet', 'scheduled', 'predecessor', 'spacing'}
UNKNOWN_CODES = {'config','runtime_unknown','runtime_config','spacing_unknown','schedule_unknown'}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def timestamp(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def result(codes, earliest=None, remaining=None):
    codes = list(dict.fromkeys(codes))
    state = ('blocked' if any(c not in WAIT_CODES | UNKNOWN_CODES for c in codes) else
             'unknown' if any(c in UNKNOWN_CODES for c in codes) else
             'waiting' if codes else 'ready')
    if 'failed' in codes:
        state = 'failed'
    return {'state': state, 'reasons': [dict(zip(('code','de','en','next_de','next_en','target'),
            (c, *REASONS[c]))) for c in codes],
            'earliest_at': earliest.isoformat() if earliest else None,
            'remaining_today': remaining}


async def global_context(state, config, provider, now=None):
    now = now or utcnow()
    codes = []
    email = config.channels.email
    if not email.enabled:
        codes.append('disabled')
    if email.provider not in ('smtp', 'gmail') or provider is None or not provider.is_configured():
        codes.append('provider')
    if await state.get_setting('sending_paused'):
        codes.append('paused')
    remaining = max(0, email.max_daily_sends - await state.count_outbox_sent_today())
    if not remaining:
        codes.append('cap')
    if getattr(getattr(config, 'usage', None), 'quiet_hours', None):
        from harvey.main import in_quiet_hours
        if in_quiet_hours(config):
            codes.append('quiet')
    return {'codes': codes, 'remaining': remaining, 'now': now}


def config_signature(config):
    # Only lifecycle-relevant, non-secret configuration; never serialize mailbox credentials.
    email = config.channels.email
    quiet = getattr(getattr(config, 'usage', None), 'quiet_hours', None)
    values = [email.enabled, email.provider, email.max_daily_sends, getattr(email,'send_to_risky',False),
              str(quiet), str(getattr(config, 'brain', None))]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


async def record_runtime(state, *, model_ok, reply_safe=None, approved_only=False, config=None):
    """Best-effort observation of checks already performed by the heartbeat."""
    try:
        await state.set_setting('delivery_runtime', json.dumps({
            'pid': os.getpid(), 'checked_at': utcnow().isoformat(),
            'model_ok': model_ok, 'reply_safe': reply_safe, 'approved_only': approved_only,
            'config_signature': config_signature(config) if config is not None else None}))
    except Exception:
        # Diagnostic storage must never change the heartbeat's send decisions.
        pass


def runtime_codes(raw, pid, now, ttl_seconds, signature=None):
    if not pid:
        return ['agent_stopped']
    try:
        snapshot = json.loads(raw or '{}')
        checked = timestamp(snapshot.get('checked_at'))
        if snapshot.get('pid') != pid or checked is None or not 0 <= (now-checked).total_seconds() <= ttl_seconds:
            return ['runtime_unknown']
        if signature is not None and snapshot.get('config_signature') != signature:
            return ['runtime_config']
        codes = []
        if snapshot.get('model_ok') is None:
            codes.append('runtime_unknown')
        elif snapshot.get('model_ok') is not True:
            codes.append('model')
        if snapshot.get('reply_safe') is not True:
            codes.append('mailbox' if snapshot.get('reply_safe') is False else 'runtime_unknown')
        return codes
    except (ValueError, TypeError, AttributeError):
        return ['runtime_unknown']


async def assess_message(state, item, config, context, *, runtime=()):
    """Return deterministic blockers. Does not mutate a message or perform I/O to a provider."""
    status = item.get('status')
    if status == 'sent':
        return {'state':'sent','reasons':[], 'earliest_at':None, 'remaining_today':context.get('remaining')}
    if status in ('failed', 'rejected', 'cancelled'):
        return result([status])
    codes = list(context['codes']) + list(runtime)
    now = context['now']
    if status != 'approved':
        codes.append('approval')
    earliest = timestamp(item.get('send_at'))
    if item.get('send_at') and earliest is None:
        codes.append('schedule_unknown')
    if earliest and earliest > now:
        codes.append('scheduled')
    if item.get('kind') == 'sequence' and item.get('step', 1) != 1:
        async with state._connect() as db:
            row = await (await db.execute("""SELECT status,sent_at FROM outbox
                WHERE kind='sequence' AND campaign_id=? AND prospect_id=? AND step=?""",
                (item.get('campaign_id',''), item.get('prospect_id',''), item.get('step',1)-1))).fetchone()
        delay = item.get('delay_days')
        if not item.get('campaign_id') or row is None or type(delay) is not int or delay < 0:
            codes.append('spacing_unknown')
        elif row[0] != 'sent':
            codes.append('predecessor')
        else:
            sent = timestamp(row[1])
            try:
                due = sent + timedelta(days=delay) if sent else None
            except OverflowError:
                due = None
            if due is None:
                codes.append('spacing_unknown')
            else:
                earliest = max(earliest, due) if earliest else due
                if due > now:
                    codes.append('spacing')
    cache = context.setdefault('cache', {})
    key = ('contact', item.get('prospect_id',''))
    if key not in cache:
        cache[key] = await state.get_prospect(item.get('prospect_id',''))
    prospect = cache[key]
    if not prospect:
        codes.append('missing_contact')
    else:
        key = ('suppression', prospect.id, item.get('to_email',''))
        if key not in cache:
            cache[key] = await state.is_contact_suppressed(prospect.id, item.get('to_email',''))
        if cache[key]:
            codes.append('suppressed')
        if item.get('kind') == 'sequence' and prospect.status in STOP_STATUSES:
            codes.append('stop')
        optional = False
        if item.get('campaign_id'):
            async with state._connect() as db:
                campaign = await (await db.execute('SELECT status,brief_json FROM campaigns WHERE id=?',
                                                    (item['campaign_id'],))).fetchone()
            if campaign and campaign[0] == 'awaiting_review':
                try:
                    optional = json.loads(campaign[1] or '{}').get('email_verification_optional') is True
                except (ValueError, AttributeError):
                    pass
        gate = pre_send_check(item.get('to_email',''), item.get('subject',''), item.get('body',''),
            prospect, allow_risky=getattr(config.channels.email,'send_to_risky',False),
            kind=item.get('kind','sequence'), verification_optional=optional)
        if not gate:
            for reason in gate.reasons:
                if reason.startswith('invalid recipient'): codes.append('address')
                elif reason.startswith('email_status'): codes.append('unverified')
                elif reason.startswith('recipient does not match'): codes.append('recipient_changed')
                elif reason.startswith('unrendered'): codes.append('placeholders')
                elif reason == 'empty subject' or reason.startswith('subject too long'): codes.append('subject')
                elif reason == 'empty body' or reason.startswith('body too long'): codes.append('body')
            codes.append('content')
    try:
        from harvey.campaign_content import load_attachments, ContactError
        ids = json.loads(item.get('attachment_ids_json') or '[]')
        if ids:
            async with state._connect() as db:
                await load_attachments(db, ids)
    except (ValueError, TypeError, ContactError):
        codes.append('attachments')
    return result(codes, earliest, context.get('remaining'))
