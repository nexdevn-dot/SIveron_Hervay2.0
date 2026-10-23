let currentTab = 'today';
let companyDrill = false;      // true while viewing a single company's contacts
let _companyDetailIndex = null;
let _companies = [], _prospects = [], _campaigns = [];
let _companyPage = 1, _companyPageData = null, _companyRequest = 0, _companyFilterTimer;
const _companySelection = new Map(), _companyLookupStates = new Map();
let _companyBulk = null;
let _signals = null;           // last /api/signals payload, for the cohort builder
let _desk = { items: [], i: 0 };

// ── Appearance ──
//
// Three states, not two: "auto" follows the OS and is the default, so the
// dashboard matches the rest of your machine until you deliberately override
// it. Stored per-browser; nothing is sent anywhere.

const THEMES = ['auto', 'light', 'dark'];

function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === 'auto') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', mode);
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = mode;
}

function cycleTheme() {
  const now = localStorage.getItem('harvey-theme') || 'auto';
  const next = THEMES[(THEMES.indexOf(now) + 1) % THEMES.length];
  try { localStorage.setItem('harvey-theme', next); } catch { /* private mode */ }
  applyTheme(next);
}

(function initTheme() {
  let saved = 'auto';
  try { saved = localStorage.getItem('harvey-theme') || 'auto'; } catch { /* ignore */ }
  applyTheme(THEMES.includes(saved) ? saved : 'auto');
})();

// ── Utilities ──

function escHtml(s) {
  if (s === null || s === undefined || s === '') return '';
  return String(s).replace(/[&<>"']/g, ch => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]
  ));
}

// ── One status vocabulary ──
//
// Siveron's tables each carry their own words for state: a prospect is `new`,
// a campaign is `draft`, an email is `pending_review`, a signal is `proposed`.
// Five of those mean "waiting on you" and the old dashboard styled every one
// differently. Everything now resolves through this map, so a status reads the
// same way no matter which table it came out of.
//
// tone: waiting (needs a human) | active (in flight) | good | bad | idle
const STATUS = {
  // prospects
  new:            ['New', 'active'],
  company_contact: ['Firmenkontakt', 'idle'],
  contacted:      ['Contacted', 'active'],
  replied:        ['Replied', 'good'],
  interested:     ['Interested', 'good'],
  meeting:        ['Meeting booked', 'note'],
  not_interested: ['Not interested', 'bad'],
  bounced:        ['Bounced', 'bad'],
  // campaigns
  draft:          ['Draft', 'waiting'],
  active:         ['Active', 'good'],
  completed:      ['Completed', 'idle'],
  paused:         ['Paused', 'bad'],
  // conversations
  open:           ['Open', 'active'],
  closed:         ['Closed', 'idle'],
  closed_won:     ['Won', 'good'],
  closed_lost:    ['Lost', 'bad'],
  objection:      ['Objection', 'waiting'],
  // outbox
  pending_review: ['Waiting on you', 'waiting'],
  approved:       ['Approved', 'good'],
  scheduled:      ['Scheduled', 'active'],
  sent:           ['Sent', 'good'],
  failed:         ['Failed', 'bad'],
  rejected:       ['Rejected', 'idle'],
  cancelled:      ['Cancelled', 'idle'],
  // signals
  proposed:       ['Waiting on you', 'waiting'],
  confirmed:      ['Confirmed', 'good'],
  // email deliverability
  verified:       ['Verified', 'good'],
  risky:          ['Catch-all', 'waiting'],
  guess:          ['Unverified', 'idle'],
  invalid:        ['Invalid', 'bad'],
  // runs
  running:        ['Running', 'active'],
  stale:          ['Stale', 'bad'],
};

function statusMeta(status) {
  const key = String(status || '').toLowerCase().replace(/[^a-z0-9]+/g, '_');
  const hit = STATUS[key];
  if (hit) return { label: hit[0], tone: hit[1] };
  const label = String(status || 'unknown').replace(/_/g, ' ');
  return { label: label.charAt(0).toUpperCase() + label.slice(1), tone: 'idle' };
}

function badge(status) {
  const m = statusMeta(status);
  return '<span class="badge t-' + m.tone + '">' + escHtml(m.label) + '</span>';
}

function formatDate(d) {
  if (!d) return '';
  try {
    const dt = new Date(d);
    if (isNaN(dt)) return escHtml(d);
    const locale = window.harveyLanguage && window.harveyLanguage() === 'de' ? 'de-DE' : 'en-US';
    return dt.toLocaleString(locale, {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
  } catch { return escHtml(d); }
}

function emptyState(glyph, title, copy) {
  return '<div class="empty"><div class="glyph">' + glyph + '</div>' +
    '<div class="title">' + title + '</div>' +
    '<div class="copy">' + copy + '</div></div>';
}

function offlineState() {
  return emptyState('&#9888;', 'Dashboard can\'t reach the server',
    'The dashboard process may have stopped. Restart it with <b>harvey dashboard</b> and refresh this page.');
}

async function api(path, opts) {
  try {
    const r = await fetch(path, opts);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

function showToast(msg, type) {
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

function toggleVisibility(inputId) {
  const el = document.getElementById(inputId);
  el.type = el.type === 'password' ? 'text' : 'password';
}

// Responsive sidebar: keep hidden links out of the mobile tab order.
const sidebarMedia = window.matchMedia('(max-width: 900px)');
function setSidebarOpen(open, restoreFocus = true) {
  const sidebar = document.getElementById('app-sidebar');
  const modal = sidebarMedia.matches && open;
  sidebar.inert = sidebarMedia.matches && !open;
  sidebar.classList.toggle('is-open', modal);
  if (modal) sidebar.setAttribute('role', 'dialog');
  else sidebar.removeAttribute('role');
  sidebar.toggleAttribute('aria-modal', modal);
  if (modal) sidebar.setAttribute('aria-modal', 'true');
  document.getElementById('sidebar-toggle').setAttribute('aria-expanded', String(modal));
  document.querySelector('.sidebar-backdrop').hidden = !modal;
  document.querySelector('main').inert = modal;
  document.querySelector('.app-header').inert = modal;
  document.body.classList.toggle('sidebar-open', modal);
  if (modal) requestAnimationFrame(() => {
    if (sidebar.classList.contains('is-open')) sidebar.querySelector('.sidebar-close').focus();
  });
  else if (sidebarMedia.matches && restoreFocus) document.getElementById('sidebar-toggle').focus();
}
sidebarMedia.addEventListener('change', () => setSidebarOpen(false, false));
setSidebarOpen(false, false);
document.addEventListener('keydown', event => {
  const sidebar = document.getElementById('app-sidebar');
  if (!sidebar.classList.contains('is-open')) return;
  if (event.key === 'Escape') { event.preventDefault(); setSidebarOpen(false); }
  if (event.key === 'Tab') {
    const links = [...sidebar.querySelectorAll('button:not([disabled]),a[href]')];
    const first = links[0], last = links[links.length-1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});

// ── Tabs ──

function showTab(id, btn) {
  if (id !== 'discover' && document.getElementById('discovery-details')?.open) closeDiscoveryDetails();
  currentTab = id;
  if (id === 'companies') companyDrill = false;
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => {
    const active = b.dataset.tab === id;
    b.classList.toggle('active', active);
    if (active) b.setAttribute('aria-current', 'page');
    else b.removeAttribute('aria-current');
  });
  document.getElementById(id).classList.add('active');
  const mobileNav = document.getElementById('mobile-nav');
  if (mobileNav) mobileNav.value = id;
  const selected = document.querySelector('.sidebar-nav button.active .nav-label');
  if (selected) document.getElementById('workspace-title').textContent = selected.textContent;
  const wasOpen = document.getElementById('app-sidebar').classList.contains('is-open');
  setSidebarOpen(false, false);
  if (wasOpen) document.getElementById('workspace').focus({preventScroll:true});
  loadCurrentTab();
}

function loadCurrentTab() {
  switch (currentTab) {
    case 'today': loadToday(); loadSetupStatus(); loadRuns(); loadTodayActivity(); break;
    case 'signals': loadSignals(); break;
    case 'discover': loadDiscoverProviders(); break;
    case 'companies': if (!companyDrill) loadCompanies(); break;
    case 'prospects': loadProspects(); break;
    case 'campaigns': loadCampaigns(); break;
    case 'outbox': loadOutbox(); break;
    case 'conversations': loadConversations(); break;
    case 'activity': loadActivity(); break;
    case 'usage': loadUsage(); break;
    case 'settings': loadSettings(); break;
    case 'controls': loadHarveyStatus(); loadLogs(); break;
  }
}

// ── Today: what needs a human ──

async function loadToday() {
  if(typeof loadWorkItems==='function')loadWorkItems();
  const data = await api('/api/today');
  const el = document.getElementById('today-queue');
  if (!data) { el.innerHTML = offlineState(); return; }

  navCount('nav-today', (data.work_total||0)+(data.items || []).filter(i => i.tone !== 'good').length);
  navCount('nav-outbox', (data.stats || {}).outbox_pending || 0);
  renderFigures(data.stats || {});

  const items = data.items || [];
  if (!items.length && data.work_total) {el.replaceChildren();return;}
  if (!items.length) {
    el.innerHTML = '<div class="queue-clear">' +
      '<div class="glyph">&#10003;</div><div>' +
      '<div class="qtitle">Nothing needs you</div>' +
      '<div class="qdetail">Siveron has everything it needs. Anything that requires a ' +
      'decision — an email to approve, a signal to confirm — shows up here.</div>' +
      '</div></div>';
    return;
  }

  el.innerHTML = '<div class="queue">' + items.map(it =>
    '<div class="queue-item ' + escHtml(it.tone || 'warn') + '">' +
      '<div class="qtext">' +
        '<div class="qtitle">' + escHtml(it.title) + '</div>' +
        '<div class="qdetail">' + escHtml(it.detail) + '</div>' +
      '</div>' +
      '<button class="btn btn-secondary btn-sm" onclick="goTab(\'' + escHtml(it.tab) + '\')">' +
        escHtml(it.action) + '</button>' +
    '</div>'
  ).join('') + '</div>';
}

function renderFigures(stats) {
  const el = document.getElementById('today-figures');
  if (!el) return;
  const overview = document.getElementById('today-overview');
  if (overview) {
    const metric = (label, value, tab, icon) =>
      '<button class="deck-metric" type="button" onclick="goTab(\'' + tab + '\')">' +
        '<span class="deck-metric-top"><svg class="deck-metric-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + icon + '"></path></svg>' +
        '<span class="deck-metric-label">' + label + '</span><span class="deck-metric-arrow" aria-hidden="true">↗</span></span>' +
        '<span class="deck-metric-value">' + value + '</span></button>';
    overview.innerHTML = metric('Companies', stats.companies || 0, 'companies', 'M4 21V3h12v18M2 21h20M16 9h4v12M8 7h4M8 11h4M8 15h4') +
      metric('Contacts', stats.prospects || 0, 'prospects', 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-2a8 8 0 0 1 16 0v2') +
      metric('Signals on', stats.signals_confirmed || 0, 'signals', 'M4 17V9m5 8V5m5 12v-6m5 6V3');
  }
  const row = (label, value) =>
    '<div class="figure"><span class="k">' + label + '</span>' +
    '<span class="v' + (value ? '' : ' zero') + '">' + value + '</span></div>';

  el.innerHTML = '<div class="figures">' +
    row('Not yet read', stats.unprofiled || 0) +
    row('Awaiting approval', stats.outbox_pending || 0) +
    row('Scheduled', stats.outbox_approved || 0) +
    row('Live conversations', stats.open_conversations || 0) +
  '</div>';
}

async function loadTodayActivity() {
  const el = document.getElementById('today-activity');
  if (!el) return;
  const data = await api('/api/activity');
  if (!Array.isArray(data) || !data.length) {
    el.innerHTML = '<p class="muted" style="font-size:12.5px">' +
      'Nothing yet. Every action Siveron takes shows up here.</p>';
    return;
  }
  el.innerHTML = '<div class="activity-feed">' + data.slice(0, 12).map(a =>
    '<div class="activity-item">' +
      '<span class="time">' + formatDate(a.created_at) + '</span>' +
      '<span class="agent">' + escHtml(a.agent) + '</span>' +
      '<span class="action">' + escHtml(String(a.action_type).replace(/_/g, ' ')) + '</span>' +
    '</div>').join('') + '</div>';
}

function navCount(id, n) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = n > 0 ? n : '';
  el.className = 'nav-count' + (n > 0 ? ' on' : '');
}

// Jump to a tab from a link that isn't itself a nav button.
function goTab(id) {
  const btns = [...document.querySelectorAll('nav button')];
  const btn = btns.find(b => (b.getAttribute('onclick') || '').includes("'" + id + "'"));
  showTab(id, btn);
}

async function loadRuns() {
  const el = document.getElementById('today-runs');
  const block = document.getElementById('today-runs-block');
  if (!el) return;
  const runs = await api('/api/runs');
  if (!Array.isArray(runs) || !runs.length) {
    if (block) block.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  if (block) block.style.display = '';

  // A rail is 300px wide — a seven-column table does not belong here.
  el.innerHTML = '<div class="figures">' + runs.slice(0, 6).map(r =>
    '<div class="figure" style="align-items:flex-start">' +
      '<span class="k">' + escHtml(r.stage) +
        '<br><span class="muted" style="font-size:11px">' +
        formatDate(r.started_at) + '</span></span>' +
      '<span style="text-align:right;flex:none">' + badge(r.status) +
        '<br><span class="muted" style="font-family:var(--mono);font-size:11px">' +
        (r.records || 0) + ' rec &middot; ' +
        (r.cost_usd ? '$' + Number(r.cost_usd).toFixed(4) : 'free') + '</span></span>' +
    '</div>').join('') + '</div>';
}

// ── Setup checklist (lives on Today, and disappears once it's done) ──

async function loadSetupStatus() {
  const el = document.getElementById('today-setup');
  if (!el) return;
  const data = await api('/api/setup-status');
  if (!data || !data.checks) { el.innerHTML = ''; return; }

  const pct = data.percent || 0;
  // Finished setup disappears completely rather than greeting you forever.
  if (pct === 100) { el.innerHTML = ''; return; }

  const renderCheck = (c, optional) =>
    '<div class="check-item">' +
      (c.done ? '<span class="check-icon done">&#10003;</span>'
              : '<span class="check-icon pending"></span>') +
      '<div class="check-info">' +
        '<div class="check-label ' + (c.done ? 'done' : '') + '">' + escHtml(c.label) +
          (optional ? '<span class="optional-tag">optional</span>' : '') + '</div>' +
        (!c.done ? '<div class="check-help">' + escHtml(c.help) + '</div>' : '') +
      '</div></div>';

  const required = data.checks.filter(c => c.required);
  const optional = data.checks.filter(c => !c.required);
  const wasOpen = el.querySelector('.deck-setup')?.open || false;

  el.innerHTML =
    '<details class="rail-block deck-disclosure deck-setup"' + (wasOpen ? ' open' : '') + '>' +
      '<summary>Setup &mdash; ' + pct + '%</summary>' +
      '<div class="progress-bar" style="margin-bottom:14px">' +
        '<div class="progress-fill yellow" style="width:' + pct + '%"></div></div>' +
      required.map(c => renderCheck(c, false)).join('') +
      (optional.length
        ? '<details style="margin-top:10px"><summary class="muted" ' +
          'style="font-size:12px">' + optional.length + ' optional</summary>' +
          '<div style="margin-top:6px">' +
          optional.map(c => renderCheck(c, true)).join('') + '</div></details>'
        : '') +
    '</details>';
}

// ── Signals: Siveron proposes, you confirm ──

async function loadSignals() {
  const data = await api('/api/signals');
  const sumEl = document.getElementById('signals-summary');
  const grpEl = document.getElementById('signals-groups');
  if (!data || data.error) { grpEl.innerHTML = offlineState(); sumEl.innerHTML = ''; return; }
  _signals = data;

  const s = data.summary || {};
  navCount('nav-signals', s.proposed || 0);
  sumEl.innerHTML = '<div class="sig-summary">' +
    ['confirmed', 'proposed', 'rejected'].map(k =>
      '<div class="sig-stat ' + k + '"><div class="n">' + (s[k] || 0) + '</div>' +
      '<div class="k">' + (k === 'proposed' ? 'awaiting you' : k) + '</div></div>'
    ).join('') +
    '</div>';

  grpEl.innerHTML = (data.groups || []).map(g => {
    const codes = g.signals.map(x => x.code);
    const undecided = g.signals.filter(x => x.status === 'proposed').length;
    return '<div class="sig-group">' +
      '<div class="sig-group-head"><div>' +
        '<h3>' + escHtml(g.label) + '</h3><p>' + escHtml(g.blurb) + '</p>' +
      '</div>' +
      (undecided
        ? '<div style="display:flex;gap:6px;flex-shrink:0">' +
            '<button class="btn btn-primary btn-sm" onclick=\'setSignals(' +
              JSON.stringify(codes) + ", \"confirmed\")'>Confirm all " + undecided + '</button>' +
            '<button class="btn btn-secondary btn-sm" onclick=\'setSignals(' +
              JSON.stringify(codes) + ", \"rejected\")'>Skip all</button>" +
          '</div>'
        : '') +
      '</div>' +
      '<div class="card" style="padding:4px 0">' + g.signals.map(sigRow).join('') + '</div>' +
    '</div>';
  }).join('');

  renderCohortBuilder();
}

function sigRow(sig) {
  const free = /free|included/i.test(sig.cost_note || '');
  const costCls = free ? 'free' : (/\$/.test(sig.cost_note || '') ? 'paid' : '');
  const seen = sig.companies
    ? '<span class="cost-chip">seen on ' + sig.companies +
      (sig.companies === 1 ? ' company' : ' companies') + ' so far</span>' : '';
  const floor = sig.confidence_floor > 0
    ? '<span class="cost-chip">only recorded above ' +
      Math.round(sig.confidence_floor * 100) + '% confidence</span>' : '';

  const decided = sig.status === 'confirmed' || sig.status === 'rejected';
  const decide = decided
    ? '<button type="button" class="signal-switch" role="switch" aria-checked="' +
        (sig.status === 'confirmed') + '" aria-label="' + escHtml(sig.label || sig.code) +
        '" title="' + (sig.status === 'confirmed' ? 'Turn off' : 'Turn on') +
        '" data-signal-code="' + escHtml(sig.code) + '" onclick="toggleSignal(this)">' +
        '<span class="signal-switch-track" aria-hidden="true"><span class="signal-switch-thumb"></span></span></button>'
    : '<button class="btn btn-primary btn-sm" onclick="setSignals([\'' + sig.code +
          '\'],\'confirmed\')">Confirm</button>' +
        '<button class="btn btn-secondary btn-sm" onclick="setSignals([\'' + sig.code +
          '\'],\'rejected\')">Skip</button>';

  return '<div class="sig-row ' + (sig.status === 'rejected' ? 'rejected' : '') + '">' +
    '<div class="sig-main">' +
      '<div class="sig-label">' + escHtml(sig.label || sig.code) +
        '<span class="sig-code">' + escHtml(sig.code) + '</span></div>' +
      '<div class="sig-desc">' + escHtml(sig.description) + '</div>' +
      '<div class="sig-meta">' +
        '<span class="cost-chip ' + costCls + '">' + escHtml(sig.cost_note || 'cost unknown') + '</span>' +
        floor + seen + badge(sig.status) +
      '</div>' +
    '</div>' +
    '<div class="sig-decide">' + decide + '</div>' +
  '</div>';
}

async function toggleSignal(button) {
  if (button.disabled) return;
  const code = button.dataset.signalCode;
  const status = button.getAttribute('aria-checked') === 'true' ? 'rejected' : 'confirmed';
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  try {
    await setSignals([code], status);
  } finally {
    // Restore keyboard focus after loadSignals replaces the rows.
    const replacement = document.querySelector('.signal-switch[data-signal-code="' + CSS.escape(code) + '"]');
    if (button.isConnected) {
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }
    if (document.activeElement === document.body || document.activeElement === button) {
      replacement?.focus({preventScroll: true});
    }
  }
}

async function setSignals(codes, status) {
  const data = await api('/api/signals/status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({codes: codes, status: status}),
  });
  if (data && data.success) {
    showToast(
      status === 'confirmed'
        ? 'Confirmed ' + data.changed + ' signal' + (data.changed === 1 ? '' : 's') +
          ' — Siveron will collect ' + (data.changed === 1 ? 'it' : 'them') + ' from now on.'
        : data.changed + ' signal' + (data.changed === 1 ? '' : 's') + ' turned off.',
      'success');
  } else {
    showToast('Could not update that signal.', 'error');
  }
  await loadSignals();
}

// ── Discover: pick a source, price it, then run it ──

let _provider = null;
let _discoverPoll = null;
let _discoverInitialized = false;
let _discoveryProviders = [];
let _osmTerms = [];
let _termSuggestions = [];
let _activeTermSuggestion = -1;
let _discoveryEstimate = null;
let _discoveryTimer = null;
let _discoveryRevision = 0;
let _discoveryRunning = false;
const tr = (text) => window.translateHarveyText ? window.translateHarveyText(text) : text;
const discoveryCount = (count, singular, plural) => tr(count + ' ' + (count === 1 ? singular : plural));
const normalizeDiscoveryTerm = text => text.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();

let _termTagify = null;
let _tagifySyncing = false;
let _termCatalog = [];
let _locationAutocomplete = null;
let _discoveryLocations = [];
let _progressTimer = null;
let _progressRequest = 0;
let _discoveryHelpInitialized = false;
let _discoveryHelpPinned = false;

function showDiscoveryTermHelp(visible) {
  document.getElementById('disc-terms-help').hidden = !visible;
  document.getElementById('disc-terms-help-toggle').setAttribute('aria-expanded', String(visible));
}

function toggleDiscoveryTermHelp() {
  _discoveryHelpPinned = !_discoveryHelpPinned;
  showDiscoveryTermHelp(_discoveryHelpPinned);
}

function initDiscoveryTermHelp() {
  if (_discoveryHelpInitialized) return;
  _discoveryHelpInitialized = true;
  const picker = document.getElementById('disc-quick-terms');
  picker.addEventListener('pointerenter', event => {
    if (event.pointerType === 'mouse') showDiscoveryTermHelp(true);
  });
  picker.addEventListener('pointerleave', () => {
    if (!_discoveryHelpPinned && !picker.matches(':focus-within')) showDiscoveryTermHelp(false);
  });
  picker.addEventListener('focusin', () => showDiscoveryTermHelp(true));
  picker.addEventListener('focusout', event => {
    if (!picker.contains(event.relatedTarget)) {
      _discoveryHelpPinned = false;
      showDiscoveryTermHelp(false);
    }
  });
  picker.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      _discoveryHelpPinned = false;
      showDiscoveryTermHelp(false);
    }
  });
  document.addEventListener('pointerdown', event => {
    if (!picker.contains(event.target)) {
      _discoveryHelpPinned = false;
      showDiscoveryTermHelp(false);
    }
  });
}

function initDiscoveryInputs() {
  initDiscoveryTermHelp();
  if (!_termTagify && window.Tagify) {
    const input = document.getElementById('disc-term-entry');
    input.removeAttribute('role'); input.removeAttribute('aria-controls');
    _termTagify = new Tagify(input, {
      whitelist: [], enforceWhitelist: false, duplicates: false, delimiters: '[,;\\n]',
      editTags: 2, addTagOnBlur: false, a11y: {focusableTags: true, inputAriaLabel: tr('What businesses are you looking for?')},
      dropdown: {enabled: 0, maxItems: 8, closeOnSelect: true, searchKeys: ['value', 'searchBy'],
                 escapeHTML: true},
      templates: {dropdownItem(item) {
        return '<div ' + this.getAttributes(item) + ' class="tagify__dropdown__item" tabindex="0" role="option">' +
          escHtml(item.value) + (item.supported === false ? '<small>' + escHtml(tr('Not supported by this source')) + '</small>' : '') + '</div>';
      }},
    });
    input.hidden = true; input.setAttribute('aria-hidden', 'true'); input.tabIndex = -1;
    _termTagify.DOM.input.setAttribute('aria-describedby', 'disc-terms-help');
    _termTagify.on('change', () => {
      if (_tagifySyncing) return;
      document.getElementById('disc-terms').value = _termTagify.value.map(tag => tag.value).join('\n');
      invalidateDiscoveryEstimate();
    });
    _termTagify.on('input', event => {
      if (event.detail.value.trim()) {
        clearTimeout(_discoveryTimer); _discoveryRevision++; _discoveryEstimate = null;
        const button = document.getElementById('disc-run');
        button.disabled = true; button.textContent = tr('Add your term to preview');
      } else invalidateDiscoveryEstimate();
    });
    document.getElementById('disc-selected-terms').hidden = true;
    document.getElementById('disc-term-add').hidden = true;
  }
  if (!_locationAutocomplete && window.autocomplete?.GeocoderAutocomplete) {
    const container = document.getElementById('disc-location-autocomplete');
    _locationAutocomplete = new autocomplete.GeocoderAutocomplete(container, '', {
      type: 'city', lang: window.harveyLanguage?.() || 'de', limit: 5, debounceDelay: 450,
      addDetails: false, skipIcons: true, addCategorySearch: false,
      placeholder: tr('e.g. Rietberg'), skipSelectionOnArrowKey: true,
    });
    const input = container.querySelector('input');
    input.id = 'disc-location-entry'; input.classList.add('form-input');
    input.setAttribute('aria-label', tr('Where?'));
    input.setAttribute('aria-describedby', 'disc-location-help disc-location-status');
    document.querySelector('label[for="disc-cities"]').htmlFor = input.id;
    _locationAutocomplete.setSendGeocoderRequestFunc(async value => {
      if (value.trim().length < 3 || _discoveryRunning) return {type: 'FeatureCollection', features: []};
      const response = await api('/api/discover/locations?' + new URLSearchParams({q: value, lang: window.harveyLanguage?.() || 'de'}));
      const message = !response ? 'Location suggestions unavailable. You can still type a location.' :
        response.reason === 'quota' ? 'Location suggestion quota exhausted. You can still type a location.' :
        response.reason ? 'Location suggestions unavailable. You can still type a location.' :
        !response.available ? 'Type a location manually. Suggestions require a configured Geoapify key.' : '';
      document.getElementById('disc-location-status').textContent = tr(message);
      return response || {type: 'FeatureCollection', features: []};
    });
    _locationAutocomplete.on('select', feature => {
      if (!feature) return;
      const props = feature.properties;
      addDiscoveryLocation(props.formatted || props.city, props.lat, props.lon);
    });
    input.addEventListener('input', invalidateDiscoveryEstimate);
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.isComposing && _locationAutocomplete.getValue().trim()) {
        event.preventDefault(); addDiscoveryLocation(_locationAutocomplete.getValue().trim());
      }
    });
  }
}

