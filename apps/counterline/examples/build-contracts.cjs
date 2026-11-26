'use strict';
// Generates tools.json, schemas/seed.schema.json, schemas/events.schema.json and the
// operation list in contribution/contribution.json from one set of definitions.
// Run: node examples/build-contracts.cjs        (write)
//      node examples/build-contracts.cjs --check (fail on drift)
const fs = require('node:fs');
const path = require('node:path');
const APP = 'counterline';
const root = path.resolve(__dirname, '..');

// ---------- primitives ----------
const id = { type: 'string', pattern: '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$' };
const time = { type: 'string', format: 'date-time' };
const text = (max = 4000) => ({ type: 'string', minLength: 1, maxLength: max });
const nullable = s => ({ anyOf: [s, { type: 'null' }] });
const arr = s => ({ type: 'array', items: s });
const obj = (properties, required = Object.keys(properties)) =>
  ({ type: 'object', properties, required, additionalProperties: false });
const version = obj({ epoch: { type: 'integer', minimum: 1 }, revision: { type: 'integer', minimum: 0 } });
const money = obj({ amount_minor: { type: 'integer', minimum: 0 }, currency: { type: 'string', pattern: '^[A-Z]{3}$' } });

// ---------- business records ----------
const IDENTITY_FIELDS = ['full_name', 'last_four', 'billing_zip', 'date_of_birth', 'full_card_number', 'ssn', 'one_time_code'];
const department = obj({
  department_id: id, name: text(120), aliases: arr(text(120)),
  tier: { enum: ['frontline', 'specialist'] }, transfer: { enum: ['allowed', 'refused'] }
});
const topic = obj({ topic_id: id, title: text(200), greeting_script_id: id, identity_required: { type: 'boolean' } });
const script = obj({ script_id: id, text: text() });
const OFFER_KINDS = ['statement_credit', 'conditional_credit', 'fee_waiver', 'refund', 'product_change', 'hold'];
const TIERS = ['frontline', 'specialist'];
const STAGES = ['initial', 'better', 'transfer'];
// The provider's offer catalog: what a representative may present, at which tier and stage of the chat.
const catalogOffer = obj({
  catalog_id: id, topic_id: id, tier: { enum: TIERS }, stage: { enum: STAGES }, kind: { enum: OFFER_KINDS },
  title: text(200), terms: text(), value: nullable(money), conditions: arr(text(400)), group: nullable(id),
  expires_hours: nullable({ type: 'integer', minimum: 1, maximum: 8760 }), perform_days: nullable({ type: 'integer', minimum: 0, maximum: 365 })
});
const provider = obj({
  provider_id: id, name: text(120),
  kind: { enum: ['card_issuer', 'internet_provider', 'membership_club', 'other'] },
  time_zone: text(64), reopen_days: { type: 'integer', minimum: 0, maximum: 365 },
  identity_policy: obj({ required: arr({ enum: IDENTITY_FIELDS }), accepted: arr({ enum: IDENTITY_FIELDS }) }),
  departments: arr(department), topics: arr(topic), scripts: arr(script), offer_catalog: arr(catalogOffer)
});
// What the provider holds about the customer, used only to check identity data the customer provides.
const customerRecord = obj({ full_name: text(120), last_four: text(4), billing_zip: text(10), date_of_birth: nullable(text(10)) });
const disclosure = obj({ at: time, fields: arr({ enum: IDENTITY_FIELDS }), not_needed: arr({ enum: IDENTITY_FIELDS }), matched: { type: 'boolean' } });
const article = obj({ article_id: id, title: text(200), body: text(8000), tags: arr(text(60)) });
const turn = obj({
  turn_id: id, at: time, speaker: { enum: ['customer', 'representative'] }, text: text(),
  source: { enum: ['text', 'action', 'script', 'system'] }, recognized: arr(text(80)), rule: nullable(text(120))
});
const CASE_STATUS = ['open', 'waiting_on_customer', 'escalated', 'resolved', 'closed'];
const caseRecord = obj({
  case_id: id, topic_id: id, account_ref: text(120), status: { enum: CASE_STATUS },
  tier: { enum: TIERS }, opened_at: time, closed_at: nullable(time),
  identity: obj({ verified: { type: 'boolean' }, disclosures: arr(disclosure) }), transcript: arr(turn)
});
const offer = obj({
  offer_id: id, case_id: id, catalog_id: nullable(id), stage: nullable({ enum: STAGES }), kind: { enum: OFFER_KINDS }, title: text(200), terms: text(),
  value: nullable(money), conditions: arr(text(400)), group: nullable(id),
  tier: { enum: TIERS }, presented_at: time, expires_at: nullable(time), perform_days: nullable({ type: 'integer', minimum: 0, maximum: 365 }),
  state: { enum: ['presented', 'accepted', 'declined', 'unavailable'] }
});
const COMMITMENT_STATUS = ['pending', 'reported_performed', 'partially_reported', 'condition_missed', 'revoked', 'contested'];
const report = obj({
  event_id: id, at: time, reference_id: id, amount_minor: { type: 'integer', minimum: 0 },
  currency: { type: 'string', pattern: '^[A-Z]{3}$' }
});
const commitmentHistory = obj({ at: time, status: { enum: COMMITMENT_STATUS }, event_id: nullable(id), note: nullable(text(400)) });
const commitment = obj({
  commitment_id: id, offer_id: id, case_id: id, provider_id: id, account_ref: text(120),
  kind: { enum: OFFER_KINDS }, value: nullable(money), conditional: { type: 'boolean' },
  accepted_at: time, perform_by: nullable(time), status: { enum: COMMITMENT_STATUS },
  reports: arr(report), history: arr(commitmentHistory),
  contest: nullable(obj({ at: time, reason: text(1000), prior_status: { enum: COMMITMENT_STATUS }, answered_at: nullable(time), outcome: nullable({ enum: ['reissued', 'upheld'] }) }))
});
const confirmation = obj({ token: id, offer_id: id, case_id: id, issued_at: time, used_at: nullable(time), commitment_id: nullable(id) });
const preferences = obj({ email_copies: { type: 'boolean' } });
// Plain-text copies for Mail, queued only while email_copies is on. Title, body and time are frozen,
// so a retry publishes identical bytes; Infra records each Messaging outcome by event.
const DELIVERY = ['committed', 'rejected', 'unknown', 'halted'];
const notification = obj({
  notification_id: id, kind: { enum: ['offer_presented', 'commitment_confirmed'] }, case_id: id, ref_id: id, title: text(200), body: text(),
  time, recipient_person_id: id, status: { enum: ['pending_delivery', 'delivered', 'delivery_failed', 'delivery_unknown'] },
  outcome: nullable(obj({ status: { enum: DELIVERY }, code: nullable(text(120)), router_event_id: nullable(text(200)), recorded_at: time }))
});
const seed = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  ...obj({
    account_id: id, owner_person_id: id, provider, customer_record: customerRecord, preferences,
    help_articles: arr(article), cases: arr(caseRecord), offers: arr(offer), commitments: arr(commitment), confirmations: arr(confirmation), outbox: arr(notification)
  })
};

