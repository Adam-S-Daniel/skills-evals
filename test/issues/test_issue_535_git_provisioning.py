#!/usr/bin/env python3
"""#535, first stage: Git 2.54 where arms run, and the `fleet_hooks` opt-in.

ADR 0012's fleet hooks addendum (2026-11-02) runs the fleet hook runner in
arms that stand for the real setup, installed as config-based Git hooks,
which need Git 2.54 or later (adam-agentskills ADR 0020). This stage builds
no hooks. It pins:

  * `fleet_hooks:` is the literal `true` or `false` in fixture.yaml
    (context._check_fleet_hooks), and is part of `fixture_digest`;
  * run_eval reads `git --version` once per run and records it in every
    summary as `harness.git_version`, which ingest accepts (optional, so an
    older summary still ingests) and checks;
  * run_eval refuses a `fleet_hooks: true` fixture on an older Git with
    `git_too_old_for_fleet_hooks`, exit 2, before any CLI call;
  * the weekly planner holds such a fixture ("git too old for fleet hooks").

The Git version is stubbed through `run_eval.git_version` or a stubbed
`subprocess.run`; the host's Git is never changed. No network, no clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "test" / "issues"))

import context  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import plan_week  # noqa: E402
import run_eval  # noqa: E402
from test_issue_routine_eval_ingest import STAMP, summary  # noqa: E402

OLD = "git version 2.43.0"
NEW = "git version 2.56.0"


def completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["git", "--version"], returncode, stdout, "")


class FleetHooksKeyTests(unittest.TestCase):
    def load(self, text: str) -> dict:
        return context.load_fixture_yaml(text.encode(), "fixture.yaml")

    def test_the_literal_booleans_load(self):
        self.assertIs(self.load("prompt: p\nfleet_hooks: true\n")["fleet_hooks"], True)
        self.assertIs(self.load("prompt: p\nfleet_hooks: false\n")["fleet_hooks"], False)
        self.assertNotIn("fleet_hooks", self.load("prompt: p\n"))

    def test_anything_else_is_refused(self):
        for value in ("yes", "on", "True", "TRUE", "'true'", '"false"', "1", "0",
                      "", "null", "[true]", "{a: true}"):
            with self.subTest(value=value), self.assertRaises(context.ContextError) as caught:
                self.load(f"prompt: p\nfleet_hooks: {value}\n")
            self.assertEqual(caught.exception.code, "invalid_fixture")
            self.assertIn("fleet_hooks", str(caught.exception))

    def test_only_the_top_level_key_is_held_to_it(self):
        self.assertEqual(self.load("env: {fleet_hooks: 'x'}\n")["env"], {"fleet_hooks": "x"})

    def test_run_eval_load_fixture_refuses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "fixture.yaml").write_text("prompt: p\nfleet_hooks: yes\n",
                                                    encoding="utf-8")
            with self.assertRaises(context.ContextError):
                run_eval.load_fixture(Path(tmp))

    def test_the_key_is_part_of_the_fixture_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            fixture = repo / "evals" / "s" / "f"
            fixture.mkdir(parents=True)
            (fixture / "fixture.yaml").write_text("prompt: p\n", encoding="utf-8")
            env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
                   "PATH": "/usr/bin:/bin"}
            subprocess.run(["git", "init", "-q", str(repo)], env=env, check=True)
            subprocess.run(["git", "-C", str(repo), "add", "."], env=env, check=True)
            before = run_eval.fixture_digest(fixture)
            (fixture / "fixture.yaml").write_text("prompt: p\nfleet_hooks: true\n",
                                                  encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], env=env, check=True)
            after = run_eval.fixture_digest(fixture)
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertNotEqual(before, after)


class GitVersionTests(unittest.TestCase):
    def test_reads_the_first_line_of_git_version(self):
        with mock.patch.object(run_eval.subprocess, "run",
                               return_value=completed(NEW + "\nextra\n")) as spawn:
            self.assertEqual(run_eval.git_version(), NEW)
        argv = spawn.call_args.args[0]
        self.assertEqual(argv, ["git", "--version"])
        env = spawn.call_args.kwargs["env"]
        self.assertFalse([k for k in env if k.startswith("GIT_") and k not in (
            "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL")])

    def test_caller_git_variables_never_reach_it(self):
        with mock.patch.dict("os.environ", {"GIT_DIR": "/elsewhere",
                                            "GIT_CONFIG_COUNT": "1"}), \
                mock.patch.object(run_eval.subprocess, "run",
                                  return_value=completed(NEW)) as spawn:
            run_eval.git_version()
        env = spawn.call_args.kwargs["env"]
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GIT_CONFIG_COUNT", env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")

    def test_unreadable_is_null_never_a_crash(self):
        for outcome in (completed("", 0), completed(NEW, 1),
                        FileNotFoundError("git")):
            with self.subTest(outcome=repr(outcome)), \
                    contextlib.redirect_stderr(io.StringIO()) as err, \
                    mock.patch.object(run_eval.subprocess, "run",
                                      side_effect=[outcome]):
                self.assertIsNone(run_eval.git_version())
            self.assertIn("could not read the Git version", err.getvalue())

    def test_the_minimum_is_2_54(self):
        cases = {"git version 2.54.0": True, "git version 2.54": True,
                 "git version 2.55.0.windows.1": True, NEW: True,
                 "git version 3.0.0": True, "git version 2.39.3 (Apple Git-146)": False,
                 OLD: False, "git version 2.53.9": False, "git version 2.5": False,
                 "git version 2.540": True, None: False, "": False, "2.56.0": False}
        for version, supported in cases.items():
            with self.subTest(version=version):
                self.assertIs(run_eval.git_supports_fleet_hooks(version), supported)

    def test_refusal_only_for_an_opted_in_fixture_on_old_git(self):
        self.assertIsNone(run_eval.fleet_hooks_refusal({}, OLD))
        self.assertIsNone(run_eval.fleet_hooks_refusal({"fleet_hooks": False}, OLD))
        self.assertIsNone(run_eval.fleet_hooks_refusal({"fleet_hooks": True}, NEW))
        for version in (OLD, None):
            with self.subTest(version=version):
                reason = run_eval.fleet_hooks_refusal({"fleet_hooks": True}, version)
                self.assertIn("2.54", reason)
                self.assertIn(version or "unreadable", reason)


class MainTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="fleet-hooks-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.fixture = self.root / "evals" / "demo"
        (self.fixture / "seed").mkdir(parents=True)

    def write(self, **doc):
        (self.fixture / "fixture.yaml").write_text(
            yaml.safe_dump({"skill": "demo", "prompt": "p", **doc}), encoding="utf-8")

    def main(self, version: str | None, *flags: str) -> tuple[int, str]:
        out = io.StringIO()
        # Every way an arm could start spending refuses loudly instead.
        with mock.patch.object(run_eval, "git_version", return_value=version), \
                mock.patch.object(run_eval, "managed_sandbox_refusal", return_value=None), \
                mock.patch.object(run_eval, "claude_version",
                                  side_effect=AssertionError("CLI started")), \
                mock.patch.object(run_eval, "run_agent",
                                  side_effect=AssertionError("agent started")), \
                mock.patch.object(sys, "argv", ["run_eval.py", str(self.fixture),
                                                "--results-dir", str(self.root / "results"),
                                                *flags]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = run_eval.main()
        return rc, out.getvalue()

    def test_an_opted_in_fixture_on_old_git_is_refused_before_any_call(self):
        self.write(fleet_hooks=True)
        for version in (OLD, None):
            with self.subTest(version=version):
                rc, out = self.main(version, "--arm", "both")
                self.assertEqual(rc, 2)
                self.assertTrue(out.startswith("git_too_old_for_fleet_hooks: "), out)
                self.assertFalse((self.root / "results").exists())

    def test_no_refusal_without_the_opt_in_or_on_new_git_or_objective_only(self):
        for doc, version, flags in (({}, OLD, ("--arm", "both")),
                                    ({"fleet_hooks": False}, OLD, ("--arm", "both")),
                                    ({"fleet_hooks": True}, NEW, ("--arm", "both")),
                                    ({"fleet_hooks": True}, OLD, ())):
            with self.subTest(doc=doc, version=version, flags=flags):
                self.write(**doc)
                try:
                    _rc, out = self.main(version, *flags)
                except AssertionError:
                    out = ""  # it got past the refusal, to the CLI
                self.assertNotIn("git_too_old_for_fleet_hooks", out)

    def test_the_version_main_reads_lands_in_the_summary(self):
        # A malformed `judge:` writes one summary per arm before any call
        # (#81's invalid_judge_block), through the same _write_summary.
        self.write(judge=[1])
        rc, out = self.main(NEW, "--arm", "both", "--timestamp", STAMP)
        self.assertEqual(rc, 2, out)
        written = sorted((self.root / "results").rglob("summary.json"))
        self.assertTrue(written)
        for path in written:
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(doc["harness"]["git_version"], NEW)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="git-version-summary-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.addCleanup(run_eval._TELEMETRY.begin)

    def write(self) -> dict:
        run_eval._write_summary(self.tmp, "s", "with_skill", STAMP, None, None, None,
                                None, None)
        return json.loads((self.tmp / "s" / STAMP / "with_skill" / "summary.json")
                          .read_text(encoding="utf-8"))

    def test_every_summary_records_the_run_git_version(self):
        run_eval._TELEMETRY.begin()
        self.assertIsNone(self.write()["harness"]["git_version"])
        run_eval._TELEMETRY.git_version = NEW
        self.assertEqual(self.write()["harness"]["git_version"], NEW)


class IngestTests(unittest.TestCase):
    PARTS = ingest.parse_result_path(f"writing-adrs/{STAMP}/bootstrap/with_skill/summary.json")

    def check(self, value):
        doc = summary()
        if value is not ...:
            doc["harness"]["git_version"] = value
        ingest.check_summary(doc, "x", self.PARTS)

    def test_absent_null_and_real_versions_ingest(self):
        for value in (..., None, OLD, NEW, "git version 2.55.0.windows.1",
                      "git version 2.39.3 (Apple Git-146)"):
            with self.subTest(value=value):
                self.check(value)

    def test_anything_else_is_rejected(self):
        for value in ("", "2.56.0", "git version ", "git version x", 2.56, True,
                      ["git version 2.56.0"], "git version 2.56.0`", "git version 2.56.0\n",
                      "git version 2." + "0" * 60):
            with self.subTest(value=value), \
                    self.assertRaisesRegex(ingest.Rejected, "harness.git_version"):
                self.check(value)

    def test_run_eval_versions_always_ingest(self):
        # run_eval keeps VERSION_MAX_CHARS of [A-Za-z0-9._() -]; the longest
        # such version ingests.
        longest = ("git version 2.56.0 " + "a" * 64)[:run_eval.VERSION_MAX_CHARS]
        self.check(longest)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="fleet-hooks-plan-")
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.context = {"revision": "a" * 40, "guidance_revision": "b" * 40}

    def hold(self, doc: dict, version: str | None):
        (self.dir / "fixture.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
        with mock.patch.object(run_eval, "git_version", return_value=version) as read:
            reason = plan_week.fixture_hold_reason(self.dir)
        return reason, read.call_count

    def test_an_opted_in_fixture_is_held_on_old_git(self):
        for doc in ({"skill": "s", "context": self.context, "fleet_hooks": True},
                    {"subject": "guidance", "fleet_hooks": True},
                    {"subject": "any", "fleet_hooks": True},
                    # Anything but false holds: the harness would refuse it.
                    {"subject": "guidance", "fleet_hooks": "yes"},
                    {"subject": "guidance", "fleet_hooks": None}):
            for version in (OLD, None):
                with self.subTest(doc=doc, version=version):
                    self.assertEqual(self.hold(doc, version)[0], plan_week.HOLD_GIT)

    def test_new_git_or_no_opt_in_is_not_held_and_git_is_read_only_on_opt_in(self):
        self.assertEqual(self.hold({"skill": "s", "context": self.context,
                                    "fleet_hooks": True}, NEW), (None, 1))
        self.assertEqual(self.hold({"skill": "s", "context": self.context}, OLD), (None, 0))
        self.assertEqual(self.hold({"skill": "s", "context": self.context,
                                    "fleet_hooks": False}, OLD), (None, 0))

    def test_only_the_audited_fixtures_opt_in(self):
        # The opt-in is the last stage of #535: exactly the fixtures its seed
        # audit cleared (proven pin, no seed hook or `origin`, no refusal on
        # the expected path). A new opt-in is audited and added here.
        opted = []
        for directory in plan_week.schedule.committed_fixtures(ROOT):
            path = ROOT / directory / "fixture.yaml"
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and run_eval.FLEET_HOOKS_KEY in doc:
                opted.append(str(path.relative_to(ROOT)))
        audited = sorted(f"evals/{name}/fixture.yaml" for name in (
            "admin-config-render", "embeddable-tool-pages", "finding-unknowns",
            "github-actions-sha-pinning", "post-failure-comment",
            "windows-elevation-from-wsl", "workflow-path-audit/required-check-routing",
            "writing-adrs/bootstrap",
            *(f"review-bash-ci-reliability/{n}" for n in (
                "drift-report-capture", "nightly-snapshot", "release-pipeline",
                "test-runner-assertions")),
            *(f"vendor-release-impact-issues/{n}" for n in (
                "closing-keywords", "issue-hygiene", "stamps-skip-quotes"))))
        self.assertEqual(sorted(opted), audited)


if __name__ == "__main__":
    unittest.main()
