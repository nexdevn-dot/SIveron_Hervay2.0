/* Deep Chat is local. Only structured plans cross the application boundary. */
let assistantPrefs=null,assistantHistory=[],assistantPlan=null,assistantLastResult=null,assistantBusy=false,assistantReturnFocus=null;
const at=(de,en)=>window.harveyLanguage?.()==='de'?de:en;
const assistantError=code=>({disabled:at('Der Assistent ist in den Einstellungen ausgeschaltet.','The assistant is disabled in Settings.'),feature_disabled:at('Diese Funktion ist in den Assistenten-Einstellungen ausgeschaltet.','This feature is disabled in assistant settings.'),busy:at('Eine Anfrage läuft bereits. Bitte kurz warten.','A request is already running. Please wait.'),invalid_plan:at('Die KI hat keinen gültigen Auftrag geliefert. Bitte formuliere die Anfrage genauer.','The AI returned no valid plan. Please make the request more specific.'),invalid_request:at('Bitte eine Anfrage mit höchstens 2000 Zeichen eingeben.','Enter a request of at most 2000 characters.')})[code]||at('Die KI ist derzeit nicht verfügbar. Bitte später erneut versuchen oder die regulären Funktionen nutzen.','AI is currently unavailable. Try again later or use the regular features.');
async function assistantFetch(path,body){const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await response.json();if(!response.ok)throw Error(d.error);return d;}
function assistantButton(label,fn){const b=document.createElement('button');b.type='button';b.className='btn btn-secondary';b.textContent=label;b.onclick=fn;return b;}
function assistantText(parent,text,tag='p'){const p=document.createElement(tag);p.textContent=text;parent.append(p);return p;}
function assistantShell(){
 const launch=document.createElement('button');launch.id='assistant-launch';launch.className='btn btn-primary assistant-launch';launch.type='button';launch.dataset.userContent='';launch.setAttribute('aria-controls','assistant-panel');launch.setAttribute('aria-expanded','false');launch.onclick=()=>openAssistant();document.body.append(launch);
 const panel=document.createElement('aside');panel.id='assistant-panel';panel.className='assistant-panel';panel.hidden=true;panel.dataset.userContent='';panel.setAttribute('aria-labelledby','assistant-title');
 panel.innerHTML='<div class="assistant-heading"><h2 id="assistant-title"></h2><button type="button" class="btn btn-secondary" id="assistant-clear"></button><button type="button" class="btn btn-secondary" id="assistant-close"></button></div><p class="assistant-intro" id="assistant-intro"></p><div id="assistant-suggestions" class="assistant-suggestions"></div><deep-chat id="assistant-chat"></deep-chat><div class="assistant-result" id="assistant-result" aria-live="polite"></div>';
 document.body.append(panel);document.getElementById('assistant-close').onclick=closeAssistant;document.getElementById('assistant-clear').onclick=()=>{if(assistantBusy)return;assistantHistory=[];assistantPlan=null;assistantLastResult=null;document.getElementById('assistant-chat').history=[];document.getElementById('assistant-chat').clearMessages();document.getElementById('assistant-result').replaceChildren();};
 panel.addEventListener('keydown',e=>{if(e.key==='Escape'){closeAssistant();e.stopPropagation();}});
 assistantLabels();
}
function assistantLabels(){
 if(!document.getElementById('assistant-panel'))return;
 document.getElementById('assistant-launch').innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v12H9l-5 4V4zM8 8h8M8 12h5"/></svg><span>'+at('Assistent','Assistant')+'</span>';
 document.getElementById('assistant-title').textContent=assistantPrefs?.name||'Siveron Assistant';document.getElementById('assistant-clear').textContent=at('Leeren','Clear');document.getElementById('assistant-close').textContent=at('Schließen','Close');
 document.getElementById('assistant-intro').textContent=at('Frage zur Bedienung, bereite eine Suche vor oder werte gespeicherte Signale aus. Der Verlauf bleibt nur bis zum Neuladen.','Ask for help, prepare a search or analyze saved signals. History lasts until you reload.');
 const suggestions=document.getElementById('assistant-suggestions');suggestions.replaceChildren();
 const examples=[['help_enabled',at('Wie erstelle ich eine Kampagne?','How do I create a campaign?')],['discovery_enabled',at('Finde Bauunternehmen bei Gütersloh im Umkreis von 25 km.','Find construction companies within 25 km of Gütersloh.')],['data_enabled',at('Wie verteilen sich vorhandene Signale nach Kategorie?','Show existing signal counts by category.')]];
 for(const [flag,text] of examples)if(assistantPrefs?.[flag]!==false)suggestions.append(assistantButton(text,()=>document.getElementById('assistant-chat').submitUserMessage({text})));
 const chat=document.getElementById('assistant-chat');if(chat.getMessages){chat.history=chat.getMessages().map(m=>({role:m.role,text:m.text}));}chat.textInput={characterLimit:2000,placeholder:{text:at('Was möchtest du erledigen?','What would you like to do?')},styles:{container:{background:'transparent',color:'inherit',border:'1px solid var(--border-strong)',borderRadius:'8px'},text:{color:'inherit'}}};
 chat.submitButtonStyles={submit:{container:{default:{backgroundColor:'var(--accent)',borderRadius:'6px'}},svg:{styles:{default:{fill:'white'}}}}};
}
async function refreshAssistant(){try{assistantPrefs=await assistantFetch('/api/settings/assistant');document.getElementById('assistant-launch').hidden=!assistantPrefs.enabled;if(!assistantPrefs.enabled)closeAssistant();assistantLabels();}catch{document.getElementById('assistant-launch').hidden=true;}}
async function openAssistant(){assistantReturnFocus=document.activeElement;await refreshAssistant();if(!assistantPrefs?.enabled)return;document.getElementById('assistant-panel').hidden=false;document.getElementById('assistant-launch').hidden=true;document.getElementById('assistant-launch').setAttribute('aria-expanded','true');document.getElementById('assistant-close').focus();}
function closeAssistant(){document.getElementById('assistant-panel').hidden=true;document.getElementById('assistant-launch').hidden=assistantPrefs?.enabled===false;document.getElementById('assistant-launch').setAttribute('aria-expanded','false');assistantReturnFocus?.focus?.();}
function assistantResult(result){
 assistantLastResult=result;assistantPlan=result.plan;const box=document.getElementById('assistant-result');box.replaceChildren();const p=result.plan,d=result.data;
 if(p.unsupported.length)assistantText(box,at('Nicht unterstützte Kriterien: ','Unsupported criteria: ')+p.unsupported.join(', '));
 if(p.action==='discover'){
  assistantText(box,at('Suchvorschlag','Search proposal'),'strong');assistantText(box,p.terms.join(', ')+' · '+(p.cities.join(', ')||at('Zielregionen','Target regions'))+' · '+p.radius_km+' km');
  assistantText(box,at('Öffentliche E-Mail-Suche: ','Public email lookup: ')+(p.email_search?at('Ja','Yes'):at('Nein','No')));
  box.append(assistantButton(at('In Entdecken prüfen','Review in Discover'),()=>applyAssistantSearch(p)));
 }else if(p.action==='navigate'||p.action==='help')box.append(assistantButton(at('Bereich öffnen','Open section'),()=>{showTab(p.section==='contacts'?'prospects':p.section);closeAssistant();}));
 if(!d)return;
 assistantText(box,at('Stand: ','As of: ')+new Date(d.checked_at).toLocaleString());
 assistantText(box,at('Treffer / Signale: ','Matches / signals: ')+d.total+' · '+at('angezeigt: ','shown: ')+d.items.length);
 if(d.counts)assistantText(box,at('Erfüllt / nicht erfüllt / unbekannt: ','Match / no match / unknown: ')+[d.counts.match,d.counts.no_match,d.counts.unknown].join(' / '));
 if(d.kind==='signal_summary'){
  assistantText(box,at('Je Signal: aktuelle Belege, höchstens ','Per signal: current evidence, at most ')+d.max_age_days+at(' Tage alt. Unternehmen können mehrfach zählen. Inaktive Signale gelten als unbekannt.',' days old. Companies may occur under several signals. Inactive signals are unknown.'));
  const table=document.createElement('table'),head=table.createTHead().insertRow();[at('Signal / Kategorie','Signal / category'),at('Erfüllt','Match'),at('Nein','No'),at('Unbekannt','Unknown')].forEach(t=>assistantText(head,t,'th'));
  const tbody=table.createTBody();for(const row of d.items){const rowElement=tbody.insertRow();[tr(row.label)+' ('+({discovery:at('Unternehmenssuche','Discovery'),profile:at('Websiteprüfung','Website profiling'),people:at('Ansprechpersonen','People'),verification:at('Prüfung','Verification')})[row.category]+')',row.match,row.no_match,row.unknown].forEach(v=>assistantText(rowElement,String(v),'td'));}box.append(table);
 }else{
  for(const c of d.items){const line=document.createElement('p');line.append(assistantButton(c.name,()=>openCompanyProfile(c.id)));if(c.location)assistantText(line,c.location,'small');box.append(line);
   for(const e of c.evidence||[])assistantText(box,[e.code,e.observed_at,e.source].filter(Boolean).join(' · '),'small');
  }
 }
 if(d.total>(assistantPrefs?.result_limit||10)){const pages=Math.ceil(d.total/assistantPrefs.result_limit);const controls=document.createElement('div');controls.className='assistant-suggestions';for(const [step,label] of [[-1,at('Zurück','Previous')],[1,at('Weiter','Next')]]){const b=assistantButton(label,async()=>{b.disabled=true;try{assistantResult(await assistantFetch('/api/assistant/report',{...p,page:d.page+step}));}catch(e){assistantText(box,assistantError(e.message));b.disabled=false;}});b.disabled=step<0?d.page<=1:d.page>=pages;controls.append(b);}box.append(controls);}
 if(!d.items.length)assistantText(box,at('Keine passenden gespeicherten Ergebnisse.','No matching saved results.'));
}
async function applyAssistantSearch(p){
 if(_discoveryRunning){showToast(tr('Stop the current search before applying criteria.'),'error');return;}
 try{showTab('discover');await loadDiscoverProviders();if(_discoveryRunning)throw Error();
 document.getElementById('disc-terms').value=p.terms.join('\n');_discoveryLocations=p.cities.map(name=>({name}));renderDiscoveryLocations();syncDiscoveryTagify();
 const radius=document.getElementById('disc-radius');if(!Array.from(radius.options).some(o=>o.value===String(p.radius_km))){const o=document.createElement('option');o.value=String(p.radius_km);o.textContent=p.radius_km+' km';radius.append(o);}radius.value=String(p.radius_km);document.getElementById('disc-email-search').checked=p.email_search;document.getElementById('disc-email-mode').value=p.email_mode;document.getElementById('disc-maps-resume').checked=false;invalidateDiscoveryEstimate();
 closeAssistant();showToast(tr('Criteria applied. Review the preview; no search was started.'));
 }catch{showToast(tr('Search criteria could not be applied. Review Discover manually.'),'error');}
}
async function assistantHandle(body,signals){
 if(assistantBusy){await signals.onResponse({text:assistantError('busy')});return;}
 const message=body.messages?.at(-1)?.text||'';assistantBusy=true;assistantLastResult=null;document.getElementById('assistant-clear').disabled=true;document.getElementById('assistant-result').replaceChildren();
 try{const result=await assistantFetch('/api/assistant/chat',{message,history:assistantHistory.slice(-(assistantPrefs?.history_turns||0)*2).filter(()=>assistantPrefs?.history_turns>0),language:window.harveyLanguage?.()||'en',section:currentTab});assistantResult(result);assistantHistory.push({role:'user',text:message},{role:'assistant',text:result.plan.explanation});assistantHistory=assistantHistory.slice(-12);await signals.onResponse({text:result.plan.explanation});}
 catch(e){await signals.onResponse({text:assistantError(e.message)});}
 finally{assistantBusy=false;document.getElementById('assistant-clear').disabled=false;}
}
function assistantFormValues(){const form=document.getElementById('assistant-settings-form');if(!form)return assistantPrefs;const d={};for(const input of form.querySelectorAll('[name]'))d[input.name]=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value;return d;}
async function loadAssistantSettings(){
 const root=document.getElementById('assistant-settings');root.dataset.userContent='';
 try{const p=await assistantFetch('/api/settings/assistant');renderAssistantSettings(p);}catch{root.textContent=at('Assistenten-Einstellungen konnten nicht geladen werden. Öffne Einstellungen erneut.','Could not load assistant settings. Reopen Settings.');}
}
function renderAssistantSettings(p){
 const root=document.getElementById('assistant-settings');root.replaceChildren();assistantText(root,at('KI-Assistent','AI assistant'),'h2');assistantText(root,at('Suchvorschläge, Bedienhilfe und gespeicherte Daten. Nutzt die vorhandene KI-Konfiguration; keine zusätzlichen Zugangsdaten erforderlich.','Search proposals, help and saved data. Uses your existing AI configuration; no additional credentials required.'));
 const form=document.createElement('form');form.id='assistant-settings-form';const grid=document.createElement('div');grid.className='assistant-settings-grid';form.append(grid);
 const field=(name,label,type,options)=>{const wrap=document.createElement('div');wrap.className='form-group';const l=document.createElement('label');l.htmlFor='assistant-pref-'+name;l.textContent=label;const el=document.createElement(type==='select'?'select':type==='textarea'?'textarea':'input');el.id=l.htmlFor;el.name=name;el.className='form-input';
 if(type==='select')for(const [value,text] of options){const o=document.createElement('option');o.value=value;o.textContent=text;el.append(o);}else if(type!=='textarea')el.type=type;
 if(type==='checkbox'){
 el.checked=!!p[name];el.className='preference-switch-input';el.setAttribute('role','switch');
 l.className='preference-toggle';
 const control=document.createElement('span');control.className='signal-switch preference-switch';
 const track=document.createElement('span');track.className='signal-switch-track';track.setAttribute('aria-hidden','true');
 const thumb=document.createElement('span');thumb.className='signal-switch-thumb';track.append(thumb);control.append(el,track);
 l.append(control);wrap.append(l);
 }else{el.value=p[name];wrap.append(l,el);}grid.append(wrap);return el;};
 field('enabled',at('Assistent aktivieren','Enable assistant'),'checkbox');field('name',at('Anzeigename','Display name'),'text').maxLength=60;
 field('language',at('Antwortsprache','Response language'),'select',[['auto',at('Wie Oberfläche','Match interface')],['de','Deutsch'],['en','English']]);field('style',at('Antwortlänge','Response length'),'select',[['brief',at('Kurz','Brief')],['detailed',at('Ausführlich','Detailed')]]);
 field('help_enabled',at('Bedienhilfe und Navigation','Help and navigation'),'checkbox');field('discovery_enabled',at('KI-Suchvorschläge','AI search proposals'),'checkbox');field('data_enabled',at('Gespeicherte Daten auswerten','Analyze saved data'),'checkbox');
 const h=field('history_turns',at('Vorherige Dialogrunden (0–6)','Previous conversation turns (0–6)'),'number');h.min=0;h.max=6;h.required=true;
 const r=field('result_limit',at('Maximal angezeigte Ergebnisse (1–30)','Maximum displayed results (1–30)'),'number');r.min=1;r.max=30;r.required=true;
 const g=field('guidance',at('Zusätzliche Antwortpräferenzen','Additional response preferences'),'textarea');g.maxLength=1000;g.rows=3;g.parentElement.classList.add('full');
 assistantText(form,at('Präferenzen ändern keine Freigaben oder Berechtigungen. Anfragen und begrenzter Gesprächskontext werden über die vorhandene KI-Anbindung verarbeitet. Unternehmensdatensätze werden für diese Auswertungen lokal berechnet. Der Chatverlauf wird nicht dauerhaft gespeichert.','Preferences do not change approvals or permissions. Requests and limited conversation context are processed through the existing AI connection. Company records for these reports are computed locally. Chat history is not stored permanently.'));
 const status=assistantText(form,'');status.setAttribute('role','status');const save=assistantButton(at('Assistenten-Einstellungen speichern','Save assistant settings'),()=>{});save.type='submit';form.append(save);form.onsubmit=async e=>{e.preventDefault();if(!form.reportValidity())return;save.disabled=true;try{assistantPrefs=await assistantFetch('/api/settings/assistant',assistantFormValues());if(!assistantPrefs.history_turns)assistantHistory=[];await refreshAssistant();status.textContent=at('Einstellungen gespeichert.','Settings saved.');}catch{status.textContent=at('Speichern fehlgeschlagen. Bitte Werte prüfen und erneut versuchen.','Save failed. Check the values and try again.');}finally{save.disabled=false;}};root.append(form);
}
window.addEventListener('harvey-language-changed',()=>{assistantLabels();if(assistantLastResult)assistantResult(assistantLastResult);if(document.getElementById('assistant-settings-form'))renderAssistantSettings(assistantFormValues());});
async function initAssistant(){assistantShell();await customElements.whenDefined('deep-chat');const chat=document.getElementById('assistant-chat');chat.connect={handler:assistantHandle};chat.requestBodyLimits={maxMessages:1};chat.htmlClassUtilities={};chat.remarkable={html:false,applyHTML:false,linkTarget:'_blank'};chat.messageStyles={default:{shared:{bubble:{backgroundColor:'var(--panel-raised)',color:'var(--text)',fontSize:'14px',maxWidth:'90%'}},user:{bubble:{backgroundColor:'var(--accent-soft)',color:'var(--text)'}}}};chat.style.height='100%';chat.style.backgroundColor='transparent';await refreshAssistant();}
initAssistant();
