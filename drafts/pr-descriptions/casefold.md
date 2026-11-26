## Track and stage

**Track (required): select one.**

- [x] Environment Track
- [ ] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/environment/casefold-client-portal.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/env/casefold-client-portal/proposals/environment/casefold-client-portal.md)

## Summary and dependencies

**Summary (required):** Casefold is a resettable, persistent workspace between one professional firm (an accountant, an attorney or a lender) and one client, seen from the client's side. The firm's document requests evolve through immutable revisions; the client, or an agent, answers with immutable submissions whose SHA-256 the portal computes from the stored bytes; the firm's reviewer accepts, waives or asks to replace each item through validated events that name the exact revision and submission they decide. Item status is derived from those records, so it is always possible to tell what was asked, what was sent and which decision applied to which file. Late submissions follow a configurable firm policy (`reject`, `archive_only` or `accept_for_review`), and the client can lower an assistant's access. The first version delivers tax-intake and immigration-evidence fixtures plus a plain baseline, with 13 Agent MCP operations and an App-owned Web page served through the shared Web Host.

**Dependencies / questions (optional):** Only the public runtime 1.6.0 (Core API 1.2.0); Files and Mail 1.3.0 are optional. Boundary with #218 Vouchfile: Vouchfile is applicant-centric dossier assembly and delivery; Casefold is provider-driven, with evolving requirements and item-level review cycles. #33 and Files hold the client's own library; Casefold holds only what the firm received. Tasks that currently plan their own portal: #102 and #106. **Activation order:** I also own #219 (Counterline) and ask maintainers to confirm activating this plan after #219's first version is submitted, so the two 14-day windows do not overlap. Planned effort is 9.5–12 person-days.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. Nothing has been implemented.
