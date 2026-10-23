"""Email enrichment remains evidence-based and scoped to an explicit run."""
from unittest.mock import AsyncMock
import httpx
import pytest
from harvey.collectors import company_contacts as C
from harvey.collectors import discover as D
from harvey import pipeline
from harvey.models.company import Company
from harvey.state import StateManager


def test_ranked_navigation_and_english_fallbacks():
    html='<a href="/team">Team</a><a href="/about-us">About us</a><a href="/reach-us">Contact us</a><a href="https://evil.test/contact">Contact</a>'
    quick=C.contact_page_links(html,'https://business.test','business.test')
    thorough=C.contact_page_links(html,'https://business.test','business.test','thorough')
    assert quick[0]=='https://business.test/reach-us' and len(quick)==2
    assert 'https://business.test/team' in thorough and 'https://business.test/about-us' in thorough
    assert 'https://business.test/contact-us' in thorough
    assert all(url.startswith('https://business.test/') for url in thorough)


def test_noise_rules_do_not_reject_numeric_mailboxes_or_manual_addresses():
    html='<p>123456@business.test hello@sentry.io hash@2x.woff aabbccddeeff1122@business.test good@sentry.io.business.test</p>'
    emails=C.extract_public_emails(html)
    assert '123456@business.test' in emails and 'good@sentry.io.business.test' in emails
    assert 'hello@sentry.io' not in emails and 'hash@2x.woff' not in emails
    assert 'aabbccddeeff1122@business.test' not in emails
    assert C.valid_email('aabbccddeeff1122@business.test') # extraction-only rule


def test_social_links_are_profiles_not_share_widgets_or_posts():
    html=''.join(f'<a href="{url}">link</a>' for url in [
        'https://www.linkedin.com/company/builders/?utm_source=site',
        'https://www.facebook.com/profile.php?id=123&ref=site',
        'https://www.facebook.com/sharer.php?u=site',
        'https://instagram.com/p/post', 'https://instagram.com/builders/',
        'https://www.tiktok.com/@builders/video/123','https://www.tiktok.com/@builders',
        'https://linkedin.com.evil.test/company/a','javascript:alert(1)'])
    profiles=C.social_profile_links(html,'https://business.test')
    assert len(profiles)==4
    assert any(p['url'].endswith('profile.php?id=123') for p in profiles)
    assert all(p['source_url']=='https://business.test' for p in profiles)


