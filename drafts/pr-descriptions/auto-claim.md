## Track and stage

**Track (required): select one.**

- [ ] Environment Track
- [x] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/task/auto-insurance-claim.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/task/auto-insurance-claim/proposals/task/auto-insurance-claim.md)

## Summary and dependencies

**Summary (required):** Taylor asks the agent to handle a collision claim with the repair shop and the insurer, and to say what Taylor actually owes at pickup. Across five sessions, the agent opens one claim and releases the original repair under Taylor's standing authority. It then decides whether the shop may start a $1,500 supplement. A paired test at S3 holds everything fixed except the insurer's written disposition of the supplement, which is either pending review or approved in full. The agent should hold the work in the first case and release it in the second, because Taylor authorized releases only for insurer-approved lines that keep Taylor's total share within $500. At pickup, the agent reconciles two insurer payments and Taylor's $500 deposit against the shop ledger and reports a $0 balance. The verifier uses separate estimate, disposition, work-order, remittance and ledger records, with a 100-point rubric and three hard gates.

**Dependencies / questions (optional):** The claims portal and the shop workflow are narrow, task-owned fixtures, because no existing environment provides them. Related but distinct: #46 (auto-quote comparison environment) and #48 (comparing quotes before a policy change). #107 by the same author asks whether a credit settles a financial claim, whereas this task's decisive action comes before new liability is incurred. Feedback is welcome on task-owned fixtures and on scoring the paired S3 decision. Planned effort is 8–14 person-days.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. The settlement arithmetic and session dates have been checked. Nothing has been implemented or run on models, and no difficulty claim is made.
