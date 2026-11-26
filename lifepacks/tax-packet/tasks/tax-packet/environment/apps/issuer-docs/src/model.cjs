'use strict';
const crypto = require('node:crypto');
const { fail, unique, ms } = require('./util.cjs');
function validateSeed(ctx, data) {
  const person = ctx.binding.people.some(p => p.person_id === data.owner_person_id);
  const account = ctx.binding.accounts.some(a => a.app_id === ctx.app_id && a.account_id === data.account_id && a.owner_person_id === data.owner_person_id);
  if (!person || !account) fail('invalid_seed', 'Account and owner must exist in the supplied binding.');
  unique(data.accounts, 'account_ref', 'account');
  unique(data.documents, 'document_id', 'document');
  const refs = new Set(data.accounts.map(a => a.account_ref));
  for (const a of data.accounts) if ((a.status === 'closed') !== (a.closed_on !== null)) fail('invalid_seed', `Account ${a.account_ref} closed_on must be set exactly when it is closed.`);
  for (const d of data.documents) {
    if (!refs.has(d.account_ref)) fail('invalid_seed', `Document ${d.document_id} names an unknown account.`);
    if (ms(d.available_from) < ms(d.issued_at)) fail('invalid_seed', `Document ${d.document_id} is available before it is issued.`);
    const bytes = Buffer.from(d.base64, 'base64');
    if (bytes.toString('base64') !== d.base64 || bytes.length !== d.size || crypto.createHash('sha256').update(bytes).digest('hex') !== d.sha256) fail('invalid_seed', `Document ${d.document_id} does not match its size or SHA-256.`);
    if (d.mime_type === 'application/pdf' && bytes.subarray(0, 5).toString('latin1') !== '%PDF-') fail('invalid_seed', `Document ${d.document_id} is not a PDF.`);
  }
}
const records = data => [...data.accounts, ...data.documents];
const objects = data => [...data.accounts.map(a => a.account_ref), ...data.documents.map(d => d.document_id)];
module.exports = { validateSeed, records, objects, references: () => [] };