function addDiscoveryLocation(name, lat, lon) {
  if (!name || _discoveryRunning) return;
  if (!_discoveryLocations.some(location => location.name.toLocaleLowerCase() === name.toLocaleLowerCase())) {
    _discoveryLocations.push({name, ...(Number.isFinite(lat) && Number.isFinite(lon) ? {lat, lon} : {})});
  }
  _locationAutocomplete?.setValue('');
  renderDiscoveryLocations(); invalidateDiscoveryEstimate();
}

function removeDiscoveryLocation(index) {
  if (_discoveryRunning) return;
  _discoveryLocations.splice(index, 1); renderDiscoveryLocations(); invalidateDiscoveryEstimate();
}

function renderDiscoveryLocations() {
  document.getElementById('disc-cities').value = _discoveryLocations.map(location => location.name).join('\n');
  document.getElementById('disc-location-chips').innerHTML = _discoveryLocations.map((location, index) =>
    '<span class="discovery-token"><span>' + escHtml(location.name) + '</span><button class="term-remove" type="button" onclick="removeDiscoveryLocation(' + index + ')" aria-label="' +
    escHtml(tr('Remove location') + ': ' + location.name) + '"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></button></span>').join('');
}

function syncDiscoveryTagify() {
  if (!_termTagify) return;
  _termTagify.whitelist = _termCatalog;
  const terms = selectedDiscoveryTerms();
  if (JSON.stringify(terms) !== JSON.stringify(_termTagify.value.map(tag => tag.value))) {
    _tagifySyncing = true;
    _termTagify.removeAllTags(); _termTagify.addTags(terms, true, true);
    _tagifySyncing = false;
  }
  _termTagify.getTagElms().forEach((element, index) => {
    const value = _termTagify.value[index]?.value;
    const unsupported = _termCatalog.find(item => item.value === value)?.supported === false ||
      !!_discoveryEstimate?.unsupported?.some(item => item.term === value);
    element.classList.toggle('discovery-unsupported', unsupported);
    element.title = unsupported ? tr('Not supported by this source') : value;
    element.querySelector('[role="button"]')?.setAttribute('aria-label', tr('Remove term') + ': ' + value);
  });
  _termTagify.setReadonly(_discoveryRunning);
}

function selectedDiscoveryTerms() {
  return document.getElementById('disc-terms').value.split(/[;\n]/).map(t => t.trim()).filter(Boolean);
}

function setDiscoveryTerms(terms) {
  if (_discoveryRunning) return;
  const seen = new Set();
  document.getElementById('disc-terms').value = terms.filter(term => {
    const key = normalizeDiscoveryTerm(term);
    if (!key || seen.has(key)) return false;
    seen.add(key); return true;
  }).join('\n');
  renderDiscoveryTerms();
  invalidateDiscoveryEstimate();
}

function renderDiscoveryTerms() {
  syncDiscoveryTagify();
  renderDiscoveryTermOptions();
  if (_termTagify) return;
  const issues = new Set((_discoveryEstimate?.unsupported || []).map(item => item.term));
  const terms = selectedDiscoveryTerms();
  document.getElementById('disc-selected-terms').innerHTML = terms.map((term, index) =>
    '<div class="discovery-token' + (issues.has(term) ? ' issue' : '') + '">' +
    '<span>' + escHtml(term) + '</span><button type="button" class="term-remove" onclick="removeDiscoveryTerm(' + index + ')" aria-label="' +
    escHtml(tr('Remove term') + ': ' + term) + '"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></button></div>').join('');
}

function removeDiscoveryTerm(index) {
  setDiscoveryTerms(selectedDiscoveryTerms().filter((_, i) => i !== index));
}

function renderDiscoveryTermOptions() {
  const select = document.getElementById('disc-term-select');
  const selected = new Set(selectedDiscoveryTerms().map(normalizeDiscoveryTerm));
  const available = _termCatalog.filter(item => !selected.has(normalizeDiscoveryTerm(item.value)));
  const options = items => items.map(item => '<option value="' + escHtml(item.value) + '"' +
    (item.supported === false ? ' disabled' : '') + '>' + escHtml(item.value) + '</option>').join('');
  const unsupported = available.filter(item => item.supported === false);
  select.innerHTML = '<option value="">' + escHtml(tr('Choose a suggestion…')) + '</option>' +
    options(available.filter(item => item.supported !== false)) +
    (unsupported.length ? '<optgroup label="' + escHtml(tr('Not supported by this source')) + '">' + options(unsupported) + '</optgroup>' : '');
  select.disabled = _discoveryRunning;
}

function chooseDiscoveryPreset(select) {
  const value = select.value;
  if (!value || _discoveryRunning) return;
  if (!_termCatalog.some(item => item.value === value && item.supported !== false)) return;
  setDiscoveryTerms([...selectedDiscoveryTerms(), value]);
  select.value = '';
}

function renderDiscoverySuggestions() {
  const input = document.getElementById('disc-term-entry');
  const query = normalizeDiscoveryTerm(input.value);
  const selected = new Set(selectedDiscoveryTerms().map(normalizeDiscoveryTerm));
  _termSuggestions = ['osm', 'geoapify'].includes(_provider) && query ? _osmTerms.filter(term =>
    normalizeDiscoveryTerm(term).includes(query) && !selected.has(normalizeDiscoveryTerm(term))).slice(0, 8) : [];
  _activeTermSuggestion = -1;
  input.removeAttribute('aria-activedescendant');
  const list = document.getElementById('disc-suggestions');
  list.hidden = !_termSuggestions.length;
  input.setAttribute('aria-expanded', String(!list.hidden));
  list.innerHTML = _termSuggestions.map((term, index) =>
    '<button id="disc-suggestion-' + index + '" type="button" role="option" aria-selected="false" tabindex="-1" onclick="chooseDiscoverySuggestion(' + index + ')">' +
    escHtml(term) + '<span>' + escHtml(tr('Select')) + '</span></button>').join('');
}

function closeDiscoverySuggestions() {
  document.getElementById('disc-suggestions').hidden = true;
  const input = document.getElementById('disc-term-entry');
  input.setAttribute('aria-expanded', 'false');
  input.removeAttribute('aria-activedescendant');
  _activeTermSuggestion = -1;
}

function chooseDiscoverySuggestion(index) { addDiscoveryTerm(_termSuggestions[index]); }
function addDiscoveryTerm(value) {
  if (_discoveryRunning) return;
  const entry = document.getElementById('disc-term-entry');
  const raw = typeof value === 'string' ? value : (_termTagify?.state.inputText || entry.value);
  const terms = raw.split(/[;\n,]/).map(term => term.trim()).filter(Boolean);
  if (!terms.length) { entry.focus(); return; }
  if (_termTagify) _termTagify.DOM.input.textContent = '';
  else entry.value = '';
  closeDiscoverySuggestions();
  setDiscoveryTerms([...selectedDiscoveryTerms(), ...terms]);
  entry.focus();
}

