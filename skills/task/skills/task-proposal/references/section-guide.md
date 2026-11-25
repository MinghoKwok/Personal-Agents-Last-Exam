# Section guide

For each part of the task proposal: what a good answer looks like, the gaps that are common in submitted proposals, and questions that close them. The questions are examples. Adapt them to the story, and always attach a suggested answer.

The section numbers follow `proposals/templates/task-proposal.md`. If the template has changed, follow the template.

## Contents

- [Sections 1–3: domains, persona and story](#sections-13-domains-persona-and-story)
- [Section 4: the decisive moment](#section-4-the-decisive-moment)
- [Section 5: rubric](#section-5-rubric)
- [Section 5: hint](#section-5-hint)
- [Section 5: reference solution](#section-5-reference-solution)
- [Section 6: construction plan](#section-6-construction-plan)
- [Upgrading an older proposal](#upgrading-an-older-proposal)
- [Review before handing over](#review-before-handing-over)

## Sections 1–3: domains, persona and story

**Good looks like:** one primary domain with its exact name from the template's table. A persona that includes only what matters to this task. A story with dated events: what the user asks, what changes later, and what a good outcome is.

**Common gaps**

- Events have no dates, or timestamps have no UTC offset, so nobody can tell what the agent could have known at each step.
- The story says a fact exists ("she is allergic to nuts") but not where it is recorded or who said it.
- Nothing changes after the first request. A task where everything is known at the start tests retrieval, not a personal agent working over time.
- The persona lists preferences that the story never uses.

**Questions**

- "On what date and at what time does each event happen, and in which time zone? I suggest: …"
- "Where is this fact recorded: an email, a message, a calendar entry? Who wrote it and when?"
- "What changes after the first request? If nothing does, should something?"
- "Which domain is primary? I suggest … because the main action happens there."

## Section 4: the decisive moment

**Good looks like:** one moment in the story where the right action depends on this person's history, limits or relationships. The four fields describe that single moment. The personalization insight is one or two sentences, at most 240 characters, because it is shown in the public proposal list.

A story may have several such moments. The proposal needs the one that matters most; the others can simply appear in the rubric.

**Finding it.** Contributors often cannot say which moment is decisive. Three tests help:

1. **One mistake.** If the agent could get only one thing wrong and the user would still be upset, which thing is it?
2. **One sentence of help.** If you could whisper one sentence to a failing agent, what would it be about?
3. **A different user.** Keep the request word for word and change only the user's past. Does the right action change? If it does not, the moment is not personal.

**Common gaps**

- The answer repeats the whole timeline instead of one moment.
- Personalization is on the surface: the user's name or preference is mentioned, but any careful assistant would act the same way.
- "Different user, different action" changes the request instead of the user's history.
- The generic mistake is a strawman that no capable assistant would make.

**Questions**

- "If the agent gets everything else right, which single mistake would make this a failure for the user?"
- "Suppose a different person sends exactly the same request. What in their history would make a different action correct?"
- "What would a careful assistant that knows nothing about this user most likely do at that moment?"

## Section 5: rubric

**Good looks like:** two lists and a pass rule.

- **Forbidden items** are lines the agent must not cross. Crossing one fails the task.
- **Expected items** are what a good outcome achieves, each with points.
- Each item states its **evidence** (the record and date from which the agent can learn the requirement) and what the grader **checks** (order records, outgoing messages, calendar and so on).
- **Full pass** is no forbidden item triggered plus a minimum score. The decisive outcome carries more points than the gap between the total and that minimum, so an agent that misses it cannot pass.

There is no separate list of constraints. A constraint is either a forbidden item or an expected item. Temporal prohibitions such as "never changes the start time" require the ordered change history or attributable tool-call trace; a final snapshot cannot detect a violation that was later undone.

**Common gaps**

- Criteria are prose ("handles the dietary need appropriately") with nothing the grader could check.
- The same thing is listed as both forbidden and expected.
- An agent that does nothing still earns points, usually from items such as "does not overspend" that are trivially true when nothing happens. Make such an item forbidden, or score it only if the main outcome exists.
- The decisive outcome is worth so little that an agent can miss it and still pass.
- An item checks whether the agent followed the reference steps instead of checking the result.
- An item relies on a fact that no record contains.

**Questions**

- "What must the agent never do, even if everything else goes well? I found these in your story: … Anything else?"
- "If the agent does nothing at all, what should the score be? With the current items it would be …"
- "For this item, which record tells the agent it is required, and what will the grader look at to decide?"
- "Can an agent miss the main outcome and still pass with these points? Right now it can / cannot."
- "Is there another way to reach a good result that these items would wrongly reject?"

## Section 5: hint

**Good looks like:** the exact text that will be shown to the agent in hinted runs. It points to the records that hold the decisive facts and may name a record's source, sender and date. It does not quote or paraphrase what a record says, does not tell the agent what to do, and does not name a record that does not exist yet when the hint is shown.

In a story with several sessions, a hint shown at the start cannot mention an email that arrives later without giving away that something will change. Refer to changing records as "the most recent message from …", so that the same text works in every session.

**Three leak tests**

1. **Reconstruction.** Could someone write the reference solution from the hint alone? If so, it says too much.
2. **Values.** Does the hint contain a number, name or choice that a rubric item checks?
3. **Actions.** Does the hint tell the agent to order, send, cancel, choose or wait?

**Common gaps**

- The hint states the fact ("remember Maya is allergic to nuts") instead of pointing to where it is.
- The hint prescribes the solution ("switch to the cheaper menu before noon").
- The hint is a description of a hint ("will point to the relevant emails"), not the text itself.

**Questions**

- "Which records hold the facts the agent needs at the decisive moment? I suggest pointing to: …"
- "Your hint says '…'. That states the fact itself. Can we say where to look instead: '…'?"
- "Is any of these records created after the session in which the hint is first shown?"

## Section 5: reference solution

**Good looks like:** one timeline that completes the task with a full score. Each step gives the trigger, what the agent does, the record it relies on, the resulting state and the rubric items it satisfies. One complete path is enough. Other good approaches are listed separately, so the grader is not built to accept only this one.

The user's behaviour at the decisive moment is fixed by the story (for example, "she does not reply before the deadline"). Other replies may depend on what the agent asks.

**Common gaps**

- The reference is one sentence ("the agent checks the messages and orders the right menu").
- A step relies on a fact that is not in any record.
- A rubric item is never satisfied by any step, or a step cites an item that does not exist.
- The user's behaviour at the decisive moment is left open, so runs would not be comparable.

**Questions**

- "Walk me through the ideal run. What does the agent do at each dated event? Here is my draft: …"
- "At the decisive moment, what exactly does the user do or not do? This has to be the same in every run."
- "What other approaches should count as correct?"

## Section 6: construction plan

**Good looks like:** each workstream has a concrete scale (number of records, sessions, runs), a deliverable with a quality check, and an effort estimate in person-days. Planned model runs follow the validation rules in `CONTRIBUTING.md`.

Propose these numbers yourself from the story and ask the contributor to correct them. They are estimates, and ranges are fine.

**Common gaps**

- "TBD" with no way to resolve it.
- Effort that does not match the scale (thirty records and a new simulated service in one day).
- Fewer planned runs than `CONTRIBUTING.md` requires, or no hinted runs.
- No statement of where the data comes from, or a real conversation reused without saying how private details are removed.

**Questions**

- "The story needs about … records and … sessions. I estimate … person-days. Does that match your experience?"
- "Which apps does this need? Do they exist in the repository already, or do you plan to build or simulate one?"
- "Is the story invented or based on something real? If real, what has been changed or removed?"

## Upgrading an older proposal

Proposals written with an earlier template keep the rubric, hint and reference inside one row of the construction plan, often as "gates" plus weighted categories. Keep the author's design and move it; do not replace it.

| The old proposal has | In the current template |
| :--- | :--- |
| A gate that prohibits something ("must not share…", "never exceeds…") | A forbidden item |
| A gate that requires an outcome ("the booking exists", "all three targets met") | An expected item, with enough points that missing it fails the task. Several such gates that describe one outcome can become one all-or-nothing item. |
| Weighted categories or scored criteria | Expected items, keeping the author's weights where they still add up |
| A list of constraints | Each one becomes a forbidden item or an expected item |
| "Success criteria" in prose | Split into items the grader can check; mark `TBD` where the check is unclear |
| A hint that states a fact or an action | Keep the author's text visible, put a suggested rewording that points to records next to it, and ask which to use |
| A one-line reference approach | A draft timeline built from the story, marked as your proposal |
| Free-text Section 4 | The four fields, split from the author's own sentences |

After mapping, three things usually need a question:

- **Arithmetic.** Old weights were not designed around a pass mark. Check whether the largest item outweighs the gap between the total and the pass mark, and ask how to rebalance if it does not.
- **Evidence.** Old criteria rarely say which record states the requirement. Ask for the record and date of each.
- **Existing results.** If the proposal reports pilot scores, compare them with the thresholds in `CONTRIBUTING.md` and tell the contributor where they stand. A pilot above the threshold means the task or the rubric needs to change before validation, and that is better said now.

## Review before handing over

The checker covers structure and arithmetic. These need judgment. Go through them before each round of questions and again before handing over, and tell the contributor about any that fail. They are advice for a stronger proposal, not conditions for submitting one.

1. **Personal.** Apply the "different user" test to Section 4. The right action must change when only the user's history changes.
2. **Discoverable.** Every requirement a rubric item scores is stated in a named record with a date, and that record exists before the agent needs it. An item that scores something nobody asked for fails this test.
3. **Doing nothing fails.** Work out the score of an agent that takes no action. It should be zero or close to it.
4. **The obvious wrong answer fails.** Work out the score of the generic mistake described in Section 4. It should trigger a forbidden item or score well below the pass mark.
5. **No overlap.** Nothing is listed as both forbidden and expected.
6. **Outcomes, not steps.** No rubric item requires the agent to follow the reference steps.
7. **The hint does not leak.** Apply the three leak tests.
8. **The reference earns a full score.** Walk through it against every item.
9. **Consistent.** Dates, amounts and names agree across the story, the rubric and the reference.
10. **Private details removed.** No real names, messages or account details are present, and the data provenance field says so.

When comparing two users with the same current request, preserve its explicit constraints. Prior history or standing permission cannot override a newer spending limit, refusal or consent boundary.
