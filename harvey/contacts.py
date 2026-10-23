"""Explicit contact creation. Transactions prevent duplicate manual/adopted contacts."""
import uuid
import re
from urllib.parse import urlparse
from harvey.models.company import Company

from harvey.collectors.company_contacts import normalize_email


class ContactError(ValueError):
    pass


async def create_contact(state, payload, candidate_id=None, contact_id=None):
    if not isinstance(payload, dict):
        raise ContactError('Bitte die Kontaktfelder ausfüllen.')
    fields = ('company_id', 'contact_type', 'first_name', 'last_name', 'title', 'email', 'phone', 'company_name', 'website')
    data = {}
    for key in fields:
        value = payload.get(key, '')
        if not isinstance(value, str) or len(value) > (200 if key != 'phone' else 80):
            raise ContactError('Ein Kontaktfeld ist zu lang oder ungültig.')
        data[key] = value.strip()
    data['contact_type'] = data['contact_type'] or 'person'
    if data['contact_type'] not in ('person', 'company'):
        raise ContactError('Bitte Person oder Firmenkontakt wählen.')
    company = await state.get_company(data['company_id']) if data['company_id'] else None
    if data['company_id'] and not company:
        raise ContactError('Das Unternehmen ist nicht mehr verfügbar.')
    if not company and data['website'] and not data['company_name']:
        raise ContactError('Bitte den Namen des neuen Unternehmens ergänzen.')
    if not company and data['company_name']:
        website = data['website']
        parsed = urlparse(website)
        if website and (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password):
            raise ContactError('Bitte eine Website mit https:// oder http:// eingeben.')
        company = Company(id=uuid.uuid4().hex[:12], name=data['company_name'], website=website,
                          domain=(parsed.hostname or '').lower().removeprefix('www.'), source='manual')
        new_company = True
    else:
        new_company = False
    if data['contact_type'] == 'company':
        if not company:
            raise ContactError('Bitte ein Unternehmen auswählen.')
        data.update(first_name='', last_name='', title='')
    elif not data['first_name'] or not data['last_name']:
        raise ContactError('Bitte Vorname und Nachname eingeben. Die Position ist optional.')
    if data['email']:
        email = normalize_email(data['email'])
        if not email:
            raise ContactError('Bitte eine gültige E-Mail-Adresse eingeben.')
        data['email'] = email
    async with state._connect() as db:
        await db.create_function('contact_casefold', 1, lambda value: (value or '').casefold(), deterministic=True)
        await db.create_function('contact_phone', 1, lambda value: re.sub(r'\D', '', value or '').removeprefix('00'), deterministic=True)
        await db.execute('BEGIN IMMEDIATE')
        original = None
        if contact_id:
            import aiosqlite
            db.row_factory = aiosqlite.Row
            row = await (await db.execute('SELECT * FROM prospects WHERE id=?', (contact_id,))).fetchone()
            if not row:
                raise ContactError('Kontakt nicht gefunden.')
            if await (await db.execute('SELECT 1 FROM contact_trash WHERE prospect_id=?',(contact_id,))).fetchone():
                raise ContactError('Der Kontakt ist gelöscht. Bitte zuerst wiederherstellen.')
            original = dict(row)
            if payload.get('revision') != original['revision']:
                raise ContactError('Der Kontakt wurde inzwischen geändert. Bitte neu laden.')
            if '_research_finding' in payload:
                from harvey.contact_research import contact_fingerprint
                import json
                evidence=await (await db.execute('''SELECT f.*,j.contact_id,j.snapshot_json FROM contact_email_findings f
                    JOIN contact_email_research j ON j.id=f.job_id WHERE f.id=? AND j.contact_id=?''',
                    (payload['_research_finding'],contact_id))).fetchone()
                if not evidence or evidence['email']!=data['email'] or payload.get('_research_reviewed') is not True:
                    raise ContactError('Ungültiger Recherchefund.')
                expected=contact_fingerprint(json.loads(evidence['snapshot_json']))
                if expected!=contact_fingerprint(original) or expected!=payload.get('_research_snapshot'):
                    raise ContactError('Der Kontakt wurde inzwischen geändert. Bitte erneut recherchieren.')
                suppressed=await (await db.execute("SELECT 1 FROM contact_suppressions WHERE prospect_id=? OR (email!='' AND (email=lower(?) OR email=lower(?)))",(contact_id,original['email'],data['email']))).fetchone()
                if original['do_not_contact'] or original['status']=='opted_out' or suppressed:
                    raise ContactError('Für diesen Kontakt besteht eine Kontaktsperre.')
                if original['contact_type']=='person' and evidence['kind'] not in ('person_explicit','provider_suggestion') and payload.get('_research_ack_unclear') is not True:
                    raise ContactError('Die persönliche Zuordnung muss ausdrücklich geprüft werden.')
                await db.execute("INSERT INTO feedback(id,entity_type,entity_id,comment) VALUES (?,'contact',?,?)",(uuid.uuid4().hex[:12],contact_id,'E-Mail-Recherche: '+evidence['email']+' · '+evidence['kind']+' · '+(evidence['source_url'] or evidence['method'])))
                await db.execute("UPDATE contact_email_findings SET adopted_at=CURRENT_TIMESTAMP WHERE id=?",(evidence['id'],))
            if data['contact_type'] != original['contact_type']:
                raise ContactError('Die Kontaktart kann bei bestehenden Kontakten nicht geändert werden.')
        if new_company:
            existing_company = await (await db.execute("SELECT id FROM companies WHERE removed_at IS NULL AND ((? != '' AND domain=?) OR contact_casefold(name)=contact_casefold(?)) LIMIT 1", (company.domain, company.domain, company.name))).fetchone()
            if existing_company:
                company = await state.get_company(existing_company[0])
            else:
                taken = await (await db.execute("SELECT id FROM companies WHERE domain=? AND domain != ''", (company.domain,))).fetchone()
                if taken:
                    raise ContactError('Diese Website gehört zu einem bereinigten Unternehmen. Bitte zuerst die Bereinigung rückgängig machen.')
                await db.execute('INSERT INTO companies(id,name,domain,website,source) VALUES (?,?,?,?,?)', (company.id, company.name, company.domain, company.website, 'manual'))
            data['company_id'] = company.id
        if company:
            active = await (await db.execute('SELECT id FROM companies WHERE id=? AND removed_at IS NULL', (company.id,))).fetchone()
            if not active:
                raise ContactError('Das Unternehmen ist nicht mehr verfügbar.')
        candidate = None
        if candidate_id:
            candidate = await (await db.execute('SELECT status, prospect_id, company_id, source_url, found_at FROM person_candidates WHERE id=?', (candidate_id,))).fetchone()
            if not candidate or candidate[2] != data['company_id'] or data['contact_type'] != 'person':
                raise ContactError('Der Personenvorschlag ist nicht mehr verfügbar.')
            if candidate[0] == 'accepted':
                return {'id': candidate[1], 'duplicate': True}
            if candidate[0] != 'pending':
                raise ContactError('Dieser Vorschlag wurde bereits verworfen.')
            if '_candidate_snapshot' in payload:
                from harvey.decision_makers import CANDIDATE_FIELDS,fingerprint
                current=await (await db.execute('SELECT '+','.join(CANDIDATE_FIELDS)+' FROM person_candidates WHERE id=?',(candidate_id,))).fetchone()
                actual=dict(zip(CANDIDATE_FIELDS,current))
                if payload['_candidate_snapshot']!=fingerprint(actual):
                    raise ContactError('Der recherchierte Vorschlag wurde inzwischen geändert. Bitte erneut prüfen.')
        existing = await (await db.execute('''SELECT id FROM prospects WHERE id != ? AND (
            (? != '' AND lower(email)=lower(?)) OR
            (? != '' AND contact_phone(phone)=contact_phone(?) AND contact_type=? AND coalesce(company_id,'')=? AND (?='person' OR ?='')) OR
            (contact_type=? AND coalesce(company_id,'')=? AND
             ((?='person' AND ? != '' AND contact_casefold(first_name)=contact_casefold(?) AND contact_casefold(last_name)=contact_casefold(?)) OR
              (?='company' AND ?='' AND coalesce(email,'')='')))) LIMIT 1''',
            (contact_id or '', data['email'], data['email'], data['phone'], data['phone'], data['contact_type'], data['company_id'], data['contact_type'], data['email'], data['contact_type'], data['company_id'], data['contact_type'], data['company_id'],
             data['first_name'], data['last_name'], data['contact_type'], data['email']))).fetchone()
        if existing and await (await db.execute('SELECT 1 FROM contact_trash WHERE prospect_id=?',(existing[0],))).fetchone():
            raise ContactError('Dieser Kontakt liegt unter Gelöschte Kontakte. Bitte zuerst wiederherstellen.')
        if existing and contact_id:
            raise ContactError('Diese Daten gehören bereits zu einem anderen Kontakt. Bitte den bestehenden Kontakt prüfen.')
        if existing:
            owner = await (await db.execute('SELECT company_id, contact_type FROM prospects WHERE id=?', (existing[0],))).fetchone()
            if (owner[0] or '') != data['company_id'] or owner[1] != data['contact_type']:
                raise ContactError('Diese E-Mail gehört bereits zu einem anderen Kontakt. Bitte den bestehenden Kontakt prüfen oder eine andere E-Mail verwenden.')
        # Standalone people with equal names may differ: require a channel match for them.
        if existing and not data['company_id'] and not data['email'] and not data['phone']:
            existing = None
        if original:
            email_changed = data['email'] != original['email']
            phone_changed = data['phone'] != original['phone']
            keys = ('first_name', 'last_name', 'title', 'email', 'phone', 'company_id')
            changed = [key for key in keys if data[key] != (original[key] or '')]
            cancelled = 0
            if changed:
                await db.execute("""UPDATE prospects SET first_name=?,last_name=?,title=?,email=?,phone=?,company_id=?,company=?,
                    email_verified=?,email_status=?,phone_verified=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (data['first_name'],data['last_name'],data['title'],data['email'],data['phone'],data['company_id'],company.name if company else '',
                     0 if email_changed else original['email_verified'], '' if email_changed else original['email_status'],
                     0 if phone_changed else original['phone_verified'],contact_id))
                cursor = await db.execute("UPDATE outbox SET status='cancelled',error='contact edited; review new data',updated_at=CURRENT_TIMESTAMP WHERE prospect_id=? AND status IN ('pending_review','approved')", (contact_id,))
                cancelled = cursor.rowcount
                await db.execute("INSERT INTO feedback(id,entity_type,entity_id,comment) VALUES (?,'contact',?,?)", (uuid.uuid4().hex[:12],contact_id,'Kontakt bearbeitet: ' + ', '.join(changed)))
                if original['do_not_contact'] and data['email']:
                    await db.execute("INSERT OR IGNORE INTO contact_suppressions(email,prospect_id,reason) VALUES (?,?,?)", (data['email'],contact_id,original['block_reason'] or 'Kontaktsperre'))
            await db.commit()
            return {'id':contact_id,'duplicate':False,'updated':bool(changed),'cancelled':cancelled}
        contact_id = existing[0] if existing else uuid.uuid4().hex[:12]
        if not existing:
            source_url = candidate[3] if candidate else ''
            source_found_at = candidate[4] if candidate else ''
            if company and data['contact_type'] == 'company' and data['email']:
                evidence = await (await db.execute('SELECT source_url,found_at FROM company_public_emails WHERE company_id=? AND email=?', (company.id, data['email']))).fetchone()
                if evidence:
                    source_url, source_found_at = evidence
            await db.execute('''INSERT INTO prospects
                (id, company_id, contact_type, first_name, last_name, title, email, phone,
                 company, source, source_url, status, email_verified, email_status, source_found_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', ?)''',
                (contact_id, data['company_id'], data['contact_type'], data['first_name'], data['last_name'],
                 data['title'], data['email'], data['phone'], company.name if company else '',
                 'public_person' if candidate else 'manual', source_url,
                 'new' if data['contact_type'] == 'person' else 'company_contact', source_found_at))
        if candidate:
            await db.execute("UPDATE person_candidates SET status='accepted', prospect_id=? WHERE id=?", (contact_id, candidate_id))
        await db.commit()
    return {'id': contact_id, 'duplicate': bool(existing)}
