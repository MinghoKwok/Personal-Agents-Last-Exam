'use strict';
// Read-only document page. Availability is computed from the virtual clock on every read.
const { fail, copy, byId, ms } = require('./util.cjs');
const APP = 'issuer-docs';
const available = (d, now) => ms(d.available_from) <= ms(now);
const meta = ({ base64, ...m }) => copy(m);

function handleTool(ctx, data, name, args) {
  const now = ctx.virtual_now;
  if (name === `${APP}.accounts.list`) {
    return { data, result: { institution: copy(data.institution), accounts: copy(data.accounts), now } };
  }
  if (name === `${APP}.documents.list`) {
    byId(data.accounts, 'account_ref', args.account_ref, 'Account');
    const docs = data.documents
      .filter(d => d.account_ref === args.account_ref && available(d, now))
      .filter(d => !args.kind || d.kind === args.kind)
      .filter(d => args.tax_year === undefined || d.tax_year === args.tax_year)
      .sort((a, b) => ms(b.issued_at) - ms(a.issued_at));
    return { data, result: { documents: docs.map(meta), now } };
  }
  if (name === `${APP}.documents.download`) {
    const d = data.documents.find(x => x.document_id === args.document_id);
    // A document that is not yet available reads exactly like an unknown one.
    if (!d || !available(d, now)) fail('not_found', `Document ${args.document_id} does not exist.`);
    const { document_id, filename, mime_type, size, sha256, base64 } = d;
    return { data, result: { file: { document_id, filename, mime_type, size, sha256, base64 } } };
  }
  fail('unknown_tool', `Unknown issuer document operation: ${name}.`);
}
module.exports = { handleTool };