@pytest.mark.asyncio
async def test_quick_stops_and_thorough_adds_team_mailboxes_with_sources(tmp_path,monkeypatch):
    state=StateManager(str(tmp_path/'test.db')); await state.init_db()
    company=Company(name='Business',domain='business.test',website='https://business.test')
    await state.add_company(company)
    requests=[]
    def respond(request):
        requests.append(request.url.path)
        body='<p>info@business.test</p><a href="/team">Team</a><a href="https://linkedin.com/company/business">LinkedIn</a>' if request.url.path=='/' else '<p>team@business.test</p>' if request.url.path=='/team' else ''
        return httpx.Response(200,text=body,headers={'content-type':'text/html'})
    original=httpx.AsyncClient
    monkeypatch.setattr(C.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    monkeypatch.setattr(C,'_public_company_url',AsyncMock(return_value=True))
    monkeypatch.setattr(C,'check_email_domain',AsyncMock(return_value='unknown'))
    assert (await C.lookup_company_emails(company,state))['found']==1
    assert requests==['/']
    requests.clear()
    assert (await C.lookup_company_emails(company,state,mode='thorough'))['found']==2
    assert '/team' in requests and len(requests)<=7
    async with state._connect() as db:
        rows=await (await db.execute('SELECT email,source_url FROM company_public_emails')).fetchall()
        socials=await (await db.execute('SELECT network,source_url FROM company_social_profiles')).fetchall()
        people=await (await db.execute('SELECT COUNT(*) FROM prospects')).fetchone()
    assert ('team@business.test','https://business.test/team') in [tuple(r) for r in rows]
    assert socials[0][0]=='LinkedIn' and not people[0]


@pytest.mark.asyncio
async def test_automatic_stage_only_uses_current_run_ids_and_mode(tmp_path,monkeypatch):
    state=StateManager(str(tmp_path/'test.db')); await state.init_db()
    one=Company(name='Selected',domain='selected.test'); other=Company(name='Unrelated',domain='other.test')
    await state.add_company(one); await state.add_company(other)
    monkeypatch.setattr(D,'run_discovery',AsyncMock(return_value=D.DiscoveryReport(company_ids=[one.id,one.id])))
    lookup=AsyncMock(return_value={'status':'found','found':1})
    monkeypatch.setattr(C,'lookup_company_emails',lookup)
    events=[]
    async def event(row): events.append(row)
    result=await pipeline.run_prospecting(state,None,profile=False,email_search=True,email_mode='thorough',on_progress=event)
    assert result.email_summary['total']==1 and result.email_summary['found']==1
    assert lookup.await_args.args[0].id==one.id and lookup.await_args.kwargs=={'mode':'thorough'}
    assert events[0]['stage']=='emails' and events[-1]['completed']==1


@pytest.mark.asyncio
async def test_email_stage_opt_in_and_pause_are_respected(tmp_path,monkeypatch):
    state=StateManager(str(tmp_path/'test.db')); await state.init_db()
    monkeypatch.setattr(D,'run_discovery',AsyncMock(return_value=D.DiscoveryReport(company_ids=['one'])))
    lookup=AsyncMock()
    monkeypatch.setattr(C,'lookup_company_emails',lookup)
    await pipeline.run_prospecting(state,None,profile=False)
    lookup.assert_not_awaited()
    await state.set_setting('discovery_paused','1')
    await pipeline.run_prospecting(state,None,profile=False,email_search=True)
    lookup.assert_not_awaited()

@pytest.mark.asyncio
async def test_job_restores_saved_mode_in_new_service(tmp_path,monkeypatch):
    from harvey.collectors.contact_jobs import ContactJobs
    state=StateManager(str(tmp_path/'test.db')); await state.init_db()
    company=Company(name='Job test',domain='jobs.test'); await state.add_company(company)
    original=ContactJobs(state)
    monkeypatch.setattr(original,'start',lambda:None)
    job_id=await original.create([company.id],mode='thorough')
    lookup=AsyncMock(return_value={'status':'not_found'})
    monkeypatch.setattr(C,'lookup_company_emails',lookup)
    restored=ContactJobs(state)
    snapshot=await restored.snapshot(job_id)
    assert snapshot['mode']=='thorough'
    await restored.task
    assert lookup.await_args.kwargs=={'mode':'thorough'}
    assert (await restored.snapshot(job_id))['status']=='completed'


def test_api_modes_and_social_evidence_are_available(tmp_path,monkeypatch):
    import asyncio
    import harvey.dashboard as dashboard
    from fastapi.testclient import TestClient
    state=StateManager(str(tmp_path/'api.db'))
    company=Company(name='API example',domain='api.test',website='https://api.test')
    async def seed():
        await state.init_db(); await state.add_company(company)
        await state.save_company_social_profiles(company.id,[{'network':'LinkedIn','url':'https://linkedin.com/company/api-example','source_url':'https://api.test/contact'}])
    asyncio.run(seed())
    monkeypatch.setattr(dashboard,'DB_PATH',tmp_path/'api.db')
    monkeypatch.setattr(dashboard,'_contact_jobs',None)
    lookup=AsyncMock(return_value={'status':'found','found':1})
    monkeypatch.setattr(C,'lookup_company_emails',lookup)
    with TestClient(dashboard.app) as client:
        invalid=client.post(f'/api/companies/{company.id}/lookup-contacts',json={'mode':'unlimited'})
        assert invalid.status_code==422
        result=client.post(f'/api/companies/{company.id}/lookup-contacts',json={'mode':'thorough'})
        assert result.status_code==200 and lookup.await_args.kwargs=={'mode':'thorough'}
        response=client.get('/api/companies/page').json()
        # The paginated response uses the shared company-detail hydration.
        rows=response.get('companies',response.get('items',[]))
        assert rows[0]['social_profiles'][0]['source_url']=='https://api.test/contact'
        job=client.post('/api/company-email-jobs',json={'company_ids':[company.id],'mode':'thorough'})
        assert job.status_code==200 and job.json()['mode']=='thorough'
