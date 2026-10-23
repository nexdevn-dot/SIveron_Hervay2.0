/* Contact actions and held campaign drafts; all consequential checks repeat on the server. */
let crmContactPage=1, crmContactPages=1, crmContactRequest=0, crmFilterTimer;
const crmContactSelection=new Map();
let crmNoteContact=null, crmBlockContact=null, crmAddTarget=null;
let crmDeletedCount=0, crmShowDeleted=false, crmActionIndex=null, crmActionTrigger=null, crmDeleteContact=null;
let campaignDraft=null, campaignDraftDirty=false, campaignSaving=false;
const crmPost=(url,payload,method='POST')=>contactRequest(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
const crmName=p=>p.contact_type==='company' ? p.company : [p.first_name,p.last_name].filter(Boolean).join(' ');
const crmHasEmail=p=>p.email_checks?!!p.email_checks.send_supported:/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(p.email||'');
const crmBlocked=p=>!!(p.suppressed || p.do_not_contact || p.status==='opted_out');
function crmError(id,message) {const el=document.getElementById(id); el.textContent=message || ''; el.hidden=!message;}

async function loadContactWorkspace() {
 closeContactActions();
 const request=++crmContactRequest, el=document.getElementById('prospects-table');
 const params=new URLSearchParams({page:crmContactPage,q:document.getElementById('crm-contact-search').value,blocked:crmShowDeleted?'':document.getElementById('crm-block-filter').value,deleted:crmShowDeleted?'yes':'no'});
 el.setAttribute('aria-busy','true');
 try {
  const result=await contactRequest('/api/contacts/page?'+params);
  if(request!==crmContactRequest) return;
  document.getElementById('crm-remote-warning').hidden=!result.remote_pause_pending;
  crmDeletedCount=result.deleted_count;
  document.getElementById('crm-trash-toggle').textContent=tr(crmShowDeleted?'Show active contacts':'Deleted contacts')+(crmShowDeleted?'':' ('+result.deleted_count+')');
  document.getElementById('crm-trash-toggle').setAttribute('aria-pressed',String(crmShowDeleted));
  document.getElementById('crm-block-filter').disabled=crmShowDeleted;
  document.getElementById('crm-trash-description').hidden=!crmShowDeleted;
  document.querySelector('#prospects .crm-selection').hidden=crmShowDeleted;
  document.getElementById('crm-selection-help').hidden=crmShowDeleted;
  _prospects=result.items; crmContactPage=result.page; crmContactPages=result.pages;
  _prospects.forEach(p=>{if(crmContactSelection.has(p.id)) {if(crmBlocked(p)||!crmHasEmail(p)) crmContactSelection.delete(p.id); else crmContactSelection.set(p.id,p);}});
  if(!_prospects.length) {el.innerHTML='<p>'+escHtml(tr(crmShowDeleted?'No deleted contacts match this search.':'No contacts match this search. Add a known person or company with Add contact.'))+'</p>'; updateCrmSelection();return;}
  el.innerHTML='<p>'+result.total+' Kontakte · Seite '+result.page+' von '+result.pages+'</p><div class="table-card"><table class="crm-contact-table"><thead><tr><th>Auswahl</th><th>Name</th><th>Position / Unternehmen</th><th>E-Mail / Telefon</th><th>Status</th><th>Quelle</th><th>Aktionen</th></tr></thead><tbody>'+_prospects.map((p,i)=>
   '<tr><td data-label="Auswahl"><input type="checkbox" aria-label="'+escHtml('Kontakt auswählen: '+crmName(p))+'" '+(crmContactSelection.has(p.id)?'checked ':'')+(crmBlocked(p)||!crmHasEmail(p)?'disabled ':'')+'onchange="selectCrmContact('+i+',this.checked)"></td><td data-label="Name"><strong>'+escHtml(crmName(p))+'</strong>'+(p.contact_type==='company'?'<small class="muted">Firmenkontakt</small>':'')+'</td><td data-label="Position / Unternehmen">'+escHtml([p.title,p.company].filter(Boolean).join(' · '))+'</td><td data-label="E-Mail / Telefon">'+escHtml(p.email || 'Keine E-Mail')+emailTag(p)+(p.phone?'<br>'+escHtml(p.phone):'')+'</td><td data-label="Status">'+(crmShowDeleted?'<strong>'+escHtml(tr('Deleted'))+'</strong>':crmBlocked(p)?'<strong class="crm-blocked">Nicht kontaktieren</strong><small>'+escHtml(p.block_reason || 'Abmeldung / gesperrte Adresse')+'</small>':badge(p.status))+'</td><td data-label="Quelle">'+contactSourceHtml(p)+'</td><td data-label="Aktionen"><div class="crm-contact-actions"><button type="button" class="btn btn-secondary btn-sm" aria-haspopup="menu" aria-expanded="false" aria-controls="contact-actions-menu" aria-label="'+escHtml('Actions: '+crmName(p))+'" onclick="openContactActions('+i+',this)" onkeydown="if(event.key===&quot;ArrowDown&quot;){event.preventDefault();openContactActions('+i+',this)}">'+tr('Actions')+'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></button></div></td></tr>').join('')+'</tbody></table></div><div class="people-candidate-pages"><button class="btn btn-secondary" onclick="goCrmContactPage(-1)"'+(crmContactPage===1?' disabled':'')+'>Zurück</button><span>Seite '+crmContactPage+' von '+crmContactPages+'</span><button class="btn btn-secondary" onclick="goCrmContactPage(1)"'+(crmContactPage===crmContactPages?' disabled':'')+'>Weiter</button></div>';
  updateCrmSelection();
 } catch(error) {if(request===crmContactRequest) el.textContent='Kontakte konnten nicht geladen werden: '+error.message;}
 finally {if(request===crmContactRequest) el.removeAttribute('aria-busy');}
}
function scheduleContactFilter(){clearTimeout(crmFilterTimer);crmFilterTimer=setTimeout(filterContactWorkspace,300);}
function filterContactWorkspace(){crmContactPage=1;crmContactSelection.clear();loadContactWorkspace();}
function goCrmContactPage(delta){crmContactPage=Math.max(1,Math.min(crmContactPages,crmContactPage+delta));loadContactWorkspace();}
function selectCrmContact(index,checked){const p=_prospects[index];if(!p||crmBlocked(p)||!crmHasEmail(p))return;if(checked)crmContactSelection.set(p.id,p);else crmContactSelection.delete(p.id);updateCrmSelection();}
function selectContactPage(){_prospects.filter(p=>!crmBlocked(p)&&crmHasEmail(p)).forEach(p=>crmContactSelection.set(p.id,p));loadContactWorkspace();}
function clearContactSelection(){crmContactSelection.clear();loadContactWorkspace();}
function updateCrmSelection(){document.getElementById('crm-selected-count').textContent=crmContactSelection.size+' ausgewählt';document.getElementById('crm-assign-campaign').disabled=!crmContactSelection.size;}
function editKnownContact(index){const p=_prospects[index];if(p)openContactEditor(null,false,null,p);}

async function openContactNotes(index){
 crmNoteContact=_prospects[index];if(!crmNoteContact)return;
 document.getElementById('contact-notes-title').textContent='Notizen: '+crmName(crmNoteContact);
 document.getElementById('contact-note-text').value='';crmError('contact-note-error','');
 document.getElementById('contact-note-history').textContent='Notizen werden geladen …';
 document.getElementById('contact-notes').showModal();await refreshContactNotes();
}
async function refreshContactNotes(){
 const id=crmNoteContact.id;
 try{const notes=await contactRequest('/api/contacts/'+encodeURIComponent(id)+'/notes');if(crmNoteContact.id!==id)return;
 document.getElementById('contact-note-history').innerHTML=notes.length?notes.map(n=>'<article class="crm-note"><small class="muted">'+escHtml(formatDate(n.created_at))+'</small><p>'+escHtml(n.comment)+'</p></article>').join(''):'<p>Noch keine Notizen zu diesem Kontakt.</p>';
 }catch(error){crmError('contact-note-error',error.message);}
}
async function saveContactNote(){
 const button=document.getElementById('contact-note-save');if(button.disabled)return;button.disabled=true;crmError('contact-note-error','');
 try{await crmPost('/api/contacts/'+encodeURIComponent(crmNoteContact.id)+'/notes',{comment:document.getElementById('contact-note-text').value});document.getElementById('contact-note-text').value='';await refreshContactNotes();await loadContactWorkspace();}
 catch(error){crmError('contact-note-error',error.message);}finally{button.disabled=false;}
}
function openContactBlock(index){
 crmBlockContact=_prospects[index];if(!crmBlockContact)return;
 const blocked=crmBlocked(crmBlockContact), optout=crmBlockContact.status==='opted_out' || !!crmBlockContact.has_opt_out;
 document.getElementById('contact-block-title').textContent=(blocked?'Kontaktsperre: ':'Nicht kontaktieren: ')+crmName(crmBlockContact);
 document.getElementById('contact-block-explanation').textContent=blocked?(optout?'Dieser Kontakt hat sich abgemeldet. Die Sperre kann hier nicht aufgehoben werden.':'Eine manuelle Sperre kann ausdrücklich aufgehoben werden. Bereits abgebrochene Nachrichten bleiben abgebrochen.'):'Die Sperre schließt den Kontakt aus Kampagnen aus und bricht wartende Nachrichten ab. Bei extern gestarteten Instantly-Kampagnen wird die gesamte betroffene Kampagne pausiert.';
 document.getElementById('contact-block-reason').value=crmBlockContact.block_reason || '';
 document.getElementById('contact-block-reason').required=!blocked;
 document.getElementById('contact-block-reason').disabled=blocked;
 const button=document.getElementById('contact-block-save');button.textContent=blocked?'Manuelle Sperre aufheben':'Kontaktsperre speichern';button.disabled=optout;button.hidden=false;
 document.getElementById('contact-block-cancel').textContent='Abbrechen';
 crmError('contact-block-error','');document.getElementById('contact-block').showModal();
}
async function saveContactBlock(){
 const button=document.getElementById('contact-block-save');if(button.disabled)return;button.disabled=true;
 try{const result=await crmPost('/api/contacts/'+encodeURIComponent(crmBlockContact.id)+'/block',{blocked:!crmBlocked(crmBlockContact),reason:document.getElementById('contact-block-reason').value});
 if(result.warning){crmError('contact-block-error',result.warning);button.hidden=true;document.getElementById('contact-block-cancel').textContent='Schließen';}else document.getElementById('contact-block').close();
 crmContactSelection.delete(crmBlockContact.id);await loadContactWorkspace();showToast(result.blocked?'Kontaktsperre gespeichert.':'Manuelle Kontaktsperre aufgehoben.','success');
 }catch(error){crmError('contact-block-error',error.message);}finally{button.disabled=false;}
}

async function chooseContactCampaign(){
 if(!crmContactSelection.size)return;
 crmError('contact-campaign-error','');document.getElementById('contact-campaign-count').textContent=crmContactSelection.size+' Kontakte für die Kampagne. Technische Verifizierung ist optional.';
 document.getElementById('contact-campaign-choice').showModal();
 try {const campaigns=await contactRequest('/api/campaigns');document.getElementById('contact-campaign-target').innerHTML='<option value="">Neuen Entwurf anlegen</option>'+campaigns.filter(c=>c.status==='manual_draft').map(c=>'<option value="'+escHtml(c.id)+'">'+escHtml(c.name)+'</option>').join('');if(crmAddTarget && campaigns.some(c=>c.id===crmAddTarget)) document.getElementById('contact-campaign-target').value=crmAddTarget;}
 catch(error){crmError('contact-campaign-error',error.message);}
}
async function continueContactCampaign(){
 const button=document.getElementById('contact-campaign-continue');button.disabled=true;
 try{const opened=await openCampaignEditor(document.getElementById('contact-campaign-target').value || null,[...crmContactSelection.values()]);if(opened)document.getElementById('contact-campaign-choice').close();}
 catch(error){crmError('contact-campaign-error',error.message);}finally{button.disabled=false;}
}
async function loadCampaignWorkspace(){
 renderCampaignResume();
 if(campaignDraft){document.getElementById('campaign-resume').hidden=true;document.getElementById('campaign-editor').hidden=false;document.getElementById('campaigns-list').hidden=true;await refreshCampaignMembers();return;}
 const el=document.getElementById('campaigns-list');document.getElementById('campaign-editor').hidden=true;el.hidden=false;
 try{_campaigns=await contactRequest('/api/campaigns');if(!_campaigns.length){el.innerHTML='<p>Noch keine Kampagnen. Erstelle einen Entwurf oder wähle Kontakte aus.</p>';return;}
 el.innerHTML=_campaigns.map((c,i)=>'<article class="campaign-card"><h3>'+escHtml(c.name)+'</h3><p>'+escHtml(c.status==='manual_draft'?'Entwurf':c.status==='awaiting_review'?'Zur Freigabe im Postausgang':tr((STATUS[c.status]||[c.status])[0]))+' · '+(c.prospect_ids||[]).length+' Kontakte · '+(c.sequence||[]).length+' Nachrichten</p><button class="btn btn-secondary" onclick="openCampaignEditor(_campaigns['+i+'].id)">Öffnen</button><button class="btn btn-secondary" onclick="openCampaignResults(_campaigns['+i+'].id)">Campaign results</button></article>').join('');
 }catch(error){el.textContent=error.message;}
}
async function openCampaignEditor(id=null,contacts=[]){
 if(campaignSaving)return false;
 campaignOutreachAck='';
 if(campaignDraft && campaignDraft.id!==id && campaignDraftDirty && !confirm(tr('Discard unsaved changes to the previous draft?')))return false;
 if(!campaignDraft || campaignDraft.id!==id){
  campaignDraft=id?await contactRequest('/api/campaign-drafts/'+encodeURIComponent(id)):{id:null,name:'',brief:{},sequence:[{step:1,subject:'',body:'',delay_days:0}],contacts:[],prospect_ids:[],revision:0,editable:true};
  campaignDraftDirty=false;campaignPreviewFingerprint=null;
 }else captureCampaignEditor();
 const known=new Set(campaignDraft.contacts.map(p=>p.id));
 contacts.forEach(p=>{if(!crmBlocked(p)&&!known.has(p.id)){campaignDraft.contacts.push(p);known.add(p.id);campaignDraftDirty=true;}});
 campaignDraft.prospect_ids=campaignDraft.contacts.map(p=>p.id);
 showTab('campaigns',document.querySelector('nav button[data-tab="campaigns"]'));
 renderCampaignEditor();return true;
}
function renderCampaignEditor(){
 rememberCampaignDraft();document.getElementById('campaign-resume').hidden=true;
 document.getElementById('campaign-recipient-results').hidden=true;document.getElementById('campaign-recipient-search').setAttribute('aria-expanded','false');
 document.getElementById('campaign-editor').hidden=false;document.getElementById('campaigns-list').hidden=true;
 document.getElementById('campaign-name').value=campaignDraft.name;
 for(const key of ['audience','offer','goal','sender','signature'])document.getElementById('campaign-'+key).value=campaignDraft.brief?.[key]||'';
 renderCampaignOutreach();renderCampaignContacts();renderCampaignSteps();crmError('campaign-suggest-error','');document.getElementById('campaign-suggest-status').textContent='';crmError('campaign-save-error','');document.getElementById('campaign-save-status').textContent='';
 document.querySelectorAll('#campaign-draft-form input,#campaign-draft-form textarea,#campaign-draft-form button').forEach(el=>el.disabled=!campaignDraft.editable);
 document.getElementById('campaign-preview-contact').disabled=false;
 refreshCampaignComposerState();
 if(!campaignDraft.editable){document.getElementById('campaign-save-status').textContent=campaignDraft.status==='awaiting_review'?'Prepared for review: this campaign is read-only.':'This campaign uses another workflow or is read-only. Return to the campaign overview.';document.getElementById('campaign-save-status').appendChild(Object.assign(document.createElement('button'),{type:'button',className:'btn btn-primary',textContent:'Open Outbox',onclick:()=>openCampaignOutbox(campaignDraft.id)}));}
 loadCampaignReadiness();
 renderCampaignPreview();
}
function captureCampaignEditor(){
 if(!campaignDraft)return;
 campaignDraft.name=document.getElementById('campaign-name').value;
 campaignDraft.brief={};for(const key of ['audience','offer','goal','sender','signature'])campaignDraft.brief[key]=document.getElementById('campaign-'+key).value;
 captureCampaignStep();
}
function renderCampaignContacts(){
 const rows=campaignDraft.contacts;
 const chosen=document.getElementById('campaign-preview-contact').value;
 const blocked=rows.filter(p=>p.missing||crmBlocked(p)).length, ready=rows.filter(p=>!p.missing&&!crmBlocked(p)&&crmHasEmail(p)).length;
 document.getElementById('campaign-contact-summary').textContent=window.harveyLanguage?.()==='en'?rows.length+' contacts · '+ready+' with email · '+blocked+' blocked / unavailable · '+(rows.length-blocked-ready)+' without a valid email':rows.length+' Kontakte · '+ready+' mit E-Mail · '+blocked+' gesperrt / nicht verfügbar · '+(rows.length-blocked-ready)+' ohne gültige E-Mail';
 document.getElementById('campaign-contact-list').innerHTML=rows.length?'<div class="campaign-recipient-chips">'+rows.map((p,i)=>'<span class="campaign-recipient-chip '+(p.missing||crmBlocked(p)||!crmHasEmail(p)?'is-unavailable':'')+'"><span><strong data-user-content>'+escHtml(p.missing?tr('Contact unavailable'):crmName(p))+'</strong><small>'+escHtml(p.email||tr('No email'))+'</small></span><button type="button" aria-label="'+escHtml(tr('Remove recipient')+': '+crmName(p))+'" onclick="removeCampaignContact('+i+')"'+(!campaignDraft.editable?' disabled':'')+'><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></button></span>').join('')+'</div>':'<p>'+tr('No recipients selected. Search for a contact below.')+'</p>';
 document.getElementById('campaign-preview-contact').innerHTML=rows.filter(p=>!p.missing).map(p=>'<option value="'+escHtml(p.id)+'">'+escHtml(crmName(p))+'</option>').join('')||'<option value="">General preview without a contact</option>';
 if(rows.some(p=>p.id===chosen))document.getElementById('campaign-preview-contact').value=chosen;
}
function removeCampaignContact(index){captureCampaignEditor();campaignDraft.contacts.splice(index,1);campaignDraftDirty=true;renderCampaignContacts();renderCampaignPreview();}
function addContactsToCurrentDraft(){captureCampaignEditor();crmAddTarget=campaignDraft.id;showTab('prospects',document.querySelector('nav button[data-tab="prospects"]'));}
async function saveCampaignEditor(){
 if(campaignSaving || !campaignDraft.editable)return false;captureCampaignEditor();campaignSaving=true;document.getElementById('campaign-save').disabled=true;crmError('campaign-save-error','');refreshCampaignComposerState();
 try{const payload={name:campaignDraft.name,brief:campaignDraft.brief,sequence:campaignDraft.sequence,prospect_ids:campaignDraft.contacts.map(p=>p.id),revision:campaignDraft.revision};
 const result=await crmPost('/api/campaign-drafts'+(campaignDraft.id?'/'+encodeURIComponent(campaignDraft.id):''),payload,campaignDraft.id?'PATCH':'POST');
 campaignDraft.id=result.id; campaignDraft=await contactRequest('/api/campaign-drafts/'+encodeURIComponent(result.id));campaignDraftDirty=false;renderCampaignEditor();document.getElementById('campaign-save-status').textContent='Draft saved. No campaign has been started.';crmAddTarget=null;crmContactSelection.clear();return true;
 }catch(error){crmError('campaign-save-error',error.message);await refreshCampaignMembers();return false;}finally{campaignSaving=false;document.getElementById('campaign-save').disabled=!campaignDraft.editable;refreshCampaignComposerState();}
}
function closeCampaignEditor(){if(campaignSaving)return;if(campaignDraftDirty&&!confirm(tr('Discard unsaved changes?')))return;disposeCampaignComposer();campaignDraft=null;campaignDraftDirty=false;crmAddTarget=null;loadCampaignWorkspace();}

async function retryRemoteCampaignPauses(){
 try{const result=await crmPost('/api/remote-campaign-pauses/retry',{});await loadContactWorkspace();showToast(result.remote_pause_pending?'Die externe Pause ist weiterhin unbestätigt. Bitte Instantly prüfen.':'Externe Kampagnenpause bestätigt.',result.remote_pause_pending?'error':'success');}
 catch(error){showToast(error.message,'error');}
}

async function refreshCampaignMembers(){
 const draft=campaignDraft;if(!draft || !draft.contacts.length)return;
 try{if(!draft.editable&&draft.id){const fresh=await contactRequest('/api/campaign-drafts/'+encodeURIComponent(draft.id));if(campaignDraft!==draft)return;draft.outbox_summary=fresh.outbox_summary;}const rows=await crmPost('/api/contacts/status',{ids:draft.contacts.map(p=>p.id)});if(campaignDraft!==draft)return;const byId=new Map(rows.map(p=>[p.id,p]));draft.contacts=draft.contacts.map(p=>byId.get(p.id)||{id:p.id,missing:true});renderCampaignContacts();renderCampaignPreview();}
 catch(error){crmError('campaign-save-error','Kontaktstatus konnte nicht aktualisiert werden. Vor dem Speichern erneut prüfen. '+error.message);}
}

async function newCampaignDraft(){
 if(campaignSaving)return;
 if(campaignDraftDirty&&!confirm(tr('Discard unsaved changes to the previous draft?')))return;
 campaignDraft=null;campaignDraftDirty=false;await openCampaignEditor();
}

async function prepareCampaignEditor(){
 if(campaignSaving||!campaignDraft?.editable)return;
 captureCampaignEditor();
 const workflow=campaignWorkflowState(campaignDraft,campaignDraftDirty,campaignPreviewFingerprint===campaignWorkflowFingerprint());
 if(!workflow.canPrepare){campaignWorkflowGo(workflow.focus);refreshCampaignGuide();return;}
 if(!await saveCampaignEditor())return;
 if(campaignPreviewFingerprint!==campaignWorkflowFingerprint()){campaignWorkflowGo('preview');return;}
 if(campaignDraft.outreach_history?.findings.length&&campaignOutreachAck!==campaignDraft.outreach_history.acknowledgment){
  renderCampaignOutreach();const panel=document.getElementById('campaign-outreach');panel.querySelector('details').open=true;panel.scrollIntoView({block:'center'});panel.querySelector('input').focus({preventScroll:true});return;
 }
 campaignSaving=true;
 document.getElementById('campaign-prepare').disabled=true;refreshCampaignComposerState();
 try{
  const result=await crmPost('/api/campaign-drafts/'+encodeURIComponent(campaignDraft.id)+'/prepare',{revision:campaignDraft.revision,outreach_acknowledgment:campaignOutreachAck});
  campaignDraft=await contactRequest('/api/campaign-drafts/'+encodeURIComponent(result.id));
  campaignDraftDirty=false;renderCampaignEditor();
  document.getElementById('campaign-save-status').textContent='Messages are waiting for review in the Outbox. Nothing has been sent.';
  document.getElementById('campaign-save-status').appendChild(Object.assign(document.createElement('button'),{type:'button',className:'btn btn-primary',textContent:'Open Outbox',onclick:()=>openCampaignOutbox(campaignDraft.id)}));
 }catch(error){
  if(error.message==='OUTREACH_REVIEW_REQUIRED'){
   campaignOutreachAck='';campaignDraft=await contactRequest('/api/campaign-drafts/'+encodeURIComponent(campaignDraft.id));renderCampaignOutreach();
   crmError('campaign-save-error',tr('Outreach history changed. Review the matching records again before preparing.'));
  }else crmError('campaign-save-error',error.message);
 }
 finally{campaignSaving=false;document.getElementById('campaign-prepare').disabled=!campaignDraft.editable;refreshCampaignComposerState();}
}
async function loadCampaignReadiness(){
 const target=document.getElementById('campaign-readiness');
 target.textContent=tr('Sending stays on hold until approval and setup are complete.');
 try{const result=await contactRequest('/api/campaign-readiness');
 const notices={'E-Mail-Versand ist deaktiviert.':'Email sending is disabled.','Das tägliche Versandlimit steht auf 0.':'The daily sending limit is 0.','Dieser Freigabeablauf benötigt SMTP oder Gmail als Versandweg.':'This review workflow requires SMTP or Gmail.','Das Versandpostfach muss noch eingerichtet werden.':'The sending mailbox needs to be configured.','Der Versand ist pausiert.':'Sending is paused.','Versandeinstellungen konnten nicht vollständig geprüft werden. Bitte Einstellungen öffnen.':'Sending settings could not be fully checked. Open Settings.'};
 target.textContent=result.notices.length?tr('Before sending:')+' '+result.notices.map(message=>tr(notices[message]||message)).join(' ')+' '+tr('Preparation is still possible.'):tr('Messages require your approval in the Outbox before sending.');
 }catch(error){target.textContent=tr('Sending settings could not be loaded. Check Settings before sending.');}
}

async function suggestCampaignText(){
 if(campaignSaving||!campaignDraft?.editable)return;
 captureCampaignEditor();
 crmError('campaign-suggest-error','');
 document.getElementById('campaign-suggest-status').textContent='';
 const missing=['offer','goal'].find(key=>!campaignDraft.brief[key]?.trim());
 if(missing){
  crmError('campaign-suggest-error','Enter an offer and a campaign goal for an AI suggestion.');
  document.getElementById('campaign-planning').open=true;
  document.getElementById('campaign-'+missing).focus();
  return;
 }
 if(campaignDraft.sequence.some(step=>step.subject||step.body)&&!confirm(tr('Replace the existing message sequence with an AI suggestion?')))return;
 const draft=campaignDraft, button=document.getElementById('campaign-suggest');
 campaignSaving=true;document.querySelectorAll('#campaign-draft-form input,#campaign-draft-form textarea,#campaign-draft-form button').forEach(el=>el.disabled=true);button.textContent='AI is drafting …';document.getElementById('campaign-suggest-status').textContent='AI is drafting a suggestion. Please wait.';crmError('campaign-save-error','');
 document.getElementById('campaign-save').disabled=true;document.getElementById('campaign-prepare').disabled=true;refreshCampaignComposerState();
 try{const result=await crmPost('/api/campaign-drafts/suggest-text',{name:draft.name,brief:draft.brief});
 if(campaignDraft!==draft)return;
 const first=draft.sequence[0];draft.sequence=result.sequence;if(first?.attachment_ids?.length&&draft.sequence[0]){draft.sequence[0].attachment_ids=[...first.attachment_ids];draft.sequence[0].attachments=[...(first.attachments||[])];}campaignDraftDirty=true;renderCampaignSteps();renderCampaignPreview();
 document.getElementById('campaign-suggest-status').textContent='AI suggestion added. Review and edit it; it has not been saved yet.';
 }catch(error){if(campaignDraft===draft){document.getElementById('campaign-suggest-status').textContent='';crmError('campaign-suggest-error',error.message);}}
 finally{campaignSaving=false;if(campaignDraft===draft){document.querySelectorAll('#campaign-draft-form input,#campaign-draft-form textarea,#campaign-draft-form button').forEach(el=>el.disabled=!draft.editable);document.getElementById('campaign-add-step').disabled=!draft.editable||draft.sequence.length>=10;button.textContent='Suggest text with AI';document.getElementById('campaign-save').disabled=!draft.editable;document.getElementById('campaign-prepare').disabled=!draft.editable;refreshCampaignComposerState();}}
}

function toggleDeletedContacts(){crmShowDeleted=!crmShowDeleted;filterContactWorkspace();}
function closeContactActions(){
 const menu=document.getElementById('contact-actions-menu');
 if(menu?.matches(':popover-open'))menu.hidePopover();
 if(crmActionTrigger)crmActionTrigger.setAttribute('aria-expanded','false');
}
function openContactActions(index,trigger){
 closeContactActions();crmActionIndex=index;crmActionTrigger=trigger;
 const p=_prospects[index];if(!p)return;
 const icon=path=>'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+path+'"/></svg>';
 const actions=[['notes','Notes','M7 3h10v3h3v15H4V6h3zM8 3v4h8V3M8 12h8M8 16h6']];
 if(crmShowDeleted)actions.push(['restore','Restore','M4 10a8 8 0 1 1 0 6M4 4v6h6']);
 else actions.push(['email-research','Research email','M3 5h18v14H3zM3 5l9 7 9-7M16 16l5 5'],['edit','Edit','m15 4 5 5M4 20l5-1L21 7l-5-5L4 14z'],['block',crmBlocked(p)?'View block':'Do not contact','M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7zM8 12h8'],['delete','Delete','M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7']);
 const menu=document.getElementById('contact-actions-menu');
 menu.innerHTML=actions.map(([action,label,path])=>'<button type="button" role="menuitem" data-contact-action="'+action+'"'+(action==='delete'?' class="contact-action-delete"':'')+'>'+icon(path)+'<span>'+escHtml(tr(label))+(action==='notes'?' ('+(p.note_count||0)+')':'')+'</span></button>').join('');
 menu.showPopover();trigger.setAttribute('aria-expanded','true');
 const rect=trigger.getBoundingClientRect();
 menu.style.left=Math.max(8,Math.min(rect.right-menu.offsetWidth,innerWidth-menu.offsetWidth-8))+'px';
 menu.style.top=Math.max(8,Math.min(rect.bottom+6,innerHeight-menu.offsetHeight-8))+'px';
 menu.querySelector('button').focus();
}
document.getElementById('contact-actions-menu').addEventListener('toggle',event=>{
 if(event.newState==='closed'&&crmActionTrigger)crmActionTrigger.setAttribute('aria-expanded','false');
});
document.getElementById('contact-actions-menu').addEventListener('click',event=>{
 const action=event.target.closest('[data-contact-action]')?.dataset.contactAction;if(!action)return;
 const index=crmActionIndex;closeContactActions();
 if(action==='email-research')openContactResearch(index);
 if(action==='notes')openContactNotes(index);
 if(action==='edit')editKnownContact(index);
 if(action==='block')openContactBlock(index);
 if(action==='delete'||action==='restore')openDeleteContact(index,action==='restore');
});
document.getElementById('contact-actions-menu').addEventListener('keydown',event=>{
 const items=[...event.currentTarget.querySelectorAll('button')],index=items.indexOf(document.activeElement);
 if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
  event.preventDefault();items[event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length].focus();
 }
 if(event.key==='Escape'){event.preventDefault();closeContactActions();crmActionTrigger?.focus();}
 if(event.key==='Tab'){closeContactActions();crmActionTrigger?.focus();}
});
window.addEventListener('resize',closeContactActions);
document.addEventListener('scroll',event=>{if(!document.getElementById('contact-actions-menu').contains(event.target))closeContactActions();},true);
function openDeleteContact(index,restore=false){
 crmDeleteContact={..._prospects[index],restore};if(!crmDeleteContact.id)return;
 document.getElementById('contact-delete-name').textContent=crmName(crmDeleteContact);
 document.getElementById('contact-delete-title').textContent=restore?'Restore contact':'Delete contact';
 document.getElementById('contact-delete-description').textContent=(restore?'The contact returns to the active list. Existing blocks remain. Cancelled messages and paused campaigns will not restart.':'The contact is removed from the active list and can be restored under Deleted contacts. Pending messages are cancelled; history and opt-outs are retained. External campaigns are paused where supported.');
 const button=document.getElementById('contact-delete-save');button.hidden=false;button.textContent=restore?'Restore':'Delete contact';button.className='btn '+(restore?'btn-primary':'btn-danger');button.disabled=false;
 crmError('contact-delete-error','');document.getElementById('contact-delete').showModal();
}
async function saveDeleteContact(){
 const p=crmDeleteContact,button=document.getElementById('contact-delete-save');if(!p||button.disabled)return;button.disabled=true;crmError('contact-delete-error','');
 try{
  const result=await crmPost('/api/contacts/'+encodeURIComponent(p.id)+'/trash',{revision:p.revision,restore:p.restore});
  crmContactSelection.delete(p.id);await loadContactWorkspace();
  if(result.warning){crmError('contact-delete-error',result.warning);button.hidden=true;}
  else{document.getElementById('contact-delete').close();showToast(tr(p.restore?'Contact restored. Cancelled messages remain cancelled.':'Contact deleted. You can restore it under Deleted contacts.'),'success');}
 }catch(error){crmError('contact-delete-error',error.message);}finally{button.disabled=false;}
}

