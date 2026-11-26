## Track and stage

**Track (required): select one.**

- [ ] Environment Track
- [x] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/task/household-payment-audit.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/task/household-payment-audit/proposals/task/household-payment-audit.md)

## Summary and dependencies

**Summary (required):** Sam asks the agent to audit a year of household statements against bills, expense reports and payslips, and to get anything still owed corrected. The year-end gap of $210 has two causes. One of two $186 train tickets was never reimbursed, and a duplicate $8 device fee recurred on three internet invoices. The duplicate is below Sam's $50 threshold for isolated errors, but Sam's instructions say to pursue recurring ones. A paired test changes only which trip the payroll remittance says it paid, so the correct payroll correction switches between the two reports while every balance stays identical. A one-time $12 late fee is a real but isolated error, which Sam wants reported but not pursued, even when a message is already going to the same provider. Two genuine look-alikes, a card payment transfer and two same-day parking charges, test false-positive control. Over four sessions, the agent sends supported corrections and then reconciles a provider account credit separately from a cash payroll adjustment. It finishes with an audit trail the user can check. A 100-point rubric reports precision and recall at the obligation level and includes three hard gates.

**Dependencies / questions (optional):** A small task-owned fixture covers the document store, the employer and provider inboxes, read-only statements and a case register. Claimline (#42) could optionally supply expense records. Related but distinct: #43 captures conference receipts during a trip, whereas this audit starts after the year closes. Feedback is welcome on whether the remittance can be found through natural search without exposing hidden matching keys. Planned effort is 8–13 person-days.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. The ledger arithmetic and session dates have been checked. Nothing has been implemented or run on models, and no difficulty claim is made.
