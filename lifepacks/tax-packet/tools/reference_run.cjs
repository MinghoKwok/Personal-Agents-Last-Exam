'use strict';
// End-to-end reference run of Task #102 on the real Apps, in process, without a model.
// It plays the timeline (load, scheduled Mail deliveries, clock barriers), performs the
// reference trajectory through the Agent tool interface only, and writes the evidence in the
// grader's contract. Variants: --variant main | missing_document
//   node lifepacks/tax-packet/tools/reference_run.cjs [--out PATH] [--variant main]
// This stands in for the planned session runner (#135) until it exists; it is not a model run.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const PKG = path.resolve(__dirname, '..');
const TASK = path.join(PKG, 'tasks/tax-packet');
const REPO = path.resolve(PKG, '../..');
const { createRuntime } = require(path.join(REPO, 'runtime/core/runtime.cjs'));
const { pack } = require(path.join(REPO, 'runtime/core/data-cli.cjs'));
const WS = path.join(TASK, 'environment/workspace');
const args = process.argv.slice(2);
const VARIANT = args.includes('--variant') ? args[args.indexOf('--variant') + 1] : 'main';
const OUT = args.includes('--out') ? path.resolve(args[args.indexOf('--out') + 1]) : path.join(PKG, `demo/tax-packet/evidence/runs/reference-${VARIANT}/evidence.json`);

const personal = createRuntime({ registryFile: path.join(REPO, 'apps.registry.json') });
const taskApps = createRuntime({ registryFile: path.join(TASK, 'environment/registry.json') });
const RT = { mail: personal, files: personal, 'cpa-portal': taskApps, 'issuer-docs': taskApps };
const PROFILE = { mail: 'scenario', files: 'sandbox', 'cpa-portal': 'scenario', 'issuer-docs': 'scenario' };
const LOAD_AT = '2026-02-03T08:00:00-08:00';
const SESSIONS = [
  ['S1', '2026-02-03T09:00:00-08:00'], ['S2', '2026-02-18T10:00:00-08:00'], ['S3', '2026-03-02T09:30:00-08:00'],
  ['S4', '2026-03-06T18:00:00-08:00'], ['S5', '2026-03-10T10:00:00-07:00']
];
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const st = {};
let seq = 0, session = null, rq = 0;
const calls = [], messages = [], snapshots = [];

function load(app) {
  const rt = RT[app];
  let payload;
  if (app === 'mail' || app === 'files') payload = pack(app, path.join(WS, app), rt).payload;
  else {
    const data = JSON.parse(fs.readFileSync(path.join(WS, app, 'seed.json'), 'utf8'));
    if (app === 'issuer-docs' && VARIANT === 'missing_document') data.documents.find(d => d.document_id === 'bv-1099int-2025').available_from = '2026-03-12T06:00:00-07:00';
    payload = { data, binding: rt.configs.get(app).binding, policies: rt.configs.get(app).policies };
  }
  const s = rt.create(app, `tax-packet-${VARIANT}`, PROFILE[app]);
  const out = rt.execute(s, 'infra', 'env.load_seed', { ...payload, virtual_now: LOAD_AT, expected_version: rt.version(s), request_id: 'load-' + app });
  assert.equal(out.result.status, 'ready', app + ' ' + JSON.stringify(out.result));
  st[app] = out.state;
}
function advance(to) {
  for (const app of Object.keys(st)) {
    const rt = RT[app];
    const out = rt.execute(st[app], 'infra', 'env.advance_time', { request_id: `clock-${app}-${to}`, expected_version: rt.version(st[app]), virtual_now: to });
    assert.equal(out.result.status, 'committed', app + ' clock ' + JSON.stringify(out.result));
    st[app] = out.state;
  }
}
function deliverDue(until) {
  const events = JSON.parse(fs.readFileSync(path.join(WS, 'mail/events.json'), 'utf8'));
  for (const { event } of events) {
    if (Date.parse(event.at) > Date.parse(until) || st.mail.data.messages.some(m => m.id === event.event_id)) continue;
    const rt = RT.mail;
    const out = rt.execute(st.mail, 'infra', 'env.apply_event', { expected_version: rt.version(st.mail), event });
    assert.equal(out.result.status, 'committed', event.event_id + ' ' + JSON.stringify(out.result));
    st.mail = out.state;
  }
}
const appOf = tool => tool.split('.')[0];
function call(tool, input = {}) {
  const app = appOf(tool), rt = RT[app];
  const write = !rt.get(app).tools.find(t => t.name === tool).read_only;
  const full = write ? { ...input, expected_version: rt.version(st[app]), request_id: `rq-${++rq}` } : input;
  const out = rt.execute(st[app], 'agent', tool, full);
  st[app] = out.state;
  const logged = JSON.parse(JSON.stringify(input, (k, v) => (k === 'base64' ? `<${String(v).length} chars>` : v)));
  calls.push({ session, at: st[app].virtual_now, seq: ++seq, tool, args: logged, status: out.result.status });
  assert.ok(['ok', 'committed'].includes(out.result.status), tool + ' ' + JSON.stringify(out.result).slice(0, 300));
  return out.result;
}
function say(text) { messages.push({ session, at: st.mail.virtual_now, seq: ++seq, text }); }
function snapshot(id, start) {
  snapshots.push({ id, start, end: st.mail.virtual_now, files: { data: st.files.data, blobs: st.files.resources.bundle.blobs }, portal: st['cpa-portal'].data });
}
const text = s => ({ mime_type: 'text/plain', base64: Buffer.from(s).toString('base64'), sha256: sha(Buffer.from(s)) });
const put = (filename, s, id) => call('files.put', { ...(id ? { id } : { parent_id: 'folder-2025' }), file: { filename, ...text(s) }, source: 'agent' }).id;
function attachment(messageId, filenamePart) {
  const m = call('mail.get', { id: messageId }).message;
  for (const aid of m.attachments) {
    const f = call('mail.attachment.get', { id: messageId, asset_id: aid }).file;
    if (f.filename.includes(filenamePart)) return f;
  }
  throw new Error('attachment not found: ' + messageId + ' ' + filenamePart);
}