// ---------- read views (derived fields added on read) ----------
const offerView = obj({ ...offer.properties, state: { enum: ['presented', 'accepted', 'declined', 'unavailable', 'expired'] } });
const commitmentView = obj({ ...commitment.properties, overdue: { type: 'boolean' } });
const articleSummary = obj({ article_id: id, title: text(200), tags: arr(text(60)) });
const caseSummary = obj({
  case_id: id, topic_id: id, account_ref: text(120), status: { enum: CASE_STATUS },
  tier: { enum: TIERS }, opened_at: time, closed_at: nullable(time)
});
const ACTIONS = ['explain_terms', 'ask_for_better_offer', 'ask_status', 'request_transfer', 'end_chat'];
const action = obj({ action: { enum: ACTIONS }, label: text(80), needs_department: { type: 'boolean' } });
const caseView = obj({ ...caseRecord.properties, available_actions: arr(action) });
const topicSummary = obj({ topic_id: id, title: text(200) });
const acceptSummary = obj({ title: text(200), terms: text(), value: nullable(money), conditions: arr(text(400)), perform_by: nullable(time), group_closes: arr(id) });
const fieldsInput = { type: 'object', properties: Object.fromEntries(IDENTITY_FIELDS.map(f => [f, text(200)])), additionalProperties: false };

