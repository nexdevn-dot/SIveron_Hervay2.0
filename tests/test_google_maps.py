"""Offline contract tests for bounded local search and branch-safe import."""
from dataclasses import asdict
import json
import pytest
from harvey.collectors.discover import Business, DiscoveryQuery, _upsert, run_discovery
from harvey.collectors import google_maps as maps
from harvey.models.company import Company
from harvey.state import StateManager


def query(**kwargs):
    return DiscoveryQuery(term='Bauunternehmen', location='Frankfurt', coordinate='50.11,8.68,20', **kwargs)


def test_grid_bounded_and_radius_origin_preserved():
    cells = maps.plan([query(maps_mode='grid')])
    assert len(cells) == 9
    assert len({c.coordinate for c in cells}) == 9
    assert all(c.maps_origin == '50.11,8.68,20' for c in cells)
    with pytest.raises(ValueError):
        maps.plan([query(maps_mode='grid')] * 12)
    with pytest.raises(ValueError):
        maps.plan([query(limit=201)])
    with pytest.raises(ValueError):
        maps.plan([query(maps_mode='invalid')])


def test_location_and_numbers_validated():
    with pytest.raises(ValueError):
        maps.plan([DiscoveryQuery(term='Dentist')])
    for raw in ('nan,8,20','50,999,20','50,8,-1','50,8,201'):
        with pytest.raises(ValueError):
            maps.coordinates(raw)


def test_exact_radius_filters_and_safe_links():
    raw = {'name':'Bau GmbH','panel':True,'website':'https://example.com','phone':'Telefon: +49 123','address':'Frankfurt'}
    url = 'https://www.google.com/maps/place/Bau/data=!1sbranch!3d50.11!4d8.68'
    b = maps.build_business(raw, url, query())
    assert b.external_id == 'google_maps:branch' and b.phone == '+49 123'
    assert maps.build_business(raw, url, query(maps_filter='no_website')) is None
    assert maps.build_business(raw, url.replace('50.11','51.11'), query()) is None
    assert maps.build_business(raw, 'https://www.google.com/maps/place/Bau/@50.11,8.68,12z', query()) is None
    assert not maps.safe_maps_url('https://www.google.com.attacker.test/maps/place/a')
    assert not maps.safe_maps_url('https://user@www.google.com/maps/place/a')
    assert maps.build_business({**raw,'panel':False},url,query()) is None


@pytest.mark.asyncio
async def test_branch_identity_and_non_destructive_updates(tmp_path):
    state = StateManager(str(tmp_path/'maps.db'))
    await state.init_db()
    q=query()
    a=Business(name='Branch',domain='example.com',website='https://example.com',phone='123',location='First',external_id='google_maps:a',source_url='https://www.google.com/maps/place/a',provider='google_maps')
    first,new=await _upsert(state,a,q)
    assert new
    second,new=await _upsert(state,Business(**{**asdict(a),'external_id':'google_maps:b','location':'Second'}),q)
    assert new and second!=first
    repeated,new=await _upsert(state,Business(**{**asdict(a),'phone':'999','location':'Changed'}),q)
    assert not new and repeated==first
    saved=await state.get_company(first)
    assert saved.phone=='123' and saved.location=='First'
    branch=await state.get_company(second)
    assert branch.website=='https://example.com' and not branch.domain


@pytest.mark.asyncio
async def test_legacy_matching_requires_name_and_phone_and_keeps_source(tmp_path):
    state=StateManager(str(tmp_path/'maps.db')); await state.init_db()
    old=Company(name='Legacy',domain='legacy.example',phone='+49 123',source='manual',external_id='osm:one')
    await state.add_company(old)
    b=Business(name='Legacy',domain='legacy.example',website='https://legacy.example',phone='+49 123',location='Frankfurt',external_id='google_maps:legacy',source_url='https://www.google.com/maps/place/Legacy',provider='google_maps')
    ident,new=await _upsert(state,b,query())
    assert not new and ident==old.id
    saved=await state.get_company(ident)
    assert saved.source=='manual' and saved.external_id=='osm:one' and saved.website==b.website
    assert (await _upsert(state,b,query()))==(old.id,False)