async function loadDiscoverProviders() {
  const el = document.getElementById('discover-providers');
  const data = await api('/api/discover/providers');
  if (!data || !data.providers?.length) { el.innerHTML = offlineState(); return; }
  initDiscoveryInputs();
  _discoveryProviders = data.providers;
  _provider = _provider || data.selected || data.default;
  document.getElementById('disc-location-attribution').innerHTML = data.location_autocomplete && _provider !== 'geoapify' ? discoveryAttribution() : '';
  _osmTerms = data.supported_terms?.[_provider] || data.suggested_terms || [];
  _termCatalog = data.term_catalog?.[_provider] || _osmTerms.map(value => ({value, supported: true}));
  const firstLoad = !_discoverInitialized;
  if (firstLoad) {
    document.getElementById('disc-terms').value = (data.default_terms || []).join('\n');
    _discoverInitialized = true;
  }
  document.getElementById('disc-location-help').innerHTML = '<span>Leave empty to use your target regions</span>: ' + escHtml((data.default_locations || []).join(', '));
  const selectedProvider = data.providers.find(p => p.key === _provider);
  el.innerHTML = '<div class="discovery-source"><div><label class="form-label" for="disc-provider">' + escHtml(tr('Source')) + '</label>' +
    '<select class="form-input" id="disc-provider" onchange="pickProvider(this.value)">' + data.providers.map(p =>
    '<option value="' + escHtml(p.key) + '"' + (p.key === _provider ? ' selected' : '') + '>' + escHtml(p.label) +
    (p.configured ? '' : ' — ' + escHtml(tr('needs a key'))) + '</option>').join('') + '</select></div>' +
    '<p class="muted">' + escHtml(tr(_provider === 'google_maps' ? 'Local browser search. No separate service or API key.' : _provider === 'osm' ? 'Free map data. No API key needed.' :
      ['geoapify', 'serpapi'].includes(_provider) ? 'Free-tier mode with a local usage limit.' : 'Review costs before starting.')) + '</p></div>' +
    '<details class="discovery-source-details"><summary>' + escHtml(tr('About this source')) + '</summary>' +
    '<p>' + escHtml(selectedProvider?.blurb || '') + '</p><p>' + escHtml(selectedProvider?.cost_note || '') + '</p>' +
    '<p>' + escHtml(selectedProvider?.caveat || '') + '</p>' +
    (selectedProvider?.needs_key ? '<p>' + escHtml(tr('Setup')) + ': ' + escHtml(selectedProvider.env_keys.join(', ')) +
      ' · <a href="' + escHtml(selectedProvider.signup_url) + '" target="_blank" rel="noopener">' + escHtml(tr('get a key')) + '</a></p>' : '') + '</details>' +
    (selectedProvider && !selectedProvider.configured && ['geoapify', 'serpapi'].includes(_provider)
      ? '<button class="btn btn-secondary btn-sm" onclick="openDiscoverySettings()">' + escHtml(tr('Configure source')) + '</button>' : '') +
    (_provider === 'geoapify' ? discoveryAttribution() : '');
  document.getElementById('discover-guidance').innerHTML = '<p>' + escHtml(tr('SME discovery note')) + '</p><p>' + escHtml(tr('Company size verification note')) + '</p>';
  _discoveryRunning = !!data.running;
  _termTagify?.setReadonly(_discoveryRunning);
  document.querySelectorAll('#disc-location-autocomplete input, #disc-radius, .discovery-advanced input, #disc-provider, #disc-term-add').forEach(input => { input.disabled = _discoveryRunning; });
  document.getElementById('disc-maps-options').hidden = _provider !== 'google_maps';
  document.querySelectorAll('#disc-maps-options input, #disc-maps-options select, #disc-email-search, #disc-email-mode, #disc-target-profile').forEach(input => { input.disabled = _discoveryRunning; });
  document.getElementById('disc-preview-refresh').hidden = true;
  document.querySelector('.discovery-radius').hidden = selectedProvider?.kind !== 'listings';
  document.getElementById('disc-stop').style.display = data.running ? '' : 'none';
  document.getElementById('disc-stop').disabled = !!(data.running && data.paused);
  document.getElementById('disc-stop').textContent = tr(data.running && data.paused ? 'Stopping…' : 'Stop');
  renderDiscoveryTerms();
  document.querySelectorAll('#disc-location-chips button').forEach(button => { button.disabled = _discoveryRunning; });
  document.getElementById('discover-estimate').hidden = _discoveryRunning;
  if (data.running && !_discoverPoll) {
    _discoverPoll = setInterval(loadDiscoverProviders, 4000);
    document.getElementById('disc-run').disabled = true;
    document.getElementById('disc-run').textContent = tr('Running…');
  } else if (!data.running && _discoverPoll) {
    clearInterval(_discoverPoll); _discoverPoll = null;
    invalidateDiscoveryEstimate();
    showToast('Discovery finished.', 'success');
  }
  renderDiscoverResult(data.last_report, data.running);
  if (data.running) pollDiscoveryProgress();
  else { clearTimeout(_progressTimer); pollDiscoveryProgress(false); }
  if (firstLoad && !data.running) invalidateDiscoveryEstimate();
}

function pickProvider(key) {
  _provider = key;
  closeDiscoverySuggestions();
  invalidateDiscoveryEstimate();
  loadDiscoverProviders();
}

function discoveryAttribution() {
  return '<p class="muted discovery-attribution"><a href="https://www.geoapify.com/" target="_blank" rel="noopener">Powered by Geoapify</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors (ODbL)</a></p>';
}

function openDiscoverySettings() {
  showTab('settings', null);
  document.getElementById('discovery-settings').scrollIntoView({block: 'start'});
}

function discoveryQuotaHtml(quota) {
  if (!quota) return '';
  return '<div class="discovery-quota"><strong>' + escHtml(tr('Local free quota')) + '</strong><p>' +
    quota.remaining + ' / ' + quota.limit + ' · ' + escHtml(tr(quota.period === 'day' ? 'per UTC day' : 'per UTC month')) +
    ' · ' + quota.required + ' ' + escHtml(tr('planned units')) + '</p><small>' +
    escHtml(tr('Counts Siveron reservations, including failed requests. Usage in other apps is not included.')) + '</small>' +
    (!quota.can_run ? '<p class="test-result pending">' + escHtml(tr('Free quota exhausted. No paid search was started.')) + '</p>' : '') + '</div>';
}

function discoverBody() {
  const raw = document.getElementById('disc-cities').value.trim();
  const draft = _locationAutocomplete?.getValue().trim() || '';
  const cities = [...new Set([...(raw ? raw.split(/[;\n]/).map(c => c.trim()).filter(Boolean) : []), ...(draft ? [draft] : [])])];
  return {
    provider: _provider,
    email_search: document.getElementById('disc-email-search').checked,
    email_mode: document.getElementById('disc-email-mode').value,
    target_profile_id:document.getElementById('disc-target-profile').value,
    maps_mode: document.getElementById('disc-maps-mode').value,
    maps_filter: document.getElementById('disc-maps-filter').value,
    maps_resume: document.getElementById('disc-maps-resume').checked,
    cities,
    locations: _discoveryLocations.filter(location => Number.isFinite(location.lat) && Number.isFinite(location.lon)),
    radius_km: Number(document.getElementById('disc-radius').value),
    terms: selectedDiscoveryTerms(),
    depth: Number(document.getElementById('disc-depth').value) || 30,
    limit: Number(document.getElementById('disc-limit').value) || 100,
    max_spend: Number(document.getElementById('disc-cap').value),
  };
}

function discoveryIssues() {
  const seen = new Set();
  return (_discoveryEstimate?.unsupported || []).filter(item => {
    if (seen.has(item.term)) return false;
    seen.add(item.term); return item.term;
  });
}

function replaceUnsupportedDiscoveryTerm(issueIndex, suggestionIndex) {
  const issue = discoveryIssues()[issueIndex];
  if (!issue) return;
  setDiscoveryTerms(selectedDiscoveryTerms().map(term => term === issue.term ? issue.suggestions[suggestionIndex] : term));
}

function useSupportedDiscoveryTerms() {
  const issues = new Set(discoveryIssues().map(item => item.term));
  setDiscoveryTerms(selectedDiscoveryTerms().filter(term => !issues.has(term)));
}

async function estimateDiscovery() {
  clearTimeout(_discoveryTimer);
  if (!_provider || _discoveryRunning) return;
  const entry = document.getElementById('disc-term-entry');
  if ((_termTagify ? _termTagify.state.inputText : entry.value)?.trim()) { addDiscoveryTerm(); return; }
  const revision = _discoveryRevision;
  const body = discoverBody();
  const el = document.getElementById('discover-estimate');
  const btn = document.getElementById('disc-run');
  btn.disabled = true;
  el.hidden = false;
  if (_provider === 'google_maps' && !body.cities.length && !body.locations.length) {
    el.innerHTML = '<p class="test-result pending">' + escHtml(tr('Google Maps requires a specific location.')) + '</p>';
    btn.textContent = tr('Refresh preview');
    return;
  }
  btn.textContent = tr('Preparing preview…');
  const data = await api('/api/discover/estimate', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
  });
  if (revision !== _discoveryRevision) return;
  if (!data || data.error) {
    el.innerHTML = '<p class="test-result error">' + escHtml(tr(data?.error || 'Could not load the preview. Please try again.')) + '</p>';
    btn.textContent = tr('Refresh preview');
    document.getElementById('disc-preview-refresh').hidden = false;
    return;
  }
  _discoveryEstimate = data;
  document.getElementById('discovery-search-summary').textContent = discoveryCount(body.terms.length, 'business type', 'business types') + ' · ' +
    discoveryCount((body.cities.length || data.query_details?.length / Math.max(1, body.terms.length) || 0), 'location', 'locations') + ' · ' + discoveryCount(data.query_count, 'search query', 'search queries');
  renderDiscoveryTerms();
  const over = data.estimated_cost > body.max_spend;
  const provider = _discoveryProviders.find(p => p.key === _provider);
  const issues = discoveryIssues();
  const supported = (data.query_details || []).filter(q => q.status !== 'unsupported');
  const recovery = issues.length ? '<div class="discovery-recovery"><p>' + escHtml(tr(_provider === 'geoapify'
    ? 'These categories are not supported by Geoapify in Siveron. Replace them or choose another source.'
    : 'These terms are not supported by this source. Choose a supported category or a web search source.')) + '</p>' +
    issues.map((issue, i) => '<div class="discovery-issue"><strong>' + escHtml(issue.term) + '</strong><div class="discovery-replacements">' +
      (issue.suggestions || []).map((term, j) => '<button type="button" class="discovery-term-pick" onclick="replaceUnsupportedDiscoveryTerm(' + i + ',' + j + ')">' + escHtml(term) + '</button>').join('') +
      '<button type="button" class="discovery-text-action" onclick="removeDiscoveryTerm(' + body.terms.indexOf(issue.term) + ')">' + escHtml(tr('Remove term')) + '</button></div></div>').join('') +
    (supported.length ? '<button type="button" class="btn btn-secondary" onclick="useSupportedDiscoveryTerms()">' + escHtml(tr('Keep supported terms only')) + '</button>' :
    '<p class="muted">' + escHtml(tr('Choose one of the suggested categories above to continue.')) + '</p>') +
    (_provider === 'geoapify' ? '<button type="button" class="btn btn-secondary btn-sm" onclick="pickProvider(\'osm\')">' + escHtml(tr('Switch to OpenStreetMap')) + '</button>' : '') + '</div>' : '';
  const queryLines = (data.query_details || []).map(q => '<li' + (q.status === 'unsupported' ? ' class="muted"' : '') + '>' + escHtml(q.keyword) +
    (q.status === 'unsupported' ? ' <span class="badge t-waiting">' + escHtml(tr('Needs a category')) + '</span>' : '') + '</li>').join('');
  const empty = !body.terms.length;
  el.innerHTML = '<div class="discovery-preview-head"><strong>' + escHtml(tr(empty ? 'Choose your first business type' : 'Search preview')) + '</strong>' +
    '<span>' + escHtml(data.quota ? tr('Free-tier mode') : data.free ? tr('Free') : '$' + data.estimated_cost.toFixed(4)) + '</span></div>' +
    (empty ? '<p class="muted">' + escHtml(tr('Click a suggested category above or type your own search term.')) + '</p>' :
    '<p class="muted">' + escHtml(tr(provider?.label || data.provider)) + ' · ' + data.query_count + ' ' + escHtml(tr('Search queries')) + '</p><ul class="discovery-query-list">' + queryLines + '</ul>') +
    (_provider === 'google_maps' ? '<p>' + data.max_results + ' · ' + escHtml(tr('Maximum listings before filters and deduplication')) + '</p>' : '') + recovery + (data.warnings || []).filter(w => w.message).map(w => '<p class="discovery-start-note muted">' + escHtml(tr(w.message)) + '</p>').join('') +
    discoveryQuotaHtml(data.quota) + (over ? '<p class="test-result error">' + escHtml(tr('Over your cap. Raise the cap or narrow the search.')) + '</p>' : '') +
    (provider && !provider.configured ? '<p class="test-result pending">' + escHtml(tr('Set up this source in Settings, or choose OpenStreetMap.')) + '</p>' : '') +
    '<p class="discovery-start-note muted">' + escHtml(tr('Nothing is searched until you press Start search.')) + '</p>';
  btn.disabled = !data.can_run || over || !provider?.configured;
  btn.textContent = tr(data.quota && !data.quota.can_run ? 'Free quota exhausted' : !body.terms.length ? 'Choose a business type' : issues.length ? 'Choose or replace a category' : 'Start search');
}

function invalidateDiscoveryEstimate() {
  if (_discoveryRunning) {
    document.getElementById('disc-run').disabled = true;
    document.getElementById('disc-run').textContent = tr('Running…');
    return;
  }
  _discoveryRevision++;
  _discoveryEstimate = null;
  clearTimeout(_discoveryTimer);
  const btn = document.getElementById('disc-run');
  btn.disabled = true;
  btn.textContent = tr('Preparing preview…');
  const el = document.getElementById('discover-estimate');
  el.innerHTML = '<p class="muted">' + escHtml(tr('Updating search preview…')) + '</p>';
  renderDiscoveryTerms();
  if (_provider && !_discoveryRunning) _discoveryTimer = setTimeout(estimateDiscovery, 350);
}

document.addEventListener('DOMContentLoaded', () => {
  initDiscoveryInputs();
  ['disc-cities', 'disc-terms', 'disc-limit', 'disc-depth', 'disc-cap'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', invalidateDiscoveryEstimate);
  });
  const entry = document.getElementById('disc-term-entry');
  entry.addEventListener('input', () => {
    if (_termTagify) return;
    renderDiscoverySuggestions();
    // A typed draft cannot silently be omitted from an already-ready search.
    if (entry.value.trim()) {
      _discoveryRevision++;
      _discoveryEstimate = null;
      clearTimeout(_discoveryTimer);
      const btn = document.getElementById('disc-run');
      btn.disabled = true; btn.textContent = tr('Add your term to preview');
    } else invalidateDiscoveryEstimate();
  });
  entry.addEventListener('keydown', event => {
    if (_termTagify) return;
    if (event.key === 'Escape') { closeDiscoverySuggestions(); return; }
    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && _termSuggestions.length) {
      event.preventDefault();
      if (document.getElementById('disc-suggestions').hidden) renderDiscoverySuggestions();
      _activeTermSuggestion = _activeTermSuggestion < 0
        ? (event.key === 'ArrowDown' ? 0 : _termSuggestions.length - 1)
        : (_activeTermSuggestion + (event.key === 'ArrowDown' ? 1 : -1) + _termSuggestions.length) % _termSuggestions.length;
      document.querySelectorAll('#disc-suggestions [role="option"]').forEach((option, index) => {
        option.setAttribute('aria-selected', String(index === _activeTermSuggestion));
      });
      const optionId = 'disc-suggestion-' + _activeTermSuggestion;
      entry.setAttribute('aria-activedescendant', optionId);
      document.getElementById(optionId).scrollIntoView({block: 'nearest'});
    } else if (event.key === 'Enter' && !event.isComposing) {
      event.preventDefault();
      _activeTermSuggestion >= 0 ? chooseDiscoverySuggestion(_activeTermSuggestion) : addDiscoveryTerm();
    }
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.discovery-business-field')) closeDiscoverySuggestions();
  });
  window.addEventListener('harvey-language-changed', () => {
    if (_discoverInitialized) {
      renderDiscoveryTerms();
      loadDiscoverProviders();
      _termTagify?.DOM.input.setAttribute('aria-label', tr('What businesses are you looking for?'));
      _locationAutocomplete?.setLang(window.harveyLanguage?.() || 'de');
      if (!(_termTagify ? _termTagify.state.inputText : entry.value)?.trim()) invalidateDiscoveryEstimate();
      else document.getElementById('disc-run').textContent = tr('Add your term to preview');
    }
    if (currentTab === 'companies') {
      companyDrill && _companyDetailIndex !== null ? showCompanyContacts(_companyDetailIndex) : loadCompanies();
    }
  });
});

async function runDiscovery() {
  // Recheck the exact previewed request; server-side validation remains authoritative.
  if (!_discoveryEstimate?.can_run || _discoveryRunning) return;
  const btn = document.getElementById('disc-run');
  btn.disabled = true; btn.textContent = tr('Running…');
  try {
    const response = await fetch('/api/discover/run', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(discoverBody()),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      showToast(data.message || tr('Could not start.'), 'error');
      invalidateDiscoveryEstimate(); return;
    }
    _discoveryRunning = true;
    pollDiscoveryProgress();
    showToast('Discovery started — ' + data.queries + ' queries.', 'success');
    await loadDiscoverProviders();
    document.getElementById('discover-progress').scrollIntoView({block: 'nearest'});
  } catch {
    showToast(tr('Could not start.'), 'error');
    invalidateDiscoveryEstimate();
  }
}

async function stopDiscovery() {
  const data = await api('/api/discover/stop', {method: 'POST'});
  showToast(data && data.success ? 'Stopping after the current query.'
                                 : 'Could not stop.', data ? 'success' : 'error');
  loadDiscoverProviders();
}

let _progressInFlight = false;
let _restoredDiscoveryRun = null;
let _discoveryProgressView = null;
let _discoverySeenRunning = null;
let _discoveryDismissed = null;
let _discoveryHistoryOpen = false;
let _discoveryDetailFocus = null;

function openDiscoveryDetails(button) {
  _discoveryDetailFocus = button;
  document.getElementById('discovery-details').showModal();
}
function closeDiscoveryDetails() {
  document.getElementById('discovery-details').close();
}
function dismissDiscoverySummary() {
  _discoveryDismissed = _discoveryProgressView?.id;
  _discoveryHistoryOpen = false;
  renderDiscoveryProgress(_discoveryProgressView);
}
function renderDiscoveryCompact(progress, phase, percent, heading) {
  const running = progress.status === 'running';
  if (running) { _discoverySeenRunning = progress.id; _discoveryHistoryOpen = false; }
  const counts = discoveryCount(progress.new_companies, 'new company', 'new companies') + ' · ' +
    tr(progress.known_companies + ' already known') + ' · ' + discoveryCount(progress.errors, 'error', 'errors');
  const detailIcon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/></svg>';
  const detail = '<button class="btn btn-secondary btn-sm discovery-detail-trigger" onclick="openDiscoveryDetails(this)" aria-label="' + escHtml(tr('Search details')) + '" title="' + escHtml(tr('Search details')) + '">' + detailIcon + '</button>';
  const phaseText = tr(phase) + (percent === null ? '' : ' · ' + progress.completed + '/' + progress.total + ' · ' + percent + '%');
  const summary = '<div class="sig-row discovery-status-row"><div class="sig-main"><div class="sig-label" role="status">' +
    '<span class="discovery-status-dot' + (running ? ' running' : progress.errors ? ' warning' : '') + '" aria-hidden="true"></span>' + escHtml(heading) + '</div>' +
    '<div class="sig-desc">' + escHtml(running ? phaseText : counts) + '</div></div><div class="sig-decide">' + detail + (!running ? '<button class="btn btn-secondary btn-sm discovery-detail-trigger" onclick="dismissDiscoverySummary()" aria-label="' + escHtml(tr('Hide summary')) + '" title="' + escHtml(tr('Hide summary')) + '"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg></button>' : '') + '</div></div>';
  const historical = !running && (_discoverySeenRunning !== progress.id || _discoveryDismissed === progress.id);
  document.getElementById('discover-progress').innerHTML = historical ?
    '<details class="discovery-history discovery-history-slim"' + (_discoveryHistoryOpen ? ' open' : '') + ' ontoggle="_discoveryHistoryOpen=this.open"><summary>' + escHtml(tr('Last search')) + ' · ' + escHtml(heading) + '</summary>' + summary + '</details>' : summary;
}


