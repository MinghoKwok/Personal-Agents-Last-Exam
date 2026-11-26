## Track and stage

**Track (required): select one.**

- [ ] Environment Track
- [x] Task Track
- [ ] Other change

**Stage (required):** Proposal

## Design

**Design file (required for Environment or Task):** [proposals/task/niw-evidence-folder.md](https://github.com/MinghoKwok/Personal-Agents-Last-Exam/blob/task/niw-evidence-folder/proposals/task/niw-evidence-folder.md)

This task tests whether a personal agent can work out which evidence a user's case needs, acquire it from fragmented personal sources, and deliver a packet whose stored bytes actually support its claims. A fictional researcher asks the agent to prepare a research-evidence folder for an immigration attorney. The attorney's requirements, the researcher's earlier approvals and the evidence itself are spread across mail, a Scholar-like profile, preprint, review and publisher surfaces, saved files and review records. None of these facts are restated in the live request.

Over four sessions and three simulated weeks, the agent faces:

- An acceptance email that must be told apart from a notice for a different submission.
- A Scholar duplicate and a namesake's article.
- A preprint whose title closely resembles another work's.
- A citation that uses a dataset rather than an algorithm.
- Peer-review services with different levels of proof.
- A stale anonymous upload in the attorney's portal.
- A proceedings version that becomes available on delivery day.

A personal-history control varies only whether the user pre-authorized merging a verified Scholar duplicate. Further controls vary the evidence that is available. In these, the gates separate three cases: acceptance proof that exists but is not found, which fails; acceptance proof that is genuinely unavailable, which is acceptable as an honest partial delivery; and missing evidence of authorship, where the agent must not claim that authorship has been verified.

Grading is outcome-based: a 100-point rubric and five gates checked against portal bytes, IDs, versions and logs. Legal merit, eligibility advice and government filing are out of scope.

## Summary and dependencies

**Summary (required):** A Public service & law task on autonomous evidence acquisition across fragmented personal sources, personal-history-dependent permissions, requirement-to-evidence traceability, and verified delivery to an attorney portal.

**Dependencies / questions (optional):** The task needs simulated Mail and cross-session persistent files with immutable bytes. The document store could reuse #33 or be a limited task-owned store. It also needs narrow task-owned adapters for the Scholar-like, preprint, publisher and review surfaces, plus a minimal attorney portal; adapter complexity will be agreed with maintainers before building. #4 (Zotero-inspired research library) is an optional source of paper records. Related but distinct: #102 by the same author maintains a largely predefined set of tax documents for artifact consistency, whereas this task centers on discovering and acquiring evidence. Feedback is welcome on the adapter scope and on cross-session file support.

## Progress and evidence

- [x] Proposal ready for design review
- [ ] Plan approved by maintainer
- [ ] Implementation complete
- [ ] Validation evidence attached

**Evidence (required for final validation; optional for proposals):** None at the proposal stage. Nothing has been implemented or run on frontier models, and no difficulty claim is made.
