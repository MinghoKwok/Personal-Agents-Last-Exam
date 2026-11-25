---
name: env-proposal-review
description: Turn an Environment Track proposal review into feedback the proposal author can act on, by combining the agent checklist results with the human reviewer's decisions. Use this whenever someone reviews an environment proposal PR, asks what the human reviewer still has to decide, answers earlier review questions, or wants feedback written for a proposal author (for example "审一下这个 proposal", "给作者写反馈", "哪些需要我判断").
---

# Environment proposal review

Help a reviewer get from "the checklist has been run" to "the author knows what to change". The agent reads and verifies, the human reviewer makes the judgment calls, and the author sees only the result.

## Sources of truth

Read these from the repository before reviewing. They change over time, so follow what they say now, not what you remember.

- `docs/review/environment-proposal-checklist/agent.en.md`: the checks, the verdicts and how to run them.
- `docs/review/environment-proposal-checklist/human.en.md` (or `human.zh-Hans.md`): what the human reviewer decides, and the review comment they post.
- `docs/review/environment-proposal.md`: the review guide.
- `docs/review/proposal-lifecycle.md`: how a plan is approved and recorded.
- `proposals/templates/environment-proposal.md` and `CONTRIBUTING.md`: what authors were asked to write.

This skill adds a way of working, a feedback format and a checker. It does not add acceptance rules. If this skill and those files disagree, follow the files and tell the reviewer. If the reviewer gives you their own copy of the checklists, use that copy and say so in the report.

If the working directory is not a clone of the repository, ask the reviewer to work in one, or read the files above from GitHub at the revision being reviewed.

## What you produce

Three files per PR, for three audiences. Keeping them apart is what keeps the author's feedback short.

| File | Audience | Contains |
| --- | --- | --- |
| `review-report.md` | The reviewer | Every verdict with its evidence, the dependency evidence, suggestions for the human checklist, and the reviewer's recorded decisions |
| `decisions-needed.md` | The reviewer | Only the questions that need the reviewer's judgment |
| `author-feedback.md` | The proposal author | What to change, answers to the author's own questions, and suggestions that affect the design |

`references/` has an outline for each. Write in the language the reviewer is using unless told otherwise, and say at the top of `decisions-needed.md` which language the author feedback is in. Do not stop to ask.

A new PR starts at step 1. A reviewer replying to earlier questions starts at step 4.

## How to work

### 1. Run the agent checklist as written

Follow `agent.en.md` for the review itself. Three habits make the result trustworthy:

- **Pin what you reviewed.** PR number, head commit, proposal path. Read the proposal with line numbers and quote it as `file:line`.
- **Open the file before stating a fact about it.** Whether an App, an operation or a format exists is settled by the repository at that revision, not by its name appearing in the proposal. Say which checks were static and what was not run. If you cannot confirm something from files you can open, do not build an item on it.
- **Classify from the proposal's own sentence, and count before you state a number.** A proposal that mentions a GUI is not "browser-only" if the same line lists MCP operations. Before reporting any list of "the PRs with problem X", re-read the cited line for each one.

Also list the questions the author asks in the proposal, and mark each as answerable from the repository as it is, or needing the reviewer.

Several PRs at once suit parallel subagents, one per PR, given the same files and the report outline. Treat their summaries as claims and spot-check quotes and dependency findings before relaying them.

### 2. Sort the findings

Put every finding that is not an Approve into one group. This is the step that turns a table of verdicts into a short list.

| Group | What belongs here | Default destination |
| --- | --- | --- |
| A. Integration | Dependencies, interfaces and platform fit, as the current checklist defines them | Problem for the author |
| B. Design | A contradiction or gap that changes how the App is built | Problem for the author |
| C. Implementation detail | Does not change whether the design is feasible | Stays in the report |

### 3. Ask the reviewer only what needs judgment

Write `decisions-needed.md`:

