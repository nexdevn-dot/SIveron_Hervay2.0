// Local reusable criteria and explainable public lookup. No contact acceptance or sending.
let targetProfiles=[],targetEvaluation=null,lookupDiagnosticJob=null,targetEvaluationRequest=0;
const targetVerdicts={match:'Match',no_match:'No match',unknown:'Unknown'};
const targetReasons={missing:'No observation',inactive_signal:'Signal not active',stale:'Evidence too old or date unavailable',low_confidence:'Insufficient confidence',unknown_value:'Value unavailable',observed:'Observed'};
function evidenceLink(value){try{const u=new URL(value);if(!['https:','http:'].includes(u.protocol))return '';u.username='';u.password='';u.search='';u.hash='';return '<a href="'+escHtml(u.href)+'" target="_blank" rel="noopener noreferrer">'+escHtml(tr('Source'))+'</a>';}catch{return '';}}
async function loadTargetProfiles(){
 try{targetProfiles=await contactRequest('/api/target-profiles');
 for(const id of ['target-profile-select','disc-target-profile']){
  const el=document.getElementById(id),chosen=el.value;
  el.innerHTML='<option value="">'+escHtml(tr(id==='disc-target-profile'?'Unrestricted search':'Choose a profile'))+'</option>'+targetProfiles.map(p=>'<option value="'+escHtml(p.id)+'">'+escHtml(p.name)+'</option>').join('');
  if(targetProfiles.some(p=>p.id===chosen))el.value=chosen;
 }
 }catch{crmError('target-profile-error',tr('Target profiles could not be loaded. Try again.'));}
}
async function saveTargetProfile(){
 crmError('target-profile-error','');
 try{const value=await contactRequest('/api/target-profiles',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:document.getElementById('target-profile-name').value,max_age_days:Number(document.getElementById('target-profile-age').value),require:[..._cohort.require],exclude:[..._cohort.exclude]})});await loadTargetProfiles();document.getElementById('target-profile-select').value=value.id;await evaluateTargetProfile();}
 catch{crmError('target-profile-error',tr('Could not save profile. Enter a name, select distinct signals above and use an evidence age of 1–365 days.'));}
}
async function deleteTargetProfile(){const id=document.getElementById('target-profile-select').value;if(!id)return;
 if(!confirm(tr('Delete this target profile? Companies and observations are retained.')))return;
 try{await contactRequest('/api/target-profiles/'+encodeURIComponent(id),{method:'DELETE'});await loadTargetProfiles();targetEvaluation=null;document.getElementById('target-profile-results').replaceChildren();}catch{crmError('target-profile-error',tr('Could not delete profile. Try again.'));}
}
async function evaluateTargetProfile(page=1){
 const requestId=++targetEvaluationRequest;
 const id=document.getElementById('target-profile-select').value;crmError('target-profile-error','');
 if(!id){targetEvaluation=null;document.getElementById('target-profile-results').replaceChildren();return;}
 try{const data=await contactRequest('/api/target-profiles/'+encodeURIComponent(id)+'/evaluate?page='+page+'&verdict='+document.getElementById('target-profile-verdict').value);if(requestId!==targetEvaluationRequest)return;targetEvaluation=data;renderTargetEvaluation();}
 catch{crmError('target-profile-error',tr('Could not evaluate profile. Reload the saved profiles and try again.'));}
}
function targetCounts(data){return Object.entries(data.counts).map(([key,n])=>tr(targetVerdicts[key])+': '+n).join(' · ');}
function renderTargetEvaluation(){
 const d=targetEvaluation;if(!d)return;
 const rules=d.profile.require.map(c=>tr('Required')+': '+c).concat(d.profile.exclude.map(c=>tr('Excluded')+': '+c));
 document.getElementById('target-profile-results').innerHTML='<p><strong>'+escHtml(targetCounts(d))+'</strong></p><p class="muted" data-user-content>'+escHtml(rules.join(' · '))+'</p><p class="muted">'+escHtml(tr('Checked after import. Counts cover all current companies. Unknown results are retained.'))+'</p>'+(d.items.length?'<ul class="target-evidence-list">'+d.items.map(item=>'<li><strong data-user-content>'+escHtml(item.name)+'</strong> · '+escHtml(tr(targetVerdicts[item.verdict]))+'<details><summary>'+escHtml(tr('Evidence'))+'</summary><ul>'+item.evidence.map(e=>'<li><span data-user-content>'+escHtml(e.code)+'</span> · '+escHtml(tr(e.rule==='require'?'Required':'Excluded'))+' · '+escHtml(tr(targetReasons[e.reason]))+' · '+escHtml(tr(e.stage==='listing'?'Listing evidence':'Website or later evidence'))+(e.observed_at?' · '+escHtml(e.observed_at)+' UTC':'')+(e.value_num!==null?' · '+escHtml(String(e.value_num)):'')+(e.value_text?' · <span data-user-content>'+escHtml(e.value_text)+'</span>':'')+' '+evidenceLink(e.source)+'</li>').join('')+'</ul></details></li>').join('')+'</ul>':'<p>'+escHtml(tr('No results for this filter.'))+'</p>')+'<div class="target-profile-controls"><button class="btn btn-secondary" '+(d.page<=1?'disabled':'')+' onclick="evaluateTargetProfile('+(d.page-1)+')">'+escHtml(tr('Previous'))+'</button><span>'+d.page+' / '+d.pages+'</span><button class="btn btn-secondary" '+(d.page>=d.pages?'disabled':'')+' onclick="evaluateTargetProfile('+(d.page+1)+')">'+escHtml(tr('Next'))+'</button></div>';
}
function renderRunTargetSummary(d){const host=document.getElementById('disc-target-summary');host.innerHTML='<p><strong data-user-content>'+escHtml(d.profile.name)+'</strong> · '+escHtml(targetCounts(d))+'</p><p class="muted">'+escHtml(tr('This run was checked after import and website checks. All results are retained, including unknowns. Review company evidence under Signals.'))+'</p>';}
const lookupReasons={redirect_limit:'Redirect limit reached',found:'Public emails found',no_email_in_checked_pages:'No email in checked pages; other pages may contain one',no_website:'No website available',unreachable:'Website unavailable',unsafe_or_external_url:'URL blocked by the public website guard',http_error:'Website returned an HTTP error',unsupported_content:'Unsupported page format',page_too_large:'Page exceeded the size limit',timeout:'Lookup timed out',network_error:'Network request failed',browser_unavailable:'Browser fallback unavailable or failed',lookup_failed:'Lookup failed',legacy_unknown:'No diagnostic recorded for this older lookup'};
function renderLookupDiagnostics(job){
 lookupDiagnosticJob=job;const host=document.getElementById('lookup-diagnostic-results');
 host.innerHTML='<p class="muted">'+escHtml(tr('Quick and thorough limits still apply. No email found is not proof that no email exists. Retries require 60 seconds and are limited to two per company in this job.'))+'</p><ul class="lookup-diagnostics">'+(job.items||[]).map(item=>'<li><strong data-user-content>'+escHtml(item.name||item.company_id)+'</strong> · '+escHtml(tr(({found:'With email',not_found:'No email in checked pages',no_website:'No website',failed:'Failed',queued:'Queued',running:'Running'})[item.status]||item.status))+'<details><summary>'+escHtml(tr('Lookup evidence'))+' · '+escHtml(tr('Attempts'))+': '+(item.attempts||0)+'</summary><ul>'+((item.diagnostic?.reasons?.length?item.diagnostic.reasons:[{code:'legacy_unknown',stage:'lookup'}]).map(r=>'<li>'+escHtml(tr(({fetch:'Read website',browser:'Browser fallback',extraction:'Extract email',lookup:'Lookup'})[r.stage]||r.stage))+': '+escHtml(tr(lookupReasons[r.code]||'Lookup failed'))+(r.http_status?' (HTTP '+Number(r.http_status)+')':'')+' '+evidenceLink(r.source)+'</li>').join(''))+'</ul></details></li>').join('')+'</ul>';
 document.getElementById('lookup-retry').hidden=!job.id||job.status!=='completed'||!(job.items||[]).some(i=>['failed','not_found'].includes(i.status)&&i.diagnostic?.retryable&&i.attempts<3);
}
async function retryLookupDiagnostics(){
 if(!lookupDiagnosticJob?.id)return;const button=document.getElementById('lookup-retry');button.disabled=true;crmError('lookup-retry-error','');
 try{const job=await contactRequest('/api/company-email-jobs/'+encodeURIComponent(lookupDiagnosticJob.id)+'/retry',{method:'POST'});applyCompanyEmailJob(job);}
 catch{crmError('lookup-retry-error',tr('No retry available. Wait 60 seconds; only transient failures from a completed job can retry, up to two times.'));}
 finally{button.disabled=false;}
}
window.addEventListener('harvey-language-changed',()=>{loadTargetProfiles();renderTargetEvaluation();if(lookupDiagnosticJob)renderLookupDiagnostics(lookupDiagnosticJob);});
loadTargetProfiles();
