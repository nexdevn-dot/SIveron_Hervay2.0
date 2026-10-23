import asyncio
import json

import pytest
from harvey.decision_makers import criteria,qualify,qualify_job
from harvey.collectors.contact_jobs import ContactJobs
from harvey.collectors import people
from tests.test_people_contacts import setup_contacts


@pytest.mark.parametrize('title,role,verdict',[
 ('Geschäftsführerin','management','match'),('Geschaeftsfuehrer','management','match'),
 ('Head of Sales','sales','match'),('Marketing Manager','marketing','match'),('IT-Leiterin','it','match'),
 ('Assistant to CEO','management','no_match'),('Former CFO','finance','no_match'),
 ('Marketing Assistant','marketing','no_match'),('Software Engineer','it','unknown'),
 ('Manager','sales','unknown'),('','management','unknown'),('Chief Technology Officer','it','match')])
def test_published_role_fit_never_guesses_authority(title,role,verdict):
 assert qualify(title,criteria({'roles':[role]}))['verdict']==verdict


def test_criteria_strict():
 for payload in [{'roles':[]},{'roles':['bad']},{'roles':'management'},{'roles':[True]},{'roles':['management'],'auto_send':True}]:
  with pytest.raises(ValueError):criteria(payload)


async def seed_job(sm,jid='decision-test',chosen=None,cids=('candidate',)):
 chosen=chosen or {'roles':['management']}
 async with sm._connect() as db:
  await db.execute("INSERT INTO company_people_jobs(id,status,criteria_json) VALUES (?,'completed',?)",(jid,json.dumps(chosen)))
  await db.execute("INSERT INTO company_people_job_items(job_id,company_id,status) VALUES (?,'acme','found')",(jid,))
  await db.commit()
 await qualify_job(sm,jid,'acme',cids,chosen)


def test_results_and_idempotent_reviewed_contact_handover(setup_contacts):
 client,sm=setup_contacts
 asyncio.run(seed_job(sm))
 data=client.get('/api/decision-makers/results?job_id=decision-test').json()
 assert data['counts']=={'match':1,'unknown':0,'no_match':0}
 person=data['items'][0]
 assert person['fit']['reason']=='published_title_matches' and not person['snapshot_changed']
 assert person['source_url']=='https://acme.test/team'
 assert client.get('/api/prospects').json()==[]
 payload={'job_id':'decision-test','candidate_ids':['candidate']}
 assert client.post('/api/decision-makers/adopt',json=payload).status_code==422
 result=client.post('/api/decision-makers/adopt',json=dict(payload,reviewed=True)).json()['items'][0]
 assert result['status']=='created'
 assert client.post('/api/decision-makers/adopt',json=dict(payload,reviewed=True)).json()['items'][0]['status']=='duplicate'
 contact=asyncio.run(sm.get_prospect(result['contact_id']))
 assert contact.source=='public_person' and contact.company_id=='acme' and not contact.email_verified
 assert contact.email=='julia@acme.test' and contact.source_url=='https://acme.test/team'
 assert asyncio.run(sm.get_outbox())==[]
 assert client.get('/api/decision-makers/results?job_id=decision-test').json()['total']==0


def test_exact_job_scope_snapshot_and_removed_company(setup_contacts):
 client,sm=setup_contacts
 asyncio.run(seed_job(sm,cids=()))
 assert client.get('/api/decision-makers/results?job_id=decision-test').json()['total']==0
 assert client.post('/api/decision-makers/adopt',json={'job_id':'decision-test','candidate_ids':['candidate'],'reviewed':True}).json()['items'][0]['status']=='unavailable'
 asyncio.run(qualify_job(sm,'decision-test','acme',['candidate'],{'roles':['management']}))
 async def change():
  async with sm._connect() as db:
   await db.execute("UPDATE person_candidates SET title='Former CEO',email='other@acme.test' WHERE id='candidate'");await db.commit()
 asyncio.run(change())
 row=client.get('/api/decision-makers/results?job_id=decision-test').json()['items'][0]
 assert row['snapshot_changed'] and row['title']=='Geschäftsführerin' and row['email']=='julia@acme.test'
 assert client.post('/api/decision-makers/adopt',json={'job_id':'decision-test','candidate_ids':['candidate'],'reviewed':True}).json()['items'][0]['status']=='review_required'
 async def remove():
  async with sm._connect() as db:
   await db.execute("UPDATE companies SET removed_at=CURRENT_TIMESTAMP WHERE id='acme'");await db.commit()
 asyncio.run(remove())
 assert client.get('/api/decision-makers/results?job_id=decision-test').json()['total']==0


def test_unknown_person_can_be_reviewed_and_imported_without_email(setup_contacts):
 client,sm=setup_contacts
 async def blank():
  async with sm._connect() as db:
   await db.execute("UPDATE person_candidates SET title='',email='' WHERE id='candidate'");await db.commit()
 asyncio.run(blank());asyncio.run(seed_job(sm))
 assert client.get('/api/decision-makers/results?job_id=decision-test').json()['counts']['unknown']==1
 result=client.post('/api/decision-makers/adopt',json={'job_id':'decision-test','candidate_ids':['candidate'],'reviewed':True}).json()['items'][0]
 assert result['status']=='created' and not asyncio.run(sm.get_prospect(result['contact_id'])).email


@pytest.mark.asyncio
async def test_job_reuses_collector_and_persists_only_this_run_candidates(tmp_path,monkeypatch):
 from harvey.state import StateManager
 from harvey.models import Company
 sm=StateManager(str(tmp_path/'decision.db'));await sm.init_db()
 await sm.add_company(Company(id='firm',name='Firm',domain='firm.test'))
 async def lookup(company,state,include_candidate_ids=False):
  assert include_candidate_ids
  async with state._connect() as db:
   await db.execute("INSERT INTO person_candidates(id,company_id,first_name,last_name,title,source_url) VALUES ('new','firm','Alex','Test','Head of Sales','https://firm.test/team')")
   await db.commit()
  return {'status':'found','found':1,'candidate_ids':['new']}
 monkeypatch.setattr(people,'lookup_company_people',lookup)
 service=ContactJobs(sm,kind='people');jid=await service.create(['firm'],people_criteria={'roles':['sales']});await service.task
 snapshot=await service.snapshot(jid)
 assert snapshot['status']=='completed' and json.loads(snapshot['criteria_json'])=={'roles':['sales']}
 async with sm._connect() as db:
  rows=await (await db.execute('SELECT verdict,fit_json FROM decision_maker_results WHERE job_id=?',(jid,))).fetchall()
 assert len(rows)==1 and rows[0][0]=='match'
 assert await sm.get_prospect('new') is None
