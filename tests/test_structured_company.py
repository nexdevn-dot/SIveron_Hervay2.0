import asyncio
import json
import pytest
from harvey.collectors.structured_company import extract_company_fields,save_structured_fields
from harvey.models import Company
from tests.test_crm_actions import crm_client


def page(nodes):return '<script type="application/ld+json">'+json.dumps({'@graph':nodes})+'</script>'


def example():return page([
 {'@type':'Organization','@id':'#company','name':'Demo Company','url':'https://firm.test/',
  'address':{'@id':'#address'},'contactPoint':[{'@id':'#sales'}]},
 {'@type':'PostalAddress','@id':'#address','streetAddress':'Example 1','postalCode':'12345','addressLocality':'Berlin'},
 {'@type':'ContactPoint','@id':'#sales','contactType':'Sales','telephone':'+49 123456789','email':'sales@firm.test'},
 {'@type':'Organization','name':'Unrelated Agency','url':'https://agency.test','telephone':'+49 999999999'},
 {'@type':'Person','name':'Unknown Author','email':'author@firm.test'}])


def test_graph_contact_points_and_address_are_explicit_and_sources_retained():
    fields=extract_company_fields(example(),'https://firm.test/contact?token=hidden','firm.test','Demo Company')
    assert {(f['field'],f['value']) for f in fields}=={
      ('phone','+49 123456789'),('email','sales@firm.test'),('location','Example 1, 12345 Berlin')}
    assert all(f['source_url']=='https://firm.test/contact' for f in fields)
    assert all(f['entity']=='Demo Company' for f in fields)
    assert next(f for f in fields if f['field']=='email')['contact_label']=='Sales'


def test_microdata_and_unrelated_entities():
    html='<div itemscope itemtype="https://schema.org/LocalBusiness"><span itemprop="name">Demo Company</span><span itemprop="telephone">+49 12345678</span></div>'
    assert extract_company_fields(html,'https://firm.test/','firm.test','Demo Company')[0]['field']=='phone'
    assert not extract_company_fields(html,'https://firm.test/','firm.test','Different Company')
    assert not extract_company_fields('<script>var email="fake@firm.test";</script>','https://firm.test/','firm.test','Demo Company')


def test_field_review_preserves_data_until_acceptance_and_detects_conflicts(crm_client):
    client,state=crm_client
    company=Company(id='structured',name='Demo Company',domain='demo.test',phone='old phone',location='Old address')
    async def seed():
        await state.add_company(company)
        await save_structured_fields(state,company,example().replace('firm.test','demo.test'),'https://demo.test/contact')
        await save_structured_fields(state,company,example().replace('firm.test','demo.test'),'https://demo.test/contact')
    asyncio.run(seed())
    detail=client.get('/api/companies/structured/profile').json()
    assert detail['company']['phone']=='old phone' and not detail['contacts']
    fields=detail['field_candidates'];assert len(fields)==3
    phone=next(f for f in fields if f['field']=='phone')
    url='/api/company-field-candidates/'+phone['id']+'/review'
    assert client.post(url,json={'action':'accept','expected_value':''}).status_code==409
    assert client.post(url,json={'action':'accept','expected_value':'old phone'}).json()['status']=='accepted'
    assert client.post(url,json={'action':'accept','expected_value':'old phone'}).status_code==409
    email=next(f for f in fields if f['field']=='email')
    assert client.post('/api/company-field-candidates/'+email['id']+'/review',json={'action':'accept','expected_value':''}).status_code==200
    detail=client.get('/api/companies/structured/profile').json()
    assert detail['company']['phone']=='+49 123456789'
    assert detail['company']['contact_emails'][0]['status']!='verified'
    assert detail['company']['location']=='Old address' and not detail['contacts']
    address=next(f for f in fields if f['field']=='location')
    assert client.post('/api/company-field-candidates/'+address['id']+'/review',json={'action':'dismiss','expected_value':'Old address'}).status_code==200
    assert not client.get('/api/companies/structured/profile').json()['field_candidates']
    assert asyncio.run(state.get_outbox())==[]


def test_ambiguous_references_and_broken_urls_do_not_assign_contacts():
    html=page([{'@type':'Organization','name':'Demo Company','contactPoint':{'@id':'#contact'}},
      {'@id':'#contact','telephone':'+49 111111111'},
      {'@id':'#contact','telephone':'+49 222222222'},
      {'@type':'Organization','name':'Unknown','url':'http://[broken','telephone':'+49 33333333'}])
    assert extract_company_fields(html,'https://firm.test/','firm.test','Demo Company')==[]


def test_invalid_review_and_removed_company_cannot_be_adopted(crm_client):
    client,state=crm_client
    assert client.post('/api/company-field-candidates/missing/review',json={}).status_code==422
    assert client.post('/api/company-field-candidates/missing/review',json={'action':'accept','expected_value':''}).status_code==404
    async def seed():
        company=Company(id='removed-structured',name='Demo Company',domain='removed.test')
        await state.add_company(company)
        await save_structured_fields(state,company,example().replace('firm.test','removed.test'),'https://removed.test/')
        async with state._connect() as db:
            candidate=(await (await db.execute('SELECT id FROM company_field_candidates WHERE company_id=?',(company.id,))).fetchone())[0]
            await db.execute('UPDATE companies SET removed_at=CURRENT_TIMESTAMP WHERE id=?',(company.id,))
            await db.commit()
            return candidate
    candidate=asyncio.run(seed())
    assert client.post('/api/company-field-candidates/'+candidate+'/review',json={'action':'accept','expected_value':''}).status_code==404
