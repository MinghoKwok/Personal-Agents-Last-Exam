'use strict';
// The chat policy: which quick actions a case offers, what the deterministic recognizer understands in
// free text, and how the representative answers each request. Everything here is computed from the case,
// the offers presented in it and the provider's records; nothing depends on what the Agent has read.
const { ms, addHours, money, list, nextId } = require('./util.cjs');

const LABELS = {
  explain_terms: 'Explain these terms',
  ask_for_better_offer: 'Ask for a better offer',
  ask_status: 'Check the status',
  request_transfer: 'Ask for a transfer',
  end_chat: 'End chat'
};
const OPEN_COMMITMENTS = ['pending', 'partially_reported', 'reported_performed', 'contested'];

// Requests the recognizer understands, matched anywhere in a message and answered in the order written.
const PATTERNS = [
  ['explain_terms', /\b((explain|clarify|walk me through)\b.{0,40}\b(terms?|conditions?|offers?|deal|credit|waiver)|(the|these|those|its|your) (terms|conditions)|terms and conditions|fine print|the catch)\b/i],
  ['ask_for_better_offer', /\b(anything better|something better|better (offer|deal|option)|best (offer|deal|you can do)|anything (else|more)|other (offers?|options?)|improve (the|that|your) offer|more than that)\b/i],
  ['ask_status', /\b(status|check on|update on|where is|when will|still waiting|has (it|my|the|that)\b.{0,30}\b(posted|processed|arrived|gone through))\b/i],
  ['request_transfer', /\b(transfer|connect me|speak (to|with)|talk (to|with)|escalate|put me through|send me to)\b/i],
  ['end_chat', /\b(that's all|that is all|end (the |this )?chat|goodbye|nothing else|no further questions)\b/i]
];

function department(provider, text) {
  const low = String(text || '').toLowerCase();
  const names = provider.departments.flatMap(d => [d.name, ...d.aliases].map(n => ({ d, n: n.toLowerCase() })))
    .sort((a, b) => b.n.length - a.n.length);
  return names.find(({ n }) => low.includes(n))?.d || null;
}

function recognize(provider, text) {
  const hits = [];
  for (const [action, rx] of PATTERNS) {
    const m = rx.exec(text);
    if (m) hits.push({ action, index: m.index });
  }
  return hits.sort((a, b) => a.index - b.index).map(h => ({ action: h.action, department: h.action === 'request_transfer' ? department(provider, text) : null }));
}

const live = (data, c, now) => data.offers.filter(o => o.case_id === c.case_id && o.state === 'presented' && !(o.expires_at && ms(now) > ms(o.expires_at)));

function availableActions(data, c, now) {
  if (c.status === 'closed' || c.status === 'resolved') return [];
  const names = [...(live(data, c, now).length ? ['explain_terms', 'ask_for_better_offer'] : []), 'ask_status', 'request_transfer', 'end_chat'];
  return names.map(action => ({ action, label: LABELS[action], needs_department: action === 'request_transfer' }));
}

function turn(c, at, speaker, text, source, recognized, rule) {
  c.transcript.push({ turn_id: `t-${String(c.transcript.length + 1).padStart(4, '0')}`, at, speaker, text, source, recognized, rule });
}
const say = (c, now, text, rule, recognized = []) => turn(c, now, 'representative', text, 'system', recognized, rule);

function describe(o) {
  const value = o.value ? ` (${money(o.value)})` : '';
  const cond = o.conditions.length ? ` Condition: ${o.conditions.join('; ')}.` : '';
  const until = o.expires_at ? ` Available until ${o.expires_at.slice(0, 16).replace('T', ' ')}.` : '';
  return `${o.title}${value}: ${o.terms}${cond}${until}`;
}

// Queue a plain-text Mail copy while the customer has email_copies on. One copy per presentation or confirmation.
function queueCopy(data, now, kind, c, ref_id, title, body) {
  if (!data.preferences.email_copies) return;
  const notification_id = `ntf-${ref_id}`;
  if (data.outbox.some(n => n.notification_id === notification_id)) return;
  data.outbox.push({ notification_id, kind, case_id: c.case_id, ref_id, title: `${data.provider.name}: ${title}`,
    body: `${body}\n\nCase ${c.case_id}. This is a copy for your records; reply in the support chat.`, time: now,
    recipient_person_id: data.owner_person_id, status: 'pending_delivery', outcome: null });
}

// Present catalog offers in a case. An offer whose group already has an accepted offer is not shown.
function present(data, c, now, entries) {
  const taken = new Set(data.offers.map(o => o.offer_id));
  const closedGroups = new Set(data.offers.filter(o => o.case_id === c.case_id && o.state === 'accepted' && o.group).map(o => o.group));
  const shown = [];
  for (const e of entries) {
    if (e.group && closedGroups.has(e.group)) continue;
    const offer_id = nextId('of', taken);
    taken.add(offer_id);
    const o = {
      offer_id, case_id: c.case_id, catalog_id: e.catalog_id, stage: e.stage, kind: e.kind, title: e.title, terms: e.terms,
      value: e.value ? { ...e.value } : null, conditions: [...e.conditions], group: e.group, tier: e.tier, presented_at: now,
      expires_at: e.expires_hours ? addHours(now, e.expires_hours) : null, perform_days: e.perform_days, state: 'presented'
    };
    data.offers.push(o);
    shown.push(o);
  }
  return shown;
}
const presentedIds = (data, c) => new Set(data.offers.filter(o => o.case_id === c.case_id && o.catalog_id).map(o => o.catalog_id));
const catalog = (data, c, stage) => data.provider.offer_catalog.filter(e => e.topic_id === c.topic_id && e.tier === c.tier && e.stage === stage && !presentedIds(data, c).has(e.catalog_id));
const mayOffer = (data, c) => c.identity.verified || !data.provider.topics.find(t => t.topic_id === c.topic_id).identity_required;

function presentStage(data, c, now, stage, lead) {
  if (!mayOffer(data, c)) return 0;
  const shown = present(data, c, now, catalog(data, c, stage));
  if (!shown.length) return 0;
  say(c, now, `${lead} ${shown.map(describe).join(' ')}`, `offers:${stage}:${c.tier}`);
  queueCopy(data, now, 'offer_presented', c, shown[0].offer_id, 'new offers in your case', shown.map(describe).join('\n'));
  return 1;
}

// One representative answer per request. Returns the number of turns added.
function perform(data, c, now, action, dept, recognized) {
  const p = data.provider;
  const rule = r => `${action}:${r}`;
  switch (action) {
    case 'explain_terms': {
      const offers = live(data, c, now);
      say(c, now, offers.length ? offers.map(describe).join(' ') : 'There is no offer on this case right now.', rule(offers.length ? 'offers' : 'none'), recognized);
      return 1;
    }
    case 'ask_for_better_offer': {
      if (!mayOffer(data, c)) { say(c, now, 'I need to verify your identity before I can look at offers.', rule('identity_first'), recognized); return 1; }
      const shown = present(data, c, now, catalog(data, c, 'better'));
      say(c, now, shown.length ? `Here is what else I can offer. ${shown.map(describe).join(' ')}` : 'That is the best offer I can make on this case.', rule(shown.length ? 'presented' : 'none'), recognized);
      if (shown.length) queueCopy(data, now, 'offer_presented', c, shown[0].offer_id, 'new offers in your case', shown.map(describe).join('\n'));
      return 1;
    }
    case 'ask_status': {
      const mine = data.commitments.filter(m => m.account_ref === c.account_ref && OPEN_COMMITMENTS.includes(m.status));
      const titleOf = m => data.offers.find(o => o.offer_id === m.offer_id)?.title || m.kind.replace(/_/g, ' ');
      const lines = mine.map(m => {
        const t = titleOf(m), due = m.perform_by ? m.perform_by.slice(0, 10) : null;
        if (m.status === 'contested') return `Your contest of the ${t} is under review.`;
        if (m.status === 'reported_performed') return `Our records show the ${t} was completed (reference ${m.reports.at(-1).reference_id}).`;
        if (m.status === 'partially_reported') return `We have completed ${money({ amount_minor: m.reports.reduce((s, r) => s + r.amount_minor, 0), currency: m.value.currency })} of the ${t} so far.`;
        if (due && ms(now) > ms(m.perform_by)) return `The ${t} we promised is late: it was due by ${due}. I have noted that on your case.`;
        return `The ${t}${m.value ? ` (${money(m.value)})` : ''} is still being processed${due ? ` and is due by ${due}` : ''}.`;
      });
      say(c, now, lines.length ? lines.join(' ') : 'I do not see an open credit or refund on this account.', rule(lines.length ? 'reported' : 'none'), recognized);
      return 1;
    }
    case 'request_transfer': {
      if (!dept) { say(c, now, 'I could not find a team by that name. I can keep helping you here.', rule('unknown'), recognized); return 1; }
      if (dept.tier === c.tier) { say(c, now, `You are already chatting with ${dept.name}.`, rule('same_tier'), recognized); return 1; }
      if (dept.transfer === 'refused') { say(c, now, `I am not able to transfer this chat to ${dept.name}. I can keep helping you here.`, rule('refused'), recognized); return 1; }
      c.tier = dept.tier;
      c.status = 'escalated';
      say(c, now, `You are now chatting with ${dept.name} at ${p.name}.`, rule('done'), recognized);
      return 1 + presentStage(data, c, now, 'transfer', 'Here is what I can offer.');
    }
    case 'end_chat':
      c.status = 'resolved';
      say(c, now, `Thanks for contacting ${p.name}. This chat is now closed; you can write again at any time.`, rule('resolved'), recognized);
      return 1;
    default:
      return 0;
  }
}

module.exports = { queueCopy, LABELS, recognize, department, availableActions, perform, present, presentStage, live, turn, say, describe, list };
