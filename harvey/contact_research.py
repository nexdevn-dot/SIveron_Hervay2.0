"""Contact-scoped evidence search. No guessing, login automation, model or sending.

Independent multi-source adapter design; PyHunter/theHarvester are references,
not runtime dependencies. Optional Hunter Finder is a provider suggestion.
"""
import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, urlsplit, urlunsplit, parse_qs, urlencode

import aiosqlite
import httpx
from bs4 import BeautifulSoup
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError
from typing import Literal

from harvey.collectors.company_contacts import (_public_company_url, contact_page_links,
    extract_public_emails, mailbox_kind, social_profile_links)
from harvey.collectors.people import extract_people
from harvey.collectors.public_pages import PublicPageReader, public_site_domain
from harvey.email_checks import normalize_public_email, email_checks


class ResearchSettings(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    enabled: StrictBool=True
    website: StrictBool=True
    web: StrictBool=True
    profiles: StrictBool=True
    hunter: StrictBool=False
    provider: Literal['serpapi','serper']='serpapi'
    mode: Literal['quick','thorough']='quick'
    max_queries: StrictInt=Field(default=4,ge=1,le=6)
    max_pages: StrictInt=Field(default=8,ge=1,le=12)
    monthly_searches: StrictInt=Field(default=50,ge=0,le=10000)
    hunter_monthly: StrictInt=Field(default=5,ge=0,le=1000)


def now():return datetime.now(timezone.utc).isoformat()
def clean_url(url):
    try:
        p=urlsplit(url)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.port not in (None,80,443):return ''
        query=''
        if p.hostname.removeprefix('www.')=='facebook.com' and p.path=='/profile.php':
            value=parse_qs(p.query).get('id',[''])[0]
            if value.isdigit():query=urlencode({'id':value})
        return urlunsplit((p.scheme,p.netloc,p.path,query,''))[:2000]
    except (ValueError,TypeError):return ''

def norm(text):return ' '.join(re.findall(r'[^\W_]+',str(text).casefold()))

SNAPSHOT_FIELDS=('id','revision','company_id','contact_type','first_name','last_name','title','email','phone')
def contact_fingerprint(contact):
    return hashlib.sha256(json.dumps([contact.get(k) for k in SNAPSHOT_FIELDS],ensure_ascii=False).encode()).hexdigest()


async def settings(sm):
    raw=await sm.get_setting('contact_research_settings','')
    return ResearchSettings.model_validate_json(raw) if raw else ResearchSettings()


async def get_contact(sm,cid):
    async with sm._connect() as db:
        db.row_factory=aiosqlite.Row
        row=await (await db.execute('''SELECT p.*,c.domain,c.website,c.location,c.removed_at,
            EXISTS(SELECT 1 FROM contact_trash t WHERE t.prospect_id=p.id) AS trashed,
            EXISTS(SELECT 1 FROM contact_suppressions s WHERE s.prospect_id=p.id OR (p.email!='' AND s.email=lower(p.email))) AS suppressed
            FROM prospects p LEFT JOIN companies c ON c.id=p.company_id WHERE p.id=?''',(cid,))).fetchone()
    if not row or row['trashed'] or row['removed_at']:raise ValueError('contact_unavailable')
    return dict(row)


def blocked(contact):return bool(contact['do_not_contact'] or contact['suppressed'] or contact['status']=='opted_out')


def classify_page(html,url,contact):
    """Only explicit name/email entities establish personal association."""
    domain=(contact.get('domain') or public_site_domain(contact.get('website') or '')).lower().removeprefix('www.')
    official=public_site_domain(url)==domain and bool(domain)
    text=norm(BeautifulSoup(html,'html.parser').get_text(' ',strip=True))
    company=norm(contact.get('company'))
    context=official or (len(company)>=4 and company in text) or (domain and domain in html.lower())
    personal=set()
    if context and contact['contact_type']=='person':
        for p in extract_people(html,url,domain):
            if norm(p['first_name'])==norm(contact['first_name']) and norm(p['last_name'])==norm(contact['last_name']) and p['email']:
                personal.add(p['email'])
    out=[]
    for email in extract_public_emails(html,url):
        if email in personal:kind='person_explicit'
        elif mailbox_kind(email)=='role' and context and email.rsplit('@',1)[-1]==domain:kind='company_mailbox'
        else:kind='unclear'
        out.append({'email':email,'kind':kind,'source_url':clean_url(url),'method':'published_page'})
    return out


async def web_search(sm,prefs,query):
    live=await settings(sm)
    if not live.enabled:raise ValueError('research_disabled')
    from harvey.collectors.discover import PROVIDERS,DiscoveryQuery
    from harvey.collectors.discovery_quota import reserve_quota
    key=os.getenv('SERPAPI_API_KEY' if prefs.provider=='serpapi' else 'SERPER_API_KEY','').strip()
    if not key:raise ValueError('search_key_missing')
    period=datetime.now(timezone.utc).strftime('%Y-%m')
    if not await sm.reserve_setting('contact_research:web:'+period,1,min(prefs.monthly_searches,live.monthly_searches)):raise ValueError('search_budget_exhausted')
    if prefs.provider=='serpapi' and not await reserve_quota(sm,'serpapi',1):raise ValueError('provider_budget_exhausted')
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
        rows=await PROVIDERS[prefs.provider].fetch(client,{prefs.provider+'_api_key':key},DiscoveryQuery(term=query,depth=10,limit=10))
    return [row.source_url or row.website for row in rows][:10]


async def hunter_search(sm,prefs,contact):
    live=await settings(sm)
    if not live.enabled or not live.hunter:raise ValueError('hunter_disabled')
    domain=(contact.get('domain') or public_site_domain(contact.get('website') or '')).lower().removeprefix('www.')
    if contact['contact_type']!='person' or not domain:raise ValueError('hunter_needs_person_domain')
    key=os.getenv('HUNTER_API_KEY','').strip()
    if not key:raise ValueError('hunter_key_missing')
    period=datetime.now(timezone.utc).strftime('%Y-%m')
    if not await sm.reserve_setting('contact_research:hunter:'+period,1,min(prefs.hunter_monthly,live.hunter_monthly)):raise ValueError('hunter_budget_exhausted')
    async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
        response=await client.get('https://api.hunter.io/v2/email-finder/found',headers={'X-API-KEY':key},params={'domain':domain,'first_name':contact['first_name'],'last_name':contact['last_name'],'max_duration':10})
        response.raise_for_status();data=response.json().get('data') or {}
    email=normalize_public_email(data.get('email',''))
    if not email:return []
    # Provider confidence/verification is never imported as our verification.
    source=next((clean_url(s.get('uri','')) for s in data.get('sources',[]) if isinstance(s,dict) and clean_url(s.get('uri',''))),'')
    return [{'email':email,'kind':'provider_suggestion','source_url':source,'method':'hunter_finder'}]


class ResearchService:
    def __init__(self,sm):self.sm=sm;self.tasks={}

    async def create(self,cid,payload):
        prefs=await settings(self.sm)
        if not prefs.enabled:raise ValueError('research_disabled')
        contact=await get_contact(self.sm,cid)
        if blocked(contact):raise ValueError('contact_blocked')
        if not isinstance(payload,dict) or set(payload)-{'sources','mode'}:raise ValueError('invalid_request')
        sources=payload.get('sources');mode=payload.get('mode',prefs.mode)
        if not isinstance(sources,list) or not sources or len(sources)>4 or any(not isinstance(s,str) or s not in ('website','web','profiles','hunter') or not getattr(prefs,s) for s in sources) or mode not in ('quick','thorough'):raise ValueError('invalid_sources')
        chosen=sorted(set(sources));jid=uuid.uuid4().hex
        async with self.sm._connect() as db:
            await db.execute('BEGIN IMMEDIATE')
            # Unknown runs from an old process never silently resume paid calls.
            for row in await (await db.execute("SELECT id FROM contact_email_research WHERE status='running'")).fetchall():
                if row[0] not in self.tasks:await db.execute("UPDATE contact_email_research SET status='interrupted' WHERE id=?",(row[0],))
            if await (await db.execute("SELECT 1 FROM contact_email_research WHERE status='running'")).fetchone():raise ValueError('research_busy')
            config=dict(prefs.model_dump(),sources=chosen,mode=mode)
            await db.execute('''INSERT INTO contact_email_research(id,contact_id,status,config_json,snapshot_json)
                VALUES (?,?,'running',?,?)''',(jid,cid,json.dumps(config),json.dumps(contact)))
            await db.commit()
        self.tasks[jid]=asyncio.create_task(self.run(jid,contact,prefs,chosen,mode))
        return jid

    async def stopped(self,jid):
        async with self.sm._connect() as db:
            row=await (await db.execute('SELECT stop_requested,contact_id FROM contact_email_research WHERE id=?',(jid,))).fetchone()
        if not row or bool(row[0]) or not (await settings(self.sm)).enabled:return True
        try:return blocked(await get_contact(self.sm,row[1]))
        except ValueError:return True

    async def add(self,jid,found):
        async with self.sm._connect() as db:
            for row in found:
                if not normalize_public_email(row.get('email','')):continue
                key=hashlib.sha256((jid+'\0'+row['email']+'\0'+row['source_url']+'\0'+row['kind']).encode()).hexdigest()[:32]
                await db.execute('''INSERT OR IGNORE INTO contact_email_findings(id,job_id,email,kind,source_url,method)
                    VALUES (?,?,?,?,?,?)''',(key,jid,row['email'],row['kind'],row['source_url'],row['method']))
            await db.commit()

    async def run(self,jid,contact,prefs,sources,mode):
        diagnostics=[];links=[];visited=set();queries=0;personal_found=False
        async def notice(code):
            if code not in diagnostics:diagnostics.append(code)
            async with self.sm._connect() as db:
                await db.execute('UPDATE contact_email_research SET diagnostics_json=? WHERE id=?',(json.dumps(diagnostics[-30:]),jid));await db.commit()
        async def add_page(url,official=False):
            nonlocal personal_found
            if await self.stopped(jid) or mode=='quick' and personal_found:return ''
            if len(visited)>=prefs.max_pages:
                await notice('page_limit');return ''
            url=clean_url(url)
            if not url or url in visited:return ''
            visited.add(url);host=public_site_domain(url)
            async def guard(target):
                # Keep redirects on this observed host, re-check all DNS addresses.
                return await _public_company_url(target,host)
            async with httpx.AsyncClient(timeout=6,follow_redirects=False,headers={'User-Agent':'Siveron public contact research'}) as client:
                page=await PublicPageReader(client,guard,timeout=8).read(url)
            if not page.html:
                await notice('public_page_unavailable');links.append({'url':url,'kind':'manual_review'});return ''
            found=classify_page(page.html,page.url,contact)
            personal_found=personal_found or any(f['kind']=='person_explicit' for f in found)
            await self.add(jid,found)
            if 'profiles' in sources:
                links.extend({'url':p['url'],'kind':p['network']} for p in social_profile_links(page.html,page.url))
            return page.html
        async def search(query):
            nonlocal queries
            if await self.stopped(jid) or mode=='quick' and personal_found:return []
            if queries>=prefs.max_queries:
                await notice('query_limit');return []
            queries+=1
            try:return await web_search(self.sm,prefs,query)
            except ValueError as e:await notice(str(e) if str(e) in ('search_key_missing','search_budget_exhausted','provider_budget_exhausted') else 'search_unavailable')
            except Exception:await notice('search_unavailable')
            return []
        try:
            async with asyncio.timeout(150):
                site=clean_url(contact.get('website') or ('https://'+contact['domain'] if contact.get('domain') else ''))
                domain=public_site_domain(site)
                if 'website' in sources:
                    if not site:await notice('no_website')
                    else:
                        html=await add_page(site,True)
                        if html:
                            for url in contact_page_links(html,site,domain,'thorough' if mode=='thorough' else 'quick'):
                                if await self.stopped(jid):break
                                await add_page(url,True)
                identity=' '.join('"'+str(x).replace('"',' ')+'"' for x in [contact['first_name']+' '+contact['last_name'] if contact['contact_type']=='person' else '',contact['company'],domain,contact.get('location','')] if x)
                if 'web' in sources:
                    for url in await search(identity+' Kontakt E-Mail'):
                        if await self.stopped(jid):break
                        await add_page(url)
                if 'profiles' in sources:
                    for network in ('linkedin.com','facebook.com','tiktok.com'):
                        for url in await search(identity+' site:'+network):
                            clean=clean_url(url)
                            host=public_site_domain(clean)
                            if clean and (host==network or host.endswith('.'+network)):
                                links.append({'url':clean,'kind':network});await add_page(clean)
                    # Also inspect explicit profile links found on checked company pages.
                    for item in list(links)[:12]:
                        if item['kind']!='manual_review':await add_page(item['url'])
                if 'hunter' in sources and not await self.stopped(jid) and not (mode=='quick' and personal_found):
                    try:await self.add(jid,await hunter_search(self.sm,prefs,contact))
                    except ValueError as e:await notice(str(e))
                    except Exception:await notice('hunter_unavailable')
                state='stopped' if await self.stopped(jid) else 'completed'
        except Exception:
            await notice('research_interrupted');state='interrupted'
        finally:
            unique={item['url']:item for item in links if clean_url(item['url'])}
            async with self.sm._connect() as db:
                await db.execute('UPDATE contact_email_research SET status=?,links_json=?,diagnostics_json=?,finished_at=? WHERE id=?',(locals().get('state','interrupted'),json.dumps(list(unique.values())[:30]),json.dumps(diagnostics[-30:]),now(),jid));await db.commit()
            self.tasks.pop(jid,None)

    async def snapshot(self,jid,cid):
        async with self.sm._connect() as db:
            db.row_factory=aiosqlite.Row
            row=await (await db.execute('SELECT * FROM contact_email_research WHERE id=? AND contact_id=?',(jid,cid))).fetchone()
            if not row:raise ValueError('research_unavailable')
            job=dict(row)
            if job['status']=='running' and jid not in self.tasks:
                await db.execute("UPDATE contact_email_research SET status='interrupted' WHERE id=?",(jid,));await db.commit();job['status']='interrupted'
            rows=await (await db.execute('SELECT * FROM contact_email_findings WHERE job_id=? ORDER BY found_at,id',(jid,))).fetchall()
        contact=await get_contact(self.sm,cid)
        return {'id':jid,'contact_id':cid,'status':job['status'],'stop_requested':bool(job['stop_requested']),
            'criteria':json.loads(job['config_json']),'contact':{k:contact.get(k) for k in SNAPSHOT_FIELDS},
            'stale':contact_fingerprint(contact)!=contact_fingerprint(json.loads(job['snapshot_json'])),
            'items':[dict(r,email_checks=email_checks(r['email'])) for r in rows],
            'links':json.loads(job['links_json']),'diagnostics':json.loads(job['diagnostics_json']),
            'created_at':job['created_at'],'finished_at':job['finished_at']}


def install_contact_research_routes(app,state_factory):
    services={}
    async def service():
        sm=state_factory();await sm.init_db();key=str(sm.db_path)
        if key not in services:services[key]=ResearchService(sm)
        return services[key]

    def error(e):return JSONResponse({'error':str(e)},status_code=409 if str(e) in ('research_busy','contact_changed') else 422)

    @app.get('/api/settings/contact-research')
    async def read():
        srv=await service();p=await settings(srv.sm)
        return dict(settings=p.model_dump(),configured={'serpapi':bool(os.getenv('SERPAPI_API_KEY')),'serper':bool(os.getenv('SERPER_API_KEY')),'hunter':bool(os.getenv('HUNTER_API_KEY'))})

    @app.post('/api/settings/contact-research')
    async def save(request:Request):
        try:
            p=ResearchSettings.model_validate(await request.json());srv=await service()
            await srv.sm.set_setting('contact_research_settings',p.model_dump_json());return {'settings':p.model_dump()}
        except (ValidationError,ValueError,TypeError):return JSONResponse({'error':'invalid_settings'},status_code=422)

    @app.post('/api/contacts/{cid}/email-research')
    async def start(cid:str,request:Request):
        try:
            srv=await service();jid=await srv.create(cid,await request.json());return await srv.snapshot(jid,cid)
        except ValueError as e:return error(e)

    @app.get('/api/contacts/{cid}/email-research/latest')
    async def latest(cid:str):
        try:
            srv=await service();await get_contact(srv.sm,cid)
            async with srv.sm._connect() as db:row=await (await db.execute('SELECT id FROM contact_email_research WHERE contact_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1',(cid,))).fetchone()
            return await srv.snapshot(row[0],cid) if row else None
        except ValueError as e:return error(e)

    @app.get('/api/contacts/{cid}/email-research/{jid}')
    async def status(cid:str,jid:str):
        try:return await (await service()).snapshot(jid,cid)
        except ValueError as e:return error(e)

    @app.post('/api/contacts/{cid}/email-research/{jid}/stop')
    async def stop(cid:str,jid:str):
        try:
            srv=await service();await srv.snapshot(jid,cid)
            async with srv.sm._connect() as db:
                await db.execute('UPDATE contact_email_research SET stop_requested=1 WHERE id=? AND contact_id=?',(jid,cid));await db.commit()
            return await srv.snapshot(jid,cid)
        except ValueError as e:return error(e)

    @app.post('/api/contacts/{cid}/email-research/{jid}/adopt')
    async def adopt(cid:str,jid:str,request:Request):
        from harvey.contacts import create_contact,ContactError
        try:
            body=await request.json()
            if not isinstance(body,dict) or body.get('reviewed') is not True or type(body.get('revision')) is not int:raise ValueError('review_required')
            srv=await service()
            if not (await settings(srv.sm)).enabled:raise ValueError('research_disabled')
            if not isinstance(body.get('finding_id'),str) or len(body['finding_id'])>100:raise ValueError('finding_unavailable')
            contact=await get_contact(srv.sm,cid)
            if blocked(contact):raise ValueError('contact_blocked')
            async with srv.sm._connect() as db:
                db.row_factory=aiosqlite.Row
                row=await (await db.execute('''SELECT f.*,j.snapshot_json FROM contact_email_findings f JOIN contact_email_research j ON j.id=f.job_id
                    WHERE f.id=? AND j.id=? AND j.contact_id=?''',(body.get('finding_id'),jid,cid))).fetchone()
            if not row:raise ValueError('finding_unavailable')
            original=json.loads(row['snapshot_json'])
            if contact_fingerprint(original)!=contact_fingerprint(contact) or body['revision']!=contact['revision']:raise ValueError('contact_changed')
            if contact['email'] and body.get('replace') is not True:raise ValueError('replacement_required')
            if row['kind'] not in ('person_explicit','provider_suggestion') and contact['contact_type']=='person' and body.get('acknowledge_unclear') is not True:raise ValueError('unclear_acknowledgment_required')
            payload={k:contact.get(k) or '' for k in ('company_id','contact_type','first_name','last_name','title','phone')}
            payload.update(email=row['email'],revision=contact['revision'],_research_finding=row['id'],_research_snapshot=contact_fingerprint(original),_research_reviewed=True,_research_ack_unclear=body.get('acknowledge_unclear') is True)
            return await create_contact(srv.sm,payload,contact_id=cid)
        except (ValueError,TypeError,ContactError) as e:return error(e)
