import {el as node, textBlock} from '/shared/client.js';
// Counterline's own pages: a provider support site seen from the customer's side. The help center, the
// case list, a case with its chat, quick actions, offers and identity form, the provider's commitments
// with their reports, and settings. The shared Host supplies only a fixed Agent MCP connection; every
// value shown comes from a Counterline read, and nothing is computed or stored here.
//
// Writes follow the shared rules: the version observed when the view opened is sent with the write, an
// unchanged retry reuses its request_id, and a stale view reports the conflict instead of overwriting.
// Binding steps stay explicit: accepting an offer is two clicks (summary, then confirm), identity data is
// sent only for the fields ticked, and a chat message never accepts anything.

const el = (name, attrs, ...children) => node(name, attrs, ...children.flat().filter(c => c !== false && c !== undefined && c !== null));

const css = new CSSStyleSheet();
css.replaceSync(`
body[data-app=counterline] .content{padding:20px 24px;max-width:1240px}
body[data-app=counterline] .brand h1{font-size:20px;white-space:nowrap}
body[data-app=counterline] .content button{white-space:nowrap}
.case-head{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.case-head h2{font-size:22px;margin:0}.case-head .actions{margin-left:auto}
@media (max-width:820px){body[data-app=counterline] .content{padding:14px}.case-head h2{font-size:18px}.turn{max-width:92%}}
.split{display:grid;grid-template-columns:minmax(220px,300px) 1fr;gap:18px;align-items:start}
@media (max-width:820px){.split{grid-template-columns:1fr}}
.case-row{display:block;width:100%;text-align:left;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px;background:#fff}
.case-row[aria-current=true]{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.case-row small{display:block;color:var(--muted)}
.panel{border:1px solid var(--line);border-radius:12px;background:#fff;padding:14px 16px;margin-bottom:14px}
.panel h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 10px}
.chat{display:flex;flex-direction:column;gap:8px;max-height:460px;overflow-y:auto;padding:4px}
.turn{max-width:78%;padding:8px 12px;border-radius:14px;background:#f1f3f7;white-space:pre-wrap}
.turn.customer{align-self:flex-end;background:#e4eefc}
.turn small{display:block;font-size:11px;color:var(--muted);margin-top:4px}
.quick{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.quick button{border-radius:999px;font-size:12px;padding:5px 11px}
.composer{display:flex;gap:8px}.composer textarea{flex:1;min-height:42px}
.offer{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:8px}
.offer.accepted{border-color:#2e8b47;background:#f2fbf4}.offer.unavailable,.offer.declined,.offer.expired{opacity:.65}
.offer .row{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}.offer .row strong{font-size:15px}
.chip{display:inline-block;white-space:nowrap;border-radius:999px;padding:1px 9px;font-size:11px;background:#eef2f8;color:#4e5d74}
.chip.accepted,.chip.reported_performed{background:#e5f6ea;color:#22693a}.chip.pending,.chip.presented,.chip.escalated,.chip.open{background:#fff6d6;color:#7a5c00}
.chip.overdue,.chip.contested,.chip.revoked,.chip.condition_missed{background:#fde4e4;color:#932222}
.idform{display:grid;grid-template-columns:auto 1fr;gap:6px 10px;align-items:center}.idform input[type=checkbox]{width:auto}
.notice{font-size:12px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px}
table.reports{width:100%;border-collapse:collapse;font-size:12px}table.reports td,table.reports th{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left}
`);
document.adoptedStyleSheets = [...document.adoptedStyleSheets, css];
document.body.dataset.app = 'counterline';

// ---- transport ----
let csrf = '', tools = [], version = null, busy = false;
async function request(url, method = 'GET', value) {
  const r = await fetch(url, {method, headers: method === 'POST' ? {'Content-Type': 'application/json', 'X-Pale-CSRF': csrf} : {},
    ...(method === 'POST' ? {body: JSON.stringify(value)} : {})});
  const out = await r.json();
  if (!r.ok) throw Error(out.error || 'Request failed');
  return out;
}
const MESSAGES = {stale_version: 'This case changed since the page loaded. Refresh before trying again.',
  permission_denied: 'This operation is not allowed for the current account and policy.'};