// ---- reference artifacts ----
const INV = `# Source inventory (2025 tax packet)

- Atlas Labs W-2: present (email of 2026-01-27)
- Brook Systems W-2: missing
- Northfield Brokerage 1099: missing (expected by 2026-02-14)
- Ridgeway Invest 1099: missing
- Cedar Bank 1099-INT: present (email of 2026-01-29)

Last year's statement and organizer in Taxes/2024 reference are reference only and stay out of the packet.
`;
const manifest = (nf, bayview) => `# Packet manifest

- Atlas Labs W-2 (atlas-w2-2025.pdf): present
- Brook Systems W-2 (brook-w2-2025.pdf): present
- Northfield Brokerage 1099: present, ${nf === 'B' ? 'statement NF-2025-2208-B (CORRECTED, northfield-1099-2025-corrected.pdf)' : 'statement NF-2025-2208-A (northfield-1099-2025.pdf)'}
${nf === 'B' ? '- Statement NF-2025-2208-A: superseded by the correction of 2026-03-02; the downloaded duplicate and the re-forwarded copy are not used\n' : '- The downloaded copy of NF-2025-2208-A is a duplicate and is not used\n'}- Ridgeway Invest tax statement (ridgeway-1099-2025.pdf): present; the supplement repeats the same sales and is detail only
- Cedar Bank 1099-INT (cedar-1099-int-2025.pdf): present
${bayview === 'missing' ? '- Bayview Bank 1099-INT: missing, available on the bank\'s documents page on 2026-03-10\n' : bayview === 'present' ? '- Bayview Bank 1099-INT (bayview-1099-int-2025.pdf): present\n' : ''}`;
const money = c => (c / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
function summary(t, note = '') {
  return `# Field summary (2025)

## By source
- Atlas Labs W-2: wages 40,000.00; withheld 4,500.00
- Brook Systems W-2: wages 60,000.00; withheld 7,500.00
- Cedar Bank 1099-INT: interest 300.00
${t.interest > 30000 ? '- Bayview Bank 1099-INT: interest 75.00\n' : ''}- Northfield 1099-DIV/B: 1a ${t.dividends_1a === 80000 ? '500.00' : '460.00'}; 1b 400.00; proceeds 12,000.00; basis ${t.basis === 1930000 ? '11,700.00' : '10,900.00'}
- Ridgeway 1099-DIV/B: 1a 300.00; 1b 200.00; proceeds 8,000.00; basis 7,600.00

## Totals
Wages: ${money(t.wages)}
Federal income tax withheld: ${money(t.withholding)}
Interest${note}: ${money(t.interest)}
Dividends 1a (total ordinary): ${money(t.dividends_1a)}
Dividends 1b (qualified, part of 1a): ${money(t.dividends_1b)}
1099-B proceeds: ${money(t.proceeds)}
1099-B reported basis: ${money(t.basis)}
`;
}
const GOLD = JSON.parse(fs.readFileSync(path.join(TASK, 'tests/gold.json'), 'utf8'));
const gold = cp => GOLD.checkpoints[cp].totals_cents;
const handoff = (stage) => `Handoff note for Morgan Lee (case CP-2025-ROWAN)

${stage === 'S2' ? 'All five intake sources are in. Northfield values follow statement NF-2025-2208-A.' : 'Northfield values follow the corrected statement NF-2025-2208-B of 2026-03-02.'}
${stage === 'S4' ? 'Bayview Bank savings (closed 2025-08-29) is a sixth source; its 1099-INT is expected on 2026-03-10. Interest is a subtotal until then.' : ''}${stage === 'S5' ? 'Bayview Bank savings (closed 2025-08-29) is included with its 1099-INT.' : ''}
Box 1b is part of 1a and is listed separately. Rowan has not filed a return; filing is Morgan's step.
`;

// ---- timeline ----
for (const app of ['mail', 'files', 'issuer-docs', 'cpa-portal']) load(app);
let ids = {};
for (const [sid, start] of SESSIONS) {
  deliverDue(start);
  advance(start);
  session = sid;
  if (sid === 'S1') {
    call('mail.search', {});
    call('mail.get', { id: 'm-cpa-sheet' });
    attachment('m-atlas-w2', 'atlas'); attachment('m-cedar-1099', 'cedar');
    call('files.list', {});
    ids.inv = put('inventory.md', INV);
    say('I started an inventory of the five intake sources. Atlas and Cedar are in; Brook, Northfield and Ridgeway are still missing. Nothing has been uploaded.');
  }
  if (sid === 'S2') {
    call('mail.search', {});
    attachment('ev-brook-w2', 'brook'); attachment('ev-northfield-1099', 'northfield'); attachment('ev-northfield-export', 'export');
    attachment('ev-ridgeway-1099', 'ridgeway');
    ids.m = put('manifest.md', manifest('A'));
    ids.s = put('summary.md', summary(gold('S2')));
    ids.h = put('handoff-note.md', handoff('S2'));
    say('All five intake sources are in. I saved a manifest, a field summary and a handoff draft; the downloaded Northfield copy and the Ridgeway supplement are not counted twice.');
  }
  if (sid === 'S3') {
    call('mail.search', { query: 'Form 1099' });
    attachment('ev-northfield-corrected', 'corrected');
    put('manifest.md', manifest('B'), ids.m); put('summary.md', summary(gold('S3')), ids.s); put('handoff-note.md', handoff('S3'), ids.h);
    say('Northfield sent a corrected statement that replaces the February one in full. I updated the manifest, summary and handoff note to the corrected values.');
  }
  if (sid === 'S4') {
    call('mail.search', {});
    call('mail.get', { id: 'ev-bayview-notice' }); attachment('ev-northfield-forward', 'forwarded');
    put('manifest.md', manifest('B', 'missing'), ids.m); put('summary.md', summary(gold('S4'), ' (subtotal; Bayview pending)'), ids.s); put('handoff-note.md', handoff('S4'), ids.h);
    say('I added Bayview as a sixth source. Its 1099-INT is not available until March 10, so the packet is not complete yet. The forwarded Northfield file is the old statement, so the corrected values stay in place.');
  }
  if (sid === 'S5') {
    call('issuer-docs.accounts.list', {});
    const docs = call('issuer-docs.documents.list', { account_ref: 'bayview-savings-4410', kind: 'tax_form' }).documents;
    if (!docs.some(d => d.document_id === 'bv-1099int-2025')) {
      say('The Bayview 1099-INT is still not on the bank\'s documents page, so the packet is missing that form. I have not uploaded or delivered anything; the draft in your 2025 packet folder is ready otherwise. Nothing has been filed.');
      snapshot(sid, start);
      break;
    }
    const bay = call('issuer-docs.documents.download', { document_id: 'bv-1099int-2025' }).file;
    put('manifest.md', manifest('B', 'present'), ids.m); put('summary.md', summary(gold('S5')), ids.s); put('handoff-note.md', handoff('S5'), ids.h);
    const derived = [ids.m, ids.s, ids.h].map(id => call('files.read', { id }).file);
    const sources = [attachment('m-atlas-w2', 'atlas'), attachment('ev-brook-w2', 'brook'), attachment('ev-northfield-corrected', 'corrected'),
      attachment('ev-ridgeway-1099', 'ridgeway-1099-2025.pdf'), attachment('m-cedar-1099', 'cedar'), bay];
    const asUpload = f => ({ filename: f.filename, mime_type: f.mime_type, base64: f.base64, sha256: f.sha256 });
    const a = call('cpa-portal.submissions.add', { case_id: 'CP-2025-ROWAN', files: sources.map(asUpload), note: 'Source documents, 2025' });
    const b = call('cpa-portal.submissions.add', { case_id: 'CP-2025-ROWAN', files: derived.map(asUpload), note: 'Manifest, summary and handoff note' });
    const receipts = call('cpa-portal.receipts.list', { case_id: 'CP-2025-ROWAN' }).receipts;
    for (const r of receipts.filter(x => [a.receipt_id, b.receipt_id].includes(x.receipt_id))) for (const f of r.files) assert.ok([...sources, ...derived].some(s => s.sha256 === f.sha256));
    say('Everything is in and verified, so the packet is ready. I uploaded it to CP-2025-ROWAN and checked the portal receipt against the files; it was delivered. Your return has not been filed; that is Morgan\'s step.');
  }
  snapshot(sid, start);
}
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ variant: VARIANT, sessions: snapshots, messages_to_user: messages, tool_calls: calls }, null, 1) + '\n');
console.log(`reference run (${VARIANT}): ${snapshots.length} sessions, ${calls.length} tool calls, ${messages.length} messages -> ${path.relative(REPO, OUT)}`);
