"""The sitelint command line's contract: exit codes and output shapes."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sitelint(*args):
    return subprocess.run([sys.executable, "-m", "sitelint", *args],
                          cwd=ROOT, capture_output=True, text=True, check=False)


class CommandLineTests(unittest.TestCase):
    def test_clean_page_exits_zero(self):
        result = sitelint("pages/docs.html")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_findings_exit_one_with_path_and_line(self):
        result = sitelint("pages/contact.html")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.strip(),
                         "pages/contact.html:10: inline-style: inline style attribute")

    def test_json_output_is_a_list_of_findings(self):
        result = sitelint("--json", "pages/home.html")
        self.assertEqual(result.returncode, 1)
        findings = json.loads(result.stdout)
        self.assertEqual([sorted(f) for f in findings], [["line", "message", "path", "rule"]])
        self.assertEqual(findings[0]["rule"], "banned-phrase")

    def test_unreadable_page_exits_two(self):
        result = sitelint("pages/missing.html")
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot read pages/missing.html", result.stderr)


if __name__ == "__main__":
    unittest.main()
