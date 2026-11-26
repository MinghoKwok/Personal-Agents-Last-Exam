'use strict';
// Generates tools.json, schemas/seed.schema.json, schemas/events.schema.json and the
// operation list in contribution/contribution.json from one set of definitions.
// Run: node examples/build-contracts.cjs        (write)
//      node examples/build-contracts.cjs --check (fail on drift)
//
// This task-owned portal is a subset of the Casefold design (PR #219's sibling, #222):
// the same case / submission / receipt records and operation names, without request
// items or reviewer events, which Task #102 does not use.
const fs = require('node:fs');
const path = require('node:path');
const APP = 'cpa-portal';
const root = path.resolve(__dirname, '..');

const id = { type: 'string', pattern: '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$' };
const time = { type: 'string', format: 'date-time' };
const text = (max = 2000) => ({ type: 'string', minLength: 1, maxLength: max });
const nullable = s => ({ anyOf: [s, { type: 'null' }] });
const arr = (s, extra = {}) => ({ type: 'array', items: s, ...extra });
const obj = (properties, required = Object.keys(properties)) =>
  ({ type: 'object', properties, required, additionalProperties: false });
const version = obj({ epoch: { type: 'integer', minimum: 1 }, revision: { type: 'integer', minimum: 0 } });
const sha = { type: 'string', pattern: '^[a-f0-9]{64}$' };
const filename = { type: 'string', minLength: 1, maxLength: 160, pattern: '^[^\\\\/\\u0000-\\u001f\\u007f]+$' };
const MIME = ['application/pdf', 'text/plain', 'text/csv', 'application/json'];
const mime = { enum: MIME };

const firm = obj({
  firm_id: id, name: text(120), time_zone: text(64),
  accepted_types: arr(mime, { minItems: 1 }),
  max_file_bytes: { type: 'integer', minimum: 1, maximum: 1048576 },
  max_case_bytes: { type: 'integer', minimum: 1, maximum: 4194304 }
});
const CASE_STATUS = ['open', 'locked', 'closed'];
const caseRecord = obj({
  case_id: id, title: text(200), status: { enum: CASE_STATUS },
  access: { enum: ['upload', 'view', 'none'] }, opened_at: time, cutoff: nullable(time),
  late_submission_policy: { enum: ['reject', 'archive_only', 'accept_for_review'] }
});
const storedFile = obj({ file_id: id, filename, mime_type: mime, size: { type: 'integer', minimum: 0 }, sha256: sha, base64: { type: 'string' } });
const fileMeta = obj({ file_id: id, filename, mime_type: mime, size: { type: 'integer', minimum: 0 }, sha256: sha });
const STANDING = ['on_time', 'late_for_review', 'late_archived'];
const submission = obj({
  submission_id: id, case_id: id, request_ids: arr(id), submitted_at: time,
  actor: { enum: ['client', 'assistant'] }, standing: { enum: STANDING },
  replaces: arr(id), superseded_by: nullable(id), withdrawn_at: nullable(time),
  note: nullable(text(1000)), files: arr(storedFile, { minItems: 1, maxItems: 8 })
});
const receipt = obj({
  receipt_id: id, submission_id: id, case_id: id, at: time, kind: { enum: ['submitted', 'withdrawn'] },
  standing: { enum: STANDING }, files: arr(fileMeta)
});
const seed = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  ...obj({ account_id: id, owner_person_id: id, firm, cases: arr(caseRecord), submissions: arr(submission), receipts: arr(receipt) })
};

// Read views: stored bytes appear only in submissions.read.
const STATE = ['active', 'superseded', 'withdrawn'];
const submissionView = obj({
  submission_id: id, case_id: id, request_ids: arr(id), submitted_at: time, actor: { enum: ['client', 'assistant'] },
  standing: { enum: STANDING }, state: { enum: STATE }, replaces: arr(id), superseded_by: nullable(id),
  withdrawn_at: nullable(time), note: nullable(text(1000)), files: arr(fileMeta)
});
const caseView = obj({ ...caseRecord.properties, after_cutoff: { type: 'boolean' }, active_submissions: { type: 'integer', minimum: 0 }, stored_bytes: { type: 'integer', minimum: 0 } });

const writeInput = (props, required) => obj({ expected_version: version, request_id: id, ...props }, ['expected_version', 'request_id', ...required]);
const readOut = props => obj({ status: { const: 'ok' }, app_id: { const: APP }, version, ...props });
const writeOut = props => {
  const o = obj({ status: { const: 'committed' }, app_id: { const: APP }, version, ...props });
  o.properties.duplicate = { type: 'boolean' };
  return o;
};
const tool = (name, description, read_only, inputSchema, outputSchema) =>
  ({ name: `${APP}.${name}`, description, read_only, scope: `${APP}.${name}`, resource_target: 'current account', inputSchema, outputSchema });
