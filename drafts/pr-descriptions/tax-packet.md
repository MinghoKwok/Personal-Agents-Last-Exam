## Track and stage

**Track (required): select one.**

- [ ] Environment Track
- [x] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/task/tax-packet.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/task/tax-packet/proposals/task/tax-packet.md)

This task tests whether a personal agent keeps a set of persistent artifacts consistent as evidence changes over five sessions and five weeks. The user, who changed jobs and closed a bank account during the year, asks the agent to maintain a tax-document packet for their accountant and to upload it only once it is complete and authorized.

As the weeks pass, the evidence changes:

- A brokerage issues a CORRECTED statement that replaces the original in full.
- A re-exported copy and a supplemental view must not be double counted.
- The original statement is forwarded again after the correction.
- The user adds a closed account whose form becomes available only on delivery day.

The agent must carry each change into every saved artifact (manifest, field-level summary, handoff note) and into the files the CPA portal actually receives. Restating the right numbers in chat is not enough. The agent must also report accurately whether the packet is ready, has been delivered or has been filed (never).

The proposal includes fictional fixtures, a 20-point rubric, four success gates, controls that separate propagation failures from extraction and tool failures, and a construction plan. Tax liability and filing decisions are out of scope.

## Summary and dependencies

**Summary (required):** A Money & insurance task on evidence versioning and persistent artifact consistency across sessions, ending in authorized, receipt-verified delivery to a CPA portal.

**Dependencies / questions (optional):** The first choice for document storage is Personal Document Records (#33); otherwise the task uses a narrow task-owned file area, since the runtime has no shared Files App. Mail comes from the public runtime. The issuer document page and the CPA portal are minimal and task-owned, and the Personal Finance Workspace (#6) is an optional later integration, not a dependency. Related but distinct is #53, which tests whether instructions inside documents expand sharing authority. #100 is a complementary task by the same author. Feedback is welcome on #33's reuse boundary, session-history visibility and difficulty calibration.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. No model rollouts have been run, and no difficulty claim is made.
