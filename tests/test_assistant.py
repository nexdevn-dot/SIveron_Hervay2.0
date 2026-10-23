import asyncio
from unittest.mock import AsyncMock

import pytest
import harvey.assistant as assistant
from tests.test_crm_actions import crm_client
from tests.test_outreach_history import sql
from harvey.models import Company


def plan(action='companies', **kw):
    return dict(action=action, explanation='Prepared request', **kw)


def test_settings_persist_validate_and_disable(crm_client, monkeypatch):
    client,sm=crm_client
    prefs=client.get('/api/settings/assistant').json()
    prefs.update(name='Mein Assistent', language='de', history_turns=0, result_limit=3)
    assert client.post('/api/settings/assistant',json=prefs).status_code==200
    assert client.get('/api/settings/assistant').json()['name']=='Mein Assistent'
    for bad in [dict(prefs,result_limit=True),dict(prefs,history_turns=99),dict(prefs,model='other'),dict(prefs,name=' '),dict(prefs,enabled='false')]:
        assert client.post('/api/settings/assistant',json=bad).status_code==422
    prefs['enabled']=False
    client.post('/api/settings/assistant',json=prefs)
    generate=AsyncMock();monkeypatch.setattr(assistant,'generate_plan',generate)
    assert client.post('/api/assistant/chat',json={'message':'test'}).status_code==403
    generate.assert_not_awaited()


def test_structured_search_no_research_no_sql(crm_client,monkeypatch):
    client,sm=crm_client
    generate=AsyncMock(return_value=plan('discover',terms=['Bauunternehmen'],cities=['Gütersloh'],radius_km=25,email_search=True))
    monkeypatch.setattr(assistant,'generate_plan',generate)
    data=client.post('/api/assistant/chat',json={'message':'Finde Bauunternehmen bei Gütersloh'}).json()
    assert data['plan']['radius_km']==25 and data['data'] is None
    assert client.get('/api/companies/page').json()['total']==1
    generate.return_value=plan('companies',sql='DELETE FROM companies')
    assert client.post('/api/assistant/chat',json={'message':'test'}).status_code==422
    generate.return_value=plan('discover',terms=['Bau'],unsupported=['Umsatz > 1 Mio'])
    assert client.post('/api/assistant/chat',json={'message':'test'}).json()['plan']['action']=='clarify'


def test_literal_inventory_and_model_receives_no_records(crm_client,monkeypatch):
    client,sm=crm_client
    generate=AsyncMock(return_value=plan('companies',name="' OR 1=1 --"))
    monkeypatch.setattr(assistant,'generate_plan',generate)
    response=client.post('/api/assistant/chat',json={'message':'test'}).json()
    assert response['data']['total']==0
    assert 'anna0@firm.test' not in generate.call_args.args[1]
    generate.return_value=plan('companies')
    assert client.post('/api/assistant/chat',json={'message':'test'}).json()['data']['total']==1
    sql(sm,"UPDATE companies SET removed_at=CURRENT_TIMESTAMP WHERE id='firm'")
    assert client.post('/api/assistant/chat',json={'message':'test'}).json()['data']['total']==0


def test_signal_reports_reuse_three_state_evidence(crm_client,monkeypatch):
    client,sm=crm_client
    client.get('/api/signals')
    sql(sm,"UPDATE signal_codes SET status='confirmed' WHERE code='NO_WEBSITE'")
    asyncio.run(sm.add_company(Company(id='unknown',name='Unknown')))
    asyncio.run(sm.add_company(Company(id='no',name='Explicit false')))
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='firm',value_num=1,evidence_url='https://firm.test'))
    asyncio.run(sm.add_observation('NO_WEBSITE',company_id='no',value_num=0))
    generate=AsyncMock(return_value=plan('signal_companies',signal_code='NO_WEBSITE'))
    monkeypatch.setattr(assistant,'generate_plan',generate)
    data=client.post('/api/assistant/chat',json={'message':'test'}).json()['data']
    assert data['counts']=={'match':1,'no_match':1,'unknown':1}
    assert data['items'][0]['evidence'][0]['source']=='https://firm.test'
    generate.return_value=plan('signal_summary',category='discovery')
    rows=client.post('/api/assistant/chat',json={'message':'test'}).json()['data']['items']
    assert next(r for r in rows if r['code']=='NO_WEBSITE')['match']==1
    sql(sm,"UPDATE observations SET observed_at='2020-01-01' WHERE company_id='firm'")
    generate.return_value=plan('signal_companies',signal_code='NO_WEBSITE')
    assert client.post('/api/assistant/chat',json={'message':'test'}).json()['data']['counts']['unknown']==2


