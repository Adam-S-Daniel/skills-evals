"""ci.yml runs the private denylist scan on every pull request.

test/test_privacy_denylist_scan.py runs in the required `test` job, not in a
suite shard, because the shards skip their work when no salient path changed
and a private detail can land in any path. This locks the step's shape from
the parsed workflow: nothing gates it, its job cannot be cancelled by a
concurrency group, the pull_request trigger has no path filter, the secret
reaches it only through `env:`, and a Dependabot run (which gets no
repository secrets) skips only the private scan while every other run with
no list fails.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test"))
from prereqs import require_executable  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
STEP = "Tracked files hold nothing from the private denylist"
SCAN = "python3 test/test_privacy_denylist_scan.py"


def _doc() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers(doc: dict) -> dict:
    # PyYAML reads the bare key `on` as the boolean True.
    return doc.get("on", doc.get(True))


class ScanStepShape(unittest.TestCase):
    def setUp(self):
        self.doc = _doc()
        self.job = self.doc["jobs"]["test"]
        names = [s.get("name") for s in self.job["steps"]]
        self.assertIn(STEP, names, "the required `test` job must run the denylist scan")
        self.index = names.index(STEP)
        self.step = self.job["steps"][self.index]

    def test_the_step_and_the_steps_before_it_are_ungated(self):
        for step in self.job["steps"][: self.index + 1]:
            self.assertNotIn("if", step, f"step {step.get('name')!r} must run unconditionally")

    def test_it_runs_before_the_shard_result_check(self):
        names = [s.get("name") for s in self.job["steps"]]
        self.assertLess(self.index, names.index("Every suite shard passed"),
                        "a failed shard must not stop the scan from running")
        self.assertTrue(any(s.get("uses", "").startswith("actions/checkout@")
                            for s in self.job["steps"][: self.index]))

    def test_the_job_always_runs_and_nothing_can_cancel_it(self):
        self.assertEqual(self.job.get("if"), "always()")
        for key in ("concurrency", "timeout-minutes", "strategy"):
            self.assertNotIn(key, self.job)
        self.assertNotIn("concurrency", self.doc)

    def test_every_pull_request_triggers_the_workflow(self):
        pull_request = _triggers(self.doc)["pull_request"]
        if pull_request is not None:
            for key in ("paths", "paths-ignore", "branches", "branches-ignore", "types"):
                self.assertNotIn(key, pull_request)

    def test_the_secret_arrives_only_through_env(self):
        self.assertEqual(self.step["env"]["PRIVACY_DENYLIST"], "${{ secrets.PRIVACY_DENYLIST }}")
        self.assertNotIn("${{", self.step["run"])
        self.assertIn(SCAN, self.step["run"])


class ScanStepBehavior(unittest.TestCase):
    """The step's own script, with python3 replaced by a stub that records CI."""

    def run_step(self, denylist: str, author: str | None):
        require_executable("jq")
        script = _doc()["jobs"]["test"]["steps"]
        script = next(s for s in script if s.get("name") == STEP)["run"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "bin").mkdir()
            stub = tmp / "bin" / "python3"
            stub.write_text('#!/bin/sh\necho "scan ran with CI=$CI: $*"\n', encoding="utf-8")
            stub.chmod(0o755)
            event = tmp / "event.json"
            event.write_text(json.dumps({"pull_request": {"user": {"login": author}}}
                                        if author else {}), encoding="utf-8")
            jq = Path(subprocess.run(["sh", "-c", "command -v jq"], capture_output=True,
                                     text=True, check=True).stdout.strip())
            env = {"PATH": f"{tmp / 'bin'}:{jq.parent}:/usr/bin:/bin", "CI": "true",
                   "GITHUB_EVENT_PATH": str(event), "PRIVACY_DENYLIST": denylist}
            return subprocess.run(["bash", "-e", "-c", script], env=env, cwd=tmp,
                                  capture_output=True, text=True, timeout=30)

    def test_a_list_runs_the_scan_in_ci_mode(self):
        proc = self.run_step("pattern-one\n", "someone")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("scan ran with CI=true: test/test_privacy_denylist_scan.py", proc.stdout)

    def test_dependabot_without_a_list_warns_and_skips_only_the_private_scan(self):
        proc = self.run_step("  \n", "dependabot[bot]")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("::warning::", proc.stdout)
        self.assertIn("scan ran with CI=false", proc.stdout)

    def test_any_other_run_without_a_list_fails(self):
        for author in ("someone", None):
            with self.subTest(author=author):
                proc = self.run_step("", author)
                self.assertEqual(proc.returncode, 1)
                self.assertIn("::error::", proc.stdout)
                self.assertNotIn("scan ran", proc.stdout)


if __name__ == "__main__":
    unittest.main()
