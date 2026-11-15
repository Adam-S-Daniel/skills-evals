#!/usr/bin/env python3
"""The monthly API-credit lane: scripts/credit_lane.py's plan rules and the
shape of .github/workflows/credit-lane.yml.

Deterministic: every case builds its own results tree, fixtures, window file
and eval.yml run list in a temporary directory and passes `now`.

    python3 -m pytest test/issues/test_credit_lane.py -q
"""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import credit_lane  # noqa: E402

OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
# A Saturday, well outside the Monday guidance merge window.
NOW = datetime(2026, 12, 12, 10, 0, tzinfo=timezone.utc)
POLICY = {"grant_day": 7, "window_days": 20, "soft_cap_usd": 170, "models": [OPUS, SONNET],
          "trials": 1, "group_max": 20,
          "est_usd_per_fixture": {OPUS: 0.95, SONNET: 0.40}}
WINDOW = "timezone: America/New_York\nweekday: 1\nstart: \"12:00\"\nend: \"14:00\"\n"


class Lane(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.results = self.tmp / "results"
        self.evals = self.tmp / "evals"
        self.guidance = self.tmp / "guidance"
        (self.guidance / "scripts").mkdir(parents=True)
        (self.guidance / "scripts" / "base-md-merge-window.yml").write_text(WINDOW)
        self.waiting = [{"kind": "skill", "subject": "some-skill"},
                        {"kind": "guidance", "subject": "alpha"},
                        {"kind": "guidance", "subject": "beta"}]
        self.fixture("alpha", "one")
        self.fixture("alpha", "two")
        self.fixture("beta", "three")
        self.policy = json.loads(json.dumps(POLICY))
        self.runs: list[dict] = []
        self.stamp = 0

    def fixture(self, subject, name, **extra):
        path = self.evals / "guidance" / subject / name / "fixture.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"prompt": "p", **extra}))

    def result(self, subject, name, model, usd, when="20261208T0000{:02d}Z", tree="results"):
        """One eval.yml (or routine) result with its own stamp."""
        self.stamp += 1
        stamp = when.format(self.stamp) if "{" in when else when
        base = self.results / tree / "guidance" / subject / stamp / "with_guidance_full"
        if tree == "routine-results":
            base = self.results / tree / f"run-{self.stamp}" / "guidance" / subject / name / "arm"
        base.mkdir(parents=True)
        (base / "summary.json").write_text(json.dumps({
            "section": subject, "fixture_name": name, "arm": "with_guidance_full",
            "cross_model": {"model": model}, "agent": {"cost_usd": usd}}))

    def plan(self, now=NOW):
        batch = self.results / "batches" / "current.json"
        batch.parent.mkdir(parents=True, exist_ok=True)
        batch.write_text(json.dumps({"waiting": self.waiting, "members": []}))
        return credit_lane.plan(self.policy, results_tree=self.results, runs=self.runs,
                                guidance_tree=self.guidance, evals=self.evals, now=now)


class WindowRules(Lane):
    def test_window_edges(self):
        start = datetime(2026, 12, 7, tzinfo=timezone.utc)
        self.assertTrue(self.plan(start)["dispatch"])
        before = self.plan(datetime(2026, 12, 6, 23, 59, 59, tzinfo=timezone.utc))
        self.assertFalse(before["dispatch"])
        self.assertIn("outside the credit window", before["reason"])
        self.assertTrue(self.plan(datetime(2026, 12, 26, 23, 59, tzinfo=timezone.utc))["dispatch"])
        self.assertFalse(self.plan(datetime(2026, 12, 27, tzinfo=timezone.utc))["dispatch"])

    def test_eval_pause_stops_the_lane(self):
        monday_noon_thirty_et = datetime(2026, 12, 14, 17, 30, tzinfo=timezone.utc)
        decision = self.plan(monday_noon_thirty_et)
        self.assertFalse(decision["dispatch"])
        self.assertIn("eval pause", decision["reason"])

    def test_unreadable_window_fails_closed(self):
        (self.guidance / "scripts" / "base-md-merge-window.yml").unlink()
        decision = self.plan()
        self.assertFalse(decision["dispatch"])
        self.assertIn("no eval may start", decision["reason"])


class RunRules(Lane):
    def test_one_dispatch_at_a_time(self):
        for status in ("queued", "in_progress", "waiting", "pending"):
            with self.subTest(status=status):
                self.runs = [{"id": 5, "status": status, "event": "schedule"}]
                decision = self.plan()
                self.assertFalse(decision["dispatch"])
                self.assertIn("one dispatch at a time", decision["reason"])

    def test_a_failed_dispatch_stops_the_window_and_names_the_run(self):
        for conclusion in ("failure", "cancelled", "timed_out"):
            with self.subTest(conclusion=conclusion):
                self.runs = [{"id": 9, "status": "completed", "conclusion": conclusion,
                              "event": "workflow_dispatch", "created_at": "2026-12-08T01:00:00Z",
                              "html_url": "https://github.com/o/r/actions/runs/9"}]
                decision = self.plan()
                self.assertFalse(decision["dispatch"])
                self.assertIn("https://github.com/o/r/actions/runs/9", decision["reason"])
                self.assertIn(conclusion, decision["reason"])

    def test_failures_outside_the_window_or_not_dispatched_do_not_stop_it(self):
        self.runs = [
            {"id": 1, "status": "completed", "conclusion": "failure",
             "event": "workflow_dispatch", "created_at": "2026-11-20T01:00:00Z"},
            {"id": 2, "status": "completed", "conclusion": "failure",
             "event": "schedule", "created_at": "2026-12-08T01:00:00Z"},
            {"id": 3, "status": "completed", "conclusion": "success",
             "event": "workflow_dispatch", "created_at": "2026-12-08T01:00:00Z"}]
        self.assertTrue(self.plan()["dispatch"])


class Selection(Lane):
    def test_targets_are_waiting_guidance_in_order_without_in_place_fixtures(self):
        self.fixture("beta", "inplace", context={"repo": "x"})
        decision = self.plan()
        self.assertEqual(decision["fixtures"], ["evals/guidance/alpha/one",
                                                "evals/guidance/alpha/two",
                                                "evals/guidance/beta/three"])
        self.assertNotIn("some-skill", json.dumps(decision))

    def test_nothing_to_run(self):
        self.waiting = [{"kind": "skill", "subject": "some-skill"}]
        decision = self.plan()
        self.assertFalse(decision["dispatch"])
        self.assertIn("no waiting guidance subject", decision["reason"])

    def test_model_with_fewer_runs_wins_and_ties_go_first(self):
        self.assertEqual(self.plan()["model"], OPUS)
        self.result("alpha", "one", OPUS, 1.0)
        self.assertEqual(self.plan()["model"], SONNET)
        self.result("alpha", "one", SONNET, 0.4)
        self.assertEqual(self.plan()["model"], OPUS)

    def test_fewest_runs_first_with_target_order_as_tiebreak(self):
        self.result("alpha", "one", OPUS, 1.0)
        self.result("alpha", "two", SONNET, 0.4)
        self.result("alpha", "two", SONNET, 0.4)
        decision = self.plan()
        self.assertEqual(decision["model"], OPUS)
        self.assertEqual(decision["fixtures"], ["evals/guidance/alpha/two",
                                                "evals/guidance/beta/three",
                                                "evals/guidance/alpha/one"])

    def test_group_max_limits_the_dispatch(self):
        self.policy["group_max"] = 2
        self.assertEqual(len(self.plan()["fixtures"]), 2)


class Spend(Lane):
    def test_cap_shrinks_the_group(self):
        self.result("beta", "three", SONNET, 168.0)  # one Sonnet run: Opus is next
        decision = self.plan()
        self.assertEqual(decision["model"], OPUS)
        self.assertAlmostEqual(decision["spent_usd"], 168.0)
        self.assertEqual(len(decision["fixtures"]), 2)  # 2 x 0.95 <= 2.00 of room
        self.assertAlmostEqual(decision["est_usd"], 1.90)
        self.assertLessEqual(decision["spent_usd"] + decision["est_usd"], 170)

    def test_cap_reached(self):
        self.result("beta", "three", SONNET, 169.5)
        decision = self.plan()
        self.assertFalse(decision["dispatch"])
        self.assertIn("cap reached", decision["reason"])

    def test_only_api_lane_results_inside_the_window_count(self):
        self.result("alpha", "one", OPUS, 100.0, tree="routine-results")
        self.result("alpha", "one", OPUS, 100.0, when="20261106T000000Z")
        self.result("alpha", "one", OPUS, 2.5)
        decision = self.plan()
        self.assertAlmostEqual(decision["spent_usd"], 2.5)
        self.assertTrue(decision["dispatch"])


class Policy(unittest.TestCase):
    def write(self, doc) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        path = tmp / "credit-policy.yml"
        path.write_text(yaml.safe_dump(doc))
        return path

    def test_the_committed_policy_loads(self):
        policy = credit_lane.load_policy(ROOT / "evals" / "credit-policy.yml")
        self.assertEqual(set(policy), set(credit_lane.POLICY_KEYS))
        roster = (ROOT / "evals" / "roster.yml").read_text()
        for model in policy["models"]:
            self.assertIn(f'id: "{model}"', roster)

    def test_each_missing_key_is_named(self):
        for key in credit_lane.POLICY_KEYS:
            with self.subTest(key=key):
                doc = {k: v for k, v in POLICY.items() if k != key}
                with self.assertRaisesRegex(credit_lane.PolicyError, key):
                    credit_lane.load_policy(self.write(doc))

    def test_missing_file_and_bad_values(self):
        with self.assertRaisesRegex(credit_lane.PolicyError, "missing"):
            credit_lane.load_policy(Path(tempfile.gettempdir()) / "no-such-credit-policy.yml")
        for key, value in (("trials", 4), ("group_max", 21), ("soft_cap_usd", 0),
                           ("models", []), ("est_usd_per_fixture", {OPUS: 1})):
            with self.subTest(key=key):
                with self.assertRaises(credit_lane.PolicyError):
                    credit_lane.load_policy(self.write({**POLICY, key: value}))

    def test_cli_fails_descriptively_on_a_missing_key(self):
        path = self.write({k: v for k, v in POLICY.items() if k != "soft_cap_usd"})
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            rc = credit_lane.main(["plan", "--policy", str(path), "--results-tree", ".",
                                   "--runs-json", "x", "--guidance-tree", ".",
                                   "--now", "2026-12-12T10:00:00Z"])
        self.assertEqual(rc, 1)
        self.assertIn("soft_cap_usd", err.getvalue())


class CliOutput(Lane):
    def test_plan_prints_the_decision_json(self):
        runs = self.tmp / "runs.json"
        runs.write_text(json.dumps({"workflow_runs": []}))
        self.plan()  # writes batches/current.json
        policy = self.tmp / "policy.yml"
        policy.write_text(yaml.safe_dump(POLICY))
        out = io.StringIO()
        with redirect_stdout(out):
            rc = credit_lane.main(["plan", "--policy", str(policy), "--results-tree",
                                   str(self.results), "--runs-json", str(runs),
                                   "--guidance-tree", str(self.guidance), "--evals",
                                   str(self.evals), "--now", "2026-12-12T10:00:00Z"])
        self.assertEqual(rc, 0)
        decision = json.loads(out.getvalue())
        self.assertEqual(set(decision), {"dispatch", "reason", "model", "fixtures",
                                         "spent_usd", "est_usd"})
        self.assertTrue(decision["dispatch"])


class Workflow(unittest.TestCase):
    PATH = ROOT / ".github" / "workflows" / "credit-lane.yml"

    @classmethod
    def setUpClass(cls):
        cls.text = cls.PATH.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.text)
        cls.job = cls.doc["jobs"]["plan-and-dispatch"]

    def test_triggers_permissions_and_concurrency(self):
        on = self.doc[True]  # PyYAML reads `on` as True
        self.assertEqual(set(on), {"schedule", "workflow_dispatch"})
        self.assertEqual(on["schedule"], [{"cron": "41 */3 * * *"}])
        dry = on["workflow_dispatch"]["inputs"]["dry_run"]
        self.assertEqual((dry["type"], dry["default"]), ("boolean", False))
        self.assertEqual(self.doc["permissions"], {})
        self.assertEqual(self.job["permissions"], {"contents": "read", "actions": "write"})
        self.assertEqual(self.doc["concurrency"],
                         {"group": "credit-lane", "cancel-in-progress": False})
        self.assertIn("default_branch", self.job["if"])

    def test_checkouts_do_not_persist_credentials(self):
        checkouts = [s for s in self.job["steps"] if str(s.get("uses", "")).startswith("actions/checkout@")]
        self.assertEqual(len(checkouts), 3)
        for step in checkouts:
            self.assertIs(step["with"]["persist-credentials"], False)
        self.assertIn("persistent/eval-results", [s["with"].get("ref") for s in checkouts])

    def test_no_expression_inside_run_and_dispatch_honours_dry_run(self):
        for step in self.job["steps"]:
            self.assertNotIn("${{", step.get("run", ""), step.get("name"))
        dispatch = next(s for s in self.job["steps"] if s.get("name") == "Dispatch eval.yml")
        self.assertIn("inputs.dry_run", dispatch["if"])
        self.assertIn("gh workflow run eval.yml", dispatch["run"])
        self.assertEqual(set(dispatch["env"]) >= {"FIXTURES", "MODEL", "TRIALS"}, True)

    def test_the_workflow_is_tabled_and_locked(self):
        table = (ROOT / "docs" / "workflows.md").read_text(encoding="utf-8")
        self.assertIn("| `credit-lane.yml` |", table)
        lock = yaml.safe_load((ROOT / ".github" / "workflows" / "actions.lock").read_text())
        self.assertIn(".github/workflows/credit-lane.yml", lock["workflows"])


if __name__ == "__main__":
    unittest.main()
