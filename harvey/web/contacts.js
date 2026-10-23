/* Person suggestions stay separate until the owner explicitly saves a contact. */
let peopleJob = null, peopleCandidates = [], peopleRefreshing = false, peopleTimer = null, peopleRefreshAgain = false, peopleCandidatePage = 1;
let contactEditing = null, contactCandidate = null, contactCompanyTimer = null, contactCompanyRequest = 0;
window.peopleSearchRunning = false;
let peopleOpenedJob=null;
function openPeopleResults(){
 const dialog=document.getElementById('people-results-dialog');
 if(!dialog.open)dialog.showModal();
}


async function contactRequest(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Die Anfrage ist fehlgeschlagen. Bitte erneut versuchen.');
  return data;
}
const contactPost = (url, data) => contactRequest(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});

async function startPeopleSearch(ids) {
  const companyIds = ids || [..._companySelection.keys()];
  if (!companyIds.length) return;
  const button = document.getElementById('company-people-search');
  button.disabled = true;
  try {
    peopleJob = await contactPost('/api/company-people-jobs', {company_ids:companyIds});
    await refreshPeopleSearch();
    peopleOpenedJob=peopleJob?.id;openPeopleResults();
  } catch (error) { showToast(error.message, 'error'); }
  finally { updateCompanyToolbar(); }
}

async function refreshPeopleSearch() {
  if (peopleRefreshing) { peopleRefreshAgain = true; return; }
  peopleRefreshing = true;
  clearTimeout(peopleTimer);
  try {
    peopleJob = await contactRequest('/api/company-people-jobs/latest');
    window.peopleSearchRunning = !!peopleJob && ['queued','running'].includes(peopleJob.status);
    const progress = document.getElementById('people-job-progress');
    progress.hidden = !peopleJob;
    progress.max = peopleJob?.total || 1;
    progress.value = peopleJob?.done || 0;
    const stop = document.getElementById('people-job-stop');
    stop.hidden = !window.peopleSearchRunning;
    stop.disabled = !!peopleJob?.stop_requested;
    const status = document.getElementById('people-job-status');
    if (peopleJob) {
      const label = peopleJob.stop_requested && window.peopleSearchRunning ? 'Wird nach den laufenden Unternehmen angehalten …' :
        window.peopleSearchRunning ? 'Ansprechpersonen werden gesucht …' : peopleJob.status === 'stopped' ? 'Suche angehalten.' : 'Suche abgeschlossen.';
      const c = peopleJob.counts;
      status.textContent = `${label} ${peopleJob.done}/${peopleJob.total} Unternehmen · ${c.found} mit Personenfund · ${c.not_found} ohne Personenfund · ${c.no_website} ohne Website · ${c.failed} nicht erreichbar oder fehlgeschlagen.`;
    } else status.textContent = 'Noch keine Suche gestartet. Wähle Unternehmen aus und starte die Suche nach Ansprechpersonen.';
    peopleCandidates = await contactRequest('/api/person-candidates');
    renderPeopleCandidates();
    const results=document.getElementById('company-people-results');
    results.hidden=!window.peopleSearchRunning&&!peopleCandidates.length;
    results.textContent=window.peopleSearchRunning?'Personensuche läuft – Fortschritt':'Personenvorschläge ansehen ('+peopleCandidates.length+')';
    if(window.peopleSearchRunning&&peopleOpenedJob!==peopleJob.id&&currentTab==='companies'&&!document.querySelector('dialog[open]')){
      peopleOpenedJob=peopleJob.id;openPeopleResults();
    }
    updateCompanyToolbar();
  } catch (error) {
    document.getElementById('people-job-status').textContent = 'Verbindung unterbrochen. Eine gestartete Suche läuft auf dem Server weiter. Erneut versuchen über Aktualisieren.';
  } finally {
    peopleRefreshing = false;
    if (window.peopleSearchRunning || peopleRefreshAgain) peopleTimer = setTimeout(refreshPeopleSearch, peopleRefreshAgain ? 0 : 1500);
    peopleRefreshAgain = false;
  }
}

async function stopPeopleSearch() {
  if (!peopleJob) return;
  document.getElementById('people-job-stop').disabled = true;
  try { await contactPost('/api/company-people-jobs/' + encodeURIComponent(peopleJob.id) + '/stop', {}); await refreshPeopleSearch(); }
  catch (error) { showToast(error.message, 'error'); document.getElementById('people-job-stop').disabled = false; }
}

