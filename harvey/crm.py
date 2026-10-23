"""Local contact actions and held campaign drafts. No implicit sending."""
import json
import uuid

import aiosqlite

from harvey.outreach_history import outreach_report
from harvey.contacts import ContactError
from harvey.campaign_content import rich_content, attachment_ids, load_attachments


async def set_contact_block(state, contact_id, blocked, reason, source='manual'):
    if not isinstance(blocked,bool) or not isinstance(reason,str) or len(reason)>2000 or (blocked and not reason.strip()):
        raise ContactError('Bitte einen Grund für die Kontaktsperre eingeben (maximal 2000 Zeichen).')
    async with state._connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute('BEGIN IMMEDIATE')
        row = await (await db.execute('SELECT * FROM prospects WHERE id=?',(contact_id,))).fetchone()
        if not row:
            raise ContactError('Kontakt nicht gefunden.')
        if await (await db.execute('SELECT 1 FROM contact_trash WHERE prospect_id=?',(contact_id,))).fetchone():
            raise ContactError('Der Kontakt ist gelöscht. Bitte zuerst wiederherstellen.')
        if not blocked and (row['status']=='opted_out' or await (await db.execute("SELECT 1 FROM contact_suppressions WHERE prospect_id=? AND source='opt_out'",(contact_id,))).fetchone()):
            raise ContactError('Eine Abmeldung kann hier nicht aufgehoben werden. Die Kontaktsperre bleibt bestehen.')
        await db.execute("UPDATE prospects SET do_not_contact=?,block_reason=?,blocked_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE '' END,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?", (int(blocked),reason.strip() if blocked else '',blocked,contact_id))
        cancelled=0
        if blocked:
            if row['email']:
                await db.execute('''INSERT INTO contact_suppressions(email,prospect_id,reason,source) VALUES (?,?,?,?)
                    ON CONFLICT(email) DO UPDATE SET reason=excluded.reason,
                    source=CASE WHEN contact_suppressions.source='opt_out' THEN 'opt_out' ELSE excluded.source END''',
                    (row['email'].strip().lower(),contact_id,reason.strip(),source))
            cursor=await db.execute("UPDATE outbox SET status='cancelled',error='do not contact',updated_at=CURRENT_TIMESTAMP WHERE (prospect_id=? OR (to_email != '' AND lower(to_email)=lower(?))) AND status IN ('pending_review','approved')",(contact_id,row['email']))
            cancelled=cursor.rowcount
            # A hosted provider may already own a sequence. Pause that whole campaign.
            campaigns=await (await db.execute("SELECT id,prospect_ids_json,instantly_campaign_id FROM campaigns WHERE instantly_campaign_id != ''")).fetchall()
            for campaign in campaigns:
                try:
                    members=json.loads(campaign['prospect_ids_json'] or '[]')
                except (ValueError,TypeError):
                    members=[]
                if contact_id in members:
                    await db.execute("UPDATE campaigns SET status='paused' WHERE id=?",(campaign['id'],))
                    await db.execute('INSERT OR IGNORE INTO campaign_pause_requests(campaign_id,remote_id) VALUES (?,?)',(campaign['id'],campaign['instantly_campaign_id']))
        else:
            await db.execute("DELETE FROM contact_suppressions WHERE prospect_id=? AND source='manual'",(contact_id,))
        await db.execute("INSERT INTO feedback(id,entity_type,entity_id,comment) VALUES (?,'contact',?,?)",(uuid.uuid4().hex[:12],contact_id,('Kontaktsperre gesetzt: '+reason.strip()) if blocked else 'Manuelle Kontaktsperre aufgehoben. Abgebrochene Nachrichten bleiben abgebrochen.'))
        await db.commit()
    return {'blocked':blocked,'cancelled':cancelled}


