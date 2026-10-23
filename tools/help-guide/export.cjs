// Run from any directory: node tools/help-guide/export.cjs
const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const root=path.resolve(__dirname,'../..');
const chapters=vm.runInNewContext(fs.readFileSync(path.join(root,'harvey/web/help-content.js'),'utf8')+';helpChapters');
for(const [locale,index,file] of [['de',0,'HANDBUCH_DE.md'],['en',1,'USER_GUIDE_EN.md']]){
 const t=pair=>pair[index];
 let text='# '+(locale==='de'?'Siveron – Hilfe und Arbeitsabläufe':'Siveron – Help and workflows')+'\n\n';
 text+=(locale==='de'?'Diese Fassung wird aus der gleichen Quelle wie die Hilfe im Dashboard erzeugt.':'This edition is generated from the same source as the in-app manual.')+'\n\n';
 for(const c of chapters){
  text+='## '+t(c.title)+'\n\n'+t(c.intro)+'\n\n';
  if(c.flow)text+='**'+(locale==='de'?'Ablauf':'Workflow')+':** '+c.flow.map(t).join(' → ')+'\n\n';
  if(c.steps)text+=c.steps.map((step,i)=>(i+1)+'. **'+t(step[0])+'** '+t(step[1])).join('\n\n')+'\n\n';
  if(c.rows)text+='| '+c.headers.map(t).join(' | ')+' |\n| --- | --- |\n'+c.rows.map(row=>'| '+row.map(t).join(' | ')+' |').join('\n')+'\n\n';
  if(c.status)text+=c.status.map(status=>'- **'+t(status[1])+'**: '+t(status[2])).join('\n')+'\n\n';
  if(c.faq)text+=c.faq.map(item=>'### '+t(item[0])+'\n\n'+t(item[1])).join('\n\n')+'\n\n';
  text+='**'+(locale==='de'?'Ergebnis und Hinweise':'Outcome and considerations')+':** '+t(c.note)+'\n\n';
 }
 fs.writeFileSync(path.join(root,'docs',file),text);
}
// Bounded bilingual retrieval for the assistant, from the same authored source.
fs.writeFileSync(path.join(root,'harvey/web/assistant-help.json'),JSON.stringify(chapters.map(c=>({id:c.id,title:c.title,text:JSON.stringify(c)}))));
