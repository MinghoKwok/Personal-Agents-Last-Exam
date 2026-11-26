#!/usr/bin/env bash
# Harbor verifier entry point for Task #102 (tax-packet).
# The runner assembles the evidence file described in the package README ("Evidence contract")
# and passes its path in PALE_EVIDENCE. The grader needs only Python 3 (standard library).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVIDENCE="${PALE_EVIDENCE:-/logs/agent/evidence.json}"
OUT_DIR="${PALE_VERIFIER_OUT:-/logs/verifier}"
mkdir -p "$OUT_DIR"
python3 -I "$HERE/test_outcomes.py" "$EVIDENCE" --out "$OUT_DIR/reward.json"
python3 -I -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["reward"])' "$OUT_DIR/reward.json" > "$OUT_DIR/reward.txt"
