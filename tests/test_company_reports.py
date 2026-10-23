"""Company reports retain evidence semantics and never initiate outreach."""
import asyncio
from datetime import datetime,timezone,timedelta
import json
import pytest
from harvey import company_reports as reports
from harvey.signals import seed_signal_catalog
from tests.test_people_contacts import setup_contacts

async def evidence(sm,code,value=1,*,age=0,source='https://acme.test',confidence=1,active=True):
    import uuid
    await seed_signal_catalog(sm)
    async with sm._connect() as db:
        await db.execute('UPDATE signal_codes SET status=?,confidence_floor=0.5 WHERE code=?',('confirmed' if active else 'proposed',code))
        await db.execute('INSERT INTO observations(id,company_id,signal_code,value_num,confidence,evidence_url,observed_at) VALUES (?,?,?,?,?,?,?)',(uuid.uuid4().hex,'acme',code,value,confidence,source,(datetime.now(timezone.utc)-timedelta(days=age)).isoformat()))
        await db.commit()

def create(client,**extra):
    return client.post('/api/company-reports',json=dict(company_ids=['acme'],categories=['profile','discovery'],language='de',**extra))

def test_saved_report_explicit_positives_negatives_and_missing(setup_contacts):
    client,sm=setup_contacts
    asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    asyncio.run(evidence(sm,'NO_ONLINE_BOOKING',0))
    result=create(client);assert result.status_code==200,result.text
    report=result.json()['reports'][0];facts={e['code']:e for e in report['findings']}
    assert facts['NO_SCHEMA_MARKUP']['section']=='potential'
    assert facts['NO_ONLINE_BOOKING']['section']=='context'
    assert facts['NO_WEBSITE']['section']=='unknown'
    assert report['counts']['potential']==1
    assert client.get('/api/prospects').json()==[] and asyncio.run(sm.get_outbox())==[]
    stored=client.get('/api/company-reports/'+report['id']).json()
    assert stored['company']['name']=='Acme' and stored['max_age_days']==90

@pytest.mark.parametrize('kwargs,reason',[({'age':100},'stale'),({'age':-1},'stale'),({'confidence':0.1},'low_confidence'),({'active':False},'inactive_signal'),({'source':''},'missing_source'),({'source':'javascript:alert(1)'},'missing_source')])
def test_unusable_facts_never_become_opportunities(setup_contacts,kwargs,reason):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP',**kwargs))
    fact=next(e for e in create(client).json()['reports'][0]['findings'] if e['code']=='NO_SCHEMA_MARKUP')
    assert fact['section']=='unknown' and fact['reason']==reason

def test_latest_negative_does_not_fall_back_to_positive_and_snapshot_persists(setup_contacts):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP',age=2))
    first=create(client).json()['reports'][0]
    asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP',0))
    second=create(client).json()['reports'][0]
    assert first['counts']['potential']==1 and second['counts']['potential']==0
    assert client.get('/api/company-reports/'+first['id']).json()['counts']['potential']==1
    history=client.get('/api/company-reports/history?company_id=acme').json()
    assert [h['id'] for h in history]==[second['id'],first['id']]

@pytest.mark.parametrize('body',[{}, {'company_ids':[],'categories':['profile']},{'company_ids':['missing'],'categories':['profile']},{'company_ids':['acme']*21,'categories':['profile']},{'company_ids':['acme'],'categories':[]},{'company_ids':['acme'],'categories':['bad']},{'company_ids':['acme'],'categories':['profile'],'max_age_days':True},{'company_ids':['acme'],'categories':['profile'],'language':'xx'},{'company_ids':['acme'],'categories':['profile'],'send':True}])
def test_invalid_requests_do_not_create_reports(setup_contacts,body):
    client,sm=setup_contacts
    assert client.post('/api/company-reports',json=body).status_code==422
    assert client.get('/api/company-reports/history?company_id=acme').json()==[]


