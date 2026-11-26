'use strict';
// Agent tool handlers. Reads never change data; writes return { data, result }.
const crypto = require('node:crypto');
const { fail, copy, byId, nextId, ms } = require('./util.cjs');
const { log } = require('./diagnostics.cjs');
const APP = 'cpa-portal';

const stateOf = s => (s.withdrawn_at ? 'withdrawn' : s.superseded_by ? 'superseded' : 'active');
function submissionView(s) {
  const { files, ...rest } = copy(s);
  return { ...rest, state: stateOf(s), files: files.map(({ base64, ...meta }) => meta) };
}
const activeOf = (data, caseId) => data.submissions.filter(s => s.case_id === caseId && stateOf(s) === 'active');
const caseBytes = (data, caseId) => data.submissions.filter(s => s.case_id === caseId).reduce((n, s) => n + s.files.reduce((m, f) => m + f.size, 0), 0);
const afterCutoff = (c, now) => c.cutoff !== null && ms(now) > ms(c.cutoff);
function caseView(data, c, now) {
  return { ...copy(c), after_cutoff: afterCutoff(c, now), active_submissions: activeOf(data, c.case_id).length, stored_bytes: caseBytes(data, c.case_id) };
}

function decode(file) {
  if (!/^[A-Za-z0-9+/]*={0,2}$/.test(file.base64) || file.base64.length % 4 !== 0) fail('invalid_file', `${file.filename} is not valid base64.`);
  const bytes = Buffer.from(file.base64, 'base64');
  if (bytes.toString('base64') !== file.base64) fail('invalid_file', `${file.filename} is not canonical base64.`);
  return bytes;
}
function contentMatches(bytes, mime) {
  if (mime === 'application/pdf') return bytes.subarray(0, 5).toString('latin1') === '%PDF-';
  const textValue = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
  if (Buffer.from(textValue, 'utf8').compare(bytes) !== 0) return false;
  if (mime === 'application/json') { try { JSON.parse(textValue); } catch { return false; } }
  return true;
}

function read(ctx, data, name, args) {
  const now = ctx.virtual_now;
  switch (name) {
    case `${APP}.cases.list`:
      return { cases: data.cases.map(c => caseView(data, c, now)), now };
    case `${APP}.cases.get`: {
      const c = byId(data.cases, 'case_id', args.case_id, 'Case');
      if (c.access === 'none') fail('access_denied', `No access to case ${c.case_id}.`);
      return { case: caseView(data, c, now), submissions: activeOf(data, c.case_id).map(submissionView), now };
    }
    case `${APP}.submissions.list`: {
      const c = byId(data.cases, 'case_id', args.case_id, 'Case');
      if (c.access === 'none') fail('access_denied', `No access to case ${c.case_id}.`);
      const list = data.submissions.filter(s => s.case_id === c.case_id && (args.include_inactive || stateOf(s) === 'active'));
      return { submissions: list.map(submissionView) };
    }
    case `${APP}.submissions.get`:
      return { submission: submissionView(byId(data.submissions, 'submission_id', args.submission_id, 'Submission')) };
    case `${APP}.submissions.read`: {
      const s = byId(data.submissions, 'submission_id', args.submission_id, 'Submission');
      return { file: copy(byId(s.files, 'file_id', args.file_id, 'File')) };
    }
    case `${APP}.receipts.list`:
      byId(data.cases, 'case_id', args.case_id, 'Case');
      return { receipts: copy(data.receipts.filter(r => r.case_id === args.case_id)) };
    case `${APP}.receipts.get`:
      return { receipt: copy(byId(data.receipts, 'receipt_id', args.receipt_id, 'Receipt')) };
    default:
      return null;
  }
}

function writable(c) {
  if (c.status !== 'open') fail('invalid_state', `Case ${c.case_id} is ${c.status} and takes no changes.`);
  if (c.access !== 'upload') fail('access_denied', `Your access to case ${c.case_id} is ${c.access}.`);
}