const uploadFile = obj({ filename, mime_type: mime, base64: { type: 'string', minLength: 1, maxLength: 1398104 }, sha256: sha }, ['filename', 'mime_type', 'base64']);

const tools = [
  tool('cases.list', 'List the client\'s cases at the firm with status, access, cutoff and counts. Read-only.', true,
    obj({}, []), readOut({ cases: arr(caseView), now: time })),
  tool('cases.get', 'Read one case with its active submissions (file names, sizes and SHA-256, no bytes). Read-only.', true,
    obj({ case_id: id }), readOut({ case: caseView, submissions: arr(submissionView), now: time })),
  tool('submissions.list', 'List the submissions of a case. Superseded and withdrawn submissions are included only when asked. Read-only.', true,
    obj({ case_id: id, include_inactive: { type: 'boolean' } }, ['case_id']), readOut({ submissions: arr(submissionView) })),
  tool('submissions.get', 'Read one submission with its files\' metadata and its state. Read-only.', true,
    obj({ submission_id: id }), readOut({ submission: submissionView })),
  tool('submissions.read', 'Read back the exact bytes the portal stored for one file of a submission, with the SHA-256 the portal computed. Read-only.', true,
    obj({ submission_id: id, file_id: id }), readOut({ file: storedFile })),
  tool('receipts.list', 'List the portal receipts for a case, oldest first. Read-only.', true,
    obj({ case_id: id }), readOut({ receipts: arr(receipt) })),
  tool('receipts.get', 'Read one portal receipt. Read-only.', true,
    obj({ receipt_id: id }), readOut({ receipt })),
  tool('submissions.add', 'Submit 1 to 8 files to a case the client can upload to. The portal stores the bytes, computes each SHA-256 (a supplied sha256 is only checked against it) and returns a receipt. "replaces" lists active submissions of the same case that this one supersedes.', false,
    writeInput({ case_id: id, files: arr(uploadFile, { minItems: 1, maxItems: 8 }), replaces: arr(id), note: text(1000) }, ['case_id', 'files']),
    writeOut({ submission_id: id, receipt_id: id, standing: { enum: STANDING }, files: arr(fileMeta) })),
  tool('submissions.withdraw', 'Withdraw an active submission of an open case. Its files stay readable in history and a withdrawal receipt is issued.', false,
    writeInput({ submission_id: id, reason: text(1000) }, ['submission_id']),
    writeOut({ submission_id: id, receipt_id: id }))
];

// No incoming events: the schema accepts no real operation, and applyEvent rejects every event.
const events = { $schema: 'https://json-schema.org/draft/2020-12/schema', ...obj({ event_id: id, at: time, operation: { const: `${APP}.no_events` }, payload: obj({}, []) }) };

const check = process.argv.includes('--check');
const outputs = new Map();
const json = v => JSON.stringify(v, null, 2) + '\n';
outputs.set('tools.json', json(tools));
outputs.set('schemas/seed.schema.json', json(seed));
outputs.set('schemas/events.schema.json', json(events));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8'));
Object.assign(manifest, {
  app_id: APP, version: '0.1.0', maintainer: { contact: 'Task #102 (tax-packet); repository issue or PR tagged task:tax-packet' },
  event_types: [], capabilities: { modes: ['synthetic'], resources: false, ui: 'none', real_delivery: false },
  limitations: [
    'Task-owned subset of the Casefold client portal (#222): cases, submissions, receipts and read-back; no request items or reviewer events.',
    'Received bytes are kept in the App\'s business data (no Core asset registration); per-file and per-case byte limits apply.',
    'MCP only in this task package.'
  ]
});
outputs.set('app.json', json(manifest));
const contribution = JSON.parse(fs.readFileSync(path.join(root, 'contribution/contribution.json'), 'utf8'));
contribution.app_id = APP;
contribution.app_categories = ['external'];
contribution.interfaces.find(i => i.interface_id === 'agent-mcp').operations =
  tools.map(t => ({ name: t.name, effect: t.read_only ? 'read' : 'write', caller: 'agent' }));
contribution.events.accepts = [];
outputs.set('contribution/contribution.json', json(contribution));
const drift = [];
for (const [file, content] of outputs) {
  const p = path.join(root, file);
  if (check) { if (!fs.existsSync(p) || fs.readFileSync(p, 'utf8') !== content) drift.push(file); }
  else fs.writeFileSync(p, content);
}
if (drift.length) { console.error('Contract drift: ' + drift.join(', ')); process.exit(1); }
console.log(check ? 'Contracts are up to date.' : 'Wrote ' + [...outputs.keys()].join(', '));