function discoveryDuration(seconds) {
  seconds = Math.max(0, Math.round(seconds));
  return seconds < 60 ? seconds + ' s' : Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0') + ' min';
}

async function pollDiscoveryProgress(schedule = true) {
  if (_progressInFlight) return;
  _progressInFlight = true;
  clearTimeout(_progressTimer);
  try {
    const data = await api('/api/discover/progress');
    if (data?.progress) renderDiscoveryProgress(data.progress);
    else if (_discoveryRunning) document.getElementById('discover-progress').innerHTML =
      '<div class="card"><p role="status">' + escHtml(tr(data ? 'Preparing search…' : 'Connection interrupted. The search continues on the server.')) + '</p></div>';
    else if (data && document.getElementById('discover-result').innerHTML && !_discoveryProgressView) {
      document.getElementById('discover-progress').innerHTML = '<details class="card discovery-history"><summary>' + escHtml(tr('Last search')) + '</summary><button class="btn btn-secondary btn-sm" onclick="openDiscoveryDetails(this)">' + escHtml(tr('Search details')) + '</button></details>';
    }
  } finally {
    _progressInFlight = false;
    if (schedule && _discoveryRunning) _progressTimer = setTimeout(pollDiscoveryProgress, 1000);
  }
}

function discoveryLimitNotice(results) {
  if (!Array.isArray(results) || !results.length) return '<p class="muted">Für diesen Suchlauf wurde das Ergebnislimit noch nicht erfasst.</p>';
  const measured=results.filter(item=>Number.isInteger(item.raw_count));
  const reached=measured.filter(item=>item.reached);
  let message=reached.length
    ? 'Ergebnislimit bei '+reached.length+' Suchanfrage(n) erreicht. Weitere Treffer sind möglich. Erhöhe das Ergebnislimit unter „Weitere Suchoptionen“.'
    : measured.length===results.length
      ? 'Die abgeschlossenen Suchanfragen lieferten weniger Rohdatensätze als das eingestellte Ergebnislimit. Mehr Limit allein liefert deshalb nicht automatisch mehr Unternehmen.'
      : 'Das Erreichen des Ergebnislimits konnte für diese Datenquelle nicht vollständig bestimmt werden.';
  return '<div class="discovery-limit-notice"><p>'+escHtml(message)+'</p><p class="muted">Das Limit gilt pro Suchanfrage für Rohdatensätze. Namenlose Einträge, Dubletten und bereits bekannte Unternehmen ergeben keine neuen Unternehmen. Dies ist keine vollständige Marktübersicht.</p>'+
    '<ul>'+results.map(item=>'<li>'+escHtml(item.query)+': '+(Number.isInteger(item.raw_count)?item.raw_count+' von maximal '+item.limit+' Rohdatensätzen':'Rohdatenlimit nicht erfasst')+' · '+item.usable_count+' nutzbare Treffer</li>').join('')+'</ul></div>';
}

function renderDiscoveryProgress(progress) {
  if (progress.target_summary&&typeof renderRunTargetSummary==='function')renderRunTargetSummary(progress.target_summary);
  _discoveryProgressView = progress;
  const stages = [['geocoding', 'Prepare locations'], ['searching', 'Find companies'], ['profiling', 'Check websites']];
  if (progress.search?.email_search || progress.stage === 'emails') stages.push(['emails','Find public emails']);
  const index = stages.findIndex(([key]) => key === progress.stage);
  const running = progress.status === 'running';
  if (running && progress.search && _restoredDiscoveryRun !== progress.id) {
    _restoredDiscoveryRun = progress.id;
    document.getElementById('disc-terms').value = progress.search.terms.join('\n');
    _discoveryLocations = progress.search.cities.map(name =>
      progress.search.locations.find(location => location.name === name) || {name});
    document.getElementById('disc-radius').value = String(progress.search.radius_km);
    document.getElementById('disc-email-search').checked = !!progress.search.email_search;
    document.getElementById('disc-target-profile').value=progress.search.target_profile_id||'';
    document.getElementById('disc-email-mode').value = progress.search.email_mode || 'quick';
    document.getElementById('disc-maps-mode').value = progress.search.maps_mode || 'quick';
    document.getElementById('disc-maps-filter').value = progress.search.maps_filter || 'all';
    document.getElementById('disc-maps-resume').checked = progress.search.maps_resume !== false;
    document.getElementById('discovery-search-summary').textContent = discoveryCount(progress.search.terms.length, 'business type', 'business types') + ' · ' + discoveryCount(progress.search.cities.length, 'location', 'locations') + ' · ' + discoveryCount(progress.search.query_count || progress.search.terms.length * Math.max(1, progress.search.cities.length), 'search query', 'search queries');
    renderDiscoveryLocations(); renderDiscoveryTerms();
    document.querySelectorAll('#disc-location-chips button').forEach(button => { button.disabled = true; });
  }
  const labels = {running: 'Search in progress', completed: 'Search completed',
    completed_with_errors: 'Search completed with errors', stopped: 'Search stopped', failed: 'Search failed', interrupted: 'Search interrupted. Start a new search to continue.'};
  const percent = progress.total ? Math.floor(progress.completed / progress.total * 100) : null;
  const phase = stages[index]?.[1] || 'Preparing search…';
  const eta = progress.eta_seconds;
  const timing = !running ? '' : progress.waiting ? tr('Waiting for a response. The estimate will update.') :
    eta ? tr('Estimated time left in this step') + ': ' + discoveryDuration(eta[0]) + '–' + discoveryDuration(eta[1]) :
    tr('Time estimate available after a few completed items.');
  const heading = tr(progress.stop_requested && running ? 'Stopping after the current item…' : labels[progress.status] || 'Search in progress');
  if (!document.activeElement?.closest('#discover-progress')) renderDiscoveryCompact(progress, phase, percent, heading);
  document.getElementById('discovery-details-progress').innerHTML = '<div class="discovery-progress">' +
    '<div class="discovery-progress-heading"><h2>' + escHtml(heading) + '</h2>' +
    '<span>' + escHtml(tr('Elapsed')) + ': ' + discoveryDuration(progress.elapsed_seconds) + '</span></div>' +
    '<ol class="discovery-stages" aria-label="' + escHtml(tr('Search steps')) + '">' + stages.map(([key, label], i) =>
      '<li' + (i === index ? ' aria-current="step"' : '') + ' class="' + (i < index ? 'complete' : i === index ? 'current' : '') + '">' + escHtml(tr(label)) + '</li>').join('') + '</ol>' +
    '<div class="discovery-progress-label"><strong>' + escHtml(tr(phase)) + '</strong><span>' +
    (percent === null ? escHtml(tr(running ? 'Preparing…' : 'No open items')) : progress.completed + '/' + progress.total + ' · ' + percent + '%') + '</span></div>' +
    (progress.email_summary ? '<p>' + emailSearchSummary(progress.email_summary) + '</p>' : '') +
    '<progress max="' + Math.max(1, progress.total) + '"' + (percent === null ? (running ? '' : ' value="0"') : ' value="' + progress.completed + '"') + ' aria-label="' + escHtml(tr(phase)) + '"></progress>' +
    (progress.current && running ? '<p class="discovery-current">' + escHtml(tr('Currently')) + ': ' + escHtml(progress.current) + '</p>' : '') +
    '<p class="muted discovery-time">' + escHtml(timing) + '</p>' +
    '<p class="discovery-live-counts" role="status">' + escHtml(discoveryCount(progress.new_companies, 'new company', 'new companies')) + ' · ' +
    escHtml(tr(progress.known_companies + ' already known')) + ' · ' + escHtml(discoveryCount(progress.errors, 'error', 'errors')) + '</p>' +
    (!running ? discoveryLimitNotice(progress.result_limits) : '') +
    '<button class="btn btn-secondary btn-sm" onclick="showTab(\'companies\', null)">' + escHtml(tr('View companies')) + '</button></div>';
}

function emailSearchSummary(summary) {
  return escHtml(tr('Email search')) + ': ' + summary.done + '/' + summary.total + ' · ' +
    summary.found + ' ' + escHtml(tr('with email')) + ' · ' + summary.not_found + ' ' + escHtml(tr('without email')) + ' · ' +
    summary.no_website + ' ' + escHtml(tr('without website')) + ' · ' + summary.failed + ' ' + escHtml(tr('failed')) +
    (summary.skipped_limit ? ' · ' + summary.skipped_limit + ' ' + escHtml(tr('above the 1000-company limit')) : '');
}

function renderDiscoverResult(report, running) {
  const el = document.getElementById('discover-result');
  if (running) {
    el.innerHTML = '';
    return;
  }
  if (!report) { el.innerHTML = ''; return; }

  const stat = (label, value, tone) =>
    '<div class="stat-card"><div class="label">' + label + '</div>' +
    '<div class="value"' + (tone ? ' style="color:var(--' + tone + ')"' : '') + '>' +
    value + '</div></div>';

  el.innerHTML = '<div class="subhead">Last run</div>' + discoveryLimitNotice(report.result_limits) +
    (report.email_summary?.total ? '<p>' + emailSearchSummary(report.email_summary) + '</p>' : '') +
    '<div class="stats-grid">' +
      stat('New companies', report.new_companies || 0, 'accent') +
      stat('Already known', report.known_companies || 0) +
      stat('Observations', report.observations || 0) +
      stat('Filtered as junk', report.junk || 0) +
      stat('Actual cost', report.actual_cost ? '$' + report.actual_cost.toFixed(4) : 'free') +
    '</div>' +
    (report.stopped ? '<div class="test-result error" style="margin-top:14px">' +
      'Stopped early: ' + escHtml(report.stopped) + '</div>' : '') +
    ((report.errors || []).length
      ? '<div class="card" style="margin-top:14px"><h2>Problems</h2>' +
        (report.errors || []).slice(0, 8).map(e =>
          '<div class="check-help">' + escHtml(e.replace('Overpass is temporarily unavailable. All backup servers failed. Please try again later.', tr('Overpass is temporarily unavailable. All backup servers failed. Please try again later.'))) + '</div>').join('') + '</div>'
      : '') + (report.provider === 'geoapify' ? discoveryAttribution() : '');
}

// ── Cohort builder: a prospect list is a query ──

let _cohort = { require: new Set(), exclude: new Set() };

function renderCohortBuilder() {
  const el = document.getElementById('cohort-builder');
  if (!el || !_signals) return;

  const confirmed = (_signals.groups || [])
    .flatMap(g => g.signals)
    .filter(s => s.status === 'confirmed');

  if (!confirmed.length) {
    el.innerHTML = '<p class="muted" style="font-size:13px">' +
      'Confirm some signals above and they become the building blocks here.</p>';
    document.getElementById('cohort-result').innerHTML = '';
    return;
  }

  const col = (title, key, hint) =>
    '<div><div class="subhead" style="margin-top:0">' + title +
      ' <span class="muted" style="font-weight:400;text-transform:none;letter-spacing:0">' +
      hint + '</span></div><div class="cohort-grid">' +
    confirmed.map(s =>
      '<label class="cohort-pick"><input type="checkbox" ' +
        (_cohort[key].has(s.code) ? 'checked ' : '') +
        'onchange="toggleCohort(\'' + key + '\',\'' + s.code + '\',this.checked)">' +
        '<span>' + escHtml(s.label || s.code) + '</span>' +
        '<span class="n">' + (s.companies || 0) + '</span></label>'
    ).join('') + '</div></div>';

  el.innerHTML = col('Must have', 'require', '&mdash; every company in the cohort carries all of these') +
    '<div style="height:18px"></div>' +
    col('Must not have', 'exclude', '&mdash; disqualifiers');
}

function toggleCohort(key, code, on) {
  if (on) _cohort[key].add(code); else _cohort[key].delete(code);
  // A company can't be both required and excluded on the same signal.
  const other = key === 'require' ? 'exclude' : 'require';
  if (on) _cohort[other].delete(code);
  runCohort();
  renderCohortBuilder();
}

async function runCohort() {
  const el = document.getElementById('cohort-result');
  if (!el) return;
  const require = [..._cohort.require], exclude = [..._cohort.exclude];
  if (!require.length) { el.innerHTML = ''; return; }

  const data = await api('/api/cohort', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({require: require, exclude: exclude}),
  });
  if (!data) { el.innerHTML = ''; return; }

  let html = '<div style="border-top:1px solid var(--border);margin-top:20px;padding-top:20px">' +
    '<div class="cohort-size">' + data.size + '</div>' +
    '<div class="muted" style="font-size:13px;margin-top:2px">compan' +
      (data.size === 1 ? 'y matches' : 'ies match') + ' this cohort right now</div>';

  if (data.companies && data.companies.length) {
    html += '<div class="table-card" style="margin-top:16px"><table><thead><tr>' +
      '<th>Company</th><th>Domain</th><th>Industry</th><th>Location</th>' +
      '</tr></thead><tbody>' +
      data.companies.slice(0, 50).map(c =>
        '<tr><td><button type="button" class="company-name-button" data-company-profile="' + escHtml(c.id) + '" data-user-content>' + escHtml(c.name) + '</button></td><td class="muted">' + escHtml(c.domain) + '</td>' +
        '<td class="muted">' + escHtml(c.industry) + '</td>' +
        '<td class="muted">' + escHtml(c.location) + '</td></tr>'
      ).join('') + '</tbody></table></div>';
    if (data.size > 50) {
      html += '<p class="muted" style="font-size:12px;margin-top:10px">Showing the first 50.</p>';
    }
  } else if (data.size === 0) {
    html += '<p class="muted" style="font-size:13px;margin-top:12px">' +
      'No company carries all of those yet. Either loosen the cohort, or run ' +
      'prospecting to collect more.</p>';
  }
  el.innerHTML = html + '</div>';
  el.querySelectorAll('[data-company-profile]').forEach(button => { button.onclick = () => openCompanyProfile(button.dataset.companyProfile); });
}

// ── Settings ──

async function loadSettings() {
  loadContactResearchSettings();
  loadAssistantSettings();
  loadSendingSettings();
  const data = await api('/api/settings');
  if (!data) return;

  // Active provider indicator
  const prov = data.provider || 'instantly';
  const provEl = document.getElementById('active-provider');
  if (provEl) provEl.textContent = prov;

  // Secret fields never echo a value — show a "saved" placeholder instead.
  const savedPh = (id, isSet, base) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = '';
    el.placeholder = isSet ? 'Saved — enter new value to change' : base;
  };
  const tag = (id, ok, okLabel) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = 'email-tag ' + (ok ? 'verified' : 'guess');
    el.textContent = ok ? okLabel : 'not set';
  };

  // Non-secret values repopulate
  document.getElementById('gmail-id').value = data.gmail_client_id || '';
  document.getElementById('smtp-host').value = data.smtp_host || '';
  document.getElementById('smtp-port').value = data.smtp_port || '';
  document.getElementById('smtp-user').value = data.smtp_username || '';
  document.getElementById('imap-host').value = data.imap_host || '';
  document.getElementById('imap-port').value = data.imap_port || '';
  document.getElementById('imap-user').value = data.imap_username || '';
  document.getElementById('linkedin-email').value = data.linkedin_email || '';
  document.getElementById('cf-account-id').value = data.cloudflare_account_id || '';

  savedPh('gmail-secret', data.gmail_client_secret_set, 'Enter client secret');
  savedPh('smtp-pass', data.smtp_password_set, 'Enter password / app password');
  savedPh('imap-pass', data.imap_password_set, 'Defaults to SMTP password');
  savedPh('instantly-key', data.instantly_api_key_set, 'Enter your Instantly API key');
  savedPh('reoon-key', data.reoon_api_key_set, '600 free/mo — reoon.com/email-verifier');
  savedPh('zerobounce-key', data.zerobounce_api_key_set, '100 free/mo — best for M365/Workspace catch-alls');
  savedPh('hunter-key', data.hunter_api_key_set, '50 free/mo + email-pattern lookup');
  savedPh('linkedin-password', data.linkedin_password_set, 'Enter password');
  savedPh('cf-api-token', data.cloudflare_api_token_set, 'Your Cloudflare API Token');
  savedPh('geoapify-key', data.geoapify_api_key_set, 'Enter API key');
  savedPh('serpapi-key', data.serpapi_api_key_set, 'Enter API key');

  // Gmail auth status chip
  const g = document.getElementById('gmail-status');
  if (g) {
    if (data.gmail_authorized) { g.className = 'email-tag verified'; g.textContent = 'authorized'; }
    else if (data.gmail_client_secret_set) { g.className = 'email-tag risky'; g.textContent = 'run: harvey gmail auth'; }
    else { g.className = 'email-tag guess'; g.textContent = 'not set up'; }
  }
  tag('reoon-status', data.reoon_api_key_set, 'set');
  tag('zerobounce-status', data.zerobounce_api_key_set, 'set');
  tag('hunter-status', data.hunter_api_key_set, 'set');
}

function saveGmail() {
  const payload = {GMAIL_CLIENT_ID: document.getElementById('gmail-id').value.trim()};
  const sec = document.getElementById('gmail-secret').value;
  if (sec) payload.GMAIL_CLIENT_SECRET = sec;
  saveEnv(payload, 'Gmail OAuth saved. Now run "harvey gmail auth" in your terminal.').then(loadSettings);
}