async def flush_remote_pauses(state, client):
    async with state._connect() as db:
        requests=await (await db.execute('SELECT campaign_id,remote_id FROM campaign_pause_requests')).fetchall()
    for campaign_id,remote_id in requests:
        try:
            import asyncio
            result=await asyncio.wait_for(client.pause_campaign(remote_id),timeout=10)
        except Exception:
            result=None
        if result is not None:
            async with state._connect() as db:
                await db.execute('DELETE FROM campaign_pause_requests WHERE campaign_id=?',(campaign_id,))
                await db.commit()
    async with state._connect() as db:
        return (await (await db.execute('SELECT COUNT(*) FROM campaign_pause_requests')).fetchone())[0]


def campaign_payload(payload):
    if not isinstance(payload,dict):
        raise ContactError('Ungültiger Kampagnenentwurf.')
    name=payload.get('name','')
    ids=payload.get('prospect_ids',[])
    sequence=payload.get('sequence',[])
    brief=payload.get('brief',{})
    if not isinstance(name,str) or not name.strip() or len(name)>200:
        raise ContactError('Bitte einen Kampagnennamen eingeben (maximal 200 Zeichen).')
    if not isinstance(ids,list) or len(ids)>5000 or any(not isinstance(i,str) or len(i)>100 for i in ids):
        raise ContactError('Bitte maximal 5000 Kontakte auswählen.')
    if not isinstance(sequence,list) or len(sequence)>10:
        raise ContactError('Eine Kampagne kann bis zu zehn Nachrichten enthalten.')
    steps=[]
    for i,step in enumerate(sequence):
        if not isinstance(step,dict):
            raise ContactError('Ungültige Nachricht.')
        subject,body,delay=step.get('subject',''),step.get('body',''),step.get('delay_days',0)
        if (not isinstance(subject,str) or len(subject)>200 or not isinstance(body,str) or len(body)>15000 or
            not isinstance(delay,int) or isinstance(delay,bool) or not 0<=delay<=365):
            raise ContactError('Bitte Betreff, Nachricht und Wartezeit prüfen (0 bis 365 Tage).')
        clean={'step':i+1,'subject':subject.strip(),'body':body.strip(),'delay_days':0 if i==0 else delay}
        if step.get('body_doc') is not None:
            doc,plain,_=rich_content(step['body_doc'])
            clean.update(body_doc=doc,body=plain.strip())
        if step.get('attachment_ids'):
            clean['attachment_ids']=attachment_ids(step['attachment_ids'])
        steps.append(clean)
    if not isinstance(brief,dict):
        raise ContactError('Ungültige Kampagnenangaben.')
    clean={}
    for key in ('audience','offer','goal','sender','signature'):
        value=brief.get(key,'')
        if not isinstance(value,str) or len(value)>4000:
            raise ContactError('Eine Kampagnenangabe ist zu lang.')
        clean[key]=value.strip()
    return name.strip(),list(dict.fromkeys(ids)),steps,clean