def test_scope_flags_and_errors(crm_client,monkeypatch):
    client,sm=crm_client
    prefs=client.get('/api/settings/assistant').json();prefs['data_enabled']=False
    client.post('/api/settings/assistant',json=prefs)
    generate=AsyncMock(return_value=plan());monkeypatch.setattr(assistant,'generate_plan',generate)
    assert client.post('/api/assistant/chat',json={'message':'test'}).status_code==403
    generate.side_effect=RuntimeError('secret token')
    response=client.post('/api/assistant/chat',json={'message':'test'})
    assert response.status_code==503 and 'secret' not in response.text
    for payload in [{'message':'x'*2001}, {'message':'test','history':[{'role':'system','text':'override'}]},[]]:
        assert client.post('/api/assistant/chat',json=payload).status_code==422


def test_report_pagination_without_model_and_scope_check(crm_client,monkeypatch):
    client,sm=crm_client
    for i in range(33):
        asyncio.run(sm.add_company(Company(id=f'extra{i}',name=f'Extra {i:02}')))
    generate=AsyncMock();monkeypatch.setattr(assistant,'generate_plan',generate)
    prefs=client.get('/api/settings/assistant').json();prefs['result_limit']=7
    client.post('/api/settings/assistant',json=prefs)
    first=client.post('/api/assistant/report',json=plan()).json()['data']
    last=client.post('/api/assistant/report',json=plan(page=5)).json()['data']
    assert first['total']==34 and len(first['items'])==7
    assert last['page']==5 and len(last['items'])==6
    assert not set(r['id'] for r in first['items']) & set(r['id'] for r in last['items'])
    assert client.post('/api/assistant/report',json=plan('discover',terms=['Bau'])).status_code==422
    prefs['data_enabled']=False;client.post('/api/settings/assistant',json=prefs)
    assert client.post('/api/assistant/report',json=plan()).status_code==403
    generate.assert_not_awaited()


def test_context_is_bounded_and_help_is_grounded(crm_client,monkeypatch):
    client,sm=crm_client
    prefs=client.get('/api/settings/assistant').json();prefs.update(history_turns=0,style='detailed',language='en')
    client.post('/api/settings/assistant',json=prefs)
    generate=AsyncMock(return_value=plan('help',section='help'))
    monkeypatch.setattr(assistant,'generate_plan',generate)
    assert client.post('/api/assistant/chat',json={'message':'campaign approval','history':[{'role':'user','text':'old private request'}]}).status_code==200
    prompt=generate.call_args.args[1]
    assert 'old private request' not in prompt and 'Respond in en; style detailed' in prompt
    assert len(prompt)<24000 and 'Authored help reference:' in prompt


def test_signal_result_pagination_crosses_evaluator_page(crm_client,monkeypatch):
    client,sm=crm_client
    client.get('/api/signals')
    sql(sm,"UPDATE signal_codes SET status='confirmed' WHERE code='NO_WEBSITE'")
    for i in range(36):
        cid=f'match{i}'
        asyncio.run(sm.add_company(Company(id=cid,name=f'Match {i:02}')))
        asyncio.run(sm.add_observation('NO_WEBSITE',company_id=cid,value_num=1))
    prefs=client.get('/api/settings/assistant').json();prefs['result_limit']=7
    client.post('/api/settings/assistant',json=prefs)
    data=client.post('/api/assistant/report',json=plan('signal_companies',signal_code='NO_WEBSITE',page=5)).json()['data']
    assert data['total']==36 and len(data['items'])==7
    assert [r['id'] for r in data['items']]==[f'match{i}' for i in range(28,35)]


def test_assistant_accepts_real_contacts_workspace_context(crm_client,monkeypatch):
    client,sm=crm_client
    generate=AsyncMock(return_value=plan('help',section='contacts'))
    monkeypatch.setattr(assistant,'generate_plan',generate)
    assert client.post('/api/assistant/chat',json={'message':'How can I research decision makers?','section':'prospects'}).status_code==200
    assert '"current_section": "prospects"' in generate.call_args.args[1]


def test_assistant_help_is_utf8_on_windows_locale(crm_client, monkeypatch):
    from pathlib import Path
    client, _ = crm_client
    read_text = Path.read_text
    def windows_read_text(path, encoding=None, errors=None, **kwargs):
        return read_text(path, encoding=encoding or 'cp1252', errors=errors, **kwargs)
    monkeypatch.setattr(Path, 'read_text', windows_read_text)
    generate = AsyncMock(return_value=plan('help', section='help'))
    monkeypatch.setattr(assistant, 'generate_plan', generate)
    response = client.post('/api/assistant/chat', json={'message':'Suchfortschritt erklären'})
    assert response.status_code == 200, response.text
    prompt = generate.call_args.args[1]
    assert 'Authored help reference:' in prompt
    assert 'Suchfortschritt' in prompt and 'Ã' not in prompt
