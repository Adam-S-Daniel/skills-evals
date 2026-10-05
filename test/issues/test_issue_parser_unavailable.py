#!/usr/bin/env python3
"""A missing Bash parser is a scorer error, never an agent failure (#88).

`shell_staged_tool_guard` needs the pinned Tree-sitter wheels. A local run in
a python without them used to score every trial's check as FAILED, the same
as an agent that wrote a bad hook. These tests drive `run_eval.py` as a
subprocess with a `tree_sitter` package on PYTHONPATH whose import raises, so
no real wheel is removed, and with the scripted CLI from test_issue_66.

Discovered and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_parser_unavailable.py`.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_issue_66 import (HARNESS_DIR, TS, _HarnessCase, _child_env,  # noqa: E402
                           _write_fixture)

sys.path.insert(0, str(HARNESS_DIR))
import run_eval  # noqa: E402
from scorers import bash_ast  # noqa: E402

SKILL = "parser-skill"
CHECKS = [
    {"id": "readme-kept", "type": "file_count", "paths": ["README.md"],
     "min": 1, "max": 1},
    {"id": "guard", "type": "shell_staged_tool_guard", "paths": ["hook.sh"],
     "tools": ["gofmt"]},
]


class _ParserCase(_HarnessCase):
    def setUp(self):
        super().setUp()
        self.fixture_dir = _write_fixture(self.evals / SKILL, SKILL,
                                          objective_checks=CHECKS)
        self.arm_dir = self.results / SKILL / TS / "without_skill"
        blocker = self.tmp / "no-parser" / "tree_sitter"
        blocker.mkdir(parents=True)
        (blocker / "__init__.py").write_text(
            "raise ImportError('deliberately absent')\n", encoding="utf-8")
        self.blocker = str(blocker.parent)

    def _run_blocked(self, *flags: str):
        # _HarnessCase._run builds the child environment itself, so the
        # blocker rides in through a wrapper that adds PYTHONPATH.
        original = _child_env

        def with_blocker(tmp, **extra):
            return original(tmp, PYTHONPATH=self.blocker, **extra)

        import test_issue_66
        test_issue_66._child_env = with_blocker
        try:
            return self._run(self.fixture_dir, *flags)
        finally:
            test_issue_66._child_env = original

    def _summary(self, *parts: str) -> dict:
        return json.loads(self.arm_dir.joinpath(*parts).read_text(encoding="utf-8"))


class TestParserUnavailable(_ParserCase):
    def test_trials_are_errors_not_failed_checks(self):
        self._script(agents=[{"write": "hook.sh"}] * 3)
        proc = self._run_blocked("--arm", "without_skill", "--trials", "3",
                                 "--timestamp", TS, "--no-judge")
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        summary = self._summary("summary.json")
        self.assertEqual((summary["n"], summary["errors"], summary["scored"]),
                         (3, 3, 0))
        self.assertEqual([e["type"] for e in summary["trial_errors"]],
                         ["scorer_unavailable"] * 3)
        for entry in summary["trial_errors"]:
            self.assertIn("tree-sitter==0.26.0", entry["detail"])
            self.assertIn("tree-sitter-bash==0.25.1", entry["detail"])
        # No check is scored, so none can be a failed one.
        self.assertIsNone(summary["aggregate"]["objective"])
        for k in (1, 2, 3):
            trial = self._summary(f"{run_eval.TRIAL_DIR_PREFIX}{k}", "summary.json")
            self.assertEqual(trial["error"]["type"], "scorer_unavailable")
            self.assertIsNone(trial["objective_checks"])
        self.assertEqual(self._calls("judges"), [])

    def test_objective_only_names_the_missing_parser(self):
        workspace = self.tmp / "ws"
        workspace.mkdir()
        (workspace / "README.md").write_text("# seed\n", encoding="utf-8")
        (workspace / "hook.sh").write_text("gofmt -w x\n", encoding="utf-8")
        proc = self._run_blocked("--arm", "objective-only",
                                 "--workspace", str(workspace))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("scorer_unavailable", proc.stdout)
        self.assertIn("tree-sitter-bash==0.25.1", proc.stdout)
        self.assertNotIn("Traceback", proc.stderr)

    @unittest.skipUnless(bash_ast.parser_importable(),
                         "the pinned parser is not installed here")
    def test_parser_present_scores_the_check_as_before(self):
        self._script(agents=[{"write": "hook.sh"}] * 2)
        proc = self._run(self.fixture_dir, "--arm", "without_skill",
                         "--trials", "2", "--timestamp", TS, "--no-judge")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        summary = self._summary("summary.json")
        self.assertEqual((summary["n"], summary["errors"], summary["scored"]),
                         (2, 0, 2))
        checks = {c["id"]: c for c in summary["aggregate"]["objective"]["checks"]}
        self.assertEqual((checks["guard"]["n"], checks["guard"]["passed"]), (2, 0))
        self.assertEqual(checks["readme-kept"]["passed"], 2)
        trial = self._summary(f"{run_eval.TRIAL_DIR_PREFIX}1", "summary.json")
        results = {c["id"]: c for c in trial["objective_checks"]}
        self.assertFalse(results["guard"]["passed"])
        self.assertTrue(results["guard"]["detail"].startswith("shell_staged_tool_guard: "))
        self.assertNotIn("parser_unavailable", results["guard"]["detail"])


class TestAggregateDenominator(unittest.TestCase):
    def test_a_scorer_error_trial_is_outside_every_check_denominator(self):
        scored = {"error": None, "agent": {"cost_usd": 0.1},
                  "objective_checks": [{"id": "guard", "passed": True}]}
        errored = {"error": {"type": "scorer_unavailable", "detail": "d"},
                   "agent": {"cost_usd": 0.1}, "objective_checks": None}
        stats = run_eval.aggregate_trials([scored, errored, scored])
        self.assertEqual((stats["n"], stats["errors"], stats["scored"]), (3, 1, 2))
        self.assertEqual(stats["trial_errors"][0]["type"], "scorer_unavailable")
        check = stats["aggregate"]["objective"]["checks"][0]
        self.assertEqual((check["n"], check["passed"], check["pass_rate"]), (2, 2, 1.0))


if __name__ == "__main__":
    unittest.main()
