'use strict';
// Seed validation and record enumeration for Core.
const { fail, unique, ms } = require('./util.cjs');
function bindingRefs(ctx, data) {
  const person = ctx.binding.people.some(p => p.person_id === data.owner_person_id);
  const account = ctx.binding.accounts.some(a => a.app_id === ctx.app_id && a.account_id === data.account_id && a.owner_person_id === data.owner_person_id);
  if (!person || !account) fail('invalid_seed', 'Account and owner must exist in the supplied binding.');
}
function ordered(times, what) {
  for (let i = 1; i < times.length; i++) if (ms(times[i]) < ms(times[i - 1])) fail('invalid_seed', `${what} times go backwards.`);
}
function validateSeed(ctx, data) {
  bindingRefs(ctx, data);
  const p = data.provider;
  unique(p.departments, 'department_id', 'department');
  unique(p.topics, 'topic_id', 'topic');
  unique(p.scripts, 'script_id', 'script');
  const scripts = new Set(p.scripts.map(s => s.script_id));
  for (const t of p.topics) if (!scripts.has(t.greeting_script_id)) fail('invalid_seed', `Topic ${t.topic_id} names a missing greeting script.`);
  if (p.identity_policy.required.some(f => !p.identity_policy.accepted.includes(f))) fail('invalid_seed', 'Every required identity field must also be accepted.');
  unique(p.offer_catalog, 'catalog_id', 'catalog offer');
  for (const e of p.offer_catalog) if (!p.topics.some(t => t.topic_id === e.topic_id)) fail('invalid_seed', `Catalog offer ${e.catalog_id} names an unknown topic.`);
  unique(data.help_articles, 'article_id', 'article');
  unique(data.cases, 'case_id', 'case');
  unique(data.offers, 'offer_id', 'offer');
  unique(data.commitments, 'commitment_id', 'commitment');
  const topics = new Set(p.topics.map(t => t.topic_id));
  for (const c of data.cases) {
    if (!topics.has(c.topic_id)) fail('invalid_seed', `Case ${c.case_id} names an unknown topic.`);
    unique(c.transcript, 'turn_id', 'turn');
    ordered([c.opened_at, ...c.transcript.map(t => t.at)], `Case ${c.case_id} transcript`);
    if ((c.status === 'closed') !== (c.closed_at !== null)) fail('invalid_seed', `Case ${c.case_id} closed_at must be set exactly when it is closed.`);
  }
  const cases = new Map(data.cases.map(c => [c.case_id, c]));
  const acceptedGroups = new Set();
  for (const o of data.offers) {
    if (!cases.has(o.case_id)) fail('invalid_seed', `Offer ${o.offer_id} names an unknown case.`);
    if (o.expires_at && ms(o.expires_at) < ms(o.presented_at)) fail('invalid_seed', `Offer ${o.offer_id} expires before it is presented.`);
    if (o.state === 'accepted' && o.group) {
      const key = `${o.case_id}/${o.group}`;
      if (acceptedGroups.has(key)) fail('invalid_seed', `Group ${o.group} has more than one accepted offer.`);
      acceptedGroups.add(key);
    }
  }
  unique(data.outbox, 'notification_id', 'notification');
  for (const n of data.outbox) {
    if (!cases.has(n.case_id)) fail('invalid_seed', `Notification ${n.notification_id} names an unknown case.`);
    if (n.recipient_person_id !== data.owner_person_id) fail('invalid_seed', 'Mail copies go to the account owner.');
    if ((n.status === 'pending_delivery') !== (n.outcome === null)) fail('invalid_seed', `Notification ${n.notification_id} has an outcome exactly when it is no longer pending.`);
  }
  const catalogIds = new Set(p.offer_catalog.map(e => e.catalog_id));
  for (const o of data.offers) if (o.catalog_id !== null && !catalogIds.has(o.catalog_id)) fail('invalid_seed', `Offer ${o.offer_id} names an unknown catalog offer.`);
  const offers = new Map(data.offers.map(o => [o.offer_id, o]));
  for (const x of data.confirmations) {
    const o = offers.get(x.offer_id);
    if (!o || o.case_id !== x.case_id) fail('invalid_seed', `Confirmation ${x.token} names an unknown offer.`);
    if ((x.used_at === null) !== (x.commitment_id === null)) fail('invalid_seed', `Confirmation ${x.token} is used exactly when it names a commitment.`);
  }
  for (const m of data.commitments) {
    const o = offers.get(m.offer_id);
    if (!o || o.state !== 'accepted') fail('invalid_seed', `Commitment ${m.commitment_id} must name an accepted offer.`);
    const c = cases.get(m.case_id);
    if (o.case_id !== m.case_id || !c || c.account_ref !== m.account_ref) fail('invalid_seed', `Commitment ${m.commitment_id} does not match its offer's case.`);
    if (m.provider_id !== p.provider_id || m.kind !== o.kind || JSON.stringify(m.value) !== JSON.stringify(o.value)) fail('invalid_seed', `Commitment ${m.commitment_id} does not match its provider or offer.`);
    if (m.conditional !== (o.conditions.length > 0)) fail('invalid_seed', `Commitment ${m.commitment_id} conditional flag does not match its offer.`);
    const reported = m.reports.reduce((sum, r) => sum + r.amount_minor, 0);
    if (m.value && (reported > m.value.amount_minor || m.reports.some(r => r.currency !== m.value.currency))) fail('invalid_seed', `Commitment ${m.commitment_id} reports exceed or mismatch its value.`);
    if (m.status === 'pending' && m.reports.length && !(m.contest && m.contest.outcome === 'reissued')) fail('invalid_seed', `Commitment ${m.commitment_id} has reports but is still pending.`);
    if ((m.status === 'contested') !== (m.contest !== null && m.contest.outcome === null)) fail('invalid_seed', `Commitment ${m.commitment_id} must carry an open contest exactly when it is contested.`);
    ordered([m.accepted_at, ...m.history.map(h => h.at)], `Commitment ${m.commitment_id} history`);
    if (!m.history.length || m.history[m.history.length - 1].status !== m.status) fail('invalid_seed', `Commitment ${m.commitment_id} history must end with its current status.`);
  }
}
const records = data => [...data.help_articles, ...data.cases, ...data.offers, ...data.commitments, ...data.confirmations, ...data.outbox];
const objects = data => [
  ...data.help_articles.map(a => a.article_id), ...data.cases.map(c => c.case_id),
  ...data.offers.map(o => o.offer_id), ...data.commitments.map(m => m.commitment_id)
];
module.exports = { validateSeed, records, objects, references: () => [] };
