#!/usr/bin/env python3
"""One eval.yml dispatch runs a batch of fixtures, each with 1 to 3 trials.

Parses the workflow with PyYAML and the planner as a module; nothing here
sleeps, touches the network or calls a model.
"""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/eval.yml"
spec = importlib.util.spec_from_file_location("planner", ROOT / "scripts/plan_scheduled_evals.py")
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)

DEFAULT = planner.DEFAULT_FIXTURE


def doc():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def eval_steps():
    return doc()["jobs"]["eval"]["steps"]


def step_named(prefix):
    for step in eval_steps():
        if (step.get("name") or "").startswith(prefix):
            return step
    raise AssertionError(f"no eval step named {prefix!r}")


class BatchPlanTests(unittest.TestCase):
    def setUp(self):
        self.committed = planner.committed_fixtures(ROOT)
        self.assertGreaterEqual(len(self.committed), 3)

    def dispatch(self, value):
        return planner.plan(ROOT, "workflow_dispatch", {"inputs": {"fixture": value}})

    def test_multiple_fixtures_keep_order_and_get_slots(self):
        paths = [self.committed[2], self.committed[0], self.committed[1]]
        # Spaces, newlines and runs of whitespace all separate entries.
        matrix = self.dispatch(f"{paths[0]} {paths[1]}\n\n{paths[2]}\n")
        self.assertEqual(matrix, {"include": [
            {"fixture": path, "eval_key": path[len("evals/"):], "slot": slot}
            for slot, path in enumerate(paths)]})

    def test_empty_or_blank_dispatch_runs_the_default(self):
        for value in (None, "", "  \n\t "):
            with self.subTest(value=value):
                self.assertEqual(self.dispatch(value)["include"],
                                 [{"fixture": DEFAULT, "eval_key": DEFAULT[6:], "slot": 0}])

    def test_every_entry_is_validated(self):
        good = self.committed[0]
        for bad in ("evals/nope", "evals/workflow-path-audit", "../x", "$(id)", "evals/a;b"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.dispatch(f"{good} {bad}")
            with self.subTest(bad=bad, first=True), self.assertRaises(ValueError):
                self.dispatch(f"{bad} {good}")
        with self.assertRaises(ValueError):
            self.dispatch("\0" + good)
        with self.assertRaises(ValueError):
            self.dispatch([good])

    def test_a_duplicate_is_rejected(self):
        good = self.committed[0]
        with self.assertRaises(ValueError):
            self.dispatch(f"{good}\n{good}")

    def test_more_than_twenty_entries_are_rejected(self):
        # Reuse a real path with a distinct, charset-clean suffix per entry so
        # only the count can be the reason: 21 invalid entries still fail, but
        # twenty valid committed ones must pass when the tree has them.
        too_many = " ".join(f"evals/x{i}" for i in range(21))
        with self.assertRaises(ValueError):
            self.dispatch(too_many)
        twenty = [f"evals/x{i}" for i in range(20)]
        fake_root = mock_committed(twenty)
        with fake_root:
            matrix = self.dispatch(" ".join(twenty))
            self.assertEqual(len(matrix["include"]), 20)
            with self.assertRaises(ValueError) as caught:
                self.dispatch(" ".join(twenty + ["evals/x20"]))
            self.assertIn("too many", str(caught.exception))


def mock_committed(paths):
    from unittest import mock
    return mock.patch.object(planner, "committed_fixtures", return_value=sorted(paths))


class WorkflowShapeTests(unittest.TestCase):
    def test_fixture_description_and_trials_input(self):
        triggers = doc().get("on", doc().get(True))
        inputs = triggers["workflow_dispatch"]["inputs"]
        self.assertIn("whitespace-separated", inputs["fixture"]["description"])
        self.assertIn("max 20", inputs["fixture"]["description"])
        trials = inputs["trials"]
        self.assertEqual(trials["default"], "1")
        self.assertEqual(trials["type"], "string")
        self.assertFalse(trials["required"])

    def test_selection_step_uses_the_matrix_fixture_only(self):
        step = step_named("Select and validate the fixture")
        self.assertEqual(step["env"]["MATRIX_FIXTURE"], "${{ matrix.fixture }}")
        self.assertNotIn("inputs.fixture", step["run"])
        self.assertNotIn("GITHUB_EVENT_PATH", step["run"])
        self.assertNotIn("SCHEDULE_FIXTURE", json.dumps(step))

    def test_each_leg_runs_its_own_fixture(self):
        script = step_named("Select and validate the fixture")["run"]
        for fixture in planner.committed_fixtures(ROOT)[:3]:
            with tempfile.TemporaryDirectory() as tmp:
                event = Path(tmp) / "event.json"
                # The event names a different fixture; the leg must ignore it.
                event.write_text(json.dumps({"inputs": {"fixture": DEFAULT + " " + fixture}}))
                env = dict(os.environ, MATRIX_FIXTURE=fixture, MATRIX_KEY=fixture[6:],
                           MATRIX_SLOT="1", GITHUB_EVENT_PATH=str(event),
                           GITHUB_OUTPUT=str(Path(tmp) / "out"), RUNNER_TEMP=tmp)
                result = subprocess.run(["bash", "-c", script], cwd=ROOT, env=env,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((Path(tmp) / "eval-fixture").read_text(), fixture)

    def _run_trials(self, event):
        script = step_named("Read and validate the trials")["run"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps(event))
            env = dict(os.environ, GITHUB_EVENT_PATH=str(path), RUNNER_TEMP=tmp)
            result = subprocess.run(["bash", "-c", script], env=env,
                                    capture_output=True, text=True)
            written = Path(tmp, "eval-trials")
            return result, written.read_text() if written.is_file() else None

    def test_trials_are_read_from_the_event_and_validated(self):
        step = step_named("Read and validate the trials")
        self.assertIn("GITHUB_EVENT_PATH", step["run"])
        self.assertIn("[1-3]", step["run"])
        for event in ({}, {"inputs": {}}, {"inputs": {"trials": ""}}):
            result, written = self._run_trials(event)
            self.assertEqual((result.returncode, written), (0, "1"), result.stderr)
        for value in ("1", "2", "3"):
            result, written = self._run_trials({"inputs": {"trials": value}})
            self.assertEqual((result.returncode, written), (0, value), result.stderr)
        for bad in ("0", "4", "10", "01", "1\n2", "a", "$(id)", "-1", " 2"):
            result, written = self._run_trials({"inputs": {"trials": bad}})
            self.assertEqual(result.returncode, 1, bad)
            self.assertIsNone(written)
            self.assertIn("'trials' must be 1, 2 or 3", result.stdout)

    def test_trials_are_validated_before_any_credential_and_no_run_interpolates_inputs(self):
        names = [s.get("name") or "" for s in eval_steps()]
        trials = next(i for i, n in enumerate(names) if n.startswith("Read and validate the trials"))
        mint = next(i for i, n in enumerate(names) if n.startswith("Mint OIDC"))
        self.assertLess(trials, mint)
        for job in doc()["jobs"].values():
            for step in job["steps"]:
                self.assertNotIn("${{ inputs.", step.get("run") or "")

    def test_run_step_passes_trials(self):
        run = step_named("Run the eval")["run"]
        self.assertIn('trials="$(cat "$RUNNER_TEMP/eval-trials")"', run)
        self.assertIn('--trials "$trials"', run)

    def test_eval_runs_three_legs_and_publish_stays_serial(self):
        jobs = doc()["jobs"]
        self.assertEqual(jobs["eval"]["strategy"]["max-parallel"], 3)
        self.assertEqual(jobs["publish"]["strategy"]["max-parallel"], 1)


if __name__ == "__main__":
    unittest.main()