def test_exports_escaped_and_removed_company_hidden(setup_contacts):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    async def rename():
        async with sm._connect() as db:
            await db.execute("UPDATE companies SET name=? WHERE id='acme'",('<script>alert(1)</script>',));await db.commit()
    asyncio.run(rename())
    r=create(client).json()['reports'][0];base='/api/company-reports/'+r['id']
    preview=client.get(base+'/preview');assert '<script>alert(1)</script>' not in preview.text and '&lt;script&gt;' in preview.text
    assert 'window.print' not in preview.text
    assert 'window.print' in client.get(base+'/preview?printing=true').text
    exported=client.get(base+'/markdown');assert exported.status_code==200 and 'attachment' in exported.headers['content-disposition']
    assert 'Ansatzpunkte' in exported.text and 'https://acme.test' in exported.text
    async def remove():
        async with sm._connect() as db:
            await db.execute("UPDATE companies SET removed_at=CURRENT_TIMESTAMP WHERE id='acme'");await db.commit()
    asyncio.run(remove())
    assert client.get(base).status_code==404 and client.get(base+'/markdown').status_code==404
    assert client.get('/api/company-reports/history?company_id=acme').json()==[]


def test_english_report_and_batched_company_isolation(setup_contacts):
    from harvey.models import Company
    client,sm=setup_contacts
    asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    asyncio.run(sm.add_company(Company(id='other',name='Other',domain='other.test')))
    result=client.post('/api/company-reports',json={'company_ids':['acme','other'],'categories':['profile'],'language':'en'}).json()['reports']
    assert len(result)==2 and result[0]['counts']['potential']==1 and result[1]['counts']['potential']==0
    text=client.get('/api/company-reports/'+result[0]['id']+'/markdown').text
    assert 'Opportunities to review' in text and 'Review structured data' in text


def ai_result(codes=('NO_SCHEMA_MARKUP',)):
    return {'text':'Einordnung gespeicherter Signale; keine gemessene Sichtbarkeit.',
            'codes':list(codes),'impacts':[dict(code=code,visibility='Kann die Einordnung von Informationen unterstützen.',
            ai_search='Für KI-Suche gelten grundlegende Anforderungen; es gibt keine Aufnahmegarantie.',
            acquisition='Ein verständliches Angebot kann passende Anfragen erleichtern; der Effekt ist nicht gemessen.',
            next_step='Quelle und sichtbare Angaben prüfen.',limitation='Der gespeicherte HTML-Befund ist keine vollständige Website-Prüfung.') for code in codes]}


def test_ai_uses_existing_boundary_is_optional_and_caches(setup_contacts,monkeypatch):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    r=create(client).json()['reports'][0];calls=[]
    async def fake(self,prompt,**kw):
        calls.append((prompt,kw));return ai_result()
    monkeypatch.setattr('harvey.brain.Brain.think_json',fake)
    url='/api/company-reports/'+r['id']+'/explain'
    assert client.get('/api/company-reports/'+r['id']).json()['ai'] is None
    assert client.post(url).json()['ai']['codes']==['NO_SCHEMA_MARKUP']
    assert client.post(url).json()['ai']['text'] and len(calls)==1
    assert 'No tools' in calls[0][0] and calls[0][1]['agent']=='company_reports'


def test_invalid_ai_does_not_destroy_facts(setup_contacts,monkeypatch):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    r=create(client).json()['reports'][0]
    async def invalid(*args,**kw):return {'text':'Unsupported claim','codes':['INVENTED']}
    monkeypatch.setattr('harvey.brain.Brain.think_json',invalid)
    base='/api/company-reports/'+r['id']
    assert client.post(base+'/explain').status_code==503
    retained=client.get(base).json()
    assert retained['ai'] is None and retained['counts']['potential']==1


