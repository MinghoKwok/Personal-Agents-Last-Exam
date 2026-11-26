'use strict';
// Shows one real business change: a provider performance report on an accepted commitment.
const assert = require('node:assert/strict');
const { fixture } = require('../tests/harness.cjs');
const f = fixture();
const before = f.call('counterline.commitments.get', { commitment_id: 'cm-0001' }).commitment;
f.event(require('./scenario.json'));
const after = f.call('counterline.commitments.get', { commitment_id: 'cm-0001' }).commitment;
assert.notEqual(before.status, after.status);
console.log(JSON.stringify({ app: 'counterline', before: { status: before.status, reports: before.reports }, after: { status: after.status, reports: after.reports } }, null, 2));
