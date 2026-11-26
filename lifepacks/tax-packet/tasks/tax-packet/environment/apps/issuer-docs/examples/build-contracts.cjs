'use strict';
// Generates tools.json, seed/events schemas and the operation list in contribution.json.
// Run: node examples/build-contracts.cjs [--check]
const fs = require('node:fs');
const path = require('node:path');
const APP = 'issuer-docs';
const root = path.resolve(__dirname, '..');
const id = { type: 'string', pattern: '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$' };
const time = { type: 'string', format: 'date-time' };
const text = (max = 400) => ({ type: 'string', minLength: 1, maxLength: max });
const nullable = s => ({ anyOf: [s, { type: 'null' }] });
const arr = s => ({ type: 'array', items: s });
const obj = (properties, required = Object.keys(properties)) => ({ type: 'object', properties, required, additionalProperties: false });
const version = obj({ epoch: { type: 'integer', minimum: 1 }, revision: { type: 'integer', minimum: 0 } });
const sha = { type: 'string', pattern: '^[a-f0-9]{64}$' };
const filename = { type: 'string', minLength: 1, maxLength: 160, pattern: '^[^\\\\/\\u0000-\\u001f\\u007f]+$' };
const mime = { enum: ['application/pdf', 'text/plain'] };
const KIND = ['tax_form', 'statement', 'letter'];

const institution = obj({ institution_id: id, name: text(120), time_zone: text(64) });
const account = obj({ account_ref: id, label: text(120), last_four: { type: 'string', pattern: '^[0-9]{4}$' }, status: { enum: ['open', 'closed'] }, closed_on: nullable({ type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$' }) });
const docMeta = {
  document_id: id, account_ref: id, kind: { enum: KIND }, title: text(200), tax_year: nullable({ type: 'integer', minimum: 2000, maximum: 2100 }),
  issued_at: time, available_from: time, filename, mime_type: mime, size: { type: 'integer', minimum: 1 }, sha256: sha
};
const document = obj({ ...docMeta, base64: { type: 'string', minLength: 1 } });
const seed = { $schema: 'https://json-schema.org/draft/2020-12/schema', ...obj({ account_id: id, owner_person_id: id, institution, accounts: arr(account), documents: arr(document) }) };
const docView = obj(docMeta);
const fileOut = obj({ document_id: id, filename, mime_type: mime, size: { type: 'integer', minimum: 1 }, sha256: sha, base64: { type: 'string' } });

const readOut = props => obj({ status: { const: 'ok' }, app_id: { const: APP }, version, ...props });
const tool = (name, description, inputSchema, outputSchema) =>
  ({ name: `${APP}.${name}`, description, read_only: true, scope: `${APP}.${name}`, resource_target: 'current account', inputSchema, outputSchema });
const tools = [
  tool('accounts.list', 'List the customer\'s accounts at this institution, including closed ones. Read-only.', obj({}, []), readOut({ institution, accounts: arr(account), now: time })),
  tool('documents.list', 'List the documents available now for one account, newest first, optionally by kind or tax year. A document that is not yet available is not listed. Read-only.',
    obj({ account_ref: id, kind: { enum: KIND }, tax_year: { type: 'integer', minimum: 2000, maximum: 2100 } }, ['account_ref']), readOut({ documents: arr(docView), now: time })),
  tool('documents.download', 'Download one available document: its bytes and SHA-256. Read-only.', obj({ document_id: id }), readOut({ file: fileOut }))
];
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
  limitations: ['Task-owned, read-only document page of one fictional institution: list and download per account.',
    'A document appears when the virtual clock reaches its available_from time; no events are needed.', 'MCP only in this task package.']
});
outputs.set('app.json', json(manifest));
const contribution = JSON.parse(fs.readFileSync(path.join(root, 'contribution/contribution.json'), 'utf8'));
contribution.app_id = APP;
contribution.app_categories = ['external'];
contribution.interfaces.find(i => i.interface_id === 'agent-mcp').operations = tools.map(t => ({ name: t.name, effect: 'read', caller: 'agent' }));
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
