"""Filter matching is global, parameterised, branch-neutral and disjunctive."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from harvey.models import Company, Prospect
from harvey.state import StateManager
import harvey.dashboard as dashboard


@pytest.fixture
def inventory(tmp_path,monkeypatch):
    state=StateManager(str(tmp_path/'filters.db'))
    records={}
    async def seed():
        await state.init_db()
        for name,city,industry,phone,source in [('A','Berlin','Hotel','111','manual'),('B','Hamburg','Hotel','','discover:osm'),('C','Berlin','Bau','222','manual'),('D','Munich','Hotel','333','discover:google_maps')]:
            c=Company(name=name,location=city,industry=industry,phone=phone,source=source,domain=f'{name.lower()}.test')
            await state.add_company(c);records[name]=c
        for i in range(34):await state.add_company(Company(name=f'Other {i}',location='Berlin',industry='Other',domain=f'other{i}.test'))
        for name in ('A','C'):await state.save_public_company_emails(records[name].id,[f'info@{name.lower()}.test'],'https://source.test')
        await state.add_prospect(Prospect(first_name='Jane',last_name='Example',company_id=records['A'].id,email='jane@a.test'))
        await state.save_company_social_profiles(records['A'].id,[{'url':'https://linkedin.com/company/a','network':'LinkedIn','source_url':'https://a.test'}])
    asyncio.run(seed())
    monkeypatch.setattr(dashboard,'DB_PATH',tmp_path/'filters.db')
    with TestClient(dashboard.app) as client:yield client,state,records


def test_multi_values_or_fields_and_and_global_pagination(inventory):
    client,_,_=inventory
    data=client.get('/api/companies/page',params=[('locations','Berlin'),('locations','Hamburg'),('industries','Hotel')]).json()
    assert data['total']==2 and {r['name'] for r in data['items']}=={'A','B'}
    assert client.get('/api/companies/page?page=2').json()['total']==38
    assert len(client.get('/api/companies/page?page=2').json()['items'])==8
    assert {r['name'] for r in client.get('/api/companies/page',params={'location':'Berlin','industry':'Hotel'}).json()['items']}=={'A'}


def test_facet_counts_exclude_only_their_own_field(inventory):
    client,_,_=inventory
    data=client.get('/api/companies/page',params={'locations':'Berlin','industries':'Hotel','email':'without'}).json()
    assert data['total']==0
    assert data['facets']['email']=={'with':1,'without':0}
    loc={r['value']:r['count'] for r in data['facets']['locations']}
    assert loc['Berlin']==0 and loc['Hamburg']==1 and loc['Munich']==1


def test_extra_filters_and_injection_are_safe(inventory):
    client,_,_=inventory
    for field in ('profiles','people'):
        data=client.get('/api/companies/page',params={field:'with'}).json()
        assert [r['name'] for r in data['items']]==['A']
    assert client.get('/api/companies/page',params={'phone':'with','industries':'Hotel'}).json()['total']==2
    assert client.get('/api/companies/page',params={'source':'discover:osm'}).json()['items'][0]['name']=='B'
    assert client.get('/api/companies/page',params={'locations':"Berlin') OR 1=1 --"}).json()['total']==0
    assert client.get('/api/companies/page',params=[('locations','Berlin')]*51).status_code==422
    assert client.get('/api/companies/page?phone=anything').status_code==422


def test_saved_views_round_trip_duplicate_validation_and_delete(inventory):
    client,_,_=inventory
    filters={'locations':['Berlin','Hamburg'],'industries':['Hotel'],'email':'with','phone':'with'}
    response=client.post('/api/company-filter-views',json={'name':'Hotels','filters':filters})
    assert response.status_code==200
    view=response.json();assert view['filters']['locations']==['Berlin','Hamburg']
    assert client.get('/api/company-filter-views').json()[0]['id']==view['id']
    assert client.post('/api/company-filter-views',json={'name':'hotels','filters':filters}).status_code==409
    assert client.post('/api/company-filter-views',json={'name':'Bad','filters':{'sql':'DROP TABLE companies'}}).status_code==422
    assert client.delete('/api/company-filter-views/'+view['id']).status_code==200
    assert client.get('/api/company-filter-views').json()==[]
    assert client.get('/api/companies/page').json()['total']==38


def test_company_contacts_are_not_counted_as_named_people(inventory):
    client,state,records=inventory
    async def add():
        await state.add_prospect(Prospect(company_id=records['B'].id,contact_type='company',company='B',email='office@b.test',phone='444'))
    asyncio.run(add())
    data=client.get('/api/companies/page',params={'locations':'Hamburg','phone':'with','people':'without'}).json()
    assert data['total']==1
    assert data['facets']['people']=={'with':0,'without':1}
