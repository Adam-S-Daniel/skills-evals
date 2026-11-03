#!/usr/bin/env python3
"""eval.yml `publish` never loses or overwrites a run that shares its directory.

Run 41587675812: two fixtures of one guidance section started in the same
second, so both legs named results/guidance/<section>/20261103T060703Z/. The
first leg published `handoff` there; the second leg's checkout of
persistent/eval-results refused over its untracked download ("untracked
working tree files would be overwritten by checkout") and `done-summary`'s
paid result was lost. scripts/relocate_colliding_runs.py moves such a run to
the next free second; the step deletes the download from the tree before the
branch switch. Hermetic: local repositories only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import relocate_colliding_runs as relocate  # noqa: E402

WORKFLOW = REPO / ".github" / "workflows" / "eval.yml"
STEP_NAME = "Build the badge over the run window, commit, and push"
BRANCH = "persistent/eval-results"
TS = "20261103T060703Z"
SECTION = "results/guidance/example-section"
ARMS = ("with_guidance_full", "without_guidance")


def git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True)


def write_run(root: Path, fixture: str, ts: str = TS) -> Path:
    run = root / SECTION / ts
    for arm in ARMS:
        (run / arm).mkdir(parents=True, exist_ok=True)
        (run / arm / "summary.json").write_text(json.dumps(
            {"arm": arm, "timestamp": ts, "fixture_name": fixture}, indent=2),
            encoding="utf-8")
    (run / "report.md").write_text(f"# Eval report\n\n- Timestamp: {ts}\n- Fixture: {fixture}\n",
                                   encoding="utf-8")
    return run


def fixture_of(run: Path) -> set:
    return {json.loads((run / arm / "summary.json").read_text())["fixture_name"]
            for arm in ARMS}


class RelocateTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.snap = self.root / "snap"
        self.branch = self.root / "branch"

    def test_a_same_second_run_of_another_fixture_moves_to_the_next_free_second(self):
        write_run(self.branch, "handoff")
        write_run(self.branch, "older", "20261103T060704Z")
        write_run(self.snap, "done-summary")
        moved = relocate.relocate(self.snap / "results", self.branch / "results")
        new = "20261103T060705Z"
        self.assertEqual(moved, [(f"guidance/example-section/{TS}",
                                  f"guidance/example-section/{new}")])
        run = self.snap / SECTION / new
        self.assertFalse((self.snap / SECTION / TS).exists())
        self.assertEqual(fixture_of(run), {"done-summary"})
        for arm in ARMS:
            self.assertEqual(json.loads((run / arm / "summary.json").read_text())["timestamp"], new)
        self.assertIn(f"- Timestamp: {new}\n", (run / "report.md").read_text())

    def test_the_same_run_published_again_is_left_in_place(self):
        write_run(self.branch, "handoff")
        write_run(self.snap, "handoff")
        self.assertEqual(relocate.relocate(self.snap / "results", self.branch / "results"), [])
        self.assertTrue((self.snap / SECTION / TS).exists())

    def test_no_collision_moves_nothing(self):
        write_run(self.branch, "handoff", "20261103T050000Z")
        write_run(self.snap, "done-summary")
        self.assertEqual(relocate.relocate(self.snap / "results", self.branch / "results"), [])

    def test_nested_timestamp_dirs_are_not_run_dirs(self):
        write_run(self.snap, "done-summary")
        (self.snap / SECTION / TS / "with_guidance_full" / "20261103T000000Z").mkdir()
        self.assertEqual([p.name for p in relocate.run_dirs(self.snap / "results")], [TS])


class TwoLegsOfOneSectionTests(unittest.TestCase):
    """The publish step's own order, driven against local repositories."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        origin = self.root / "origin.git"
        git(self.root, "init", "--bare", "-b", "main", str(origin))
        seed = self.root / "seed"
        git(self.root, "clone", str(origin), str(seed))
        for repo in (seed,):
            git(repo, "config", "user.name", "Test")
            git(repo, "config", "user.email", "test@example.com")
        (seed / "README").write_text("main\n")
        git(seed, "add", "README")
        git(seed, "commit", "-m", "main")
        git(seed, "push", "origin", "main")
        # Leg 1 (handoff) has already published its run.
        git(seed, "checkout", "-b", BRANCH)
        write_run(seed, "handoff")
        git(seed, "add", "results")
        git(seed, "commit", "-m", "leg 1")
        git(seed, "push", "origin", BRANCH)
        # Leg 2 (done-summary): a main checkout with its download in results/.
        self.leg = self.root / "leg"
        git(self.root, "clone", str(origin), str(self.leg))
        git(self.leg, "config", "user.name", "Test")
        git(self.leg, "config", "user.email", "test@example.com")
        write_run(self.leg, "done-summary")

    def test_the_second_leg_publishes_beside_the_first(self):
        snap = self.root / "eval-outputs"
        shutil.copytree(self.leg / "results", snap / "results")
        shutil.rmtree(self.leg / "results")
        git(self.leg, "checkout", "--", ".")
        git(self.leg, "fetch", "origin", BRANCH)
        git(self.leg, "checkout", "-B", BRANCH, f"origin/{BRANCH}")
        relocate.main([str(snap / "results"), str(self.leg / "results")])
        shutil.copytree(snap / "results", self.leg / "results", dirs_exist_ok=True)
        self.assertEqual(fixture_of(self.leg / SECTION / TS), {"handoff"})
        self.assertEqual(fixture_of(self.leg / SECTION / "20261103T060704Z"), {"done-summary"})

    def test_the_old_order_is_the_reported_failure(self):
        # Without deleting the download first, the branch switch refuses.
        git(self.leg, "fetch", "origin", BRANCH)
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            git(self.leg, "checkout", "-B", BRANCH, f"origin/{BRANCH}")
        self.assertIn("untracked working tree files would be overwritten", caught.exception.stderr)


class PublishStepOrderTests(unittest.TestCase):

    def test_the_step_deletes_then_switches_then_relocates_then_copies(self):
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        step = next(s for s in jobs["publish"]["steps"] if s.get("name") == STEP_NAME)
        run = step["run"]
        marks = ['cp -r results "$snap/results"',
                 'cp scripts/relocate_colliding_runs.py "$RUNNER_TEMP/"',
                 "rm -rf results",
                 "git checkout -B persistent/eval-results origin/persistent/eval-results",
                 'python3 "$RUNNER_TEMP/relocate_colliding_runs.py" "$snap/results" results',
                 'cp -r "$snap/results/." results/']
        positions = [run.index(mark) for mark in marks]
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
