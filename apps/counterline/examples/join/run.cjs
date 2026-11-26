'use strict';
// T21: the settlement join check, through the public runtime. Run from a full checkout:
//   node apps/counterline/examples/join/run.cjs
// Counterline is read only through its Agent MCP tools; reports arrive as Infra events. A synthetic ledger
// file stands in for the owning App (a contract test, not a delivered integration with #182).
// Cases: (1) a report whose reference is on the ledger for the same account and amount: settled.
// (2) a report with no ledger record, (3) one posted with a different amount and (4) one posted to another
// account: not settled, while Counterline reads reported_performed. (5) a representative saying the credit
// was processed, with no report: the commitment stays pending and the join finds no report.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os'), assert = require('node:assert/strict');
const pkg = path.resolve(__dirname, '../..');
let root = pkg; while (!fs.existsSync(path.join(root, 'runtime/client.cjs'))) { const up = path.dirname(root); if (up === root) throw Error('Run inside the PALE checkout'); root = up; }
const {Client} = require(path.join(root, 'runtime/client.cjs'));
const {settle} = require('./join.cjs');
const ledger = require('./ledger.json').records;
const report = (event_id, at, reference_id, amount_minor) => ({event_id, at, operation: 'counterline.commitment.performance_reported',
  payload: {commitment_id: 'cm-0001', provider_id: 'issuer-larchmont', reference_id, amount_minor, currency: 'USD', status: 'reported'}});

async function world(run) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'counterline-join-'));
  const registry = path.join(pkg, 'registry.json');
  const infra = new Client('counterline', 'infra', run, dir, 'join-infra', {registry}); await infra.initialize();
  const agent = new Client('counterline', 'agent', run, dir, 'join-agent', {registry}); await agent.initialize();
  const apply = async event => { const s = await infra.call('env.snapshot'); const r = await infra.call('env.apply_event', {expected_version: s.version, event}); assert.equal(r.status, 'committed', JSON.stringify(r)); };
  const commitment = async () => (await agent.call('counterline.commitments.get', {commitment_id: 'cm-0001'})).commitment;
  return {apply, commitment, close: async () => { await Promise.allSettled([infra.close(), agent.close()]); fs.rmSync(dir, {recursive: true, force: true}); }};
}

async function main() {
  const cases = [
    ['1 matching ledger record', [report('ev-j-1', '2026-12-04T09:00:00-05:00', 'POST-301', 12500)], 'settled'],
    ['2 no ledger record', [report('ev-j-2', '2026-12-04T09:00:00-05:00', 'POST-399', 12500)], 'not_settled'],
    ['3 different amount on the ledger', [report('ev-j-3', '2026-12-05T09:00:00-05:00', 'POST-302', 12500)], 'not_settled'],
    ['4 posted to another account', [report('ev-j-4', '2026-12-05T09:00:00-05:00', 'POST-303', 12500)], 'not_settled'],
    ['5 "processed" in chat, no report', [{event_id: 'ev-j-5', at: '2026-12-03T09:00:00-05:00', operation: 'counterline.case.followup',
      payload: {case_id: 'cs-0001', script_id: 'followup-credit-processed'}}], 'no_report']
  ];
  const out = [];
  for (const [name, events, want] of cases) {
    const w = await world('join-' + name.split(' ')[0]);
    try {
      for (const e of events) await w.apply(e);
      const m = await w.commitment();
      const r = settle(m, ledger);
      assert.equal(r.result, want, `${name}: ${JSON.stringify(r)}`);
      assert.ok(!/settled|verified/.test(m.status), 'Counterline has no settled state');
      out.push({case: name, counterline_status: m.status, join: r.result, reasons: r.reasons});
    } finally { await w.close(); }
  }
  return out;
}

module.exports = {main};
if (require.main === module) main().then(r => { console.log(JSON.stringify(r, null, 2)); console.log(`PASS: settlement join, ${r.length} cases (T21).`); })
  .catch(e => { console.error(e); process.exitCode = 1; });
