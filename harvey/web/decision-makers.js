/* Target roles -> official-site research -> explained fit -> explicit Contacts adoption. */
let dmRoles=[],dmCompanies=new Map(),dmCompanyRows=[],dmJob=null,dmRows=[],dmSelected=new Set(),dmPage=1,dmTimer=null,dmLookupTimer=null,dmLookupRequest=0,dmBusy=false,dmRefreshBusy=false,dmRefreshAgain=false;
const dt=(de,en)=>window.harveyLanguage?.()==='de'?de:en;
function dmText(parent,text,tag='p'){const e=document.createElement(tag);e.textContent=text;parent.append(e);return e;}
function dmButton(text,fn){const b=document.createElement('button');b.type='button';b.className='btn btn-secondary btn-sm';b.textContent=text;b.onclick=fn;return b;}
function dmError(text){document.getElementById('dm-error').textContent=text;}
function dmRoleName(id){const role=dmRoles.find(r=>r.id===id);return role?.[window.harveyLanguage?.()||'en']||id;}
async function openDecisionMakerSearch(ids=[]){
 document.getElementById('company-actions-panel')?.hidePopover?.();
 const dialog=document.getElementById('decision-maker-dialog');if(!dialog.open)dialog.showModal();
 dmLabels();dmError('');dmCompanies=new Map();dmSelected.clear();
 try{dmRoles=await contactRequest('/api/decision-makers/roles');
 const roleBox=document.getElementById('dm-roles');roleBox.replaceChildren();for(const role of dmRoles){const label=document.createElement('label');const c=document.createElement('input');c.type='checkbox';c.name='dm-role';c.value=role.id;c.checked=role.id==='management';label.append(c,' '+dmRoleName(role.id));roleBox.append(label);}
 for(const id of ids){const known=_companySelection.get(id)||_companies.find(c=>c.id===id);if(known)dmCompanies.set(id,known.name);else{const data=await contactRequest('/api/companies/'+encodeURIComponent(id)+'/profile');dmCompanies.set(id,data.company.name);}}
 dmRenderSelected();await dmFindCompanies();const last=await contactRequest('/api/decision-makers/latest');if(last){dmJob=last;if(!ids.length)dmCompanies=new Map(last.items.map(c=>[c.company_id,c.name]));const chosen=JSON.parse(last.criteria_json).roles;for(const c of document.querySelectorAll('#dm-roles input'))c.checked=chosen.includes(c.value);dmRenderSelected();dmRenderCompanies();document.getElementById('dm-criteria').open=false;await dmRefresh();}else{document.getElementById('dm-criteria').open=true;dmJob=null;dmRenderResults(null);}
 }catch{dmError(dt('Recherche konnte nicht geladen werden. Bitte erneut öffnen.','Research could not be loaded. Reopen this window.'));}
 document.getElementById(document.getElementById('dm-criteria').open?'dm-company-query':'dm-filter').focus();
}
function dmLabels(){
 document.getElementById('dm-title').textContent=dt('B2B-Entscheider recherchieren','Research B2B decision makers');
 for(const [id,de,en] of [['dm-close','Schließen','Close'],['dm-source','Quelle: öffentliche Unternehmensseiten. Rollen sind Hinweise, keine bestätigte Entscheidungsbefugnis. Persönliche E-Mails werden nur bei eindeutiger Zuordnung übernommen.','Source: public company websites. Roles are hints, not confirmed purchasing authority. Personal emails require an explicit association.'],['dm-company-label','Unternehmen suchen und auswählen','Search and select companies'],['dm-role-legend','Gesuchte Zielrollen','Target roles'],['dm-criteria-summary','Suchkriterien bearbeiten','Edit search criteria'],['dm-start','Recherche starten','Start research'],['dm-stop','Suche anhalten','Stop search'],['dm-filter-label','Rollenpassung','Role fit'],['dm-review-label','Ich habe die Rollen und Originalquellen der ausgewählten Personen geprüft.','I reviewed the roles and original sources of the selected people.'],['dm-adopt','Auswahl in Kontakte übernehmen','Add selected people to Contacts'],['dm-open-contacts','Kontakte öffnen','Open Contacts']])document.getElementById(id).textContent=dt(de,en);
 const filter=document.getElementById('dm-filter');const val=filter.value;filter.replaceChildren();for(const [value,label] of [['match',dt('Passende Rollen','Matching roles')],['unknown',dt('Rolle nicht belegt','Role not established')],['no_match',dt('Keine aktuelle Zielrolle','Not a current target role')],['all',dt('Alle Vorschläge','All suggestions')]]){const option=document.createElement('option');option.value=value;option.textContent=label;filter.append(option);}filter.value=val||'match';
}
function dmRenderSelected(){
 const box=document.getElementById('dm-selected-companies');box.replaceChildren();
 dmText(box,dt('Ausgewählte Unternehmen: ','Selected companies: ')+dmCompanies.size);
 for(const [id,name] of dmCompanies)box.append(dmButton(name+' ×',()=>{dmCompanies.delete(id);dmRenderSelected();dmRenderCompanies();}));
}
async function dmFindCompanies(){
 const seq=++dmLookupRequest;try{const rows=await contactRequest('/api/contact-company-options?q='+encodeURIComponent(document.getElementById('dm-company-query').value));if(seq!==dmLookupRequest)return;dmCompanyRows=rows;dmRenderCompanies();}catch{dmError(dt('Unternehmen konnten nicht geladen werden.','Companies could not be loaded.'));}
}
function dmScheduleCompanies(){clearTimeout(dmLookupTimer);dmLookupTimer=setTimeout(dmFindCompanies,250);}
function dmRenderCompanies(){const box=document.getElementById('dm-company-options');box.replaceChildren();for(const company of dmCompanyRows){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=dmCompanies.has(company.id);input.onchange=()=>{if(input.checked)dmCompanies.set(company.id,company.name);else dmCompanies.delete(company.id);dmRenderSelected();};label.append(input,' '+company.name);box.append(label);}if(!dmCompanyRows.length)dmText(box,dt('Keine Unternehmen gefunden. Lege Unternehmen zuerst unter Entdecken oder Unternehmen an.','No companies found. Add companies through Discover or Companies first.'));}
async function dmStart(){
 if(dmBusy)return;const roles=[...document.querySelectorAll('#dm-roles input:checked')].map(e=>e.value);dmError('');
 if(!dmCompanies.size||!roles.length){dmError(dt('Bitte mindestens ein Unternehmen und eine Zielrolle auswählen.','Select at least one company and target role.'));return;}
 dmBusy=true;document.getElementById('dm-start').disabled=true;dmSelected.clear();dmPage=1;
 try{dmJob=await contactPost('/api/company-people-jobs',{company_ids:[...dmCompanies.keys()],decision_makers:{roles}});peopleOpenedJob=dmJob.id;document.getElementById('dm-criteria').open=false;await dmRefresh();}
 catch(e){dmError(e.message);}finally{dmBusy=false;document.getElementById('dm-start').disabled=dmJob&&['queued','running'].includes(dmJob.status);}
}
async function dmRefresh(){
 if(!dmJob)return;if(dmRefreshBusy){dmRefreshAgain=true;return;}dmRefreshBusy=true;clearTimeout(dmTimer);const jobId=dmJob.id,filter=document.getElementById('dm-filter').value;
 try{const snapshot=await contactRequest('/api/decision-makers/jobs/'+encodeURIComponent(jobId));if(dmJob?.id!==jobId)return;dmJob=snapshot;const result=await contactRequest('/api/decision-makers/results?job_id='+encodeURIComponent(dmJob.id)+'&page='+dmPage+'&verdict='+filter);if(dmJob?.id!==jobId||document.getElementById('dm-filter').value!==filter){dmRefreshAgain=true;return;}dmPage=result.page;dmRenderResults(result);}
 catch{dmError(dt('Verbindung unterbrochen. Ergebnisse erneut über den Recherche-Knopf öffnen.','Connection interrupted. Reopen research to load results.'));}
 finally{dmRefreshBusy=false;const again=dmRefreshAgain;dmRefreshAgain=false;if(document.getElementById('decision-maker-dialog').open&&(again||dmJob&&['queued','running'].includes(dmJob.status)))dmTimer=setTimeout(dmRefresh,again?0:1600);}
}
function dmRenderResults(data){
 const box=document.getElementById('dm-results');box.replaceChildren();const running=dmJob&&['queued','running'].includes(dmJob.status);document.getElementById('dm-stop').hidden=!running;document.getElementById('dm-start').disabled=!!running;
 const status=document.getElementById('dm-status');status.textContent=dmJob?(running?dt('Recherche läuft','Research running'):dmJob.status==='stopped'?dt('Recherche angehalten','Research stopped'):dt('Recherche abgeschlossen','Research complete'))+' · '+dmJob.done+'/'+dmJob.total+' · '+dt('ohne Website: ','no website: ')+dmJob.counts.no_website+' · '+dt('fehlgeschlagen: ','failed: ')+dmJob.counts.failed:dt('Noch keine Entscheider-Recherche vorhanden.','No decision-maker research yet.');
 if(!data){dmRows=[];dmUpdateSelection();return;}dmRows=data.items;const available=new Set(dmRows.filter(p=>!p.snapshot_changed).map(p=>p.id));for(const id of dmSelected)if(!available.has(id))dmSelected.delete(id);
 dmText(box,dt('Zielrollen dieses Suchlaufs: ','Target roles for this run: ')+data.criteria.roles.map(dmRoleName).join(', '));
 dmText(box,dt('Offen: passend / unbekannt / nicht passend: ','Pending: match / unknown / no match: ')+[data.counts.match,data.counts.unknown,data.counts.no_match].join(' / '));
 dmText(box,dt('Gefunden bedeutet nicht kontaktierbar oder freigegeben. Prüfe die Originalquelle vor der Übernahme.','Found does not mean contactable or approved. Review the original source before adoption.'));
 for(const person of dmRows){const article=document.createElement('article');article.className='dm-person';const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.disabled=person.snapshot_changed;check.checked=dmSelected.has(person.id);if(person.snapshot_changed)dmSelected.delete(person.id);check.onchange=()=>{if(check.checked)dmSelected.add(person.id);else dmSelected.delete(person.id);document.getElementById('dm-reviewed').checked=false;dmUpdateSelection();};label.append(check,' '+person.first_name+' '+person.last_name);article.append(label);
 if(person.snapshot_changed)dmText(article,dt('Vorschlag inzwischen geändert. Prüfe die aktuellen Angaben einzeln oder starte die Recherche erneut.','Suggestion has changed. Review the current details individually or research again.'));
 dmText(article,[person.title||dt('Position unbekannt','Unknown title'),person.company].join(' · '));
 const reason=person.fit.reason==='published_title_matches'?dt('Passung: Die veröffentlichte Position enthält eine gewählte Zielrolle.','Fit: the published title matches a selected target role.'):person.fit.reason==='non_current_or_support_role'?dt('Keine aktuelle Zielrolle belegt: Assistenz, frühere Rolle oder Ausbildung.','No current target role established: support, former role or training.'):dt('Die gewünschte Führungsrolle ist aus der veröffentlichten Position nicht belegt.','The published title does not establish the requested leadership role.');dmText(article,reason);
 dmText(article,[person.email||dt('Keine persönliche E-Mail veröffentlicht','No personal email published'),person.phone].filter(Boolean).join(' · '));
 const source=document.createElement('a');source.href=safeContactSource(person.source_url);source.target='_blank';source.rel='noopener noreferrer';source.textContent=dt('Originalquelle öffnen','Open original source');article.append(source);dmText(article,dt('Gefunden: ','Found: ')+formatDate(person.found_at),'small');
 article.append(dmButton(dt('Prüfen und bearbeiten','Review and edit'),async()=>{try{const rows=await contactRequest('/api/person-candidates?company_id='+encodeURIComponent(person.company_id));const current=rows.find(r=>r.id===person.id);if(current)await openContactEditor(null,false,current);else dmError(dt('Vorschlag nicht mehr verfügbar.','Suggestion no longer available.'));}catch{dmError(dt('Vorschlag konnte nicht geladen werden.','Could not load suggestion.'));}}));box.append(article);
 }
 if(!dmRows.length)dmText(box,dt('Keine offenen Vorschläge für diesen Filter. Prüfe „Rolle nicht belegt“ oder recherchiere weitere Unternehmen.','No pending suggestions for this filter. Check “Role not established” or research more companies.'));
 if(data.pages>1){const nav=document.createElement('div');nav.className='dm-pagination';for(const [step,text] of [[-1,dt('Zurück','Previous')],[1,dt('Weiter','Next')]]){const b=dmButton(text,()=>{dmPage+=step;dmSelected.clear();document.getElementById('dm-reviewed').checked=false;dmRefresh();});b.disabled=step<0?data.page===1:data.page===data.pages;nav.append(b);}dmText(nav,data.page+' / '+data.pages,'span');box.append(nav);}
 dmUpdateSelection();
}
function dmUpdateSelection(){document.getElementById('dm-selection-count').textContent=dt('Ausgewählt: ','Selected: ')+dmSelected.size;document.getElementById('dm-adopt').disabled=dmBusy||!dmSelected.size||!document.getElementById('dm-reviewed').checked;}
function dmFilterChanged(){dmPage=1;dmSelected.clear();document.getElementById('dm-reviewed').checked=false;dmRefresh();}
async function dmAdopt(){
 if(dmBusy||!dmSelected.size||!document.getElementById('dm-reviewed').checked)return;dmBusy=true;dmUpdateSelection();dmError('');
 try{const result=await contactPost('/api/decision-makers/adopt',{job_id:dmJob.id,candidate_ids:[...dmSelected],reviewed:true});const counts={created:0,duplicate:0,unavailable:0,review_required:0};for(const item of result.items)counts[item.status]++;dmError(dt('Übernommen / bereits vorhanden / nicht verfügbar / einzeln prüfen: ','Added / already present / unavailable / review individually: ')+Object.values(counts).join(' / '));dmSelected.clear();document.getElementById('dm-reviewed').checked=false;await dmRefresh();if(currentTab==='prospects')await loadProspects();await refreshPeopleSearch();}
 catch{dmError(dt('Übernahme fehlgeschlagen. Bitte erneut versuchen.','Adoption failed. Try again.'));}finally{dmBusy=false;dmUpdateSelection();}
}
async function dmStop(){if(!dmJob)return;try{await contactPost('/api/company-people-jobs/'+encodeURIComponent(dmJob.id)+'/stop',{});await dmRefresh();}catch{dmError(dt('Suche konnte nicht angehalten werden.','Could not stop research.'));}}
function dmClose(){document.getElementById('decision-maker-dialog').close();clearTimeout(dmTimer);}
window.addEventListener('harvey-language-changed',()=>{dmLabels();if(document.getElementById('decision-maker-dialog').open){for(const label of document.querySelectorAll('#dm-roles label')){const c=label.querySelector('input');label.lastChild.textContent=' '+dmRoleName(c.value);}dmRenderSelected();dmRefresh();}});

document.getElementById('decision-maker-dialog').addEventListener('close',()=>{clearTimeout(dmTimer);clearTimeout(dmLookupTimer);});