async def save_campaign_draft(state,payload,campaign_id=None):
    name,ids,steps,brief=campaign_payload(payload)
    async with state._connect() as db:
        await db.execute('BEGIN IMMEDIATE')
        for step in steps:
            await load_attachments(db,step.get('attachment_ids',[]))
        if campaign_id:
            old=await (await db.execute('SELECT status,revision,instantly_campaign_id FROM campaigns WHERE id=?',(campaign_id,))).fetchone()
            if not old:
                raise ContactError('Kampagne nicht gefunden.')
            staged=await (await db.execute('SELECT 1 FROM outbox WHERE campaign_id=? LIMIT 1',(campaign_id,))).fetchone()
            if old[0] not in ('manual_draft','draft') or old[2] or staged:
                raise ContactError('Diese Kampagne ist bereits an den Versand übergeben. Bitte einen neuen Entwurf anlegen.')
            if payload.get('revision')!=old[1]:
                raise ContactError('Die Kampagne wurde inzwischen geändert. Bitte neu laden.')
        for pid in ids:
            row=await (await db.execute('''SELECT p.id,p.do_not_contact,p.status,
                EXISTS(SELECT 1 FROM contact_suppressions s WHERE s.email=lower(p.email))
                FROM prospects p WHERE id=?''',(pid,))).fetchone()
            if not row or await (await db.execute('SELECT 1 FROM contact_trash WHERE prospect_id=?',(pid,))).fetchone():
                raise ContactError('Ein ausgewählter Kontakt ist nicht mehr verfügbar.')
            if row[1] or row[2]=='opted_out' or row[3]:
                raise ContactError('Ein ausgewählter Kontakt ist gesperrt. Bitte aus der Auswahl entfernen.')
        if campaign_id:
            await db.execute("UPDATE campaigns SET name=?,prospect_ids_json=?,sequence_json=?,brief_json=?,status='manual_draft',revision=revision+1 WHERE id=?",(name,json.dumps(ids),json.dumps(steps),json.dumps(brief),campaign_id))
        else:
            campaign_id=uuid.uuid4().hex[:12]
            await db.execute("INSERT INTO campaigns(id,name,channel,status,prospect_ids_json,sequence_json,brief_json) VALUES (?,?,'email','manual_draft',?,?,?)",(campaign_id,name,json.dumps(ids),json.dumps(steps),json.dumps(brief)))
        await db.commit()
    return {'id':campaign_id,'status':'manual_draft'}


async def campaign_detail(state,campaign_id):
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        row=await (await db.execute('SELECT * FROM campaigns WHERE id=?',(campaign_id,))).fetchone()
        if not row:
            raise ContactError('Kampagne nicht gefunden.')
        result=dict(row)
        result['prospect_ids']=json.loads(result.pop('prospect_ids_json') or '[]')
        result['sequence']=json.loads(result.pop('sequence_json') or '[]')
        result['brief']=json.loads(result.pop('brief_json') or '{}')
        for step in result['sequence']:
            step['attachments']=await load_attachments(db,step.get('attachment_ids',[]))
        result['contacts']=[]
        for pid in result['prospect_ids']:
            contact=await (await db.execute('''SELECT id,first_name,last_name,title,personalization_notes,company,contact_type,email,email_status,do_not_contact,status,
              EXISTS(SELECT 1 FROM contact_suppressions s WHERE s.email=lower(prospects.email)) AS suppressed
              FROM prospects WHERE id=?''',(pid,))).fetchone()
            result['contacts'].append(dict(contact) if contact else {'id':pid,'missing':True})
        counts = await (await db.execute('SELECT status,COUNT(*) FROM outbox WHERE campaign_id=? GROUP BY status', (campaign_id,))).fetchall()
        from harvey.email_checks import email_checks
        for contact in result['contacts']:
            if not contact.get('missing'):
                contact['email_checks'] = email_checks(contact.get('email'))
        result['outbox_summary'] = {status: count for status, count in counts}
        result['outreach_history'] = await outreach_report(db, campaign_id, result['prospect_ids'])
        result['editable']=result['status'] in ('manual_draft','draft') and not result['instantly_campaign_id'] and not await (await db.execute('SELECT 1 FROM outbox WHERE campaign_id=? LIMIT 1',(campaign_id,))).fetchone()
    return result


