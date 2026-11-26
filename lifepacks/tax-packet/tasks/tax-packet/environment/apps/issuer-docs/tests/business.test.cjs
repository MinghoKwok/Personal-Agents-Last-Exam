'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const plugin = require('../plugin.cjs');
const { fixture } = require('./harness.cjs');
const ACCT = 'bayview-savings-4410';

test('before March 10 the 1099-INT is neither listed nor downloadable', () => {
  const f = fixture({ now: '2026-03-06T18:00:00-08:00' });
  const before = f.data;
  const docs = f.call('issuer-docs.documents.list', { account_ref: ACCT }).documents;
  assert.deepEqual(docs.map(d => d.document_id), ['bv-closure-2025', 'bv-stmt-2025-07']);
  assert.throws(() => f.call('issuer-docs.documents.download', { document_id: 'bv-1099int-2025' }), /does not exist/);
  assert.deepEqual(f.data, before);
});

test('from its available_from time the 1099-INT is listed first and downloads byte-exact', () => {
  const f = fixture({ now: '2026-03-10T10:00:00-07:00' });
  const docs = f.call('issuer-docs.documents.list', { account_ref: ACCT, kind: 'tax_form', tax_year: 2025 }).documents;
  assert.deepEqual(docs.map(d => d.document_id), ['bv-1099int-2025']);
  const file = f.call('issuer-docs.documents.download', { document_id: 'bv-1099int-2025' }).file;
  const bytes = Buffer.from(file.base64, 'base64');
  assert.equal(bytes.length, file.size);
  assert.equal(file.sha256, crypto.createHash('sha256').update(bytes).digest('hex'));
  assert.equal(bytes.subarray(0, 5).toString('latin1'), '%PDF-');
  assert.match(bytes.toString('latin1'), /Form 1099-INT 2025/);
});

test('the closed account is listed with its closing date', () => {
  const f = fixture();
  const { accounts, institution } = f.call('issuer-docs.accounts.list');
  assert.equal(institution.name, 'Bayview Bank');
  assert.deepEqual(accounts.map(a => [a.account_ref, a.status, a.closed_on]), [[ACCT, 'closed', '2025-08-29']]);
});

test('unknown accounts and documents fail without changes', () => {
  const f = fixture();
  assert.throws(() => f.call('issuer-docs.documents.list', { account_ref: 'nope' }), /does not exist/);
  assert.throws(() => f.call('issuer-docs.documents.download', { document_id: 'nope' }), /does not exist/);
});

test('seed validation rejects tampered bytes and early availability', () => {
  const f = fixture();
  const bad = f.data;
  bad.documents[2].sha256 = '0'.repeat(64);
  assert.throws(() => plugin.validateSeed(f.ctx, bad), /SHA-256/);
  const early = f.data;
  early.documents[2].available_from = '2026-03-01T00:00:00-08:00';
  assert.throws(() => plugin.validateSeed(f.ctx, early), /available before it is issued/);
});

test('the page accepts no events', () => {
  assert.throws(() => plugin.applyEvent(), /accepts no events/);
});
