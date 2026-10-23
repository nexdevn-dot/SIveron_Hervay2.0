"""Parking searches use real categories and require evidence of an operator.

All provider calls are mocked; these checks never launch a live search.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

import harvey.dashboard as dashboard
from harvey.collectors import discover as D
from harvey.collectors.parking import parking_intent
from harvey.discovery_catalog import term_catalog


@pytest.mark.parametrize('term', [
    'Parkplatzbetreiber', 'Parkhausbetreiber', 'Parkraumbewirtschaftung',
    'Parkraummanagement', 'Parkplatzmanagement', 'Parkservice',
    'Parkplatz', 'Parkplätze', 'Parkhaus', 'Tiefgarage',
    '  PARKPLATZBETREIBER  ', 'parking operator', 'parking garage',
])
def test_parking_terms_are_supported_by_map_sources(term):
    assert D.OpenStreetMap()._tags(term) == ['amenity=parking']
    assert D.Geoapify().category_for(term).startswith('parking.cars')


@pytest.mark.parametrize('term', [
    'Parkplatzbau', 'Valet Parking', 'Flughafenparken', 'Lkw-Parkplatzbetreiber',
    'Parkplatz Software', 'Freizeitpark',
])
def test_specialist_terms_are_not_silently_broadened(term):
    assert parking_intent(term) is None
    assert D.OpenStreetMap()._tags(term) == []
    assert D.Geoapify().category_for(term) == ''


@pytest.mark.asyncio
async def test_osm_operator_query_keeps_operator_and_facility_contacts_separate():
    requests = []

    def respond(request):
        requests.append(request.content.decode())
        return httpx.Response(200, json={'elements': [
            {'type': 'way', 'id': 1, 'tags': {
                'amenity': 'parking', 'operator': 'Example Parking GmbH',
                'operator:website': 'https://operator.example',
                'name': 'Station parking', 'website': 'https://facility.example',
                'phone': 'facility-phone', 'email': 'facility@example.test',
                'addr:street': 'Facility Street',
            }},
            {'type': 'node', 'id': 2, 'tags': {'amenity': 'parking', 'name': 'No operator'}},
            {'type': 'node', 'id': 3, 'tags': {'amenity': 'parking', 'operator': 'unknown'}},
            # A named operator is useful even on an unnamed parking facility.
            {'type': 'relation', 'id': 4, 'tags': {
                'amenity': 'parking', 'operator': 'Second Operator',
                'operator:email': 'office@second.example',
            }},
        ]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        results = await D.OpenStreetMap().fetch(client, {},
            D.DiscoveryQuery('Parkplatzbetreiber', location='Example city', coordinate='51,8,20'))
    assert 'way[amenity=parking][operator]' in requests[0]
    assert 'relation[amenity=parking][operator]' in requests[0]
    assert [r.name for r in results] == ['Example Parking GmbH', 'Second Operator']
    assert results[0].domain == 'operator.example'
    assert results[0].phone == results[0].public_email == results[0].address == ''
    assert results[0].source_url == 'https://www.openstreetmap.org/way/1'
    assert results[1].identity() == 'osm:relation/4:operator'
    assert results[1].public_email == 'office@second.example'
    assert results[1].has_website is None  # Missing operator metadata is not evidence of no website.


@pytest.mark.asyncio
async def test_osm_garage_search_does_not_include_surface_parking():
    requests = []

    def respond(request):
        requests.append(request.content.decode())
        return httpx.Response(200, json={'elements': [
            {'type': 'way', 'id': i, 'tags': {
                'amenity': 'parking', 'parking': kind, 'name': kind,
            }} for i, kind in enumerate(('multi-storey', 'underground', 'surface'))
        ]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        results = await D.OpenStreetMap().fetch(client, {},
            D.DiscoveryQuery('Parkhaus', coordinate='51,8,20'))
    assert '[parking~"^(multi-storey|underground)$"]' in requests[0]
    assert [r.name for r in results] == ['multi-storey', 'underground']
    assert all(r.category == 'parking' for r in results)


@pytest.mark.asyncio
@pytest.mark.parametrize('term,category', [
    ('Parkplatzbetreiber', 'parking.cars'),
    ('Parkhausbetreiber', 'parking.cars.multistorey,parking.cars.underground'),
])
async def test_geoapify_operator_evidence_and_documented_categories(term, category):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={'features': [
            {'properties': {'place_id': 'one', 'name': 'Facility',
                'contact': {'website': 'https://facility.example', 'phone': '123'},
                'datasource': {'raw': {'operator': 'Operator',
                    'operator:website': 'https://operator.example'}}}},
            {'properties': {'place_id': 'two', 'name': 'Facility without operator'}},
        ]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        results = await D.Geoapify().fetch(client, {'geoapify_api_key': 'test-key'},
            D.DiscoveryQuery(term, coordinate='51,8,20'))
    assert requests[0].url.params['categories'] == category
    assert len(results) == 1
    assert results[0].name == 'Operator'
    assert results[0].domain == 'operator.example'
    assert results[0].phone == ''


def test_parking_catalog_suggestions_have_provider_support_flags():
    catalog = {x['value']: x for x in term_catalog('osm', dashboard._discovery_category_supported)}
    assert catalog['Parkplatzbetreiber']['supported'] is True
    assert 'Parkraumbewirtschaftung' in catalog['Parkplatzbetreiber']['searchBy']
    assert catalog['Flughafenparken']['supported'] is False
    assert 'Parkplatzbetreiber' in D.OpenStreetMap().suggest_terms('Parkplatzbetreibr')


@pytest.mark.parametrize('provider', ['osm', 'geoapify'])
def test_parking_preview_explains_coverage_and_accepts_operator_terms(tmp_path, monkeypatch, provider):
    monkeypatch.setattr(dashboard, 'DB_PATH', tmp_path / 'preview.db')
    with TestClient(dashboard.app) as client:
        response = client.post('/api/discover/estimate', json={
            'provider': provider, 'terms': ['Parkplatzbetreiber', 'Parkhausbetreiber'],
            'cities': ['Example city'],
        })
    assert response.status_code == 200
    data = response.json()
    assert data['unsupported'] == []
    assert all(q['status'] == 'supported' for q in data['query_details'])
    warning = next(w for w in data['warnings'] if w['code'] == 'parking_operator_evidence')
    assert 'not assigned' in warning['message']
    if provider == 'osm':
        assert data['can_run'] is True


def test_facility_warning_does_not_claim_operator_discovery():
    from harvey.config import load_config
    result = dashboard._discovery_preflight('osm', [D.DiscoveryQuery('Parkplatz')], load_config())
    assert any(w['code'] == 'parking_facilities' for w in result['warnings'])
    assert result['can_run'] is True
