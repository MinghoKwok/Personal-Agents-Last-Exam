"""Tests for skills/env/skills/env-proposal-review/scripts/check_feedback.py."""
import subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/env/skills/env-proposal-review/scripts/check_feedback.py"

PROPOSAL = textwrap.dedent("""\
    # Environment Track proposal

    - **Operations and access (required):** Agent-facing MCP tools: `orders.list`, `orders.cancel`.
    - **Shared data and dependencies (required):** Depends on the shared Mail app.

    Reset restores the seed.
    """)

GOOD = textwrap.dedent("""\
    ## Review feedback: Demo (PR #1)

    **Recommendation:** Ready for scope approval once the items below are addressed

    **Reviewed:** `proposals/environment/demo.md` @ `abc1234`

    ### Problems to resolve (1 items)

    1. **Mail interface is not pinned**
       - Current: Line 4 says "Depends on the shared Mail app".
       - Problem: The file and version are not given.
       - Change: Link the receive schema and state the version.
    """)


def run(feedback, *flags):
    with tempfile.TemporaryDirectory() as d:
        fb, pr = Path(d, "fb.md"), Path(d, "proposal.md")
        fb.write_text(feedback, encoding="utf-8"); pr.write_text(PROPOSAL, encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), *flags, str(fb), str(pr)], capture_output=True, text=True)
        return r.returncode, r.stdout


class CheckFeedback(unittest.TestCase):
    def test_clean_feedback_passes(self):
        code, out = run(GOOD)
        self.assertEqual(code, 0, out)

    def test_missing_line_is_reported(self):
        code, out = run(GOOD.replace("Line 4", "Line 40"))
        self.assertEqual(code, 1); self.assertIn("line 40", out)

    def test_quote_not_in_proposal_is_reported(self):
        code, out = run(GOOD.replace("Depends on the shared Mail app", "Requires the Files app"))
        self.assertEqual(code, 1); self.assertIn("not found", out)

    def test_quote_on_wrong_line_is_reported(self):
        code, out = run(GOOD.replace("Line 4", "Line 6"))
        self.assertEqual(code, 1); self.assertIn("not on any line cited", out)

    def test_item_count_mismatch_is_reported(self):
        code, out = run(GOOD.replace("(1 items)", "(3 items)"))
        self.assertEqual(code, 1); self.assertIn("header says 3", out)

    def test_placeholder_is_reported(self):
        code, out = run(GOOD.replace("Demo (PR #1)", "<App name> (PR #1)"))
        self.assertEqual(code, 1); self.assertIn("placeholder", out)

    def test_filler_wording_is_reported(self):
        code, out = run(GOOD + "\n- The missing owner is not a blocker.\n")
        self.assertEqual(code, 1); self.assertIn("fine instead of something to do", out)

    def test_report_mode_skips_author_only_checks(self):
        code, out = run(GOOD.replace("(1 items)", "(3 items)") + "\n- not a blocker\n", "--report")
        self.assertEqual(code, 0, out)

    def test_chinese_citation_and_quote(self):
        zh = GOOD.replace('Line 4 says "Depends on the shared Mail app".', '第 4 行写"Depends on the shared Mail app"。').replace("(1 items)", "（共 1 条）")
        code, out = run(zh)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
