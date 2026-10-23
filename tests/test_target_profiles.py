import asyncio
from datetime import datetime,timezone,timedelta
import pytest
from harvey.models import Company
from harvey.target_profiles import evaluate_profile
from tests.test_crm_actions import crm_client
from tests.test_outreach_history import sql


@pytest.fixture(autouse=True)
def signal_catalog(crm_client):
    crm_client[0].get('/api/signals')


def create(client,**kw):
    return client.post('/api/target-profiles',json={'name':'Local fit','require':['NO_WEBSITE'],**kw})


def test_profile_crud_validation_and_no_signal_activation(crm_client):
    client,sm=crm_client
    for payload in [{'name':''},{'require':['BAD']},{'exclude':['NO_WEBSITE']},{'max_age_days':True},{'require':'NO_WEBSITE'}]:
        assert create(client,**payload).status_code==422
    cid=create(client).json()['id']
    assert client.get('/api/target-profiles').json()[0]['id']==cid
    outcome=client.get(f'/api/target-profiles/{cid}/evaluate').json()
    assert outcome['counts']=={'match':0,'no_match':0,'unknown':1}
    assert outcome['items'][0]['evidence'][0]['reason']=='inactive_signal'
    assert client.delete('/api/target-profiles/'+cid).status_code==200
    assert client.get('/api/target-profiles').json()==[]
    assert client.get(f'/api/target-profiles/{cid}/evaluate').status_code==404


def test_boolean_true_false_missing_and_latest_evidence(crm_client):
    client,sm=crm_client
    sql(sm,"UPDATE signal_codes SET status='confirmed' WHERE code='NO_WEBSITE'")
    asyncio.run(sm.add_company(Company(id='false',name='False')))
    asyncio.run(sm.add_company(Company(id='unknown',name='Unknown')))
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='firm',value_num=1,evidence_url='https://firm.test/listing'))
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='false',value_num=1,observed_at='2020-01-01'))
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='false',value_num=0))
    cid=create(client).json()['id']
    data=client.get(f'/api/target-profiles/{cid}/evaluate').json()
    assert data['counts']=={'match':1,'no_match':1,'unknown':1}
    match=next(x for x in data['items'] if x['id']=='firm')
    assert match['evidence'][0]['source']=='https://firm.test/listing'
    assert data['policy']=='retain_all' and data['stage']=='after_import'
    assert client.get(f'/api/target-profiles/{cid}/evaluate?verdict=unknown').json()['total']==1


def test_exclusion_absence_is_unknown_not_a_match(crm_client):
    client,sm=crm_client
    sql(sm,"UPDATE signal_codes SET status='confirmed' WHERE code='NO_WEBSITE'")
    cid=create(client,require=[],exclude=['NO_WEBSITE']).json()['id']
    assert client.get(f'/api/target-profiles/{cid}/evaluate').json()['counts']['unknown']==1
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='firm',value_num=1))
    assert client.get(f'/api/target-profiles/{cid}/evaluate').json()['counts']['no_match']==1
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='firm',value_num=0))
    assert client.get(f'/api/target-profiles/{cid}/evaluate').json()['counts']['match']==1


@pytest.mark.parametrize('date,confidence,reason', [('2000-01-01',1,'stale'),('2999-01-01',1,'stale'),('invalid',1,'stale'),(None,0.1,'low_confidence')])
def test_stale_future_low_confidence_are_unknown(crm_client,date,confidence,reason):
    client,sm=crm_client
    sql(sm,"UPDATE signal_codes SET status='confirmed',confidence_floor=0.8 WHERE code='NO_WEBSITE'")
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='firm',value_num=1,observed_at=date,confidence=confidence))
    cid=create(client).json()['id'];data=client.get(f'/api/target-profiles/{cid}/evaluate').json()
    assert data['counts']['unknown']==1 and data['items'][0]['evidence'][0]['reason']==reason


def test_counts_are_uncapped_and_run_scope_does_not_include_backlog(crm_client):
    client,sm=crm_client
    async def seed():
        for i in range(35):await sm.add_company(Company(id=str(i),name=str(i)))
    asyncio.run(seed());cid=create(client).json()['id']
    data=client.get(f'/api/target-profiles/{cid}/evaluate').json()
    assert data['counts']['unknown']==36 and len(data['items'])==30 and data['pages']==2
    assert len(client.get(f'/api/target-profiles/{cid}/evaluate?page=2').json()['items'])==6
    report=asyncio.run(evaluate_profile(sm,{'id':cid,'name':'Scope','require':['NO_WEBSITE'],'exclude':[],'max_age_days':90},company_ids=['firm']))
    assert report['counts']['unknown']==1 and report['scope']=='search_run'
    assert client.get(f'/api/target-profiles/{cid}/evaluate?verdict=bad').status_code==422
