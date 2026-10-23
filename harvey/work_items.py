"""Derived tasks: no second scheduler, no stale notification rows to resolve."""
from collections import defaultdict
import json
from datetime import datetime,timezone
import aiosqlite
from fastapi.responses import JSONResponse
from harvey.campaign_results import reply_fingerprint,incoming
from harvey.delivery_readiness import assess_message,result


async def work_items(state,assessment):
    config,context,runtime=assessment
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        messages=[dict(r) for r in await (await db.execute("SELECT o.*,c.name AS campaign_name FROM outbox o LEFT JOIN campaigns c ON c.id=o.campaign_id WHERE o.status IN ('pending_review','approved') ORDER BY o.created_at,o.id")).fetchall()]
        conversations=[dict(r) for r in await (await db.execute('''SELECT c.*,p.first_name,p.last_name,p.email,ca.name AS campaign_name,r.fingerprint AS reviewed_fingerprint
            FROM conversations c LEFT JOIN prospects p ON p.id=c.prospect_id LEFT JOIN campaigns ca ON ca.id=c.campaign_id
            LEFT JOIN conversation_reviews r ON r.conversation_id=c.id WHERE c.status IN ('open','replied') ORDER BY c.updated_at,c.id''')).fetchall()]
    tasks=[]
    for c in conversations:
        fingerprint=reply_fingerprint(c)
        try:thread=json.loads(c['thread_json'] or '[]')
        except (ValueError,TypeError):thread=[]
        meaningful=[m for m in thread if isinstance(m,dict) and m.get('sender') in ('harvey','prospect') and m.get('content')] if isinstance(thread,list) else []
        if not fingerprint or c['reviewed_fingerprint']==fingerprint or not meaningful or meaningful[-1]['sender']!='prospect':continue
        tasks.append({'key':'reply:'+c['id'],'kind':'reply','conversation_id':c['id'],'campaign_id':c['campaign_id'],
            'campaign_name':c['campaign_name'] or '', 'name':' '.join(filter(None,[c['first_name'],c['last_name']])) or c['email'] or c['id'],
            'fingerprint':fingerprint,'count':len(incoming(c['thread_json']))})
    pending=defaultdict(list);blocked=defaultdict(list)
    for m in messages:
        if m['status']=='pending_review':pending[m['campaign_id'] or ''].append(m);continue
        readiness=await assess_message(state,m,config,context,runtime=runtime) if config is not None else result(['config','runtime_unknown'])
        if readiness['state'] in ('blocked','unknown'):
            blocked[m['campaign_id'] or ''].append((m,readiness))
    for cid,rows in pending.items():
        tasks.append({'key':'approval:'+cid,'kind':'approval','campaign_id':cid,'campaign_name':rows[0]['campaign_name'] or '', 'count':len(rows),'message_id':rows[0]['id']})
    for cid,rows in blocked.items():
        reasons={r['code']:r for _,readiness in rows for r in readiness['reasons'] if r['code'] not in ('scheduled','spacing','predecessor','approval','cap','quiet')}
        tasks.append({'key':'blocked:'+cid,'kind':'blocked','campaign_id':cid,'campaign_name':rows[0][0]['campaign_name'] or '',
            'count':len(rows),'message_id':rows[0][0]['id'],'reasons':list(reasons.values())})
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        rows=await (await db.execute("SELECT o.*,c.name AS campaign_name FROM opportunities o LEFT JOIN campaigns c ON c.id=o.campaign_id WHERE o.stage NOT IN ('won','lost') AND o.next_due!='' AND o.next_due<=date('now') ORDER BY o.next_due,o.id")).fetchall()
    for row in rows:
        tasks.append({'key':'opportunity:'+row['id'],'kind':'opportunity','opportunity_id':row['id'],'campaign_id':row['campaign_id'],'campaign_name':row['campaign_name'] or '', 'name':row['title'],'next_action':row['next_action'],'next_due':row['next_due'],'owner':row['owner']})
    return {'items':tasks,'total':len(tasks),'checked_at':datetime.now(timezone.utc).isoformat()}


def install_work_routes(app,state_factory,assessment_factory):
    async def current():
        sm=state_factory();await sm.init_db();return await work_items(sm,await assessment_factory(sm))
    @app.get('/api/work-items')
    async def listing(page:int=1):
        if page<1:return JSONResponse({'error':'Invalid page'},status_code=422)
        data=await current();pages=max(1,(data['total']+29)//30);page=min(page,pages)
        return dict(data,items=data['items'][(page-1)*30:page*30],page=page,pages=pages)
    @app.get('/api/work-items/{key}')
    async def item(key:str):
        data=await current()
        found=next((x for x in data['items'] if x['key']==key),None)
        return found if found else JSONResponse({'error':'This task is already resolved or changed.'},status_code=410)
