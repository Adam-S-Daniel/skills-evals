"""scripts/run_costs.py: one row per run and the cost percentiles that size
evals/budget.yml (Adam, 2026-11-01: keep the script to recalculate them)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_costs  # noqa: E402


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _trial(cost, judge=None, delta=None):
    doc = {"skill": "demo", "fixture": "demo/case", "arm": "with_skill",
           "cross_model": {"model": "claude-sonnet-5-5"},
           "agent": {"cost_usd": cost, "num_turns": 3, "duration_ms": 60000,
                     "usage": {"output_tokens": 100}},
           "objective_checks": [{"passed": True}, {"passed": False}]}
    if judge is not None:
        doc["judge"] = judge
    if delta is not None:
        doc["usage"] = {"meter_delta": {"windows": {"seven_day": {
            "delta": delta, "from": 0.40, "to": 0.40 + delta}}}}
    return doc


class RunCostsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = Path(self.tmp.name)
        base = self.tree / "routine-results"
        # Run A: two trials, one judged with a recorded judge cost, plus an
        # aggregate roll-up that must not count as a trial.
        _write(base / "run-a/demo/case/with_skill/trial-1/summary.json",
               _trial(1.0, {"overall": 0.8, "cost_usd": 0.05}, delta=0.01))
        _write(base / "run-a/demo/case/with_skill/trial-2/summary.json",
               _trial(1.0, {"status": "skipped"}))
        _write(base / "run-a/demo/case/with_skill/summary.json",
               {"aggregate": {}, "arm": "with_skill", "fixture": "demo/case"})
        # Run B: one trial, two points on the meter.
        _write(base / "run-b/demo/case/with_skill/trial-1/summary.json",
               _trial(2.0, delta=0.02))
        # Run C: no meter reading.
        _write(base / "run-c/demo/case/with_skill/trial-1/summary.json", _trial(0.5))

    def tearDown(self):
        self.tmp.cleanup()

    def table(self):
        return {r["run_id"]: r for r in run_costs.rows(run_costs.collect(self.tree))}

    def test_one_row_per_run_with_trials_judge_and_meter(self):
        table = self.table()
        self.assertEqual(sorted(table), ["run-a", "run-b", "run-c"])
        a = table["run-a"]
        self.assertEqual(a["trials"], 2)
        self.assertEqual(a["judged_trials"], 1)
        self.assertEqual(a["objective_decided_trials"], 1)
        self.assertEqual(a["fixture"], "demo/case")
        self.assertEqual(a["model"], "claude-sonnet-5-5")
        self.assertEqual(a["agent_api_equiv_usd"], 2.0)
        self.assertAlmostEqual(a["judge_usd"], 0.05)
        self.assertAlmostEqual(a["meter_delta_points"], 1.0)
        self.assertEqual(table["run-c"]["meter_delta_points"], "")
        self.assertEqual(table["run-c"]["judge_usd"], "")

    def test_percentiles_and_points_per_dollar(self):
        summary = run_costs.summarize(list(self.table().values()))
        self.assertEqual(summary["runs"], 3)
        self.assertEqual(summary["metered"], 2)
        self.assertAlmostEqual(summary["percentiles"][0.5], 1.5)
        self.assertAlmostEqual(summary["percentiles"][0.99], 1.99)
        self.assertAlmostEqual(summary["max"], 2.0)
        # 3 points over 4 agent dollars.
        self.assertAlmostEqual(summary["points_per_usd"], 0.75)
        self.assertAlmostEqual(summary["agent_call_points"]["max"], 1.5)
        self.assertEqual(summary["runs_with_judge_cost"], 1)

    def test_percentile_interpolates_linearly(self):
        self.assertEqual(run_costs.percentile([1, 2, 3, 4, 5], 0.5), 3)
        self.assertAlmostEqual(run_costs.percentile([0, 10], 0.975), 9.75)
        with self.assertRaises(ValueError):
            run_costs.percentile([], 0.5)

    def test_main_writes_csv_and_prints_report(self):
        out = self.tree / "runs.csv"
        self.assertEqual(run_costs.main(["--results-tree", str(self.tree),
                                         "--evals", str(self.tree / "none"),
                                         "--csv", str(out)]), 0)
        self.assertEqual(len(out.read_text(encoding="utf-8").splitlines()), 4)


if __name__ == "__main__":
    unittest.main()
