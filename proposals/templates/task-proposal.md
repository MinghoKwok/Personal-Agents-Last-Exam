# Task Track proposal

**PR title format:** `[Task Proposal] [<Domain>] <Short task title>`

Example: `[Task Proposal] [Travel & commuting] Adapt an airport pickup after a flight change`

Copy this template to `proposals/task/<slug>.md`. Keep the persona, story and personalization insight concise. Section 5 defines how the task is scored. The construction plan defines the scope, deliverables, quality checks and effort that reviewers will follow through implementation and merge in this same PR.

Completed implementations use the [LifePack v1.0 task delivery format](../../docs/lifepack-task-format.md). This proposal defines the plan; the package and run evidence follow approval.

✍️ Replace each `[Fill in: …]` with your answer. Optional fields can be `None`. For unresolved details, use `TBD` and explain how they will be resolved. See the [worked example](../task/lena-spring-gathering.md).

## 1. Task and domains

- **Authors / GitHub handles (required):** `[Fill in: names and @handles]`
- **Short task title (required):** `[Fill in: a concise task title]`
- **Primary domain (required):** `[Fill in: one domain from the table below]`
- **Secondary domains (optional):** `[Fill in: other relevant domains, or None]`

### Domain names

Use the exact names from the [homepage](../../README.md#environment-domains). Choose one primary domain and optional secondary domains; list the primary first in the PR title and join others with ` + `.

<table>
<tr><td>💳 <strong>Money &amp; insurance</strong></td><td>🛍️ <strong>Shopping &amp; groceries</strong></td><td>✈️ <strong>Travel &amp; commuting</strong></td></tr>
<tr><td>🩺 <strong>Health &amp; care</strong></td><td>🍽️ <strong>Food &amp; dining</strong></td><td>💬 <strong>Social &amp; communities</strong></td></tr>
<tr><td>🏠 <strong>Home &amp; utilities</strong></td><td>🏛️ <strong>Public service &amp; law</strong></td><td>🎬 <strong>Media &amp; entertainment</strong></td></tr>
<tr><td>📚 <strong>Learning &amp; research</strong></td><td>💼 <strong>Work &amp; business</strong></td><td>📰 <strong>News &amp; information</strong></td></tr>
<tr><td>🌤️ <strong>Weather &amp; outdoors</strong></td><td>🎮 <strong>Games &amp; play</strong></td><td>🏃 <strong>Fitness &amp; wellbeing</strong></td></tr>
</table>

## 2. User persona and prior history

Who is the user? Briefly describe the background, preferences and prior experiences that matter to this task.

**✍️ Your answer (required):** `[Fill in: user persona and relevant history]`

## 3. Story outline

What does the user want, what changes, and what would a good outcome look like? Mention the approximate time span if relevant.

**✍️ Your answer (required):** `[Fill in: the story outline]`

## 4. What makes this distinct and personal

Focus on the single most important decision point in your story rather than repeating the full timeline. Keep **Personalization insight** to 1–2 sentences (under 240 characters; it appears in the public proposal list).

- **Personalization insight (required):** `[Fill in: 1–2 sentences on why the right action depends on this person's history, boundaries or relationships rather than the surface request alone]`
- **Decisive context and trigger (required):** `[Fill in: one concrete request, mid-task change or non-response, plus where and when the agent can discover the personal context that governs it]`
- **Generic assistant mistake (required):** `[Fill in: what a capable non-personal assistant would plausibly do at that moment and why it fails this user]`
- **Different user, different action (required):** `[Fill in: keep the user's request wording identical, change only the user's prior history, preferences or standing permissions, and state how the right action changes]`

Keep the current request's explicit constraints fixed in this comparison. Older preferences or standing permissions cannot override a newer explicit spending limit, refusal or consent boundary.

## 5. Rubric, hint and reference solution

Define how the task will be scored before implementation. Exact weights and thresholds can be calibrated with pilot runs before the freeze. Adding or removing rubric items, or changing what counts as success, needs another design review. At implementation, each item becomes either a rule-based check or an LLM-judge question, keeping the same ID. A first submission does not need all of this settled: mark open parts `TBD`, and they are worked out with reviewers before plan approval.

### Rubric

List **forbidden** items (lines the agent must not cross; crossing any one fails the task) and **expected** items (what a good outcome achieves, with points). Do not list the same thing in both. For each item, give the evidence (where and when the agent can learn what is required) and the data the grader checks. Every requirement in Sections 2–4 must map to at least one item. Give the decisive outcome more points than the gap between the total and the pass mark, so an agent that misses it cannot pass. Check outcomes, not whether the agent copied the reference.

**✍️ Forbidden (required):**

- **F1 — `[Fill in: short name]`.** `[Fill in: the line the agent must not cross]` *Evidence:* `[Fill in: record and date]`. *Checked from:* `[Fill in: data the grader reads]`.

**✍️ Expected (required):** `[Fill in: total]` points.

- **E1 (`[Fill in: points]`) — `[Fill in: short name]`.** `[Fill in: the outcome and how its points are awarded]` *Evidence:* `[Fill in: record and date]`. *Checked from:* `[Fill in: data the grader reads]`.

**✍️ Full pass (required):** `[Fill in: no forbidden item is triggered and the score is at least N of the total; show that the decisive item carries more points than the gap]`

### Hint

Write the exact hint text. The hint points to the records that hold the decisive facts. It may name a record’s source, sender and date. It must not quote or paraphrase what a record says, prescribe actions, or name a record that does not exist yet when the hint is shown. Hinted runs follow the validation rules in [CONTRIBUTING](../../CONTRIBUTING.md).

**✍️ Hint (required):** `[Fill in: the exact hint text]`

- **Injection:** `[Fill in: when and where the hint is shown; identical for all models]`

### Reference solution

Give one timeline that completes the task with a full score: what triggers each step, what the agent does, which record it relies on, the resulting state and the rubric items it satisfies. One complete path is enough; it does not need to cover every way the conversation could go. Then list other approaches the grader must accept.

**✍️ Reference (required):**

| Time | Trigger | Agent action | Relies on | Resulting state | Items |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[Fill in: timestamp]` | `[Fill in: request or event]` | `[Fill in: what the agent does]` | `[Fill in: records used]` | `[Fill in: state afterwards]` | `[Fill in: rubric IDs]` |

**✍️ Other accepted approaches (required):** `[Fill in: other ways to reach a full score that the grader must accept]`

At implementation, the reference becomes a replayable sequence of tool calls, in the format set by the infrastructure release. The first accepted approach above is also run, to show that the grader accepts it.

## 6. Construction plan and effort

Specify the work needed to turn the story into an executable, scoreable task. Include expected coverage and effort in person-days; estimates may be ranges. The user rollout is the planned sequence of user interactions and responses, including branches. Fix what the user does at the decisive moment; other replies may depend on what the agent asks. Agent rollouts are actual model executions against that scenario.

**✍️ Work breakdown (required):**

| Workstream | Planned work and scale | Deliverable / quality check | Effort (person-days) |
| :--- | :--- | :--- | :--- |
| Persona, history and workspace | `[Fill in: context, records/media to create or reuse, quantities and sources]` | `[Fill in: coherent user context and discoverable evidence for the personalization insight]` | `[Fill in: estimate]` |
| User rollout and scenario script | **Sessions:** `[Fill in: number of sessions]`<br>**Simulated world time span:** `[Fill in: hours, days, months or years covered]`<br>**Estimated total tokens:** `[Fill in: range or order of magnitude across all sessions]`<br>Use timestamps with UTC offsets for sessions and events (e.g. `2026-11-12T08:30:00-08:00`). | `[Fill in: executable user script, response/no-reply paths, changes over simulated time and state carried across sessions]` | `[Fill in: estimate]` |
| Environment integration | `[Fill in: apps/environments to reuse or build, fixtures, actions and missing dependencies]` | `[Fill in: runnable task package and initial-state/reset checks]` | `[Fill in: estimate]` |
| Rubrics, reference and hints | `[Fill in: grader work for the items in Section 5, the reference and any accepted alternative to be run]` | `[Fill in: checks that the reference earns a full score, doing nothing earns none, and accepted alternatives pass]` | `[Fill in: estimate]` |
| Agent rollouts and analysis | `[Fill in: planned runs per designated GPT, Claude and Gemini model, hinted runs and analysis work]` | `[Fill in: traces, scores and failure analysis meeting the linked validation protocol]`<br>Timestamp agent actions and observations on the same simulated timeline as the user script; record real execution dates and wall-clock duration separately. | `[Fill in: estimate]` |

Estimate token volume for **one complete scenario across all sessions** and state what is included, such as dialogue, prior context and tool outputs. The simulated time span is the time elapsed in the user's world; development duration is recorded below.

On the simulated timeline, tasks involving interaction with external platforms must start their first session **on or after 2026-01-01**, records of the user's interactions with external platforms must be dated **on or after 2025-01-01**, and text-only user history, such as personal background, past experiences, preferences and user–agent conversations, has **no earliest-date restriction**.

- **Milestones, owners and dependencies (required):** `[Fill in: work order, responsible contributors, expected calendar duration and environment/infra dependencies; link related PRs]`
- **Resources and total effort (required):** `[Fill in: total person-days, estimated model/API and generation costs, and compute needs; estimates or explained TBDs]`
- **Scope boundary and open questions (required):** `[Fill in: what is excluded or deferred, and how unresolved decisions will be settled]`
- **Data provenance and privacy (required):** `[Fill in: invented, or transformed from a real experience; sources and reuse terms of any collected material; confirm that private messages, account details and third-party personal information are removed]`

After approval, add the script, grader and author-run evidence against these deliverables in the same PR. Reviewers use the approved plan as the acceptance baseline; substantial scope changes require another design review. Follow the [implementation and validation guide](../../CONTRIBUTING.md#task-difficulty-and-validation).