function renderPeopleCandidates() {
  const el = document.getElementById('people-candidates');
  if (!peopleCandidates.length) {
    el.innerHTML = '<p class="muted">Keine offenen Personenvorschläge. Bereits übernommene Personen findest du unter Kontakte.</p>';
    return;
  }
  peopleCandidatePage = Math.min(peopleCandidatePage, Math.max(1, Math.ceil(peopleCandidates.length / 20)));
  const offset = (peopleCandidatePage - 1) * 20;
  el.innerHTML = '<p>' + peopleCandidates.length + ' offene Vorschläge aus bisherigen Suchen</p>' + peopleCandidates.slice(offset, offset + 20).map((p,j) => { const i = offset + j; return '<article class="person-candidate"><strong>' + escHtml(p.first_name + ' ' + p.last_name) + '</strong><p>' +
    escHtml([p.title || 'Position nicht angegeben', p.company, p.email || 'Keine persönliche E-Mail veröffentlicht', p.phone].filter(Boolean).join(' · ')) +
    '</p><p><a href="' + escHtml(safeContactSource(p.source_url)) + '" target="_blank" rel="noopener noreferrer">Quelle öffnen</a> · Gefunden: ' + escHtml(formatDate(p.found_at)) +
    '</p><button class="btn btn-primary btn-sm" onclick="reviewPersonCandidate(' + i + ')">Prüfen und übernehmen</button>' +
    '<button class="btn btn-secondary btn-sm" onclick="dismissPersonCandidate(' + i + ',this)">Verwerfen</button></article>'; }).join('') + (peopleCandidates.length > 20 ? '<div class="people-candidate-pages"><button class="btn btn-secondary btn-sm" onclick="changePeopleCandidatePage(-1)"' + (peopleCandidatePage === 1 ? ' disabled' : '') + '>Zurück</button><span>Seite ' + peopleCandidatePage + ' von ' + Math.ceil(peopleCandidates.length / 20) + '</span><button class="btn btn-secondary btn-sm" onclick="changePeopleCandidatePage(1)"' + (offset + 20 >= peopleCandidates.length ? ' disabled' : '') + '>Weiter</button></div>' : '');
}

function changePeopleCandidatePage(delta) { peopleCandidatePage += delta; renderPeopleCandidates(); }

function safeContactSource(url) {
  try { const parsed = new URL(url); return ['http:','https:'].includes(parsed.protocol) ? parsed.href : '#'; } catch { return '#'; }
}

async function dismissPersonCandidate(index, button) {
  const person = peopleCandidates[index];
  if (!person) return;
  button.disabled = true;
  try { await contactPost('/api/person-candidates/' + encodeURIComponent(person.id) + '/dismiss', {}); await refreshPeopleSearch(); }
  catch (error) { showToast(error.message, 'error'); button.disabled = false; }
}

function reviewPersonCandidate(index) {
  const candidate = peopleCandidates[index];
  if (candidate) openContactEditor(null, false, candidate);
}

