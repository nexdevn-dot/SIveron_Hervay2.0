const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const chapters=vm.runInNewContext(fs.readFileSync(path.join(root,'harvey/web/help-content.js'),'utf8')+';helpChapters');
function bilingual(pair,location){
 assert.equal(pair.length,2,location+' must contain DE and EN');
 for(const text of pair){assert.equal(typeof text,'string',location);assert.ok(text.trim().length,location+' cannot be empty');assert.ok(!/<\/?(?:script|iframe|img|a|button)\b/i.test(text),location+' must be plain text');}
}
test('every chapter has complete DE and EN editions, including all visual labels',()=>{
 assert.ok(chapters.length>=18);
 const ids=new Set();
 for(const c of chapters){
  assert.match(c.id,/^[a-z-]+$/);assert.ok(!ids.has(c.id));ids.add(c.id);
  for(const key of ['group','title','intro','note'])bilingual(c[key],c.id+'.'+key);
  for(const key of ['flow','headers'])for(const pair of c[key]||[])bilingual(pair,c.id+'.'+key);
  for(const key of ['steps','rows','faq'])for(const row of c[key]||[]){assert.equal(row.length,2);for(const pair of row)bilingual(pair,c.id+'.'+key);}
  for(const status of c.status||[]){assert.ok(['good','wait','bad','idle'].includes(status[0]));bilingual(status[1],c.id+'.status.title');bilingual(status[2],c.id+'.status.body');}
  assert.ok(c.steps?.length||c.rows?.length||c.faq?.length,c.id+' must explain actions or reference details');
 }
});
test('the guide covers every dashboard area and the entire manual sending lifecycle',()=>{
 const ids=new Set(chapters.map(c=>c.id));
 for(const id of ['overview','navigation','setup','discover','progress','companies','emails','people','cleanup','contacts','contact-management','campaign','editor','ai','outbox','sending','replies','signals','operations','troubleshooting','glossary'])assert.ok(ids.has(id),id);
 assert.ok(chapters.filter(c=>c.flow).length>=8,'workflows need visual representations');
 assert.equal(chapters.find(c=>c.id==='outbox').status.length,4);
 assert.ok(chapters.find(c=>c.id==='troubleshooting').faq.length>=8);
});
test('manual is mounted once and loaded after its bilingual content',()=>{
 const html=fs.readFileSync(path.join(root,'harvey/web/index.html'),'utf8');
 assert.equal((html.match(/id="help-guide"/g)||[]).length,1);
 assert.ok(html.indexOf('/static/help-content.js')<html.indexOf('/static/help.js'));
 assert.ok(!html.includes('Instantly API Key (required)'));
});
