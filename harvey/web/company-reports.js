/* Company report UI. Saved evidence stays separate from optional AI prose. */
let reportCompanies=[],reportCurrent=null,reportGeneration=0,reportBusy=false,reportReturnFocus=null;
const reportText=(de,en)=>window.harveyLanguage?.()==='de'?de:en;
const reportErrors=code=>({invalid_companies:reportText('Bitte 1 bis 20 Unternehmen auswählen.','Select 1–20 companies.'),invalid_categories:reportText('Mindestens eine Signalkategorie auswählen.','Select at least one signal category.'),invalid_options:reportText('Sprache und Belegalter prüfen (1–365 Tage).','Check language and evidence age (1–365 days).'),company_unavailable:reportText('Ein Unternehmen ist nicht mehr verfügbar. Auswahl aktualisieren.','A company is no longer available. Refresh the selection.'),no_signals:reportText('Keine Signale in diesen Kategorien vorhanden.','No signals exist in these categories.'),ai_busy:reportText('Eine KI-Erläuterung läuft bereits.','An AI explanation is already running.'),ai_unavailable:reportText('KI-Erläuterung nicht verfügbar. Der Faktenbericht bleibt erhalten.','AI explanation unavailable. The factual report is retained.')})[code]||reportText('Anfrage fehlgeschlagen. Bitte erneut versuchen.','Request failed. Please try again.');
function updateCompanyReportAction(){
 const count=_companySelection.size,button=document.getElementById('company-report-action');
 button.disabled=count<1||count>20;
 const hint=count<1?reportText('Markiere zuerst ein Unternehmen in der Liste.','Select a company in the list first.'):count>20?reportText('Bitte höchstens 20 Unternehmen für einen Berichtslauf auswählen.','Select up to 20 companies per report batch.'):reportText('Für die ausgewählten Unternehmen · aus gespeicherten Signalen.','For the selected companies · from saved signals.');
 button.title=hint;button.dataset.companyTip=hint;button.setAttribute('aria-description',hint);
}
function reportLabels(){
 for(const [id,de,en] of [['reports-title','Optimierungsberichte','Optimization reports'],['reports-close','Schließen','Close'],['reports-options-title','Berichtseinstellungen','Report options'],['reports-categories-label','Signalkategorien','Signal categories'],['reports-language-label','Berichtssprache','Report language'],['reports-age-label','Maximales Belegalter in Tagen','Maximum evidence age in days'],['reports-create','Berichte für Auswahl erstellen','Create reports for selection'],['reports-company-label','Unternehmen','Company'],['reports-history-label','Gespeicherte Berichte','Saved reports'],['reports-ai','KI-Erläuterung ergänzen','Add AI explanation'],['reports-markdown','Markdown herunterladen','Download Markdown'],['reports-print','PDF / Drucken','PDF / Print']])document.getElementById(id).textContent=reportText(de,en);
 document.getElementById('reports-intro').textContent=reportText('Pro Unternehmen ein Bericht aus gespeicherten Signalen. Keine neue Website-Prüfung. Fehlende Daten bleiben offene Prüfpunkte.','One report per company from saved signals. No new website audit. Missing data remains an open check.');
 document.getElementById('reports-pdf-note').textContent=reportText('PDF öffnet die Druckansicht. Wähle dort „Als PDF sichern“. KI erklärt bis zu sechs belegte Signale: digitale Sichtbarkeit, KI-Suche, mögliche Kundengewinnung und nächste Schritte. Ableitungen sind keine gemessenen Ergebnisse.','PDF opens the print view. Choose “Save as PDF” there. AI explains up to six evidenced signals: digital visibility, AI search, potential customer acquisition and next steps. Inferences are not measured outcomes.');
 document.getElementById('reports-action-label').textContent=reportText('Optimierungsbericht erstellen','Create optimization report');
 for(const [value,de,en] of [['discovery','Sichtbarkeit und Verzeichnisse','Visibility and listings'],['profile','Website und Unternehmensprofil','Website and company profile'],['people','Ansprechpersonen','People'],['verification','Verifizierung','Verification']])document.querySelector('[data-report-category="'+value+'"]').textContent=reportText(de,en);
 updateCompanyReportAction();
 if(reportCurrent?.ai&&reportCurrent.ai.version!==2)document.getElementById('reports-ai').textContent=reportText('KI-Analyse erweitern','Extend AI analysis');
 document.getElementById('reports-frame').title=reportText('Vorschau des Unternehmensberichts','Company report preview');
}
async function openCompanyReports(companies=null,returnFocus=null){
 const chosen=companies||[..._companySelection.values()];if(!chosen.length||chosen.length>20){alert(reportErrors('invalid_companies'));return;}
 reportReturnFocus=returnFocus||document.getElementById('company-actions-trigger');reportCompanies=chosen;reportCurrent=null;++reportGeneration;reportLabels();document.getElementById('reports-error').textContent='';document.getElementById('reports-status').textContent=reportText(chosen.length+' Unternehmen ausgewählt.',chosen.length+(chosen.length===1?' company selected.':' companies selected.'));
 const select=document.getElementById('reports-company');select.replaceChildren();for(const c of chosen){const o=document.createElement('option');o.value=c.id;o.textContent=c.name;select.append(o);}
 document.getElementById('reports-language').value=window.harveyLanguage?.()||'de';document.getElementById('reports-options').open=true;reportShow(null);
 const dialog=document.getElementById('company-reports-dialog');if(!dialog.open)dialog.showModal();await reportLoadHistory();
}
function reportShow(report){
 reportCurrent=report;const has=!!report;
 document.getElementById('reports-preview').hidden=!has;
 document.getElementById('reports-company').disabled=reportBusy;document.getElementById('reports-history').disabled=reportBusy||!document.getElementById('reports-history').value;
 document.getElementById('reports-ai').textContent=report?.ai&&report.ai.version!==2?reportText('KI-Analyse erweitern','Extend AI analysis'):reportText('KI-Erläuterung ergänzen','Add AI explanation');
 document.getElementById('reports-ai').disabled=!has||reportBusy||report?.ai?.version===2||!report?.findings.some(f=>f.section!=='unknown');
 if(has){const base='/api/company-reports/'+encodeURIComponent(report.id);document.getElementById('reports-frame').src=base+'/preview';document.getElementById('reports-markdown').href=base+'/markdown';document.getElementById('reports-print').href=base+'/preview?printing=true';}
 else document.getElementById('reports-frame').removeAttribute('src');
 document.getElementById('reports-create').disabled=reportBusy;
}
async function reportLoadHistory(preferred){
 const gen=++reportGeneration,cid=document.getElementById('reports-company').value;reportShow(null);
 try{const rows=await contactRequest('/api/company-reports/history?company_id='+encodeURIComponent(cid));if(gen!==reportGeneration)return;
 const select=document.getElementById('reports-history');select.replaceChildren();if(!rows.length){const option=document.createElement('option');option.textContent=reportText('Noch kein Bericht gespeichert','No saved report');option.value='';select.append(option);select.disabled=true;return;}
 select.disabled=reportBusy;for(const r of rows){const o=document.createElement('option');o.value=r.id;o.textContent=formatDate(r.created_at)+' · '+r.language.toUpperCase();select.append(o);}if(preferred)select.value=preferred;await reportRead(gen);
 }catch(e){if(gen===reportGeneration)document.getElementById('reports-error').textContent=reportErrors(e.message);}
}
async function reportRead(gen=++reportGeneration){
 const rid=document.getElementById('reports-history').value;if(!rid)return;try{const report=await contactRequest('/api/company-reports/'+encodeURIComponent(rid));if(gen===reportGeneration)reportShow(report);}catch(e){if(gen===reportGeneration)document.getElementById('reports-error').textContent=reportErrors(e.message);}
}
async function reportCreate(){
 if(reportBusy)return;reportBusy=true;reportShow(reportCurrent);const gen=reportGeneration;document.getElementById('reports-error').textContent='';document.getElementById('reports-status').textContent=reportText('Berichte werden erstellt …','Creating reports …');
 try{const result=await contactPost('/api/company-reports',{company_ids:reportCompanies.map(c=>c.id),categories:[...document.querySelectorAll('#reports-categories input:checked')].map(c=>c.value),language:document.getElementById('reports-language').value,max_age_days:Number(document.getElementById('reports-age').value)});if(gen!==reportGeneration)return;document.getElementById('reports-options').open=false;document.getElementById('reports-status').textContent=reportText(result.reports.length+(result.reports.length===1?' Bericht gespeichert.':' Berichte gespeichert.'),result.reports.length+(result.reports.length===1?' report saved.':' reports saved.'));const cid=document.getElementById('reports-company').value;await reportLoadHistory(result.reports.find(r=>r.company.id===cid)?.id);
 }catch(e){if(gen===reportGeneration){document.getElementById('reports-error').textContent=reportErrors(e.message);document.getElementById('reports-status').textContent='';}}finally{reportBusy=false;reportShow(reportCurrent);}
}
async function reportAI(){
 if(!reportCurrent||reportBusy)return;const rid=reportCurrent.id,gen=reportGeneration;reportBusy=true;reportShow(reportCurrent);document.getElementById('reports-error').textContent='';document.getElementById('reports-status').textContent=reportText('KI-Erläuterung wird erstellt …','Creating AI explanation …');
 try{const report=await contactPost('/api/company-reports/'+encodeURIComponent(rid)+'/explain',{});if(gen!==reportGeneration)return;reportShow(report);document.getElementById('reports-status').textContent=reportText('KI-Erläuterung gespeichert. Bitte vor externer Verwendung prüfen.','AI explanation saved. Review before external use.');}catch(e){if(gen===reportGeneration){document.getElementById('reports-error').textContent=reportErrors(e.message);document.getElementById('reports-status').textContent='';}}finally{reportBusy=false;reportShow(reportCurrent);}
}
document.getElementById('company-reports-dialog').addEventListener('close',()=>{++reportGeneration;reportReturnFocus?.focus?.();});
window.addEventListener('harvey-language-changed',reportLabels);reportLabels();