async function call(name, args = {}) {
  const r = await request('/api/call', 'POST', {name, arguments: args});
  if (!['ok', 'committed'].includes(r.status)) throw Object.assign(Error(MESSAGES[r.status] || r.message || r.status), {code: r.status});
  if (r.version) version = r.version;
  return r;
}
const has = name => tools.some(t => t.name === 'counterline.' + name);
const schemaOf = name => tools.find(t => t.name === 'counterline.' + name)?.inputSchema || {properties: {}};
const pending = new Map();
async function write(name, args, viewVersion) {
  if (busy) throw Error('An operation is already in progress.');
  const payload = {...args, expected_version: viewVersion}, key = name + JSON.stringify(payload);
  if (!pending.has(key)) pending.set(key, 'web-' + crypto.randomUUID());
  busy = true;
  try { const r = await call('counterline.' + name, {...payload, request_id: pending.get(key)}); pending.delete(key); return r; } finally { busy = false; }
}

// ---- presentation helpers ----
const words = s => String(s ?? '').replace(/_/g, ' ');
const chip = (text, kind = text) => el('span', {class: 'chip ' + kind}, words(text));
const money = v => v ? (v.amount_minor / 100).toLocaleString('en-US', {minimumFractionDigits: 2}) + (v.currency === 'USD' ? ' USD' : ' ' + v.currency) : '';
const when = t => t ? t.slice(0, 16).replace('T', ' ') : '—';
const panel = (title, ...body) => el('section', {class: 'panel'}, el('h3', {}, title), ...body);

// ---- shell ----
const status = el('p', {role: 'status', 'aria-live': 'polite', id: 'status'}, 'Connecting…');
const nav = el('nav', {'aria-label': 'Counterline navigation'});
const brandName = el('strong', {}, 'Support');
const content = el('div', {class: 'content', id: 'content'});
document.querySelector('#app').replaceChildren(el('div', {class: 'app-shell'},
  el('aside', {class: 'sidebar'}, el('div', {class: 'brand'}, el('span', {class: 'brand-mark', 'aria-hidden': 'true'}, '✉'), el('h1', {}, 'Counterline')),
    nav, el('div', {class: 'sidebar-foot'}, el('div', {}, brandName, el('small', {}, 'Customer support · synthetic data')))),
  el('main', {class: 'app-main'}, el('header', {class: 'toolbar'}, el('span', {}), el('button', {type: 'button', onclick: () => refresh().catch(showError)}, 'Refresh')), status, content)));
function showError(e) { status.textContent = e.message; status.dataset.error = 'true'; status.dataset.code = e.code || 'error'; }
function ok(text) { status.textContent = text; delete status.dataset.error; delete status.dataset.code; }
const setBusy = on => document.querySelector('#app').setAttribute('aria-busy', String(on));
async function act(fn, done) {
  setBusy(true);
  try { const r = await fn(); await refresh(); ok(typeof done === 'function' ? done(r) : done); } catch (e) { showError(e); } finally { setBusy(false); }
}

// ---- state read from the App on every refresh ----
let view = sessionStorage.getItem('counterline-view') || 'cases', current = sessionStorage.getItem('counterline-case');
let listing = null, caseData = null, commitments = [], helpHits = null, article = null, helpQuery = '';
function go(next, id) {
  view = next; if (id !== undefined) current = id;
  sessionStorage.setItem('counterline-view', view);
  if (current) sessionStorage.setItem('counterline-case', current);
  return refresh().catch(showError);
}

async function refresh() {
  setBusy(true);
  try { await load(); } finally { setBusy(false); }
}
async function load() {
  tools = (await request('/api/tools')).tools;
  listing = await call('counterline.cases.list');
  brandName.textContent = listing.provider.name;
  document.title = `${listing.provider.name} support · Counterline`;
  if (!current && listing.cases.length) current = listing.cases.at(-1).case_id;
  caseData = view === 'cases' && current && listing.cases.some(c => c.case_id === current) ? await call('counterline.cases.get', {case_id: current}) : null;
  commitments = view === 'commitments' ? (await call('counterline.commitments.list')).commitments : [];
  if (view === 'help') helpHits = (await call('counterline.help.search', {query: helpQuery})).articles;
  render();
}

function render() {
  nav.replaceChildren(...[['cases', 'Cases'], ['help', 'Help center'], ['commitments', 'Commitments'], ['settings', 'Settings']].map(([v, label]) =>
    el('button', {type: 'button', 'aria-current': String(view === v), onclick: () => go(v)}, label)));
  const pages = {cases: casesPage, help: helpPage, commitments: commitmentsPage, settings: settingsPage};
  content.replaceChildren(pages[view]());
}

