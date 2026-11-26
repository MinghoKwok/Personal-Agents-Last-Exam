# Counterline Web App

`index.html` and `src/app.js` are Counterline's own pages; the shared public Web Host (`runtime/web/server.cjs`) serves them and forwards only the Agent MCP tools the run's policy allows. `src/view.js` is the compatible reviewer renderer.

From the repository root:

```sh
node runtime/web/server.cjs --app counterline --registry apps/counterline/registry.json --run web-demo --profile sandbox
```

Open the access link the Host prints. `apps/counterline/registry.json` lists only this package, so the Host serves it without a change to the repository's `apps.registry.json`. Seed, reset and scenario events stay on the separate Infra MCP connection; the page has no route to them.

## Pages

- **Cases:** the case list and a new-case form; a case shows the chat with its transcript, the quick actions the chat offers now, a message box, offer cards with terms, conditions and expiry, a two-step accept (summary, then confirm) and decline, and an identity form that sends only the fields ticked. Close and reopen.
- **Help center:** search and read articles. Departments such as Account Review are named only here.
- **Commitments:** what the provider promised, its reports with references, the overdue flag and any contest, with a note that neither a promise nor a report shows the money arrived. Contest a commitment.
- **Settings:** email copies of offers and confirmations.

## How it talks to the App

Every value shown comes from a Counterline read on each refresh; there is no browser-side business store. A write carries the version observed when the view loaded, so a stale view reports the conflict instead of overwriting; an unchanged retry reuses its `request_id`, so a lost response does not repeat a committed effect. App text is inserted as text, never as HTML. Styles beyond the shared stylesheet come from a constructed stylesheet.

## Browser check

```sh
node apps/counterline/tests/browser.test.cjs
```

29 checks with real clicks and form entry, each write checked in the App state through a separate Infra MCP connection: opening a case; identity with only the ticked fields; two requests in one message; a message that tries to accept by text; a transfer by alias; two-step acceptance with cancel and confirm; a retry after a lost response; a stale view; a scenario event seen after Refresh; reload persistence; a contest; help search; the email preference; close and reopen; a refused direct management request; text escaping; the narrow layout; and JavaScript errors. Screenshots and `report.json` go to `.artifacts/web/counterline/`. The page reads offers and commitments through `cases.get` and `commitments.list`, so `offers.get` and `commitments.get` are not used by it; the report lists them.
