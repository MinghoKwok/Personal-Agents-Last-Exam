'use strict';
// Read-time derivations. Time-based states are computed from the virtual clock, never stored.
const { copy, ms } = require('./util.cjs');
function offerView(offer, now) {
  const view = copy(offer);
  if (view.state === 'presented' && view.expires_at && ms(now) > ms(view.expires_at)) view.state = 'expired';
  return view;
}
function commitmentView(commitment, now) {
  const view = copy(commitment);
  view.overdue = view.status === 'pending' && view.perform_by !== null && ms(now) > ms(view.perform_by);
  return view;
}
function caseSummary(c) {
  const { case_id, topic_id, account_ref, status, tier, opened_at, closed_at } = c;
  return { case_id, topic_id, account_ref, status, tier, opened_at, closed_at };
}
module.exports = { offerView, commitmentView, caseSummary };
