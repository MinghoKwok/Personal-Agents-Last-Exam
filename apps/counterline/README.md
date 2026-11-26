# Counterline provider service desk (skeleton, v0.1.0)

Counterline is a resettable customer-service desk run by one provider, seen from one customer's side. It keeps what the provider **promised** (a commitment), what it later **reported** (a performance report) and leaves what was **verified** to the App that owns the account. Design: `proposals/environment/counterline-service-desk.md` (PR #219).

This package is a skeleton built ahead of plan approval. It runs on the public runtime 1.6.0 (Core API 1.2.0) and passes the public verifier, but it implements only part of the approved plan.

## Implemented

| Kind | Name | Effect |
| :--- | :--- | :--- |
| Read | `counterline.help.search`, `counterline.help.get` | Help center search and articles. Departments such as Account Review are named only here. |
| Read | `counterline.cases.list`, `counterline.cases.get` | Cases with transcripts and the offers presented in them. |
| Read | `counterline.offers.get` | One offer; a presented offer past `expires_at` reads `expired`, computed on read. |
| Read | `counterline.commitments.list`, `counterline.commitments.get` | Commitments with reports, history and a derived `overdue` flag. |
| Write | `counterline.cases.open` | Opens a case on a provider topic; the representative answers with the topic's greeting script. |
| Event | `counterline.commitment.performance_reported` | Must name an existing open commitment and provider; cannot exceed the committed amount or change currency; a partial amount gives `partially_reported`. |
| Event | `counterline.case.followup` | Appends a scripted representative turn. A script can say "processed" without any report. |

## Not implemented yet (planned in #219)

`cases.send_message`, `cases.take_action` and `available_actions` (quick actions), the text recognizer, `cases.close`, `cases.reopen`, `identity.provide`, `offers.accept` (two-step with a confirmation token), `offers.decline`, `commitments.contest`, `preferences.update`, the remaining events (`condition_missed`, `revoked`, `contest.answered`, `offer.added`), the internet-provider fixture family, and the optional Mail notices.

## Commands

From this directory:

```sh
npm test                 # business tests
npm run example          # one event, before and after
npm run contracts        # regenerate tools.json, seed/events schemas and the operation list
npm run contracts:check  # fail if generated files drifted
```

From the repository root:

```sh
npm run app:verify -- --app apps/counterline --output .artifacts/counterline.json
```

## Data

`fixtures/minimal.json` is a hand-authored synthetic card issuer ("Larchmont Card Services"), three help articles, one resolved annual-fee case with an accepted 125.00 credit and an unavailable conditional offer in the same group, and one pending commitment. No real people, providers or account numbers. Money is in integer minor units.

## Limitations

No language model, account ledger, balances or payments. One provider and one customer per instance. MCP only; no GUI.