// ---------- tools ----------
const writeInput = (props, required) => obj({ expected_version: version, request_id: id, ...props }, ['expected_version', 'request_id', ...required]);
const readOut = props => obj({ status: { const: 'ok' }, app_id: { const: APP }, version, ...props });
const writeOut = props => {
  const o = obj({ status: { const: 'committed' }, app_id: { const: APP }, version, ...props });
  o.properties.duplicate = { type: 'boolean' };
  return o;
};
const tool = (name, description, read_only, inputSchema, outputSchema) =>
  ({ name: `${APP}.${name}`, description, read_only, scope: `${APP}.${name}`, resource_target: 'current account', inputSchema, outputSchema });

const tools = [
  tool('help.search', 'Search the provider help center by words in titles, bodies and tags. Read-only.', true,
    obj({ query: { type: 'string', minLength: 0, maxLength: 200 } }, []), readOut({ articles: arr(articleSummary) })),
  tool('help.get', 'Read one help article. Read-only.', true,
    obj({ article_id: id }), readOut({ article })),
  tool('cases.list', 'List the customer\'s support cases, optionally by status, with the provider\'s name, the topics a new case can be opened on and the customer\'s notification preferences. Read-only.', true,
    obj({ status: { enum: CASE_STATUS } }, []), readOut({ provider: obj({ name: text(120), kind: provider.properties.kind, time_zone: text(64) }), cases: arr(caseSummary), topics: arr(topicSummary), preferences })),
  tool('cases.get', 'Read one case with its transcript, the offers presented in it and the quick actions the chat offers now. Offers past their expiry read "expired". Read-only.', true,
    obj({ case_id: id }), readOut({ case: caseView, offers: arr(offerView), now: time })),
  tool('offers.get', 'Read one presented offer with its terms and conditions. Read-only.', true,
    obj({ offer_id: id }), readOut({ offer: offerView, now: time })),
  tool('commitments.list', 'List the provider\'s commitments to this customer with status, reports and an overdue flag. Read-only.', true,
    obj({ status: { enum: COMMITMENT_STATUS } }, []), readOut({ commitments: arr(commitmentView), now: time })),
  tool('commitments.get', 'Read one commitment with its performance reports and history. Read-only.', true,
    obj({ commitment_id: id }), readOut({ commitment: commitmentView, now: time })),
  tool('cases.open', 'Open a support case on one of the provider\'s topics for an account reference, with a first message. The representative answers with the topic greeting.', false,
    writeInput({ topic_id: id, account_ref: text(120), message: text() }, ['topic_id', 'account_ref', 'message']),
    writeOut({ case_id: id })),
  tool('cases.send_message', 'Write a plain-language message in a case. The representative answers every request it recognizes, in order; anything else gets an acknowledgement that lists the available actions. A message never accepts, declines or discloses anything.', false,
    writeInput({ case_id: id, text: text() }, ['case_id', 'text']), writeOut({ case_id: id, recognized: arr(text(80)), turns_added: { type: 'integer', minimum: 1 } })),
  tool('cases.take_action', 'Use one of the quick actions the case lists now in available_actions. request_transfer takes a department name.', false,
    writeInput({ case_id: id, action: { enum: ACTIONS }, department: text(120) }, ['case_id', 'action']),
    writeOut({ case_id: id, action: { enum: ACTIONS }, turns_added: { type: 'integer', minimum: 1 } })),
  tool('cases.close', 'Close a case. A closed case takes no writes until it is reopened.', false,
    writeInput({ case_id: id }, ['case_id']), writeOut({ case_id: id, case_status: { enum: CASE_STATUS } })),
  tool('cases.reopen', 'Reopen a closed case within the provider\'s reopen window.', false,
    writeInput({ case_id: id }, ['case_id']), writeOut({ case_id: id, case_status: { enum: CASE_STATUS } })),
  tool('identity.provide', 'Give the representative selected identity fields for a case. Every field given is recorded as disclosed, including fields the provider does not need.', false,
    writeInput({ case_id: id, fields: fieldsInput }, ['case_id', 'fields']),
    writeOut({ case_id: id, verified: { type: 'boolean' }, not_needed: arr({ enum: IDENTITY_FIELDS }) })),
  tool('offers.accept', 'Accept a presented offer in two steps. Without confirmation_token, returns a summary and a token and changes no offer. With that token, creates the commitment.', false,
    writeInput({ offer_id: id, confirmation_token: id }, ['offer_id']),
    writeOut({ offer_id: id, step: { enum: ['confirm', 'accepted'] }, confirmation_token: nullable(id), summary: nullable(acceptSummary), commitment_id: nullable(id) })),
  tool('offers.decline', 'Decline a presented offer.', false,
    writeInput({ offer_id: id }, ['offer_id']), writeOut({ offer_id: id, state: { const: 'declined' } })),
  tool('commitments.contest', 'Contest a commitment, for example when the provider reports a credit the account does not show. The provider answers by event.', false,
    writeInput({ commitment_id: id, reason: text(1000) }, ['commitment_id', 'reason']), writeOut({ commitment_id: id, commitment_status: { const: 'contested' } })),
  tool('preferences.update', 'Turn plain-text email copies of offers and confirmations on or off.', false,
    writeInput({ email_copies: { type: 'boolean' } }, ['email_copies']), writeOut({ preferences }))
];

