#!/usr/bin/env python3
"""eval.yml's `failure-watch` job keeps one tracking issue (skills-evals#664).

eval.yml is dispatch-only, so the scheduled-run health audit never sees it
fail. Its last job opens or comments on one `eval-lane-failure` issue when a
run on main has a failed job, and closes it after a clean run. Pinned here,
from the parsed workflow:

  * the job needs every other job, so it sees every result;
  * it runs always, but only on main;
  * it holds `issues: write` and nothing else, and has no `concurrency`;
  * no `run:` script interpolates `${{ }}`; inputs arrive through `env`.

Nothing here sleeps, touches the network or calls a model.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"


def workflow():
    # PyYAML reads the `on:` key as True; only `jobs` is used here.
    return yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))


class FailureWatchTests(unittest.TestCase):
    def setUp(self):
        self.jobs = workflow()["jobs"]
        self.job = self.jobs["failure-watch"]

    def test_job_exists(self):
        self.assertIn("failure-watch", self.jobs)

    def test_needs_every_other_job(self):
        others = set(self.jobs) - {"failure-watch"}
        self.assertEqual(set(self.job["needs"]), others)

    def test_runs_always_but_only_on_main(self):
        cond = self.job["if"]
        self.assertIn("always()", cond)
        self.assertIn("refs/heads/main", cond)

    def test_permissions_are_issues_write_only(self):
        self.assertEqual(self.job["permissions"], {"issues": "write"})

    def test_no_concurrency(self):
        self.assertNotIn("concurrency", self.job)

    def test_scripts_do_not_interpolate_expressions(self):
        runs = [s["run"] for s in self.job["steps"] if "run" in s]
        self.assertTrue(runs)
        for run in runs:
            self.assertNotIn("${{", run)

    def test_step_env_carries_needs(self):
        envs = [s.get("env", {}) for s in self.job["steps"] if "run" in s]
        self.assertTrue(any("NEEDS" in env for env in envs))


if __name__ == "__main__":
    unittest.main()