// ---- cases ----
function casesPage() {
  const rows = listing.cases.slice().reverse().map(c => el('button', {type: 'button', class: 'case-row', 'aria-current': String(c.case_id === current), onclick: () => go('cases', c.case_id)},
    el('strong', {}, listing.topics.find(t => t.topic_id === c.topic_id)?.title || words(c.topic_id)), ' ', chip(c.status),
    el('small', {}, `${c.case_id} · ${words(c.tier)} · opened ${when(c.opened_at)}`)));
  const left = el('div', {}, has('cases.open') && newCaseForm(), ...rows);
  return el('div', {class: 'split'}, left, caseData ? caseDetail() : el('p', {class: 'muted'}, 'Open a case to start a chat.'));
}

function newCaseForm() {
  const v = structuredClone(version);
  const topic = el('select', {'aria-label': 'Topic'}, ...listing.topics.map(t => el('option', {value: t.topic_id}, t.title)));
  const account = el('input', {'aria-label': 'Account reference', value: listing.cases.at(-1)?.account_ref || '', placeholder: 'Account reference'});
  const message = el('textarea', {'aria-label': 'First message', placeholder: 'How can we help?'});
  return panel('New case', el('form', {onsubmit: e => { e.preventDefault();
    act(() => write('cases.open', {topic_id: topic.value, account_ref: account.value, message: message.value}, v).then(r => { current = r.case_id; return r; }), r => `Case ${r.case_id} opened.`); }},
  el('div', {class: 'fields'}, topic, account, message), el('div', {class: 'form-actions'}, el('button', {type: 'submit', class: 'primary'}, 'Open case'))));
}

function caseDetail() {
  const c = caseData.case, offers = caseData.offers, v = structuredClone(version);
  const topic = listing.topics.find(t => t.topic_id === c.topic_id)?.title || words(c.topic_id);
  const writable = c.status !== 'closed';
  const transcript = el('div', {class: 'chat', 'aria-label': 'Conversation', role: 'log'}, ...c.transcript.map(t =>
    el('div', {class: 'turn ' + t.speaker}, t.text, el('small', {}, `${t.speaker === 'customer' ? 'You' : 'Representative'} · ${when(t.at)}${t.source === 'action' ? ' · quick action' : ''}`))));
  setTimeout(() => { transcript.scrollTop = transcript.scrollHeight; });
  const quick = el('div', {class: 'quick', 'aria-label': 'Quick actions'}, ...c.available_actions.map(a => el('button', {type: 'button', 'data-action': a.action,
    onclick: () => a.needs_department ? transferForm(c, v) : act(() => write('cases.take_action', {case_id: c.case_id, action: a.action}, v), `${a.label}: sent.`)}, a.label)));
  const text = el('textarea', {'aria-label': 'Message', placeholder: writable ? 'Write a message' : 'This case is closed', disabled: !writable});
  const composer = el('form', {class: 'composer', onsubmit: e => { e.preventDefault(); if (!text.value.trim()) return;
    act(() => write('cases.send_message', {case_id: c.case_id, text: text.value}, v), 'Message sent.'); }},
  text, el('button', {type: 'submit', class: 'primary', disabled: !writable}, 'Send'));
  const caseButtons = el('div', {class: 'actions'},
    c.status !== 'closed' && has('cases.close') && el('button', {type: 'button', onclick: () => act(() => write('cases.close', {case_id: c.case_id}, v), 'Case closed.')}, 'Close case'),
    c.status === 'closed' && has('cases.reopen') && el('button', {type: 'button', onclick: () => act(() => write('cases.reopen', {case_id: c.case_id}, v), 'Case reopened.')}, 'Reopen'));
  return el('div', {},
    el('div', {class: 'case-head'}, el('h2', {}, topic), chip(c.status), chip(c.tier, 'tier'), caseButtons),
    el('p', {class: 'muted'}, `${c.case_id} · account ${c.account_ref} · identity ${c.identity.verified ? 'verified' : 'not verified'}`),
    panel('Chat', transcript, writable && quick, writable && composer),
    offers.length > 0 && panel('Offers', ...offers.map(o => offerCard(o, v, writable))),
    writable && has('identity.provide') && identityForm(c, v));
}

function transferForm(c, v) {
  const dept = el('input', {'aria-label': 'Department', placeholder: 'Department name'});
  const dialog = el('dialog', {'aria-label': 'Ask for a transfer'}, el('form', {method: 'dialog', onsubmit: e => { e.preventDefault(); dialog.close();
    act(() => write('cases.take_action', {case_id: c.case_id, action: 'request_transfer', department: dept.value}, v), 'Transfer requested.'); }},
  el('h2', {}, 'Ask for a transfer'), el('p', {class: 'notice'}, 'Name the team you want. The help center lists the provider\'s teams.'),
  el('div', {class: 'fields'}, dept), el('div', {class: 'form-actions'}, el('button', {type: 'button', onclick: () => dialog.close()}, 'Cancel'), el('button', {type: 'submit', class: 'primary'}, 'Request'))));
  document.body.append(dialog);
  dialog.addEventListener('close', () => dialog.remove());
  dialog.showModal();
}