@pytest.mark.parametrize('language',['de','en'])
def test_ai_sections_exported_and_general_sources_are_not_company_evidence(setup_contacts,monkeypatch,language):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    r=client.post('/api/company-reports',json={'company_ids':['acme'],'categories':['profile'],'language':language}).json()['reports'][0]
    async def fake(*args,**kwargs):return ai_result()
    monkeypatch.setattr('harvey.brain.Brain.think_json',fake)
    base='/api/company-reports/'+r['id']
    result=client.post(base+'/explain').json()
    assert result['ai']['version']==2
    assert len(result['ai']['sources'])==2
    preview=client.get(base+'/preview').text;md=client.get(base+'/markdown').text
    for label in ([labels[language=='en'] for labels in reports.IMPACT_FIELDS.values()]+['Fachliche Grundlagen (keine Unternehmensbelege)' if language=='de' else 'Background guidance (not company evidence)']):
        assert label in preview and label in md
    assert result['findings']==r['findings']


@pytest.mark.parametrize('defect',['missing_section','unknown_code','duplicate','too_long','empty'])
def test_ai_rejects_incomplete_or_misattributed_impacts(setup_contacts,monkeypatch,defect):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    r=create(client).json()['reports'][0];data=ai_result()
    if defect=='missing_section':del data['impacts'][0]['ai_search']
    elif defect=='unknown_code':data['impacts'][0]['code']='NOT_OBSERVED'
    elif defect=='duplicate':data['impacts'].append(data['impacts'][0])
    elif defect=='too_long':data['impacts'][0]['acquisition']='X'*401
    else:data['impacts'][0]['limitation']=' '
    async def fake(*args,**kwargs):return data
    monkeypatch.setattr('harvey.brain.Brain.think_json',fake)
    base='/api/company-reports/'+r['id']
    assert client.post(base+'/explain').status_code==503
    assert client.get(base).json()['ai'] is None


def test_legacy_ai_can_be_explicitly_extended_and_preserved_on_failure(setup_contacts,monkeypatch):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP'))
    r=create(client).json()['reports'][0];base='/api/company-reports/'+r['id']
    async def old():
        async with sm._connect() as db:
            await db.execute('UPDATE company_reports SET ai_json=? WHERE id=?',(json.dumps({'text':'Vorherige Erläuterung','codes':['NO_SCHEMA_MARKUP']}),r['id']));await db.commit()
    asyncio.run(old());calls=[]
    async def invalid(*args,**kwargs):calls.append(1);return {}
    monkeypatch.setattr('harvey.brain.Brain.think_json',invalid)
    assert client.get(base).json()['ai']['text']=='Vorherige Erläuterung' and calls==[]
    assert client.post(base+'/explain').status_code==503
    assert client.get(base).json()['ai']['text']=='Vorherige Erläuterung'
    async def valid(*args,**kwargs):calls.append(1);return ai_result()
    monkeypatch.setattr('harvey.brain.Brain.think_json',valid)
    assert client.post(base+'/explain').json()['ai']['version']==2
    assert client.post(base+'/explain').status_code==200 and len(calls)==2


def test_ai_scope_bounded_excludes_unknown_and_handles_negative_facts(setup_contacts,monkeypatch):
    client,sm=setup_contacts;asyncio.run(evidence(sm,'NO_SCHEMA_MARKUP',0))
    r=create(client).json()['reports'][0];prompts=[]
    async def fake(self,prompt,**kwargs):prompts.append(prompt);return ai_result()
    monkeypatch.setattr('harvey.brain.Brain.think_json',fake)
    client.post('/api/company-reports/'+r['id']+'/explain')
    facts=json.loads(prompts[0].split('DATA: ',1)[1])
    assert len(facts)==1 and facts[0]['value_num']==0
    assert 'negative observations must never be inverted into defects' in prompts[0]
    assert 'GPTBot' in prompts[0] and 'no required special AI schema' in prompts[0]
    assert 'conditional' in prompts[0] and 'no demonstrated direct relevance' in prompts[0]
