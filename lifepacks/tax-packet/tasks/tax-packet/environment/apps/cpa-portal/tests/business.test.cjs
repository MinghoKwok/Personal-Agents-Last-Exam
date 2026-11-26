'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const plugin = require('../plugin.cjs');
const { fixture } = require('./harness.cjs');
const CASE = 'CP-2025-ROWAN';
const pdf = (body = 'SYNTHETIC BENCHMARK NOT FOR FILING') => {
  const bytes = Buffer.from(`%PDF-1.4\n% ${body}\n%%EOF\n`, 'latin1');
  return { bytes, file: name => ({ filename: name, mime_type: 'application/pdf', base64: bytes.toString('base64') }) };
};
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function unchanged(f, fn, pattern) { const before = f.data; assert.throws(fn, pattern); assert.deepEqual(f.data, before); }

test('reads list cases, show no bytes and change nothing', () => {
  const f = fixture();
  const before = f.data;
  const cases = f.call('cpa-portal.cases.list').cases;
  assert.deepEqual(cases.map(c => [c.case_id, c.status, c.access]), [[CASE, 'open', 'upload'], ['CP-2024-ROWAN', 'closed', 'view']]);
  const old = f.call('cpa-portal.cases.get', { case_id: 'CP-2024-ROWAN' }).submissions[0];
  assert.equal(old.files[0].base64, undefined);
  assert.deepEqual(f.data, before);
});

test('a submission stores the bytes, computes SHA-256 and returns a matching receipt', () => {
  const f = fixture();
  const a = pdf('W-2 Atlas'), b = pdf('1099-INT Cedar');
  const out = f.call('cpa-portal.submissions.add', { case_id: CASE, files: [a.file('w2-atlas.pdf'), b.file('1099-int-cedar.pdf')], note: 'packet v1' });
  assert.deepEqual(out.files.map(x => x.sha256), [sha(a.bytes), sha(b.bytes)]);
  const receipt = f.call('cpa-portal.receipts.get', { receipt_id: out.receipt_id }).receipt;
  assert.equal(receipt.kind, 'submitted');
  assert.deepEqual(receipt.files.map(x => x.sha256), out.files.map(x => x.sha256));
  const back = f.call('cpa-portal.submissions.read', { submission_id: out.submission_id, file_id: out.files[0].file_id }).file;
  assert.equal(Buffer.from(back.base64, 'base64').compare(a.bytes), 0);
  assert.equal(back.sha256, sha(a.bytes));
});

test('a supplied SHA-256 is only checked; a mismatch stores nothing', () => {
  const f = fixture();
  const a = pdf();
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [{ ...a.file('x.pdf'), sha256: '0'.repeat(64) }] }), /does not match the bytes/);
  const ok = f.call('cpa-portal.submissions.add', { case_id: CASE, files: [{ ...a.file('x.pdf'), sha256: sha(a.bytes) }] });
  assert.equal(ok.files[0].sha256, sha(a.bytes));
});

test('type, content, size and access are enforced without partial writes', () => {
  const f = fixture();
  const a = pdf();
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [{ filename: 'x.pdf', mime_type: 'application/pdf', base64: Buffer.from('not a pdf').toString('base64') }] }), /does not match its type/);
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: 'CP-2024-ROWAN', files: [a.file('x.pdf')] }), /closed/);
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: 'CP-9999', files: [a.file('x.pdf')] }), /does not exist/);
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [a.file('x.pdf'), a.file('x.pdf')] }), /Duplicate file name/);
  const big = Buffer.concat([Buffer.from('%PDF-1.4\n'), Buffer.alloc(300000, 32)]);
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [{ filename: 'big.pdf', mime_type: 'application/pdf', base64: big.toString('base64') }] }), /larger than/);
});

test('replaces supersedes an earlier packet of the same case; history stays readable', () => {
  const f = fixture();
  const v1 = f.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf('v1').file('summary.pdf')] });
  const v2 = f.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf('v2').file('summary.pdf')], replaces: [v1.submission_id] });
  const active = f.call('cpa-portal.cases.get', { case_id: CASE }).submissions.map(s => s.submission_id);
  assert.deepEqual(active, [v2.submission_id]);
  const all = f.call('cpa-portal.submissions.list', { case_id: CASE, include_inactive: true }).submissions;
  assert.deepEqual(all.map(s => [s.submission_id, s.state]), [[v1.submission_id, 'superseded'], [v2.submission_id, 'active']]);
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf('v3').file('s.pdf')], replaces: [v1.submission_id] }), /already superseded/);
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf('v3').file('s.pdf')], replaces: ['sb-0001'] }), /another case/);
});

test('withdrawal issues a receipt and keeps the files readable', () => {
  const f = fixture();
  const v1 = f.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf('v1').file('summary.pdf')] });
  const w = f.call('cpa-portal.submissions.withdraw', { submission_id: v1.submission_id, reason: 'wrong statement' });
  assert.equal(f.call('cpa-portal.receipts.get', { receipt_id: w.receipt_id }).receipt.kind, 'withdrawn');
  assert.equal(f.call('cpa-portal.submissions.get', { submission_id: v1.submission_id }).submission.state, 'withdrawn');
  assert.ok(f.call('cpa-portal.submissions.read', { submission_id: v1.submission_id, file_id: `${v1.submission_id}-f1` }).file.base64);
  unchanged(f, () => f.call('cpa-portal.submissions.withdraw', { submission_id: v1.submission_id }), /already withdrawn/);
});

test('cutoff policy: reject, archive_only and accept_for_review', () => {
  const late = policy => {
    const s = structuredClone(require('../fixtures/minimal.json'));
    Object.assign(s.cases[0], { cutoff: '2026-03-10T17:00:00-07:00', late_submission_policy: policy });
    const f = fixture({ seed: s, now: '2026-03-11T09:00:00-07:00' });
    return f;
  };
  const r = late('reject');
  unchanged(r, () => r.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf().file('a.pdf')] }), /stopped taking submissions/);
  assert.equal(late('archive_only').call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf().file('a.pdf')] }).standing, 'late_archived');
  assert.equal(late('accept_for_review').call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf().file('a.pdf')] }).standing, 'late_for_review');
});

test('lowered access blocks writes and hides the case', () => {
  const s = structuredClone(require('../fixtures/minimal.json'));
  s.cases[0].access = 'view';
  const f = fixture({ seed: s });
  unchanged(f, () => f.call('cpa-portal.submissions.add', { case_id: CASE, files: [pdf().file('a.pdf')] }), /access to case/);
  s.cases[0].access = 'none';
  const g = fixture({ seed: s });
  assert.throws(() => g.call('cpa-portal.cases.get', { case_id: CASE }), /No access/);
});

test('seed validation rejects bytes that do not match their recorded hash', () => {
  const f = fixture();
  const bad = f.data;
  bad.submissions[0].files[0].sha256 = '0'.repeat(64);
  assert.throws(() => plugin.validateSeed(f.ctx, bad), /SHA-256/);
});

test('the portal accepts no events', () => {
  assert.throws(() => plugin.applyEvent({}, {}, { operation: 'cpa-portal.no_events' }), /accepts no events/);
});
