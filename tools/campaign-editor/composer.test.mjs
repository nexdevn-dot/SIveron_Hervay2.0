import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {generateText} from '@tiptap/core';
import Document from '@tiptap/extension-document';
import Paragraph from '@tiptap/extension-paragraph';
import Text from '@tiptap/extension-text';
import HardBreak from '@tiptap/extension-hard-break';
const source=fs.readFileSync('../../harvey/web/campaign-composer.js','utf8');
function environment(){
 const context={campaignDraft:{editable:true,sequence:[]},campaignSaving:false,campaignDraftDirty:false,
  captureCampaignEditor(){},tr:value=>value,document:{getElementById:()=>({textContent:''})},confirm:()=>true};
 vm.createContext(context);vm.runInContext(source,context);
 vm.runInContext('renderCampaignSteps=()=>{};renderCampaignPreview=()=>{};',context);
 return context;
}
const nl=String.fromCharCode(10);
for(const text of ['', ['Guten Tag,','','Text','Viele Grüße'].join(nl), nl+'Am Anfang'+nl, 'ÄÖÜ 🙂 {{company}}', '<img src="https://untrusted.test/image">', ['Eine Zeile','','','Ende'].join(nl)]){
 test('Klartext bleibt unverändert: '+JSON.stringify(text),()=>{
  const context=environment(),doc=JSON.parse(JSON.stringify(context.campaignPlainDoc(text)));
  assert.equal(generateText(doc,[Document,Paragraph,Text,HardBreak],{blockSeparator:nl}),text);
  assert.ok(doc.content.every(node=>node.type==='paragraph'));
 });
}
test('Umsortieren behält Texte und macht den neuen Erstkontakt sofortig',()=>{
 const context=environment();
 const first={step:1,subject:'Erstkontakt',body:'Original\n{{company}}',delay_days:0};
 const second={step:2,subject:'Nachfrage',body:'Zweite Nachricht',delay_days:5};
 context.campaignDraft.sequence=[first,second];context.moveCampaignStep(1,0);
 assert.equal(context.campaignDraft.sequence[0],second);assert.equal(second.delay_days,0);
 assert.equal(first.delay_days,3);assert.equal(first.body,'Original\n{{company}}');
 assert.deepEqual(context.campaignDraft.sequence.map(s=>s.step),[1,2]);
 assert.ok(context.campaignDraftDirty);
});
test('Duplikat ist unabhängig und bekommt als Folge des Erstkontakts eine Wartezeit',()=>{
 const context=environment();context.campaignDraft.sequence=[{subject:'Hallo',body:'Original',delay_days:0}];
 context.duplicateCampaignStep();assert.equal(context.campaignDraft.sequence.length,2);
 assert.equal(context.campaignDraft.sequence[1].delay_days,3);
 context.campaignDraft.sequence[1].body='Neue Fassung';assert.equal(context.campaignDraft.sequence[0].body,'Original');
});
test('Schreibgeschützte Kampagnen können nicht umsortiert oder dupliziert werden',()=>{
 const context=environment();context.campaignDraft.sequence=[{subject:'A',body:'A',delay_days:0},{subject:'B',body:'B',delay_days:3}];context.campaignDraft.editable=false;
 const before=JSON.stringify(context.campaignDraft.sequence);context.moveCampaignStep(1,0);context.duplicateCampaignStep();context.removeCampaignStep(0);
 assert.equal(JSON.stringify(context.campaignDraft.sequence),before);
});

test('Duplikate teilen weder Formatierungsdokument noch Anhangsauswahl',()=>{
 const context=environment();context.campaignDraft.sequence=[{subject:'A',body:'Text',delay_days:0,body_doc:{type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Text',marks:[{type:'bold'}]}]}]},attachment_ids:['a'.repeat(32)],attachments:[{id:'a'.repeat(32),filename:'A.pdf',size:10}]}];
 context.duplicateCampaignStep();
 const first=context.campaignDraft.sequence[0],second=context.campaignDraft.sequence[1];
 second.body_doc.content[0].content[0].text='Changed';second.attachment_ids.pop();second.attachments.pop();
 assert.equal(first.body_doc.content[0].content[0].text,'Text');assert.equal(first.attachment_ids.length,1);assert.equal(first.attachments.length,1);
});