function saveSmtp() {
  const payload = {
    SMTP_HOST: document.getElementById('smtp-host').value.trim(),
    SMTP_PORT: document.getElementById('smtp-port').value.trim(),
    SMTP_USERNAME: document.getElementById('smtp-user').value.trim(),
    IMAP_HOST: document.getElementById('imap-host').value.trim(),
    IMAP_PORT: document.getElementById('imap-port').value.trim(),
    IMAP_USERNAME: document.getElementById('imap-user').value.trim(),
  };
  const pass = document.getElementById('smtp-pass').value;
  const imapPass = document.getElementById('imap-pass').value;
  if (pass) payload.SMTP_PASSWORD = pass;
  if (imapPass) payload.IMAP_PASSWORD = imapPass;
  saveEnv(payload, 'SMTP settings saved.').then(loadSettings);
}

function saveVerifiers() {
  const payload = {};
  const r = document.getElementById('reoon-key').value;
  const z = document.getElementById('zerobounce-key').value;
  const h = document.getElementById('hunter-key').value;
  if (r) payload.REOON_API_KEY = r;
  if (z) payload.ZEROBOUNCE_API_KEY = z;
  if (h) payload.HUNTER_API_KEY = h;
  if (!Object.keys(payload).length) { showToast('Enter at least one key first.', 'error'); return; }
  saveEnv(payload, 'Verification keys saved.').then(loadSettings);
}

function saveDiscoveryKeys() {
  const payload = {};
  const geoapify = document.getElementById('geoapify-key').value.trim();
  const serpapi = document.getElementById('serpapi-key').value.trim();
  if (geoapify) payload.GEOAPIFY_API_KEY = geoapify;
  if (serpapi) payload.SERPAPI_API_KEY = serpapi;
  if (!Object.keys(payload).length) { showToast('Enter at least one key first.', 'error'); return; }
  saveEnv(payload, tr('Discovery keys saved.')).then(loadSettings);
}

async function saveEnv(payload, okMsg) {
  const data = await api('/api/settings/env', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  if (data && data.success) showToast(okMsg, 'success');
  else showToast((data && data.message) || 'Save failed — is the dashboard still running?', 'error');
}

function saveInstantly() {
  saveEnv({INSTANTLY_API_KEY: document.getElementById('instantly-key').value.trim()}, 'Instantly API key saved.');
}

function saveLinkedIn() {
  const payload = {LINKEDIN_EMAIL: document.getElementById('linkedin-email').value.trim()};
  const pass = document.getElementById('linkedin-password').value;
  if (pass) payload.LINKEDIN_PASSWORD = pass;
  saveEnv(payload, 'LinkedIn credentials saved.');
}

function saveCloudflare() {
  saveEnv({
    CLOUDFLARE_ACCOUNT_ID: document.getElementById('cf-account-id').value.trim(),
    CLOUDFLARE_API_TOKEN: document.getElementById('cf-api-token').value.trim()
  }, 'Cloudflare credentials saved.');
}

async function testInstantly() {
  const key = document.getElementById('instantly-key').value.trim();
  const el = document.getElementById('instantly-test-result');
  el.innerHTML = '<div class="test-result pending">Testing&hellip;</div>';
  const data = await api('/api/settings/test-instantly', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({api_key: key})
  });
  if (!data) {
    el.innerHTML = '<div class="test-result error">Could not reach the dashboard server.</div>';
    return;
  }
  el.innerHTML = '<div class="test-result ' + (data.success ? 'success' : 'error') + '">' + escHtml(data.message) + '</div>';
}

// ── Controls ──

let agentControlBusy = false;
let agentStatusKnown = false;
let agentIsRunning = false;
function syncAgentControls() {
  document.getElementById('header-agent-toggle').disabled = agentControlBusy || !agentStatusKnown;
  document.getElementById('header-agent-toggle').setAttribute('aria-busy', String(agentControlBusy));
  document.getElementById('btn-start').disabled = agentControlBusy;
  document.getElementById('btn-stop').disabled = agentControlBusy;
}
function toggleHeaderAgent() {
  if (agentControlBusy || !agentStatusKnown) return;
  return agentIsRunning ? stopHarvey() : startHarvey();
}
async function loadHarveyStatus() {
  const data = await api('/api/harvey/status');
  const headerDot = document.getElementById('header-dot');
  const headerText = document.getElementById('header-status-text');

  agentStatusKnown = !!data;
  syncAgentControls();
  if (!data) {
    headerDot.className = 'status-dot offline';
    headerText.textContent = 'Offline';
    return;
  }
  const running = !!data.running;
  agentIsRunning = running;
  document.getElementById('header-agent-toggle').setAttribute('aria-checked', String(running));

  headerDot.className = 'status-dot ' + (running ? 'running' : 'stopped');
  headerText.textContent = running ? 'Running' : 'Stopped';
  document.getElementById('control-dot').className = 'dot ' + (running ? 'running' : 'stopped');
  const label = document.getElementById('control-label');
  label.className = 'label ' + (running ? 'running' : 'stopped');
  label.textContent = running ? 'Running' : 'Stopped';

  const meta = document.getElementById('control-meta');
  if (running && data.pid) {
    let info = 'PID ' + escHtml(String(data.pid));
    if (data.started_at) info += ' &middot; started ' + formatDate(data.started_at);
    meta.innerHTML = info;
  } else {
    meta.innerHTML = 'Siveron wakes every few minutes, does what needs doing, and sleeps.';
  }

  document.getElementById('btn-start').style.display = running ? 'none' : '';
  document.getElementById('btn-stop').style.display = running ? '' : 'none';
}

async function setAgentRunning(running) {
  if (agentControlBusy) return;
  agentControlBusy = true;
  syncAgentControls();
  try {
    const data = await api('/api/harvey/' + (running ? 'start' : 'stop'), {method: 'POST'});
    if (data && data.success) showToast(running ? 'Siveron started.' : 'Siveron stopped.', 'success');
    else showToast((data && data.message) || (running ? 'Failed to start.' : 'Failed to stop.'), 'error');
  } finally {
    try { await loadHarveyStatus(); }
    finally { agentControlBusy = false; syncAgentControls(); }
  }
}
async function startHarvey() { return setAgentRunning(true); }
async function stopHarvey() { return setAgentRunning(false); }

async function loadLogs() {
  const data = await api('/api/harvey/logs');
  const el = document.getElementById('log-viewer');
  if (data && data.lines && data.lines.length) {
    const stick = el.scrollTop + el.clientHeight >= el.scrollHeight - 30;
    el.textContent = data.lines.join('\n');
    if (stick) el.scrollTop = el.scrollHeight;
  } else {
    el.textContent = 'No logs yet. Start Siveron to see activity.';
  }
}

// ── Pipeline data ──

async function loadStats() {
  const grid = document.getElementById('stats-grid');
  const data = await api('/api/stats');
  if (!data) { grid.innerHTML = offlineState(); return; }
  if (data.error) {
    grid.innerHTML = emptyState('&#9670;', 'No pipeline data yet',
      'Start Siveron from the <b>Controls</b> tab and it will begin prospecting, writing, and sending on its own.');
    return;
  }
  const p = data.prospects || {}, c = data.campaigns || {}, v = data.conversations || {};
  const chips = (map) => {
    const entries = Object.entries(map || {});
    if (!entries.length) return '<span class="chip muted">none yet</span>';
    return entries.map(([k, n]) =>
      '<span class="chip">' + escHtml(k) + ' <b>' + escHtml(String(n)) + '</b></span>'
    ).join('');
  };
  const card = (label, value, breakdown) =>
    '<div class="stat-card"><div class="label">' + label + '</div>' +
    '<div class="value">' + value + '</div>' +
    '<div class="breakdown">' + breakdown + '</div></div>';

  grid.innerHTML =
    card('Prospects', p.total || 0, chips(p.by_status)) +
    card('Campaigns', c.total || 0, chips(c.by_status)) +
    card('Conversations', v.total || 0, chips(v.by_status)) +
    card('Actions Logged', data.actions_total || 0, brainCallChips(data));
}

// Calls today per subscription — each labelled with the provider it ran on.
function brainCallChips(data) {
  const chip = (label, n) => '<span class="chip">' + label + ' calls today <b>' + escHtml(String(n || 0)) + '</b></span>';
  const codex = data.codex_calls_today || 0;
  const st = data.brain_status || {};
  // A paused brain must not look healthy: say so, and why.
  const paused = st.status === 'paused'
    ? '<span class="chip" title="' + escHtml(st.reason || '') + '">' +
      escHtml(st.provider === 'codex' ? 'Codex' : 'Brain') + ' <b>paused</b>: ' +
      escHtml((st.reason || '').slice(0, 120)) + '</span>'
    : '';
  if (data.brain_provider === 'codex') {
    return paused + chip('Codex', codex) + (data.claude_calls_today ? chip('Claude', data.claude_calls_today) : '');
  }
  return paused + chip('Claude', data.claude_calls_today) + (codex ? chip('Codex', codex) : '');
}

function fmtTokens(n) {
  n = n || 0;
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return String(n);
}


function emailTag(p) {
  if (!p.email) return '';
  // Fall back to the legacy boolean for rows predating email_status.
  if(p.email_checks && !p.email_checks.send_supported)return ' <span class="badge t-waiting">'+escHtml(tr('Address format not supported for sending'))+'</span>';
  const status = p.email_status || (p.email_verified ? 'verified' : 'guess');
  if (!STATUS[status]) return '';
  const m = statusMeta(status);
  return ' <span class="badge t-' + m.tone + '" style="margin-left:6px">' + escHtml(m.label) + '</span>';
}

// Quota gauges for the ACTIVE provider only: Claude's are the numbers
// `/usage` shows in Claude Code; Codex's are the ChatGPT plan's limits.
// When they can't be read, say so rather than hiding the card.
function quotaCardHtml(data, refreshing = false) {
  const provider = data && data.quota_provider;
  if (!provider) return '';
  const title = provider === 'codex' ? 'Codex (ChatGPT plan) Quota' : 'Claude Subscription Quota';
  let html = '<h2>' + escHtml(tr(title)) + '</h2><p class="muted">'+escHtml(tr(data.quota_checked_at?'Last checked:':'Last checked: unknown'))+(data.quota_checked_at?' '+escHtml(formatDate(data.quota_checked_at)):'')+'</p><button type="button" class="btn btn-secondary btn-sm" id="usage-quota-refresh" onclick="refreshUsageQuota()"'+(refreshing?' disabled':'')+'>'+escHtml(tr(refreshing?'Refreshing quota…':'Refresh quota now'))+'</button><p class="muted">'+escHtml(tr('Automatic readings are cached for up to 5 minutes. Calls below only include Siveron.'))+'</p>';
  if (!data.quota || !Object.keys(data.quota).length) {
    const why = provider === 'codex'
      ? "Quota unavailable: Siveron couldn't read your ChatGPT plan's limits (check codex login, the Codex CLI version, and network)."
      : "Quota unavailable: Siveron couldn't read your Claude subscription's limits (check claude login and network).";
    return html + '<p class="muted">' + escHtml(why) + ' Until it can, budgets count Siveron\'s own calls.</p>';
  }
  const labels = {five_hour: '5-hour window', seven_day: 'Weekly', primary: 'Primary window',
                  secondary: 'Secondary window', limit_reached: 'Usage limit reached'};
  for (const [key, w] of Object.entries(data.quota)) {
    const pct = Math.min(100, Math.max(0, w.utilization || 0));
    const color = pct >= 80 ? 'yellow' : 'green';
    const resets = w.resets_at ? 'resets ' + formatDate(w.resets_at) : '';
    html += '<div class="progress-wrap">' +
      '<div class="progress-label">' +
        '<span class="text">' + escHtml(labels[key] || key) + (resets ? ' &middot; ' + escHtml(resets) : '') + '</span>' +
        '<span class="pct">' + pct.toFixed(0) + '%</span>' +
      '</div>' +
      '<div class="progress-bar"><div class="progress-fill ' + color + '" style="width:' + pct + '%"></div></div>' +
    '</div>';
  }
  return html;
}

let usageRefreshRunning = false;
async function refreshUsageQuota() {
 if (usageRefreshRunning) return;
 usageRefreshRunning = true;
 const button=document.getElementById('usage-quota-refresh');if(button){button.disabled=true;button.textContent=tr('Refreshing quota…');}
 try { await loadUsage(true); } finally { usageRefreshRunning=false;const current=document.getElementById('usage-quota-refresh');if(current){current.disabled=false;current.textContent=tr('Refresh quota now');} }
}
async function loadUsage(force = false) {
  if (usageRefreshRunning && !force) return;
  const data = await api('/api/usage'+(force?'?refresh=true':''));
  const statsEl = document.getElementById('usage-stats');
  if (!data) { statsEl.innerHTML = offlineState(); document.getElementById('usage-quota').innerHTML=offlineState(); return; }

  const quotaEl = document.getElementById('usage-quota');
  const qHtml = quotaCardHtml(data, usageRefreshRunning);
  quotaEl.innerHTML = qHtml;
  quotaEl.style.display = qHtml ? 'block' : 'none';

  // Totals cards — usage-first (calls is the headline; tokens as chips).
  // No dollars: on a subscription plan usage isn't billed per token.
  const t = data.totals || {};
  const card = (label, p) => {
    p = p || {};
    return '<div class="stat-card"><div class="label">' + label + '</div>' +
      '<div class="value">' + (p.calls || 0) + '</div>' +
      '<div class="breakdown">' +
        '<span class="chip">calls</span>' +
        '<span class="chip">out <b>' + fmtTokens(p.output_tokens) + '</b></span>' +
        '<span class="chip">in <b>' + fmtTokens(p.input_tokens) + '</b></span>' +
        '<span class="chip">cached <b>' + fmtTokens(p.cache_read_tokens) + '</b></span>' +
      '</div></div>';
  };
  statsEl.innerHTML = card('Today', t.today) + card('Last 7 Days', t.week) + card('Last 30 Days', t.month);

  // Daily bars — output tokens per day (the work done)
  const dailyEl = document.getElementById('usage-daily');
  const days = data.by_day || [];
  if (days.length) {
    const maxOut = Math.max(...days.map(d => d.output_tokens || 0), 1);
    let dHtml = '<h2>Daily Output Tokens (30 days)</h2>';
    for (const d of days.slice(-30)) {
      const pct = Math.max(2, (d.output_tokens || 0) / maxOut * 100);
      dHtml += '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;font-size:12px">' +
        '<span class="muted" style="width:78px;flex-shrink:0;font-family:var(--mono)">' + escHtml(d.day || '') + '</span>' +
        '<div style="flex:1;background:rgba(255,255,255,0.05);border-radius:99px;height:10px;overflow:hidden">' +
          '<div style="width:' + pct + '%;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent-deep),var(--accent))"></div>' +
        '</div>' +
        '<span style="width:130px;text-align:right;font-variant-numeric:tabular-nums">' + fmtTokens(d.output_tokens) + ' out' +
          ' <span class="muted">&middot; ' + (d.calls || 0) + ' calls</span></span>' +
      '</div>';
    }
    dailyEl.innerHTML = dHtml;
    dailyEl.style.display = 'block';
  } else {
    dailyEl.style.display = 'none';
  }

  // Breakdown tables — calls + tokens, no cost column
  const tablesEl = document.getElementById('usage-tables');
  const table = (title, rows, keyName) => {
    if (!rows || !rows.length) return '';
    let h = '<div class="card"><h2>' + title + '</h2><div class="table-card"><table><thead><tr>' +
      '<th>' + keyName + '</th><th>Calls</th><th>Input</th><th>Output</th><th>Cache read</th>' +
      '</tr></thead><tbody>';
    for (const r of rows) {
      h += '<tr><td>' + escHtml(String(r[keyName.toLowerCase()] || '')) + '</td>' +
        '<td>' + (r.calls || 0) + '</td>' +
        '<td class="muted">' + fmtTokens(r.input_tokens) + '</td>' +
        '<td>' + fmtTokens(r.output_tokens) + '</td>' +
        '<td class="muted">' + fmtTokens(r.cache_read_tokens) + '</td></tr>';
    }
    return h + '</tbody></table></div></div>';
  };

  const anyRows = (data.by_agent || []).length || (data.by_task || []).length;
  if (!anyRows) {
    tablesEl.innerHTML = emptyState('&#9680;', 'No usage recorded yet',
      'Once Siveron starts making model calls (Claude or Codex), every one is logged here with exact calls and tokens by provider, agent and task.');
  } else {
    const providers = data.by_provider || [];
    const showProviders = providers.length > 1 || (providers.length === 1 && providers[0].provider !== 'claude');
    tablesEl.innerHTML =
      (showProviders ? table('By Provider (30 days)', providers, 'Provider') : '') +
      table('By Agent (30 days)', data.by_agent, 'Agent') +
      table('By Task (30 days)', data.by_task, 'Task') +
      table('By Model (30 days)', data.by_model, 'Model');
  }
}

// ── Outbox: a decisions desk, not a wall of drafts ──
//
// Approving mail is a queue of one-at-a-time judgements. Showing all of them
// stacked invites a single "approve all" reflex, which is exactly the review
// the approval ladder exists to prevent. One email fills the pane; the rest
// wait in the rail.

function outboxStatus(status) {
  const states = {
    sent: ['good', 'Sent'],
    approved: ['waiting', 'Queued'],
    pending_review: ['waiting', 'Awaiting approval'],
    failed: ['bad', 'Sending failed'],
    rejected: ['idle', 'Rejected'],
    cancelled: ['idle', 'Cancelled'],
  };
  const [tone, label] = states[status] || ['idle', 'Unknown status'];
  return '<span class="badge t-' + tone + ' outbox-status"><span class="outbox-status-dot" aria-hidden="true"></span>' + label + '</span>';
}