async def prepare_campaign_review(state, campaign_id, revision, outreach_acknowledgment=None):
    """Atomically snapshot a manual draft into the review queue. Never sends."""
    from datetime import datetime, timedelta, timezone
    from harvey.gate import pre_send_check
    from harvey.models import Prospect
    from harvey.agents.sender import Sender
    async with state._connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute('BEGIN IMMEDIATE')
        row = await (await db.execute('SELECT * FROM campaigns WHERE id=?', (campaign_id,))).fetchone()
        if not row:
            raise ContactError('Kampagne nicht gefunden.')
        if row['status'] == 'awaiting_review':
            return {'id': campaign_id, 'status': 'awaiting_review', 'already_prepared': True}
        if row['status'] != 'manual_draft' or row['instantly_campaign_id'] or revision != row['revision']:
            raise ContactError('Der Entwurf wurde geändert oder bereits übergeben. Bitte neu laden.')
        if await (await db.execute('SELECT 1 FROM outbox WHERE campaign_id=?', (campaign_id,))).fetchone():
            raise ContactError('Für diese Kampagne existieren bereits Nachrichten.')
        ids = json.loads(row['prospect_ids_json'])
        steps = json.loads(row['sequence_json'])
        if not ids or not steps:
            raise ContactError('Bitte Kontakte und mindestens eine vollständige Nachricht hinzufügen.')
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        messages, seen = [], set()
        for pid in ids:
            contact = await (await db.execute('SELECT * FROM prospects WHERE id=?', (pid,))).fetchone()
            if not contact:
                raise ContactError('Ein Kontakt ist nicht mehr verfügbar. Bitte aus dem Entwurf entfernen.')
            if contact['do_not_contact'] or contact['status'] == 'opted_out' or await (await db.execute('SELECT 1 FROM contact_suppressions WHERE email=lower(?)', (contact['email'],))).fetchone():
                raise ContactError('Ein Kontakt ist gesperrt. Bitte aus dem Entwurf entfernen.')
            if contact['status'] not in ('new', 'queued', 'company_contact'):
                raise ContactError('Ein Kontakt wurde bereits bearbeitet oder kontaktiert. Bitte aus dem Entwurf entfernen.')
            prospect = Prospect(**dict(contact))
            email = prospect.email.strip().lower()
            if email in seen:
                continue
            seen.add(email)
            days = 0
            for step in steps:
                days += step['delay_days']
                subject = Sender._render(None, step['subject'], prospect)
                body = Sender._render(None, step['body'], prospect)
                body_html=''
                if step.get('body_doc') is not None:
                    values={'first_name':prospect.first_name,'last_name':prospect.last_name,'company':prospect.company,'title':prospect.title,'personalization':prospect.personalization_notes}
                    _,body,body_html=rich_content(step['body_doc'],values)
                    body=body.strip()
                attachment_list=attachment_ids(step.get('attachment_ids',[]))
                files=await load_attachments(db,attachment_list)
                check = pre_send_check(email, subject, body, prospect, verification_optional=True)
                if not check:
                    translations={'empty subject':'Bitte einen Betreff eingeben','empty body':'Bitte einen Nachrichtentext eingeben'}
                    reasons=[translations.get(reason, 'Unbekannte Platzhalter im Text' if reason.startswith('unrendered merge tags') else 'Bitte eine gültige E-Mail-Adresse eintragen' if reason.startswith('invalid recipient') else reason) for reason in check.reasons]
                    raise ContactError('Nachricht für '+(prospect.company or email)+': '+ '; '.join(reasons))
                messages.append((uuid.uuid4().hex[:12], campaign_id, pid, step['step'], email, subject, body, (now+timedelta(days=days)).isoformat(),body_html,json.dumps(attachment_list),json.dumps(files),step['delay_days']))
        history = await outreach_report(db, campaign_id, ids)
        if history['findings'] and outreach_acknowledgment != history['acknowledgment']:
            raise ContactError('OUTREACH_REVIEW_REQUIRED')
        if history['findings']:
            await db.execute("INSERT INTO feedback(id,entity_type,entity_id,comment) VALUES (?,'campaign',?,?)",
                (uuid.uuid4().hex[:12], campaign_id, 'Outreach history explicitly reviewed: '+history['acknowledgment']))
        for values in messages:
            await db.execute("INSERT INTO outbox(id,campaign_id,prospect_id,step,to_email,subject,body,send_at,body_html,attachment_ids_json,attachment_metadata_json,delay_days,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pending_review')", values)
        for pid in ids:
            await db.execute("UPDATE prospects SET status='queued',revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?", (pid,))
        brief=json.loads(row['brief_json'] or '{}')
        brief['email_verification_optional']=True
        await db.execute("UPDATE campaigns SET status='awaiting_review',brief_json=?,revision=revision+1 WHERE id=?", (json.dumps(brief),campaign_id))
        await db.execute("INSERT INTO feedback(id,entity_type,entity_id,comment) VALUES (?,'campaign',?,'Manuell zur Freigabe vorbereitet; technische E-Mail-Verifizierung optional. Kein Versand gestartet.')", (uuid.uuid4().hex[:12],campaign_id))
        await db.commit()
    return {'id':campaign_id,'status':'awaiting_review','messages':len(messages)}