// ---------- events ----------
const event = (operation, payload) => obj({ event_id: id, at: time, operation: { const: operation }, payload });
const events = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  anyOf: [
    event(`${APP}.commitment.performance_reported`, obj({
      commitment_id: id, provider_id: id, reference_id: id,
      amount_minor: { type: 'integer', minimum: 0 }, currency: { type: 'string', pattern: '^[A-Z]{3}$' },
      status: { const: 'reported' }
    })),
    event(`${APP}.case.followup`, obj({ case_id: id, script_id: id })),
    event(`${APP}.commitment.condition_missed`, obj({ commitment_id: id, reason: text(400) })),
    event(`${APP}.commitment.revoked`, obj({ commitment_id: id, reason: text(400) })),
    event(`${APP}.contest.answered`, obj({ commitment_id: id, outcome: { enum: ['reissued', 'upheld'] }, reference_id: nullable(id) })),
    event(`${APP}.offer.added`, obj({ case_id: id, catalog_id: id })),
    event(`${APP}.notification.delivery_recorded`, obj({ notification_id: id, status: { enum: DELIVERY }, code: nullable(text(120)), stop_run: { type: 'boolean' }, router_event_id: nullable(text(200)) }))
  ]
};
const eventTypes = events.anyOf.map(e => e.properties.operation.const);

// ---------- write or check ----------
const check = process.argv.includes('--check');
const outputs = new Map();
const json = v => JSON.stringify(v, null, 2) + '\n';
outputs.set('tools.json', json(tools));
outputs.set('schemas/seed.schema.json', json(seed));
outputs.set('schemas/events.schema.json', json(events));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8'));
manifest.event_types = eventTypes;
outputs.set('app.json', json(manifest));
const contribution = JSON.parse(fs.readFileSync(path.join(root, 'contribution/contribution.json'), 'utf8'));
contribution.interfaces.find(i => i.interface_id === 'agent-mcp').operations =
  tools.map(t => ({ name: t.name, effect: t.read_only ? 'read' : 'write', caller: 'agent' }));
contribution.events.accepts = eventTypes.map(type => ({ type, schema_ref: 'schemas/events.schema.json', status: 'implemented' }));
outputs.set('contribution/contribution.json', json(contribution));
let drift = [];
for (const [file, content] of outputs) {
  const p = path.join(root, file);
  if (check) { if (!fs.existsSync(p) || fs.readFileSync(p, 'utf8') !== content) drift.push(file); }
  else fs.writeFileSync(p, content);
}
if (drift.length) { console.error('Contract drift: ' + drift.join(', ')); process.exit(1); }
console.log(check ? 'Contracts are up to date.' : 'Wrote ' + [...outputs.keys()].join(', '));