function offerCard(o, v, writable) {
  const live = o.state === 'presented' && writable;
  return el('div', {class: 'offer ' + o.state, 'data-offer': o.offer_id},
    el('div', {class: 'row'}, el('strong', {}, o.title), o.value && el('span', {}, money(o.value)), chip(o.state)),
    textBlock(o.terms),
    o.conditions.length > 0 && el('p', {class: 'notice'}, 'Conditions: ' + o.conditions.join('; ')),
    el('small', {class: 'muted'}, `${o.offer_id} · presented ${when(o.presented_at)}${o.expires_at ? ' · available until ' + when(o.expires_at) : ''}`),
    live && el('div', {class: 'actions'},
      has('offers.accept') && el('button', {type: 'button', class: 'primary', onclick: () => acceptOffer(o, v)}, 'Accept…'),
      has('offers.decline') && el('button', {type: 'button', onclick: () => act(() => write('offers.decline', {offer_id: o.offer_id}, v), `Declined ${o.title}.`)}, 'Decline')));
}

// Step one returns a summary and a token and changes no offer; step two, after the person confirms, creates the commitment.
async function acceptOffer(o, v) {
  let step;
  try { step = await write('offers.accept', {offer_id: o.offer_id}, v); } catch (e) { return showError(e); }
  const s = step.summary, closes = s.group_closes.map(id => caseData.offers.find(x => x.offer_id === id)?.title || id);
  const confirmVersion = structuredClone(version);
  const dialog = el('dialog', {'aria-label': 'Confirm acceptance'}, el('h2', {}, 'Confirm: ' + s.title),
    s.value && el('p', {}, el('strong', {}, money(s.value))), textBlock(s.terms),
    s.conditions.length > 0 && el('p', {class: 'notice'}, 'Conditions: ' + s.conditions.join('; ')),
    s.perform_by && el('p', {}, 'Due by ' + when(s.perform_by)),
    closes.length > 0 && el('p', {class: 'notice'}, 'Accepting closes these offers: ' + closes.join(', ')),
    el('div', {class: 'form-actions'}, el('button', {type: 'button', onclick: () => dialog.close()}, 'Cancel'),
      el('button', {type: 'button', class: 'primary', onclick: () => { dialog.close();
        act(() => write('offers.accept', {offer_id: o.offer_id, confirmation_token: step.confirmation_token}, confirmVersion), r => `Accepted. Commitment ${r.commitment_id} created.`); }}, 'Confirm')));
  document.body.append(dialog);
  dialog.addEventListener('close', () => dialog.remove());
  dialog.showModal();
  await refresh().catch(showError);
}

// Only ticked fields are sent; the values are never shown back, and every field sent is recorded as disclosed.
function identityForm(c, v) {
  const labels = {full_name: 'Full name', last_four: 'Last four digits', billing_zip: 'Billing ZIP code', date_of_birth: 'Date of birth',
    full_card_number: 'Full card number', ssn: 'Social Security number', one_time_code: 'One-time code'};
  const fields = Object.keys(schemaOf('identity.provide').properties?.fields?.properties || {});
  const rows = fields.map(f => ({f, box: el('input', {type: 'checkbox', 'aria-label': 'Share ' + labels[f], 'data-field': f}), input: el('input', {'aria-label': labels[f], autocomplete: 'off'})}));
  const last = c.identity.disclosures.at(-1);
  const wrap = (...body) => c.identity.verified
    ? el('details', {class: 'panel'}, el('summary', {}, 'Identity verified · share more details'), ...body)
    : panel('Verify identity', ...body);
  return wrap(
    el('p', {class: 'notice'}, 'Tick only what the representative needs. Everything you send is recorded as disclosed.'),
    last && el('p', {class: 'muted'}, `Last shared ${when(last.at)}: ${last.fields.map(f => labels[f]).join(', ')}${last.not_needed.length ? ' (not needed: ' + last.not_needed.map(f => labels[f]).join(', ') + ')' : ''}`),
    el('form', {onsubmit: e => { e.preventDefault();
      const chosen = Object.fromEntries(rows.filter(r => r.box.checked).map(r => [r.f, r.input.value]));
      if (!Object.keys(chosen).length) return showError(Error('Tick at least one field to share.'));
      act(() => write('identity.provide', {case_id: c.case_id, fields: chosen}, v), r => r.verified ? 'Identity verified.' : 'Details sent; not verified.'); }},
    el('div', {class: 'idform'}, ...rows.flatMap(r => [r.box, el('label', {}, labels[r.f], r.input)])),
    el('div', {class: 'form-actions'}, el('button', {type: 'submit'}, 'Send selected'))));
}

