'use strict';
// The settlement join: a provider's report is matched against the owning App's ledger by business IDs.
// Counterline never decides settlement; this function is what a task or an evaluator runs.
//   settled      every reported reference has a ledger record on the same account with the same amount
//                and currency, and the reports add up to the committed amount
//   not_settled  a report has no matching ledger record, or the account or amount differs
//   no_report    the provider has reported nothing (whatever its representative said in chat)
function settle(commitment, ledger) {
  if (!commitment.reports.length) return {commitment_id: commitment.commitment_id, result: 'no_report', reasons: ['no performance report']};
  const reasons = [];
  let matched = 0;
  for (const r of commitment.reports) {
    const rec = ledger.find(x => x.reference_id === r.reference_id);
    if (!rec) { reasons.push(`${r.reference_id}: no ledger record`); continue; }
    if (rec.account_ref !== commitment.account_ref) { reasons.push(`${r.reference_id}: posted to ${rec.account_ref}, not ${commitment.account_ref}`); continue; }
    if (rec.amount_minor !== r.amount_minor || rec.currency !== r.currency) { reasons.push(`${r.reference_id}: ledger shows ${rec.amount_minor} ${rec.currency}, report says ${r.amount_minor} ${r.currency}`); continue; }
    matched += rec.amount_minor;
  }
  if (!reasons.length && commitment.value && matched < commitment.value.amount_minor) reasons.push(`ledger shows ${matched} of ${commitment.value.amount_minor}`);
  return {commitment_id: commitment.commitment_id, result: reasons.length ? 'not_settled' : 'settled', reasons};
}
module.exports = {settle};
