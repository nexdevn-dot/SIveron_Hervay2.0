import json
from unittest.mock import AsyncMock

import pytest

from harvey.discovery_progress import DiscoveryProgress, progress_view, KEY
from harvey.collectors.location_suggestions import suggest_locations
from harvey.state import StateManager


@pytest.mark.asyncio
async def test_progress_eta_is_measured_and_resets_per_phase(tmp_path):
    state = StateManager(str(tmp_path / 'progress.db'))
    await state.init_db()
    clock = [100.0]
    progress = DiscoveryProgress(state, clock=lambda: clock[0])
    await progress.update({'stage': 'searching', 'total': 4})
    assert progress_view(progress.data, True, now=101)['eta_seconds'] is None
    clock[0] = 103
    await progress.update({'completed': 1, 'new_companies': 3})
    clock[0] = 107
    await progress.update({'completed': 2, 'known_companies': 1})
    snapshot = progress_view(progress.data, True, now=108)
    assert snapshot['completed'] == 2 and snapshot['total'] == 4
    assert snapshot['eta_seconds'][0] <= snapshot['eta_seconds'][1]
    assert snapshot['elapsed_seconds'] == 8
    assert progress_view(progress.data, True, now=150)['eta_seconds'] is None
    assert progress_view(progress.data, True, now=150)['waiting']
    clock[0] = 110
    await progress.update({'stage': 'profiling', 'total': 6, 'completed': 0})
    assert progress_view(progress.data, True, now=110)['eta_seconds'] is None
    saved = json.loads(await state.get_setting(KEY))
    assert saved['new_companies'] == 3 and saved['known_companies'] == 1
    assert saved['stage'] == 'profiling'
    assert progress_view(saved, False, now=111)['status'] == 'interrupted'
    await progress.finish('stopped')
    assert progress_view(progress.data, False, now=200)['elapsed_seconds'] == 10


@pytest.mark.asyncio
async def test_geocoding_progress_uses_selected_coordinates_and_radius(tmp_path, monkeypatch):
    from harvey.collectors import discover as D
    state = StateManager(str(tmp_path / 'geo.db'))
    await state.init_db()
    geocode = AsyncMock(return_value='51,8,25')
    monkeypatch.setattr(D, 'geocode_city', geocode)
    events = []
    async def update(event):
        events.append(event)
    queries = [D.DiscoveryQuery(term='Arztpraxis', location='Selected', coordinate='52,9,25'),
               D.DiscoveryQuery(term='Zahnarzt', location='Manual')]
    await D.resolve_coordinates(state, queries, on_progress=update, radius_km_override=25)
    assert geocode.await_count == 1 and geocode.call_args.args[2] == 25
    assert events[0] == {'stage': 'geocoding', 'total': 1, 'completed': 0, 'current': ''}
    assert events[-1] == {'completed': 1}
    assert queries[0].coordinate == '52,9,25'


@pytest.mark.asyncio
async def test_location_suggestions_use_server_key_cache_and_shared_quota(tmp_path, monkeypatch):
    import httpx
    from harvey.collectors import location_suggestions as L
    from harvey.collectors.discovery_quota import quota_status
    state = StateManager(str(tmp_path / 'locations.db'))
    await state.init_db()
    requests = []
    def respond(request):
        requests.append(request)
        assert request.url.params['apiKey'] == 'fixture-key'
        return httpx.Response(200, json={'features': [{'properties': {
            'formatted': 'Rietberg, NRW, Deutschland', 'city': 'Rietberg', 'lat': 51.8, 'lon': 8.4}}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(L.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    result = await suggest_locations(state, 'Riet', 'de', 'fixture-key')
    assert result['features'][0]['properties']['city'] == 'Rietberg'
    assert 'fixture-key' not in json.dumps(result)
    assert await suggest_locations(state, 'riet', 'de', 'fixture-key') == result
    assert len(requests) == 1 and (await quota_status(state, 'geoapify'))['used'] == 1
    assert not (await suggest_locations(state, 'Riet', 'de', ''))['available']
    assert not (await suggest_locations(state, 'Ri', 'de', 'fixture-key'))['features']


@pytest.mark.asyncio
async def test_exhausted_quota_prevents_location_network_call(tmp_path):
    from harvey.collectors.discovery_quota import quota_key
    state = StateManager(str(tmp_path / 'quota.db'))
    await state.init_db()
    await state.set_setting(quota_key('geoapify'), '3000')
    assert (await suggest_locations(state, 'Rietberg', 'de', 'fixture-key'))['reason'] == 'quota'


@pytest.mark.asyncio
async def test_failed_query_advances_progress_and_pause_prevents_next_query(tmp_path, monkeypatch):
    from harvey.collectors import discover as D
    from harvey.config import load_config
    from harvey.signals import seed_signal_catalog
    state = StateManager(str(tmp_path / 'query.db'))
    await state.init_db()
    await seed_signal_catalog(state)
    await state.set_signal_status('FOUND_IN_SERP', 'confirmed')
    class Provider(D.DiscoveryProvider):
        key = 'progress_fixture'
        kind = 'serp'
        def configured(self, env): return True
        def estimate(self, queries): return 0
        async def fetch(self, client, env, query):
            raise RuntimeError('simulated timeout')
    monkeypatch.setitem(D.PROVIDERS, Provider.key, Provider())
    events = []
    async def update(event):
        events.append(event)
        if event.get('completed') == 1:
            await state.set_setting('discovery_paused', 'stop')
    report = await D.run_discovery(state, load_config(), Provider.key,
        [D.DiscoveryQuery(term='first'), D.DiscoveryQuery(term='second')], on_progress=update)
    assert len(report.errors) == 1 and report.stopped == 'paused'
    assert any(event.get('completed') == 1 and event.get('errors') == 1 for event in events)
    assert not any(event.get('current') == 'second' for event in events)


@pytest.mark.asyncio
async def test_profile_stop_counts_only_processed_companies(tmp_path, monkeypatch):
    from harvey.models import Company
    from harvey.signals import seed_signal_catalog
    from harvey.collectors.profile import ProfileCollector
    from harvey.pipeline import run_profile_stage
    state = StateManager(str(tmp_path / 'profile.db'))
    await state.init_db()
    await seed_signal_catalog(state)
    await state.set_signal_status('FOUND_IN_SERP', 'confirmed')
    for domain in ('first.test', 'second.test'):
        await state.add_company(Company(name=domain, domain=domain))
    async def read(self, company_id, domain): return []
    monkeypatch.setattr(ProfileCollector, 'profile_company', read)
    events = []
    async def update(event):
        events.append(event)
        if event.get('completed') == 1:
            await state.set_setting('discovery_paused', 'stop')
    processed, _, _ = await run_profile_stage(state, on_progress=update)
    assert processed == 1 and events[0]['total'] == 2
    assert await state.count_companies_needing_profile() == 1


@pytest.mark.asyncio
async def test_limit_measurements_survive_profile_phase_and_reload(tmp_path):
    state=StateManager(str(tmp_path/'limit.db'));await state.init_db()
    progress=DiscoveryProgress(state)
    results=[{'query':'Bauunternehmen Frankfurt','limit':100,'raw_count':49,'usable_count':49,'reached':False}]
    await progress.update({'stage':'searching','result_limits':results})
    await progress.update({'stage':'profiling','total':26})
    await progress.finish()
    saved=json.loads(await state.get_setting(KEY))
    assert progress_view(saved,False)['result_limits']==results