// ---- help center ----
function helpPage() {
  const q = el('input', {type: 'search', 'aria-label': 'Search help', placeholder: 'Search help articles', value: helpQuery});
  return el('div', {class: 'split'},
    el('div', {}, el('form', {onsubmit: e => { e.preventDefault(); helpQuery = q.value; article = null; refresh().catch(showError); }}, q),
      ...(helpHits || []).map(a => el('button', {type: 'button', class: 'case-row', 'aria-current': String(article?.article_id === a.article_id),
        onclick: async () => { setBusy(true); try { article = (await call('counterline.help.get', {article_id: a.article_id})).article; render(); } catch (e) { showError(e); } finally { setBusy(false); } }},
      el('strong', {}, a.title), el('small', {}, a.tags.join(' · '))))),
    article ? panel(article.title, textBlock(article.body)) : el('p', {class: 'muted'}, 'Choose an article.'));
}

// ---- commitments ----
function commitmentsPage() {
  const v = structuredClone(version);
  return el('div', {},
    el('p', {class: 'notice'}, 'A commitment is what the provider promised. A report is what the provider says it did. Neither shows that money reached your account: check the account itself.'),
    commitments.length ? null : el('p', {class: 'muted'}, 'No commitments yet.'),
    ...commitments.slice().reverse().map(m => panel(`${m.commitment_id} · ${words(m.kind)}`,
      el('div', {class: 'row'}, m.value && el('strong', {}, money(m.value)), ' ', chip(m.status), m.overdue && chip('overdue'), m.conditional && chip('conditional', 'conditional')),
      el('p', {class: 'muted'}, `Case ${m.case_id} · account ${m.account_ref} · accepted ${when(m.accepted_at)}${m.perform_by ? ' · due by ' + when(m.perform_by) : ''}`),
      m.reports.length ? el('table', {class: 'reports'}, el('tr', {}, el('th', {}, 'Reported'), el('th', {}, 'Reference'), el('th', {}, 'Amount')),
        ...m.reports.map(r => el('tr', {}, el('td', {}, when(r.at)), el('td', {}, r.reference_id), el('td', {}, money(r))))) : el('p', {class: 'muted'}, 'No performance report yet.'),
      m.contest && el('p', {class: 'notice'}, `Contested ${when(m.contest.at)}: ${m.contest.reason}${m.contest.outcome ? ` · answered ${when(m.contest.answered_at)}: ${m.contest.outcome}` : ' · awaiting the provider'}`),
      ['pending', 'reported_performed', 'partially_reported'].includes(m.status) && has('commitments.contest') && contestForm(m, v))));
}
function contestForm(m, v) {
  const reason = el('input', {'aria-label': 'Reason', placeholder: 'Why you are contesting this'});
  return el('form', {class: 'composer', onsubmit: e => { e.preventDefault(); if (!reason.value.trim()) return;
    act(() => write('commitments.contest', {commitment_id: m.commitment_id, reason: reason.value}, v), `Contested ${m.commitment_id}.`); }},
  reason, el('button', {type: 'submit'}, 'Contest'));
}

// ---- settings ----
function settingsPage() {
  const v = structuredClone(version);
  const box = el('input', {type: 'checkbox', id: 'email-copies', 'aria-label': 'Email copies of offers and confirmations'});
  box.checked = listing.preferences.email_copies;
  box.disabled = !has('preferences.update');
  box.onchange = () => act(() => write('preferences.update', {email_copies: box.checked}, v), 'Preference saved.');
  return panel('Notifications', el('label', {class: 'field'}, el('span', {}, el('span', {}, box), ' Email me a copy when an offer is presented or confirmed')));
}

// ---- start ----
(async () => {
  try {
    const token = new URLSearchParams(location.hash.slice(1)).get('access');
    if (token) { history.replaceState(null, '', location.pathname); ({csrf} = await request('/session', 'POST', {token})); }
    else ({csrf} = await request('/session'));
    await refresh();
    ok('Ready.');
  } catch (e) { showError(e); }
})();
