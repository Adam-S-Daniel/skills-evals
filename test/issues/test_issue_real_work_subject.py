"""Subject-agnostic real-work fixtures: the subject named at run time, the
`draft:` key, and the answer-leak lint with its `interface_strings:`
exemption list.

Owner decision Q4 (Adam, 2026-10-06, "Subject-agnostic"): a real-work
fixture runs under whichever skill or guidance treatment the run names, so it
is not copied once per subject. Offline: no network, no CLI, no agent call;
every run here is `--arm objective-only` or is refused before any arm starts.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "harness"))
import answer_leak  # noqa: E402
import guidance  # noqa: E402
import run_eval  # noqa: E402

BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
HIDDEN_TEST = ("import unittest\n\nimport calc\n\n\n"
               "class CalcTests(unittest.TestCase):\n"
               "    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n")
ADD = "test_calc.CalcTests.test_add"


class _Fixture(unittest.TestCase):
    """A subject-agnostic toy fixture under `<root>/evals/real-work/toy-1/`."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="real-work-subject-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.fixture_dir = self.root / "evals" / "real-work" / "toy-1"
        (self.fixture_dir / "seed").mkdir(parents=True)
        (self.fixture_dir / "seed" / "calc.py").write_text(BUGGY, encoding="utf-8")
        (self.fixture_dir / "checker").mkdir()
        (self.fixture_dir / "checker" / "test_calc.py").write_text(
            HIDDEN_TEST, encoding="utf-8")
        # Every network-namespace probe off, so a run reads the same on any host.
        patcher = mock.patch("scorers.commands._network_prefix", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_fixture(self, **changes):
        fixture = {"subject": "any", "draft": True, "prompt": "Fix add().",
                   "objective_checks": [{
                       "id": "hidden-tests", "type": "repo_tests",
                       "overlay": "checker",
                       "argv": ["python3", "-m", "unittest"],
                       "fail_to_pass": [ADD]}]}
        fixture.update(changes)
        fixture = {key: value for key, value in fixture.items() if value is not None}
        (self.fixture_dir / "fixture.yaml").write_text(
            yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8")

    def fixed_workspace(self) -> Path:
        workspace = self.root / "fixed"
        shutil.copytree(self.fixture_dir / "seed", workspace)
        (workspace / "calc.py").write_text(FIXED, encoding="utf-8")
        return workspace

    def main(self, *argv, eval_dir=None):
        out = io.StringIO()
        args = ["run_eval.py", str(eval_dir or self.fixture_dir),
                "--results-dir", str(self.root / "results"), *map(str, argv)]
        with mock.patch.object(sys, "argv", args), contextlib.redirect_stdout(out):
            code = run_eval.main()
        return code, out.getvalue()


class SubjectAtRunTimeTests(_Fixture):
    def test_objective_only_scores_a_subject_agnostic_fixture_red_then_green(self):
        self.write_fixture()
        code, out = self.main("--arm", "objective-only")
        self.assertEqual(code, 1, out)
        report = json.loads(out)
        self.assertEqual(report["subject"], "any")
        self.assertIn("fail_to_pass=0/1", report["checks"][0]["detail"])
        code, out = self.main("--arm", "objective-only",
                              "--workspace", self.fixed_workspace())
        self.assertEqual(code, 0, out)
        self.assertIn("fail_to_pass=1/1", json.loads(out)["checks"][0]["detail"])
        self.assertFalse((self.root / "results").exists(),
                         "objective-only writes no results")

    def test_skill_flag_runs_it_as_that_skill(self):
        self.write_fixture()
        code, out = self.main("--arm", "objective-only", "--skill", "toy-skill")
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out)["skill"], "toy-skill")
        # Found by discovery under evals/real-work/, it is named after its own
        # directory rather than refused for not sitting under evals/toy-skill/.
        code, out = self.main("--arm", "objective-only", "--skill", "toy-skill",
                              eval_dir=self.fixture_dir.parent)
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out)["skill"], "toy-skill")

    def test_apply_runtime_subject_maps_each_flag(self):
        path = Path("fixture.yaml")
        base = {"subject": "any", "prompt": "p"}
        as_skill = run_eval.apply_runtime_subject(base, "toy", None, "with_skill", path)
        self.assertEqual((as_skill["subject"], as_skill["skill"]), ("skill", "toy"))
        as_guidance = run_eval.apply_runtime_subject(base, None, "security", "both", path)
        self.assertEqual((as_guidance["subject"], as_guidance["section"]),
                         ("guidance", "security"))
        self.assertEqual(base, {"subject": "any", "prompt": "p"}, "input not mutated")
        self.assertIs(run_eval.apply_runtime_subject(base, None, None, "objective-only", path),
                      base)

    def test_refusals_are_configuration_errors(self):
        path = Path("fixture.yaml")
        cases = [
            ({"subject": "any"}, "toy", "security", "both", "both --skill and --section"),
            ({"subject": "any"}, None, None, "with_skill", "names no subject"),
            ({"subject": "any", "skill": "x"}, "toy", None, "with_skill", "names no `skill:`"),
            ({"subject": "any", "section": "x"}, None, "s", "both", "names no `skill:`"),
            ({"skill": "x"}, "toy", None, "with_skill", "fixes its subject"),
            ({"subject": "guidance", "section": "s"}, None, "t", "both", "fixes its subject"),
            ({"subject": "any"}, "", None, "with_skill", "nonblank"),
            ({"subject": "any"}, None, " ", "both", "nonblank"),
        ]
        for fixture, skill, section, arm, message in cases:
            with self.subTest(fixture=fixture, skill=skill, section=section):
                with self.assertRaises(guidance.GuidanceError) as caught:
                    run_eval.apply_runtime_subject(fixture, skill, section, arm, path)
                self.assertIn(message, str(caught.exception))

    def test_an_agent_arm_without_a_subject_is_refused_before_any_arm(self):
        self.write_fixture(draft=None)
        code, out = self.main("--arm", "with_skill")
        self.assertEqual(code, 2, out)
        self.assertIn("names no subject", out)

    def test_a_fixed_subject_fixture_refuses_the_flag(self):
        self.write_fixture(subject=None, skill="toy-skill")
        code, out = self.main("--arm", "objective-only", "--skill", "other")
        self.assertEqual(code, 2, out)
        self.assertIn("fixes its subject", out)


