# Replies to TianyuCodings (post after the commits are pushed)

## #100
Thanks for checking the cash flow. All three points are addressed in the latest commit:
- The October 2 session is a record in LifePack `context/user/history.json`; until a loader provides conversation search, the same text is in a pinned note in Notes, "Conversation with Kai (2026-10-02)".
- E1 to E4 now list points per part, and the Full pass paragraph checks the 18/20 mark against the runs: the reference and accepted alternatives earn 20, while the literal transfer, ignored pending charges, missed S2 revision and investing against payroll each trigger F2 and fail. E4 is now scored only if a purchase fills, so doing nothing earns 0.
- I'll post the three ledger needs on #6 with questions (b) and (c).

## #106
Thanks. The facts come from two sessions with Lin, on 2026-01-12 and 2026-01-20, delivered as records in LifePack `context/user/history.json`. Until a loader provides conversation search, the same text is in two pinned notes in Notes, "Conversation with Lin (2026-01-12)" and "Conversation with Lin (2026-01-20)". The two Scholar-authorization histories differ only in the Jan 20 record. The approved PES itself stays in Files.

## #107
Thanks. Both points are addressed in the latest commit:
- The billing-problems conversation (2026-08-24) is a record in LifePack `context/user/history.json`; until a loader provides conversation search, the same text is in a pinned note in Notes, "Conversation with Riley (2026-08-24)". Histories A and B differ only in that record.
- S2 and the 09:00 turn of S5 now open in mode A, B or C as in #100; in mode C Riley asks "Anything from the gym?" (S2) and "Anything new on the gym charge?" (Event A) without mentioning the refund, credit or case. Without in-session time advance, Event B opens its own session at 15:00 with the same neutral question, and the 09:00 answer is still graded against the morning snapshot.

I also noted #219 as a later option for the merchant's support replies; the task-owned merchant fixture stays the plan.

## #128
Thanks. All three are addressed in the latest commit:
- Taylor's standing authority comes from a 2026-02-27 conversation, a record in LifePack `context/user/history.json`; until a loader provides conversation search, it is in a pinned note in Notes, "Conversation with Taylor (2026-02-27)".
- S2, S3 and S4 open in mode A, B or C as in #100; in mode C Taylor asks "Any news on the car?" without mentioning the estimate, supplement or approval.
- I followed your suggestion: the approved fixture is now the main one, and the pending fixture is the paired control, in which holding is right for any user. The reference now releases the approved lines at S3 and confirms a single work order at S4.

## #129
Thanks. All three are addressed in the latest commit:
- Sam's earlier message is an earlier conversation (2025-12-15), not an App record. It is a record in LifePack `context/user/history.json`; until a loader provides conversation search, it is in a pinned note in Notes, "Conversation with Sam (2025-12-15)".
- S2, S3 and S4 open in mode A, B or C as in #100; in mode C Sam asks "How's the audit going?". The remittance is published on Jan 7 whether or not the agent asks, so it does not need row 8 of #135; a neutral request to payroll gets a reply pointing to it. Payroll and provider responses are released at the next session boundary only if a valid request reached them.
- The integration row now gives each component a first choice, fallback and owner: Files and Mail from main; payslips and remittance from #183 or Files; expense reports from #42 or Files; internet invoices and the credit from #170 or Files; statements in Files; and the case register as a file the agent writes in Files.

## #133
Thanks. The 2026-10-14 conversation is delivered as a record in LifePack `context/user/history.json`. Until a loader provides conversation search, the same text is in a pinned note in Notes, "Conversation with Jordan (2026-10-14)". 

I also updated the integration row, which still said no environment provides an issuer service desk: the desk now prefers #219 (proposed by me) and the ledger prefers #182, whose author has agreed the split, with task-owned fallbacks for both until they are implemented.

---

# Comment on #6 (for the #100 ledger needs)

Hi! Task #100 (cross-account liquidity) plans to build on Finance Workspace, and TianyuCodings suggested raising its ledger needs here. #6 already covers recurring debits and minimum-balance rules, which is most of it. Three things the task still uses, in case they fit a later version:

1. A recurring debit that fails visibly when cash is short (the proposal already describes this, so it may be covered).
2. Transfers made outside business hours that are queued until the next business day and can be cancelled or replaced until they process, with a business-day calendar that includes a holiday.
3. A standing monthly grant (move up to a fixed amount between two owned accounts and buy one fund) inside your preview and approval model.

Two questions from #100: can a standing monthly grant like (3) fit your approval model, and can one user hold two separately branded brokerage accounts in the same workspace? If any of this is out of scope, #100 keeps a task-owned fallback, so there is no pressure. Thanks!
