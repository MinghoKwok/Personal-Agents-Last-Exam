# PR #<n> · <App name> — review report

## Baseline
PR, author, head commit, proposal path, review date, repository revision and App versions checked against, which standard was used, whether the PR description and comments were read.

**Result:** <recommendation>. Reject <n> · Partial <n> · Approve <n> · Human judge <n>.

## Format check
One row per check (title, single proposal file, headings and labels, no leftover placeholder, primary domain).

## Workflow traces
| # | Workflow | Precondition | Action or event | Expected outcome | Failure / control | Line |

## Dependency evidence
| Workflow and needed effect | App, required or optional | Revision and interface actually opened | What was verified | Gap, owner, fallback |

State that these were static checks unless something was run.

## The 24 verdicts
| ID | Verdict | Evidence (`file:line` + quote) | Requested change | Group (A integration / B design / C implementation detail) |

## Design gaps
List any, or "none". Everything else is already grouped in the verdict table.

## The author's own open questions
| Line | Question | Answer from the platform as it is, or "needs the reviewer" |

## Reviewer's decisions (<date>)
One line per decision, in the reviewer's words, with what it changed. Write "none yet" before any answer arrives.

## Human checklist
| Item | Suggestion (tick / hold / reviewer decides) | Reason |

## Not verified
What was not run or not read.