@pytest.mark.asyncio
async def test_completed_checkpoint_needs_no_browser(tmp_path):
    import hashlib
    state=StateManager(str(tmp_path/'maps.db')); await state.init_db()
    q=query(); fingerprint={k:v for k,v in asdict(q).items() if k!='maps_resume'}
    key='maps_checkpoint:'+hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()
    await state.set_setting(key,json.dumps({'complete':True,'records':[asdict(Business(name='Saved'))]}))
    result=await maps.fetch(q,state)
    assert result[0].name=='Saved'

@pytest.mark.asyncio
async def test_estimate_is_local_and_counts_grid_sections(tmp_path, monkeypatch):
    import harvey.dashboard as dashboard
    from harvey.config import load_config
    monkeypatch.setattr(dashboard, 'DB_PATH', tmp_path/'preview.db')
    async def ready(): return True
    monkeypatch.setattr(maps, 'browser_available', ready)
    class Request:
        async def json(self):
            return {'provider':'google_maps','terms':['Bauunternehmen'],'cities':['Frankfurt'],
                    'locations':[{'name':'Frankfurt','lat':50.11,'lon':8.68}],
                    'maps_mode':'grid','limit':5,'radius_km':20}
    response=await dashboard.estimate_discovery(Request())
    assert isinstance(response,dict), response
    assert response['query_count']==9 and response['max_results']==45
    assert response['can_run'] and response['estimated_cost']==0


@pytest.mark.asyncio
async def test_missing_location_and_oversized_grid_rejected():
    import harvey.dashboard as dashboard
    from harvey.config import load_config
    with pytest.raises(ValueError, match='specific location'):
        dashboard._discovery_queries({'provider':'google_maps','terms':['Bau']},load_config())
    with pytest.raises(ValueError, match='100 search sections'):
        dashboard._discovery_queries({'provider':'google_maps','terms':['Bau']*12,
            'cities':['Frankfurt'], 'maps_mode':'grid'},load_config())

@pytest.mark.asyncio
async def test_partial_checkpoint_resumes_only_missing_places_and_closes_browser(tmp_path, monkeypatch):
    import hashlib
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock
    import playwright.async_api
    state=StateManager(str(tmp_path/'maps.db')); await state.init_db()
    q=query(); fingerprint={k:v for k,v in asdict(q).items() if k!='maps_resume'}
    key='maps_checkpoint:'+hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()
    first='https://www.google.com/maps/place/One/data=!1sone!3d50.11!4d8.68'
    second='https://www.google.com/maps/place/Two/data=!1stwo!3d50.11!4d8.68'
    await state.set_setting(key,json.dumps({'records':[asdict(Business(name='One'))],
        'done':[first],'links':[first,second],'complete':False}))
    locator=MagicMock(); locator.count=AsyncMock(return_value=0); locator.first.wait_for=AsyncMock()
    detail=MagicMock(); detail.url=second; detail.goto=AsyncMock(); detail.locator.return_value=locator
    detail.evaluate=AsyncMock(return_value={'name':'Two','panel':True,'website':'https://two.example'})
    page=MagicMock()
    context=MagicMock(); context.route=AsyncMock(); context.new_page=AsyncMock(side_effect=[page,detail])
    browser=SimpleNamespace(new_context=AsyncMock(return_value=context),close=AsyncMock())
    p=SimpleNamespace(chromium=SimpleNamespace(launch=AsyncMock(return_value=browser)))
    class Playwright:
        async def __aenter__(self): return p
        async def __aexit__(self,*args): pass
    monkeypatch.setattr(playwright.async_api,'async_playwright',Playwright)
    monkeypatch.setattr(maps.asyncio,'sleep',AsyncMock())
    rows=await maps.fetch(q,state)
    assert [r.name for r in rows]==['One','Two']
    assert detail.goto.await_count==1 and detail.goto.call_args.args[0]==second
    assert json.loads(await state.get_setting(key))['complete'] is True
    browser.close.assert_awaited_once()
