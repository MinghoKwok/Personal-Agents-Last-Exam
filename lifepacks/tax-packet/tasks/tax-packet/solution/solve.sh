#!/usr/bin/env bash
# Reference solution for Task #102. Until the shared session runner (#135) exists, the reference
# trajectory is played in process on the real Apps through their Agent tool interface only:
# Mail, Files (public runtime), the task-owned CPA portal and issuer document page.
# It writes the evidence file in the grader's contract; tests/test.sh then scores it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="$(cd "$HERE/../../.." && pwd)"
VARIANT="${1:-main}"
OUT="${PALE_EVIDENCE:-$PKG/demo/tax-packet/evidence/runs/reference-$VARIANT/evidence.json}"
node "$PKG/tools/reference_run.cjs" --variant "$VARIANT" --out "$OUT"
