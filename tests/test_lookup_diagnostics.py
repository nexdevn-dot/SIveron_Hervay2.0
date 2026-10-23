import asyncio
import json
from datetime import datetime,timezone,timedelta
import httpx
import pytest
from harvey.state import StateManager
from harvey.models import Company
from harvey.collectors.contact_jobs import ContactJobs
from harvey.collectors import company_contacts as C
from harvey.lookup_diagnostics import diagnostic


def test_diagnostics_never_include_credentials_query_or_exception():
    value=diagnostic('fetch','http_error','https://user:secret@company.test/kontakt?token=private#fragment',http_status=503)
    assert value['source']=='https://company.test/kontakt'
    assert 'secret' not in json.dumps(value) and 'private' not in json.dumps(value)


@pytest.mark.asyncio
async def test_http_and_timeout_evidence_are_distinct_and_guard_preserved(tmp_path,monkeypatch):
    sm=StateManager(str(tmp_path/'db'));await sm.init_db();co=Company(id='c',name='C',domain='company.test',website='https://company.test')
    await sm.add_company(co)
    async def allow(*a):return True
    monkeypatch.setattr(C,'_public_company_url',allow)
    original=httpx.AsyncClient
    monkeypatch.setattr(C.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(503,headers={'content-type':'text/html'})),**kw))
    data=await C.lookup_company_emails(co,sm)
    assert data['status']=='unreachable'
    assert any(r['code']=='http_error' and r['http_status']==503 and r['retryable'] for r in data['diagnostics'])
    async def deny(*a):return False
    monkeypatch.setattr(C,'_public_company_url',deny)
    data=await C.lookup_company_emails(co,sm)
    assert all(not r['retryable'] for r in data['diagnostics'])
    assert any(r['code']=='unsafe_or_external_url' for r in data['diagnostics'])


@pytest.mark.asyncio
async def test_durable_retry_is_bounded_cooldown_and_success_is_not_repeated(tmp_path,monkeypatch):
    sm=StateManager(str(tmp_path/'db'));await sm.init_db()
    for cid in ['a','b']:await sm.add_company(Company(id=cid,name=cid))
    service=ContactJobs(sm);monkeypatch.setattr(service,'start',lambda:None)
    jid=await service.create(['a','b'])
    now=datetime.now(timezone.utc)
    async def finish(attempts,checked):
        async with sm._connect() as db:
            info={'checked_at':checked.isoformat(),'retryable':True,'reasons':[diagnostic('lookup','timeout',retryable=True)]}
            await db.execute("UPDATE company_email_jobs SET status='completed' WHERE id=?",(jid,))
            await db.execute("UPDATE company_email_job_items SET status='failed',attempts=?,diagnostic_json=? WHERE company_id='a'",(attempts,json.dumps(info)))
            await db.execute("UPDATE company_email_job_items SET status='found',attempts=1 WHERE company_id='b'")
            await db.commit()
    await finish(1,now)
    assert not await service.retry(jid)
    await finish(1,now-timedelta(seconds=61))
    assert await service.retry(jid)
    snap=await service.snapshot(jid)
    assert {i['company_id']:i['status'] for i in snap['items']}=={'a':'queued','b':'found'}
    assert snap['items'][0]['diagnostic']['reasons'][0]['code']=='timeout'
    await finish(3,now-timedelta(seconds=61))
    assert not await service.retry(jid)


@pytest.mark.asyncio
async def test_retry_runs_under_original_budget_and_persists_second_result(tmp_path,monkeypatch):
    sm=StateManager(str(tmp_path/'retry.db'));await sm.init_db()
    await sm.add_company(Company(id='retry',name='Retry'))
    calls=[]
    async def lookup(company,state,**kwargs):
        calls.append(kwargs.get('mode','quick'))
        return {'status':'unreachable','diagnostics':[diagnostic('fetch','network_error',retryable=True)]} if len(calls)==1 else {'status':'not_found','diagnostics':[diagnostic('extraction','no_email_in_checked_pages')]}
    monkeypatch.setattr(C,'lookup_company_emails',lookup)
    service=ContactJobs(sm);jid=await service.create(['retry'],mode='thorough');await service.task
    first=await service.snapshot(jid)
    assert first['items'][0]['attempts']==1 and first['items'][0]['status']=='failed'
    info=first['items'][0]['diagnostic'];info['checked_at']=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat()
    async with sm._connect() as db:
        await db.execute('UPDATE company_email_job_items SET diagnostic_json=?',(json.dumps(info),));await db.commit()
    assert await service.retry(jid);await service.task
    second=await service.snapshot(jid)
    assert second['status']=='completed' and second['items'][0]['attempts']==2
    assert second['counts']['not_found']==1 and second['items'][0]['diagnostic']['reasons'][0]['code']=='no_email_in_checked_pages'
    assert calls==['thorough','thorough']
    assert not await service.retry(jid)
