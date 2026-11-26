## Track and stage

**Track (required): select one.**

- [x] Environment Track
- [ ] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/environment/counterline-service-desk.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/env/counterline-service-desk/proposals/environment/counterline-service-desk.md)

## Summary and dependencies

**Summary (required):** Counterline is a resettable customer-service desk for one provider, seen from the customer's side. An agent opens support cases, writes to a representative in plain language and uses the quick actions the chat shows, verifies identity, hears offers, asks for escalation, and accepts or declines through a confirmed two-step operation. What the provider agrees to becomes a first-class commitment that is later reported performed, partly performed, missed, revoked or contested. The desk keeps what was promised, what the provider reported and what a trusted account record shows apart, and never stores balances. Quick actions depend only on the case state and the provider's chat policy, so they never reveal an unpresented offer or a department named only in the help center. Free text is recognized where reliable, several requests in one message are answered in order, and anything else gets the list of available actions rather than an error. Binding effects come only from explicit confirmed operations, and no language model runs, so every reply is reproducible. The first version delivers a card-issuer and an internet-provider fixture family, including a plain refund-status inquiry as the baseline, with 17 Agent MCP operations and an App-owned Web page served through the shared Web Host.

**Dependencies / questions (optional):** Only the public runtime 1.6.0 (Core API 1.2.0); Mail 1.3.0 is optional and send-only. Brindle Card (#182) leaves the issuer's service desk out of scope and names #133; Counterline is that desk, joined to account records by `commitment_id` and `reference_id` rather than by shared state. Tasks that currently plan their own desk: #133, #129 and #107. Claims stay with #181. Feedback welcome on the quick-action interface and on keeping transfers discoverable only through the help center. Planned effort is 9.5–12 person-days.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. Nothing has been implemented.
