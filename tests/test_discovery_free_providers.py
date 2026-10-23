"""Free adapters: correct categories, secret-safe failures and pre-I/O quotas."""
import asyncio
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio

from harvey.collectors import discover as D
from harvey.collectors.discovery_quota import quota_key, quota_status, reserve_quota
from harvey.config import EnvConfig, load_config
from harvey.signals import SIGNAL_CATALOG, seed_signal_catalog
from harvey.state import StateManager


@pytest_asyncio.fixture
async def state(tmp_path):
    state = StateManager(str(tmp_path / 'test.db'))
    await state.init_db()
    return state


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [429, 500, 502, 503, 504])
async def test_overpass_retries_gateway_failures_and_remembers_healthy_mirror(status, monkeypatch):
    monkeypatch.setattr(D.OpenStreetMap, 'BACKOFF', 0)
    seen = []
    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(status if len(seen) == 1 else 200, json={'elements': []})
    osm = D.OpenStreetMap()
    query = D.DiscoveryQuery(term='Elektriker', coordinate='51.8,8.4,20')
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        await osm.fetch(client, {}, query)
        await osm.fetch(client, {}, query)
    assert seen == [osm.ENDPOINTS[0], osm.ENDPOINTS[1], osm.ENDPOINTS[1]]


@pytest.mark.asyncio
async def test_overpass_does_not_retry_a_malformed_query():
    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(400)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await D.OpenStreetMap().fetch(client, {}, D.DiscoveryQuery(term='roofer', coordinate='51,8,20'))
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_geoapify_category_radius_contacts_and_medical_evidence():
    seen = []
    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={'features': [{'properties': {
            'place_id': 'place1', 'name': 'Praxis Beispiel', 'city': 'Rietberg',
            'categories': ['healthcare.clinic_or_praxis'],
            'contact': {'website': 'https://www.praxis.example', 'phone': '123'},
        }}]})
    provider = D.Geoapify()
    assert provider.category_for('Elektriker') == 'service.electrician'
    assert provider.category_for('Zahnarztpraxis') == 'healthcare.dentist'
    assert provider.category_for('Hausarztpraxis') == 'healthcare.clinic_or_praxis.general'
    assert provider.category_for('Dachdecker') == ''  # No fabricated catch-all category.
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        results = await provider.fetch(client, {'geoapify_api_key': 'private-test-key'},
            D.DiscoveryQuery(term='Arztpraxis', coordinate='51.8,8.4,20', limit=100))
    assert seen[0].url.params['filter'] == 'circle:8.4,51.8,20000'
    assert results[0].domain == 'praxis.example'
    assert results[0].category == 'Doctor practice — specialty unknown'
    assert provider.quota_units(D.DiscoveryQuery('Arztpraxis', limit=21)) == 2
    assert provider.quota_units(D.DiscoveryQuery('Arztpraxis', limit=1000)) == 25


@pytest.mark.asyncio
async def test_key_bearing_provider_errors_are_redacted():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(502))) as client:
        with pytest.raises(RuntimeError) as error:
            await D.Geoapify().fetch(client, {'geoapify_api_key': 'TOP-SECRET'},
                D.DiscoveryQuery('Arztpraxis', coordinate='51,8,20'))
    assert '502' in str(error.value)
    assert 'TOP-SECRET' not in str(error.value)
    assert 'apiKey' not in str(error.value)


@pytest.mark.asyncio
async def test_serpapi_free_account_paging_and_rank():
    starts = []
    def respond(request):
        if request.url.path == '/account.json':
            return httpx.Response(200, json={'plan_monthly_price': 0, 'searches_per_month': 250, 'plan_searches_left': 20})
        start = int(request.url.params['start'])
        starts.append(start)
        assert request.url.params['gl'] == 'de'
        return httpx.Response(200, json={'organic_results': [
            {'title': 'Example', 'link': f'https://company{start}.example', 'position': 1}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        found = await D.SerpApi().fetch(client, {'serpapi_api_key': 'test-key'},
            D.DiscoveryQuery('Elektriker', location='Rietberg', depth=20))
    assert starts == [0, 10]
    assert [biz.rank for biz in found] == [1, 11]


@pytest.mark.asyncio
@pytest.mark.parametrize('account', [
    {'plan_monthly_price': 25, 'searches_per_month': 1000, 'plan_searches_left': 100},
    {}, {'plan_monthly_price': 0, 'searches_per_month': 250, 'plan_searches_left': 0},
])
async def test_serpapi_blocks_paid_unknown_or_empty_accounts(account):
    calls = []
    def respond(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=account)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(RuntimeError):
            await D.SerpApi().fetch(client, {'serpapi_api_key': 'key'}, D.DiscoveryQuery('Elektriker'))
    assert calls == ['/account.json']


@pytest.mark.asyncio
async def test_quota_reservations_are_atomic_and_do_not_overrun(state):
    await state.set_setting(quota_key('geoapify'), '2999')
    reserved = await asyncio.gather(*(reserve_quota(state, 'geoapify', 1) for _ in range(5)))
    assert sum(reserved) == 1
    info = await quota_status(state, 'geoapify', 1)
    assert info['used'] == 3000 and info['remaining'] == 0 and not info['can_run']


def test_quota_periods_reset_independently_of_browser_clock():
    first = datetime(2026, 10, 31, tzinfo=timezone.utc)
    next_day = datetime(2026, 11, 1, tzinfo=timezone.utc)
    assert quota_key('geoapify', first) != quota_key('geoapify', next_day)
    assert quota_key('serpapi', first) != quota_key('serpapi', next_day)


@pytest.mark.asyncio
async def test_run_stops_before_external_fetch_when_free_quota_is_exhausted(state, monkeypatch):
    import harvey.config as config_module
    monkeypatch.setattr(config_module, 'load_env', lambda: EnvConfig(geoapify_api_key='test-key'))
    async def must_not_fetch(*args):
        pytest.fail('external search attempted after quota exhausted')
    monkeypatch.setattr(D.PROVIDERS['geoapify'], 'fetch', must_not_fetch)
    await seed_signal_catalog(state)
    for sig in SIGNAL_CATALOG:
        await state.set_signal_status(sig['code'], 'confirmed')
    await state.set_setting(quota_key('geoapify'), '3000')
    report = await D.run_discovery(state, load_config(), 'geoapify',
        [D.DiscoveryQuery('Arztpraxis', coordinate='51,8,20')], max_spend=0)
    assert report.stopped == 'free quota exhausted'
    assert report.actual_cost == 0


@pytest.mark.asyncio
async def test_request_logs_never_contain_api_keys(caplog):
    import logging
    caplog.set_level(logging.INFO, logger='httpx')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))) as client:
        await D._provider_json(client, 'https://api.geoapify.com/v2/places', {'apiKey': 'PRIVATE-KEY'}, 'Geoapify')
        await D._provider_json(client, 'https://serpapi.com/account.json', {'api_key': 'PRIVATE-KEY'}, 'SerpApi')
    assert 'PRIVATE-KEY' not in caplog.text
    assert '[redacted]' in caplog.text
