'use strict';
// Loads Rowan's Mail and Files workspaces through the public runtime (env.load_seed via
// data-cli pack), then applies the scheduled Mail deliveries in time order and checks that
// every attachment reads back byte-exact. Run from the repository root:
//   node lifepacks/tax-packet/tasks/tax-packet/environment/build/check_workspace.cjs
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const repo = path.resolve(__dirname, '../../../../../..');
const { createRuntime } = require(path.join(repo, 'runtime/core/runtime.cjs'));
const { pack } = require(path.join(repo, 'runtime/core/data-cli.cjs'));
const ws = path.resolve(__dirname, '../workspace');
const runtime = createRuntime({ registryFile: path.join(repo, 'apps.registry.json') });
const sha = b => crypto.createHash('sha256').update(b).digest('hex');

function load(app, dir, virtualNow) {
  const { payload, quality } = pack(app, path.join(ws, dir), runtime);
  let s = runtime.create(app, 'tax-packet-check');
  const out = runtime.execute(s, 'infra', 'env.load_seed', { ...payload, virtual_now: virtualNow, expected_version: runtime.version(s), request_id: 'load-' + app });
  assert.equal(out.result.status, 'ready', app + ': ' + JSON.stringify(out.result));
  return { state: out.state, quality };
}
const call = (st, name, args) => runtime.execute(st.state, 'agent', name, args);

const mail = load('mail', 'mail', '2026-02-03T08:00:00-08:00');
const files = load('files', 'files', '2026-02-03T08:00:00-08:00');
console.log('mail loaded:', mail.quality.counts.assets, 'assets;', 'files loaded:', files.quality.counts.assets, 'assets');

const listed = call(mail, 'mail.search', {}).result;
assert.equal(listed.status, 'ok', JSON.stringify(listed));
const before = (listed.items || listed.messages || []).length;
for (const m of mail.state.data.messages) for (const id of m.attachments) {
  const r = call(mail, 'mail.attachment.get', { id: m.id, asset_id: id }).result;
  assert.equal(r.status, 'ok', JSON.stringify(r));
  assert.equal(sha(Buffer.from(r.file.base64, 'base64')), r.file.sha256);
}
const events = JSON.parse(fs.readFileSync(path.join(ws, 'mail/events.json'), 'utf8'));
let last = '2026-02-03T08:00:00-08:00';
for (const { session, event } of events) {
  assert.ok(Date.parse(event.at) >= Date.parse(last), 'events in time order');
  last = event.at;
  const out = runtime.execute(mail.state, 'infra', 'env.apply_event', { expected_version: runtime.version(mail.state), event });
  assert.equal(out.result.status, 'committed', event.event_id + ': ' + JSON.stringify(out.result));
  mail.state = out.state;
  const m = mail.state.data.messages.find(x => x.id === event.event_id);
  assert.ok(m, 'delivered ' + event.event_id);
  for (const id of m.attachments) {
    const r = call(mail, 'mail.attachment.get', { id: m.id, asset_id: id }).result;
    assert.equal(r.status, 'ok', JSON.stringify(r));
    const sent = event.payload.message?.data.content.attachments.find(a => a.filename === r.file.filename);
    assert.equal(r.file.sha256, sent.sha256);
  }
  console.log(session, event.event_id, 'from', m.from, 'attachments', m.attachments.length);
}
const fileList = call(files, 'files.list', {}).result;
assert.equal(fileList.status, 'ok');
const nf = files.state.data.files.find(f => f.id === 'file-nf-2024');
const read = call(files, 'files.read', { id: nf.id }).result;
assert.equal(read.status, 'ok', JSON.stringify(read));
console.log('files: 2024 reference readable,', read.file.filename, read.file.sha256.slice(0, 12));
console.log('OK: mail', before, '->', mail.state.data.messages.length, 'messages');
