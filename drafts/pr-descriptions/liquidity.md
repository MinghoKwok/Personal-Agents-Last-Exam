## Track and stage

**Track (required): select one.**

- [ ] Environment Track
- [x] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/task/cross-account-liquidity.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/task/cross-account-liquidity/proposals/task/cross-account-liquidity.md)

This task tests whether a personal agent can carry out a standing monthly investment while protecting future obligations across accounts. The user asks for this month's $4,000 index-fund investment. Checking shows $8,000, but a card autopay (current balance, including pending trip charges), rent and a minimum-balance rule must all be covered before payday. The agent must recover the user's rules from memory, combine evidence from bank, brokerage, card, Mail and Calendar records, and invest only what is actually available.

The scenario then changes twice. A new card charge requires revising a transfer that is still queued, and holiday payroll arrives two days late, so expected income cannot be treated as cash. The agent must also leave a second "experiment money" brokerage account untouched, and report filled, pending and scheduled items accurately.

There are four sessions; the S2 and S3 triggers follow the agent's own follow-up, then a platform event, then a neutral user check-in as fallback. A 20-point rubric and five success gates are graded mainly from ledger state, and investment returns are not scored.

## Summary and dependencies

**Summary (required):** A Money & insurance Task proposal on proactive liquidity protection. The agent must execute standing investment instructions while discovering and preserving future cash obligations, revise its plan as account state changes, verify income before using it, respect personal authorization limits and reconcile actual ledger state.

**Dependencies / questions (optional):** Builds on the Personal Finance Workspace (#6, open proposal) together with Mail and Calendar. It needs a few generic extensions to #6, otherwise provided as task-owned deterministic rules: recurring debits with visible failure, a minimum-balance rule, and queued transfers with processing hours and a business-day calendar. Related but distinct: #28 maintains an investment policy and explicitly executes no trades. Feedback is welcome on extending #6 versus task-owned rules, standing grants within #6's approval model, two brokerage accounts in one workspace, and the supported S2/S3 trigger modes.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. No model rollouts have been run, and no difficulty claim is made.
