/* Sequence editor: canonical rich documents with a plain-text alternative. */
let composerDraft=null, composerActive=0, composerMode='edit', composerSortable=null;
let composerEditors=new Map(), composerRendering=false, composerTarget='body',campaignUploading=false;
const composerIcon='<svg viewBox="0 0 12 18" width="12" height="18" aria-hidden="true"><g fill="currentColor"><circle cx="3" cy="3" r="1.5"/><circle cx="9" cy="3" r="1.5"/><circle cx="3" cy="9" r="1.5"/><circle cx="9" cy="9" r="1.5"/><circle cx="3" cy="15" r="1.5"/><circle cx="9" cy="15" r="1.5"/></g></svg>';

function disposeCampaignComposer(){
 composerSortable?.destroy();composerSortable=null;
 composerEditors.forEach(item=>item.editor?.destroy());composerEditors.clear();composerDraft=null;
}
function campaignPlainDoc(text){
 return {type:'doc',content:String(text||'').split('\n').map(line=>({type:'paragraph',...(line?{content:[{type:'text',text:line}]}:{})}))};
}
function campaignBodyText(editor){return editor.getText({blockSeparator:'\n'});}
function composerCanEdit(){return !!campaignDraft?.editable&&!campaignSaving;}
function captureCampaignStep(){
 if(!campaignDraft||composerDraft!==campaignDraft)return;
 const step=campaignDraft.sequence[composerActive], panel=document.getElementById('campaign-step-editor');
 if(!step||Number(panel?.dataset.index)!==composerActive)return;
 step.subject=document.getElementById('campaign-step-subject')?.value??step.subject;
 const record=composerEditors.get(step);
 step.body=record?.editor?campaignBodyText(record.editor):(document.getElementById('campaign-step-body-fallback')?.value??step.body);
 if(record?.editor)step.body_doc=record.editor.getJSON();
 const delay=document.getElementById('campaign-step-delay');
 step.delay_days=composerActive===0?0:delay?Number(delay.value):step.delay_days;
}
function campaignStepChanged(){
 if(!composerCanEdit()||composerRendering)return;
 captureCampaignStep();campaignDraftDirty=true;updateCampaignStepSummary();renderCampaignPreview();updateCampaignEditorTools();
}
function updateCampaignStepSummary(){
 if(!campaignDraft)return;
 campaignDraft.sequence.forEach((step,i)=>{
  const subject=document.querySelector('#campaign-step-list [data-index="'+i+'"] .campaign-step-subject');
  const snippet=document.querySelector('#campaign-step-list [data-index="'+i+'"] .campaign-step-snippet');
  const delay=document.querySelector('#campaign-step-list [data-index="'+i+'"] .campaign-step-wait');
  if(subject)subject.textContent=step.subject||tr('No subject yet');
  if(snippet)snippet.textContent=step.body?.replace(/\s+/g,' ').slice(0,90)||tr('No message yet');
  if(delay)delay.textContent=i===0?'Initial message':step.delay_days+' '+(step.delay_days===1?'day':'days')+' later';
 });
}
function renderCampaignSteps(){
 if(composerDraft!==campaignDraft){const keep=!!composerDraft?.id&&composerDraft.id===campaignDraft.id,active=composerActive,mode=composerMode;disposeCampaignComposer();composerDraft=campaignDraft;composerActive=keep?active:0;composerMode=keep?mode:'edit';}
 composerActive=Math.min(composerActive,Math.max(0,campaignDraft.sequence.length-1));
 composerRendering=true;
 for(const [step,record] of composerEditors)if(!campaignDraft.sequence.includes(step)){record.editor?.destroy();composerEditors.delete(step);}
 composerSortable?.destroy();composerSortable=null;
 const list=document.getElementById('campaign-step-list');
 list.innerHTML=campaignDraft.sequence.map((step,i)=>'<li class="campaign-step-item" data-index="'+i+'">'+
 '<span class="campaign-drag-handle" aria-hidden="true">'+composerIcon+'</span><button class="campaign-step-select" type="button" onclick="selectCampaignStep('+i+')"'+(i===composerActive?' aria-current="step"':'')+'>'+
 '<span class="campaign-step-caption">Message '+(i+1)+'<span class="campaign-step-wait">'+(i===0?'Initial message':step.delay_days+' days later')+'</span></span>'+
 '<strong data-user-content class="campaign-step-subject">'+escHtml(step.subject||tr('No subject yet'))+'</strong><span data-user-content class="campaign-step-snippet">'+escHtml(step.body?.replace(/\s+/g,' ').slice(0,90)||tr('No message yet'))+'</span></button></li>').join('');
 document.getElementById('campaign-add-step').disabled=!composerCanEdit()||campaignDraft.sequence.length>=10;
 if(window.CampaignComposerDeps)composerSortable=new CampaignComposerDeps.Sortable(list,{
  disabled:!composerCanEdit(),handle:'.campaign-drag-handle',draggable:'.campaign-step-item',animation:matchMedia('(prefers-reduced-motion: reduce)').matches?0:120,
  delayOnTouchOnly:true,delay:180,ghostClass:'campaign-step-ghost',
  onEnd:event=>moveCampaignStep(event.oldIndex,event.newIndex)
 });
 renderActiveCampaignStep();composerRendering=false;setCampaignComposerMode(composerMode);updateCampaignEditorTools();
}
function renderActiveCampaignStep(){
 const step=campaignDraft.sequence[composerActive], panel=document.getElementById('campaign-step-editor');
 if(!step){panel.innerHTML='<p>No message yet. Add the initial message.</p>';document.getElementById('campaign-step-title').textContent='Message sequence';return;}
 panel.dataset.index=composerActive;
 document.getElementById('campaign-step-title').textContent='Message '+(composerActive+1)+' · '+(composerActive===0?'Initial message':'Follow-up');
 panel.innerHTML='<label class="form-label" for="campaign-step-subject">Subject</label><input class="form-input" id="campaign-step-subject" maxlength="200" value="'+escHtml(step.subject)+'" onfocus="composerTarget=\'subject\'" oninput="campaignStepChanged()">'+
 '<div class="campaign-text-heading"><span id="campaign-step-body-label">Message</span><span id="campaign-text-count" class="muted"></span></div>'+
 '<div class="campaign-writing-toolbar" role="group" aria-label="Edit text"><button class="btn btn-secondary btn-sm" type="button" id="campaign-undo" onclick="campaignEditorUndo()">Undo</button><button class="btn btn-secondary btn-sm" type="button" id="campaign-redo" onclick="campaignEditorRedo()">Redo</button></div><div class="campaign-format-toolbar" role="group" aria-label="Format message">'+campaignFormatToolbar()+'</div>'+
 '<div id="campaign-step-body-host"></div><div class="campaign-placeholder-tools" role="group" aria-label="Insert placeholders"><span>Insert:</span>'+[['first_name','First name'],['last_name','Last name'],['company','Company'],['title','Title'],['personalization','Personalization']].map(([key,label])=>'<button class="btn btn-secondary btn-sm" type="button" onclick="insertCampaignPlaceholder(\''+key+'\')">'+label+'</button>').join('')+'</div>'+
 '<section class="campaign-attachments" aria-label="Attachments"><div class="campaign-attachment-heading"><strong>Attachments</strong><button class="btn btn-secondary btn-sm" type="button" onclick="document.getElementById(\'campaign-attachment-input\').click()">Add files</button><input hidden type="file" id="campaign-attachment-input" multiple accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.docx,.xlsx" onchange="uploadCampaignAttachments(this.files)"></div><p class="muted">Up to 5 files · 10 MB each · 20 MB total per message</p><div id="campaign-attachment-list"></div><p id="campaign-upload-status" role="status"></p></section>'+
 (composerActive?'<div class="campaign-wait-setting"><label class="form-label" for="campaign-step-delay">Delay after the previous message</label><div><input class="form-input" type="number" min="0" max="365" step="1" id="campaign-step-delay" value="'+step.delay_days+'" oninput="campaignStepChanged()"><span>days</span></div></div>':'<p class="muted campaign-first-hint">The initial message can send after your approval.</p>')+
 '<div class="campaign-message-actions" role="group" aria-label="Manage message"><button class="btn btn-secondary btn-sm" type="button" id="campaign-move-up" onclick="moveCampaignStep(composerActive,composerActive-1,true)">Move up</button><button class="btn btn-secondary btn-sm" type="button" id="campaign-move-down" onclick="moveCampaignStep(composerActive,composerActive+1,true)">Move down</button><button class="btn btn-secondary btn-sm" type="button" id="campaign-duplicate" onclick="duplicateCampaignStep()">Duplicate</button><button class="btn btn-secondary btn-sm campaign-remove-step" type="button" id="campaign-remove" onclick="removeCampaignStep(composerActive)">Remove</button></div>';
 const host=document.getElementById('campaign-step-body-host');
 if(window.CampaignComposerDeps){
  let record=composerEditors.get(step);
  if(!record){
   const deps=CampaignComposerDeps,element=document.createElement('div');element.className='campaign-body-editor';element.setAttribute('data-user-content','');
   record={element,editor:new deps.Editor({element,extensions:[deps.Document,deps.Paragraph,deps.Text,deps.HardBreak,deps.UndoRedo,deps.Bold,deps.Italic,deps.Strike,deps.Underline,deps.Link.configure({openOnClick:false,autolink:false,linkOnPaste:false}),deps.BulletList,deps.OrderedList,deps.ListItem,deps.Blockquote],
    content:step.body_doc||campaignPlainDoc(step.body),editable:composerCanEdit(),injectCSS:false,
    editorProps:{attributes:{role:'textbox','aria-multiline':'true','aria-labelledby':'campaign-step-body-label'},
     handlePaste(view,event){const text=event.clipboardData?.getData('text/plain');if(text===undefined)return false;event.preventDefault();view.dispatch(view.state.tr.insertText(text));return true;}},
    onFocus(){composerTarget='body';},onUpdate({editor}){step.body=campaignBodyText(editor);step.body_doc=editor.getJSON();if(!composerRendering){campaignDraftDirty=true;updateCampaignStepSummary();renderCampaignPreview();updateCampaignEditorTools();}},
    onTransaction(){if(!composerRendering)updateCampaignEditorTools();}
   })};composerEditors.set(step,record);
  }
  host.appendChild(record.element);record.editor.setEditable(composerCanEdit(),false);
 }else{
  host.innerHTML='<textarea data-user-content class="form-input" id="campaign-step-body-fallback" aria-labelledby="campaign-step-body-label" rows="9" maxlength="15000" onfocus="composerTarget=\'body\'" oninput="campaignStepChanged()">'+escHtml(step.body)+'</textarea>';
 }
 renderCampaignAttachments();
 document.querySelectorAll('#campaign-step-editor input,#campaign-step-editor textarea').forEach(el=>el.disabled=!composerCanEdit());
}
function updateCampaignEditorTools(){
 const step=campaignDraft?.sequence[composerActive];if(!step)return;
 const editor=composerEditors.get(step)?.editor, editable=composerCanEdit();
 for(const [id,enabled] of [['campaign-undo',editor?.can().undo()],['campaign-redo',editor?.can().redo()],['campaign-move-up',composerActive>0],['campaign-move-down',composerActive<campaignDraft.sequence.length-1],['campaign-duplicate',campaignDraft.sequence.length<10],['campaign-remove',campaignDraft.sequence.length>1]]){
  const button=document.getElementById(id);if(button)button.disabled=!editable||!enabled;
 }
 document.querySelectorAll('.campaign-placeholder-tools button').forEach(button=>button.disabled=!editable);
 document.querySelectorAll('.campaign-format-toolbar button').forEach(button=>button.disabled=!editable||!editor);
 document.querySelectorAll('[data-format]').forEach(button=>{button.setAttribute('aria-pressed',String(!!editor?.isActive(button.dataset.format)));});
 document.querySelectorAll('.campaign-attachments button').forEach(button=>button.disabled=!editable);
 const count=document.getElementById('campaign-text-count');if(count){const words=step.body?.trim()?step.body.trim().split(/\s+/).length:0;count.textContent=words+'/220 '+tr('words')+' · '+(step.body||'').length+'/15000 '+tr('characters');count.classList.toggle('crm-blocked',(step.body||'').length>15000||words>220);}
}
function selectCampaignStep(index){captureCampaignEditor();composerActive=index;renderCampaignSteps();renderCampaignPreview();}
function commitCampaignSequence(){
 campaignDraft.sequence.forEach((step,i)=>{step.step=i+1;if(i===0)step.delay_days=0;});
 campaignDraftDirty=true;renderCampaignSteps();renderCampaignPreview();
 document.getElementById('campaign-composer-announcement').textContent=tr('Sequence updated. Selected message:')+' '+(composerActive+1);
}
function moveCampaignStep(from,to,focus=false){
 if(!composerCanEdit()||from===to||to<0||to>=campaignDraft.sequence.length)return;
 captureCampaignEditor();const selected=campaignDraft.sequence[composerActive],first=campaignDraft.sequence[0];
 const [step]=campaignDraft.sequence.splice(from,1);
 campaignDraft.sequence.splice(to,0,step);if(campaignDraft.sequence.indexOf(first)>0&&first.delay_days===0)first.delay_days=3;composerActive=campaignDraft.sequence.indexOf(selected);commitCampaignSequence();
 if(focus)document.querySelector('#campaign-step-list [aria-current="step"]')?.focus();
}
function addCampaignStep(){
 if(!composerCanEdit()||campaignDraft.sequence.length>=10)return;
 captureCampaignEditor();campaignDraft.sequence.push({subject:'',body:'',delay_days:campaignDraft.sequence.length?3:0});composerActive=campaignDraft.sequence.length-1;composerMode='edit';commitCampaignSequence();document.getElementById('campaign-step-subject')?.focus();
}
function duplicateCampaignStep(){
 if(!composerCanEdit()||campaignDraft.sequence.length>=10)return;
 captureCampaignEditor();const copy={...JSON.parse(JSON.stringify(campaignDraft.sequence[composerActive])),delay_days:composerActive===0?3:campaignDraft.sequence[composerActive].delay_days};
 campaignDraft.sequence.splice(composerActive+1,0,copy);composerActive++;commitCampaignSequence();
}
function removeCampaignStep(index){
 if(!composerCanEdit()||campaignDraft.sequence.length<=1)return;
 captureCampaignEditor();const step=campaignDraft.sequence[index];
 if((step.subject||step.body)&&!confirm(tr('Remove this message from the draft?')))return;
 composerEditors.get(step)?.editor?.destroy();composerEditors.delete(step);campaignDraft.sequence.splice(index,1);composerActive=Math.min(index,campaignDraft.sequence.length-1);commitCampaignSequence();
}
function insertCampaignPlaceholder(key){
 if(!composerCanEdit())return;const text='{{'+key+'}}';
 if(composerTarget==='subject'){
  const input=document.getElementById('campaign-step-subject');input.setRangeText(text,input.selectionStart??input.value.length,input.selectionEnd??input.value.length,'end');input.focus();campaignStepChanged();
 }else{
  const editor=composerEditors.get(campaignDraft.sequence[composerActive])?.editor;
  if(editor)editor.chain().focus().insertContent({type:'text',text}).run();
  else{const input=document.getElementById('campaign-step-body-fallback');input.setRangeText(text,input.selectionStart,input.selectionEnd,'end');input.focus();campaignStepChanged();}
 }
}
function campaignEditorUndo(){composerEditors.get(campaignDraft.sequence[composerActive])?.editor?.chain().focus().undo().run();}
function campaignEditorRedo(){composerEditors.get(campaignDraft.sequence[composerActive])?.editor?.chain().focus().redo().run();}
function setCampaignComposerMode(mode){
 composerMode=mode;document.getElementById('campaign-step-editor').hidden=mode!=='edit';document.getElementById('campaign-preview-panel').hidden=mode!=='preview';
 document.getElementById('campaign-mode-edit').setAttribute('aria-pressed',String(mode==='edit'));document.getElementById('campaign-mode-preview').setAttribute('aria-pressed',String(mode==='preview'));
 if(mode==='preview'){renderCampaignPreview();campaignPreviewFingerprint=campaignWorkflowFingerprint();}
 refreshCampaignGuide();
}
function renderCampaignPreview(){
 if(!campaignDraft)return;captureCampaignEditor();
 const selected=document.getElementById('campaign-preview-contact').value,contact=campaignDraft.contacts.find(p=>p.id===selected)||{};
 const render=text=>String(text||'').replace(/\{\{\s*(first_name|last_name|company|title|personalization)\s*\}\}/g,(_,key)=>contact[key==='personalization'?'personalization_notes':key]||'');
 const step=campaignDraft.sequence[composerActive];if(!step){document.getElementById('campaign-preview').textContent='No message yet.';return;}
 const subject=render(step.subject),body=render(step.body),leftovers=/\{\{?\s*\w+\s*\}?\}/.test(subject+' '+body);
 document.getElementById('campaign-preview').innerHTML=(leftovers?'<p class="crm-blocked">Unknown placeholders. Correct them before review.</p>':'')+'<article data-user-content class="crm-preview-message"><h4>'+escHtml(subject||tr('No subject yet'))+'</h4><div class="campaign-formatted-content" data-user-content>'+ (step.body_doc?campaignRichHtml(step.body_doc,{...contact,personalization:contact.personalization_notes}):'<p>'+escHtml(body||tr('No message yet'))+'</p>')+'</div><div class="campaign-preview-files">'+campaignAttachmentLinks(step.attachments)+'</div></article>';
 refreshCampaignGuide();
}
function refreshCampaignComposerState(){
 const editable=composerCanEdit();
 document.querySelectorAll('#campaign-draft-form input,#campaign-draft-form textarea,#campaign-draft-form button').forEach(el=>el.disabled=!editable);
 composerEditors.forEach(record=>record.editor?.setEditable(editable,false));
 composerSortable?.option('disabled',!editable);
 document.querySelectorAll('#campaign-step-editor input,#campaign-step-editor textarea').forEach(el=>el.disabled=!editable);
 document.querySelectorAll('.campaign-step-select').forEach(el=>el.disabled=campaignUploading);
 document.querySelectorAll('#campaign-mode-edit,#campaign-mode-preview,#campaign-save-status button').forEach(el=>el.disabled=false);
 document.querySelectorAll('#campaign-save,#campaign-prepare,#campaign-recipient-search').forEach(el=>el.disabled=!editable);
 document.getElementById('campaign-add-step').disabled=!editable||campaignDraft.sequence.length>=10;
 updateCampaignEditorTools();refreshCampaignGuide();
}

