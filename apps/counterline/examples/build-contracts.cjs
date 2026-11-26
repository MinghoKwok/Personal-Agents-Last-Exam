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
const topic = obj({ topic_id: id, title: text(200), greeting_script_id: id });
const script = obj({ script_id: id, text: text() });
const provider = obj({
  provider_id: id, name: text(120),
  kind: { enum: ['card_issuer', 'internet_provider', 'membership_club', 'other'] },
  time_zone: text(64), reopen_days: { type: 'integer', minimum: 0, maximum: 365 },
  identity_policy: obj({ required: arr({ enum: IDENTITY_FIELDS }), accepted: arr({ enum: IDENTITY_FIELDS }) }),
  departments: arr(department), topics: arr(topic), scripts: arr(script)
});
const article = obj({ article_id: id, title: text(200), body: text(8000), tags: arr(text(60)) });
const turn = obj({
  turn_id: id, at: time, speaker: { enum: ['customer', 'representative'] }, text: text(),
  source: { enum: ['text', 'action', 'script', 'system'] }, recognized: arr(text(80)), rule: nullable(text(120))
});
const CASE_STATUS = ['open', 'waiting_on_customer', 'escalated', 'resolved', 'closed'];
const caseRecord = obj({
  case_id: id, topic_id: id, account_ref: text(120), status: { enum: CASE_STATUS },
  tier: { enum: ['frontline', 'specialist'] }, opened_at: time, closed_at: nullable(time), transcript: arr(turn)
});
const OFFER_KINDS = ['statement_credit', 'conditional_credit', 'fee_waiver', 'refund', 'product_change', 'hold'];
const offer = obj({
  offer_id: id, case_id: id, kind: { enum: OFFER_KINDS }, title: text(200), terms: text(),
  value: nullable(money), conditions: arr(text(400)), group: nullable(id),
  tier: { enum: ['frontline', 'specialist'] }, presented_at: time, expires_at: nullable(time),
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
  reports: arr(report), history: arr(commitmentHistory)
});
const seed = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  ...obj({
    account_id: id, owner_person_id: id, provider,
    help_articles: arr(article), cases: arr(caseRecord), offers: arr(offer), commitments: arr(commitment)
  })
};

// ---------- read views (derived fields added on read) ----------
const offerView = obj({ ...offer.properties, state: { enum: ['presented', 'accepted', 'declined', 'unavailable', 'expired'] } });
const commitmentView = obj({ ...commitment.properties, overdue: { type: 'boolean' } });
const articleSummary = obj({ article_id: id, title: text(200), tags: arr(text(60)) });
const caseSummary = obj({
  case_id: id, topic_id: id, account_ref: text(120), status: { enum: CASE_STATUS },
  tier: { enum: ['frontline', 'specialist'] }, opened_at: time, closed_at: nullable(time)
});

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
  tool('cases.list', 'List the customer\'s support cases, optionally by status. Read-only.', true,
    obj({ status: { enum: CASE_STATUS } }, []), readOut({ cases: arr(caseSummary) })),
  tool('cases.get', 'Read one case with its transcript and the offers presented in it. Offers past their expiry read "expired". Read-only.', true,
    obj({ case_id: id }), readOut({ case: caseRecord, offers: arr(offerView), now: time })),
  tool('offers.get', 'Read one presented offer with its terms and conditions. Read-only.', true,
    obj({ offer_id: id }), readOut({ offer: offerView, now: time })),
  tool('commitments.list', 'List the provider\'s commitments to this customer with status, reports and an overdue flag. Read-only.', true,
    obj({ status: { enum: COMMITMENT_STATUS } }, []), readOut({ commitments: arr(commitmentView), now: time })),
  tool('commitments.get', 'Read one commitment with its performance reports and history. Read-only.', true,
    obj({ commitment_id: id }), readOut({ commitment: commitmentView, now: time })),
  tool('cases.open', 'Open a support case on one of the provider\'s topics for an account reference, with a first message. The representative answers with the topic greeting.', false,
    writeInput({ topic_id: id, account_ref: text(120), message: text() }, ['topic_id', 'account_ref', 'message']),
    writeOut({ case_id: id }))
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
    event(`${APP}.case.followup`, obj({ case_id: id, script_id: id }))
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