function outboxSendDate(item) {
 const value=item.readiness?.earliest_at || item.send_at;
 return formatDate(value && !/(Z|[+-]\d{2}:?\d{2})$/.test(value)?value+'Z':value);
}
function outboxReadiness(item) {
  const de=window.harveyLanguage?.()==='de';
  const value=item.readiness || {state:'blocked',reasons:[]};
  const labels=de?{ready:'Bereit',waiting:'Wartet',blocked:'Blockiert',unknown:'Ungeklärt',failed:'Fehlgeschlagen',sent:'Versendet'}:{ready:'Ready',waiting:'Waiting',blocked:'Blocked',unknown:'Unconfirmed',failed:'Failed',sent:'Sent'};
  const reasons=value.reasons||[];
  const state=Object.hasOwn(labels,value.state)?value.state:'blocked';
  const reasonHTML=reason=>{
    const target=['outbox','settings','prospects','control','conversations'].includes(reason.target)?reason.target:'outbox';
    return '<li><strong>'+escHtml(de?reason.de:reason.en)+'</strong><span>'+escHtml(de?reason.next_de:reason.next_en)+'</span>'+
      (target!=='outbox'?'<button type="button" class="btn btn-secondary btn-sm" onclick="showTab(\''+target+'\')">'+(de?'Bereich öffnen':'Open section')+'</button>':'')+'</li>';
  };
  let body=reasons.length?'<ul>'+reasonHTML(reasons[0])+'</ul>':'<p>'+(de?'Nach letzter Prüfung für den nächsten zulässigen Durchlauf bereit; keine Versandgarantie.':'Eligible at the last assessment for the next permitted cycle; sending is not guaranteed.')+'</p>';
  if(reasons.length>1)body+='<details><summary>'+(de?'Weitere Ursachen':'More reasons')+' ('+(reasons.length-1)+')</summary><ul>'+reasons.slice(1).map(reasonHTML).join('')+'</ul></details>';
  if(!item.readiness)body='<p>'+(de?'Aktuelle Prüfung nicht verfügbar. Bitte aktualisieren.':'Current assessment unavailable. Please refresh.')+'</p>';

  return '<div class="outbox-readiness" data-user-content><span class="readiness-label readiness-'+state+'">'+labels[state]+'</span>'+body+'</div>';
}
window.addEventListener('harvey-language-changed',()=>{if(currentTab==='outbox')loadOutbox();});

let outboxCampaignId=null;
try{outboxCampaignId=sessionStorage.getItem('siveron-outbox-campaign')||null;}catch{}
let outboxTaskItemId=null;
function openCampaignOutbox(id,itemId=null){
 outboxTaskItemId=itemId;
 outboxCampaignId=typeof id==='string'&&id.length<=100?id:null;
 try{if(outboxCampaignId)sessionStorage.setItem('siveron-outbox-campaign',outboxCampaignId);else sessionStorage.removeItem('siveron-outbox-campaign');}catch{}
 _desk.i=0;showTab('outbox');
}
function outboxScopeQuery(includeItem=true){const p=new URLSearchParams();if(outboxCampaignId)p.set('campaign_id',outboxCampaignId);if(includeItem&&outboxTaskItemId)p.set('item_id',outboxTaskItemId);return p.size?'?'+p:'';}

async function loadOutbox() {
  const data = await api('/api/outbox'+outboxScopeQuery());
  const banner = document.getElementById('outbox-banner');
  const desk = document.getElementById('outbox-desk');
  const list = document.getElementById('outbox-list');
  const actions = document.getElementById('outbox-actions');
  if (!data || data.error) { desk.innerHTML = offlineState(); list.innerHTML = ''; banner.innerHTML = ''; return; }

  const pending = data.pending || [];
  _desk.items = pending;
  if (_desk.i >= pending.length) _desk.i = Math.max(0, pending.length - 1);
  navCount('nav-outbox', pending.length);

  actions.innerHTML =
    (pending.length && !data.paused && !data.item_id
      ? '<button class="btn btn-primary btn-sm" onclick="outboxApproveAll()">Approve all ' +
        pending.length + '</button>' : '') +
    (data.paused
      ? '<button class="btn btn-secondary btn-sm" onclick="sendingToggle(\'resume\')">' +
        'Resume sending</button>'
      : '<button class="btn btn-secondary btn-sm" onclick="sendingToggle(\'pause\')">' +
        'Pause all sending</button>');

  // The kill switch gets a banner only when it's actually on — a permanent
  // bar for a thing that isn't happening is just noise.
  banner.innerHTML = data.paused
    ? '<div class="card" style="border-color:var(--red);margin-bottom:16px">' +
        '<h2 style="color:var(--red)">&#9888; Sending is paused</h2>' +
        '<p style="color:var(--text-2);font-size:13px">' + escHtml(data.paused) +
        '. Approved mail stays queued until you resume.</p></div>'
    : '';

  if(data.campaign_id||data.item_id)banner.innerHTML='<div class="outbox-campaign-scope"><strong data-user-content>'+escHtml(data.campaign_name||tr('Without campaign'))+'</strong><button type="button" class="btn btn-secondary btn-sm" onclick="openCampaignOutbox(null)">Show all campaigns</button></div>'+banner.innerHTML;

  desk.innerHTML = pending.length ? renderDesk(pending, _desk.i) :
    (data.approved || []).length
      ? '<p role="status">' + outboxStatus('approved') + ' Approved messages are waiting to send.</p>'
      : (data.failed || []).some(item => item.status === 'failed')
        ? '<p role="status">' + outboxStatus('failed') + ' At least one message could not be sent. Details are below.</p>'
      : (data.sent || []).length
        ? '<p role="status">' + outboxStatus('sent') + ' No messages are waiting for approval or sending.</p>'
        : '<div class="card">' + emptyState('&#10003;', 'Nothing to review',
          'Every draft Siveron writes lands here first. Approve one and it sends on schedule.') + '</div>';

  const table = (title, rows, cols) => {
    if (!rows || !rows.length) return '';
    let h = '<div class="card"><h2>' + title + '</h2><div class="table-card"><table><thead><tr>' +
      cols.map(c => '<th>' + c[0] + '</th>').join('') + '</tr></thead><tbody>';
    for (const r of rows) {
      h += '<tr>' + cols.map(c => '<td data-label="'+escHtml(tr(c[0]))+'"' + (c[2] ? ' class="muted"' : '') + '>' +
        (c[3] ? c[1](r) : escHtml(String(c[1](r) ?? ''))) + '</td>').join('') + '</tr>';
    }
    return h + '</tbody></table></div></div>';
  };

  list.innerHTML = '<p class="muted outbox-assessed-at" data-user-content>'+escHtml((window.harveyLanguage?.()==='de'?'Stand der Prüfung: ':'Assessment time: ')+formatDate(data.readiness_checked_at))+'</p>'+
    table('Approved &amp; scheduled', data.approved, [
      ['Status', r => outboxStatus(r.status), false, true],
      ['To', r => r.to_email], ['Step', r => r.step], ['Subject', r => r.subject], ['Attachments', r => campaignAttachmentLinks(outboxAttachments(r)), false, true],
      ['Readiness', r => outboxReadiness(r), false, true],
      ['Sends', r => outboxSendDate(r), true],
    ]) +
    table('Recently sent', data.sent, [
      ['Status', r => outboxStatus(r.status), false, true],
      ['To', r => r.to_email], ['Step', r => r.step], ['Subject', r => r.subject], ['Attachments', r => campaignAttachmentLinks(outboxAttachments(r)), false, true],
      ['Sent', r => formatDate(r.sent_at), true],
    ]) +
    table('Didn\'t send', data.failed, [
      ['To', r => r.to_email], ['Status', r => outboxStatus(r.status), false, true],
      ['Readiness', r => outboxReadiness(r), false, true],
      ['Reason', r => r.error, true], ['Updated', r => formatDate(r.updated_at), true],
    ]);
}

function outboxAttachments(item){try{const files=JSON.parse(item.attachment_metadata_json||'[]');return Array.isArray(files)?files:[];}catch{return [];}}

function renderDesk(items, i) {
  const cur = items[i];
  const rail = items.map((it, n) =>
    '<div class="desk-item ' + (n === i ? 'active' : '') + '" onclick="deskGo(' + n + ')">' +
      '<div class="to">' + escHtml(it.to_email) + '</div>' +
      '<div class="sub">' + escHtml(it.subject || '(no subject)') + '</div>' +
    '</div>').join('');

  return '<div class="desk">' +
    '<div class="desk-list">' + rail + '</div>' +
    '<div class="desk-pane">' +
      '<div class="to-line">' + outboxStatus(cur.status || 'pending_review') + ' To <b>' + escHtml(cur.to_email) + '</b> &middot; step ' +
        cur.step + ' (' + escHtml(cur.kind) + ') &middot; sends ' +
        outboxSendDate(cur) + '</div>' +
      outboxReadiness(cur) + '<div class="subject" data-user-content>' + escHtml(cur.subject || '(no subject)') + '</div>' +
      '<div class="body campaign-formatted-content" data-user-content>' + (cur.body_html?campaignSafeMailHtml(cur.body_html):escHtml(cur.body)) + '</div><div class="campaign-preview-files">'+campaignAttachmentLinks(outboxAttachments(cur))+'</div>' +
      '<div class="desk-actions">' +
        '<button class="btn btn-primary" onclick="outboxAct(\'' + cur.id + '\',\'approve\')">' +
          'Approve <kbd>A</kbd></button>' +
        '<button class="btn btn-secondary" onclick="outboxAct(\'' + cur.id + '\',\'reject\')">' +
          'Reject <kbd>R</kbd></button>' +
        '<span class="muted" style="font-size:12px;margin-left:auto">' +
          (i + 1) + ' of ' + items.length + '</span>' +
      '</div>' +
    '</div></div>';
}

function deskGo(n) {
  if (n < 0 || n >= _desk.items.length) return;
  _desk.i = n;
  document.getElementById('outbox-desk').innerHTML = renderDesk(_desk.items, n);
}

// Keyboard review. Ignored while typing into a field, so Settings still works.
document.addEventListener('keydown', e => {
  if (currentTab !== 'outbox' || e.metaKey || e.ctrlKey || e.altKey) return;
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
  const cur = _desk.items[_desk.i];
  const k = e.key.toLowerCase();
  if (k === 'j') { e.preventDefault(); deskGo(_desk.i + 1); }
  else if (k === 'k') { e.preventDefault(); deskGo(_desk.i - 1); }
  else if (k === 'a' && cur) { e.preventDefault(); outboxAct(cur.id, 'approve'); }
  else if (k === 'r' && cur) { e.preventDefault(); outboxAct(cur.id, 'reject'); }
});

async function outboxAct(id, action) {
  const data = await api('/api/outbox/' + encodeURIComponent(id) + '/' + action, {method: 'POST'});
  if (data && data.success) showToast(action === 'approve' ? 'Approved — will send on schedule.' : 'Rejected.', 'success');
  else showToast('Action failed.', 'error');
  loadOutbox();
}

async function outboxApproveAll() {
  if(outboxTaskItemId)return;
  const data = await api('/api/outbox/approve-all'+outboxScopeQuery(false), {method: 'POST'});
  if (data && data.success) showToast('Approved ' + data.approved + ' email(s).', 'success');
  else showToast('Approve-all failed.', 'error');
  loadOutbox();
}

async function sendingToggle(action) {
  const data = await api('/api/sending/' + action, {method: 'POST'});
  if (data && data.success) showToast(action === 'pause' ? 'Sending paused.' : 'Sending resumed.', 'success');
  else showToast('Failed.', 'error');
  loadOutbox();
}

function companyWebsite(company) {
  const candidate = company.website || (company.domain ? 'https://' + company.domain : '');
  try { const url = new URL(candidate); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; }
  catch { return ''; }
}

function companyEmailSummary(company) {
  const emails = company.contact_emails || [];
  if (!emails.length) return '<span class="muted">' + escHtml(tr('No email found yet')) + '</span>';
  const renderEmail = item => {
      let source = '';
      try { const url = new URL(item.source_url); if (['http:', 'https:'].includes(url.protocol)) source = url.href; } catch {}
      const validation = item.validation || {};
      const facts = [];
      if (validation.syntax === 'valid') facts.push(tr('Valid email format'));
      if (validation.domain === 'mail_domain_present') facts.push(tr('Mail domain present'));
      if (validation.domain === 'no_mail_domain') facts.push(tr('No mail domain found'));
      if (validation.domain === 'unknown') facts.push(tr('Mail domain check inconclusive'));
      if (validation.kind === 'role') facts.push(tr('General company inbox'));
      if (item.checked_at) facts.push(tr('Checked') + ': ' + item.checked_at + ' UTC');
      const details = facts.length ? '<details class="company-email-facts" onclick="event.stopPropagation()"><summary>Prüfdetails</summary><small class="muted">' + facts.map(escHtml).join(' · ') + '</small></details>' : '';
      return '<div class="company-email"><a href="mailto:' + encodeURIComponent(item.email) + '" onclick="event.stopPropagation()">' + escHtml(item.email) + '</a>' +
        '<span class="badge ' + (item.status === 'verified' ? 't-good' : 't-waiting') + '">' + escHtml(tr(item.status === 'verified' ? 'Verified' : 'Unverified')) + '</span>' +
        (source ? '<a class="company-evidence" href="' + escHtml(source) + '" target="_blank" rel="noopener" onclick="event.stopPropagation()">' + escHtml(tr('Source')) + '</a>' : '') + details + '</div>';
  };
  return '<div class="company-contact-details">' + renderEmail(emails[0]) +
    (emails.length > 1 ? '<details class="company-more-emails" onclick="event.stopPropagation()"><summary>' + (emails.length - 1) + (emails.length === 2 ? ' weitere E-Mail-Adresse' : ' weitere E-Mail-Adressen') + '</summary><div class="company-email-list" tabindex="0" aria-label="Weitere E-Mail-Adressen">' + emails.slice(1).map(renderEmail).join('') + '</div></details>' : '') + '</div>';
}

function companyContactSummary(company, includeEmails = true) {
  const phones = company.contact_phones || (company.phone ? [company.phone] : []);
  const site = companyWebsite(company);
  return (includeEmails ? companyEmailSummary(company) : '') + '<div class="company-contact-details">' +
    phones.map(phone => '<a href="tel:' + escHtml(phone.replace(/[^+0-9]/g, '')) + '" onclick="event.stopPropagation()">' + escHtml(phone) + '</a>').join('') +
    (site ? '<a href="' + escHtml(site) + '" target="_blank" rel="noopener" onclick="event.stopPropagation()">' + escHtml(tr('Website')) + '</a>' : '') +
    companySocialLinks(company) +
    (!phones.length && !site ? '<span class="muted">' + escHtml(tr('No phone or website')) + '</span>' : '') + '</div>';
}

function companySocialLinks(company) {
  const rows = (company.social_profiles || []).filter(row => {
    try { return ['https:','http:'].includes(new URL(row.url).protocol); } catch { return false; }
  });
  if (!rows.length) return '';
  return '<details class="company-social-profiles"><summary>' + escHtml(tr('Linked profiles')) + ' (' + rows.length + ')</summary><p class="muted">' + escHtml(tr('Linked by the company website; identity not independently verified.')) + '</p>' + rows.map(row =>
    '<div><a href="' + escHtml(row.url) + '" target="_blank" rel="noopener noreferrer">' + escHtml(row.network) + '</a> · <a href="' + escHtml(row.source_url) + '" target="_blank" rel="noopener noreferrer">' + escHtml(tr('Source')) + '</a></div>').join('') + '</details>';
}

async function requestCompanyEmailLookup(company) {
  const controller = new AbortController();
  const mode = document.getElementById('company-email-mode').value;
  const timeout = setTimeout(() => controller.abort(), mode === 'thorough' ? 85000 : 30000);
  try {
    const response = await fetch('/api/companies/' + encodeURIComponent(company.id) + '/lookup-contacts', {
      method: 'POST', signal: controller.signal, headers:{'Content-Type':'application/json'}, body:JSON.stringify({mode}),
    });
    const data = await response.json();
    if (!response.ok && data.status !== 'busy') return {status: 'failed'};
    return data;
  } catch { return {status: 'failed'}; }
  finally { clearTimeout(timeout); }
}

async function findCompanyContactDetails(index, button) {
  const company = _companies[index];
  if (!company || _companyBulk?.running) return;
  _companyLookupStates.set(company.id, 'running');
  button.disabled = true; button.textContent = tr('Looking up public contacts…');
  try {
    const data = await requestCompanyEmailLookup(company);
    _companyLookupStates.set(company.id, data.status);
    const messages = {found: 'Public email addresses found. They are not yet verified.',
      not_found: 'No public email found on the checked pages.', unreachable: 'The website could not be read. Please try again later.',
      no_website: 'No website available for this company.', busy: 'A contact lookup is already running. Please wait.'};
    showToast(tr(messages[data.status] || 'Could not load contact details.'), data.status === 'found' ? 'success' : 'error');
    if (currentTab === 'companies') await loadCompanies();
    if(data.diagnostics){renderLookupDiagnostics({items:[{company_id:company.id,name:company.name,status:data.status,diagnostic:{reasons:data.diagnostics},attempts:1}]});openCompanyEmailResults();}

  } catch { showToast(tr('Could not load contact details.'), 'error'); }
  finally { if (button.isConnected) { button.disabled = false; button.textContent = tr('Find public email'); } }
}

function scheduleCompanyFilter() {
  clearTimeout(_companyFilterTimer);
  _companyFilterTimer = setTimeout(changeCompanyFilters, 300);
}

function changeCompanyFilters() {
  if (_companyFilterHydrating || _companyBulk?.running) return;
  clearTimeout(_companyFilterTimer);
  companyFiltersChanged();
  _companyPage = 1;
  _companySelection.clear();
  updateCompanyToolbar();
  loadCompanies();
}

function resetCompanyFilters() {
  if (_companyBulk?.running) return;
  applyCompanyFilterState({});
  changeCompanyFilters();
}

