import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/task/skills/task-proposal/scripts/check_task_proposal.py"
spec = importlib.util.spec_from_file_location("check_task_proposal", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class TaskProposalCheckTests(unittest.TestCase):
    def setUp(self):
        self.template = (ROOT / "proposals/templates/task-proposal.md").read_text()
        self.example = (ROOT / "proposals/task/lena-spring-gathering.md").read_text()

    def gaps(self, text):
        report, _ = checker.check(text, self.template)
        return [message for _, message in report.gaps]

    def test_worked_example_passes(self):
        report, title = checker.check(self.example, self.template)
        self.assertEqual(report.gaps, [])
        self.assertEqual(
            title,
            "[Task Proposal] [Food & dining + Social & communities] Arrange catering for Lena’s spring gathering",
        )

    def test_empty_template_fails(self):
        gaps = self.gaps(self.template)
        self.assertTrue(any("placeholder" in e for e in gaps))
        self.assertTrue(any("Short task title" in e for e in gaps))

    def test_older_format_reports_missing_sections(self):
        legacy = self.example.split("## 5. Rubric, hint and reference solution")[0]
        gaps = self.gaps(legacy)
        self.assertTrue(any("Rubric" in e for e in gaps))
        self.assertTrue(any("Forbidden" in e for e in gaps))

    def test_rubric_arithmetic(self):
        low_mark = self.example.replace("at least 16 of 20", "at least 10 of 20")
        self.assertTrue(any("still pass" in e for e in self.gaps(low_mark)))
        wrong_total = self.example.replace("**✍️ Expected (required):** 20 points.", "**✍️ Expected (required):** 25 points.")
        self.assertTrue(any("add up to 20" in e for e in self.gaps(wrong_total)))

    def test_rubric_items_need_evidence_and_reference_coverage(self):
        no_evidence = self.example.replace("*Evidence:* Cedar Table’s update (Apr 16). *Checked from:* messages", "*Checked from:* messages")
        self.assertTrue(any("E4 has no" in e for e in self.gaps(no_evidence)))
        uncovered = self.example.replace("| E3, E4 |", "| E3 |")
        self.assertTrue(any("cites E4" in e for e in self.gaps(uncovered)))

    def test_domains_insight_and_timestamps(self):
        bad_domain = self.example.replace("- **Primary domain (required):** Food & dining", "- **Primary domain (required):** Catering")
        self.assertTrue(any("primary domain" in e for e in self.gaps(bad_domain)))
        long_insight = self.example.replace("- **Personalization insight (required):** ", "- **Personalization insight (required):** " + "x" * 240)
        self.assertTrue(any("limit is 240" in e for e in self.gaps(long_insight)))
        no_offset = self.example.replace("`2026-04-08T09:05:00-04:00`", "`2026-04-08T09:05:00`", 1)
        self.assertTrue(any("no UTC offset" in e for e in self.gaps(no_offset)))

    def test_hint_warnings(self):
        leaky = self.example.replace("re-read these records:", "switch to the $236 menu and re-read these records:")
        report, _ = checker.check(leaky, self.template)
        notes = " ".join(message for _, message in report.notes)
        self.assertIn("amount", notes)
        self.assertIn("switch", notes)

    def test_gaps_do_not_block_unless_strict(self):
        template = str(ROOT / "proposals/templates/task-proposal.md")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(checker.main([template]), 0)
            self.assertEqual(checker.main([template, "--strict"]), 1)
        self.assertIn("do not block submission", output.getvalue())


if __name__ == "__main__":
    unittest.main()
