"""Saved signal criteria and conservative, evidence-linked company classification."""
import json
import uuid
import math
from datetime import datetime, timezone, timedelta
import aiosqlite
from fastapi import Request
from fastapi.responses import JSONResponse


def validate_profile(payload, signals):
    if not isinstance(payload,dict):
        raise ValueError('Invalid target profile')
    name=payload.get('name','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=120:
        raise ValueError('Enter a profile name (1–120 characters)')
    result={'name':name.strip()}
    for key in ('require','exclude'):
        values=payload.get(key,[])
        if not isinstance(values,list) or len(values)>100 or any(not isinstance(v,str) or v not in signals for v in values):
            raise ValueError('Choose known signals')
        result[key]=sorted(set(values))
    if not (result['require'] or result['exclude']) or set(result['require'])&set(result['exclude']):
        raise ValueError('Choose distinct required or excluded signals')
    days=payload.get('max_age_days',90)
    if type(days) is not int or not 1<=days<=365:
        raise ValueError('Evidence age must be between 1 and 365 days')
    result['max_age_days']=days
    return result


async def get_profile(state, profile_id):
    async with state._connect() as db:
        row=await (await db.execute('SELECT criteria_json FROM target_profiles WHERE id=?',(profile_id,))).fetchone()
    if not row:
        raise ValueError('Target profile not found')
    return dict(json.loads(row[0]),id=profile_id)


async def evaluate_profile(state, profile, company_ids=None, page=1, verdict='all'):
    """No absence-as-false inference. All inventory counts, paginated evidence."""
    now=datetime.now(timezone.utc)
    async with state._connect() as db:
        db.row_factory=aiosqlite.Row
        signals={r['code']:dict(r) for r in await (await db.execute('SELECT * FROM signal_codes')).fetchall()}
        companies=[dict(r) for r in await (await db.execute('SELECT id,name FROM companies WHERE removed_at IS NULL ORDER BY name,id')).fetchall()]
        if company_ids is not None:
            chosen=set(company_ids);companies=[c for c in companies if c['id'] in chosen]
        # Latest recorded evidence, not a capped historical sample. Unknown latest
        # evidence must not fall back to an older positive finding.
        codes=profile['require']+profile['exclude']
        slots=','.join('?' for _ in codes)
        rows=await (await db.execute(f'''SELECT * FROM (SELECT o.*,ROW_NUMBER() OVER
            (PARTITION BY company_id,signal_code ORDER BY (julianday(observed_at) IS NULL) DESC,julianday(observed_at) DESC,rowid DESC) AS rn
            FROM observations o WHERE signal_code IN ({slots})) WHERE rn=1''',codes)).fetchall()
    facts={(r['company_id'],r['signal_code']):dict(r) for r in rows}
    counts={'match':0,'no_match':0,'unknown':0};items=[]
    for company in companies:
        evidence=[]
        for kind in ('require','exclude'):
            for code in profile[kind]:
                signal=signals.get(code,{});fact=facts.get((company['id'],code))
                reason='missing';present=None
                if signal.get('status')!='confirmed':
                    reason='inactive_signal'
                elif fact:
                    try:
                        observed=datetime.fromisoformat(fact['observed_at'].replace('Z','+00:00'))
                        if observed.tzinfo is None:observed=observed.replace(tzinfo=timezone.utc)
                        fresh=now-timedelta(days=profile['max_age_days'])<=observed<=now+timedelta(minutes=5)
                    except (ValueError,TypeError):fresh=False
                    if not fresh:reason='stale'
                    elif fact['confidence'] is None or not math.isfinite(fact['confidence']) or fact['confidence']<signal.get('confidence_floor',0):reason='low_confidence'
                    elif signal.get('value_type')=='bool':
                        present={0:False,1:True}.get(fact['value_num']);reason='observed' if present is not None else 'unknown_value'
                    else:
                        present=True if fact['value_num'] is not None or (fact['value_text'] or '').strip() else None
                        reason='observed' if present else 'unknown_value'
                satisfied=present if kind=='require' else (not present if present is not None else None)
                evidence.append({'code':code,'rule':kind,'satisfied':satisfied,'reason':reason,
                    'collector':signal.get('collector',''),'stage':'listing' if signal.get('collector')=='discover' else 'after_import',
                    'value_num':fact['value_num'] if fact else None,'value_text':fact['value_text'] if fact else '',
                    'source':fact['evidence_url'] if fact else '', 'observed_at':fact['observed_at'] if fact else '',
                    'confidence':fact['confidence'] if fact else None})
        values=[e['satisfied'] for e in evidence]
        outcome='no_match' if False in values else 'unknown' if None in values else 'match'
        counts[outcome]+=1
        if verdict=='all' or outcome==verdict:items.append(dict(company,verdict=outcome,evidence=evidence))
    total=len(items);pages=max(1,(total+29)//30);page=min(page,pages)
    return {'profile':profile,'counts':counts,'total':total,'page':page,'pages':pages,
        'items':items[(page-1)*30:page*30],'checked_at':now.isoformat(),'stage':'after_import',
        'policy':'retain_all','scope':'inventory' if company_ids is None else 'search_run'}


def install_target_profile_routes(app,state_factory):
    async def state():
        sm=state_factory();await sm.init_db();return sm

    @app.get('/api/target-profiles')
    async def profiles():
        sm=await state()
        async with sm._connect() as db:
            rows=await (await db.execute('SELECT id,criteria_json FROM target_profiles ORDER BY name')).fetchall()
        return [dict(json.loads(r[1]),id=r[0]) for r in rows]

    @app.post('/api/target-profiles')
    async def save(request:Request):
        try:
            sm=await state()
            async with sm._connect() as db:
                signals={r[0] for r in await (await db.execute('SELECT code FROM signal_codes')).fetchall()}
                profile=validate_profile(await request.json(),signals);pid=uuid.uuid4().hex
                await db.execute('INSERT INTO target_profiles(id,name,criteria_json) VALUES (?,?,?)',(pid,profile['name'],json.dumps(profile)))
                await db.commit()
            return dict(profile,id=pid)
        except (ValueError,TypeError):return JSONResponse({'error':'Invalid target profile. Check name, signals and evidence age.'},status_code=422)

    @app.delete('/api/target-profiles/{profile_id}')
    async def delete(profile_id:str):
        sm=await state()
        async with sm._connect() as db:
            await db.execute('DELETE FROM target_profiles WHERE id=?',(profile_id,));await db.commit()
        return {'deleted':True}

    @app.get('/api/target-profiles/{profile_id}/evaluate')
    async def evaluate(profile_id:str,page:int=1,verdict:str='all'):
        if page<1 or verdict not in ('all','match','no_match','unknown'):
            return JSONResponse({'error':'Invalid result filter'},status_code=422)
        try:
            sm=await state();profile=await get_profile(sm,profile_id)
            return await evaluate_profile(sm,profile,page=page,verdict=verdict)
        except ValueError:return JSONResponse({'error':'Target profile not found'},status_code=404)
