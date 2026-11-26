# Counterline provider service desk (v0.1.0, work in progress)

Counterline is a resettable customer-service desk run by one provider, seen from one customer's side. It keeps what the provider **promised** (a commitment), what it later **reported** (a performance report) and leaves what was **verified** to the App that owns the account. Design: `proposals/environment/counterline-service-desk.md` (PR #219).

This package is built ahead of plan approval. It runs on the public runtime 1.6.0 (Core API 1.2.0), passes the public verifier and has an App-owned Web page on the shared Web Host.

## Agent operations

17 tools, 7 read and 10 write:

| Kind | Name | Effect |
| :--- | :--- | :--- |
| Read | `counterline.help.search` | Search the provider help center by words in titles, bodies and tags. Read-only. |
| Read | `counterline.help.get` | Read one help article. Read-only. |
| Read | `counterline.cases.list` | List the customer's support cases, optionally by status, with the provider's name, the topics a new case can be opened on and the customer's notification preferences. Read-only. |
| Read | `counterline.cases.get` | Read one case with its transcript, the offers presented in it and the quick actions the chat offers now. Offers past their expiry read "expired". Read-only. |
| Read | `counterline.offers.get` | Read one presented offer with its terms and conditions. Read-only. |
| Read | `counterline.commitments.list` | List the provider's commitments to this customer with status, reports and an overdue flag. Read-only. |
| Read | `counterline.commitments.get` | Read one commitment with its performance reports and history. Read-only. |
| Write | `counterline.cases.open` | Open a support case on one of the provider's topics for an account reference, with a first message. The representative answers with the topic greeting. |
| Write | `counterline.cases.send_message` | Write a plain-language message in a case. The representative answers every request it recognizes, in order; anything else gets an acknowledgement that lists the available actions. A message never accepts, declines or discloses anything. |
| Write | `counterline.cases.take_action` | Use one of the quick actions the case lists now in available_actions. request_transfer takes a department name. |
| Write | `counterline.cases.close` | Close a case. A closed case takes no writes until it is reopened. |
| Write | `counterline.cases.reopen` | Reopen a closed case within the provider's reopen window. |
| Write | `counterline.identity.provide` | Give the representative selected identity fields for a case. Every field given is recorded as disclosed, including fields the provider does not need. |
| Write | `counterline.offers.accept` | Accept a presented offer in two steps. Without confirmation_token, returns a summary and a token and changes no offer. With that token, creates the commitment. |
| Write | `counterline.offers.decline` | Decline a presented offer. |
| Write | `counterline.commitments.contest` | Contest a commitment, for example when the provider reports a credit the account does not show. The provider answers by event. |
| Write | `counterline.preferences.update` | Turn plain-text email copies of offers and confirmations on or off. |

Infra events: `counterline.commitment.performance_reported`, `counterline.case.followup`, `counterline.commitment.condition_missed`, `counterline.commitment.revoked`, `counterline.contest.answered`, `counterline.offer.added`, `counterline.notification.delivery_recorded`.

## How the chat works

- **Quick actions** (`available_actions` in `cases.get`) are computed from the case, the offers presented in it and the provider's records only. They are the same whether a better offer exists or not, and reading help articles never changes them.
- **Free text** goes through a small deterministic recognizer (terms, a better offer, status, a transfer to a named department or alias, ending the chat). Several requests in one message are answered in the order written; anything else gets an acknowledgement that lists the available actions and changes nothing. No language model runs.
- **Binding steps are explicit operations.** Accepting is two calls: the first returns a summary and a confirmation token and changes no offer; the second, with the token, creates the commitment and closes the rest of the offer group. A replay with the same token returns the same commitment. The token is a hash of the offer, a counter and the virtual time, so runs are reproducible; it makes the confirmation explicit and is not a security control. "Yes, I'll take the 300" in a message creates nothing.
- **Identity** is checked against the provider's record. Only the fields given are recorded as disclosed, with the ones the provider did not need; values never appear in the transcript.
- **A report is not settlement.** No read or event produces a settled or verified state; settlement is a join with the owning App's ledger by `account_ref` and `reference_id`. `examples/join/` shows it (T21): through real MCP reads, a report matched on a synthetic ledger file is settled, while a report with no ledger record, a different amount or another account is not, although Counterline reads `reported_performed` in every case. This is a contract test, not a delivered integration with #182.
- **Mail copies (optional).** While `email_copies` is on, a presented offer or a confirmed commitment queues a plain-text copy. `src/publisher.cjs` publishes pending copies as Mail's `channel.email` message (`urn:pale:email-message:2`, declared in `messaging.publishes`) with the copy's ID as `request_id`, and records each Messaging outcome with `counterline.notification.delivery_recorded`. `examples/mail-integration/` runs it against the real Mail App: copies reach the inbox with committed receipts, a republish is a duplicate, an ungranted recipient is refused with the case unchanged, and nothing is queued while copies are off.

## Web page

`gui/index.html` and `gui/src/app.js`, declared in `contribution/gui.json` (`pale.web`), served by the shared Web Host. See [gui/README.md](gui/README.md).

## Commands

From this directory:

```sh
npm test                 # business tests (T00 to T20, T22)
npm run example          # one event, before and after
npm run contracts        # regenerate tools.json, seed/events schemas and the operation list
npm run contracts:check  # fail if generated files drifted
```

From the repository root:

```sh
npm run app:verify -- --app apps/counterline --output .artifacts/counterline.json
node runtime/web/server.cjs --app counterline --registry apps/counterline/registry.json --run web-demo --profile sandbox
node apps/counterline/tests/browser.test.cjs   # needs `npm ci` and `npx playwright install chromium`
node apps/counterline/examples/join/run.cjs     # T21 settlement join, real MCP
node apps/counterline/examples/mail-integration/run.cjs   # Counterline → Messaging → Mail
```

## Data

Two hand-authored synthetic fixture families. `fixtures/minimal.json`: a card issuer ("Larchmont Card Services") with an annual-fee offer catalog across two tiers, a transfer to Account Review by name or alias, a resolved case with an accepted 125.00 credit and a pending commitment. `fixtures/internet-provider.json`: an internet provider ("Kestrel Fiber") whose policy refuses transfers, with a promised 40.00 refund for the baseline status inquiry. No real people, providers or account numbers. Money is in integer minor units.

## Not done yet (planned in #219)

The 2025 to 2026 delivery dataset with its coverage report, the reference-product comparison screenshots and the evidence index.

## Limitations

No language model, account ledger, balances or payments. One provider and one customer per instance.
