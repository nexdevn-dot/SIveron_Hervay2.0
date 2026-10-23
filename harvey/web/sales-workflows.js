let workflowTemplates=[],opportunityRows=[],opportunityEdit=null,opportunityConversation=null,opportunityRequest=0,opportunitySourcePage=1;
const opportunityStages={new:'New opportunity',qualified:'Qualified',proposal:'Proposal',negotiation:'Negotiation',won:'Won',lost:'Lost'};
async function loadWorkflowTemplates(){
 try{workflowTemplates=await contactRequest('/api/workflow-templates');const select=document.getElementById('workflow-template-select'),value=select.value;select.innerHTML='<option value="">'+escHtml(tr('Choose a template'))+'</option>'+workflowTemplates.map(t=>'<option data-user-content value="'+escHtml(t.id)+'">'+escHtml(t.name)+'</option>').join('');if(workflowTemplates.some(t=>t.id===value))select.value=value;}
 catch{crmError('workflow-template-error',tr('Templates unavailable. Refresh and try again.'));}
}
function selectedWorkflowTemplate(){return workflowTemplates.find(t=>t.id===document.getElementById('workflow-template-select').value);}
async function openWorkflowTemplateSave(){
 if(!campaignDraft||campaignSaving)return;
 if(campaignDraft.editable&&(!campaignDraft.id||campaignDraftDirty)&&!await saveCampaignEditor())return;
 if(!campaignDraft.id)return;
 document.getElementById('template-name').value=campaignDraft.name||'';document.getElementById('template-search').checked=false;crmError('template-save-error','');
 try{const profiles=await contactRequest('/api/target-profiles');document.getElementById('template-profile').innerHTML='<option value="">'+escHtml(tr('No target profile'))+'</option>'+profiles.map(p=>'<option data-user-content value="'+escHtml(p.id)+'">'+escHtml(p.name)+'</option>').join('');document.getElementById('template-save-dialog').showModal();}
 catch{showToast(tr('Target profiles could not be loaded. Try again.'),'error');}
}
function currentTemplateSearch(){const d=discoverBody();return {terms:d.terms,cities:d.cities,provider:d.provider||'osm',radius_km:d.radius_km,maps_mode:d.maps_mode,maps_filter:d.maps_filter,email_mode:d.email_mode,depth:d.depth,limit:d.limit};}
async function saveWorkflowTemplate(){
 const button=document.getElementById('template-save');if(button.disabled)return;button.disabled=true;crmError('template-save-error','');
 try{const result=await crmPost('/api/workflow-templates',{name:document.getElementById('template-name').value,campaign_id:campaignDraft.id,revision:campaignDraft.revision,target_profile_id:document.getElementById('template-profile').value,search:document.getElementById('template-search').checked?currentTemplateSearch():{}});await loadWorkflowTemplates();document.getElementById('workflow-template-select').value=result.id;document.getElementById('template-save-dialog').close();showToast(tr('Template saved without recipients or approvals.'));}
 catch{crmError('template-save-error',tr('Template could not be saved. Save the draft and check name, profile and search criteria.'));}finally{button.disabled=false;}
}
async function useWorkflowTemplate(){
 const t=selectedWorkflowTemplate();crmError('workflow-template-error','');if(!t){crmError('workflow-template-error',tr('Choose a template'));return;}
 if(campaignDraftDirty&&!confirm(tr('Discard unsaved changes?')))return;
 try{const d=await crmPost('/api/workflow-templates/'+encodeURIComponent(t.id)+'/instantiate',{name:document.getElementById('template-campaign-name').value});campaignDraftDirty=false;await openCampaignEditor(d.id);document.getElementById('workflow-template-status').textContent=tr(d.target_profile_missing?'The referenced target profile was deleted. Choose a profile manually before searching.':'An empty manual draft was created. Select recipients and review every message. Apply search criteria separately if needed.');}
 catch{crmError('workflow-template-error',tr('Template unavailable or campaign name invalid.'));}
}
async function applyWorkflowSearch(){
 const t=selectedWorkflowTemplate();if(!t)return;if(!t.search){crmError('workflow-template-error',tr('This template has no search criteria. Configure Discover manually.'));return;}if(_discoveryRunning){crmError('workflow-template-error',tr('Stop the current search before applying criteria.'));return;}
 try{_provider=t.search.provider;showTab('discover');await loadDiscoverProviders();if(_discoveryRunning)throw new Error();document.getElementById('disc-terms').value=t.search.terms.join('\n');_discoveryLocations=t.search.cities.map(name=>({name}));renderDiscoveryLocations();syncDiscoveryTagify();
 for(const [key,id] of [['radius_km','disc-radius'],['maps_mode','disc-maps-mode'],['maps_filter','disc-maps-filter'],['email_mode','disc-email-mode'],['depth','disc-depth'],['limit','disc-limit']])document.getElementById(id).value=t.search[key];
 document.getElementById('disc-maps-resume').checked=false;document.getElementById('disc-email-search').checked=false;await loadTargetProfiles();document.getElementById('disc-target-profile').value=t.target_profile_id;invalidateDiscoveryEstimate();showToast(tr(t.target_profile_id&&!targetProfiles.some(p=>p.id===t.target_profile_id)?'The referenced target profile was deleted. Choose a profile manually before searching.':'Criteria applied. Review the preview; no search was started.'));}
 catch{showToast(tr('Search criteria could not be applied. Review Discover manually.'),'error');}
}
async function deleteWorkflowTemplate(){const t=selectedWorkflowTemplate();if(!t||!confirm(tr('Delete this template? Existing campaigns are retained.')))return;try{await contactRequest('/api/workflow-templates/'+encodeURIComponent(t.id),{method:'DELETE'});await loadWorkflowTemplates();}catch{crmError('workflow-template-error',tr('Templates unavailable. Refresh and try again.'));}}
async function loadOpportunities(page=1){
 const request=++opportunityRequest;crmError('opportunities-error','');
 try{const d=await contactRequest('/api/opportunities?page='+page+'&stage='+document.getElementById('opportunity-filter').value);if(request!==opportunityRequest)return;opportunityRows=d.items;opportunitySourcePage=d.page;
 document.getElementById('opportunities-list').innerHTML='<p>'+escHtml(tr('Sales opportunities'))+': '+d.total+'</p>'+d.items.map((o,i)=>'<button class="conversation-row" onclick="openOpportunity(opportunityRows['+i+'].id)"><strong data-user-content>'+escHtml(o.title)+'</strong><span>'+escHtml(tr(opportunityStages[o.stage]))+'</span><span data-user-content>'+escHtml([o.owner||tr('Unassigned'),o.next_action,o.next_due,o.campaign_name].filter(Boolean).join(' · '))+'</span></button>').join('')+(d.pages>1?'<div class="target-profile-controls"><button class="btn btn-secondary" '+(d.page===1?'disabled':'')+' onclick="loadOpportunities('+(d.page-1)+')">'+escHtml(tr('Previous'))+'</button><span>'+d.page+' / '+d.pages+'</span><button class="btn btn-secondary" '+(d.page===d.pages?'disabled':'')+' onclick="loadOpportunities('+(d.page+1)+')">'+escHtml(tr('Next'))+'</button></div>':'');
 }catch{crmError('opportunities-error',tr('Opportunities unavailable. Refresh and try again.'));}
}
function fillOpportunity(o){
 for(const [id,key] of [['name','title'],['stage','stage'],['owner','owner'],['next','next_action'],['due','next_due'],['note','note']])document.getElementById('opportunity-'+id).value=o[key]||'';
 document.getElementById('opportunity-links').replaceChildren();crmError('opportunity-error','');updateOpportunityMode();
}
function updateOpportunityMode(){const link=!opportunityEdit&&!!document.getElementById('opportunity-link').value,closed=['won','lost'].includes(document.getElementById('opportunity-stage').value);document.getElementById('opportunity-fields').disabled=link;document.getElementById('opportunity-next').required=!closed;document.getElementById('opportunity-due').required=!closed;}
async function openOpportunityFromReply(){
 if(!activeConversationReview)return;opportunityConversation=activeConversationReview;opportunityEdit=null;
 const c=opportunityConversation;document.getElementById('opportunity-source').textContent=[c.first_name,c.last_name,c.campaign_name].filter(Boolean).join(' · ');document.getElementById('opportunity-interest-label').hidden=false;document.getElementById('opportunity-interest').required=true;document.getElementById('opportunity-interest').checked=false;document.getElementById('opportunity-link-label').hidden=false;
 try{const rows=[];let page=1,pages=1;do{const d=await contactRequest('/api/opportunities?prospect_id='+encodeURIComponent(c.prospect_id)+'&page='+page);rows.push(...d.items);pages=d.pages;page++;}while(page<=pages);
 document.getElementById('opportunity-link').innerHTML='<option value="">'+escHtml(tr('Create a new opportunity'))+'</option>'+rows.map(o=>'<option data-user-content value="'+escHtml(o.id)+'">'+escHtml(o.title)+' · '+escHtml(tr(opportunityStages[o.stage]))+'</option>').join('');fillOpportunity({title:[c.first_name,c.last_name].filter(Boolean).join(' ')||c.prospect_email,stage:'new'});document.getElementById('opportunity-dialog').showModal();}
 catch{showToast(tr('Opportunities unavailable. Refresh and try again.'),'error');}
}
async function openOpportunity(id){
 try{opportunityEdit=await contactRequest('/api/opportunities/'+encodeURIComponent(id));opportunityConversation=null;const o=opportunityEdit;document.getElementById('opportunity-interest-label').hidden=true;document.getElementById('opportunity-interest').required=false;document.getElementById('opportunity-link-label').hidden=true;document.getElementById('opportunity-link').value='';document.getElementById('opportunity-source').textContent=[o.first_name,o.last_name,o.campaign_name].filter(Boolean).join(' · ');fillOpportunity(o);
 const links=document.getElementById('opportunity-links');for(const source of o.sources){const b=document.createElement('button');b.type='button';b.className='btn btn-secondary';b.textContent=tr('Open conversation')+' · '+source.conversation_id;b.onclick=()=>{document.getElementById('opportunity-dialog').close();if(document.getElementById('conversation-dialog').open)document.getElementById('conversation-dialog').close();openConversationRecord(source.conversation_id);};links.appendChild(b);}
 document.getElementById('opportunity-dialog').showModal();}
 catch{showToast(tr('Opportunity unavailable'),'error');}
}
async function saveOpportunity(){
 const button=document.getElementById('opportunity-save');if(button.disabled)return;button.disabled=true;crmError('opportunity-error','');
 const data={};for(const [id,key] of [['name','title'],['stage','stage'],['owner','owner'],['next','next_action'],['due','next_due'],['note','note']])data[key]=document.getElementById('opportunity-'+id).value;
 try{let result;if(opportunityEdit)result=await crmPost('/api/opportunities/'+encodeURIComponent(opportunityEdit.id),{...data,revision:opportunityEdit.revision},'PATCH');else result=await crmPost('/api/conversations/'+encodeURIComponent(opportunityConversation.id)+'/opportunity',{...data,link_id:document.getElementById('opportunity-link').value,interest_confirmed:document.getElementById('opportunity-interest').checked});document.getElementById('opportunity-dialog').close();await loadOpportunities();loadToday();showToast(tr(result.already_linked?'This conversation already has an opportunity. Open it in Sales opportunities.':'Opportunity saved. No messages were sent or approved.'));}
 catch{crmError('opportunity-error',tr('Opportunity changed or invalid. Reload and check interest, next task and date.'));}finally{button.disabled=false;}
}
window.addEventListener('harvey-language-changed',()=>{loadWorkflowTemplates();loadOpportunities(opportunitySourcePage);});
loadWorkflowTemplates();
