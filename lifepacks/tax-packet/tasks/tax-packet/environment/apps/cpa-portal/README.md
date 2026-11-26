# CPA portal for Task #102 (task-owned, v0.1.0)

A minimal client portal of a fictional accounting firm, owned by Task #102 (`tax-packet`). The agent uploads Rowan's tax packet to case `CP-2025-ROWAN`, reads back the stored bytes and checks the receipt.

It is a **subset of the Casefold design** proposed in #222: the same case, submission and receipt records and the same operation names (`cases.*`, `submissions.add/withdraw/list/get/read`, `receipts.*`), without request items or reviewer events, which this task does not use. If Casefold is merged, the task can move to it with the same records.

## Behavior

- `submissions.add` stores the received bytes, computes each SHA-256 (a supplied hash is only checked) and returns a receipt. `replaces` supersedes earlier active submissions of the same case; superseded and withdrawn submissions stay readable in history.
- A case is `open`, `locked` or `closed`; the client's access is `upload`, `view` or `none`. After a cutoff, the case's `late_submission_policy` rejects, archives or accepts a submission for review.
- Type, content signature, per-file and per-case size limits are enforced. A failed call stores nothing.
- Received bytes are kept in the App's business data rather than Core assets, so the package needs no platform resource registration. Limits keep the state small.
- No incoming events.

## Commands

```sh
npm test
npm run example
npm run contracts:check
```

From the repository root:

```sh
npm run app:verify -- --app lifepacks/tax-packet/tasks/tax-packet/environment/apps/cpa-portal
```

All data is synthetic. MIT License.