- Human-checklist items that evidence cannot settle, such as value, realism of effort, licensing and naming, and first-version scope.
- Verdicts where the checklist text points two ways. Quote the clause on each side and say what changes for the author. When asked whether something is a Reject, re-read both the Reject condition and the general rules that soften it, and show both.

One question per decision; number the parts 3a, 3b, 3c when they could be answered differently. With several PRs, group by question so one answer settles all of them. For each question, say what each answer would do to the author feedback.

Draft `author-feedback.md` at the same time, because the reviewer usually wants to read it next to the questions:

- An item whose request to the author is the same whatever the answer stays in the draft.
- An item whose request would differ stays out; put the alternative wordings in the decision list.
- A question the repository already answers is stated as a fact in the draft. The reviewer can still overrule it.

### 4. Apply the reviewer's answers

1. Split compound answers and record each one, dated and in the reviewer's words, under "Reviewer's decisions" in the report.
2. Apply each to the feedback:

| Answer | Effect on author feedback |
| --- | --- |
| "Not a problem" | Remove the item. Do not tell the author it is fine. |
| "Must change" | Problem to resolve. Ask for exactly what the reviewer required; if the checklist asks for more, tell the reviewer rather than adding it. |
| "Worth mentioning" | Suggestion. |
| "Keep the verdict" or "keep the author's approach" | No new problem. If it answers a question the author asked, put it under the answers. |

3. Leave verdicts and counts as they were and annotate the affected rows. The report records what the agent found and what the human then decided.
4. Update the suggestions for the human checklist.
5. Do not stretch an answer. "No implementer is fine" does not settle "is this worth building".
6. Re-verify items that are new or reworded, run the checker, and mark the questions as answered.
7. Reply to the reviewer in a few lines: what changed against the draft, anything you kept or added on your own judgment, what was not verified, what still waits on them.

### 5. Write for the author

Use `references/author-feedback.en.md` or `references/author-feedback.zh-Hans.md`:

1. **Header**: the recommendation and the reviewed file @ commit.
2. **Problems to resolve**: numbered, three lines each. What the proposal says, with the line number; why it does not work; what to change.
3. **Answers to your questions**: only when the author asked something.
4. **Suggestions**: only those that affect design or implementation.

Delete the last two sections when they are empty. Merge items that share one fix. More than about eight problems usually means some belong in group C.

Every line should be something the author can act on. Leave out:

- **Strengths, "this is fine", the reviewer's decisions and how the review was done.** They belong in the report.
- **Open-ended referrals.** Do not write that something "has been forwarded" unless it has. If a decision belongs to someone else, name who decides and what the author should do meanwhile.
- **Implementation-level detail.** It belongs to delivery review. An example of a message sent to another App is different: it is how compatibility with the receiver is checked.
- **Cosmetic points** such as slightly inconsistent numbers, wording or field formatting. They bury the items that matter.
- **Anything unverified.** Verify it and state it plainly, or drop it.

When a requirement is newer than the proposal, word it neutrally ("the review criteria now ask for…") so it does not read as the author's oversight.

The human checklist defines the review comment that is posted on the PR. `author-feedback.md` is the readable part of that comment; it does not replace the checklist block.

## Check before handing over

```bash
python3 scripts/check_feedback.py <author-feedback.md> <proposal.md>
python3 scripts/check_feedback.py --report <review-report.md> <proposal.md>
```

The first form checks cited lines, quotations, the item count, leftover placeholders and wording that should not reach the author. The second checks only citations and quotations. Double-quoted English phrases are treated as quotations from the proposal, so keep double quotes for proposal text and put other terms in backticks. The checker cannot judge whether a paraphrase is fair, so also read each "what the proposal says" line against the line it cites.

Then tell the reviewer what was verified and how, what was not, and what still waits on them.

Do not post to GitHub, request changes, approve, or issue a lifecycle command such as `/approve-plan` on the reviewer's behalf unless they ask for that specific action. The files are drafts for the reviewer to send, and approving a plan is the reviewer's own step.
