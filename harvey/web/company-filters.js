// Filter controls are presentation only. Matching and facet counts live in SQLite.
let _companyFilterHydrating = false;
const COMPANY_FILTER_IDS = {q:'company-search',locations:'company-location',industries:'company-industry',
 email:'company-email-filter',website:'company-website-filter',phone:'company-phone-filter',
 people:'company-people-filter',profiles:'company-profiles-filter',source:'company-source-filter'};
const companyMulti = {};
let companyViews = [];
let companyViewApplying = false;

function companyFilterState() {
 const result = {};
 for (const [key,id] of Object.entries(COMPANY_FILTER_IDS)) {
  const el=document.getElementById(id);
  result[key]=el.multiple ? Array.from(el.selectedOptions,o=>o.value).filter(Boolean) : el.value.trim();
 }
 return result;
}
function applyCompanyFilterState(filters) {
 _companyFilterHydrating=true;
 try {
  for(const [key,id] of Object.entries(COMPANY_FILTER_IDS)) {
   const el=document.getElementById(id), value=filters[key] || (el.multiple?[]:'');
   if(el.multiple) {
    if(companyMulti[key]) {
     value.forEach(v=> {if(!companyMulti[key].options[v]) companyMulti[key].addOption({value:v,text:v});});
     companyMulti[key].setValue(value,true);
    } else { el.replaceChildren(...value.map(v=>new Option(v,v,true,true))); }
   } else {
    if(el.tagName==='SELECT' && value && !Array.from(el.options).some(o=>o.value===value)) el.add(new Option(value,value));
    el.value=value;
   }
  }
 } finally { _companyFilterHydrating=false; }
}
function companySourceLabel(value) {
 const labels={'discover:google_maps':'Google Maps','discover:osm':'OpenStreetMap','discover:geoapify':'Geoapify',
 'discover:serpapi':'SerpApi','manual':'Manual','discover:serper':'Serper',
 'discover:dataforseo_listings':'DataForSEO','discover:dataforseo_serp':'DataForSEO'};
 return tr(labels[value] || value);
}
function refreshCompanyFilterControls(data) {
 _companyFilterHydrating=true;
 try {
  const state=companyFilterState();
  for(const key of ['locations','industries']) {
   const el=document.getElementById(COMPANY_FILTER_IDS[key]);
   const rows=data.facets?.[key] || [];
   const counts=new Map(rows.map(row=>[row.value,row.count]));
   const values=[...new Set([...rows.map(r=>r.value),...state[key]])];
   const options=values.map(value=>({value,text:value+' ('+(counts.get(value)||0)+')'}));
   if(!companyMulti[key] && window.TomSelect) {
    companyMulti[key]=new TomSelect(el,{plugins:{remove_button:{title:tr('Remove filter')}},create:false,maxItems:50,hidePlaceholder:true,
      closeAfterSelect:false,placeholder:tr(key==='locations'?'All locations':'All industries'),
      render:{no_results:()=>'<div class="no-results">'+escHtml(tr('No matching options'))+'</div>'},
      });
   }
   if(companyMulti[key]) {
    const ts=companyMulti[key];
    const searchText=ts.control_input.value, focused=ts.isFocused;
    const signature=JSON.stringify(options);
    if(el.dataset.facets!==signature) {
     ts.clear(true);ts.clearOptions();ts.addOptions(options);ts.setValue(state[key],true);
     if(focused && searchText){ts.setTextboxValue(searchText);ts.refreshOptions(false);}
     el.dataset.facets=signature;
    }
    const placeholder=tr(key==='locations'?'All locations':'All industries');
    ts.settings.placeholder=placeholder;ts.control_input.placeholder=state[key].length?'':placeholder;
    ts.control.setAttribute('data-user-content','');ts.dropdown.setAttribute('data-user-content','');
    ts.control_input.setAttribute('aria-label',tr(key==='locations'?'Location':'Industry'));
    ts.control.querySelectorAll('.remove').forEach(button=>{button.setAttribute('title',tr('Remove filter'));button.setAttribute('aria-label',tr('Remove filter'));});
   } else { el.replaceChildren(...options.map(o=>new Option(o.text,o.value,false,state[key].includes(o.value)))); }
  }
  for(const key of ['email','website','phone','people','profiles']) {
   const el=document.getElementById(COMPANY_FILTER_IDS[key]);
   const labels=JSON.parse(el.dataset.labels);
   el.replaceChildren(...['','with','without'].map((value,index)=>new Option(tr(labels[index])+(value?' ('+(data.facets?.[key]?.[value]||0)+')':''),value,false,state[key]===value)));
  }
  const source=document.getElementById('company-source-filter');
  const rows=data.facets?.source || [];
  source.replaceChildren(new Option(tr('All sources'),''),...rows.map(row=>new Option(companySourceLabel(row.value)+' ('+row.count+')',row.value)));
  if(state.source && !rows.some(r=>r.value===state.source))source.add(new Option(companySourceLabel(state.source)+' (0)',state.source));
  source.value=state.source;
  renderCompanyFilterChips();
 } finally { _companyFilterHydrating=false; }
}
function renderCompanyFilterChips() {
 const state=companyFilterState(),chips=[];
 for(const [key,value] of Object.entries(state)) {
  for(const item of (Array.isArray(value)?value:value?[value]:[])) {
   const label=key==='locations'||key==='industries'||key==='q'?item:key==='source'?companySourceLabel(item):
     tr(JSON.parse(document.getElementById(COMPANY_FILTER_IDS[key]).dataset.labels)[item==='with'?1:2]);
   chips.push({key,value:item,label});
  }
 }
 const el=document.getElementById('company-active-filters');
 el.replaceChildren();el.hidden=!chips.length;
 chips.forEach(chip=>{
  const button=document.createElement('button');button.type='button';button.className='company-filter-chip';
  const text=document.createElement('span');text.dataset.userContent='';text.textContent=chip.label;
  button.append(text);button.insertAdjacentHTML('beforeend','<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 7 10 10M17 7 7 17"/></svg>');
  button.setAttribute('aria-label',tr('Remove filter')+': '+chip.label);
  button.disabled=!!_companyBulk?.running;
  button.onclick=()=>{
   const filters=companyFilterState();filters[chip.key]=Array.isArray(filters[chip.key])?filters[chip.key].filter(v=>v!==chip.value):'';
   applyCompanyFilterState(filters);changeCompanyFilters();
  };
  el.append(button);
 });
}
function companyFiltersChanged() {
 if(!companyViewApplying)document.getElementById('company-view-select').value='';
 renderCompanyFilterChips();
}
async function loadCompanyViews() {
 const rows=await api('/api/company-filter-views');
 if(!Array.isArray(rows))return;
 companyViews=rows;
 const el=document.getElementById('company-view-select'),selected=el.value;
 el.replaceChildren(new Option(tr('Choose saved view…'),''),...rows.map(row=>new Option(row.name,row.id)));
 el.value=rows.some(row=>row.id===selected)?selected:'';
 document.getElementById('company-view-delete').disabled=!el.value || !!_companyBulk?.running;
}
function chooseCompanyView() {
 if(_companyBulk?.running)return;
 const view=companyViews.find(row=>row.id===document.getElementById('company-view-select').value);
 document.getElementById('company-view-delete').disabled=!view;
 if(!view)return;
 companyViewApplying=true;
 try {applyCompanyFilterState(view.filters);changeCompanyFilters();}
 finally {companyViewApplying=false;}
}
async function saveCompanyView(event) {
 event.preventDefault();
 if(_companyBulk?.running)return;
 const name=document.getElementById('company-view-name'),button=document.getElementById('company-view-save');
 button.disabled=true;
 try {
  const response=await fetch('/api/company-filter-views',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name.value,filters:companyFilterState()})});
  const result=await response.json();
  if(!response.ok){showToast(tr(result.error || 'Could not save view.'),'error');return;}
  name.value='';await loadCompanyViews();document.getElementById('company-view-select').value=result.id;
  document.getElementById('company-view-delete').disabled=false;showToast(tr('View saved.'),'success');
 } catch {showToast(tr('Could not save view.'),'error');}
 finally {button.disabled=false;}
}
async function deleteCompanyView() {
 if(_companyBulk?.running)return;
 const el=document.getElementById('company-view-select');if(!el.value)return;
 const result=await api('/api/company-filter-views/'+encodeURIComponent(el.value),{method:'DELETE'});
 if(!result?.success){showToast(tr('Could not delete view.'),'error');return;}
 await loadCompanyViews();showToast(tr('View removed. Company data is unchanged.'),'success');
}
