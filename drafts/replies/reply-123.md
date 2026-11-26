Thanks @mingyin1, happy to answer for #95.

**Outlook text:** yes, the daily `summary` is enough. #95 only needs the agent to be able to read an outlook sentence such as "Storms this evening could be strong to severe" alongside the headline. It does not need a separate structured product. The task needs one thing from it: the `summary` must be returned exactly as issued for each issuance, like `headline`.

**Two sources with their own issue times:** these are the core, but #95 also relies on three other things Rainshadow already describes:

1. **Hourly and daily rows per issuance:**
   - Hourly `pop` (and ideally `thunder_prob`) in the park's local time with its UTC offset. The park is MDT (`-06:00`), and the user is in CDT, so the offset matters.
   - Daily `headline` plus `pop_day`. The task's headline is "Strong Storms, 60%".
2. **Task-scheduled issuances, with earlier ones still queryable:** #95 releases issuances at fixed virtual times: an afternoon issuance on 2026-09-11, a revised one at 2026-09-11T19:30-06:00, and a new one at 2026-09-12T05:00-06:00. The grader checks the agent's figures against the issuance current when each message was sent, so it needs `issuance.id`, `issued_at` and access to superseded issuances. Please confirm that "latest" means the most recent `issued_at` at or before the current virtual time, which is the open point in your design.
3. **One alert thread:** a Flood Watch for the park's zone, with `onset` 2026-09-12T18:00-06:00 and `ends` 2026-09-13T06:00-06:00, that stays unchanged across the issuances.

**Park status:** agreed, it stays in the task.

The two sources only need to differ modestly. One has a 60% daily headline and an 88% evening peak; the other has 50% and 80%. Neither falls back to the other, which matches Rainshadow's "never interpolates" rule. I have no preference on field names: if Rainshadow and Gustline converge on one naming, #95 will follow it.
