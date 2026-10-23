"""Independent OpenOutFind-inspired role qualification; no GPL code/dependency.

Official-site evidence only. A matching title is a review hint, never proof of
purchasing authority, personal identity, mailbox validity or outreach consent.
"""
import json
import hashlib
import re

import aiosqlite
from fastapi import Request
from fastapi.responses import JSONResponse

ROLES = {
    'management': ('Geschäftsführung / Inhaber', 'Management / owner', r'\b(geschäftsführ\w*|geschaeftsfuehr\w*|inhaber\w*|vorstand\w*|gründer\w*|gruender\w*|ceo|cfo|cto|cio|coo|cmo|chief\b.{0,40}\bofficer|owner|founder|managing director|geschäftsleit\w*)\b'),
    'sales': ('Vertriebsleitung', 'Sales leadership', r'\b(vertriebsleit\w*|verkaufsleit\w*|sales director|sales manager|head of sales|vp.{0,10}sales|chief revenue officer|cro)\b'),
    'marketing': ('Marketingleitung', 'Marketing leadership', r'\b(marketingleit\w*|marketing director|marketing manager|head of marketing|cmo|chief marketing officer)\b'),
    'it': ('IT / Technikleitung', 'IT / engineering leadership', r'\b(it[- ]?leit\w*|technikleit\w*|technisch\w* leit\w*|cto|cio|head of (?:it|engineering|technology)|(?:it|engineering|technology) (?:director|manager)|chief (?:technology|information) officer)\b'),
    'hr': ('Personalleitung', 'HR leadership', r'\b(personalleit\w*|hr[- ]?leit\w*|head of (?:hr|people|human resources)|(?:hr|human resources) (?:director|manager)|chief people officer)\b'),
    'finance': ('Finanzleitung', 'Finance leadership', r'\b(finanzleit\w*|kaufmännisch\w* leit\w*|cfo|head of finance|finance (?:director|manager)|chief financial officer)\b'),
    'purchasing': ('Einkaufsleitung', 'Purchasing leadership', r'\b(einkaufsleit\w*|head of (?:procurement|purchasing)|(?:procurement|purchasing) (?:director|manager))\b'),
    'operations': ('Betriebsleitung', 'Operations leadership', r'\b(betriebsleit\w*|produktionsleit\w*|coo|head of operations|operations (?:director|manager)|chief operating officer)\b'),
}
_NEGATIVE = re.compile(r'\b(assist(?:ant|enz|ent\w*)|intern|praktik\w*|student\w*|ehemalig\w*|former|retired)\b', re.I)


CANDIDATE_FIELDS=('company_id','first_name','last_name','title','email','phone','source_url','found_at')

def fingerprint(person):
    return hashlib.sha256(json.dumps([person[k] for k in CANDIDATE_FIELDS],ensure_ascii=False).encode()).hexdigest()

def criteria(payload):
    if not isinstance(payload, dict) or set(payload)-{'roles'}:
        raise ValueError('Invalid criteria')
    roles=payload.get('roles', ['management'])
    if not isinstance(roles,list) or not 1<=len(roles)<=len(ROLES) or any(not isinstance(r,str) or r not in ROLES for r in roles):
        raise ValueError('Choose supported roles')
    return {'roles':sorted(set(roles))}


def qualify(title, chosen):
    title=(title or '').strip()
    matches=[key for key in chosen['roles'] if re.search(ROLES[key][2],title,re.I)]
    if _NEGATIVE.search(title):
        return {'verdict':'no_match','roles':[], 'reason':'non_current_or_support_role','title':title}
    if matches:
        return {'verdict':'match','roles':matches,'reason':'published_title_matches','title':title}
    return {'verdict':'unknown','roles':[], 'reason':'role_not_established','title':title}


async def qualify_job(state, job_id, company_id, candidate_ids, chosen):
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        for cid in candidate_ids:
            row=await (await db.execute("SELECT * FROM person_candidates WHERE id=? AND company_id=? AND status='pending'",(cid,company_id))).fetchone()
            if not row:continue
            fit=qualify(row['title'],chosen)
            await db.execute('''INSERT INTO decision_maker_results(job_id,candidate_id,verdict,fit_json,evidence_at,candidate_json)
                VALUES (?,?,?,?,?,?) ON CONFLICT(job_id,candidate_id) DO UPDATE SET verdict=excluded.verdict,fit_json=excluded.fit_json,evidence_at=excluded.evidence_at,candidate_json=excluded.candidate_json''',
                (job_id,cid,fit['verdict'],json.dumps(fit),row['found_at'],json.dumps(dict(row))))
        await db.commit()


