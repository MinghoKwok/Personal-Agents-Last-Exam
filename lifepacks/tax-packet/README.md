# LifePack: tax-packet (Task #102)

LifePack 1.0 delivery package for **"Maintain and deliver a verified tax packet as evidence changes"**, approved at commit `8af3a0c` in [PR #102](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/102). This is a work-in-progress implementation: everything that does not depend on the shared session runner is built and checked; model rollouts wait for it.

| Task ID | Domain | Sessions | Simulated span | Estimated tokens per scenario |
| :--- | :--- | :--- | :--- | :--- |
| `tax-packet` | Money & insurance | 5 (S1 to S5) | 2026-02-03 to 2026-03-10 (about 5 weeks) | about 150k to 300k (dialogue, carried context, tool results, agent output; excluding grading and hidden reasoning) |

## Status

| Part | State | Check |
| :--- | :--- | :--- |
| Task-owned CPA portal (`environment/apps/cpa-portal`) | built; subset of the Casefold design in #222 | 10 business tests; public verifier 36/36 |
| Task-owned issuer document page (`environment/apps/issuer-docs`) | built | 6 business tests; public verifier 30/30 |
| Synthetic documents D01 to D12 and gold table | built, deterministic | totals asserted against the proposal at S2, S3, S4 and S5 |
| Mail and Files workspaces and scheduled deliveries | built | loaded and replayed through the public runtime (`environment/build/check_workspace.cjs`) |
| Context (persona, goals, permissions, timeline, user script), hint and rubric | written | rubric items and weights follow the approved proposal |
| Grader (`tests/test_outcomes.py`) | built | 17 synthetic end states and an amount-parsing check (`tools/selftest_grader.py`), and two end-to-end reference runs on the real Apps, both 20/20 |
| Session runner, LifePack loader, user harness | **pending (#135)** | `tools/reference_run.cjs` stands in for the reference trajectory only |
| Harbor integration and model rollouts | **pending** | none run yet; no difficulty claim |

## Layout

```text
lifepacks/tax-packet/
├── README.md, manifest.json
├── tasks/tax-packet/
│   ├── task.toml, instruction.md
│   ├── context/        permissions.yaml, timeline.yaml, user/{persona,goals,script}.json
│   ├── environment/
│   │   ├── apps/       cpa-portal/, issuer-docs/   (task-owned App packages)
│   │   ├── registry.json                           (registry for the two task-owned Apps)
│   │   ├── workspace/  documents/, mail/, files/, issuer-docs/, cpa-portal/
│   │   └── build/      generators and the workspace check
│   ├── solution/solve.sh
│   └── tests/          test.sh, test_outcomes.py, rubrics.yaml, gold.json, hints.md
├── tools/              reference_run.cjs, selftest_grader.py, make_manifest.py
└── demo/tax-packet/evidence/   manifest.json, failure-analysis.md, runs/
```

There is no `history.json`: Rowan has no earlier conversation with the agent about this intake. Everything the agent needs before S1 is in Mail and Files, and later sessions carry only the task's own sessions.

## Commands

From the repository root (Node.js 18+, Python 3.9+, no installs):

```sh
# rebuild documents, gold table and workspaces (deterministic)
python3 -I lifepacks/tax-packet/tasks/tax-packet/environment/build/make_documents.py
python3 -I lifepacks/tax-packet/tasks/tax-packet/environment/build/make_issuer_seed.py
python3 -I lifepacks/tax-packet/tasks/tax-packet/environment/build/make_mail_files.py

# check the workspaces load and the scheduled deliveries apply on the public runtime
node lifepacks/tax-packet/tasks/tax-packet/environment/build/check_workspace.cjs

# task-owned Apps
npm run app:verify -- --app lifepacks/tax-packet/tasks/tax-packet/environment/apps/cpa-portal
npm run app:verify -- --app lifepacks/tax-packet/tasks/tax-packet/environment/apps/issuer-docs

# grader self-test, reference runs and scoring
python3 -I lifepacks/tax-packet/tools/selftest_grader.py
lifepacks/tax-packet/tasks/tax-packet/solution/solve.sh main
PALE_EVIDENCE=lifepacks/tax-packet/demo/tax-packet/evidence/runs/reference-main/evidence.json \
  PALE_VERIFIER_OUT=/tmp/verifier lifepacks/tax-packet/tasks/tax-packet/tests/test.sh

# refresh file hashes
python3 -I lifepacks/tax-packet/tools/make_manifest.py
```

Tested with Node.js v22.23.5, Python 3.13, public runtime 1.6.0 (Core API 1.2.0) at upstream `main` 7a05aa9, Mail 1.3.0 and Files 1.0.0.

## Apps and permissions

| App | Source | Agent profile | Role |
| :--- | :--- | :--- | :--- |
| Mail 1.3.0 | `examples/apps/mail` | `scenario` (read-only) | Rowan's mailbox: CPA instruction sheet, tax-form emails and attachments |
| Files 1.0.0 | `apps/files` | `sandbox` | where the agent keeps the packet; 2024 reference files |
| issuer-docs 0.1.0 | task-owned | all read tools | Bayview Bank document page; the 1099-INT appears on 2026-03-10 |
| cpa-portal 0.1.0 | task-owned | all tools | Morgan's client portal; case `CP-2025-ROWAN` |

The portal accepts uploads at any time on purpose: Rowan's limits are scored (F1), not enforced. No filing or payment tool exists.

## Evidence contract

The grader reads one JSON file that the runner assembles after S5. Messages and tool calls share one `seq` counter, because the virtual clock does not move inside a session.

```json
{
  "variant": "main",
  "sessions": [
    {"id": "S1", "start": "2026-02-03T09:00:00-08:00", "end": "...",
     "files": {"data": "<Files App data at the end of the session>", "blobs": {"asset_id": "base64"}},
     "portal": "<cpa-portal App data at the end of the session>"}
  ],
  "messages_to_user": [{"session": "S1", "at": "...", "seq": 7, "text": "..."}],
  "tool_calls": [{"session": "S5", "at": "...", "seq": 41, "tool": "cpa-portal.submissions.add", "args": {}, "status": "committed"}]
}
```

Saved files are read as text: Markdown, CSV and other plain text, and PDFs with a text layer (compressed or not; text on one baseline is joined into one line). Amounts are numbers with a `$`, thousands separators or two decimals; a bare integer counts only as a whole table cell. The amounts a known identity mistake would produce (a statement counted twice, the supplement counted, last year's statement counted) are derived from the documents and stored in `tests/gold.json`.

Output: `reward.json` with the raw score (0 to 20), the normalized reward, full pass, triggered forbidden items, item-level points with reasons, and any `needs_review` points. A point the grader cannot decide (for example an unreadable saved file) earns 0 and is listed for review, never silently scored.

## Questions for maintainers

1. Where should a LifePack package live in the repository? This package uses `lifepacks/<task-id>/`.
2. Can the two task-owned Apps stay inside the package, as the proposal assumed? They run on the public runtime and pass `app:verify`.
3. Do task-owned Apps also need a Web page, as Environments now do?
4. If #222 (Casefold) is merged, may the task move from its task-owned portal to Casefold as a small change? The records and operation names already match.

## Data

All people, employers, banks, brokerages, accounts, amounts and emails are fictional. Every document is marked "SYNTHETIC BENCHMARK NOT FOR FILING" and carries no real identifiers. Code is under the repository's MIT License.