function add(ctx, data, args) {
  const now = ctx.virtual_now;
  const c = byId(data.cases, 'case_id', args.case_id, 'Case');
  writable(c);
  let standing = 'on_time';
  if (afterCutoff(c, now)) {
    if (c.late_submission_policy === 'reject') fail('after_cutoff', `Case ${c.case_id} stopped taking submissions at ${c.cutoff}.`);
    standing = c.late_submission_policy === 'archive_only' ? 'late_archived' : 'late_for_review';
  }
  const replaces = [...new Set(args.replaces || [])];
  for (const rid of replaces) {
    const old = byId(data.submissions, 'submission_id', rid, 'Submission');
    if (old.case_id !== c.case_id) fail('invalid_state', `Submission ${rid} belongs to another case.`);
    if (stateOf(old) !== 'active') fail('invalid_state', `Submission ${rid} is already ${stateOf(old)}.`);
  }
  const submission_id = nextId('sb', new Set(data.submissions.map(s => s.submission_id)));
  const firm = data.firm;
  let added = 0;
  const names = new Set();
  const files = args.files.map((f, i) => {
    if (!firm.accepted_types.includes(f.mime_type)) fail('unsupported_type', `${f.mime_type} is not accepted by ${firm.name}.`);
    if (names.has(f.filename)) fail('invalid_file', `Duplicate file name ${f.filename} in one submission.`);
    names.add(f.filename);
    const bytes = decode(f);
    if (bytes.length > firm.max_file_bytes) fail('too_large', `${f.filename} is larger than ${firm.max_file_bytes} bytes.`);
    if (!contentMatches(bytes, f.mime_type)) fail('invalid_file', `${f.filename} does not match its type ${f.mime_type}.`);
    const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
    if (f.sha256 && f.sha256 !== sha256) fail('hash_mismatch', `${f.filename}: the supplied SHA-256 does not match the bytes received.`);
    added += bytes.length;
    return { file_id: `${submission_id}-f${i + 1}`, filename: f.filename, mime_type: f.mime_type, size: bytes.length, sha256, base64: f.base64 };
  });
  if (caseBytes(data, c.case_id) + added > firm.max_case_bytes) fail('too_large', `Case ${c.case_id} would exceed ${firm.max_case_bytes} stored bytes.`);
  for (const rid of replaces) byId(data.submissions, 'submission_id', rid, 'Submission').superseded_by = submission_id;
  data.submissions.push({
    submission_id, case_id: c.case_id, request_ids: [], submitted_at: now, actor: 'assistant', standing,
    replaces, superseded_by: null, withdrawn_at: null, note: args.note ?? null, files
  });
  const receipt_id = nextId('rc', new Set(data.receipts.map(r => r.receipt_id)));
  const meta = files.map(({ base64, ...m }) => m);
  data.receipts.push({ receipt_id, submission_id, case_id: c.case_id, at: now, kind: 'submitted', standing, files: copy(meta) });
  log(ctx, 'cpa-portal.submitted', { submission_id, files: files.length });
  return { data, result: { submission_id, receipt_id, standing, files: meta } };
}

function withdraw(ctx, data, args) {
  const s = byId(data.submissions, 'submission_id', args.submission_id, 'Submission');
  const c = byId(data.cases, 'case_id', s.case_id, 'Case');
  writable(c);
  if (stateOf(s) !== 'active') fail('invalid_state', `Submission ${s.submission_id} is already ${stateOf(s)}.`);
  s.withdrawn_at = ctx.virtual_now;
  const receipt_id = nextId('rc', new Set(data.receipts.map(r => r.receipt_id)));
  data.receipts.push({ receipt_id, submission_id: s.submission_id, case_id: c.case_id, at: ctx.virtual_now, kind: 'withdrawn', standing: s.standing, files: s.files.map(({ base64, ...m }) => copy(m)) });
  log(ctx, 'cpa-portal.withdrawn', { submission_id: s.submission_id });
  return { data, result: { submission_id: s.submission_id, receipt_id } };
}

function handleTool(ctx, data, name, args) {
  const view = read(ctx, data, name, args);
  if (view) return { data, result: view };
  if (name === `${APP}.submissions.add`) return add(ctx, data, args);
  if (name === `${APP}.submissions.withdraw`) return withdraw(ctx, data, args);
  fail('unknown_tool', `Unknown CPA portal operation: ${name}.`);
}
module.exports = { handleTool, stateOf };
