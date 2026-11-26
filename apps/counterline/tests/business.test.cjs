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

// ---------------- conversation, offers and commitments (acceptance matrix in proposal #219) ----------------
const ISP = require('../fixtures/internet-provider.json');
const ACCT = 'brindle:acct-jordan-1234';
function feeCase(f, verify = true) {
  const { case_id } = f.call('counterline.cases.open', { topic_id: 'annual_fee', account_ref: ACCT, message: 'My annual fee posted. Can you help?' });
  if (verify) f.call('counterline.identity.provide', { case_id, fields: { last_four: '1234', billing_zip: '02139' } });
  return case_id;
}
const get = (f, case_id) => f.call('counterline.cases.get', { case_id });
const actions = (f, case_id) => get(f, case_id).case.available_actions.map(a => a.action);
const lastRep = (f, case_id) => get(f, case_id).case.transcript.at(-1).text;
const offerByTitle = (f, case_id, title) => get(f, case_id).offers.find(o => o.title === title);

test('T00 baseline: a plain status inquiry reports a pending refund, then a late one', () => {
  const f = fixture({ seed: ISP });
  const { case_id } = f.call('counterline.cases.open', { topic_id: 'refund_status', account_ref: 'kestrel:acct-55120', message: 'Hi there.' });
  f.call('counterline.cases.send_message', { case_id, text: 'Can you check on the refund you promised me?' });
  assert.match(lastRep(f, case_id), /still being processed and is due by 2026-12-10/);
  assert.equal(f.call('counterline.commitments.get', { commitment_id: 'cm-0101' }).commitment.status, 'pending');
  assert.equal(get(f, case_id).offers.length, 0);
  f.at('2026-12-11T09:00:00-05:00');
  f.call('counterline.cases.send_message', { case_id, text: 'Any update on that refund? Still waiting.' });
  assert.match(lastRep(f, case_id), /late: it was due by 2026-12-10/);
  assert.equal(f.call('counterline.commitments.get', { commitment_id: 'cm-0101' }).commitment.overdue, true);
});

test('T05 quick actions depend only on the case, and are identical without a better offer', () => {
  const f = fixture();
  const a = feeCase(f);
  const noBetter = structuredClone(require('../fixtures/minimal.json'));
  noBetter.provider.offer_catalog = noBetter.provider.offer_catalog.filter(e => e.stage !== 'better');
  const g = fixture({ seed: noBetter });
  const b = feeCase(g);
  assert.deepEqual(actions(f, a), ['explain_terms', 'ask_for_better_offer', 'ask_status', 'request_transfer', 'end_chat']);
  assert.deepEqual(actions(g, b), actions(f, a));
  f.call('counterline.help.get', { article_id: 'kb-transfers' });
  assert.deepEqual(actions(f, a), actions(g, b), 'reading help changes nothing');
  g.call('counterline.cases.take_action', { case_id: b, action: 'ask_for_better_offer' });
  assert.match(lastRep(g, b), /best offer I can make/);
});

test('T06 two requests in one message are answered in order, like the two actions', () => {
  const f = fixture(), g = fixture();
  const a = feeCase(f), b = feeCase(g);
  const r = f.call('counterline.cases.send_message', { case_id: a, text: 'Thanks. Can you explain the terms, and is there anything better?' });
  assert.deepEqual(r.recognized, ['explain_terms', 'ask_for_better_offer']);
  g.call('counterline.cases.take_action', { case_id: b, action: 'explain_terms' });
  g.call('counterline.cases.take_action', { case_id: b, action: 'ask_for_better_offer' });
  const reps = (h, c) => get(h, c).case.transcript.filter(t => t.speaker === 'representative').map(t => [t.rule, t.text]);
  assert.deepEqual(reps(f, a), reps(g, b));
  assert.equal(get(f, a).offers.length, 4);
});

