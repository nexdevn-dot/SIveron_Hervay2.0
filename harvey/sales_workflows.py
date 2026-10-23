"""Reusable drafts and explicit local opportunities. No automated acceptance or delivery."""
import json
import uuid
from datetime import date
import aiosqlite
from fastapi import Request
from fastapi.responses import JSONResponse
from harvey.crm import campaign_payload,save_campaign_draft
from harvey.contacts import ContactError
from harvey.campaign_results import incoming

STAGES={'new','qualified','proposal','negotiation','won','lost'}


def search_recipe(data):
    if not isinstance(data,dict):raise ValueError()
    result={}
    for key in ('terms','cities'):
        rows=data.get(key,[])
        if not isinstance(rows,list) or len(rows)>50 or any(not isinstance(x,str) or not x.strip() or len(x)>200 for x in rows):raise ValueError()
        result[key]=list(dict.fromkeys(x.strip() for x in rows))
    provider=data.get('provider','osm')
    if provider not in ('osm','geoapify','serpapi','google_maps','dataforseo_listings','dataforseo_serp','serper'):raise ValueError()
    radius=data.get('radius_km',40)
    if type(radius) is not int or radius not in (10,25,40,75,100,200):raise ValueError()
    result.update(provider=provider,radius_km=radius)
    for key,default in [('depth',30),('limit',100)]:
        value=data.get(key,default)
        if type(value) is not int or not 1<=value<=1000:raise ValueError()
        result[key]=value
    for key,values,default in [('maps_mode',('quick','grid'),'quick'),('maps_filter',('all','website','no_website','phone'),'all'),('email_mode',('quick','thorough'),'quick')]:
        value=data.get(key,default)
        if value not in values:raise ValueError()
        result[key]=value
    return result


def opportunity_values(data):
    if not isinstance(data,dict):raise ValueError()
    result={}
    for key,limit in [('title',200),('owner',120),('next_action',1000),('note',4000)]:
        value=data.get(key,'')
        if not isinstance(value,str) or len(value)>limit:raise ValueError()
        result[key]=value.strip()
    result['stage']=data.get('stage','new')
    if result['stage'] not in STAGES or not result['title']:raise ValueError()
    due=data.get('next_due','')
    if not isinstance(due,str) or (due and (len(due)!=10 or date.fromisoformat(due).isoformat()!=due)):raise ValueError()
    if result['stage'] not in ('won','lost') and (not result['next_action'] or not due):raise ValueError()
    result['next_due']=due
    return result


async def get_opportunity(state,oid):
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        row=await (await db.execute('''SELECT o.*,p.first_name,p.last_name,p.email,p.company,p.do_not_contact,p.status AS contact_status,
            c.name AS campaign_name,EXISTS(SELECT 1 FROM contact_trash t WHERE t.prospect_id=o.prospect_id) AS contact_deleted
            FROM opportunities o LEFT JOIN prospects p ON p.id=o.prospect_id LEFT JOIN campaigns c ON c.id=o.campaign_id WHERE o.id=?''',(oid,))).fetchone()
        if not row:raise LookupError()
        result=dict(row)
        result['sources']=[dict(r) for r in await (await db.execute('SELECT * FROM opportunity_conversations WHERE opportunity_id=? ORDER BY created_at,conversation_id',(oid,))).fetchall()]
    return result


