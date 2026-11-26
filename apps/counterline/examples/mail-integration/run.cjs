'use strict';
// Counterline → Messaging → Mail through the public runtime, with the real Mail App. Run from a full checkout:
//   node apps/counterline/examples/mail-integration/run.cjs
// Cases: (1) with email copies on, a presented offer and a confirmed commitment reach Mail's inbox with
// committed receipts, and Counterline records each outcome; (2) republishing a copy is a duplicate and Mail
// is unchanged; (3) without a grant the copy is rejected, Mail is unchanged, the case is unchanged and the
// copy becomes delivery_failed; (4) with copies off nothing is queued. Local commit, Mail delivery and
// business confirmation are reported separately; a copy has no business confirmation.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os'), assert = require('node:assert/strict');
const pkg = path.resolve(__dirname, '../..');
let root = pkg; while (!fs.existsSync(path.join(root, 'runtime/client.cjs'))) { const up = path.dirname(root); if (up === root) throw Error('Run inside the PALE checkout'); root = up; }
const {Client} = require(path.join(root, 'runtime/client.cjs'));
const publisher = require('../../src/publisher.cjs');
const MAIL_REGISTRY = path.join(root, 'examples/registry.mail.json');
const ACCT = 'brindle:acct-maya-1234';

// The card-issuer fixture, owned by Maya, the owner of the reference Mail account.
function seed(copies) {
  const data = structuredClone(require('../../fixtures/minimal.json'));
  data.account_id = 'counterline-maya'; data.owner_person_id = 'person-maya';
  data.preferences.email_copies = copies;
  return data;
}
const binding = {people: [{person_id: 'person-maya', name: 'Maya Chen'}], accounts: [{app_id: 'counterline', account_id: 'counterline-maya', owner_person_id: 'person-maya'}], objects: {}};

async function world({granted, copies}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'counterline-mail-')), clients = [];
  fs.cpSync(pkg, path.join(dir, 'pkg/counterline'), {recursive: true, filter: s => !s.includes('node_modules')});
  const registry = path.join(dir, 'pkg/registry.json');
  fs.writeFileSync(registry, JSON.stringify({schema_version: 1, apps: [{app_id: 'counterline', version: '0.1.0', path: 'counterline'}], initial_time: '2026-12-02T09:00:00-05:00'}));
  const config = path.join(dir, 'router.json');
  fs.writeFileSync(config, JSON.stringify({schema_version: 2, registry: 'examples/registry.mail.json', publishers: [{
    app_id: 'counterline', account_id: 'counterline-maya', owner_person_id: 'person-maya', package_root: path.relative(root, pkg),
    contribution_ref: 'contribution/contribution.json',
    allowed_recipients: granted ? [{app_id: 'mail', account_id: 'mail-maya', channel: 'channel.email'}] : []}],
    authentication: {mode: 'trusted-stdio'}}));
  const run = 'counterline-mail';
  try {
    const infra = new Client('counterline', 'infra', run, dir, 'counterline-infra', {registry}); clients.push(infra); await infra.initialize();
    const agent = new Client('counterline', 'agent', run, dir, 'counterline-agent', {registry}); clients.push(agent); await agent.initialize();
    const mail = new Client('mail', 'agent', run, dir, 'mail-reader', {registry: MAIL_REGISTRY}); clients.push(mail); await mail.initialize();
    const router = new Client(null, null, null, null, 'counterline-router', {commandArgs: [path.join(root, 'runtime/messaging/service.cjs'),
      '--config', config, '--publisher', 'counterline', '--run', run, '--state-dir', dir]}); clients.push(router); await router.initialize();
    const snap = await infra.call('env.snapshot');
    const loaded = await infra.call('env.load_seed', {expected_version: snap.version, request_id: 'seed-maya', data: seed(copies), binding, virtual_now: '2026-12-02T09:00:00-05:00'});
    assert.equal(loaded.status, 'ready', JSON.stringify(loaded));
    const write = async (name, args) => {
      const s = await infra.call('env.snapshot');
      const r = await agent.call(name, {...args, expected_version: s.version, request_id: name + '-' + s.version.revision});
      assert.equal(r.status, 'committed', JSON.stringify(r));
      return r;
    };
    const data = async () => (await infra.call('env.snapshot')).snapshot.data;
    const inbox = async () => (await mail.call('mail.search', {})).messages;
    return {infra, mail, router, write, data, inbox,
      close: async () => { await Promise.allSettled(clients.map(c => c.close())); fs.rmSync(dir, {recursive: true, force: true}); }};
  } catch (e) { await Promise.allSettled(clients.map(c => c.close())); fs.rmSync(dir, {recursive: true, force: true}); throw e; }
}