def install_decision_maker_routes(app,state_factory, jobs_factory):
    @app.get('/api/decision-makers/latest')
    async def latest():
        sm=state_factory();await sm.init_db()
        async with sm._connect() as db:
            row=await (await db.execute("SELECT id FROM company_people_jobs WHERE criteria_json != '' ORDER BY created_at DESC,rowid DESC LIMIT 1")).fetchone()
        return await jobs_factory().snapshot(row[0]) if row else None

    @app.get('/api/decision-makers/jobs/{job_id}')
    async def snapshot(job_id:str):
        job=await jobs_factory().snapshot(job_id)
        if not job or not job.get('criteria_json'):return JSONResponse({'error':'job_not_found'},status_code=404)
        return job

    @app.get('/api/decision-makers/roles')
    async def roles():
        return [{'id':key,'de':v[0],'en':v[1]} for key,v in ROLES.items()]

    @app.get('/api/decision-makers/results')
    async def results(job_id:str, page:int=1, verdict:str='match'):
        if page<1 or verdict not in ('match','unknown','no_match','all'):
            return JSONResponse({'error':'invalid_filter'},status_code=422)
        sm=state_factory();await sm.init_db()
        async with sm._connect() as db:
            db.row_factory=aiosqlite.Row
            job=await (await db.execute('SELECT criteria_json FROM company_people_jobs WHERE id=?',(job_id,))).fetchone()
            if not job or not job[0]:return JSONResponse({'error':'job_not_found'},status_code=404)
            where="r.job_id=? AND c.removed_at IS NULL AND p.status='pending'"
            counts={key:0 for key in ('match','unknown','no_match')}
            for row in await (await db.execute('SELECT r.verdict,COUNT(*) FROM decision_maker_results r JOIN person_candidates p ON p.id=r.candidate_id JOIN companies c ON c.id=p.company_id WHERE '+where+' GROUP BY r.verdict',(job_id,))).fetchall():counts[row[0]]=row[1]
            args=[job_id]
            if verdict!='all':where+=' AND r.verdict=?';args.append(verdict)
            total=sum(counts.values()) if verdict=='all' else counts[verdict]
            pages=max(1,(total+19)//20);page=min(page,pages)
            rows=await (await db.execute('''SELECT p.*,c.name AS company,r.fit_json,r.evidence_at,r.candidate_json FROM decision_maker_results r
                JOIN person_candidates p ON p.id=r.candidate_id JOIN companies c ON c.id=p.company_id WHERE '''+where+' ORDER BY c.name,p.last_name,p.id LIMIT 20 OFFSET ?',(*args,(page-1)*20))).fetchall()
        return {'criteria':json.loads(job[0]),'counts':counts,'total':total,'page':page,'pages':pages,
            'items':[dict(json.loads(r['candidate_json']),company=r['company'],fit=json.loads(r['fit_json']),snapshot_changed=fingerprint(r)!=fingerprint(json.loads(r['candidate_json']))) for r in rows]}

    @app.post('/api/decision-makers/adopt')
    async def adopt(request:Request):
        try:
            body=await request.json();ids=body.get('candidate_ids');job=body.get('job_id')
            if body.get('reviewed') is not True or not isinstance(job,str) or not isinstance(ids,list) or not 1<=len(ids)<=100 or any(not isinstance(v,str) or not 1<=len(v)<=100 for v in ids):raise ValueError()
        except (ValueError,TypeError,AttributeError):return JSONResponse({'error':'invalid_selection'},status_code=422)
        from harvey.contacts import create_contact,ContactError
        sm=state_factory();await sm.init_db();out=[]
        for cid in dict.fromkeys(ids):
            async with sm._connect() as db:
                db.row_factory=aiosqlite.Row
                row=await (await db.execute('''SELECT p.*,r.candidate_json FROM person_candidates p JOIN decision_maker_results r ON r.candidate_id=p.id
                    JOIN companies c ON c.id=p.company_id WHERE p.id=? AND r.job_id=? AND c.removed_at IS NULL''',(cid,job))).fetchone()
            if not row:out.append({'candidate_id':cid,'status':'unavailable'});continue
            snapshot=json.loads(row['candidate_json'])
            payload={key:snapshot[key] for key in ('company_id','first_name','last_name','title','email','phone')}
            payload['_candidate_snapshot']=fingerprint(snapshot)
            try:
                contact=await create_contact(sm,payload,candidate_id=cid)
                out.append({'candidate_id':cid,'status':'duplicate' if contact['duplicate'] else 'created','contact_id':contact['id']})
            except ContactError:
                out.append({'candidate_id':cid,'status':'review_required'})
        return {'items':out}
