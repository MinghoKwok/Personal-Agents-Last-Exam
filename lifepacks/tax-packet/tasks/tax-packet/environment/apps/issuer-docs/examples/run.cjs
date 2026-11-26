'use strict';
// Shows the 1099-INT appearing on the page once the clock reaches March 10.
const { fixture } = require('../tests/harness.cjs');
const list = now => fixture({ now }).call('issuer-docs.documents.list', { account_ref: 'bayview-savings-4410' }).documents.map(d => d.document_id);
console.log(JSON.stringify({ app: 'issuer-docs', march_6: list('2026-03-06T18:00:00-08:00'), march_10: list('2026-03-10T10:00:00-07:00') }, null, 2));
