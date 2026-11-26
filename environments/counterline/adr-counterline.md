# ADR-001: Counterline as a separate provider service desk

- **Status:** Proposed (local draft, not submitted)
- **Date:** 2026-11-23
- **Baseline:** upstream `main` a4bce02 (runtime 1.6.0, Core API 1.2.0, Mail 1.3.0); #182 head 68df112

## Context

Four task proposals (#133, #129, #107, #128) each plan a task-owned service desk: a representative who offers, escalates, asks for identity and promises things the provider later does or does not do. No open proposal models this. Brindle Card (#182) is the closest App. It owns a card account and ledger, takes offers only as Infra events, and states in its design file that "the issuer's service desk" is outside the App, naming #133. #182 has an approving design review (skyve2012, 2026-11-22) but no `plan-approved` label.

## Options

| Option | For | Against |
| :--- | :--- | :--- |
| A. Extend Brindle with a desk | One App for card tasks | Another author's PR, which explicitly excludes the desk; ties desk logic to cards, so #129, #107 and #128 cannot reuse it; adds scope to a proposal the reviewer already called ambitious for one owner |
| **B. Separate, provider-agnostic Counterline** | Clean split (ledger vs conversation and commitments); one package serves card, utility, club and insurer desks; no dependency on an unapproved API | Needs a join contract to relate commitments to account records; v1 dialog realism is limited by a deterministic matcher |
| C. Small shared library only | Least code | Not an App: no state, events or Agent operations, so tasks would still rebuild the desk |
| D. A different Environment | | No gap found with broader reuse for these tasks |

## Decision

Choose B. Counterline owns support cases, the dialog policy, offers and the commitment lifecycle. It never owns balances. Account-owning Apps stay the source of truth for what actually posted; Counterline records only what the provider promised and reported.

## Consequences

- Each commitment and performance report joins only on business IDs (`commitment_id`, `reference_id`, `provider_id`, `account_ref`) within a `run_id`. Core's `version` (a per-App reset `epoch` and commit `revision`) is ordering context, not a key. In v1 a task timeline supplies both sides and an evaluator joins them.
- A published `commitment.accepted` message is deferred until an account App declares a receiver, to be agreed with that App's author.
- Interaction is free text plus Agent-visible quick actions (see ADR-002 below). Binding actions go only through confirmed operations. No language model runs in v1.
- #133, #129 and #107 would later switch their desk dependency to Counterline. #128 is not a user: its insurer side is #181 (Alderbrook Mutual claims).

## Not verified

- No reply yet from the #182 author on the split.
- Brindle's interfaces may change before approval; nothing here depends on them.

---

# ADR-002: Free text plus Agent-visible quick actions

- **Status:** Proposed (local draft)
- **Date:** 2026-11-24

## Context

Counterline must let an Agent talk to a representative in a way that is realistic and fully reproducible, without letting the interface itself cause failures. #133 measures whether the Agent keeps the person's limits under pressure, not whether it can guess a desk's vocabulary.

## Options

| Option | Realism | Reproducible | Risk |
| :--- | :--- | :--- | :--- |
| Structured intents only | Low | High | Mechanical; feels like a menu, not a desk |
| Free text with a hidden lexicon | Medium | High | Normal sentences such as two requests in one message read as unclear, so the Environment causes failures |
| Free text decided by a language model | High | Low | Outcomes not reproducible |
| **Free text plus visible quick actions** | High | High | Actions could leak hidden paths if designed carelessly |

## Decision

Free text plus quick actions, with four rules:

1. Quick actions are part of the Agent interface, like the buttons of a real chat.
2. `available_actions` depends only on the case state, presented offers and the provider's chat policy. It does not change with what the Agent has read (reads cannot mutate state, and a real chat does not know which pages were opened), and it is identical whether or not a better offer exists.
3. Hidden paths stay discoverable, not listed: `request_transfer` is always present and takes a department name; departments are named only in the help center.
4. Free text is recognized only where reliable and only for what quick actions also do; several requests in one message are answered in order; anything else gets the action list, never an error. Binding effects never come from text.

## Consequences

- The text recognizer is off the critical path: an Agent can always reach every path through actions. Its diagnostic is reported without an accuracy target.
- #133's graded decisions (accept, decline, disclose, approve a product change) are explicit operations under every option, so this choice removes interface failures without removing the difficulty #133 intends.
- Alternative rejected: showing a specialist action only after the Agent reads the help article. That would make the interface depend on reads. Instead the generic transfer action is always present and useful only with the department name.
