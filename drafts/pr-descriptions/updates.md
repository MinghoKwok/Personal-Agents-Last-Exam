# PR description updates (replace the "Dependencies / questions" paragraph on GitHub)

## #128

**Dependencies / questions (optional):** The insurer side prefers Alderbrook Mutual claims (#181), which models written decisions per repair line, one deductible per claim and supplements, and names this task; a task-owned claims fixture with the same states is the fallback. The repair-shop workflow stays narrow and task-owned, because no proposal provides it. Related but distinct: #46 (auto-quote comparison environment) and #48 (comparing quotes before a policy change). #107 by the same author asks whether a credit settles a financial claim, whereas this task's decisive action comes before new liability is incurred. Feedback is welcome on the task-owned shop fixture and on scoring the paired S3 decision. Planned effort is 8–14 person-days.

## #107

**Dependencies / questions (optional):** The issuer side prefers Brindle Card (#182), which models partial refunds, a dispute's temporary credit and its reversal, and a merchant refund closed as matched, and names this task; a task-owned issuer fixture with the same states is the fallback. The merchant side is a narrow task-owned fixture. Related proposals include [merchant returns #7](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/7), [subscription cancellation #20](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/20) and [billing grievances #17](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/17). The runtime or scenario driver must deliver two ordered observations within one session. Planned effort is 7–12 person-days.

## #102

**Dependencies / questions (optional):** The first choice for document storage is Personal Document Records (#33); otherwise the task uses the shared Files App (`apps/files`, merged with #131), with version and source relationships kept in the task's manifest. Mail comes from the public runtime. The issuer document page and the CPA portal are minimal and task-owned, and the Personal Finance Workspace (#6) is an optional later integration, not a dependency. Related but distinct is #53, which tests whether instructions inside documents expand sharing authority. #100 is a complementary task by the same author. Feedback is welcome on #33's reuse boundary, session-history visibility and difficulty calibration.

## #95 (only if the description on GitHub still has the old text)

**Dependencies / questions (optional):** Calendar, Mail and Messages are in `main` (#12), and the runtime validation guidance (#61) is merged. Weather: Gustline (#126) first, Rainshadow (#123) as the alternative, a narrow task-owned fixture as the fallback; park status stays in the task. Related but distinct: #60 (transit replanning, closed) and #25 (campground environment, no forecasts). Feedback requested on: (a) whether session memory and timed events are available as infra primitives; (b) whether the rule-based S2 branch (tool-log rules plus a frozen field extractor) is acceptable, or whether S2 should be a single neutral check-in that always runs; whether difficulty is sufficient is an open design risk, so a pilot runs first after `plan-approved`; (c) whether the counterfactual "bad morning" fixture should become a scored variant.