// The Agent's side: open a fee case, verify, accept the first offer with confirmation.
async function acceptFirstOffer(w) {
  const {case_id} = await w.write('counterline.cases.open', {topic_id: 'annual_fee', account_ref: ACCT, message: 'My annual fee posted. Can you help?'});
  await w.write('counterline.identity.provide', {case_id, fields: {last_four: '1234', billing_zip: '02139'}});
  const offer = (await w.data()).offers.find(o => o.case_id === case_id && o.state === 'presented');
  const step = await w.write('counterline.offers.accept', {offer_id: offer.offer_id});
  const done = await w.write('counterline.offers.accept', {offer_id: offer.offer_id, confirmation_token: step.confirmation_token});
  return {case_id, commitment_id: done.commitment_id};
}

async function main() {
  const report = {};
  const w = await world({granted: true, copies: true});
  try {
    const before = (await w.inbox()).length;
    const {commitment_id} = await acceptFirstOffer(w);
    const queued = (await w.data()).outbox;
    assert.deepEqual(queued.map(n => [n.kind, n.status]), [['offer_presented', 'pending_delivery'], ['commitment_confirmed', 'pending_delivery']]);
    const sent = await publisher.deliver({infra: w.infra, router: w.router});
    assert.equal(sent.length, 2);
    for (const s of sent) assert.equal(s.receipt.status, 'committed', JSON.stringify(s.receipt));
    const after = (await w.data()).outbox;
    assert.ok(after.every(n => n.status === 'delivered'));
    const confirm = after.find(n => n.kind === 'commitment_confirmed');
    const got = await w.mail.call('mail.get', {id: confirm.outcome.router_event_id});
    assert.equal(got.status, 'ok');
    assert.match(got.message.subject, /confirmed/);
    assert.match(got.message.body, new RegExp(commitment_id));
    assert.equal((await w.inbox()).length, before + 2);
    report.case1_delivered = {local_commit: commitment_id, mail_message_id: got.message.id, mail_subject: got.message.subject,
      receipts: sent.map(s => s.receipt.status), business_confirmation: 'none for a copy'};
    const again = await w.router.call('router.publish', {request_id: confirm.notification_id, message: publisher.message(await w.data(), confirm)});
    assert.equal(again.duplicate, true);
    assert.equal((await w.inbox()).length, before + 2);
    report.case2_duplicate = {duplicate: again.duplicate, inbox_unchanged: true};
  } finally { await w.close(); }

  const u = await world({granted: false, copies: true});
  try {
    const before = (await u.inbox()).length;
    await acceptFirstOffer(u);
    const caseBefore = JSON.stringify((await u.data()).cases);
    const out = await publisher.deliver({infra: u.infra, router: u.router});
    assert.ok(out.every(o => o.receipt.status === 'rejected'));
    assert.equal(out[0].receipt.code, 'recipient_not_authorized');
    assert.equal((await u.inbox()).length, before);
    const d = await u.data();
    assert.ok(d.outbox.every(n => n.status === 'delivery_failed'));
    assert.equal(JSON.stringify(d.cases), caseBefore, 'a refused copy leaves the case unchanged');
    report.case3_ungranted = {code: out[0].receipt.code, inbox_unchanged: true, case_unchanged: true, status: 'delivery_failed'};
  } finally { await u.close(); }

  const z = await world({granted: true, copies: false});
  try {
    await acceptFirstOffer(z);
    assert.equal((await z.data()).outbox.length, 0);
    assert.equal((await publisher.deliver({infra: z.infra, router: z.router})).length, 0);
    report.case4_copies_off = {queued: 0};
  } finally { await z.close(); }
  return report;
}

module.exports = {main};
if (require.main === module) main().then(r => { console.log(JSON.stringify(r, null, 2)); console.log('PASS: Counterline → Messaging → Mail, 4 cases.'); })
  .catch(e => { console.error(e); process.exitCode = 1; });
