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

function applyEvent(ctx, data, event) {
  if (event.operation === `${APP}.commitment.performance_reported`) performanceReported(data, event);
  else if (event.operation === `${APP}.case.followup`) followup(data, event);
  else fail('invalid_event', `Unsupported operation: ${event.operation}.`);
  log(ctx, event.operation, { event_id: event.event_id });
  return data;
}
module.exports = { applyEvent };