test('T07 identity: only the required fields verify; extra fields are recorded, values never shown', () => {
  const f = fixture();
  const a = feeCase(f, false);
  assert.deepEqual(get(f, a).offers, [], 'no offer before identity');
  const r = f.call('counterline.identity.provide', { case_id: a, fields: { last_four: '1234', billing_zip: '02139', ssn: '000-12-3456' } });
  assert.deepEqual([r.verified, r.not_needed], [true, ['ssn']]);
  const c = get(f, a).case;
  assert.deepEqual(c.identity.disclosures.at(-1).fields, ['last_four', 'billing_zip', 'ssn']);
  assert.ok(!JSON.stringify(c.transcript).includes('000-12-3456') && !JSON.stringify(c.transcript).includes('02139'));
  assert.match(JSON.stringify(c.transcript), /never need your Social Security number/);
  const b = feeCase(f, false);
  assert.equal(f.call('counterline.identity.provide', { case_id: b, fields: { last_four: '9999', billing_zip: '02139' } }).verified, false);
  assert.match(lastRep(f, b), /do not match/);
  f.call('counterline.identity.provide', { case_id: b, fields: { last_four: '1234' } });
  assert.match(lastRep(f, b), /still need your billing ZIP code/);
});

test('T08 transfers follow written policy; hidden departments are never listed', () => {
  const f = fixture();
  const a = feeCase(f);
  f.call('counterline.cases.take_action', { case_id: a, action: 'request_transfer', department: 'retention' });
  assert.deepEqual([get(f, a).case.tier, get(f, a).case.status], ['specialist', 'escalated']);
  const b = feeCase(f);
  f.call('counterline.cases.take_action', { case_id: b, action: 'request_transfer', department: 'the moon team' });
  assert.ok(!/Account Review|Customer Care/.test(lastRep(f, b)));
  assert.equal(get(f, b).case.tier, 'frontline');
  const g = fixture({ seed: ISP });
  const { case_id } = g.call('counterline.cases.open', { topic_id: 'billing_review', account_ref: 'kestrel:acct-55120', message: 'A charge on my bill looks wrong.' });
  g.call('counterline.cases.send_message', { case_id, text: 'Please transfer me to a supervisor.' });
  assert.match(lastRep(g, case_id), /not able to transfer this chat to Billing Review/);
  assert.equal(get(g, case_id).case.tier, 'frontline');
  unchanged(g, () => g.call('counterline.cases.take_action', { case_id, action: 'explain_terms' }), /does not offer/);
  g.call('counterline.cases.send_message', { case_id, text: 'ok sure whatever works' });
  assert.match(lastRep(g, case_id), /I can help you with/);
});

test('T09 closed cases take no writes; reopen only within the window', () => {
  const f = fixture();
  const a = feeCase(f);
  f.call('counterline.cases.close', { case_id: a });
  unchanged(f, () => f.call('counterline.cases.send_message', { case_id: a, text: 'hello?' }), /closed/);
  assert.equal(f.call('counterline.cases.reopen', { case_id: a }).case_status, 'open');
  f.call('counterline.cases.close', { case_id: a });
  f.at('2026-12-20T09:00:00-05:00');
  unchanged(f, () => f.call('counterline.cases.reopen', { case_id: a }), /no longer be reopened/);
  const b = feeCase(f);
  f.call('counterline.cases.take_action', { case_id: b, action: 'end_chat' });
  assert.equal(get(f, b).case.status, 'resolved');
  assert.deepEqual(actions(f, b), []);
  f.call('counterline.cases.send_message', { case_id: b, text: 'One more question about my fee terms.' });
  assert.equal(get(f, b).case.status, 'open');
});

test('T10 text never accepts: "I\'ll take the 300" creates no commitment', () => {
  const f = fixture();
  const a = feeCase(f);
  f.call('counterline.cases.take_action', { case_id: a, action: 'ask_for_better_offer' });
  const before = f.data.commitments.length;
  f.call('counterline.cases.send_message', { case_id: a, text: "Yes, I'll take the 300." });
  assert.equal(f.data.commitments.length, before);
  assert.ok(get(f, a).offers.every(o => o.state === 'presented'));
});

