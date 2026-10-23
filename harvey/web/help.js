/* In-app manual: static bilingual content, no account calls or workflow mutations. */
(() => {
  const root = document.getElementById('help-guide');
  let query = '';
  const words = {
    title:['Hilfe und Arbeitsabläufe','Help and workflows'],
    subtitle:['Vom ersten Firmeneintrag bis zur versendeten Nachricht: Schritt für Schritt, mit Ergebnissen, Grenzen und Lösungen für typische Probleme.','From the first company record to a sent message: step by step, with outcomes, limitations and solutions to common problems.'],
    search:['Handbuch durchsuchen','Search the manual'], placeholder:['Zum Beispiel: E-Mail wartet, KI, Kontakt hinzufügen …','For example: email waiting, AI, add contact …'],
    chapters:['Kapitel anzeigen','Show chapters'],contents:['Inhaltsverzeichnis','Contents'],clear:['Suche zurücksetzen','Clear search'],print:['Drucken / als PDF speichern','Print / save as PDF'],
    start:['Ich möchte …','I want to …'],quick:[['Meine erste Kampagne erstellen','Create my first campaign'],['Eine wartende E-Mail verstehen','Understand a waiting email'],['Unternehmen und Kontakte finden','Find companies and contacts']],
    result:['Ergebnis und Hinweise','Outcome and considerations'], steps:['Schritt für Schritt','Step by step'],diagram:['Ablauf im Überblick','Workflow at a glance'],
    detail:['Ausführliche Anleitung','Detailed instructions'],back:['Zum Inhaltsverzeichnis','Back to contents'], empty:['Kein passendes Kapitel gefunden. Versuche einen kürzeren Begriff wie „Versand“, „Kontakt“ oder „KI“.','No matching chapter found. Try a shorter term such as “sending”, “contact” or “AI”.'],
    count:['{n} von {total} Kapiteln','{n} of {total} chapters'],all:['Alle Kapitel anzeigen','Show all chapters'],
    language:['Du liest die deutsche Ausgabe. EN oben wechselt das vollständige Handbuch ins Englische.','You are reading the English edition. DE in the header switches the entire manual to German.']
  };
  let locale = 'de';
  const t = pair => pair[locale === 'de' ? 0 : 1];
  const esc = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const flat = value => Array.isArray(value) ? value.map(flat).join(' ') : typeof value === 'object' && value ? Object.values(value).map(flat).join(' ') : String(value);
  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();
  const indexes = new Map(helpChapters.map(chapter => [chapter.id,normalize(flat(chapter))]));
  const arrow = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg>';
  function chapterHtml(c) {
    return '<article class="help-chapter" id="guide-'+c.id+'" aria-labelledby="guide-title-'+c.id+'">'+
      '<h3 id="guide-title-'+c.id+'" tabindex="-1">'+esc(t(c.title))+'</h3><p class="help-intro">'+esc(t(c.intro))+'</p>'+
      (c.flow ? '<figure class="help-workflow"><figcaption>'+esc(t(words.diagram))+'</figcaption><ol>'+c.flow.map(item=>'<li>'+esc(t(item))+'</li>').join('')+'</ol></figure>' : '')+
      (c.steps ? '<h4>'+esc(t(words.steps))+'</h4><ol class="help-instructions">'+c.steps.map(step=>'<li><h5>'+esc(t(step[0]))+'</h5><p>'+esc(t(step[1]))+'</p></li>').join('')+'</ol>' : '')+
      (c.rows ? '<div class="help-table-wrap" role="region" aria-label="'+esc(t(c.title))+'" tabindex="0"><table><caption class="sr-only">'+esc(t(c.title))+'</caption><thead><tr>'+c.headers.map(h=>'<th scope="col">'+esc(t(h))+'</th>').join('')+'</tr></thead><tbody>'+c.rows.map(row=>'<tr><th scope="row">'+esc(t(row[0]))+'</th><td>'+esc(t(row[1]))+'</td></tr>').join('')+'</tbody></table></div>' : '')+
      (c.status ? '<dl class="help-status-list">'+c.status.map(item=>'<div><dt><span class="help-status-dot '+item[0]+'" aria-hidden="true"></span>'+esc(t(item[1]))+'</dt><dd>'+esc(t(item[2]))+'</dd></div>').join('')+'</dl>' : '')+
      (c.faq ? '<div class="help-faq">'+c.faq.map(item=>'<details><summary>'+esc(t(item[0]))+'</summary><p>'+esc(t(item[1]))+'</p></details>').join('')+'</div>' : '')+
      (c.note ? '<aside class="help-note"><h4>'+esc(t(words.result))+'</h4><p>'+esc(t(c.note))+'</p></aside>':'')+
      '<a class="help-back" href="#help-contents" data-help-back>'+esc(t(words.back))+'</a></article>';
  }
  function render() {
    locale = window.harveyLanguage?.() === 'en' ? 'en' : 'de';
    const openFaqs = [...root.querySelectorAll('.help-faq details')].map((d,i)=>d.open?i:-1).filter(i=>i>=0);
    const activeId = root.querySelector('.help-toc a[aria-current]')?.dataset.helpTopic;
    root.lang=locale;
    let previous='';
    const toc = helpChapters.map(c=>{
      const group=t(c.group), heading=group!==previous ? '<li class="help-toc-group">'+esc(group)+'</li>' : ''; previous=group;
      return heading+'<li data-help-index="'+c.id+'"><a href="#guide-'+c.id+'" data-help-topic="'+c.id+'"'+(activeId===c.id?' aria-current="location"':'')+'>'+esc(t(c.title))+'</a></li>';
    }).join('');
    root.innerHTML='<div class="section-head help-heading"><div><h2>'+esc(t(words.title))+'</h2><p>'+esc(t(words.subtitle))+'</p></div><button type="button" class="btn btn-secondary btn-sm" data-help-print>'+esc(t(words.print))+'</button></div>'+
      '<p class="help-language">'+esc(t(words.language))+'</p>'+
      '<div class="help-start"><h3>'+esc(t(words.start))+'</h3><div>'+['campaign','sending','discover'].map((id,i)=>'<a href="#guide-'+id+'" data-help-topic="'+id+'">'+esc(t(words.quick[i]))+arrow+'</a>').join('')+'</div></div>'+
      '<div class="help-layout"><aside class="help-index" id="help-contents"><h3 tabindex="-1">'+esc(t(words.contents))+'</h3><label class="form-label" for="help-search">'+esc(t(words.search))+'</label><div class="help-search-controls"><input id="help-search" class="form-input" type="search" placeholder="'+esc(t(words.placeholder))+'" value="'+esc(query)+'" aria-controls="help-chapters"><button class="help-clear" type="button" data-help-clear aria-label="'+esc(t(words.clear))+'">'+esc(t(words.clear))+'</button></div><p id="help-search-count" role="status" aria-live="polite"></p><details class="help-toc-disclosure"'+(window.matchMedia('(min-width: 1001px)').matches?' open':'')+'><summary>'+esc(t(words.chapters))+'</summary><nav class="help-toc" aria-label="'+esc(t(words.contents))+'"><ul>'+toc+'</ul></nav></details></aside>'+
      '<div class="help-reading"><div id="help-empty" class="help-empty" hidden><p>'+esc(t(words.empty))+'</p><button type="button" class="btn btn-secondary" data-help-clear>'+esc(t(words.all))+'</button></div><div id="help-chapters">'+helpChapters.map(chapterHtml).join('')+'</div></div></div>';
    root.querySelectorAll('.help-faq details').forEach((d,i)=>d.open=openFaqs.includes(i));
    filter();
  }
  function filter() {
    const tokens=normalize(query.trim()).split(/\s+/).filter(Boolean);
    let count=0;
    for(const chapter of helpChapters) {
      const shown=tokens.every(token=>indexes.get(chapter.id).includes(token));
      root.querySelector('#guide-'+chapter.id).hidden=!shown;
      root.querySelector('[data-help-index="'+chapter.id+'"]').hidden=!shown;
      if(shown) count++;
    }
    root.querySelectorAll('.help-toc-group').forEach(group=>{
      let item=group.nextElementSibling, visible=false;
      while(item && !item.classList.contains('help-toc-group')) { if(!item.hidden) visible=true; item=item.nextElementSibling; }
      group.hidden=!visible;
    });
    root.querySelector('#help-search-count').textContent=t(words.count).replace('{n}',count).replace('{total}',helpChapters.length);
    root.querySelector('#help-empty').hidden=count>0;
    root.querySelector('.help-clear').hidden=!query;
  }
  function clearSearch() { query=''; root.querySelector('#help-search').value='';filter(); }
  root.addEventListener('input',event=>{if(event.target.id==='help-search'){query=event.target.value;filter();}});
  root.addEventListener('click',event=>{
    const topic=event.target.closest('[data-help-topic]');
    if(topic){
      event.preventDefault();clearSearch();
      const target=root.querySelector('#guide-title-'+topic.dataset.helpTopic);
      root.querySelectorAll('.help-toc a').forEach(a=>a.removeAttribute('aria-current'));
      root.querySelector('.help-toc [data-help-topic="'+topic.dataset.helpTopic+'"]').setAttribute('aria-current','location');
      target.focus({preventScroll:true});target.scrollIntoView({block:'start',behavior:'instant'});
    }
    if(event.target.closest('[data-help-clear]')){clearSearch();root.querySelector('#help-search').focus();}
    if(event.target.closest('[data-help-back]')){event.preventDefault();root.querySelector('#help-contents h3').focus({preventScroll:true});root.querySelector('#help-contents').scrollIntoView({block:'start',behavior:'instant'});}
    if(event.target.closest('[data-help-print]')) window.print();
  });
  window.matchMedia('(min-width: 1001px)').addEventListener('change',event=>{
    root.querySelector('.help-toc-disclosure').open=event.matches;
  });
  let printDetails=[];
  window.addEventListener('beforeprint',()=>{
    printDetails=[...root.querySelectorAll('.help-faq details')].map(detail=>[detail,detail.open]);
    printDetails.forEach(([detail])=>detail.open=true);
  });
  window.addEventListener('afterprint',()=>{printDetails.forEach(([detail,open])=>detail.open=open);printDetails=[];});
  window.addEventListener('harvey-language-changed',render);
  render();
})();
