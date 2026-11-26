## Track and stage

**Track (required): select one.**

- [ ] Environment Track
- [x] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/task/refund-recovery.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/task/refund-recovery/proposals/task/refund-recovery.md)

## Summary and dependencies

**Summary (required):** Riley wants a canceled membership charge recovered. Across five sessions, the agent reconciles a partial merchant refund, acts within Riley’s earlier authorization and checks whether a credit is final. Two paired tests isolate these decisions. S3 varies only the earlier delegation. S4 starts both settlement variants from the same authorized filing and shows the same card balance. On the provisional-credit path, the simulator gives the agent two turns on November 23. It records the morning answer while the case is open, then advances the clock and releases the afternoon reversal and closure notice. A separate stop-tracking diagnostic ends when the user withdraws permission to follow up.

**Dependencies / questions (optional):** Related proposals include [merchant returns #7](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/7), [subscription cancellation #20](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/20) and [billing grievances #17](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/17). This task needs a narrow issuer ledger and case fixture, which could be shared with the card fixture of #100 by the same author (a liquidity-planning task, not claim recovery). The runtime or scenario driver must deliver two ordered observations within one session. Planned effort is 7–12 person-days.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** The design specifies a 100-point verifier, three hard gates and branch-specific reference outcomes. The calendar and ledger examples have been checked. Implementation and model rollout evidence follow design approval.