def install_sales_routes(app,state_factory):
    async def state():
        sm=state_factory();await sm.init_db();return sm

    @app.get('/api/workflow-templates')
    async def templates():
        sm=await state()
        async with sm._connect() as db:
            rows=await (await db.execute('SELECT id,name,payload_json FROM workflow_templates ORDER BY name,id')).fetchall()
        return [dict(json.loads(payload),id=tid,name=name) for tid,name,payload in rows]

    @app.post('/api/workflow-templates')
    async def template_save(request:Request):
        try:
            data=await request.json()
            if not isinstance(data,dict) or not isinstance(data.get('name'),str) or not 1<=len(data['name'].strip())<=120:raise ValueError()
            if not isinstance(data.get('campaign_id'),str) or len(data['campaign_id'])>100 or type(data.get('revision')) is not int:raise ValueError()
            raw_search=data.get('search',{})
            if not isinstance(raw_search,dict):raise ValueError()
            search=search_recipe(raw_search) if raw_search else None
            profile=data.get('target_profile_id','')
            if not isinstance(profile,str) or len(profile)>100:raise ValueError()
            sm=await state()
            async with sm._connect() as db:
                db.row_factory=aiosqlite.Row;await db.execute('BEGIN IMMEDIATE')
                row=await (await db.execute('SELECT * FROM campaigns WHERE id=?',(data.get('campaign_id'),))).fetchone()
                if not row or data.get('revision')!=row['revision']:raise ValueError()
                if profile and not await (await db.execute('SELECT 1 FROM target_profiles WHERE id=?',(profile,))).fetchone():raise ValueError()
                sequence=json.loads(row['sequence_json'] or '[]')
                # Attachments and private sender fields are deliberately omitted.
                sequence=[{k:s[k] for k in ('subject','body','body_doc','delay_days') if k in s} for s in sequence]
                brief=json.loads(row['brief_json'] or '{}')
                _,_,sequence,brief=campaign_payload({'name':data['name'],'sequence':sequence,'brief':{k:brief.get(k,'') for k in ('audience','offer','goal')}})
                brief={k:brief[k] for k in ('audience','offer','goal')}
                if not sequence:raise ValueError()
                payload={'sequence':sequence,'brief':brief,'search':search,'target_profile_id':profile}
                tid=uuid.uuid4().hex
                await db.execute('INSERT INTO workflow_templates(id,name,payload_json) VALUES (?,?,?)',(tid,data['name'].strip(),json.dumps(payload)));await db.commit()
            return {'id':tid}
        except (ValueError,TypeError,ContactError):return JSONResponse({'error':'Template could not be saved. Save the draft and check name, profile and search criteria.'},status_code=422)

    @app.delete('/api/workflow-templates/{tid}')
    async def template_delete(tid:str):
        sm=await state()
        async with sm._connect() as db:
            await db.execute('DELETE FROM workflow_templates WHERE id=?',(tid,));await db.commit()
        return {'deleted':True}

    @app.post('/api/workflow-templates/{tid}/instantiate')
    async def template_use(tid:str,request:Request):
        try:
            data=await request.json()
            if not isinstance(data,dict):raise ValueError()
            sm=await state()
            async with sm._connect() as db:
                row=await (await db.execute('SELECT payload_json FROM workflow_templates WHERE id=?',(tid,))).fetchone()
                if not row:raise ValueError()
                payload=json.loads(row[0]);profile=payload.get('target_profile_id','')
                missing=bool(profile and not await (await db.execute('SELECT 1 FROM target_profiles WHERE id=?',(profile,))).fetchone())
            result=await save_campaign_draft(sm,{'name':data.get('name'),'prospect_ids':[],'sequence':payload['sequence'],'brief':payload['brief']})
            return dict(result,search=payload['search'],target_profile_id=profile,target_profile_missing=missing)
        except (ValueError,TypeError,ContactError):return JSONResponse({'error':'Template unavailable or campaign name invalid.'},status_code=422)

    @app.get('/api/opportunities')
    async def opportunities(page:int=1,stage:str='',prospect_id:str=''):
        if page<1 or stage and stage not in STAGES or len(prospect_id)>100:return JSONResponse({'error':'Invalid opportunity filter'},status_code=422)
        sm=await state();where=[];params=[]
        if stage:where.append('o.stage=?');params.append(stage)
        if prospect_id:where.append('o.prospect_id=?');params.append(prospect_id)
        clause=' WHERE '+' AND '.join(where) if where else ''
        async with sm._connect() as db:
            db.row_factory=aiosqlite.Row
            total=(await (await db.execute('SELECT COUNT(*) FROM opportunities o'+clause,params)).fetchone())[0]
            pages=max(1,(total+29)//30);page=min(page,pages)
            rows=await (await db.execute('SELECT o.*,c.name AS campaign_name FROM opportunities o LEFT JOIN campaigns c ON o.campaign_id=c.id'+clause+' ORDER BY o.next_due,o.id LIMIT 30 OFFSET ?',params+[(page-1)*30])).fetchall()
        return {'items':[dict(r) for r in rows],'total':total,'page':page,'pages':pages}

    @app.get('/api/opportunities/{oid}')
    async def opportunity_detail(oid:str):
        try:return await get_opportunity(await state(),oid)
        except LookupError:return JSONResponse({'error':'Opportunity unavailable'},status_code=404)

    @app.post('/api/conversations/{conversation_id}/opportunity')
    async def opportunity_create(conversation_id:str,request:Request):
        try:
            data=await request.json()
            if not isinstance(data,dict) or data.get('interest_confirmed') is not True:raise ValueError()
            link=data.get('link_id','')
            if not isinstance(link,str) or len(link)>100:raise ValueError()
            values=opportunity_values(data) if not link else None
            sm=await state()
            async with sm._connect() as db:
                db.row_factory=aiosqlite.Row;await db.execute('BEGIN IMMEDIATE')
                c=await (await db.execute('SELECT * FROM conversations WHERE id=?',(conversation_id,))).fetchone()
                if not c or not incoming(c['thread_json']) or not await (await db.execute('SELECT 1 FROM prospects WHERE id=?',(c['prospect_id'],))).fetchone() or await (await db.execute('SELECT 1 FROM contact_trash WHERE prospect_id=?',(c['prospect_id'],))).fetchone():raise ValueError()
                existing=await (await db.execute('SELECT opportunity_id FROM opportunity_conversations WHERE conversation_id=?',(conversation_id,))).fetchone()
                if existing:return {'id':existing[0],'already_linked':True}
                oid=link or uuid.uuid4().hex
                if link:
                    old=await (await db.execute('SELECT prospect_id FROM opportunities WHERE id=?',(link,))).fetchone()
                    if not old or old[0]!=c['prospect_id']:raise ValueError()
                else:
                    await db.execute('''INSERT INTO opportunities(id,prospect_id,campaign_id,title,stage,owner,next_action,next_due,note)
                        VALUES (?,?,?,?,?,?,?,?,?)''',(oid,c['prospect_id'],c['campaign_id'],*[values[k] for k in ('title','stage','owner','next_action','next_due','note')]))
                await db.execute('INSERT INTO opportunity_conversations(opportunity_id,conversation_id,campaign_id) VALUES (?,?,?)',(oid,conversation_id,c['campaign_id']));await db.commit()
            return {'id':oid}
        except (ValueError,TypeError):return JSONResponse({'error':'Review interest explicitly, select the same contact and enter a title, stage and next task/date.'},status_code=422)

    @app.patch('/api/opportunities/{oid}')
    async def opportunity_update(oid:str,request:Request):
        try:
            data=await request.json();values=opportunity_values(data)
            if type(data.get('revision')) is not int:raise ValueError()
            sm=await state()
            async with sm._connect() as db:
                await db.execute('BEGIN IMMEDIATE')
                cursor=await db.execute('''UPDATE opportunities SET title=?,stage=?,owner=?,next_action=?,next_due=?,note=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP
                    WHERE id=? AND revision=?''',(*[values[k] for k in ('title','stage','owner','next_action','next_due','note')],oid,data['revision']))
                if cursor.rowcount!=1:raise ValueError()
                await db.commit()
            return {'id':oid}
        except (ValueError,TypeError):return JSONResponse({'error':'Opportunity changed or entries invalid. Reload before saving.'},status_code=409)
