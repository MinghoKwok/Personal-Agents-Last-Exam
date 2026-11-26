'use strict';
// Infra events. The task chooses timing; Counterline validates and applies the business effect.
const { fail, byId, ms } = require('./util.cjs');
const { log } = require('./diagnostics.cjs');
const APP = 'counterline';
const OPEN = ['pending', 'partially_reported'];

function performanceReported(data, event) {
  const p = event.payload;
  const m = data.commitments.find(x => x.commitment_id === p.commitment_id);
  if (!m) fail('invalid_event', 'A performance report must name an existing commitment.');
  if (p.provider_id !== m.provider_id) fail('invalid_event', 'The report names a different provider.');
  if (!OPEN.includes(m.status)) fail('invalid_event', `Commitment ${m.commitment_id} is ${m.status} and takes no report.`);
  if (m.reports.some(r => r.reference_id === p.reference_id)) fail('invalid_event', 'This reference was already reported.');
  const reported = m.reports.reduce((sum, r) => sum + r.amount_minor, 0) + p.amount_minor;
  if (m.value) {
    if (p.currency !== m.value.currency) fail('invalid_event', 'The report currency differs from the commitment.');
    if (reported > m.value.amount_minor) fail('invalid_event', 'Reports cannot exceed the committed amount.');
  }
  m.reports.push({ event_id: event.event_id, at: event.at, reference_id: p.reference_id, amount_minor: p.amount_minor, currency: p.currency });
  m.status = !m.value || reported === m.value.amount_minor ? 'reported_performed' : 'partially_reported';
  m.history.push({ at: event.at, status: m.status, event_id: event.event_id, note: null });
}

function followup(data, event) {
  const c = byId(data.cases, 'case_id', event.payload.case_id, 'Case');
  if (c.status === 'closed') fail('invalid_event', 'A closed case takes no follow-up.');
  const s = byId(data.provider.scripts, 'script_id', event.payload.script_id, 'Script');
  const last = c.transcript[c.transcript.length - 1];
  if (last && ms(event.at) < ms(last.at)) fail('invalid_event', 'A follow-up cannot precede the last transcript turn.');
  c.transcript.push({
    turn_id: `t-${String(c.transcript.length + 1).padStart(4, '0')}`, at: event.at, speaker: 'representative',
    text: s.text, source: 'script', recognized: [], rule: `followup:${s.script_id}`
  });
}

const { say, present, describe } = require('./policy.cjs');
const commitmentOf = (data, id) => {
  const m = data.commitments.find(x => x.commitment_id === id);
  if (!m) fail('invalid_event', 'The event must name an existing commitment.');
  return m;
};
function note(data, m, event, text, rule) {
  const c = data.cases.find(x => x.case_id === m.case_id);
  if (c && c.status !== 'closed') say(c, event.at, text, rule);
}
function conditionMissed(data, event) {
  const m = commitmentOf(data, event.payload.commitment_id);
  if (!m.conditional) fail('invalid_event', `Commitment ${m.commitment_id} has no condition to miss.`);
  if (!OPEN.includes(m.status)) fail('invalid_event', `Commitment ${m.commitment_id} is ${m.status}.`);
  m.status = 'condition_missed';
  m.history.push({ at: event.at, status: m.status, event_id: event.event_id, note: event.payload.reason });
}
function revoked(data, event) {
  const m = commitmentOf(data, event.payload.commitment_id);
  if (m.status !== 'pending') fail('invalid_event', `Only a pending commitment can be revoked; ${m.commitment_id} is ${m.status}.`);
  m.status = 'revoked';
  m.history.push({ at: event.at, status: m.status, event_id: event.event_id, note: event.payload.reason });
  note(data, m, event, `We are unable to complete this commitment: ${event.payload.reason}.`, 'commitment:revoked');
}
function contestAnswered(data, event) {
  const m = commitmentOf(data, event.payload.commitment_id);
  if (m.status !== 'contested' || !m.contest) fail('invalid_event', `Commitment ${m.commitment_id} is not contested.`);
  const { outcome, reference_id } = event.payload;
  m.status = outcome === 'reissued' ? 'pending' : m.contest.prior_status;
  Object.assign(m.contest, { answered_at: event.at, outcome });
  m.history.push({ at: event.at, status: m.status, event_id: event.event_id, note: `Contest ${outcome}${reference_id ? ` (${reference_id})` : ''}.` });
  note(data, m, event, outcome === 'reissued' ? `We reviewed your contest and are reissuing this commitment${reference_id ? ` under reference ${reference_id}` : ''}.`
    : 'We reviewed your contest and our record stands.', `contest:${outcome}`);
}
function offerAdded(data, event) {
  const c = byId(data.cases, 'case_id', event.payload.case_id, 'Case');
  if (['closed', 'resolved'].includes(c.status)) fail('invalid_event', `Case ${c.case_id} is ${c.status}.`);
  const e = data.provider.offer_catalog.find(x => x.catalog_id === event.payload.catalog_id);
  if (!e || e.topic_id !== c.topic_id) fail('invalid_event', 'The catalog offer does not exist for this case topic.');
  const shown = present(data, c, event.at, [{ ...e, tier: c.tier }]);
  if (!shown.length) fail('invalid_event', 'An offer in this group was already accepted.');
  say(c, event.at, `I can also offer: ${describe(shown[0])}`, 'offers:added');
  require('./policy.cjs').queueCopy(data, event.at, 'offer_presented', c, shown[0].offer_id, 'a new offer in your case', describe(shown[0]));
}
// Infra records the Messaging outcome of one Mail copy. Counterline's own commit and Mail's receipt are separate.
function deliveryRecorded(data, event) {
  const p = event.payload;
  const n = data.outbox.find(x => x.notification_id === p.notification_id);
  if (!n) fail('invalid_event', 'The outcome must name an existing notification.');
  if (n.status !== 'pending_delivery') fail('invalid_event', `Notification ${n.notification_id} is already ${n.status}.`);
  n.status = { committed: 'delivered', rejected: 'delivery_failed' }[p.status] || 'delivery_unknown';
  n.outcome = { status: p.status, code: p.code, router_event_id: p.router_event_id, recorded_at: event.at };
}

const HANDLERS = {
  [`${APP}.commitment.performance_reported`]: performanceReported, [`${APP}.case.followup`]: followup,
  [`${APP}.commitment.condition_missed`]: conditionMissed, [`${APP}.commitment.revoked`]: revoked,
  [`${APP}.contest.answered`]: contestAnswered, [`${APP}.offer.added`]: offerAdded,
  [`${APP}.notification.delivery_recorded`]: deliveryRecorded
};
function applyEvent(ctx, data, event) {
  const handler = HANDLERS[event.operation];
  if (!handler) fail('invalid_event', `Unsupported operation: ${event.operation}.`);
  handler(data, event);
  log(ctx, event.operation, { event_id: event.event_id });
  return data;
}
module.exports = { applyEvent };
