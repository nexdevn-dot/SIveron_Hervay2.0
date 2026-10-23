"""Read-only campaign counts and explicitly recorded conversation outcomes."""
import hashlib
import json
import re
from datetime import datetime,timedelta,timezone

import aiosqlite
from fastapi import Request
from fastapi.responses import JSONResponse
from harvey.delivery_readiness import timestamp


def incoming(thread_json):
    try:thread=json.loads(thread_json or '[]')
    except (ValueError,TypeError):return []
    if not isinstance(thread,list):return []
    unique={}
    for msg in thread:
        if not isinstance(msg,dict) or msg.get('sender')!='prospect' or not isinstance(msg.get('content'),str) or not msg['content'].strip():continue
        key=msg.get('provider_id') or hashlib.sha256(json.dumps([msg.get('timestamp'),msg['content']],sort_keys=True).encode()).hexdigest()
        if not isinstance(key,str):continue
        unique[key]=msg
    return list(unique.values())


def reply_fingerprint(row):
    messages=incoming(row.get('thread_json'))
    return hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest() if messages else ''


def bounds(start,end):
    def parse(value):
        if value is None:return None
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Invalid UTC date')
        return datetime.strptime(value,'%Y-%m-%d')
    first,last=parse(start),parse(end)
    if first and last and first>last:raise ValueError('Invalid date range')
    try:return first,last+timedelta(days=1) if last else None
    except OverflowError:raise ValueError('Invalid date range')


async def campaign_results(state,campaign_id,start=None,end=None):
    lower,upper=bounds(start,end)
    def inside(value):
        at=timestamp(value)
        return at is not None and (lower is None or at>=lower) and (upper is None or at<upper)
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        row=await (await db.execute('SELECT * FROM campaigns WHERE id=?',(campaign_id,))).fetchone()
        if not row:raise LookupError('Campaign not found')
        campaign=dict(row)
        try:members=set(x for x in json.loads(campaign['prospect_ids_json'] or '[]') if isinstance(x,str) and x)
        except (ValueError,TypeError):members=set()
        messages=[dict(r) for r in await (await db.execute('SELECT * FROM outbox WHERE campaign_id=? ORDER BY id',(campaign_id,))).fetchall()]
        conversations=[dict(r) for r in await (await db.execute('''SELECT c.*,o.qualified,o.meeting,o.qualified_at,o.meeting_at
            FROM conversations c LEFT JOIN conversation_outcomes o ON c.id=o.conversation_id
            WHERE c.campaign_id=? ORDER BY c.id''',(campaign_id,))).fetchall()]
        people={r['id']:dict(r) for r in await (await db.execute('''SELECT p.id,p.email,p.first_name,p.last_name,p.company,p.do_not_contact,p.status,
            EXISTS(SELECT 1 FROM contact_suppressions s WHERE s.email=lower(trim(p.email))) AS suppressed,
            EXISTS(SELECT 1 FROM contact_trash t WHERE t.prospect_id=p.id) AS deleted FROM prospects p''')).fetchall()}
    participants=members|{r['prospect_id'] for r in messages+conversations if r['prospect_id']}
    valid=re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    contactable={pid for pid in members if (p:=people.get(pid)) and valid.fullmatch(p['email'] or '') and not(p['suppressed'] or p['deleted'] or p['do_not_contact'] or p['status']=='opted_out')}
    def stage(rows,field):
        chosen=[r for r in rows if inside(r.get(field))]
        return {'contacts':len({r['prospect_id'] for r in chosen if r['prospect_id']}),'messages':len(chosen),
            'contact_ids':sorted({r['prospect_id'] for r in chosen if r['prospect_id']}),'message_ids':[r['id'] for r in chosen]}
    approved=stage(messages,'approved_at');sent=stage([r for r in messages if r['status']=='sent'],'sent_at')
    reply_ids=set();reply_messages=0;reply_convos=[];unknown_reply_dates=0
    seen_receipts=set()
    for convo in conversations:
        counted=False
        for message in incoming(convo['thread_json']):
            key=(convo['prospect_id'],message.get('provider_id') or json.dumps([message.get('timestamp'),message['content']]))
            if key in seen_receipts:continue
            seen_receipts.add(key)
            if not timestamp(message.get('timestamp')):unknown_reply_dates+=1
            if inside(message.get('timestamp')):
                reply_messages+=1
                if convo['prospect_id']:reply_ids.add(convo['prospect_id'])
                counted=True
        if counted:reply_convos.append(convo['id'])
    outcomes={}
    for field in ('qualified','meeting'):
        latest={}
        for c in conversations:
            if c[field] is None:continue
            old=latest.get(c['prospect_id'])
            if old is None or (timestamp(c[field+'_at']) or datetime.min,c['id'])>(timestamp(old[field+'_at']) or datetime.min,old['id']):latest[c['prospect_id']]=c
        chosen=[c for c in latest.values() if c['prospect_id'] and c[field]==1 and inside(c[field+'_at'])]
        outcomes[field]={'contacts':len({c['prospect_id'] for c in chosen}),'contact_ids':sorted({c['prospect_id'] for c in chosen}),
            'conversation_ids':[c['id'] for c in chosen],
            'unassessed_conversations':sum(c[field] is None for c in conversations)}
    contact_rows=[dict(people.get(pid,{'id':pid,'missing':True}),member=pid in members,contactable=pid in contactable,
        approved=pid in approved['contact_ids'],sent=pid in sent['contact_ids'],replied=pid in reply_ids,
        qualified=pid in outcomes['qualified']['contact_ids'],meeting=pid in outcomes['meeting']['contact_ids']) for pid in sorted(participants)]
    return {'id':campaign_id,'name':campaign['name'],'window':{'from':start,'through':end,'timezone':'UTC'},
        'checked_at':datetime.now(timezone.utc).isoformat(),'participants':len(participants),'members_current':len(members),
        'external_delivery':None,'coverage':'local_records_only','researched':None,'contactable_current':len(contactable),'approved':approved,'sent':sent,
        'replied':{'contacts':len(reply_ids),'messages':reply_messages,'conversation_ids':reply_convos},**outcomes,
        'unknown_approval_dates':sum(r['status'] in ('approved','sent') and not timestamp(r['approved_at']) for r in messages),
        'unknown_sent_dates':sum(r['status']=='sent' and not timestamp(r['sent_at']) for r in messages),
        'unknown_reply_dates':unknown_reply_dates,'contacts':contact_rows,
        'conversation_ids':[c['id'] for c in conversations], 'message_status_counts':{status:sum(r['status']==status for r in messages) for status in sorted({r['status'] for r in messages})}}


