// Derived operational tasks and explicit outcomes. Navigation never approves or sends.
let workRows=[],workPage=1,workRequest=0,activeConversationReview=null,reviewRequest=0,resultsCampaignId=null,resultsData=null,resultsRequest=0;
const workCopy={opportunity:['Opportunity task due','Review the next task and update its stage or due date.','Open opportunity'],reply:['Reply needs review','Read the latest incoming reply and decide the next step.','Open reply'],approval:['Messages need approval','Review each prepared message before approving sending.','Review message'],blocked:['Delivery needs attention','Read the delivery reasons and next action. No automatic restart.','Inspect message']};
async function loadWorkItems(page=1){
 const ticket=++workRequest;crmError('today-work-error','');
 try{const d=await contactRequest('/api/work-items?page='+page);if(ticket!==workRequest)return;workRows=d.items;workPage=d.page;
 document.getElementById('today-work-items').innerHTML=(d.total?'<p>'+escHtml(tr('Actionable tasks'))+': '+d.total+'</p><div class="queue">'+d.items.map((r,i)=>'<div class="queue-item warn"><div class="qtext"><div class="qtitle">'+escHtml(tr(workCopy[r.kind][0]))+'</div><div data-user-content>'+escHtml([r.campaign_name,r.name].filter(Boolean).join(' · ')||tr('Without campaign'))+'</div><div class="qdetail">'+escHtml(tr(workCopy[r.kind][1]))+(['reply','opportunity'].includes(r.kind)?'':' '+r.count+' '+escHtml(tr(r.count===1?'message':'messages')))+(r.kind==='opportunity'?' <span data-user-content>'+escHtml([r.next_action,r.next_due,r.owner].filter(Boolean).join(' · '))+'</span>':'')+((r.reasons||[]).length?'<ul>'+r.reasons.map(reason=>'<li>'+escHtml(reason[window.harveyLanguage?.()==='de'?'de':'en'])+' · '+escHtml(reason[window.harveyLanguage?.()==='de'?'next_de':'next_en'])+'</li>').join('')+'</ul>':'')+'</div></div><button class="btn btn-secondary btn-sm" onclick="openWorkItem('+i+')">'+escHtml(tr(workCopy[r.kind][2]))+'</button></div>').join('')+'</div>':'<p>'+escHtml(tr('No pending operational tasks.'))+'</p>')+(d.pages>1?'<div class="target-profile-controls"><button class="btn btn-secondary" '+(d.page===1?'disabled':'')+' onclick="loadWorkItems('+(d.page-1)+')">'+escHtml(tr('Previous'))+'</button><span>'+d.page+' / '+d.pages+'</span><button class="btn btn-secondary" '+(d.page===d.pages?'disabled':'')+' onclick="loadWorkItems('+(d.page+1)+')">'+escHtml(tr('Next'))+'</button></div>':'');
 }catch{crmError('today-work-error',tr('Tasks could not be checked. Refresh to retry; an empty list is not confirmation that all work is done.'));}
}
async function openWorkItem(index){
 const chosen=workRows[index];if(!chosen)return;
 try{const fresh=await contactRequest('/api/work-items/'+encodeURIComponent(chosen.key));
 if(fresh.kind==='opportunity'){await openOpportunity(fresh.opportunity_id);return;}
 if(fresh.kind==='reply')await openConversationRecord(fresh.conversation_id);else openCampaignOutbox(fresh.campaign_id||null,fresh.message_id);
 }catch{showToast(tr('This task changed or was resolved. The list has been refreshed.'));loadToday();}
}
async function openConversationRecord(id){
 try{const c=await contactRequest('/api/conversations/'+encodeURIComponent(id)+'/review');conversationRows.push(c);if(document.getElementById('campaign-results-dialog').open)document.getElementById('campaign-results-dialog').close();openConversation(conversationRows.length-1);}
 catch{showToast(tr('Conversation could not be opened. Refresh and try again.'),'error');}
}
async function loadConversationOutcome(id){
 const ticket=++reviewRequest;activeConversationReview=null;document.getElementById('opportunity-from-reply').disabled=true;document.getElementById('outcome-save').disabled=true;document.getElementById('reply-reviewed').disabled=true;crmError('outcome-error','');document.getElementById('outcome-status').textContent='';
 try{const c=await contactRequest('/api/conversations/'+encodeURIComponent(id)+'/review');if(ticket!==reviewRequest)return;activeConversationReview=c;document.getElementById('opportunity-from-reply').disabled=!c.fingerprint;
 document.getElementById('conversation-dialog-title').textContent=[c.first_name,c.last_name].filter(Boolean).join(' ')||c.prospect_email||tr('Unknown');
 document.getElementById('conversation-dialog-thread').innerHTML=c.thread.filter(m=>m&&typeof m==='object').map(m=>'<div class="thread-msg '+(m.sender==='harvey'?'sent':'received')+'"><div class="sender">'+escHtml(m.sender==='harvey'?'Siveron':tr('Contact'))+' · '+escHtml(formatDate(m.timestamp))+'</div><div data-user-content>'+escHtml(m.content||'')+'</div></div>').join('');
 for(const key of ['qualified','meeting'])document.getElementById('outcome-'+key).value=c.outcome[key]===null?'':c.outcome[key]?'yes':'no';
 document.getElementById('outcome-note').value=c.outcome.note||'';document.getElementById('outcome-save').disabled=false;document.getElementById('reply-reviewed').disabled=!c.fingerprint;
 }catch{crmError('outcome-error',tr('Outcome could not be loaded. Reopen the conversation.'));}
}
async function saveConversationOutcome(){
 const c=activeConversationReview;if(!c)return;const button=document.getElementById('outcome-save');button.disabled=true;
 try{await crmPost('/api/conversations/'+encodeURIComponent(c.id)+'/outcome',{revision:c.outcome.revision,qualified:document.getElementById('outcome-qualified').value===''?null:document.getElementById('outcome-qualified').value==='yes',meeting:document.getElementById('outcome-meeting').value===''?null:document.getElementById('outcome-meeting').value==='yes',note:document.getElementById('outcome-note').value});if(activeConversationReview?.id!==c.id)return;await loadConversationOutcome(c.id);document.getElementById('outcome-status').textContent=tr('Outcome saved. No messages were sent or approved.');resultsData=null;}
 catch{crmError('outcome-error',tr('Outcome changed or invalid. Reopen the conversation and check your entries.'));}finally{button.disabled=false;}
}
async function markConversationReviewed(){
 const c=activeConversationReview;if(!c)return;const button=document.getElementById('reply-reviewed');button.disabled=true;
 try{await crmPost('/api/conversations/'+encodeURIComponent(c.id)+'/review',{fingerprint:c.fingerprint});document.getElementById('outcome-status').textContent=tr('Reply marked reviewed. A new incoming reply will appear again.');loadToday();}
 catch{crmError('outcome-error',tr('Reply changed. Reopen the conversation before marking reviewed.'));button.disabled=false;}
}
async function openCampaignResults(id){resultsCampaignId=id;resultsData=null;document.getElementById('results-from').value='';document.getElementById('results-through').value='';document.getElementById('campaign-results-title').textContent=tr('Campaign results');document.getElementById('campaign-results-content').replaceChildren();document.getElementById('campaign-results-dialog').showModal();await loadCampaignResults();}
async function loadCampaignResults(){
 const ticket=++resultsRequest;crmError('campaign-results-error','');
 const p=new URLSearchParams();if(document.getElementById('results-from').value)p.set('start',document.getElementById('results-from').value);if(document.getElementById('results-through').value)p.set('end',document.getElementById('results-through').value);
 try{const d=await contactRequest('/api/campaigns/'+encodeURIComponent(resultsCampaignId)+'/results?'+p);if(ticket!==resultsRequest)return;resultsData=d;renderCampaignResults();}
 catch{crmError('campaign-results-error',tr('Results unavailable. Check the UTC date range and try again.'));}
}
function renderCampaignResults(){
 const d=resultsData;if(!d)return;document.getElementById('campaign-results-title').textContent=d.name;
 const rows=[['Research attributed to campaign',null,null],['Contactable now',d.contactable_current,null],['Recorded approvals',d.approved.contacts,d.approved.messages],['Recorded sends',d.sent.contacts,d.sent.messages],['Incoming replies',d.replied.contacts,d.replied.messages],['Manually qualified',d.qualified.contacts,null],['Manually recorded meetings',d.meeting.contacts,null]];
 document.getElementById('campaign-results-content').innerHTML='<p>'+escHtml(tr('Unique participants (contact IDs)'))+': '+d.participants+' · '+escHtml(tr('Current members'))+': '+d.members_current+'</p><p class="muted">'+escHtml(tr('Event counts use the selected UTC period. Contactability is a current snapshot. Stages are independent and are not a conversion rate.'))+'</p><div class="table-card"><table><thead><tr><th>'+escHtml(tr('Stage'))+'</th><th>'+escHtml(tr('Unique contacts'))+'</th><th>'+escHtml(tr('Local messages'))+'</th></tr></thead><tbody>'+rows.map(([label,contacts,messages])=>'<tr><th>'+escHtml(tr(label))+'</th><td>'+escHtml(contacts===null?tr('Unknown or not applicable'):String(contacts))+'</td><td>'+escHtml(messages===null?'—':String(messages))+'</td></tr>').join('')+'</tbody></table></div><p class="muted">'+escHtml(tr('Contactable now means a usable email format without a known block; deliverability is not proven.'))+'</p><p class="muted">'+escHtml(tr('Undated legacy approvals / sends / replies are excluded from event counts.'))+' '+d.unknown_approval_dates+' / '+d.unknown_sent_dates+' / '+d.unknown_reply_dates+'</p><p class="muted">'+escHtml(tr('Conversations not manually assessed (qualification / meeting)'))+': '+d.qualified.unassessed_conversations+' / '+d.meeting.unassessed_conversations+'</p><p>'+escHtml(tr('These counts cover stored local records. External delivery, research attribution and revenue are unknown. A reply is not a qualified lead or a booked meeting.'))+'</p><details><summary>'+escHtml(tr('Counted contacts and records'))+'</summary><ul class="results-records">'+d.contacts.map(c=>'<li><strong data-user-content>'+escHtml([c.first_name,c.last_name].filter(Boolean).join(' ')||c.email||c.id)+'</strong> <button class="btn btn-secondary btn-sm" data-result-contact="'+escHtml(c.id)+'">'+escHtml(tr('Open contact'))+'</button> · '+escHtml(['contactable','approved','sent','replied','qualified','meeting'].filter(k=>c[k]).map(k=>tr(({contactable:'Contactable now',approved:'Recorded approvals',sent:'Recorded sends',replied:'Incoming replies',qualified:'Manually qualified',meeting:'Manually recorded meetings'})[k])).join(' · ')||tr('No recorded events'))+'</li>').join('')+'</ul></details><h3>'+escHtml(tr('Linked records'))+'</h3><div class="results-records">'+d.conversation_ids.map((id,i)=>'<button class="btn btn-secondary" onclick="openConversationRecord(resultsData.conversation_ids['+i+'])">'+escHtml(tr('Open conversation'))+' · '+escHtml(id)+'</button>').join('')+d.approved.message_ids.concat(d.sent.message_ids).filter((v,i,a)=>a.indexOf(v)===i).map((id,i)=>'<button class="btn btn-secondary" data-result-message="'+escHtml(id)+'">'+escHtml(tr('Open message'))+' · '+escHtml(id)+'</button>').join('')+'</div>';
 document.querySelectorAll('[data-result-contact]').forEach(button=>button.onclick=()=>openResultContact(button.dataset.resultContact));
 document.querySelectorAll('[data-result-message]').forEach(button=>button.onclick=()=>{document.getElementById('campaign-results-dialog').close();openCampaignOutbox(d.id,button.dataset.resultMessage);});
}
window.addEventListener('harvey-language-changed',()=>{loadWorkItems(workPage);renderCampaignResults();});
loadWorkItems();

async function openResultContact(id){
 try{const rows=await crmPost('/api/contacts/status',{ids:[id]});if(!rows.length)throw new Error();document.getElementById('campaign-results-dialog').close();await openContactEditor(null,false,null,rows[0]);}
 catch{showToast(tr('Contact unavailable or deleted. Historical counts are retained.'),'error');}
}
