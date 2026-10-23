"""Exact local outreach evidence. No fuzzy identity merge or implicit permission."""
import hashlib
import json

import aiosqlite


def _normal(value):
    return (value or '').strip().lower()


async def outreach_report(db, campaign_id, contact_ids):
    """Use the caller's transaction so acknowledgment cannot race preparation."""
    db.row_factory = aiosqlite.Row
    people = {r['id']: dict(r) for r in await (await db.execute('''
        SELECT p.id,p.email,p.company,p.company_id,p.first_name,p.last_name,
        c.id AS established_company FROM prospects p LEFT JOIN companies c ON c.id=p.company_id
    ''')).fetchall()}
    selected = {pid: people[pid] for pid in contact_ids if pid in people}
    campaigns = await (await db.execute('SELECT id,name,status,prospect_ids_json FROM campaigns WHERE id!=? ORDER BY id', (campaign_id,))).fetchall()
    messages = await (await db.execute('''SELECT o.id,o.campaign_id,o.prospect_id,o.to_email,o.status,o.sent_at,
        c.name AS campaign_name,c.status AS campaign_status FROM outbox o
        LEFT JOIN campaigns c ON c.id=o.campaign_id WHERE COALESCE(o.campaign_id,'')!=? ORDER BY o.id''', (campaign_id,))).fetchall()
    events = []
    for campaign in campaigns:
        try:
            members = json.loads(campaign['prospect_ids_json'] or '[]')
        except (ValueError, TypeError):
            continue
        if not isinstance(members, list):
            continue
        for pid in sorted({p for p in members if isinstance(p, str)}):
            events.append({'contact_id':pid,'campaign_id':campaign['id'],'campaign_name':campaign['name'],
                'campaign_status':campaign['status'],'kind':'membership','status':campaign['status'],'id':pid,'sent_at':''})
    for row in messages:
        events.append({'contact_id':row['prospect_id'],'campaign_id':row['campaign_id'],
            'campaign_name':row['campaign_name'] or row['campaign_id'],'campaign_status':row['campaign_status'] or 'unknown',
            'kind':'message','status':row['status'],'id':row['id'],'sent_at':row['sent_at'] or '', 'email':row['to_email']})
    # Other selected recipients are evidence too, not a guessed identity merge.
    for pid in sorted(selected):
        events.append({'contact_id':pid,'campaign_id':campaign_id,'campaign_name':'','campaign_status':'manual_draft',
            'kind':'selection','status':'selected','id':pid,'sent_at':''})
    # Index once instead of scanning every historical event for every recipient.
    from collections import defaultdict
    indices = [defaultdict(set) for _ in range(4)]
    for i, event in enumerate(events):
        person = people.get(event['contact_id'], {})
        keys = [event['contact_id'], _normal(event.get('email') if event['kind']=='message' else person.get('email')),
                person.get('established_company'), _normal(person.get('company'))]
        for index, key in zip(indices, keys):
            if key:
                index[key].add(i)
    findings = []
    for pid, person in sorted(selected.items()):
        keys = [pid, _normal(person['email']), person['established_company'], _normal(person['company'])]
        candidates = set().union(*(index.get(key, set()) for index, key in zip(indices, keys) if key))
        for i in sorted(candidates):
            event = events[i]
            other = people.get(event['contact_id'], {})
            if event['kind']=='selection' and event['contact_id']==pid:
                continue
            reasons = []
            if event['contact_id']==pid:
                reasons.append('same_contact')
            address = event.get('email') if event['kind']=='message' else other.get('email')
            if _normal(person['email']) and _normal(person['email'])==_normal(address):
                reasons.append('same_email')
            if person['established_company'] and person['established_company']==other.get('established_company'):
                reasons.append('same_company')
            elif _normal(person['company']) and _normal(person['company'])==_normal(other.get('company')):
                reasons.append('uncertain_company_name')
            if not reasons:
                continue
            findings.append(dict(event, recipient_id=pid, recipient_email=person['email'],
                matched_email=address or '', matched_name=' '.join(filter(None,[other.get('first_name'),other.get('last_name')])),
                company=person['company'], reasons=reasons))
    token = hashlib.sha256(json.dumps({'campaign_id':campaign_id,'findings':findings},sort_keys=True,ensure_ascii=True).encode()).hexdigest() if findings else ''
    return {'findings':findings,'acknowledgment':token}
