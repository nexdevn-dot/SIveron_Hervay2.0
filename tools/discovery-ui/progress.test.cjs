const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('harvey/web/app.js','utf8');
const fragment=code.slice(code.indexOf('let _progressInFlight'),code.indexOf('async function pollDiscoveryProgress'));
function harness() {
 const elements={'discover-progress':{innerHTML:''},'discovery-details':{showModal(){this.open=true},close(){this.open=false}}};
 const context=vm.createContext({document:{getElementById:id=>elements[id]},escHtml:s=>String(s).replaceAll('<','&lt;'),tr:s=>s,discoveryCount:(n,a,b)=>n+' '+(n===1?a:b)});
 vm.runInContext(fragment,context);
 return {elements,run:s=>vm.runInContext(s,context)};
}
const progress={id:'test-run',status:'running',new_companies:2,known_companies:8,errors:3,total:10,completed:5};
test('live phase is compact; completion stays visible then explicitly collapses',()=>{
 const h=harness();h.run(`_discoveryProgressView=${JSON.stringify(progress)}; renderDiscoveryCompact(_discoveryProgressView,'Find companies',50,'Search in progress')`);
 assert.match(h.elements['discover-progress'].innerHTML,/5\/10 · 50%/);
 assert.doesNotMatch(h.elements['discover-progress'].innerHTML,/<details/);
 h.run(`_discoveryProgressView.status='completed_with_errors'; renderDiscoveryCompact(_discoveryProgressView,'Find companies',100,'Search completed with errors')`);
 assert.match(h.elements['discover-progress'].innerHTML,/3 errors/);
 assert.doesNotMatch(h.elements['discover-progress'].innerHTML,/<progress/);
 // dismiss invokes the real renderer in production; substitute its compact delegation here.
 h.run(`function renderDiscoveryProgress(p){renderDiscoveryCompact(p,'Find companies',100,'Search completed with errors')} dismissDiscoverySummary()`);
 assert.match(h.elements['discover-progress'].innerHTML,/<details/);
 assert.doesNotMatch(h.elements['discover-progress'].innerHTML,/<details[^>]* open/);
});
test('persisted finished run loads collapsed and retains detail access',()=>{
 const h=harness();h.run(`renderDiscoveryCompact(${JSON.stringify({...progress,status:'failed'})},'Find companies',50,'Search failed')`);
 assert.match(h.elements['discover-progress'].innerHTML,/<details/);
 assert.match(h.elements['discover-progress'].innerHTML,/Search details/);
 assert.doesNotMatch(h.elements['discover-progress'].innerHTML,/<details[^>]* open/);
 h.run('openDiscoveryDetails(null)');assert.equal(h.elements['discovery-details'].open,true);
 h.run('closeDiscoveryDetails()');assert.equal(h.elements['discovery-details'].open,false);
});