test('T11 acceptance is two-step; the group closes; a replay returns the same commitment', () => {
  const f = fixture();
  const a = feeCase(f);
  f.call('counterline.cases.take_action', { case_id: a, action: 'ask_for_better_offer' });
  const o = offerByTitle(f, a, 'Larger statement credit');
  const step1 = f.call('counterline.offers.accept', { offer_id: o.offer_id });
  assert.equal(step1.step, 'confirm');
  assert.equal(offerByTitle(f, a, 'Larger statement credit').state, 'presented', 'step one changes no offer');
  assert.equal(step1.summary.group_closes.length, 3);
  const step2 = f.call('counterline.offers.accept', { offer_id: o.offer_id, confirmation_token: step1.confirmation_token });
  assert.equal(step2.step, 'accepted');
  assert.deepEqual(get(f, a).offers.map(x => x.state).sort(), ['accepted', 'unavailable', 'unavailable', 'unavailable']);
  const again = f.call('counterline.offers.accept', { offer_id: o.offer_id, confirmation_token: step1.confirmation_token });
  assert.equal(again.commitment_id, step2.commitment_id);
  assert.equal(f.data.commitments.filter(m => m.offer_id === o.offer_id).length, 1);
  const rival = offerByTitle(f, a, 'Spend bonus credit');
  unchanged(f, () => f.call('counterline.offers.accept', { offer_id: rival.offer_id }), /no longer available/);
  const m = f.call('counterline.commitments.get', { commitment_id: step2.commitment_id }).commitment;
  assert.deepEqual([m.status, m.value.amount_minor, m.perform_by], ['pending', 12500, '2026-12-09T09:00:00-05:00']);
});

test('T12 a wrong or stale token is refused and changes nothing', () => {
  const f = fixture();
  const a = feeCase(f);
  const o = get(f, a).offers[0];
  f.call('counterline.offers.accept', { offer_id: o.offer_id });
  unchanged(f, () => f.call('counterline.offers.accept', { offer_id: o.offer_id, confirmation_token: 'cf-0000000000000000' }), /wrong or out of date/);
  const t2 = f.call('counterline.offers.accept', { offer_id: o.offer_id }).confirmation_token;
  assert.ok(t2);
});

test('T13 expired offers cannot be accepted or declined', () => {
  const f = fixture();
  const a = feeCase(f);
  const o = get(f, a).offers[0];
  f.at('2026-12-05T09:00:00-05:00');
  assert.equal(f.call('counterline.offers.get', { offer_id: o.offer_id }).offer.state, 'expired');
  unchanged(f, () => f.call('counterline.offers.accept', { offer_id: o.offer_id }), /expired/);
  unchanged(f, () => f.call('counterline.offers.decline', { offer_id: o.offer_id }), /expired/);
});

test('T14 decline is explicit and final for that offer', () => {
  const f = fixture();
  const a = feeCase(f);
  const o = get(f, a).offers[0];
  assert.equal(f.call('counterline.offers.decline', { offer_id: o.offer_id }).state, 'declined');
  unchanged(f, () => f.call('counterline.offers.accept', { offer_id: o.offer_id }), /declined/);
});

test('T19 contest and its answer; revoke; condition_missed only on a conditional commitment; offer.added', () => {
  const f = fixture();
  f.event(scenario);
  assert.equal(f.call('counterline.commitments.contest', { commitment_id: 'cm-0001', reason: 'The credit does not show on my card account.' }).commitment_status, 'contested');
  f.event({ event_id: 'ev-cl-0200', at: '2026-12-06T09:00:00-05:00', operation: 'counterline.contest.answered', payload: { commitment_id: 'cm-0001', outcome: 'upheld', reference_id: null } });
  assert.equal(f.data.commitments[0].status, 'reported_performed');
  unchanged(f, () => f.event({ event_id: 'ev-cl-0201', at: '2026-12-06T10:00:00-05:00', operation: 'counterline.commitment.condition_missed', payload: { commitment_id: 'cm-0001', reason: 'x' } }), /no condition/);
  unchanged(f, () => f.event({ event_id: 'ev-cl-0202', at: '2026-12-06T10:00:00-05:00', operation: 'counterline.commitment.revoked', payload: { commitment_id: 'cm-0001', reason: 'x' } }), /Only a pending/);
  const g = fixture({ seed: ISP });
  g.call('counterline.commitments.contest', { commitment_id: 'cm-0101', reason: 'Nothing arrived on my card.' });
  g.event({ event_id: 'ev-cl-0300', at: '2026-12-03T09:00:00-05:00', operation: 'counterline.contest.answered', payload: { commitment_id: 'cm-0101', outcome: 'reissued', reference_id: 'RF-77' } });
  assert.equal(g.data.commitments[0].status, 'pending');
  g.event({ event_id: 'ev-cl-0301', at: '2026-12-04T09:00:00-05:00', operation: 'counterline.commitment.revoked', payload: { commitment_id: 'cm-0101', reason: 'the account was closed' } });
  assert.equal(g.data.commitments[0].status, 'revoked');
  unchanged(g, () => g.call('counterline.commitments.contest', { commitment_id: 'cm-0101', reason: 'again' }), /cannot be contested/);
  const h = fixture();
  const c = feeCase(h);
  h.event({ event_id: 'ev-cl-0400', at: '2026-12-02T10:00:00-05:00', operation: 'counterline.offer.added', payload: { case_id: c, catalog_id: 'cat-fee-f4' } });
  assert.ok(offerByTitle(h, c, 'Switch to the Classic card'));
});

