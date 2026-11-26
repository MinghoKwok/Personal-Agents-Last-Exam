'use strict';
// One real business change: a packet is submitted, read back and receipted.
const { fixture } = require('../tests/harness.cjs');
const f = fixture();
const bytes = Buffer.from('%PDF-1.4\n% SYNTHETIC BENCHMARK NOT FOR FILING\n%%EOF\n', 'latin1');
const out = f.call('cpa-portal.submissions.add', { case_id: 'CP-2025-ROWAN', files: [{ filename: 'manifest.pdf', mime_type: 'application/pdf', base64: bytes.toString('base64') }] });
console.log(JSON.stringify({ app: 'cpa-portal', submission: out, receipts: f.call('cpa-portal.receipts.list', { case_id: 'CP-2025-ROWAN' }).receipts }, null, 2));
