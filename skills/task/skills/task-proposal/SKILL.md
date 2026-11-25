---
name: task-proposal
description: Draft, complete or upgrade a Task Track proposal for Personal Agents' Last Exam by interviewing the contributor for the details they tend to leave out. Use this whenever someone wants to turn a story, idea, pasted chat or old proposal into `proposals/task/<slug>.md`, asks for help with the task template, its rubric, hint or reference solution, wants an existing proposal moved to the current template, or wants a proposal checked before opening or updating a PR.
---

# Task proposal

Help a contributor write a Task Track proposal at `proposals/task/<slug>.md`. The contributor knows the story. Your job is to write it down in the template's structure and to ask for what is missing, because the parts people skip (where each fact lives, what must never happen, what the hint may say) are the parts reviewers need most.

You are a helper, not a gate. Nothing here stops a contributor from submitting. A proposal with open gaps can still be opened as a PR, and reviewers will pick up what is left. Point out what is missing, make it easy to fix, and leave the decision to them.

## Sources of truth

Read these from the repository before drafting. They change over time, so follow what they say now, not what you remember.

- `proposals/templates/task-proposal.md`: the structure and the instructions for each field.
- `proposals/task/lena-spring-gathering.md`: a worked example showing the expected level of detail.
- `CONTRIBUTING.md`, the Task Track and validation parts: the acceptance rules.

This skill adds a way of working and a checker. It does not add acceptance rules. If this skill and those files disagree, follow the files and tell the contributor.

If the working directory is not a clone of the repository, ask the contributor to work in a clone of their fork. They need one to open the PR anyway.

## How to work

### 1. Take whatever the contributor has

Accept any of these, and ask which one they have if it is not clear:

- **A few sentences describing the story.** The usual starting point.
- **An existing proposal**, as a file path or a PR number. Read the file and treat it as the draft to upgrade.
- **A pasted conversation or an exported file.**
- **A link to a shared chat.** Try to read it. These links often need a login, so if you cannot read it, ask the contributor to paste the text.

Raw material stays out of the repository. A real conversation or a story about real people usually contains names, messages, health or account details, and the template requires those to be removed. Raise this in your first reply, not at the end: ask the contributor to remove sensitive details before pasting, write only a fictionalized version into the proposal, and do not save the raw material to a file in the repository. Screenshots are a poor source for the same reason; ask for text.

Before drafting, open the [live proposal list](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/blob/proposal-index/proposals/proposal-list.md) and look for proposals with a similar story. `proposals/proposal-list.md` on `main` is only a link to that generated index; do not treat it as the list itself. If the live index cannot be read, inspect the current GitHub PR list or state that the overlap check is incomplete. Tell the contributor about related proposals; approval does not reserve a topic or automatically exclude parallel work.

### 2. Draft first, then ask

Copy the template to `proposals/task/<slug>.md` and fill it in. Do not start with a list of questions: a contributor reacts faster to a draft than to an empty form. For a new proposal, the slug is a few lowercase words joined by hyphens. When upgrading, keep the file path the proposal already has, so its PR keeps pointing at the same file.

How much to write yourself depends on what you were given:

- **Details you may invent:** names, dates, prices, places, the wording of messages. Use fictional ones and say which they are.
- **The core you may propose but not decide:** the decisive moment, what changes during the story, what must never happen, and the rubric that follows from them. For a new story, draft all of these so the contributor has something to react to, and make the parts that were not in their material your first questions. If the story has no change after the first request, propose one and ask.
- **An existing design you should preserve:** when upgrading, keep the author's wording, items and weights wherever they fit the current template, and move content to the field where it now belongs. Where the old design does not fit, write `TBD` with your suggestion next to it instead of silently replacing it. `references/section-guide.md` has a section on upgrading.

Where you do not know something, write `TBD` followed by what is needed to resolve it.

Write the proposal in English. Talk to the contributor in the language they use.

### 3. Ask for what is missing, a few questions at a time

Before each round, run the checker (step 4) and go through the "Review before handing over" list in `references/section-guide.md`. Together they are the best source of questions: they show what is missing and what would not survive review.

Each message to the contributor has two short parts:

- **What you assumed.** A brief list of the details you invented, for them to correct. They do not need to answer these one by one.
- **Questions.** At most four per round, as a plain numbered list. Give each a suggested answer, so the contributor can reply "1 yes, 2 use yours, 3 no, it should be…". Say in a few words why a question matters when that is not obvious. Plain numbered text works in every tool; a structured question prompt is fine if your environment has one.

When more than four things are open, choose by this priority, because later answers depend on earlier ones:

1. **The decisive moment** (Section 4), together with the facts it rests on: where they are recorded and when. Everything else is built around it.
2. **The rubric**: what must never happen, what a good outcome achieves, and whether the points make the decisive outcome necessary.
3. **The hint and the reference solution.**
4. **The construction plan.** Propose the estimates yourself and ask the contributor to correct them.

This is a priority, not a script. One round may mix sections, and when upgrading a proposal whose story is already settled, start with whatever the checker and the review list flag.

`references/section-guide.md` lists, for each section, what a good answer looks like, the gaps that are common in submitted proposals and questions that close them. Read it before the first round.

Update the file after each round, so progress lives in the proposal and not in the conversation. The contributor can stop at any point, continue later from the file, or submit as it is. Stop asking when nothing important is open, or as soon as the contributor says it is good enough. Do not repeat a question they have chosen not to answer; write `TBD` there and move on.

### 4. Check

Run the checker from this skill's folder:

```sh
python3 <this skill's folder>/scripts/check_task_proposal.py proposals/task/<slug>.md
```

It is advisory. It lists gaps (something the template asks for that is not there yet) and notes (worth a second look), and neither blocks submission. It checks structure against the template, leftover placeholders, domain names, the length of the personalization insight, rubric points and the pass mark, that every rubric item appears in the reference solution, and timestamps. It is quick, so run it after every round. Fix what you can yourself and turn the rest into questions.

The checker cannot judge content. A draft can have no gaps while a rubric item relies on a fact no record contains, or while the hint gives the answer away. The review list in `references/section-guide.md` covers those; go through it yourself each round and report anything that fails.

### 5. Hand over

Tell the contributor:

- where the file is, and which gaps and `TBD`s are still open, so they can mention them in the PR if they submit now;
- which parts you proposed and they have not confirmed;
- the PR title the checker printed, and that the PR description follows `proposals/templates/pr-summary.md`.

Do not commit, push or open a PR unless the contributor asks. The proposal goes out under their name, so they decide when it is ready.
