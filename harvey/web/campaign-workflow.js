// Guided navigation over existing persisted drafts; never approves or sends mail.
function campaignWorkflowState(draft, dirty, previewSeen) {
 const contacts=draft.contacts||[], steps=draft.sequence||[];
 const contactsOK=contacts.length>0 && contacts.every(p=>!p.missing&&!p.suppressed&&!p.do_not_contact&&['new','queued','company_contact'].includes(p.status)&&(p.email_checks?!!p.email_checks.send_supported:/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(p.email||'')));
 const contentOK=!!draft.name?.trim() && steps.length>0 && steps.every(s=>!!s.subject?.trim()&&!!s.body?.trim());
 const summary=draft.outbox_summary||{};
 const prepared=draft.status==='awaiting_review'||Object.values(summary).some(n=>n>0);
 const unavailable=!draft.editable&&!prepared;
 const sent=summary.sent||0, pending=summary.pending_review||0, approved=summary.approved||0;
 const issues=summary.failed||summary.rejected||summary.cancelled;
 const approvalDone=prepared&&pending===0&&!issues&&(approved+sent)>0;
 const focus=prepared?(approvalDone?null:'approval'):!contactsOK?'contacts':!contentOK?'draft':!previewSeen?'preview':'prepare';
 return {contactsOK,contentOK,prepared,unavailable,focus,canPrepare:!prepared&&contactsOK&&contentOK&&previewSeen,
  steps:[{id:'contacts',label:'Contacts',done:prepared||contactsOK},{id:'draft',label:'Draft',done:prepared||contentOK},
   {id:'preview',label:'Preview',done:prepared||previewSeen},{id:'prepare',label:'Prepare',done:prepared},
   {id:'approval',label:'Approval',done:approvalDone}],
  pending,approved,sent,total:Object.values(summary).reduce((n,v)=>n+v,0),issues:!!issues,dirty};
}
let campaignPreviewFingerprint=null;
function campaignWorkflowFingerprint(){
 return JSON.stringify({name:campaignDraft?.name?.trim(),
  contacts:(campaignDraft?.contacts||[]).map(p=>[p.id,p.first_name||'',p.last_name||'',p.company||'',p.title||'',p.email||'',p.personalization_notes||'',p.status,!!p.missing,!!p.suppressed,!!p.do_not_contact]),
  sequence:(campaignDraft?.sequence||[]).map(s=>[s.step,s.subject?.trim(),s.body?.trim(),s.body_doc||null,s.delay_days,s.attachment_ids||[]])});
}
function rememberCampaignDraft(){
 if(!campaignDraft?.id)return;
 try{localStorage.setItem('siveron-last-campaign',campaignDraft.id);}catch{}
}
function renderCampaignResume(){
 const el=document.getElementById('campaign-resume');if(!el)return;
 let id='';try{id=localStorage.getItem('siveron-last-campaign')||'';}catch{}
 el.hidden=!id||id.length>100;
}
async function resumeCampaignDraft(){
 let id='';try{id=localStorage.getItem('siveron-last-campaign')||'';}catch{}
 if(!id||id.length>100)return;
 try{await openCampaignEditor(id);}
 catch{try{localStorage.removeItem('siveron-last-campaign');}catch{}renderCampaignResume();showToast(tr('Saved campaign unavailable. Choose another campaign.'),'error');}
}
function refreshCampaignGuide(){
 if(!campaignDraft)return;
 const el=document.getElementById('campaign-workflow');if(!el)return;
 const model=campaignWorkflowState(campaignDraft,campaignDraftDirty,campaignPreviewFingerprint===campaignWorkflowFingerprint());
 const icons={contacts:'M16 21v-2a4 4 0 0 0-8 0v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8',draft:'M4 3h12l4 4v14H4zM8 11h8M8 15h8',preview:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6',prepare:'M3 5h18v14H3zM3 6l9 7 9-7',approval:'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6zM12 8v5M12 16h.01'};
 const descriptions={contacts:'Choose contacts with an email. Remove blocked or unavailable recipients.',draft:'Give the campaign a name and complete every message.',preview:'Open the preview and check the personalized messages before preparing them.',prepare:'Save and prepare these messages for separate approval. Nothing is sent.',approval:'Review the remaining messages in Outbox.'};
 const actions={contacts:'Choose recipients',draft:'Complete draft',preview:'Check preview',prepare:'Save and prepare for review',approval:'Review campaign in Outbox'};
 const nav=document.getElementById('campaign-workflow-steps');
 const focused=nav.contains(document.activeElement)?document.activeElement.dataset.workflowStep:null;
 nav.innerHTML=model.steps.map(step=>'<li class="'+(step.done?'is-complete':'')+(step.id===model.focus?' is-current':'')+'"><button type="button" data-workflow-step="'+step.id+'" onclick="campaignWorkflowGo(\''+step.id+'\')"'+(step.id===model.focus?' aria-current="step"':'')+(campaignSaving?' disabled':'')+'><span class="workflow-node"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+(step.done?'m5 12 4 4L19 6':icons[step.id])+'"/></svg></span><span class="workflow-label">'+escHtml(tr(step.label))+'</span><small>'+escHtml(tr(step.id===model.focus?'Current step':step.done?'Complete':'Upcoming'))+'</small></button></li>').join('');
 document.getElementById('campaign-workflow-title').textContent=tr(model.focus?'Campaign preparation':'Preparation complete');
 const delivery=document.getElementById('campaign-workflow-delivery');delivery.hidden=!model.prepared;
 const deliveryState=model.issues?'needs-review':model.sent>0&&model.sent===model.total?'sent':'waiting';
 delivery.dataset.state=deliveryState;
 delivery.innerHTML='<span class="workflow-delivery-dot" aria-hidden="true"></span><div><strong>'+escHtml(tr(deliveryState==='sent'?'All messages sent':deliveryState==='needs-review'?'Delivery needs review':'Delivery pending'))+'</strong><p>'+model.sent+' / '+model.total+' '+escHtml(tr('messages sent'))+' · '+model.pending+' '+escHtml(tr('Awaiting approval'))+' · '+model.approved+' '+escHtml(tr('Approved'))+(model.issues?' · '+['failed','rejected','cancelled'].filter(k=>campaignDraft.outbox_summary[k]).map(k=>campaignDraft.outbox_summary[k]+' '+tr({failed:'Failed',rejected:'Rejected',cancelled:'Cancelled'}[k])).map(escHtml).join(' · '):'')+'</p></div>';

 if(focused)nav.querySelector('[data-workflow-step="'+focused+'"]')?.focus({preventScroll:true});
 const description=document.getElementById('campaign-workflow-description');
 description.textContent=tr(model.focus?descriptions[model.focus]:'Preparation and approval are complete. View delivery details in Outbox.');

 document.getElementById('campaign-workflow-storage').textContent=tr(campaignDraftDirty?'Unsaved changes: save the draft to resume after reloading.':campaignDraft.id?'Saved draft: you can resume it after reloading.':'Not saved yet. Only saved drafts can be resumed.');
 if(model.unavailable)description.textContent=tr('This campaign uses another workflow or is read-only. Return to the campaign overview.');
 const next=document.getElementById('campaign-workflow-next');next.textContent=tr(actions[model.focus||'approval']);next.disabled=campaignSaving;next.onclick=model.unavailable?()=>closeCampaignEditor():()=>campaignWorkflowGo(model.focus||'approval',true);
 if(model.unavailable)next.textContent=tr('Back to campaigns');
 if(model.focus==='prepare'&&!campaignDraftDirty&&campaignDraft.outreach_history?.findings.length&&campaignOutreachAck!==campaignDraft.outreach_history.acknowledgment){
  description.textContent=tr('Review overlapping recipients before preparing this campaign.');
  next.textContent=tr('Review previous outreach');next.onclick=()=>{const panel=document.getElementById('campaign-outreach');panel.querySelector('details').open=true;panel.scrollIntoView({block:'center'});panel.querySelector('input').focus({preventScroll:true});};
 }
 const error=document.getElementById('campaign-save-error');
 if(!error.hidden&&error.textContent){
  description.textContent=tr('A check failed. Read the error below, correct it and try again.');
  next.textContent=tr('Show error');next.onclick=()=>{error.tabIndex=-1;error.scrollIntoView({block:'center',behavior:'instant'});error.focus({preventScroll:true});};
 }
 document.getElementById('campaign-prepare').disabled=campaignSaving||model.unavailable||!model.canPrepare;
}
function campaignWorkflowGo(step, proceed=false){
 if(campaignSaving||!campaignDraft)return;
 if(step==='approval'){
  if(campaignDraft.editable){showToast(tr('Prepare the campaign before opening its review queue.'),'info');return;}
  return openCampaignOutbox(campaignDraft.id);
 }
 if(step==='prepare'){
  if(proceed)return prepareCampaignEditor();
  document.getElementById('campaign-editor-actions').scrollIntoView({block:'center',behavior:'instant'});
  document.getElementById('campaign-save').focus({preventScroll:true});return;
 }
 if(step==='preview'){
  setCampaignComposerMode('preview');campaignPreviewFingerprint=campaignWorkflowFingerprint();refreshCampaignGuide();
  document.getElementById('campaign-preview-panel').scrollIntoView({block:'center',behavior:'instant'});
  document.getElementById('campaign-preview-contact').focus({preventScroll:true});return;
 }
 if(step==='draft'){
  setCampaignComposerMode('edit');
  const target=!campaignDraft.name?.trim()?document.getElementById('campaign-name'):document.getElementById('campaign-step-subject');
  target?.scrollIntoView({block:'center',behavior:'instant'});target?.focus({preventScroll:true});return;
 }
 const target=document.getElementById('campaign-recipient-search');target.scrollIntoView({block:'center',behavior:'instant'});target.focus({preventScroll:true});
}
if(typeof document!=='undefined'){
 document.getElementById('campaign-draft-form').addEventListener('input',()=>{crmError('campaign-save-error','');captureCampaignEditor();refreshCampaignGuide();});
 window.addEventListener('harvey-language-changed',()=>{if(campaignDraft)refreshCampaignGuide();});
}

// Acknowledgment is session-local and bound to the exact server evidence.
let campaignOutreachAck='';
function renderCampaignOutreach(){
 const host=document.getElementById('campaign-outreach');if(!host||!campaignDraft)return;
 const report=campaignDraft.outreach_history||{findings:[],acknowledgment:''};
 host.hidden=!campaignDraft.editable||!report.findings.length;
 if(host.hidden){host.replaceChildren();return;}
 const groups=new Map();
 for(const item of report.findings){
  const key=JSON.stringify([item.recipient_id,item.campaign_id,item.contact_id,item.reasons]);
  if(!groups.has(key))groups.set(key,{...item,counts:{},sent_at:''});
  const group=groups.get(key);group.counts[item.kind==='membership'?'membership':item.status]=(group.counts[item.kind==='membership'?'membership':item.status]||0)+1;
  if(item.sent_at>group.sent_at)group.sent_at=item.sent_at;
 }
 const reasons={same_contact:'Same contact',same_email:'Same email address',same_company:'Linked company',uncertain_company_name:'Same company name — identity uncertain'};
 const labels={membership:'Campaign membership',selected:'Selected in this draft',pending_review:'Awaiting approval',approved:'Approved',sent:'Sent',failed:'Failed',rejected:'Rejected',cancelled:'Cancelled'};
 const states={unknown:'Unknown',manual_draft:'Draft',draft:'Draft',awaiting_review:'Awaiting approval',active:'Active',paused:'Paused',completed:'Completed',archived:'Archived'};
 const rows=[...groups.values()].map(item=>'<li><strong>'+escHtml(item.recipient_email)+'</strong> · '+escHtml(item.reasons.map(r=>tr(reasons[r])).join(', '))+'<br>'+escHtml(item.matched_name||item.matched_email||item.contact_id)+' · '+escHtml(item.kind==='selection'?tr('Selected in this draft'):(item.campaign_name||tr('Messages without campaign')))+' · '+escHtml(tr(states[item.campaign_status]||item.campaign_status))+'<br>'+escHtml(Object.entries(item.counts).map(([status,n])=>tr(labels[status]||status)+': '+n).join(' · '))+(item.sent_at?'<br>'+escHtml(tr('Last sent:'))+' '+escHtml(formatDate(/(Z|[+-]\d{2}:?\d{2})$/.test(item.sent_at)?item.sent_at:item.sent_at+'Z')):'')+'</li>').join('');
 host.innerHTML='<h4>'+escHtml(tr('Review previous outreach'))+'</h4><p>'+escHtml(tr('These saved recipients overlap with other campaigns or selected colleagues. A draft is not a sent message. Review the evidence before continuing.'))+'</p><details><summary>'+escHtml(tr('Show matching records'))+' ('+groups.size+')</summary><ul class="campaign-outreach-records">'+rows+'</ul></details><label class="campaign-outreach-ack"><input type="checkbox" id="campaign-outreach-ack"'+(campaignOutreachAck===report.acknowledgment?' checked':'')+'> '+escHtml(tr('I reviewed these overlaps and want to prepare this campaign.'))+'</label><p class="muted">'+escHtml(tr('This does not lift contact blocks or opt-outs and does not approve sending. The check runs again when preparing.'))+'</p>';
 host.querySelector('input').onchange=event=>{campaignOutreachAck=event.target.checked?report.acknowledgment:'';refreshCampaignGuide();};
}

if(typeof document!=='undefined')window.addEventListener('harvey-language-changed',renderCampaignOutreach);