class DraftTests(_Fixture):
    def test_a_draft_runs_objective_only_but_no_agent_arm(self):
        self.write_fixture()
        code, out = self.main("--arm", "objective-only")
        self.assertEqual(code, 1, out)  # scored, red: not refused
        code, out = self.main("--arm", "with_skill", "--skill", "toy-skill")
        self.assertEqual(code, 2, out)
        self.assertIn("draft: true", out)

    def test_check_draft(self):
        path = Path("fixture.yaml")
        run_eval.check_draft({"draft": True}, "objective-only", False, path)
        run_eval.check_draft({"draft": True}, "with_skill", True, path)
        run_eval.check_draft({"draft": False}, "with_skill", False, path)
        run_eval.check_draft({}, "both", False, path)
        with self.assertRaisesRegex(guidance.GuidanceError, "draft: true"):
            run_eval.check_draft({"draft": True}, "both", False, path)
        for bad in ("yes", 1, None, []):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    guidance.GuidanceError, "true or false"):
                run_eval.check_draft({"draft": bad}, "objective-only", False, path)

    def test_eval_workflows_never_pass_allow_draft(self):
        for name in ("eval.yml", "routine-eval-fire.yml"):
            text = (REPO / ".github" / "workflows" / name).read_text(encoding="utf-8")
            self.assertNotIn("--allow-draft", text, name)


class AnswerLeakTests(_Fixture):
    PATCH = ("--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n"
             "-    return a - b\n+    return a + b  # refusing to report on a partial read\n")

    def test_added_lines_skip_headers_and_context(self):
        self.assertEqual(answer_leak.added_lines(self.PATCH),
                         ["    return a + b  # refusing to report on a partial read"])

    def test_a_four_word_run_from_the_answer_is_a_leak(self):
        answer = "\n".join(answer_leak.added_lines(self.PATCH))
        self.assertEqual(answer_leak.leaked_runs("Fix add(). It must say: Return A + B!", answer),
                         [])  # three words of the answer, `+` is not a word
        self.assertEqual(
            answer_leak.leaked_runs("Print REFUSING to report on, then stop.", answer),
            ["refusing to report on"])

    def test_declared_interface_strings_are_exempt(self):
        answer = "\n".join(answer_leak.added_lines(self.PATCH))
        prompt = "The error must contain `refusing to report on a partial read`."
        self.assertEqual(len(answer_leak.leaked_runs(prompt, answer)), 4)
        self.assertEqual(answer_leak.leaked_runs(
            prompt, answer, ["refusing to report on a partial read"]), [])
        # An exemption covers its own words only, not a longer quotation.
        self.assertEqual(answer_leak.leaked_runs(
            "Write: return a b refusing to report", answer,
            ["refusing to report on a partial read"]),
            ["return a b refusing", "a b refusing to", "b refusing to report"])

    def test_interface_strings_are_validated_at_fixture_load(self):
        path = Path("fixture.yaml")
        answer_leak.validate_fixture({}, path)
        answer_leak.validate_fixture({"interface_strings": ["fetch-failed"]}, path)
        for bad in ("fetch-failed", [], [""], ["  "], [3], ["x" * 201], ["a"] * 33):
            with self.subTest(bad=bad), self.assertRaises(guidance.GuidanceError):
                answer_leak.validate_fixture({"interface_strings": bad}, path)

    def test_a_bad_list_is_refused_by_run_eval_before_scoring(self):
        self.write_fixture(interface_strings="fetch-failed")
        code, out = self.main("--arm", "objective-only")
        self.assertEqual(code, 2, out)
        self.assertIn("interface_strings", out)


if __name__ == "__main__":
    unittest.main()
