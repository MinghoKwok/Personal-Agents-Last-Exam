Hi @genglinliu, thanks for this proposal. I'm drafting a Task proposal that would build on the Personal Finance Workspace, and I wanted to check whether a few small additions could fit your scope before I commit to task-owned fixtures.

**The task (short version):** a user asks the agent to make this month's $4,000 index-fund investment. Checking shows $8,000, but a card autopay and a rent debit are due before payday, and checking has a $1,500 minimum-balance rule. Mid-scenario, a new card charge posts and payroll is delayed by a holiday. The agent has to work out what is actually available, revise a transfer that is still pending, and report which items are filled, pending or scheduled. Grading is based on ledger state, not returns.

**What I'd reuse as proposed:** cash and brokerage accounts on one ledger, transfer and buy previews with receipts, the shared simulated clock, scheduled postings over time, the separation of posted cash from expected income, and Mail/Calendar for obligations.

**Possible additions.** Each one is small, deterministic and configured by the task, so other tasks can ignore it:

1. **Recurring debits from a cash account** (rent, card autopay), with an observable insufficient-funds outcome (returned or failed payment) instead of a silent negative balance.
2. **Account-terms rules on cash accounts**, e.g. a fee if any end-of-day balance in a cycle falls below a threshold. This would be checked from a daily end-of-day balance log.
3. **A post-execution transfer lifecycle**: initiated → pending → available, with a processing cutoff and a business-day calendar (holidays), where a transfer can be edited or cancelled until it processes. As I read it, the current cancel/replace applies to proposals before approval, and settlement is out of scope, so this may be the largest change.
4. **Standing grants with a cap** (e.g. "move money between these two accounts and buy fund X, up to $4,000 per calendar month") alongside per-action approval.
5. **Optional:** a buy order that executes when a pending deposit becomes available.

**Probably outside your scope**, so I'm not asking for it: a credit-card account with statement vs current balance, pending authorizations that finalize later, and an autopay setting. I plan to keep that as a task-owned fixture, or propose it separately, unless you think it belongs here.

Two questions:
- Would any of items 1–4 fit your v1, or should my task carry its own deterministic rules on top of your ledger?
- Can one user hold more than one brokerage account in the workspace (e.g. a second "experiment money" account the agent must not touch)?

I'll link my Task PR here once it's open. Happy to help with fixture or test cases for any of these if that's useful.
