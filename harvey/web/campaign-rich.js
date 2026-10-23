/* Rich content is rendered from structured nodes, never pasted HTML. */
function campaignRichHtml(doc,values={}){
 const safeLink=value=>{try{const url=new URL(value);return ['https:','http:','mailto:'].includes(url.protocol)&&!url.username&&!url.password&&!/[\x00-\x20]/.test(value)?value:'';}catch{return '';}};
 const tags={paragraph:'p',bulletList:'ul',orderedList:'ol',listItem:'li',blockquote:'blockquote'};
 const marks={bold:'strong',italic:'em',underline:'u',strike:'s'};
 const text=value=>String(value||'').replace(/\{\{\s*(first_name|last_name|company|title|personalization)\s*\}\}/g,(_,key)=>values[key]??'');
 const node=(n,depth=0)=>{
  if(!n||depth>25)return '';
  if(n.type==='text'){
   let out=escHtml(text(n.text)).replace(/\n/g,'<br>');
   for(const mark of n.marks||[]){if(marks[mark.type])out='<'+marks[mark.type]+'>'+out+'</'+marks[mark.type]+'>';else if(mark.type==='link'){const href=safeLink(mark.attrs?.href);if(href)out='<a href="'+escHtml(href)+'" target="_blank" rel="noopener noreferrer">'+out+'</a>';}}
   return out;
  }
  if(n.type==='hardBreak')return '<br>';
  const children=(n.content||[]).map(child=>node(child,depth+1)).join('');
  return tags[n.type]?'<'+tags[n.type]+'>'+children+'</'+tags[n.type]+'>':n.type==='doc'?children:'';
 };
 return node(doc);
}
function campaignSafeMailHtml(html){
 const parsed=new DOMParser().parseFromString(html,'text/html');
 const allowed=new Set(['P','BR','UL','OL','LI','BLOCKQUOTE','STRONG','EM','U','S','A']);
 const render=node=>{
  if(node.nodeType===3)return escHtml(node.textContent);
  if(node.nodeType!==1)return '';
  if(['SCRIPT','STYLE','IFRAME','OBJECT','SVG','MATH'].includes(node.tagName))return '';
  const content=[...node.childNodes].map(render).join('');
  if(!allowed.has(node.tagName))return content;
  const tag=node.tagName.toLowerCase();if(tag==='br')return '<br>';
  let attr='';
  if(tag==='a'){try{const value=node.getAttribute('href')||'',url=new URL(value);if(['https:','http:','mailto:'].includes(url.protocol)&&!/[\x00-\x20]/.test(value))attr=' href="'+escHtml(value)+'" target="_blank" rel="noopener noreferrer"';}catch{}}
  return '<'+tag+attr+'>'+content+'</'+tag+'>';
 };
 return [...parsed.body.childNodes].map(render).join('');
}
function campaignAttachmentLinks(items){return (items||[]).map(item=>'<a data-user-content class="campaign-file-link" href="/api/campaign-attachments/'+encodeURIComponent(item.id)+'" download>'+escHtml(item.filename)+' <small>'+Math.ceil(item.size/1024)+' KB</small></a>').join('');}
