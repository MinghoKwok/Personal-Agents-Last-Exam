'use strict';
// Seed validation and record enumeration for Core.
const crypto = require('node:crypto');
const { fail, unique, ms } = require('./util.cjs');
function validateSeed(ctx, data) {
  const person = ctx.binding.people.some(p => p.person_id === data.owner_person_id);
  const account = ctx.binding.accounts.some(a => a.app_id === ctx.app_id && a.account_id === data.account_id && a.owner_person_id === data.owner_person_id);
  if (!person || !account) fail('invalid_seed', 'Account and owner must exist in the supplied binding.');
  unique(data.cases, 'case_id', 'case');
  unique(data.submissions, 'submission_id', 'submission');
  unique(data.receipts, 'receipt_id', 'receipt');
  const cases = new Map(data.cases.map(c => [c.case_id, c]));
  const subs = new Map(data.submissions.map(s => [s.submission_id, s]));
  for (const s of data.submissions) {
    if (!cases.has(s.case_id)) fail('invalid_seed', `Submission ${s.submission_id} names an unknown case.`);
    unique(s.files, 'file_id', 'file');
    for (const f of s.files) {
      const bytes = Buffer.from(f.base64, 'base64');
      if (bytes.toString('base64') !== f.base64 || bytes.length !== f.size || crypto.createHash('sha256').update(bytes).digest('hex') !== f.sha256) {
        fail('invalid_seed', `File ${f.file_id} does not match its stored size or SHA-256.`);
      }
    }
    for (const rid of s.replaces) {
      const old = subs.get(rid);
      if (!old || old.case_id !== s.case_id || old.superseded_by !== s.submission_id) fail('invalid_seed', `Submission ${s.submission_id} replaces ${rid} inconsistently.`);
    }
    if (s.superseded_by && !(subs.get(s.superseded_by)?.replaces || []).includes(s.submission_id)) fail('invalid_seed', `Submission ${s.submission_id} names a successor that does not replace it.`);
    if (s.withdrawn_at && ms(s.withdrawn_at) < ms(s.submitted_at)) fail('invalid_seed', `Submission ${s.submission_id} is withdrawn before it was submitted.`);
  }
  for (const r of data.receipts) {
    const s = subs.get(r.submission_id);
    if (!s || s.case_id !== r.case_id) fail('invalid_seed', `Receipt ${r.receipt_id} names an unknown submission or the wrong case.`);
  }
}
const records = data => [...data.cases, ...data.submissions, ...data.receipts];
const objects = data => [...data.cases.map(c => c.case_id), ...data.submissions.map(s => s.submission_id), ...data.receipts.map(r => r.receipt_id)];
module.exports = { validateSeed, records, objects, references: () => [] };