function campaignFormatToolbar(){
 const tools=[['bold','Bold','<strong>B</strong>'],['italic','Italic','<em>I</em>'],['underline','Underline','<u>U</u>'],['strike','Strikethrough','<s>S</s>'],['bulletList','Bullet list','<svg viewBox="0 0 24 24"><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/></svg>'],['orderedList','Numbered list','<svg viewBox="0 0 24 24"><path d="M10 6h10M10 12h10M10 18h10M3 4h2v4M3 10h3l-3 4h3M3 17h3v4H3"/></svg>'],['blockquote','Quote','<svg viewBox="0 0 24 24"><path d="M4 6h6v7H4zM14 6h6v7h-6zM10 13c0 4-2 5-4 5M20 13c0 4-2 5-4 5"/></svg>'],['link','Link','<svg viewBox="0 0 24 24"><path d="m10 7 3-3a5 5 0 0 1 7 7l-3 3M14 17l-3 3a5 5 0 0 1-7-7l3-3M8 16l8-8"/></svg>']];
 return tools.map(([key,label,icon])=>'<button type="button" data-format="'+key+'" aria-label="'+label+'" title="'+label+'" aria-pressed="false" onmousedown="event.preventDefault()" onclick="formatCampaignText(\''+key+'\')">'+icon.replace('<svg ','<svg aria-hidden="true" ')+'</button>').join('')+'<button type="button" aria-label="Insert emoji" title="Insert emoji" onmousedown="event.preventDefault()" onclick="insertCampaignEmoji()"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 14c2 3 6 3 8 0M8 9h.01M16 9h.01"/></svg></button>';
}
function formatCampaignText(kind){
 if(!composerCanEdit())return;const editor=composerEditors.get(campaignDraft.sequence[composerActive])?.editor;if(!editor)return;
 const commands={bold:'toggleBold',italic:'toggleItalic',underline:'toggleUnderline',strike:'toggleStrike',bulletList:'toggleBulletList',orderedList:'toggleOrderedList',blockquote:'toggleBlockquote'};
 if(kind==='link'){
  const value=prompt(tr('Enter a link (https://, http:// or mailto:). Leave empty to remove it.'),editor.getAttributes('link').href||'https://');
  if(value===null)return;if(!value.trim()){editor.chain().focus().extendMarkRange('link').unsetLink().run();return;}
  try{const url=new URL(value.trim());if(!['https:','http:','mailto:'].includes(url.protocol)||url.username||url.password||/[\x00-\x20]/.test(value.trim()))throw Error();editor.chain().focus().extendMarkRange('link').setLink({href:value.trim()}).run();}
  catch{showToast(tr('Please enter a valid web or email link.'),'error');}
 }else if(commands[kind])editor.chain().focus()[commands[kind]]().run();
}
function insertCampaignEmoji(){
 if(!composerCanEdit())return;const value=prompt(tr('Insert an emoji or symbol:'),'');if(!value)return;
 composerEditors.get(campaignDraft.sequence[composerActive])?.editor?.chain().focus().insertContent({type:'text',text:value.slice(0,20)}).run();
}
function renderCampaignAttachments(){
 const step=campaignDraft?.sequence[composerActive],list=document.getElementById('campaign-attachment-list');if(!step||!list)return;
 list.innerHTML=(step.attachments||[]).map((file,i)=>'<div class="campaign-attachment">'+campaignAttachmentLinks([file])+'<button class="btn btn-secondary btn-sm" type="button" onclick="removeCampaignAttachment('+i+')"'+(!composerCanEdit()?' disabled':'')+'>Remove attachment</button></div>').join('');
}
function removeCampaignAttachment(index){
 if(!composerCanEdit())return;const step=campaignDraft.sequence[composerActive];step.attachments.splice(index,1);step.attachment_ids=step.attachments.map(file=>file.id);campaignDraftDirty=true;renderCampaignAttachments();renderCampaignPreview();
}
async function uploadCampaignAttachments(files){
 if(!composerCanEdit()||!files.length)return;
 const step=campaignDraft.sequence[composerActive],chosen=[...files],existing=step.attachments||[];
 if(chosen.length+existing.length>5||chosen.some(file=>file.size>10*1024*1024)||chosen.reduce((sum,file)=>sum+file.size,0)+existing.reduce((sum,file)=>sum+file.size,0)>20*1024*1024){showToast(tr('Choose up to 5 files, at most 10 MB each and 20 MB in total.'),'error');return;}
 captureCampaignEditor();campaignSaving=true;campaignUploading=true;refreshCampaignComposerState();
 const status=document.getElementById('campaign-upload-status');
 try{
  step.attachments=existing;
  for(const file of chosen){
   status.textContent=tr('Uploading:')+' '+file.name;
   const response=await fetch('/api/campaign-attachments?filename='+encodeURIComponent(file.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file});
   const data=await response.json();if(!response.ok)throw Error(data.error||tr('Upload failed.'));
   step.attachments.push(data);step.attachment_ids=step.attachments.map(file=>file.id);campaignDraftDirty=true;
  }
  status.textContent=tr('Files attached. Save the draft to keep this selection.');
 }catch(error){status.textContent=error.message;}
 finally{campaignSaving=false;campaignUploading=false;renderCampaignAttachments();renderCampaignPreview();refreshCampaignComposerState();const input=document.getElementById('campaign-attachment-input');if(input)input.value='';}
}
