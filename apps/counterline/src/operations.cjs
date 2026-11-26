'use strict';
// Agent tool handlers. Reads never change data; writes return { data, result }.
// Binding effects (accepting, declining, disclosing identity, contesting, closing) are explicit
// operations; a chat message can only ask, and never changes an offer or a commitment.
const { fail, copy, byId, nextId, ms, addDays, money, list, token } = require('./util.cjs');
const { offerView, commitmentView, caseSummary, caseView } = require('./views.cjs');
const { log } = require('./diagnostics.cjs');
const P = require('./policy.cjs');
const APP = 'counterline';

function read(ctx, data, name, args) {
  const now = ctx.virtual_now;
  switch (name) {
    case `${APP}.help.search`: {
      const q = (args.query || '').toLocaleLowerCase();
      const hits = data.help_articles.filter(a => [a.title, a.body, ...a.tags].join(' ').toLocaleLowerCase().includes(q));
      return { articles: hits.map(({ article_id, title, tags }) => ({ article_id, title, tags: copy(tags) })) };
    }
    case `${APP}.help.get`:
      return { article: copy(byId(data.help_articles, 'article_id', args.article_id, 'Article')) };
    case `${APP}.cases.list`:
      return {
        provider: { name: data.provider.name, kind: data.provider.kind, time_zone: data.provider.time_zone },
        cases: data.cases.filter(c => !args.status || c.status === args.status).map(caseSummary),
        topics: data.provider.topics.map(({ topic_id, title }) => ({ topic_id, title })), preferences: copy(data.preferences)
      };
    case `${APP}.cases.get`: {
      const c = byId(data.cases, 'case_id', args.case_id, 'Case');
      return { case: caseView(data, c, now), offers: data.offers.filter(o => o.case_id === c.case_id).map(o => offerView(o, now)), now };
    }
    case `${APP}.offers.get`:
      return { offer: offerView(byId(data.offers, 'offer_id', args.offer_id, 'Offer'), now), now };
    case `${APP}.commitments.list`:
      return { commitments: data.commitments.filter(m => !args.status || m.status === args.status).map(m => commitmentView(m, now)), now };
    case `${APP}.commitments.get`:
      return { commitment: commitmentView(byId(data.commitments, 'commitment_id', args.commitment_id, 'Commitment'), now), now };
    default:
      return null;
  }
}

const writable = c => { if (c.status === 'closed') fail('invalid_state', `Case ${c.case_id} is closed.`); return c; };
const FIELD_LABEL = { full_name: 'full name', last_four: 'last four digits', billing_zip: 'billing ZIP code', date_of_birth: 'date of birth',
  full_card_number: 'full card number', ssn: 'Social Security number', one_time_code: 'one-time code' };