async def trash_contact(state, contact_id, revision, restore=False):
    """Reversibly remove a contact; atomically cancel pending delivery, retain history."""
    if not isinstance(revision,int) or isinstance(revision,bool):
        raise ContactError('Bitte den Kontakt neu laden.')
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        await db.execute('BEGIN IMMEDIATE')
        row=await (await db.execute('SELECT * FROM prospects WHERE id=?',(contact_id,))).fetchone()
        if not row:
            raise ContactError('Kontakt nicht gefunden.')
        if row['revision'] != revision:
            raise ContactError('Der Kontakt wurde inzwischen geändert. Bitte neu laden.')
        old=await (await db.execute('SELECT * FROM contact_trash WHERE prospect_id=?',(contact_id,))).fetchone()
        cancelled=0
        if restore:
            if not old:
                raise ContactError('Dieser Kontakt ist nicht gelöscht.')
            opted_out=row['status']=='opted_out' or bool(await (await db.execute("SELECT 1 FROM contact_suppressions WHERE prospect_id=? AND source='opt_out'",(contact_id,))).fetchone())
            await db.execute("UPDATE prospects SET status=?,do_not_contact=?,block_reason=?,blocked_at=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                ('opted_out' if opted_out else old['previous_status'] if row['status']=='deleted' else row['status'],
                 1 if opted_out else old['previous_blocked'], 'Abmeldung' if opted_out else old['previous_reason'],old['previous_blocked_at'],contact_id))
            await db.execute('DELETE FROM contact_trash WHERE prospect_id=?',(contact_id,))
            note='Kontakt wiederhergestellt. Abgebrochene Nachrichten und pausierte Kampagnen bleiben unverändert.'
        else:
            if old:
                raise ContactError('Dieser Kontakt ist bereits gelöscht.')
            await db.execute('INSERT INTO contact_trash(prospect_id,previous_status,previous_blocked,previous_reason,previous_blocked_at) VALUES (?,?,?,?,?)',
                (contact_id,row['status'],row['do_not_contact'],row['block_reason'],row['blocked_at']))
            await db.execute("UPDATE prospects SET status='deleted',do_not_contact=1,block_reason='Kontakt gelöscht',blocked_at=CURRENT_TIMESTAMP,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?",(contact_id,))
            cursor=await db.execute("UPDATE outbox SET status='cancelled',error='contact deleted',updated_at=CURRENT_TIMESTAMP WHERE (prospect_id=? OR (to_email != '' AND lower(to_email)=lower(?))) AND status IN ('pending_review','approved')",(contact_id,row['email']))
            cancelled=cursor.rowcount
            for campaign in await (await db.execute("SELECT id,prospect_ids_json,instantly_campaign_id FROM campaigns WHERE instantly_campaign_id != ''")).fetchall():
                if contact_id in json.loads(campaign['prospect_ids_json'] or '[]'):
                    await db.execute("UPDATE campaigns SET status='paused' WHERE id=?",(campaign['id'],))
                    await db.execute('INSERT OR IGNORE INTO campaign_pause_requests(campaign_id,remote_id) VALUES (?,?)',(campaign['id'],campaign['instantly_campaign_id']))
            note='Kontakt gelöscht: aus aktiver Liste entfernt; wartende Nachrichten abgebrochen. Wiederherstellung möglich.'
        await db.execute("INSERT INTO feedback(id,entity_type,entity_id,comment) VALUES (?,'contact',?,?)",(uuid.uuid4().hex[:12],contact_id,note))
        await db.commit()
    return {'deleted':not restore,'cancelled':cancelled}
