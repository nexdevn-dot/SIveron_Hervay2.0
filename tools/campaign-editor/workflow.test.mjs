import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync(new URL('../../harvey/web/campaign-workflow.js',import.meta.url),'utf8'),ctx);
const state=ctx.campaignWorkflowState;
const contact={id:'p',status:'new',email:'known@example.com'};
const draft={editable:true,name:'Example',contacts:[contact],sequence:[{subject:'Question',body:'Hello.'}]};
test('empty draft guides to contact selection before content',()=>{
 assert.equal(state({...draft,contacts:[]},true,false).focus,'contacts');
 assert.equal(state({...draft,name:''},true,false).focus,'draft');
});
test('missing, suppressed and already contacted recipients cannot prepare',()=>{
 for(const changes of [{missing:true},{suppressed:true},{do_not_contact:true},{status:'contacted'},{email:''}]){
  const value=state({...draft,contacts:[{...contact,...changes}]},false,true);
  assert.equal(value.contactsOK,false);assert.equal(value.canPrepare,false);
 }
});
test('complete content still needs an opened preview; saving is not preparation',()=>{
 assert.equal(state(draft,false,false).focus,'preview');
 const value=state(draft,true,true);
 assert.equal(value.focus,'prepare');assert.equal(value.canPrepare,true);assert.equal(value.prepared,false);
});
test('prepared campaign directs to explicit review and counts decisions separately',()=>{
 const value=state({...draft,editable:false,status:'awaiting_review',outbox_summary:{pending_review:1}},false,false);
 assert.equal(value.focus,'approval');assert.equal(value.canPrepare,false);
 assert.equal(value.steps[4].done,false);
 assert.equal(state({...draft,editable:false,status:'awaiting_review',outbox_summary:{approved:1}},false,false).steps[4].done,true);
 assert.equal(state({...draft,editable:false,status:'awaiting_review',outbox_summary:{rejected:1}},false,false).steps[4].done,false);
});
test('external/read-only campaign is not falsely marked prepared',()=>{
 const value=state({...draft,editable:false,status:'active'},false,false);
 assert.equal(value.unavailable,true);assert.equal(value.prepared,false);
});
test('preview fingerprint ignores transport metadata but detects recipient and content changes',()=>{
 ctx.campaignDraft={...draft};const first=ctx.campaignWorkflowFingerprint();
 ctx.campaignDraft={...draft,contacts:[{...contact,revision:7,phone:'123'}]};
 assert.equal(ctx.campaignWorkflowFingerprint(),first);
 ctx.campaignDraft={...draft,contacts:[{...contact,email:'changed@example.com'}]};
 assert.notEqual(ctx.campaignWorkflowFingerprint(),first);
});
test('completed approval has no current preparation step while delivery remains separate',()=>{
 for(const summary of [{approved:2},{sent:2},{approved:1,sent:1}]){
  const value=state({...draft,editable:false,status:'awaiting_review',outbox_summary:summary},false,false);
  assert.equal(value.focus,null);assert.ok(value.steps.every(s=>s.done));assert.equal(value.total,2);
 }
 const mixed=state({...draft,editable:false,status:'awaiting_review',outbox_summary:{sent:1,failed:1}},false,false);
 assert.equal(mixed.focus,'approval');assert.equal(mixed.issues,true);assert.equal(mixed.total,2);
});
test('saved backend email checks override optimistic local syntax',()=>{
 const value=state({...draft,contacts:[{...contact,email:'first..last@business.org',email_checks:{syntax_valid:false,send_supported:false}}]},false,true);
 assert.equal(value.contactsOK,false);assert.equal(value.focus,'contacts');
});