function selectCompany(index, checked) {
  if (_companyBulk?.running) return;
  const company = _companies[index];
  if (!company) return;
  if (checked) _companySelection.set(company.id, company);
  else _companySelection.delete(company.id);
  updateCompanyToolbar();
}

function selectCompanyPage(checked) {
  if (_companyBulk?.running) return;
  _companies.forEach((company, index) => selectCompany(index, checked));
  document.querySelectorAll('.company-row-select').forEach((input, index) => {
    input.checked = _companySelection.has(_companies[index].id);
  });
}

function clearCompanySelection() {
  if (_companyBulk?.running) return;
  _companySelection.clear();
  document.querySelectorAll('.company-row-select').forEach(input => { input.checked = false; });
  updateCompanyToolbar();
}

let _companyCleaning = false;
let _companyCleanupBatch = null;
try { _companyCleanupBatch = sessionStorage.getItem('company-cleanup-batch'); } catch {}

function rememberCompanyCleanup(batch) {
  _companyCleanupBatch = batch;
  try {
    if (batch) sessionStorage.setItem('company-cleanup-batch', batch);
    else sessionStorage.removeItem('company-cleanup-batch');
  } catch {}
}

function companyCleanupMessage(message) {
  document.getElementById('company-cleanup-result').hidden = false;
  document.getElementById('company-cleanup-message').textContent = tr(message);
  document.getElementById('company-cleanup-undo').hidden = !_companyCleanupBatch;
}

async function cleanupCompanies(companyIds=null) {
  if (_companyCleaning || _companyBulk?.running) return;
  _companyCleaning = true;
  clearTimeout(_companyFilterTimer);
  updateCompanyToolbar();
  try {
    const response = await fetch('/api/companies/cleanup', companyIds?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({company_ids:companyIds})}:{method:'POST'});
    if (response.status === 409) {
      companyCleanupMessage('Please wait until the public email search has finished.');
      return;
    }
    if (!response.ok) throw new Error('cleanup failed');
    const result = await response.json();
    if (result.batch_id) rememberCompanyCleanup(result.batch_id);
    companyCleanupMessage(result.removed ? result.removed + ' companies removed from the list.' : 'No companies without contact details found.');
    if(companyIds)companyIds.forEach(id=>_companySelection.delete(id));else _companySelection.clear();
    _companyPage = 1;
    if(!companyIds)applyCompanyFilterState({});
    await loadCompanies();
  } catch {
    companyCleanupMessage('Could not clean up records. Please try again.');
  } finally {
    _companyCleaning = false;
    updateCompanyToolbar();
  }
}

async function undoCompanyCleanup() {
  if (!_companyCleanupBatch || _companyCleaning || _companyBulk?.running) return;
  _companyCleaning = true;
  updateCompanyToolbar();
  try {
    const result = await api('/api/companies/cleanup/' + encodeURIComponent(_companyCleanupBatch) + '/restore', {method: 'POST'});
    if (!result || typeof result.restored !== 'number') throw new Error('restore failed');
    rememberCompanyCleanup(null);
    companyCleanupMessage(result.restored + ' companies restored.');
    await loadCompanies();
  } catch {
    companyCleanupMessage('Could not restore records. Please try again.');
  } finally {
    _companyCleaning = false;
    updateCompanyToolbar();
  }
}

let companyEmailOpenedJob=null;
function openCompanyEmailResults(){
 const dialog=document.getElementById('company-email-results-dialog');
 if(!dialog.open)dialog.showModal();
}

// Keep action labels separate so status updates preserve their icons.
const companyActionPaths = {
 'company-select-page-button':'M4 4h16v16H4zM8 12l3 3 5-6',
 'company-clear-selection':'M6 6l12 12M18 6 6 18',
 'company-bulk-lookup':'M3 5h18v14H3zM3 6l9 7 9-7',
 'company-people-search':'M15 21v-2a5 5 0 0 0-10 0v2M10 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8M17 12h5M19.5 9.5v5',
 'company-delete-selected':'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',
 'company-cleanup':'m4 20 5-1L20 8l-4-4L4 16zM12 8l4 4M3 21h18',
 'company-email-results':'M4 3h12l4 4v14H4zM8 11h8M8 15h8',
 'company-people-results':'M15 21v-2a5 5 0 0 0-10 0v2M10 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8M17 15l2 2 3-4'
};
for (const [id,path] of Object.entries(companyActionPaths)) {
 const labels={'company-delete-selected':'Delete selected companies','company-select-page-button':'Select this page','company-clear-selection':'Clear selection','company-bulk-lookup':'Find public emails for selection','company-people-search':'Find people for selection','company-cleanup':'Clean up records','company-email-results':'E-Mail-Suchergebnis ansehen','company-people-results':'Personenvorschläge ansehen'};
 const button=document.getElementById(id),label=labels[id];
 button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+path+'"/></svg><span class="company-action-label"></span>';
 button.querySelector('span').textContent=label;
}
const companyActionsPanel=document.getElementById('company-actions-panel');
const companyActionsTrigger=document.getElementById('company-actions-trigger');
function positionCompanyActions(){
 const rect=companyActionsTrigger.getBoundingClientRect();
 companyActionsPanel.style.left=Math.max(8,Math.min(rect.left,innerWidth-companyActionsPanel.offsetWidth-8))+'px';
 companyActionsPanel.style.top=Math.max(8,Math.min(rect.bottom+8,innerHeight-companyActionsPanel.offsetHeight-8))+'px';
}
companyActionsPanel.addEventListener('toggle',event=>{
 const open=event.newState==='open';companyActionsTrigger.setAttribute('aria-expanded',String(open));
 if(open)positionCompanyActions();
});
companyActionsPanel.addEventListener('click',event=>{
 if(event.target.closest('button:not(:disabled)'))companyActionsPanel.hidePopover();
});
companyActionsPanel.addEventListener('keydown',event=>{
 if(event.key==='Escape'){companyActionsPanel.hidePopover();companyActionsTrigger.focus();}
});
window.addEventListener('resize',()=>{if(companyActionsPanel.matches(':popover-open'))positionCompanyActions();});

function updateCompanyToolbar() {
  document.getElementById('company-report-action').disabled = !_companySelection.size || _companySelection.size>20;
  window.updateCompanyReportAction?.();
  const running = !!_companyBulk?.running;
  const busy = running || _companyCleaning;
  document.getElementById('company-people-search').disabled = busy || !_companySelection.size || !!window.peopleSearchRunning;
  document.getElementById('company-delete-selected').disabled = busy || !_companySelection.size || !!window.peopleSearchRunning;
  document.getElementById('company-cleanup').disabled = busy || !!window.peopleSearchRunning;
  document.querySelector('#company-cleanup .company-action-label').textContent = tr(_companyCleaning ? 'Cleaning up…' : 'Clean up records');
  document.getElementById('company-cleanup-undo').disabled = busy;
  document.getElementById('company-selection-count').textContent = tr(_companySelection.size + ' selected');
  document.getElementById('company-clear-selection').disabled = busy || !_companySelection.size;
  document.getElementById('company-select-page-button').disabled = busy || !_companies.length;
  document.getElementById('company-email-mode').disabled = busy;
  if (running && _companyBulk.mode) document.getElementById('company-email-mode').value = _companyBulk.mode;
  document.getElementById('company-bulk-lookup').disabled = busy || !_companySelection.size;
  document.querySelector('#company-bulk-lookup .company-action-label').textContent = tr(running ? 'Searching public emails…' : 'Find public emails for selection');
  document.getElementById('company-bulk-stop').hidden = !running;
  document.getElementById('company-bulk-stop').disabled = !!_companyBulk?.stopped;
  document.querySelectorAll('#company-filters input, #company-filters select, #company-reset, .company-row-select, #company-view-select, #company-view-name, #company-view-save').forEach(el => { el.disabled = busy; });
  Object.values(companyMulti).forEach(ts=>busy?ts.disable():ts.enable());
  document.getElementById('company-view-delete').disabled=busy || !document.getElementById('company-view-select').value;
  renderCompanyFilterChips();
  document.querySelectorAll('.company-row-select').forEach(input => {
    input.closest('tr').classList.toggle('company-selected', input.checked);
  });
  const all = document.getElementById('company-select-page');
  if (all) {
    const selected = _companies.filter(c => _companySelection.has(c.id)).length;
    all.checked = !!_companies.length && selected === _companies.length;
    all.indeterminate = selected > 0 && selected < _companies.length;
    all.disabled = busy;
  }
  const resultButton=document.getElementById('company-email-results');
  resultButton.hidden=!_companyBulk;
  resultButton.querySelector('.company-action-label').textContent=running?'E-Mail-Suche läuft – Fortschritt':'E-Mail-Suchergebnis ansehen';
  const progress = document.getElementById('company-bulk-progress');
  progress.hidden = !_companyBulk;
  if (_companyBulk) {
    const b = _companyBulk;
    const state = b.running ? (b.stopped ? 'Stopping after current lookups…' : 'Searching public emails…') : (b.stopped ? 'Search stopped.' : 'Public email search finished.');
    progress.textContent = tr(state) + ' ' + b.done + '/' + b.total + ' · ' +
      b.found + ' ' + tr('with email') + ' · ' + b.missing + ' ' + tr('without email') + ' · ' +
      b.skipped + ' ' + tr('without website') + ' · ' + b.failed + ' ' + tr('unavailable or failed');
  }
}

let _companyJobPoll = null;

function applyCompanyEmailJob(job) {
  if (!job) return;
  renderLookupDiagnostics(job);
  _companyBulk = {id: job.id, mode: job.mode || 'quick', running: ['queued', 'running'].includes(job.status),
    stopped: !!job.stop_requested || job.status === 'stopped', total: job.total, done: job.done,
    found: job.counts.found, missing: job.counts.not_found,
    skipped: job.counts.no_website, failed: job.counts.failed};
  (job.items || []).forEach(item => _companyLookupStates.set(item.company_id, item.status));
  updateCompanyToolbar();
  if (_companyBulk.running && companyEmailOpenedJob!==job.id && currentTab==='companies' && !document.querySelector('dialog[open]')) {
    companyEmailOpenedJob=job.id;openCompanyEmailResults();
  }
  clearTimeout(_companyJobPoll);
  if (_companyBulk.running) _companyJobPoll = setTimeout(pollCompanyEmailJob, 1200);
}

async function pollCompanyEmailJob() {
  const wasRunning = _companyBulk?.running;
  const job = await api('/api/company-email-jobs/latest');
  if (!job) {
    // A temporary network failure does not cancel the server-side job.
    if (wasRunning) _companyJobPoll = setTimeout(pollCompanyEmailJob, 3000);
    return;
  }
  applyCompanyEmailJob(job);
  if (wasRunning && !_companyBulk.running && currentTab === 'companies' && !companyDrill) await loadCompanies();
}

async function findSelectedCompanyEmails(companyIds=null) {
  const ids=companyIds||[..._companySelection.keys()];
  if (_companyCleaning || _companyBulk?.running || !ids.length) return;
  clearTimeout(_companyFilterTimer);
  const job = await api('/api/company-email-jobs', {method: 'POST',
    body: JSON.stringify({company_ids: ids, mode:document.getElementById('company-email-mode').value})});
  if (!job?.id) {
    showToast(tr('Could not start public email search. Please refresh.'), 'error');
    await pollCompanyEmailJob();
    return;
  }
  applyCompanyEmailJob(job);
  companyEmailOpenedJob=job.id;openCompanyEmailResults();
  renderCompanyPage();
}

async function stopCompanyEmailSearch() {
  if (!_companyBulk?.running || !_companyBulk.id) return;
  const job = await api('/api/company-email-jobs/' + encodeURIComponent(_companyBulk.id) + '/stop', {method: 'POST'});
  if (job?.id) applyCompanyEmailJob(job);
}

function goCompanyPage(page) {
  if (!_companyPageData || page < 1 || page > _companyPageData.pages) return;
  _companyPage = page;
  loadCompanies();
  document.getElementById('companies').scrollIntoView({block: 'start'});
}

async function loadCompanies() {
  if (typeof refreshPeopleSearch === 'function') refreshPeopleSearch();
  if (_companyCleanupBatch && document.getElementById('company-cleanup-result').hidden) {
    companyCleanupMessage('You can undo the last cleanup.');
  }
  if (!_companyBulk) await pollCompanyEmailJob();
  companyDrill = false;
  _companyDetailIndex = null;
  document.getElementById('company-list-tools').hidden = false;
  const el = document.getElementById('companies-list');
  const request = ++_companyRequest;
  const params = new URLSearchParams({page: _companyPage});
  for (const [key,value] of Object.entries(companyFilterState())) {
    if(Array.isArray(value)) value.forEach(item=>params.append(key,item));
    else if(value)params.set(key,value);
  }
  el.setAttribute('aria-busy', 'true');
  const data = await api('/api/companies/page?' + params);
  if (request !== _companyRequest || companyDrill) return;
  el.removeAttribute('aria-busy');
  if (!data || !Array.isArray(data.items)) {
    _companies = [];
    _companyPageData = null;
    el.innerHTML = '<p role="alert">' + escHtml(tr('Could not load companies. Please refresh.')) + '</p>';
    updateCompanyToolbar();
    return;
  }
  _companyPageData = data;
  _companyPage = data.page;
  _companies = data.items;
  _companies.forEach(company => { if (_companySelection.has(company.id)) _companySelection.set(company.id, company); });
  refreshCompanyFilterControls(data);
  await loadCompanyViews();
  renderCompanyPage();
}

function renderCompanyPage() {
  if (!_companyPageData) return;
  const el = document.getElementById('companies-list');
  const data = _companyPageData;
  const count = data.total ? ((_companyPage - 1) * 30 + 1) + '–' + Math.min(_companyPage * 30, data.total) : '0–0';
  let html = '<div class="company-results-summary" role="status">' + escHtml(tr(count + ' of ' + data.total + ' companies')) +
    '<span>' + escHtml(tr('30 companies per page')) + '</span></div>';
  if (!_companies.length) {
    const filtered = Object.values(companyFilterState()).some(value=>Array.isArray(value)?value.length:!!value);
    el.innerHTML = html + '<div class="company-empty"><h3>' + escHtml(tr(filtered ? 'No matching companies' : 'No companies yet')) + '</h3><p>' +
      escHtml(tr(filtered ? 'Change the filters or reset them to see all companies.' : 'Run a discovery search to find companies.')) + '</p></div>';
    updateCompanyToolbar();
    return;
  }
  html += '<div class="table-card company-table-wrap"><table class="companies-table"><caption class="sr-only">' + escHtml(tr('Companies')) + '</caption>' +
    '<colgroup><col class="company-select-col"><col class="company-name-col"><col class="company-email-col"><col class="company-details-col"><col class="company-industry-col"><col class="company-location-col"><col class="company-people-col"></colgroup>' +
    '<thead><tr><th scope="col"><label class="company-checkbox-label"><input id="company-select-page" type="checkbox" onchange="selectCompanyPage(this.checked)" aria-label="' + escHtml(tr('Select all on this page')) + '"></label></th>' +
    ['Company', 'Email', 'Phone / website', 'Industry', 'Location', 'Actions'].map(label => '<th scope="col">' + escHtml(tr(label)) + '</th>').join('') + '</tr></thead><tbody>';
  _companies.forEach((company, i) => {
    const lookup = _companyLookupStates.get(company.id);
    const busy = _companyBulk?.running || lookup === 'running';
    html += '<tr' + (_companySelection.has(company.id) ? ' class="company-selected"' : '') + '><td class="company-select-cell"><label class="company-checkbox-label"><input class="company-row-select" type="checkbox" ' +
      (_companySelection.has(company.id) ? 'checked ' : '') + 'onchange="selectCompany(' + i + ',this.checked)" aria-label="' + escHtml(tr('Select company') + ': ' + company.name) + '"></label></td>' +
      '<td class="company-identity"><button class="company-name-button" data-company-profile="' + escHtml(company.id) + '" type="button">' + escHtml(company.name) + '</button>' +
      '<small class="muted">' + escHtml(company.company_size || tr('Company size unknown')) + '</small></td>' +
      '<td class="company-email-cell" data-label="' + escHtml(tr('Email')) + '">' + companyEmailSummary(company) +
      (companyWebsite(company) ? '<button class="btn btn-secondary btn-sm company-lookup" onclick="findCompanyContactDetails(' + i + ',this)"' + (busy ? ' disabled' : '') + '>' + escHtml(tr(lookup === 'running' ? 'Looking up public contacts…' : 'Find public email')) + '</button>' : '') + '</td>' +
      '<td class="company-contact-cell" data-label="' + escHtml(tr('Phone / website')) + '">' + companyContactSummary(company, false) + '</td>' +
      '<td class="company-industry" data-label="' + escHtml(tr('Industry')) + '">' + escHtml(company.industry) + '</td><td class="company-location" data-label="' + escHtml(tr('Location')) + '">' + escHtml(company.location) + '</td>' +
      '<td data-label="'+escHtml(tr('Actions'))+'"><button type="button" class="btn btn-secondary btn-sm company-row-actions-trigger" data-company-row-actions="'+escHtml(company.id)+'" aria-haspopup="menu" aria-expanded="false" aria-label="'+escHtml(tr('Actions')+': '+company.name)+'">'+escHtml(tr('Actions'))+'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></button></td></tr>';
  });
  const pages = [...new Set([1, _companyPage - 1, _companyPage, _companyPage + 1, data.pages])].filter(n => n >= 1 && n <= data.pages).sort((a, b) => a - b);
  html += '</tbody></table></div><div class="company-pagination" role="navigation" aria-label="' + escHtml(tr('Company pages')) + '"><span>' + escHtml(tr('Page ' + _companyPage + ' of ' + data.pages)) + '</span><div>' +
    '<button class="btn btn-secondary btn-sm" onclick="goCompanyPage(' + (_companyPage - 1) + ')"' + (_companyPage === 1 ? ' disabled' : '') + '>' + escHtml(tr('Previous')) + '</button>';
  pages.forEach((page, index) => {
    if (index && page > pages[index - 1] + 1) html += '<span class="company-page-gap">…</span>';
    html += '<button class="btn btn-secondary btn-sm company-page-number" onclick="goCompanyPage(' + page + ')" aria-label="' + escHtml(tr('Page') + ' ' + page) + '"' + (page === _companyPage ? ' aria-current="page"' : '') + '>' + page + '</button>';
  });
  html += '<button class="btn btn-secondary btn-sm" onclick="goCompanyPage(' + (_companyPage + 1) + ')"' + (_companyPage === data.pages ? ' disabled' : '') + '>' + escHtml(tr('Next')) + '</button></div></div>';
  el.innerHTML = html + (_companies.some(company => company.source === 'discover:geoapify') ? discoveryAttribution() : '');
  el.querySelectorAll('[data-company-profile]').forEach(button => { button.onclick = () => openCompanyProfile(button.dataset.companyProfile); });
  updateCompanyToolbar();
}

