'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const plugin = require('../plugin.cjs');
const { fixture } = require('./harness.cjs');
const scenario = require('../examples/scenario.json');
const report = (over = {}) => {
  const e = structuredClone(scenario);
  Object.assign(e.payload, over.payload || {});
  return { ...e, ...over, payload: e.payload };
};
function unchanged(f, fn, pattern) {
  const before = f.data;
  assert.throws(fn, pattern);
  assert.deepEqual(f.data, before);
}

test('T01 help center search and read are side-effect free', () => {
  const f = fixture();
  const hits = f.call('counterline.help.search', { query: 'annual fee' }).articles;
  assert.deepEqual(hits.map(a => a.article_id), ['kb-annual-fee']);
  assert.match(f.call('counterline.help.get', { article_id: 'kb-annual-fee' }).article.body, /Account Review/);
  unchanged(f, () => f.call('counterline.help.get', { article_id: 'missing' }), /does not exist/);
});

test('T02 departments are named in the help center, never in the tool list', () => {
  const tools = require('../tools.json');
  assert.ok(!JSON.stringify(tools).includes('Account Review'));
  assert.ok(!JSON.stringify(tools).toLowerCase().includes('retention'));
});

test('T03 cases.open records the message and the scripted greeting', () => {
  const f = fixture();
  const { case_id } = f.call('counterline.cases.open', { topic_id: 'annual_fee', account_ref: 'brindle:acct-jordan-1234', message: 'Can you help with my fee?' });
  const c = f.call('counterline.cases.get', { case_id }).case;
  assert.equal(c.status, 'open');
  assert.equal(c.tier, 'frontline');
  assert.deepEqual(c.transcript.map(t => [t.speaker, t.source]), [['customer', 'text'], ['representative', 'script']]);
  assert.match(c.transcript[1].text, /last four digits/);
  unchanged(f, () => f.call('counterline.cases.open', { topic_id: 'nope', account_ref: 'x', message: 'hi' }), /does not exist/);
});

test('T04 offers read expired after their expiry, computed on read', () => {
  const f = fixture({ now: '2026-12-09T09:00:00-05:00' });
  const before = f.data;
  assert.equal(f.call('counterline.offers.get', { offer_id: 'of-0001' }).offer.state, 'accepted');
  const g = fixture({ seed: (() => { const s = structuredClone(require('../fixtures/minimal.json')); s.offers[1].state = 'presented'; s.offers[1].group = 'other'; return s; })(), now: '2026-12-09T09:00:00-05:00' });
  assert.equal(g.call('counterline.offers.get', { offer_id: 'of-0002' }).offer.state, 'expired');
  assert.deepEqual(f.data, before);
});

test('T15 a full report makes the commitment reported_performed', () => {
  const f = fixture();
  f.event(scenario);
  const m = f.call('counterline.commitments.get', { commitment_id: 'cm-0001' }).commitment;
  assert.equal(m.status, 'reported_performed');
  assert.equal(m.reports[0].reference_id, 'POST-301');
  assert.equal(m.overdue, false);
});

test('T16 a partial report makes it partially_reported; the rest completes it', () => {
  const f = fixture();
  f.event(report({ payload: { amount_minor: 5000, reference_id: 'POST-301A' } }));
  assert.equal(f.data.commitments[0].status, 'partially_reported');
  f.event(report({ event_id: 'ev-cl-0002', at: '2026-12-05T09:00:00-05:00', payload: { amount_minor: 7500, reference_id: 'POST-301B' } }));
  assert.equal(f.data.commitments[0].status, 'reported_performed');
});

test('T17 a scripted "processed" message is not a report; overdue is derived', () => {
  const f = fixture();
  f.event({ event_id: 'ev-cl-0100', at: '2026-12-03T09:00:00-05:00', operation: 'counterline.case.followup', payload: { case_id: 'cs-0001', script_id: 'followup-credit-processed' } });
  f.at('2026-12-10T09:00:00-05:00');
  const m = f.call('counterline.commitments.get', { commitment_id: 'cm-0001' }).commitment;
  assert.equal(m.status, 'pending');
  assert.equal(m.overdue, true);
  assert.match(f.data.cases[0].transcript.at(-1).text, /processed/);
});

test('T18 invalid reports are rejected and change nothing', () => {
  const f = fixture();
  unchanged(f, () => f.event(report({ payload: { commitment_id: 'cm-9999' } })), /existing commitment/);
  unchanged(f, () => f.event(report({ payload: { amount_minor: 99999 } })), /exceed/);
  unchanged(f, () => f.event(report({ payload: { provider_id: 'someone-else' } })), /different provider/);
  unchanged(f, () => f.event(report({ payload: { currency: 'EUR' } })), /currency/);
  f.event(scenario);
  unchanged(f, () => f.event(report({ event_id: 'ev-cl-0003', payload: { reference_id: 'POST-302' } })), /takes no report/);
});

test('seed validation rejects inconsistent history', () => {
  const f = fixture();
  const bad = f.data;
  bad.commitments[0].offer_id = 'of-0002';
  assert.throws(() => plugin.validateSeed(f.ctx, bad), /accepted offer/);
  const twoAccepted = f.data;
  twoAccepted.offers[1].state = 'accepted';
  assert.throws(() => plugin.validateSeed(f.ctx, twoAccepted), /more than one accepted/);
});

test('diagnostics are optional and do not change results', () => {
  const on = fixture(), off = fixture({ logging: false });
  on.event(scenario); off.event(scenario);
  assert.deepEqual(on.data, off.data);
  assert.ok(on.logs.length > 0);
});
