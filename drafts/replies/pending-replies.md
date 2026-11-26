# Pending replies

## #123 Rainshadow (reply to mingyin1)

https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/123

Thanks @mingyin1, and sorry for the slow reply. For #95:

- **Outlook text:** yes, the daily `summary` is enough, as long as it is returned exactly as issued for each issuance, like `headline`.
- **Beyond two sources with their own issue times, #95 needs:**
  - Hourly `pop` (ideally also `thunder_prob`) in the park's local time with its UTC offset. The park is in MDT and the user is in CDT.
  - Daily `headline` and `pop_day`.
  - Issuances released at task-scheduled virtual times, with superseded ones still queryable by `issuance.id`. The grader checks each figure against the issuance current when a message was sent.
  - One Flood Watch alert thread with `onset` and `ends`.
- **Choosing the latest issuance:** picking it by `issued_at` at or before the virtual time, as Jasonya suggested, is what #95 assumes.
- **Park status:** stays in the task, as you said.

No preference on field names: #95 will follow whatever Rainshadow and Gustline converge on.

---

## TianyuCodings reviews: one comment on each PR

Post the matching text on each PR.

### #100

Thanks for the review. I've updated the proposal to the current template: Section 4 is now the four fields, and Section 5 has the rubric, hint and reference solution. The file path is unchanged. I also changed the PR title to match the Short task title. Ready for the detailed review when you have time.

### #102

Thanks for the review. I've updated the proposal to the current template: Section 4 is now the four fields, and Section 5 has the rubric, hint and reference solution. The file path is unchanged. One open item is marked TBD: the per-point split of E1, E3 and E5, which will be fixed against the gold table before weights are frozen. I also dated the two 2024 reference documents in 2025, following the timeline rule in #164. Ready for the detailed review when you have time.

### #106

Thanks for the review. I've updated the proposal to the current template: Section 4 is now the four fields, and Section 5 has the rubric, hint and reference solution. The file path is unchanged. Qualification uses the default history; the Scholar-authorization counterfactual is reported separately as a paired diagnostic. I also stated that all platform records are dated on or after 2025-01-01, following #164. Ready for the detailed review when you have time.

### #107, #128, #129 and #133 (same text for each)

Thanks for the review. I've updated the proposal to the current template: Section 4 is now the four fields, and Section 5 has the rubric, hint and reference solution. The file path is unchanged. Ready for the detailed review when you have time.