async function showCompanyContacts(index) {
  const company = _companies[index];
  if (!company) return;
  companyDrill = true;
  ++_companyRequest;
  document.getElementById('company-list-tools').hidden = true;
  _companyDetailIndex = index;
  const el = document.getElementById('companies-list');
  const data = await api('/api/companies/' + encodeURIComponent(company.id) + '/contacts');
  let html = '<div class="card"><h2>' + escHtml(company.name) + ' — ' + escHtml(tr('Contacts')) + '</h2>' +
    '<button class="btn btn-secondary btn-sm" onclick="loadCompanies()" style="margin-bottom:16px">&larr; Back to Companies</button>' + companyContactSummary(company) + '<div class="contact-detail-actions"><button class="btn btn-primary btn-sm" onclick="openContactEditor(' + index + ')">Kontakt hinzufügen</button><button class="btn btn-secondary btn-sm" onclick="openContactEditor(' + index + ',true)">Als Firmenkontakt übernehmen</button><button class="btn btn-secondary btn-sm" onclick="startPeopleSearch([_companies[' + index + '].id])">Ansprechpersonen suchen</button></div>';
  if (!data || !data.length) {
    html += '<p style="color:var(--text-3);font-size:13px">No contacts found at this company yet.</p></div>';
  } else {
    html += '<div class="table-card"><table><thead><tr><th>Name</th><th>Title</th><th>Email</th><th>Phone</th><th>LinkedIn</th><th>Status</th><th>Source</th></tr></thead><tbody>';
    for (const p of data) {
      const emailIcon = emailTag(p);
      const phoneIcon = p.phone_verified ? ' <span class="verified">&#10003;</span>' : '';
      html += '<tr><td>' + escHtml(p.contact_type === 'company' ? p.company : [p.first_name, p.last_name].filter(Boolean).join(' ')) + (p.contact_type === 'company' ? ' <small class="muted">Firmenkontakt</small>' : '') + '</td>' +
        '<td>' + escHtml(p.title) + '</td><td>' + escHtml(p.email) + emailIcon + '</td>' +
        '<td>' + escHtml(p.phone) + phoneIcon + '</td>' +
        '<td>' + (p.linkedin_url ? '<a href="' + escHtml(p.linkedin_url) + '" target="_blank" rel="noopener">Profile</a>' : '') + '</td>' +
        '<td>' + badge(p.status) + '</td><td class="muted">' + contactSourceHtml(p) + '</td></tr>';
    }
    html += '</tbody></table></div></div>';
  }
  el.innerHTML = html + (company.source === 'discover:geoapify' ? discoveryAttribution() : '');
}

async function submitFeedback(entityType, entityId, promptText) {
  const comment = prompt(promptText || 'Add your feedback:');
  if (!comment) return;
  const data = await api('/api/feedback', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({entity_type: entityType, entity_id: entityId, comment: comment})
  });
  if (data && data.success) showToast('Notiz gespeichert.', 'success');
  else showToast((data && data.message) || 'Could not save feedback.', 'error');
}

function fbProspect(i) {
  const p = _prospects[i];
  if (p) submitFeedback('contact', p.id, 'Feedback on this contact:');
}

function fbCampaign(i) {
  const c = _campaigns[i];
  if (c) submitFeedback('campaign', c.id, 'Leave feedback on this campaign:');
}

async function loadProspects() {
  return loadContactWorkspace();
}

async function loadCampaigns() {
  return loadCampaignWorkspace();
}

let conversationRows = [];
async function loadConversations() {
  if(typeof loadOpportunities==='function')loadOpportunities();
  const el = document.getElementById('conversations-list');
  const data = await api('/api/conversations');
  if (!data) { el.innerHTML = offlineState(); return; }
  conversationRows = data;
  if (!data.length) {
    el.innerHTML = emptyState('&#9737;', 'No conversations yet',
      'No replies have been imported yet. Replies can already be in your mailbox even when this view is empty.');
    return;
  }
  const groups = new Map();
  data.forEach((c, i) => {
    const key = c.campaign_id || '';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push({c, i});
  });
  el.innerHTML = [...groups.entries()].map(([id, rows]) => {
    const title = rows[0].c.campaign_name || tr(id ? 'Campaign unavailable' : 'Without campaign');
    return '<section class="conversation-group"><div class="conversation-group-heading"><h3 data-user-content>' + escHtml(title) +
      '</h3><span class="muted">' + rows.length + '</span></div>' + rows.map(({c,i}) => {
        const name = [c.first_name,c.last_name].filter(Boolean).join(' ') || c.prospect_email || tr('Unknown');
        return '<button type="button" class="conversation-row" onclick="openConversation(' + i + ')">' +
          '<span class="conversation-row-heading"><strong data-user-content>' + escHtml(name) + '</strong>' + badge(c.status) + '</span>' +
          '<span class="conversation-row-detail" data-user-content>' + escHtml([c.company,c.prospect_email].filter(Boolean).join(' · ')) + '</span>' +
          '<span class="conversation-row-footer"><span>' + formatDate(c.updated_at) + '</span><span>' + escHtml(tr('Open conversation')) + ' ↗</span></span></button>';
      }).join('') + '</section>';
  }).join('');
}
function openConversation(index) {
  const c = conversationRows[index];
  if (!c) return;
  if(typeof loadConversationOutcome==='function')loadConversationOutcome(c.id);
  document.getElementById('conversation-dialog-title').textContent = [c.first_name,c.last_name].filter(Boolean).join(' ') || c.prospect_email || tr('Unknown');
  document.getElementById('conversation-dialog-meta').textContent = [c.campaign_name || tr(c.campaign_id ? 'Campaign unavailable' : 'Without campaign'), c.prospect_email].filter(Boolean).join(' · ');
  document.getElementById('conversation-dialog-thread').innerHTML = (c.thread || []).map(msg =>
    '<div class="thread-msg ' + (msg.sender === 'harvey' ? 'sent' : 'received') + '"><div class="sender">' +
    escHtml(msg.sender === 'harvey' ? 'Siveron' : tr('Contact')) + ' · ' + formatDate(msg.timestamp) +
    '</div><div data-user-content>' + escHtml(msg.content || '') + '</div></div>').join('') ||
    '<p>' + escHtml(tr('No messages in this thread yet.')) + '</p>';
  document.getElementById('conversation-dialog').showModal();
}

async function loadActivity() {
  const el = document.getElementById('activity-list');
  const data = await api('/api/activity');
  if (!data) { el.innerHTML = offlineState(); return; }
  if (!data.length) {
    el.innerHTML = emptyState('&#9202;', 'No activity yet',
      'Siveron hasn\'t taken any actions. Every prospect found, email written, and reply handled will appear here the moment it happens.');
    return;
  }
  let html = '<div class="activity-feed">';
  for (const a of data) {
    html += '<div class="activity-item"><span class="time">' + formatDate(a.created_at) + '</span>' +
      '<span class="agent">' + escHtml(a.agent) + '</span>' +
      '<span class="action">' + escHtml(a.action_type) + '</span></div>';
  }
  el.innerHTML = html + '</div>';
}

// ── Init & live refresh ──

loadToday();
loadSetupStatus();
loadRuns();
loadTodayActivity();
loadHarveyStatus();

// Agent status: quick poll
setInterval(loadHarveyStatus, 8000);

// Nav counts stay live wherever you are, so "something needs me" is visible
// from any tab without polling that tab's contents.
setInterval(async () => {
  if (document.hidden || currentTab === 'today') return;
  const data = await api('/api/today');
  if (!data) return;
  navCount('nav-today', (data.work_total||0)+(data.items || []).filter(i => i.tone !== 'good').length);
  navCount('nav-outbox', (data.stats || {}).outbox_pending || 0);
}, 20000);

// Data tabs: auto-refresh live views without clobbering anything in progress.
// Refresh Outbox only with no pending decisions, preserving the review desk.
// Settings and help are excluded because their contents may be mid-edit.
setInterval(() => {
  if (document.hidden) return;
  switch (currentTab) {
    case 'today': loadToday(); loadRuns(); loadTodayActivity(); break;
    case 'companies': if (!companyDrill && !_companyBulk?.running && !document.activeElement.closest('#company-filters, #company-active-filters, #company-actions-panel, #company-row-actions-menu, .company-saved-views, .companies-table')) loadCompanies(); break;
    case 'prospects': if (!document.querySelector('#contact-actions-menu:popover-open, dialog[open]') && !document.activeElement.closest('.crm-contact-table, #crm-contact-search, #crm-block-filter')) loadProspects(); break;
    case 'campaigns': loadCampaigns(); break;
    case 'conversations': loadConversations(); break;
    case 'activity': loadActivity(); break;
    case 'usage': loadUsage(); break;
    case 'controls': loadLogs(); break;
    case 'outbox': if (!document.activeElement.closest('#outbox-actions, .desk-actions, .outbox-readiness details[open]')) loadOutbox(); break;
  }
}, 15000);


let sendingSettingsRevision=null, sendingSettingsBusy=false;
async function loadSendingSettings(){
 const message=document.getElementById('sending-settings-message');
 try{
  const data=await contactRequest('/api/settings/sending');
  sendingSettingsRevision=data.revision;
  document.getElementById('sending-enabled').checked=data.enabled;
  document.getElementById('sending-daily-limit').value=data.max_daily_sends;
  document.querySelectorAll('#sending-settings-form input,#sending-settings-save').forEach(el=>el.disabled=!!data.agent_running);
  message.textContent=data.agent_running?'Der Agent läuft. Bitte unter Steuerung anhalten, um die Versandeinstellungen zu ändern.':'';
 }catch(error){sendingSettingsRevision=null;message.textContent='Versandeinstellungen konnten nicht geladen werden. Bitte die Seite neu laden.';}
}
async function saveSendingSettings(){
 if(sendingSettingsBusy||!sendingSettingsRevision)return;
 const form=document.getElementById('sending-settings-form');if(!form.reportValidity())return;
 const button=document.getElementById('sending-settings-save'),message=document.getElementById('sending-settings-message');
 sendingSettingsBusy=true;button.disabled=true;button.textContent='Wird gespeichert …';
 try{
  const result=await contactRequest('/api/settings/sending',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:document.getElementById('sending-enabled').checked,max_daily_sends:Number(document.getElementById('sending-daily-limit').value),revision:sendingSettingsRevision})});
  sendingSettingsRevision=result.revision;
  message.textContent='Gespeichert. Die Werte gelten beim nächsten Agentenstart. Es wurde kein Versand gestartet.';
 }catch(error){message.textContent=error.message;}
 finally{sendingSettingsBusy=false;button.disabled=false;button.textContent='Versandeinstellungen speichern';}
}

let companyProfileRequest = 0, companyProfileFields = [], companyProfileId = null, companyFieldSaving = false;
async function openCompanyProfile(companyId) {
 const request = ++companyProfileRequest, dialog = document.getElementById('company-profile-dialog');
 const title = document.getElementById('company-profile-title'), body = document.getElementById('company-profile-body');
 companyProfileId = companyId; companyProfileFields = [];
 title.textContent = tr('Company profile'); body.textContent = tr('Loading...');
 if (!dialog.open) dialog.showModal();
 try {
  const response = await fetch('/api/companies/' + encodeURIComponent(companyId) + '/profile');
  if (!response.ok) throw new Error();
  const {company:c, contacts, field_candidates=[]} = await response.json();
  if (request !== companyProfileRequest || !dialog.open) return;
  companyProfileFields=field_candidates;
  title.textContent = c.name;
  body.innerHTML = '<dl class="company-profile-facts">'+[['Domain',c.domain],['Industry',c.industry],['Location',c.location],['Size',c.company_size]].map(([label,value])=>'<div><dt>'+escHtml(tr(label))+'</dt><dd data-user-content>'+escHtml(value||'—')+'</dd></div>').join('')+'</dl>'+companyContactSummary(c)+companyFieldReviewHtml()+'<h3>'+escHtml(tr('Contacts'))+' ('+contacts.length+')</h3>'+
   (contacts.length ? '<ul class="company-profile-contacts">'+contacts.map(p=>'<li><strong data-user-content>'+escHtml(p.contact_type==='company'?p.company:[p.first_name,p.last_name].filter(Boolean).join(' '))+'</strong><p data-user-content>'+escHtml([p.title,p.email,p.phone].filter(Boolean).join(' · '))+'</p></li>').join('')+'</ul>':'<p>'+escHtml(tr('No contacts found at this company yet.'))+'</p>');
 } catch {
  if(request===companyProfileRequest && dialog.open)body.innerHTML='<p role="alert">'+escHtml(tr('Company profile unavailable. Close and try again.'))+'</p>';
 }
}

async function deleteSelectedCompanies(companyIds=null) {
 const ids=companyIds||[..._companySelection.keys()];
 if (_companyCleaning || _companyBulk?.running || window.peopleSearchRunning || !ids.length) return;
 const question=ids.length===1?tr('Delete company?')+'\n'+(_companies.find(company=>company.id===ids[0])?.name||ids[0]):tr('Delete selected companies?')+' ('+ids.length+')';
 if (!confirm(question+'\n'+tr('You can undo this removal. Linked contacts, campaigns and sent messages are retained.'))) return;
 _companyCleaning = true; updateCompanyToolbar();
 try {
  const response = await fetch('/api/companies/remove-selected', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({company_ids:ids})});
  if(response.status===409){companyCleanupMessage('Please wait until the public email search has finished.');return;}
  if(!response.ok)throw new Error();
  const result=await response.json();
  if(result.batch_id)rememberCompanyCleanup(result.batch_id);
  ids.forEach(id=>_companySelection.delete(id));_companyPage=1;
  companyCleanupMessage(tr('Companies removed:')+' '+result.removed);
  await loadCompanies();
 } catch {companyCleanupMessage('Could not remove companies. Please try again.');}
 finally {_companyCleaning=false;updateCompanyToolbar();}
}

function companyFieldReviewHtml(){
 if(!companyProfileFields.length)return '';
 const labels={phone:'Phone',location:'Location',email:'Email'};
 return '<section class="company-field-review"><h3>'+escHtml(tr('Review found details'))+'</h3><p>'+escHtml(tr('Website declarations are suggestions. Check the source before adopting.'))+'</p><div id="company-field-error" role="alert"></div>'+companyProfileFields.map(f=>'<article><strong>'+escHtml(tr(labels[f.field]||f.field))+'</strong><p data-user-content>'+escHtml(f.value)+'</p><small>'+escHtml(tr('Current value:'))+' <span data-user-content>'+escHtml(f.current_value||'—')+'</span></small><p class="muted" data-user-content>'+escHtml([f.entity,f.contact_label].filter(Boolean).join(' · '))+'</p><a href="'+escHtml(f.source_url)+'" target="_blank" rel="noopener">'+escHtml(tr('Source'))+'</a> · <small>'+escHtml(tr('Checked'))+': '+escHtml(formatDate(f.checked_at+'Z'))+'</small><div class="company-field-actions"><button class="btn btn-secondary btn-sm" type="button" data-field-id="'+escHtml(f.id)+'" data-field-action="accept">'+escHtml(tr('Adopt detail'))+'</button><button class="btn btn-secondary btn-sm" type="button" data-field-id="'+escHtml(f.id)+'" data-field-action="dismiss">'+escHtml(tr('Dismiss'))+'</button></div></article>').join('')+'</section>';
}
document.getElementById('company-profile-body').addEventListener('click',async event=>{
 const button=event.target.closest('[data-field-action]');if(!button||companyFieldSaving)return;
 const candidate=companyProfileFields.find(f=>f.id===button.dataset.fieldId);if(!candidate)return;
 if(button.dataset.fieldAction==='accept'&&candidate.current_value&&candidate.current_value!==candidate.value&&!confirm(tr('Replace the current company value with this suggestion?')))return;
 companyFieldSaving=true;const companyId=companyProfileId;
 document.querySelectorAll('[data-field-action]').forEach(b=>b.disabled=true);
 try{
  const response=await fetch('/api/company-field-candidates/'+encodeURIComponent(candidate.id)+'/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:button.dataset.fieldAction,expected_value:candidate.current_value})});
  if(!response.ok)throw new Error();
  if(document.getElementById('company-profile-dialog').open&&companyProfileId===companyId)await openCompanyProfile(companyId);
 }catch{const error=document.getElementById('company-field-error');if(error)error.textContent=tr('Detail changed or unavailable. Close and reopen the profile before trying again.');}
 finally{companyFieldSaving=false;document.querySelectorAll('[data-field-action]').forEach(b=>b.disabled=false);}
});

// Native dialog Escape restores focus without interrupting the server-side search.
document.getElementById('discovery-details').addEventListener('close', () => {
  const trigger = _discoveryDetailFocus?.isConnected ? _discoveryDetailFocus :
    document.querySelector('#discover-progress button');
  trigger?.focus();
});

window.addEventListener('harvey-language-changed', () => {
  if (_discoveryProgressView) renderDiscoveryProgress(_discoveryProgressView);
});
