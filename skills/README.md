# Agent skills

Agent skills for Personal Agents' Last Exam, grouped into three categories. Each category is a Claude Code and Codex plugin, so you install only the categories you need, and every skill name carries its category, for example `pale-env:<skill>`.

| Category | Folder | Plugin | What goes here |
| :--- | :--- | :--- | :--- |
| Environment | `skills/env/` | `pale-env` | Skills for the Environment Track: designing, building, testing and reviewing App environments |
| Task | `skills/task/` | `pale-task` | Skills for the Task Track: personas and histories, scenario scripts, rubrics, rollouts and review |
| General | `skills/general/` | `pale-general` | Skills that serve both tracks |

## Skills

| Skill | Category | What it does |
| :--- | :--- | :--- |
| `pale-env:env-proposal-review` | Environment | Turns an environment proposal review into feedback the author can act on: runs the agent checklist, lists what the human reviewer still has to decide, applies the reviewer's answers and writes the author feedback, with a script that checks cited lines and quotations. |
| `pale-task:task-proposal` | Task | Drafts, completes or upgrades a Task Track proposal. It writes a draft from the contributor's story or old proposal, asks for the details that are usually missing, and runs an advisory checker against the task template. It does not block submission. |

The General category is ready for skills.


## Layout

```text
.claude-plugin/marketplace.json      # Lists the three categories; Claude Code reads it from the repository root
skills/
├── README.md                        # This file
├── env/
│   ├── .claude-plugin/plugin.json   # Claude Code plugin manifest
│   ├── .codex-plugin/plugin.json    # Codex plugin manifest
│   └── skills/
│       └── <skill-name>/
│           ├── SKILL.md             # Required: front matter and instructions
│           ├── references/          # Optional: longer documents the skill reads when needed
│           └── scripts/             # Optional: scripts the skill runs
├── task/                            # Same layout
└── general/                         # Same layout
```

## Install

Claude Code:

```sh
claude plugin marketplace add MatrAIx-ai/Personal-Agents-Last-Exam --sparse .claude-plugin skills
claude plugin install pale-env@pale        # or pale-task@pale, pale-general@pale
```

Inside a session, use `/plugin marketplace add …` and `/plugin install …` with the same arguments.

Codex:

```sh
codex plugin marketplace add MatrAIx-ai/Personal-Agents-Last-Exam --sparse .claude-plugin --sparse skills
codex plugin add pale-env@pale             # or pale-task@pale, pale-general@pale
```

Both tools also accept the path of a local clone in place of `MatrAIx-ai/Personal-Agents-Last-Exam`. Installed skills carry their category in both tools, for example `pale-env:<skill>`.

## Add a skill

1. **Choose the category by when the skill is used.** Building or reviewing an environment goes in `env`; writing or validating a task goes in `task`; work that serves both tracks goes in `general`.
2. **Create the folder.** Add `skills/<category>/skills/<skill-name>/SKILL.md`. The folder name is the skill name: lowercase words joined by hyphens, such as `env-proposal-review`.
3. **Start `SKILL.md` with front matter.**

   ```markdown
   ---
   name: <skill-name>
   description: <what the skill does and when to use it, in one or two sentences>
   ---
   ```

   Agents decide whether to load a skill from its description, so state when to use it.
4. **Keep the skill self-contained.** Put everything it needs in its own `references/` and `scripts/` folders. Do not point to files in other skills or categories, and do not hard-code personal paths, hosts or credentials.
5. **Bump the version.** Raise `version` in the category's two plugin manifests and in its entry in `.claude-plugin/marketplace.json`. Codex keeps installed plugins in a cache folder named by version, so an unchanged version can hide your edits.
6. **Validate before opening the PR.** Run `claude plugin validate .` from the repository root and `claude plugin validate skills/<category>`. For Codex, add your clone with `codex plugin marketplace add <clone path>`, install the category with `codex plugin add pale-<category>@pale`, and check that `codex debug prompt-input` lists the skill.