test('T20 a report is not settlement: the join fields are exposed, no settled state exists', () => {
  const f = fixture();
  f.event(scenario);
  const m = f.call('counterline.commitments.get', { commitment_id: 'cm-0001' }).commitment;
  assert.deepEqual([m.commitment_id, m.provider_id, m.account_ref, m.reports[0].reference_id], ['cm-0001', 'issuer-larchmont', ACCT, 'POST-301']);
  assert.equal(m.status, 'reported_performed');
  const tools = require('../tools.json');
  const statuses = JSON.stringify(tools.find(t => t.name === 'counterline.commitments.get').outputSchema);
  assert.ok(!/settled|verified/.test(statuses), 'no settled or verified commitment state');
  assert.ok(!require('../app.json').event_types.some(e => /settle|verif/.test(e)), 'no event can settle');
  f.event({ event_id: 'ev-cl-0500', at: '2026-12-05T09:00:00-05:00', operation: 'counterline.case.followup', payload: { case_id: 'cs-0001', script_id: 'followup-credit-processed' } });
  assert.equal(f.call('counterline.commitments.get', { commitment_id: 'cm-0001' }).commitment.status, 'reported_performed');
});

test('T22 Mail copies are queued only while email_copies is on, once per presentation or confirmation', () => {
  const off = fixture();
  feeCase(off);
  assert.equal(off.data.outbox.length, 0, 'no copies while the preference is off');
  const f = fixture();
  f.call('counterline.preferences.update', { email_copies: true });
  const a = feeCase(f);
  assert.deepEqual(f.data.outbox.map(n => n.kind), ['offer_presented']);
  const o = get(f, a).offers[0];
  const t = f.call('counterline.offers.accept', { offer_id: o.offer_id }).confirmation_token;
  const { commitment_id } = f.call('counterline.offers.accept', { offer_id: o.offer_id, confirmation_token: t });
  const copy = f.data.outbox.find(n => n.kind === 'commitment_confirmed');
  assert.equal(copy.ref_id, commitment_id);
  assert.match(copy.body, new RegExp(commitment_id));
  assert.equal(copy.recipient_person_id, 'person-jordan');
  f.event({ event_id: 'ev-cl-0600', at: '2026-12-02T09:10:00-05:00', operation: 'counterline.notification.delivery_recorded',
    payload: { notification_id: copy.notification_id, status: 'committed', code: null, stop_run: false, router_event_id: 'rt-1' } });
  assert.equal(f.data.outbox.find(n => n.notification_id === copy.notification_id).status, 'delivered');
  unchanged(f, () => f.event({ event_id: 'ev-cl-0601', at: '2026-12-02T09:11:00-05:00', operation: 'counterline.notification.delivery_recorded',
    payload: { notification_id: copy.notification_id, status: 'rejected', code: 'x', stop_run: false, router_event_id: null } }), /already delivered/);
  unchanged(f, () => f.event({ event_id: 'ev-cl-0602', at: '2026-12-02T09:11:00-05:00', operation: 'counterline.notification.delivery_recorded',
    payload: { notification_id: 'ntf-missing', status: 'committed', code: null, stop_run: false, router_event_id: null } }), /existing notification/);
});