async function openContactEditor(index = null, asCompany = false, candidate = null, editing = null) {
  const dialog = document.getElementById('contact-editor');
  document.getElementById('contact-editor-form').reset();
  resetKnownCompanyEmails();
  ++contactCompanyRequest;
  clearTimeout(contactCompanyTimer);
  contactCandidate = candidate;
  contactEditing = editing;
  document.getElementById('contact-editor-error').hidden = true;
  document.getElementById('contact-editor-save').disabled = false;
  document.getElementById('contact-type').disabled = !!candidate || !!editing;
  const company = index !== null ? _companies[index] : null;
  document.getElementById('contact-editor-intro').textContent = editing ? 'Korrigiere die Angaben. Bei geänderter E-Mail ist eine erneute Prüfung nötig. Wartende Nachrichten werden bei Änderungen abgebrochen.' : candidate ? 'Prüfe die Originalquelle und ergänze bei Bedarf die Kontaktdaten.' : 'Erfasse eine bekannte Person oder einen allgemeinen Firmenkontakt.';
  document.getElementById('contact-company-search').hidden = !!candidate;
  document.querySelector('label[for="contact-company-search"]').hidden = !!candidate;
  document.getElementById('contact-editor-title').textContent = editing ? 'Kontakt bearbeiten' : candidate ? 'Ansprechperson übernehmen' : 'Kontakt hinzufügen';
  document.getElementById('contact-type').value = editing?.contact_type || (asCompany ? 'company' : 'person');
  for (const [id,key] of [['contact-first','first_name'],['contact-last','last_name'],['contact-title','title'],['contact-email','email'],['contact-phone','phone']]) {
    document.getElementById(id).value = (candidate || editing)?.[key] || (asCompany && key === 'phone' ? company?.phone || '' : '');
  }
  const companySelect = document.getElementById('contact-company');
  const selectedId = candidate?.company_id || editing?.company_id || company?.id || '';
  const selectedName = candidate?.company || editing?.company || company?.name || '';
  companySelect.innerHTML = '<option value="">Ohne Zuordnung / neues Unternehmen</option>' + (selectedId ? '<option selected value="' + escHtml(selectedId) + '">' + escHtml(selectedName) + '</option>' : '');
  companySelect.disabled = !!candidate;
  document.getElementById('contact-company-search').disabled = !!candidate;
  document.getElementById('contact-editor-source').innerHTML = candidate ? '<a href="' + escHtml(safeContactSource(candidate.source_url)) + '" target="_blank" rel="noopener noreferrer">Originalquelle prüfen</a> · Gefunden: ' + escHtml(formatDate(candidate.found_at)) : '';
  updateContactType();
  if (!dialog.open) dialog.showModal();
  document.getElementById(document.getElementById('contact-type').value === 'company' ? 'contact-email' : 'contact-first').focus();
  if (!candidate) await loadContactCompanies('', selectedId, selectedName);
}