def install_result_routes(app,state_factory):
    async def state():
        sm=state_factory();await sm.init_db();return sm

    @app.get('/api/campaigns/{campaign_id}/results')
    async def results(campaign_id:str,start:str|None=None,end:str|None=None):
        try:return await campaign_results(await state(),campaign_id,start,end)
        except ValueError:return JSONResponse({'error':'Invalid UTC date range'},status_code=422)
        except LookupError:return JSONResponse({'error':'Campaign not found'},status_code=404)

    @app.get('/api/conversations/{conversation_id}/review')
    async def detail(conversation_id:str):
        sm=await state()
        async with sm._connect() as db:
            db.row_factory=aiosqlite.Row
            row=await (await db.execute('''SELECT c.*,p.first_name,p.last_name,p.email AS prospect_email,ca.name AS campaign_name
                FROM conversations c LEFT JOIN prospects p ON c.prospect_id=p.id LEFT JOIN campaigns ca ON ca.id=c.campaign_id WHERE c.id=?''',(conversation_id,))).fetchone()
            if not row:return JSONResponse({'error':'Conversation not found'},status_code=404)
            result=dict(row);outcome=await (await db.execute('SELECT * FROM conversation_outcomes WHERE conversation_id=?',(conversation_id,))).fetchone()
        try:result['thread']=json.loads(result['thread_json'] or '[]')
        except ValueError:result['thread']=[]
        if not isinstance(result['thread'],list):result['thread']=[]
        result['fingerprint']=reply_fingerprint(result)
        result['outcome']=dict(outcome) if outcome else {'qualified':None,'meeting':None,'note':'','revision':0}
        return result

    @app.post('/api/conversations/{conversation_id}/review')
    async def review(conversation_id:str,request:Request):
        try:
            data=await request.json();sm=await state()
            async with sm._connect() as db:
                db.row_factory=aiosqlite.Row;await db.execute('BEGIN IMMEDIATE')
                row=await (await db.execute('SELECT * FROM conversations WHERE id=?',(conversation_id,))).fetchone()
                fingerprint=reply_fingerprint(dict(row)) if row else ''
                if not isinstance(data,dict) or not fingerprint or data.get('fingerprint')!=fingerprint:raise ValueError()
                await db.execute('INSERT INTO conversation_reviews(conversation_id,fingerprint) VALUES (?,?) ON CONFLICT(conversation_id) DO UPDATE SET fingerprint=excluded.fingerprint,reviewed_at=CURRENT_TIMESTAMP',(conversation_id,fingerprint));await db.commit()
            return {'reviewed':True}
        except (ValueError,TypeError):return JSONResponse({'error':'Reply changed or unavailable. Reload before marking reviewed.'},status_code=409)

    @app.post('/api/conversations/{conversation_id}/outcome')
    async def outcome(conversation_id:str,request:Request):
        try:
            data=await request.json()
            if not isinstance(data,dict) or 'qualified' not in data or 'meeting' not in data or type(data.get('revision')) is not int or any(v is not None and type(v) is not bool for v in [data.get('qualified'),data.get('meeting')]) or not isinstance(data.get('note',''),str) or len(data.get('note',''))>2000:raise ValueError()
            sm=await state()
            async with sm._connect() as db:
                db.row_factory=aiosqlite.Row;await db.execute('BEGIN IMMEDIATE')
                if not await (await db.execute('SELECT 1 FROM conversations WHERE id=?',(conversation_id,))).fetchone():raise ValueError()
                old=await (await db.execute('SELECT * FROM conversation_outcomes WHERE conversation_id=?',(conversation_id,))).fetchone()
                if data['revision']!=(old['revision'] if old else 0):raise ValueError()
                now=datetime.now(timezone.utc).isoformat()
                def at(key):return old[key+'_at'] if old and old[key]==data.get(key) else now if data.get(key) is not None else None
                await db.execute('''INSERT INTO conversation_outcomes(conversation_id,qualified,meeting,qualified_at,meeting_at,note,revision,updated_at)
                    VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(conversation_id) DO UPDATE SET qualified=excluded.qualified,meeting=excluded.meeting,qualified_at=excluded.qualified_at,meeting_at=excluded.meeting_at,note=excluded.note,revision=excluded.revision,updated_at=excluded.updated_at''',
                    (conversation_id,data.get('qualified'),data.get('meeting'),at('qualified'),at('meeting'),data.get('note','').strip(),data['revision']+1,now));await db.commit()
            return {'saved':True}
        except (ValueError,TypeError):return JSONResponse({'error':'Outcome changed or invalid. Reload and check your entries.'},status_code=409)