window.addEventListener('harvey-language-changed',()=>{closeContactActions();document.getElementById('crm-trash-toggle').textContent=tr(crmShowDeleted?'Show active contacts':'Deleted contacts')+(crmShowDeleted?'':' ('+crmDeletedCount+')');});

let campaignRecipientTimer, campaignRecipientRequest=0, campaignRecipientResults=[];
function searchCampaignRecipients(){
 clearTimeout(campaignRecipientTimer);const request=++campaignRecipientRequest;
 const input=document.getElementById('campaign-recipient-search'),results=document.getElementById('campaign-recipient-results');
 results.hidden=true;input.setAttribute('aria-expanded','false');
 if(!campaignDraft?.editable||input.value.trim().length<2)return;
 const draft=campaignDraft;
 campaignRecipientTimer=setTimeout(async()=>{
  try{
   const data=await contactRequest('/api/contacts/page?blocked=no&q='+encodeURIComponent(input.value.trim()));
   if(request!==campaignRecipientRequest||campaignDraft!==draft)return;
   campaignRecipientResults=data.items.filter(p=>!crmBlocked(p)&&crmHasEmail(p)&&!draft.contacts.some(c=>c.id===p.id));
   results.innerHTML=campaignRecipientResults.map((p,i)=>'<button type="button" role="option" aria-selected="false" onclick="addInlineCampaignRecipient('+i+')"><strong data-user-content>'+escHtml(crmName(p))+'</strong><small data-user-content>'+escHtml([p.email,p.company].filter(Boolean).join(' · '))+'</small></button>').join('');
   results.hidden=!campaignRecipientResults.length;input.setAttribute('aria-expanded',String(!!campaignRecipientResults.length));
   document.getElementById('campaign-recipient-status').textContent=tr(campaignRecipientResults.length?'Select a contact to add it.':'No available contacts found. Already selected, blocked or email-less contacts are excluded.');
  }catch{document.getElementById('campaign-recipient-status').textContent=tr('Contact search failed. Please try again.');}
 },250);
}
function addInlineCampaignRecipient(index){
 if(!campaignDraft?.editable||campaignSaving)return;
 const p=campaignRecipientResults[index];if(!p||campaignDraft.contacts.some(c=>c.id===p.id))return;
 captureCampaignEditor();campaignDraft.contacts.push(p);campaignDraftDirty=true;
 campaignRecipientRequest++;document.getElementById('campaign-recipient-results').hidden=true;
 const input=document.getElementById('campaign-recipient-search');input.value='';input.setAttribute('aria-expanded','false');
 document.getElementById('campaign-recipient-status').textContent=tr('Recipient added.');renderCampaignContacts();renderCampaignPreview();input.focus();
}
function campaignRecipientKey(event){
 const results=document.getElementById('campaign-recipient-results');
 if(event.key==='Escape'){results.hidden=true;event.currentTarget.setAttribute('aria-expanded','false');}
 if(event.key==='ArrowDown'&&!results.hidden){event.preventDefault();results.querySelector('button')?.focus();}
}
document.getElementById('campaign-recipient-results').addEventListener('keydown',event=>{
 const items=[...event.currentTarget.querySelectorAll('button')],index=items.indexOf(document.activeElement);
 if(event.key==='Escape'){event.currentTarget.hidden=true;document.getElementById('campaign-recipient-search').focus();}
 if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();items[(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length]?.focus();}
});
document.addEventListener('pointerdown',event=>{if(!event.target.closest('.campaign-recipient-picker')){document.getElementById('campaign-recipient-results').hidden=true;document.getElementById('campaign-recipient-search').setAttribute('aria-expanded','false');}});

window.addEventListener('harvey-language-changed',()=>{if(campaignDraft){renderCampaignContacts();updateCampaignEditorTools();updateCampaignStepSummary();loadCampaignReadiness();}});
