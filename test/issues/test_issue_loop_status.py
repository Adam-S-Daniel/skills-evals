"""scripts/loop_status.py: the status document the AI Usage dashboard shows
(Adam, 2026-11-20, "observability on the loop guards, pace, usage"). Every
figure comes from allowance_guard.py or forecast_catch_up.py; these tests
check the document carries their numbers and verdicts. Invented data only;
`now` and the fire counts are passed in, so nothing reads the network."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
import allowance_guard as guard  # noqa: E402
import loop_status  # noqa: E402

NOW = datetime(2026, 11, 20, 18, 0, 0, tzinfo=timezone.utc)
LIMITS = {"weekly_cap": 0.25, "per_run_cap": 0.01, "per_run_overrun": 0.0005,
          "stop_when_account_above": 0.80, "legacy_usd_per_point": 12.35,
          "claude_plan": "ultra"}
RESETS = datetime(2026, 11, 23, 17, 0, 0, tzinfo=timezone.utc)


def iso(when):
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def base_state(**extra):
    state = {"session_hold": False, "pace_hold": False, "pace_probe": False,
             "spent": 0.10, "pending": 0.01, "committed": 0.11, "bound": None,
             "stop_left": None, "stop": 0.8, "runs": 4, "fires": 5, "recent": 0,
             "reservation": 0.0105, "cap": 0.16, "cap_configured": 0.25,
             "loop_reserve": 0.09, "pace_room": 0.0, "account_used": None,
             "week_elapsed": None, "improve_fires": 0, "improve_charge": 0.1,
             "improve_finished": 0, "improve_finished_held": 0.0}
    state.update(extra)
    return state


class VerdictTests(unittest.TestCase):
    def test_room_under_the_cap_is_open(self):
        code, why = loop_status.verdict(base_state())
        self.assertEqual(code, "open")
        self.assertIn(str(guard.fits(base_state())), why)

    def test_the_5_hour_stop_comes_first(self):
        code, _ = loop_status.verdict(base_state(session_hold=True, pace_hold=True))
        self.assertEqual(code, "session_hold")

    def test_pace_hold_with_a_reading(self):
        code, why = loop_status.verdict(base_state(pace_hold=True, account_used=0.74))
        self.assertEqual(code, "pace_hold")
        self.assertIn("ahead", why)

    def test_pace_hold_without_a_reading_and_the_probe(self):
        self.assertEqual(loop_status.verdict(base_state(pace_hold=True))[0], "pace_hold")
        self.assertEqual(loop_status.verdict(base_state(pace_hold=True, pace_probe=True))[0],
                         "pace_probe")

    def test_a_full_cap(self):
        self.assertEqual(loop_status.verdict(base_state(spent=0.16, committed=0.16))[0], "cap_full")


class LiveReadingTests(unittest.TestCase):
    def test_a_fresh_reading_gives_the_share_of_the_week_gone(self):
        got = loop_status.live_reading(76.0, NOW - timedelta(minutes=5), RESETS, NOW)
        self.assertAlmostEqual(got["used"], 0.76)
        left = (RESETS - NOW).total_seconds() / guard.WINDOW.total_seconds()
        self.assertAlmostEqual(got["elapsed"], 1 - left)

    def test_stale_future_or_out_of_range_readings_are_not_used(self):
        self.assertIsNone(loop_status.live_reading(76.0, NOW - timedelta(hours=2), RESETS, NOW))
        self.assertIsNone(loop_status.live_reading(76.0, NOW + timedelta(hours=1), RESETS, NOW))
        self.assertIsNone(loop_status.live_reading(120.0, NOW, RESETS, NOW))
        self.assertIsNone(loop_status.live_reading(76.0, NOW, NOW - timedelta(hours=1), NOW))
        self.assertIsNone(loop_status.live_reading(None, NOW, RESETS, NOW))

    def test_the_pace_line_is_the_guards(self):
        reading = loop_status.live_reading(76.0, NOW, RESETS, NOW)
        block = loop_status.pace_block(reading, LIMITS, "live")
        self.assertAlmostEqual(block["line_pct"], 80 * reading["elapsed"])
        self.assertEqual(block["ahead"], guard.ahead_of_pace(0.76, reading["elapsed"], LIMITS))
        self.assertTrue(block["ahead"])
        under = loop_status.pace_block(loop_status.live_reading(10.0, NOW, RESETS, NOW),
                                       LIMITS, "live")
        self.assertFalse(under["ahead"])
        self.assertGreater(under["under_line_points"], 0)


    def test_the_live_reading_is_read_as_rounded_not_truncated(self):
        # The collector passes the usage endpoint's utilization, which rounds
        # to a whole percent: 45 is [44.5, 45.5), so with the line at 45.75
        # the account is under it. Read as a truncated CLI value (top 46) it
        # would show as ahead.
        reading = loop_status.live_reading(45.0, NOW, RESETS, NOW)
        limits = {**LIMITS, "stop_when_account_above": 0.4575 / reading["elapsed"]}
        self.assertFalse(loop_status.pace_block(reading, limits, "live")["ahead"])
        self.assertTrue(loop_status.pace_block(reading, limits, "guard")["ahead"])


FORECAST = {
    "inputs": {"usd_per_point": [6.0, 8.0], "weekly_cap_points": 16.0,
               "loop_jobs_points_per_week": 9.0,
               "assumptions": {"non_eval_points_per_week": 50.0, "pace_hold": True},
               "scheduled_tasks": [{"task": "Dashboard refresh", "in_loop": True, "model": "m",
                                    "fires_per_week": 7, "points_per_week": 3.5}]},
    "subjects": [{}, {}],
    "backlog_points_central": 26.0,
    "keep_up_usd_per_week": 70.0,
    "capacity_usd_per_week": {"plan_central": 140.0},
    "scenarios": {"plan_cap_only": {"weeks_central": 2.5, "weeks_fast": 1.0,
                                    "weeks_slow": float("inf"),
                                    "done_central": "2026-12-08T00:00:00+00:00",
                                    "done_fast": "2026-11-27T00:00:00+00:00",
                                    "done_slow": None}},
}


class ForecastTests(unittest.TestCase):
    def test_points_are_dollars_at_the_mid_rate(self):
        got = loop_status.forecast_block(FORECAST)
        self.assertAlmostEqual(got["keep_up_points_per_week"], 10.0)
        self.assertAlmostEqual(got["capacity_points_per_week"], 20.0)
        self.assertEqual(got["open_subjects"], 2)

    def test_catch_up_weeks_and_dates(self):
        got = loop_status.forecast_block(FORECAST)
        self.assertEqual(got["catch_up_weeks"], {"central": 2.5, "fast": 1.0, "slow": None})
        self.assertEqual(got["catch_up_date"]["central"], "2026-12-08T00:00:00+00:00")

    def test_per_task_rows(self):
        got = loop_status.forecast_block(FORECAST)
        self.assertEqual(got["tasks"][0]["task"], "Dashboard refresh")
        self.assertEqual(got["tasks"][0]["points_per_week"], 3.5)

    def test_the_pace_replay_behind_the_capacity(self):
        doc = json.loads(json.dumps(FORECAST))
        doc["inputs"]["pace_replay"] = {
            "points": 6.0, "low": 4.5, "high": 8.0, "flat_points": 0.0,
            "weeks": [{"half_spent_by_hours": 17.0}, {"half_spent_by_hours": 57.0}]}
        got = loop_status.forecast_block(doc)["pace_replay"]
        self.assertEqual(got, {"weeks": 2, "low_points": 4.5, "high_points": 8.0,
                               "flat_points": 0.0, "half_spent_by_hours": 37.0})
        self.assertIsNone(loop_status.forecast_block(FORECAST)["pace_replay"])

    def test_the_catch_up_calculation_step_by_step_in_points(self):
        doc = json.loads(json.dumps(FORECAST))
        doc["subjects"] = [{"kind": "skill", "subject": "a", "route": "keep", "open_cells": 1,
                            "pairs_central": 4, "usd_central": 14.0},
                           {"kind": "guidance", "subject": "b", "route": "remove-or-cap",
                            "open_cells": 2, "pairs_central": 20, "usd_central": 70.0}]
        doc["backlog_usd"] = {"central": 84.0, "low": 70.0, "high": 140.0}
        doc["backlog_pairs"] = {"central": 24}
        doc["keep_up_items"] = {"new skills": 35.0, "new git hooks": 0.0, "re-checks": 35.0}
        doc["inputs"]["cap_steps"] = {"weekly_cap_points": 25.0, "after_loop_jobs_points": 16.0,
                                      "after_account_stop_points": 16.0,
                                      "account_stop_basis": "pace_replay"}
        doc["inputs"]["assumptions"]["start"] = "2026-11-23T17:00:00Z"
        c = loop_status.forecast_block(doc)["calculation"]
        self.assertEqual([r["subject"] for r in c["subjects"]], ["b", "a"])  # largest first
        self.assertAlmostEqual(c["subjects"][0]["points"], 10.0)
        self.assertEqual(c["subjects_total"], 2)
        self.assertAlmostEqual(c["backlog_points"]["central"], 12.0)
        self.assertEqual((c["weekly_cap_points"], c["loop_jobs_points"],
                          c["after_loop_jobs_points"], c["capacity_basis"]),
                         (25.0, 9.0, 16.0, "pace_replay"))
        self.assertAlmostEqual(c["capacity_points"], 20.0)
        self.assertEqual([i["item"] for i in c["keep_up_items"]], ["new skills", "re-checks"])
        self.assertAlmostEqual(c["keep_up_points"], 10.0)
        self.assertAlmostEqual(c["room_points"], 10.0)
        self.assertEqual(c["weeks_central"], 2.5)
        self.assertEqual(c["start"], "2026-11-23T17:00:00Z")
        doc["keep_up_items"] = ["not", "a", "dict"]
        self.assertIsNone(loop_status.forecast_block(doc)["calculation"])

    def test_a_document_without_the_figures_is_none(self):
        self.assertIsNone(loop_status.forecast_block({"inputs": {}}))
        self.assertIsNone(loop_status.forecast_block(None))

    def test_the_loop_jobs_input_carries_only_their_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            (tree / "spend").mkdir()
            (tree / "spend" / "weekly.json").write_text(json.dumps(
                {"loop_jobs": {"as_of": iso(NOW), "points_per_week": 8.5, "usd_per_week": 1}}))
            out = loop_status.loop_jobs_input(tree, tree / "jobs.json")
            doc = json.loads(out.read_text())
            self.assertEqual(doc["loop_meter_points_per_week"], 8.5)
            self.assertEqual(doc["categories"], [])
            self.assertIsNone(loop_status.loop_jobs_input(tree / "none", tree / "x.json"))


class BasisWindowTests(unittest.TestCase):
    """The page can switch between basis windows (evals/forecast.yml), so
    `collect` precomputes each one (Adam, 2026-11-26)."""

    def windowed(self, days, keep_up_usd):
        doc = json.loads(json.dumps(FORECAST))
        doc["keep_up_usd_per_week"] = keep_up_usd
        doc["inputs"]["basis_window"] = {"days": days, "meter_days_covered": min(days, 24.0)}
        return doc

    def test_every_window_is_shown_and_the_default_is_named(self):
        doc = self.windowed(28, 70.0)
        doc["by_window"] = {"56": self.windowed(56, 63.0), "14": self.windowed(14, 77.0),
                            "28": self.windowed(28, 70.0)}
        got = loop_status.forecast_section(doc)
        self.assertEqual(got["basis_window_days"], 28)
        self.assertEqual(list(got["by_window"]), ["14", "28", "56"])
        self.assertAlmostEqual(got["by_window"]["14"]["keep_up_points_per_week"], 11.0)
        self.assertEqual(got["by_window"]["56"]["basis_meter_days"], 24.0)
        self.assertNotIn("by_window", got["by_window"]["28"])

    def test_a_document_from_before_the_window_still_shows(self):
        got = loop_status.forecast_section(json.loads(json.dumps(FORECAST)))
        self.assertEqual(got["by_window"], {})
        self.assertIsNone(got["basis_window_days"])
        self.assertIsNone(loop_status.forecast_section(None))

    def test_collect_runs_the_forecast_once_per_window(self):
        import forecast_catch_up
        basis = forecast_catch_up.load_basis(ROOT / "evals")
        seen = []

        def fake_main(argv):
            days = int(argv[argv.index("--basis-days") + 1])
            seen.append(days)
            out = Path(argv[argv.index("--out-json") + 1])
            out.write_text(json.dumps(self.windowed(days, 10.0 * days)), encoding="utf-8")
            return 0

        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch.object(loop_status, "fetch_gates", return_value=Path(tmp) / "g"), \
                unittest.mock.patch.object(loop_status, "shallow"), \
                unittest.mock.patch.object(loop_status, "loop_jobs_input", return_value=None), \
                unittest.mock.patch.object(forecast_catch_up, "main", side_effect=fake_main):
            out = loop_status.run_forecast(Path(tmp), Path(tmp), None, NOW)
            doc = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse((Path(tmp) / "forecast.tmp.json").exists())
        self.assertEqual(seen, basis["choices"])
        self.assertEqual(doc["inputs"]["basis_window"]["days"], basis["days"])
        self.assertEqual(sorted(doc["by_window"], key=int), [str(d) for d in basis["choices"]])
        self.assertEqual(doc["as_of"], loop_status.iso(NOW))
        self.assertEqual(loop_status.forecast_section(doc)["by_window"][str(basis["choices"][0])]
                         ["basis_window_days"], basis["choices"][0])

    def test_a_failed_window_keeps_the_previous_forecast(self):
        import forecast_catch_up
        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch.object(loop_status, "fetch_gates", return_value=Path(tmp) / "g"), \
                unittest.mock.patch.object(loop_status, "shallow"), \
                unittest.mock.patch.object(loop_status, "loop_jobs_input", return_value=None), \
                unittest.mock.patch.object(forecast_catch_up, "main", return_value=2):
            (Path(tmp) / "forecast.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(RuntimeError) as raised:
                loop_status.run_forecast(Path(tmp), Path(tmp), None, NOW)
            self.assertEqual((Path(tmp) / "forecast.json").read_text(encoding="utf-8"), "{}")
        self.assertIn("basis window", str(raised.exception))


@pytest.mark.real_loop_reserve
class StatusTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = Path(self._tmp.name)

    def counts(self):
        return {"fire_count": lambda now: (0, 0), "improve_count": lambda now: (0, 0)}

    def test_without_the_loop_reserve_the_guard_refuses_and_the_page_says_so(self):
        doc = loop_status.status_from_tree(self.tree, LIMITS, NOW, _args(), None, **self.counts())
        self.assertEqual(doc["guard"]["verdict"], "error")
        self.assertIn("loop reserve", doc["guard"]["why"])
        self.assertIsNone(doc["loop"])

    def test_loop_spend_is_the_guards_committed_plus_the_loop_jobs(self):
        (self.tree / "spend").mkdir()
        (self.tree / "spend" / "weekly.json").write_text(json.dumps(
            {"loop_jobs": {"as_of": iso(NOW - timedelta(hours=1)), "points_per_week": 9.0,
                           "usd_per_week": 60.0}}))
        args = _args(week_used=40.0, week_at=iso(NOW), week_resets=iso(RESETS))
        doc = loop_status.status_from_tree(self.tree, LIMITS, NOW, args, None, **self.counts())
        state = guard.live_state(self.tree, LIMITS, NOW, **self.counts())
        self.assertAlmostEqual(doc["loop"]["loop_jobs_points"], 9.0)
        self.assertAlmostEqual(doc["loop"]["used_points"], (state["committed"] + 0.09) * 100)
        self.assertAlmostEqual(doc["loop"]["cap_points"], 25.0)
        # No ingested reading: the guard holds, fails safe, while the live pace shows.
        self.assertEqual(doc["guard"]["verdict"], "pace_hold")
        self.assertEqual(doc["pace"]["source"], "live")
        self.assertIsNone(doc["guard_pace"])
        self.assertEqual(doc["week"]["resets_at"], iso(RESETS))
        self.assertEqual(doc["session"], {"plan": "ultra", "stop_pct": None, "hold": False})

    def test_estimated_spend_is_token_priced_runs_improve_and_jobs_so_far(self):
        # Adam, 2026-11-24: "Loop spend is shown as higher than all usage".
        # The guard's booked figure (overrun per run, the account-wide bound,
        # the jobs' whole week) is not spend; the estimate prices each run's
        # own calls, falls back to run_cost only for a run it cannot price,
        # and counts the jobs for the share of the week gone.
        since = guard.window_start(NOW)
        runs = [self.tree / "a", self.tree / "b"]
        priced = {runs[0]: {"points": 0.06}, runs[1]: None}
        state = base_state(loop_reserve=0.07, improve_matched_cost=0.02)
        with unittest.mock.patch.object(guard, "ingested_runs", return_value=runs), \
                unittest.mock.patch.object(guard, "run_points", side_effect=lambda r, *_: priced[r]), \
                unittest.mock.patch.object(guard, "run_cost", return_value=0.0015):
            spend = loop_status.estimated_spend(self.tree, LIMITS, NOW, since, state)
        gone = (NOW - since) / guard.WINDOW
        self.assertAlmostEqual(spend["evals"], 0.0006 + 0.0015)
        self.assertAlmostEqual(spend["improve"], 0.02)
        self.assertAlmostEqual(spend["jobs"], 0.07 * gone)
        self.assertAlmostEqual(spend["total"], 0.0006 + 0.0015 + 0.02 + 0.07 * gone)

    def test_the_document_carries_the_estimate_below_the_booked_figure(self):
        (self.tree / "spend").mkdir()
        (self.tree / "spend" / "weekly.json").write_text(json.dumps(
            {"loop_jobs": {"as_of": iso(NOW - timedelta(hours=1)), "points_per_week": 9.0,
                           "usd_per_week": 60.0}}))
        doc = loop_status.status_from_tree(self.tree, LIMITS, NOW, _args(), None, **self.counts())
        loop = doc["loop"]
        gone = (NOW - guard.window_start(NOW)) / guard.WINDOW
        self.assertAlmostEqual(loop["loop_jobs_so_far_points"], 9.0 * gone)
        self.assertAlmostEqual(loop["estimated_points"],
                               loop["eval_estimated_points"] + loop["improve_estimated_points"]
                               + loop["loop_jobs_so_far_points"])
        self.assertLess(loop["estimated_points"], loop["used_points"])

    def test_main_prints_one_json_document(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = loop_status.main(["status", "--results-tree", str(self.tree)], now=NOW,
                                    **self.counts())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["schema"], loop_status.SCHEMA)


def _args(**values):
    base = {"week_used": None, "week_at": None, "week_resets": None}
    base.update(values)
    return type("Args", (), base)()


if __name__ == "__main__":
    unittest.main()