function updateContactType() {
  const person = document.getElementById('contact-type').value === 'person';
  document.querySelector('.contact-person-fields').hidden = !person;
  document.getElementById('contact-first').required = person;
  document.getElementById('contact-last').required = person;
  contactCompanyChanged();
}
function contactCompanyChanged() {
  const hasCompany = !!document.getElementById('contact-company').value;
  document.getElementById('contact-new-company').hidden = hasCompany;
  document.getElementById('contact-company-name').required = !hasCompany && document.getElementById('contact-type').value === 'company';
  refreshKnownCompanyEmails();
}
function scheduleContactCompanies() {
  clearTimeout(contactCompanyTimer);
  contactCompanyTimer = setTimeout(() => loadContactCompanies(document.getElementById('contact-company-search').value), 300);
}
async function loadContactCompanies(q, selectedId, selectedName) {
  const request = ++contactCompanyRequest;
  const select = document.getElementById('contact-company');
  selectedId = selectedId || select.value;
  selectedName = selectedName || select.selectedOptions[0]?.textContent || '';
  try {
    const rows = await contactRequest('/api/contact-company-options?q=' + encodeURIComponent(q));
    if (request !== contactCompanyRequest) return;
    if (selectedId && !rows.some(c => c.id === selectedId)) rows.unshift({id:selectedId,name:selectedName});
    select.innerHTML = '<option value="">Ohne Zuordnung / neues Unternehmen</option>' + rows.map(c => '<option value="' + escHtml(c.id) + '"' + (c.id === selectedId ? ' selected' : '') + '>' + escHtml(c.name) + '</option>').join('');
    contactCompanyChanged();
  } catch (error) { showToast(error.message, 'error'); }
}
async function saveContactEditor() {
  const button = document.getElementById('contact-editor-save');
  if (button.disabled) return;
  button.disabled = true;
  const errorEl = document.getElementById('contact-editor-error');
  errorEl.hidden = true;
  const data = {};
  for (const [key,id] of Object.entries({contact_type:'contact-type',company_id:'contact-company',company_name:'contact-company-name',website:'contact-company-website',first_name:'contact-first',last_name:'contact-last',title:'contact-title',email:'contact-email',phone:'contact-phone'})) data[key] = document.getElementById(id).value.trim();
  if (data.company_id) { data.company_name = ''; data.website = ''; }
  if (contactEditing) data.revision = contactEditing.revision;
  const endpoint = contactEditing ? '/api/contacts/' + encodeURIComponent(contactEditing.id) : contactCandidate ? '/api/person-candidates/' + encodeURIComponent(contactCandidate.id) + '/accept' : '/api/contacts';
  try {
    const result = await contactRequest(endpoint, {method:contactEditing ? 'PATCH' : 'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    document.getElementById('contact-editor').close();
    showToast(result.updated ? 'Kontakt aktualisiert. Wartende Nachrichten wurden bei Änderungen abgebrochen.' : result.duplicate ? 'Kontakt bereits vorhanden. Deine eingegebenen Ergänzungen wurden nicht gespeichert; bestehende Daten bleiben erhalten.' : 'Kontakt gespeichert. E-Mail bleibt ungeprüft.', 'success');
    await refreshPeopleSearch();
    if(document.getElementById('decision-maker-dialog')?.open && typeof dmRefresh==='function')await dmRefresh();
    if (document.getElementById('prospects').classList.contains('active')) await loadProspects();
    else if (companyDrill && _companyDetailIndex !== null) await showCompanyContacts(_companyDetailIndex);
    else await loadCompanies();
  } catch (error) { errorEl.textContent = error.message; errorEl.hidden = false; }
  finally { button.disabled = false; }
}

function contactSourceHtml(p) {
  const source = ({manual:'Manuell', public_person:'Öffentliche Unternehmensseite'})[p.source] || p.source || '';
  return escHtml(source) + (p.source_url ? ' <a href="' + escHtml(safeContactSource(p.source_url)) + '" target="_blank" rel="noopener noreferrer">Quelle</a>' : '') + (p.source_found_at ? '<small class="muted"> · ' + escHtml(formatDate(p.source_found_at)) + '</small>' : '');
}

let knownCompanyEmailRequest=0, knownCompanyEmailId='', knownCompanyEmailRows=[];
function resetKnownCompanyEmails(){
 ++knownCompanyEmailRequest;knownCompanyEmailId='';knownCompanyEmailRows=[];
 document.getElementById('contact-known-emails').hidden=true;
 document.getElementById('contact-known-email').replaceChildren();
}
async function refreshKnownCompanyEmails(){
 const id=document.getElementById('contact-company').value;
 if(contactCandidate||contactEditing||document.getElementById('contact-type').value!=='company'||!id){resetKnownCompanyEmails();return;}
 if(knownCompanyEmailId===id)return;
 const previous=knownCompanyEmailRows.some(row=>row.email===document.getElementById('contact-email').value);
 if(previous)document.getElementById('contact-email').value='';
 knownCompanyEmailId=id;knownCompanyEmailRows=[];
 const request=++knownCompanyEmailRequest,wrapper=document.getElementById('contact-known-emails'),select=document.getElementById('contact-known-email'),help=document.getElementById('contact-known-email-help');
 wrapper.hidden=false;select.disabled=true;select.innerHTML='<option>'+escHtml(tr('Loading...'))+'</option>';help.textContent='';
 try{
  const data=await contactRequest('/api/companies/'+encodeURIComponent(id)+'/profile');
  if(request!==knownCompanyEmailRequest)return;
  const seen=new Set();knownCompanyEmailRows=(data.company.contact_emails||[]).filter(row=>{const key=row.email.toLowerCase();if(seen.has(key))return false;seen.add(key);return true;});
  select.innerHTML='<option value="">'+escHtml(tr('Choose an email or enter one below'))+'</option>'+knownCompanyEmailRows.map(row=>'<option data-user-content value="'+escHtml(row.email)+'">'+escHtml(row.email)+'</option>').join('');
  select.disabled=!knownCompanyEmailRows.length;
  help.textContent=tr(knownCompanyEmailRows.length?'Choose which email to use for this company contact. Saving does not verify or send mail.':'No known emails available. You can enter a known address below.');
  if(knownCompanyEmailRows.length===1&&!document.getElementById('contact-email').value){select.value=knownCompanyEmailRows[0].email;chooseKnownCompanyEmail();}
 }catch{
  if(request!==knownCompanyEmailRequest)return;
  select.innerHTML='<option value="">'+escHtml(tr('Known emails unavailable'))+'</option>';
  help.textContent=tr('You can enter a known address below or reopen this dialog to try again.');knownCompanyEmailId='';
 }
}
function chooseKnownCompanyEmail(){
 const value=document.getElementById('contact-known-email').value;
 if(value)document.getElementById('contact-email').value=value;
}
