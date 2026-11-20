"""scripts/run_costs.py: one row per run and the cost percentiles that size
evals/budget.yml (Adam, 2026-11-01: keep the script to recalculate them)."""
import contextlib
import io
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


def _trial(cost, judge=None, delta=None, judge_usd=None):
    doc = {"skill": "demo", "fixture": "demo/case", "arm": "with_skill",
           "cross_model": {"model": "claude-sonnet-5-5"},
           "agent": {"cost_usd": cost, "num_turns": 3, "duration_ms": 60000,
                     "usage": {"output_tokens": 100}},
           "objective_checks": [{"passed": True}, {"passed": False}]}
    if judge is not None:
        doc["judge"] = judge
    doc["usage"] = {}
    if delta is not None:
        doc["usage"]["meter_delta"] = {"windows": {"seven_day": {
            "delta": delta, "from": 0.40, "to": 0.40 + delta}}}
    if judge_usd is not None:
        doc["usage"]["measured"] = {"judge": {"cost_usd": judge_usd}}
    return doc


class RunCostsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = Path(self.tmp.name)
        base = self.tree / "routine-results"
        # Run A: two trials, one judged with a recorded judge cost, plus an
        # aggregate roll-up that must not count as a trial.
        _write(base / "run-a/demo/case/with_skill/trial-1/summary.json",
               _trial(1.0, {"overall": 0.8}, delta=0.01, judge_usd=0.05))
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
        # 3 points over 4.05 dollars: agent 4.00 plus the 0.05 judge call.
        rate = 3 / 4.05
        self.assertAlmostEqual(summary["points_per_usd"], rate)
        # Largest call: 1.00 in run A, 2.00 in run B.
        self.assertAlmostEqual(summary["largest_call_points"][1.0], 2.0 * rate)
        self.assertAlmostEqual(summary["largest_call_points"][0.5], 1.5 * rate)
        self.assertEqual(summary["runs_with_judge_cost"], 1)

    def test_percentile_interpolates_linearly(self):
        self.assertEqual(run_costs.percentile([1, 2, 3, 4, 5], 0.5), 3)
        self.assertAlmostEqual(run_costs.percentile([0, 10], 0.975), 9.75)
        with self.assertRaises(ValueError):
            run_costs.percentile([], 0.5)

    def test_main_writes_csv_and_prints_report(self):
        out = self.tree / "runs.csv"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.assertEqual(run_costs.main(["--results-tree", str(self.tree),
                                             "--evals", str(self.tree / "none"),
                                             "--csv", str(out)]), 0)
        # Adam's standing rule: the overrun is the p95 of the largest call.
        # Largest calls are 1.00 (run A) and 2.00 (run B) dollars: p95 1.95.
        expected = 1.95 * 3 / 4.05 / 100
        self.assertIn("per_run_overrun for evals/budget.yml (p95 of the largest call, "
                      f"at the meter rate): {expected:.4f}", printed.getvalue())
        # The key no longer exists in budget.yml, so no line suggests it.
        self.assertNotIn("points_per_usd for evals/budget.yml", printed.getvalue())
        self.assertEqual(len(out.read_text(encoding="utf-8").splitlines()), 4)


    def test_meter_delta_range_columns(self):
        # Run A's delta reads 40 to 41 in the CLI's truncated whole
        # percents: the meter truly moved more than 0 and less than 2.
        row = self.table()["run-a"]
        self.assertAlmostEqual(row["meter_delta_points_low"], 0.0)
        self.assertAlmostEqual(row["meter_delta_points_high"], 2.0)
        self.assertEqual(self.table()["run-c"]["meter_delta_points_low"], "")
        self.assertEqual(self.table()["run-c"]["meter_delta_points_high"], "")


def _tokens_trial(cost, delta=None):
    """A trial whose agent role carries token counts by type."""
    doc = _trial(cost, delta=delta)
    doc["usage"]["measured"] = {"scope": "trial", "agent": {
        "calls": 1, "cost_usd": cost, "models": {"claude-sonnet-5-5": {
            "input_tokens": 1000, "output_tokens": 2000, "cache_read_input_tokens": 3000,
            "cache_creation_input_tokens": 400, "cost_usd": cost}}}}
    return doc


class EstimatedPointsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tree = Path(self.tmp.name)
        base = self.tree / "routine-results"
        _write(base / "run-a/demo/case/with_skill/trial-1/summary.json",
               _tokens_trial(2.0, delta=0.02))
        _write(base / "run-b/demo/case/with_skill/trial-1/summary.json", _trial(1.0, delta=0.01))
        self.table = {r["run_id"]: r for r in run_costs.rows(run_costs.collect(self.tree))}

    def test_rows_carry_estimated_points_when_tokens_priced_them(self):
        import allowance_points
        a = self.table["run-a"]
        expected = allowance_points.estimate_blocks(
            [_tokens_trial(2.0)["usage"]["measured"]])["points"]
        self.assertGreater(expected, 0)
        self.assertAlmostEqual(a["estimated_points"], expected)
        self.assertEqual(a["estimated_points_from_tokens"], "yes")
        self.assertEqual(self.table["run-b"]["estimated_points"], "")

    def test_summary_reports_estimated_points_per_dollar_and_charges_the_call_at_it(self):
        summary = run_costs.summarize(list(self.table.values()))
        rate = self.table["run-a"]["estimated_points"] / 2.0
        self.assertAlmostEqual(summary["estimated_points_per_usd"], rate)
        self.assertEqual(summary["estimated_runs"], 1)
        self.assertEqual(summary["largest_call_rate"], "estimated")
        # Run A's 2.00 call is the largest, at the estimated rate.
        self.assertAlmostEqual(summary["largest_call_points"][1.0], 2.0 * rate)
        self.assertAlmostEqual(summary["points_per_usd"], 3 / 3.0)
        text = "\n".join(run_costs.report(summary))
        self.assertIn("estimated points per dollar", text)
        self.assertIn("at the estimated rate", text)


if __name__ == "__main__":
    unittest.main()
