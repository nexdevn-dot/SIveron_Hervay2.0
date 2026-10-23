/* Row actions always receive explicit IDs; never borrow or change bulk selection. */
let companyRowTarget=null,companyRowTrigger=null;
const caText=(de,en)=>window.harveyLanguage?.()==='de'?de:en;
const companyRowMenu=document.getElementById('company-row-actions-menu');
const caPaths={profile:'M4 3h11l5 5v13H4zM8 13h8M8 17h6',contacts:'M15 21v-2a5 5 0 0 0-10 0v2M10 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8',add:'M12 5v14M5 12h14',email:companyActionPaths['company-bulk-lookup'],people:companyActionPaths['company-people-search'],decision:companyActionPaths['company-people-results'],report:companyActionPaths['company-email-results'],cleanup:companyActionPaths['company-cleanup'],remove:companyActionPaths['company-delete-selected']};
function closeCompanyRowActions(restore=false){
 if(companyRowMenu.matches(':popover-open'))companyRowMenu.hidePopover();
 companyRowTrigger?.setAttribute('aria-expanded','false');if(restore)companyRowTrigger?.focus();
}
function openCompanyRowActions(trigger){
 const company=_companies.find(c=>c.id===trigger.dataset.companyRowActions);if(!company)return;
 closeCompanyRowActions();companyRowTarget={...company};companyRowTrigger=trigger;trigger.setAttribute('aria-expanded','true');
 companyRowMenu.replaceChildren();companyRowMenu.setAttribute('aria-label',caText('Aktionen: ','Actions: ')+company.name);
 const busy=_companyCleaning||_companyBulk?.running||window.peopleSearchRunning;
 const entries=[['profile',caText('Unternehmensprofil','Company profile')],['contacts',caText('Kontakte ansehen','View contacts')+' ('+(company.contact_count||0)+')'],['add',caText('Kontakt hinzufügen','Add contact')],['report',caText('Optimierungsbericht erstellen','Create optimization report')],['email',caText('Öffentliche E-Mails suchen','Find public emails')],['decision',caText('Entscheider recherchieren','Research decision makers')],['people',caText('Ansprechpersonen suchen','Find people')],['cleanup',caText('Datensatz bereinigen','Clean up record')],['remove',caText('Unternehmen löschen','Delete company')]];
 for(const [action,label] of entries){
  const button=document.createElement('button');button.type='button';button.className='btn btn-secondary';button.setAttribute('role','menuitem');button.dataset.companyRowAction=action;
  button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+caPaths[action]+'"/></svg><span></span>';button.querySelector('span').textContent=label;
  button.disabled=['email','people','decision','cleanup','remove'].includes(action)&&!!busy||action==='email'&&(_companyLookupStates.get(company.id)==='running');
  if(action==='remove')button.classList.add('company-row-remove');
  companyRowMenu.append(button);
 }
 companyRowMenu.showPopover();const r=trigger.getBoundingClientRect();
 companyRowMenu.style.left=Math.max(8,Math.min(r.left,innerWidth-companyRowMenu.offsetWidth-8))+'px';
 companyRowMenu.style.top=Math.max(8,Math.min(r.bottom+6,innerHeight-companyRowMenu.offsetHeight-8))+'px';
 companyRowMenu.querySelector('button:not(:disabled)')?.focus();
}
async function runCompanyRowAction(action){
 const company=companyRowTarget;if(!company)return;const index=_companies.findIndex(c=>c.id===company.id);
 closeCompanyRowActions(true);if(index<0)return;
 try{
  if(action==='profile')return openCompanyProfile(company.id);
  if(action==='contacts')return showCompanyContacts(index);
  if(action==='add')return openContactEditor(index);
  if(action==='report')return openCompanyReports([company],companyRowTrigger);
  if(_companyCleaning||_companyBulk?.running||window.peopleSearchRunning)return;
  if(action==='email')return await findSelectedCompanyEmails([company.id]);
  if(action==='people')return await startPeopleSearch([company.id]);
  if(action==='decision')return openDecisionMakerSearch([company.id]);
  if(action==='cleanup')return await cleanupCompanies([company.id]);
  if(action==='remove')return await deleteSelectedCompanies([company.id]);
 }catch{showToast(caText('Aktion fehlgeschlagen. Bitte erneut versuchen.','Action failed. Please try again.'),'error');}
}
document.addEventListener('click',event=>{
 const trigger=event.target.closest('[data-company-row-actions]');if(trigger){openCompanyRowActions(trigger);return;}
 const item=event.target.closest('[data-company-row-action]');if(item){runCompanyRowAction(item.dataset.companyRowAction);return;}
 if(!companyRowMenu.contains(event.target))closeCompanyRowActions();
});
document.addEventListener('keydown',event=>{
 if(event.key==='ArrowDown'&&event.target.matches('[data-company-row-actions]')){event.preventDefault();openCompanyRowActions(event.target);}
});
companyRowMenu.addEventListener('keydown',event=>{
 if(event.key==='Escape'){event.preventDefault();closeCompanyRowActions(true);return;}
 if(event.key==='Tab'){closeCompanyRowActions();return;}
 if(!['ArrowDown','ArrowUp','Home','End'].includes(event.key))return;
 event.preventDefault();const buttons=[...companyRowMenu.querySelectorAll('button:not(:disabled)')],index=buttons.indexOf(document.activeElement);
 buttons[event.key==='Home'?0:event.key==='End'?buttons.length-1:(index+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();
});
window.addEventListener('resize',()=>closeCompanyRowActions());

// Bulk explanations are available on hover/focus, never as persistent menu copy.
const caTooltip=document.createElement('div');caTooltip.id='company-actions-tooltip';caTooltip.className='company-actions-tooltip';caTooltip.setAttribute('role','tooltip');caTooltip.hidden=true;document.getElementById('company-actions-panel').append(caTooltip);
function companyActionTips(){
 const definitions={
 'company-actions-trigger':['Aktionen für die Unternehmensauswahl.','Actions for the company selection.'],
 'company-bulk-lookup':['Öffentliche E-Mails für die ausgewählten Unternehmen suchen.','Find public emails for the selected companies.'],
 'company-people-search':['Öffentliche Unternehmensseiten nach Ansprechpersonen durchsuchen.','Search public company pages for people.'],
 'company-cleanup':['Entfernt Unternehmen ohne bekannte gültige E-Mail, Telefon und Website aus dem gesamten Bestand. Rückgängig möglich.','Removes companies without known valid email, phone or website from the entire inventory. Can be undone.'],
 'company-delete-selected':['Ausgewählte Unternehmen ausblenden. Kontakte und Verlauf bleiben erhalten; rückgängig möglich.','Hide selected companies. Contacts and history are retained; can be undone.'],
 'company-email-results':['Ergebnisse des letzten E-Mail-Suchlaufs öffnen.','Open results of the latest email research.'],
 'company-people-results':['Gespeicherte Personenvorschläge prüfen.','Review saved person suggestions.'],
 'company-email-mode':['Schnell endet nach einem passenden Fund. Gründlich prüft weitere Kontakt-, Über-uns- und Teamseiten.','Quick stops after a matching result. Thorough checks additional contact, about and team pages.']};
 for(const [id,labels] of Object.entries(definitions)){const el=document.getElementById(id);if(!el)continue;const text=caText(...labels);el.dataset.companyTip=text;el.title=text;el.setAttribute('aria-description',text);}
 const decision=document.querySelector('#company-actions-panel [onclick^="openDecisionMakerSearch"]');if(decision){decision.dataset.companyTip=caText('Entscheiderrollen für ausgewählte Unternehmen recherchieren und Funde vor der Übernahme prüfen.','Research decision-maker roles for selected companies and review before adoption.');decision.title=decision.dataset.companyTip;}
}
function hideCompanyTip(){caTooltip.hidden=true;}
const caPanel=document.getElementById('company-actions-panel');
function showCompanyTip(event){
 const el=event.target.closest('[data-company-tip]');if(!el||event.pointerType==='touch'||event.type==='focusin'&&!el.matches(':focus-visible'))return;
 caTooltip.textContent=el.dataset.companyTip;caTooltip.hidden=false;const r=el.getBoundingClientRect();
 caTooltip.style.left=Math.max(8,Math.min(r.left,innerWidth-caTooltip.offsetWidth-8))+'px';
 caTooltip.style.top=Math.max(8,Math.min(r.bottom+6,innerHeight-caTooltip.offsetHeight-8))+'px';
}
caPanel.addEventListener('pointerover',showCompanyTip);caPanel.addEventListener('focusin',showCompanyTip);caPanel.addEventListener('pointerout',hideCompanyTip);caPanel.addEventListener('focusout',hideCompanyTip);caPanel.addEventListener('toggle',hideCompanyTip);caPanel.addEventListener('scroll',hideCompanyTip);
window.addEventListener('harvey-language-changed',()=>{closeCompanyRowActions();hideCompanyTip();companyActionTips();});companyActionTips();