const writes = {
  'cases.open'(ctx, data, args) {
    const p = data.provider;
    const topic = byId(p.topics, 'topic_id', args.topic_id, 'Topic');
    const greeting = byId(p.scripts, 'script_id', topic.greeting_script_id, 'Script');
    const case_id = nextId('cs', new Set(data.cases.map(c => c.case_id)));
    const now = ctx.virtual_now;
    const c = { case_id, topic_id: topic.topic_id, account_ref: args.account_ref, status: 'open', tier: 'frontline', opened_at: now, closed_at: null,
      identity: { verified: false, disclosures: [] }, transcript: [] };
    data.cases.push(c);
    P.turn(c, now, 'customer', args.message, 'text', [], null);
    P.turn(c, now, 'representative', greeting.text, 'script', [], `topic:${topic.topic_id}:greeting`);
    P.presentStage(data, c, now, 'initial', 'Here is what I can offer.');
    return { case_id };
  },

  'cases.send_message'(ctx, data, args) {
    const c = writable(byId(data.cases, 'case_id', args.case_id, 'Case'));
    const now = ctx.virtual_now;
    if (c.status === 'resolved') c.status = 'open';
    const asks = P.recognize(data.provider, args.text);
    P.turn(c, now, 'customer', args.text, 'text', asks.map(a => a.action), null);
    let added = 0;
    for (const a of asks) {
      if (a.action === 'request_transfer' && !a.department) {
        P.say(c, now, 'Which team would you like to talk to?', 'request_transfer:ask_department', [a.action]);
        added++;
      } else added += P.perform(data, c, now, a.action, a.department, [a.action]);
    }
    if (!asks.length) {
      const labels = P.availableActions(data, c, now).map(x => x.label.toLowerCase());
      P.say(c, now, `Thanks for your message. I can help you with: ${list(labels)}.`, 'unrecognized');
      added = 1;
    }
    return { case_id: c.case_id, recognized: asks.map(a => a.action), turns_added: added };
  },

  'cases.take_action'(ctx, data, args) {
    const c = writable(byId(data.cases, 'case_id', args.case_id, 'Case'));
    const now = ctx.virtual_now;
    if (!P.availableActions(data, c, now).some(a => a.action === args.action)) fail('action_unavailable', `The chat does not offer ${args.action} now.`);
    let dept = null;
    if (args.action === 'request_transfer') {
      if (!args.department) fail('invalid_input', 'A transfer needs a department name.');
      dept = P.department(data.provider, args.department);
    }
    P.turn(c, now, 'customer', P.LABELS[args.action] + (args.department ? `: ${args.department}` : ''), 'action', [args.action], null);
    const added = P.perform(data, c, now, args.action, dept, [args.action]);
    return { case_id: c.case_id, action: args.action, turns_added: added };
  },

  'cases.close'(ctx, data, args) {
    const c = writable(byId(data.cases, 'case_id', args.case_id, 'Case'));
    c.status = 'closed';
    c.closed_at = ctx.virtual_now;
    P.say(c, ctx.virtual_now, 'This case is closed.', 'case:closed');
    return { case_id: c.case_id, case_status: c.status };
  },

  'cases.reopen'(ctx, data, args) {
    const c = byId(data.cases, 'case_id', args.case_id, 'Case');
    if (c.status !== 'closed') fail('invalid_state', `Case ${c.case_id} is not closed.`);
    if (ms(ctx.virtual_now) > ms(addDays(c.closed_at, data.provider.reopen_days))) fail('too_late', `Case ${c.case_id} can no longer be reopened.`);
    c.status = 'open';
    c.closed_at = null;
    P.say(c, ctx.virtual_now, 'This case is open again.', 'case:reopened');
    return { case_id: c.case_id, case_status: c.status };
  },

  'identity.provide'(ctx, data, args) {
    const c = writable(byId(data.cases, 'case_id', args.case_id, 'Case'));
    const now = ctx.virtual_now, policy = data.provider.identity_policy, record = data.customer_record;
    const fields = Object.keys(args.fields);
    if (!fields.length) fail('invalid_input', 'Give at least one identity field.');
    const not_needed = fields.filter(f => !policy.required.includes(f));
    const missing = policy.required.filter(f => !fields.includes(f));
    const matches = policy.required.every(f => record[f] !== undefined && String(args.fields[f] ?? '').trim().toLowerCase() === String(record[f]).trim().toLowerCase());
    c.identity.disclosures.push({ at: now, fields, not_needed, matched: matches });
    if (matches) c.identity.verified = true;
    // The transcript names the fields, never their values.
    P.turn(c, now, 'customer', `Shared: ${list(fields.map(f => FIELD_LABEL[f]))}.`, 'action', [], null);
    const extra = not_needed.filter(f => !policy.accepted.includes(f));
    const parts = [missing.length ? `I still need your ${list(missing.map(f => FIELD_LABEL[f]))}.` : matches ? 'Thank you, you are verified.' : 'Those details do not match our records.'];
    if (extra.length) parts.push(`For your security, we never need your ${list(extra.map(f => FIELD_LABEL[f]))} in chat.`);
    P.say(c, now, parts.join(' '), `identity:${matches ? 'verified' : missing.length ? 'missing' : 'mismatch'}`);
    if (matches && !data.offers.some(o => o.case_id === c.case_id && o.stage === 'initial')) P.presentStage(data, c, now, 'initial', 'Here is what I can offer.');
    return { case_id: c.case_id, verified: c.identity.verified, not_needed };
  },

  'offers.accept'(ctx, data, args) {
    const now = ctx.virtual_now;
    const o = byId(data.offers, 'offer_id', args.offer_id, 'Offer');
    const c = writable(byId(data.cases, 'case_id', o.case_id, 'Case'));
    const used = args.confirmation_token && data.confirmations.find(x => x.token === args.confirmation_token && x.offer_id === o.offer_id && x.used_at);
    if (used) return { offer_id: o.offer_id, step: 'accepted', confirmation_token: used.token, summary: null, commitment_id: used.commitment_id };
    const view = offerView(o, now);
    if (view.state === 'expired') fail('too_late', `Offer ${o.offer_id} has expired.`);
    if (o.state === 'unavailable') fail('unavailable', `Offer ${o.offer_id} is no longer available.`);
    if (o.state !== 'presented') fail('invalid_state', `Offer ${o.offer_id} is ${o.state}.`);
    const rivals = data.offers.filter(x => x.case_id === o.case_id && x.offer_id !== o.offer_id && o.group && x.group === o.group && x.state === 'presented');
    const perform_by = o.perform_days === null ? null : addDays(now, o.perform_days);
    if (!args.confirmation_token) {
      const t = token(o.offer_id, data.confirmations.length, now);
      data.confirmations.push({ token: t, offer_id: o.offer_id, case_id: o.case_id, issued_at: now, used_at: null, commitment_id: null });
      return { offer_id: o.offer_id, step: 'confirm', confirmation_token: t, commitment_id: null,
        summary: { title: o.title, terms: o.terms, value: copy(o.value), conditions: copy(o.conditions), perform_by, group_closes: rivals.map(x => x.offer_id) } };
    }
    const pending = data.confirmations.filter(x => x.offer_id === o.offer_id && !x.used_at).at(-1);
    if (!pending || pending.token !== args.confirmation_token) fail('confirmation_mismatch', 'The confirmation token is wrong or out of date.');
    const commitment_id = nextId('cm', new Set(data.commitments.map(m => m.commitment_id)));
    data.commitments.push({ commitment_id, offer_id: o.offer_id, case_id: c.case_id, provider_id: data.provider.provider_id, account_ref: c.account_ref,
      kind: o.kind, value: copy(o.value), conditional: o.conditions.length > 0, accepted_at: now, perform_by, status: 'pending', reports: [],
      history: [{ at: now, status: 'pending', event_id: null, note: 'Accepted with confirmation.' }], contest: null });
    o.state = 'accepted';
    for (const x of rivals) x.state = 'unavailable';
    Object.assign(pending, { used_at: now, commitment_id });
    const confirmed = `Your ${o.title}${o.value ? ` (${money(o.value)})` : ''} is confirmed${perform_by ? ` and is due by ${perform_by.slice(0, 10)}` : ''}.`;
    P.say(c, now, confirmed, 'offer:accepted');
    P.queueCopy(data, now, 'commitment_confirmed', c, commitment_id, `${o.title} confirmed`, `${confirmed}\nCommitment ${commitment_id}. ${o.terms}`);
    return { offer_id: o.offer_id, step: 'accepted', confirmation_token: pending.token, summary: null, commitment_id };
  },

  'offers.decline'(ctx, data, args) {
    const now = ctx.virtual_now;
    const o = byId(data.offers, 'offer_id', args.offer_id, 'Offer');
    const c = writable(byId(data.cases, 'case_id', o.case_id, 'Case'));
    if (offerView(o, now).state === 'expired') fail('too_late', `Offer ${o.offer_id} has expired.`);
    if (o.state !== 'presented') fail('invalid_state', `Offer ${o.offer_id} is ${o.state}.`);
    o.state = 'declined';
    P.say(c, now, `Understood. I have noted that you declined the ${o.title}.`, 'offer:declined');
    return { offer_id: o.offer_id, state: 'declined' };
  },

  'commitments.contest'(ctx, data, args) {
    const now = ctx.virtual_now;
    const m = byId(data.commitments, 'commitment_id', args.commitment_id, 'Commitment');
    if (!['pending', 'reported_performed', 'partially_reported'].includes(m.status)) fail('invalid_state', `Commitment ${m.commitment_id} is ${m.status} and cannot be contested.`);
    m.contest = { at: now, reason: args.reason, prior_status: m.status, answered_at: null, outcome: null };
    m.status = 'contested';
    m.history.push({ at: now, status: 'contested', event_id: null, note: args.reason });
    const c = data.cases.find(x => x.case_id === m.case_id);
    if (c && c.status !== 'closed') P.say(c, now, 'We have opened a review of this commitment and will answer in this case.', 'commitment:contested');
    return { commitment_id: m.commitment_id, commitment_status: 'contested' };
  },

  'preferences.update'(ctx, data, args) {
    data.preferences.email_copies = args.email_copies;
    return { preferences: copy(data.preferences) };
  }
};

function handleTool(ctx, data, name, args) {
  const view = read(ctx, data, name, args);
  if (view) return { data, result: view };
  const op = writes[name.slice(APP.length + 1)];
  if (!name.startsWith(APP + '.') || !op) fail('unknown_tool', `Unknown Counterline operation: ${name}.`);
  const result = op(ctx, data, args);
  log(ctx, `${name}`, { result: Object.keys(result) });
  return { data, result };
}
module.exports = { handleTool };
