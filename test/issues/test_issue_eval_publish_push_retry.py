#!/usr/bin/env python3
"""eval.yml `publish` push survives a lost race (run 41542886876).

The publish matrix jobs run in parallel and other workflows push
persistent/eval-results too, so a bare push is rejected with "fetch first" and
the eval's paid result is never published. scripts/push_results_branch.sh
rebases onto the remote tip and retries. The behavioral tests drive it against
local bare repositories; no network, no sleeps.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "push_results_branch.sh"
WORKFLOW = REPO / ".github" / "workflows" / "eval.yml"
BRANCH = "persistent/eval-results"
STEP_NAME = "Build the badge over the run window, commit, and push"


def git(cwd, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=check,
        capture_output=True, text=True,
    )


class PushRetryBehaviorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.origin = self.root / "origin.git"
        git(self.root, "init", "--bare", "-b", "main", str(self.origin))
        self.a = self._clone("a")
        self.b = self._clone("b")
        # Seed the results branch from A so both clones start in step.
        git(self.a, "checkout", "-b", BRANCH)
        self._commit(self.a, "base.txt", "base\n")
        git(self.a, "push", "origin", BRANCH)
        git(self.b, "fetch", "origin", BRANCH)
        git(self.b, "checkout", "-B", BRANCH, f"origin/{BRANCH}")

    def _clone(self, name):
        path = self.root / name
        git(self.root, "clone", str(self.origin), str(path))
        git(path, "config", "user.name", "Test")
        git(path, "config", "user.email", "test@example.com")
        git(path, "config", "commit.gpgsign", "false")
        return path

    def _commit(self, clone, name, text):
        (clone / name).write_text(text)
        git(clone, "add", name)
        git(clone, "commit", "-m", f"add {name}")

    def _run(self, clone, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
        return subprocess.run(
            ["bash", str(SCRIPT), *args], cwd=clone, env=env,
            capture_output=True, text=True,
        )

    def _origin_files(self):
        out = git(self.origin, "ls-tree", "-r", "--name-only", BRANCH).stdout
        return set(out.split())

    def test_plain_push_without_a_race(self):
        self._commit(self.b, "b.txt", "b\n")
        result = self._run(self.b, "origin", BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._origin_files(), {"base.txt", "b.txt"})

    def test_lost_race_is_rebased_and_pushed(self):
        self._commit(self.a, "a.txt", "a\n")
        git(self.a, "push", "origin", BRANCH)
        self._commit(self.b, "b.txt", "b\n")
        result = self._run(self.b, "origin", BRANCH, "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._origin_files(), {"base.txt", "a.txt", "b.txt"})

    def test_conflict_exits_1_and_leaves_no_rebase_in_progress(self):
        self._commit(self.a, "same.txt", "from a\n")
        git(self.a, "push", "origin", BRANCH)
        self._commit(self.b, "same.txt", "from b\n")
        result = self._run(self.b, "origin", BRANCH)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("::error::", result.stdout)
        gitdir = Path(git(self.b, "rev-parse", "--absolute-git-dir").stdout.strip())
        self.assertFalse((gitdir / "rebase-merge").exists())
        self.assertFalse((gitdir / "rebase-apply").exists())

    def test_bad_attempts_argument_fails(self):
        self._commit(self.b, "b.txt", "b\n")
        for bad in ("0", "-1", "x", "", "1.5"):
            with self.subTest(attempts=bad):
                result = self._run(self.b, "origin", BRANCH, bad)
                self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("b.txt", self._origin_files())


class PublishStepTests(unittest.TestCase):
    def setUp(self):
        wf = yaml.safe_load(WORKFLOW.read_text())
        steps = wf["jobs"]["publish"]["steps"]
        matches = [s for s in steps if s.get("name") == STEP_NAME]
        self.assertEqual(len(matches), 1)
        self.run_text = matches[0]["run"]

    def test_step_uses_the_retrying_helper(self):
        self.assertIn("push_results_branch.sh", self.run_text)
        self.assertIn('cp scripts/push_results_branch.sh "$RUNNER_TEMP/"', self.run_text)
        self.assertIn('bash "$RUNNER_TEMP/push_results_branch.sh" origin persistent/eval-results', self.run_text)

    def test_no_bare_push_remains(self):
        for line in self.run_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertNotRegex(stripped, r"\bpush origin persistent/eval-results\b")


if __name__ == "__main__":
    unittest.main()
