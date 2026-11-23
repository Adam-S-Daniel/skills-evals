"""The catch-up forecast prices subjects deep-first from the planner's own
projection (scripts/forecast_catch_up.py). Synthetic verdict documents only:
no results tree, no network, no clock."""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
import forecast_catch_up as fc  # noqa: E402

POLICY = {"max_runs_per_cell": 20, "recheck_weeks": 8, "recheck_weeks_high": 4}
CTX = {"policy": POLICY, "guidance_policy": POLICY}


def projection(**kw):
    out = {"pairs": 5, "keep": 5, "remove": math.inf, "remaining": 12,
           "past_cap": False, "blocked": None}
    out.update(kw)
    return out


class CellEstimate(unittest.TestCase):
    def estimate(self, proj, pairs=8):
        cell = {"skill": "s", "model": "m", "pairs": pairs, "class": "insufficient"}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=proj):
            return fc.cell_estimate(cell, CTX, prior_pairs=15)

    def test_unprojected_cell_costs_the_prior_at_most_its_remaining(self):
        est = self.estimate(None, pairs=8)
        self.assertEqual((est["central"], est["high"], est["keep_route"]), (12, 12, False))

    def test_projection_is_capped_and_keep_route_named(self):
        est = self.estimate(projection(pairs=4.2, keep=4.2))
        self.assertEqual((est["central"], est["high"], est["keep_route"]), (5, 12, True))

    def test_past_cap_runs_to_the_cap(self):
        est = self.estimate(projection(pairs=40, keep=math.inf, remove=40, past_cap=True))
        self.assertEqual((est["central"], est["keep_route"]), (12, False))

    def test_a_crossed_remove_test_is_no_keep_route(self):
        est = self.estimate(projection(pairs=0, keep=3, remove=0))
        self.assertFalse(est["keep_route"])

    def test_blocked_on_cli_versions_costs_nothing_now(self):
        est = self.estimate(projection(pairs=math.inf, keep=math.inf, remove=math.inf,
                                       blocked="cli"))
        self.assertEqual(est["central"], 0)


class SubjectEstimate(unittest.TestCase):
    def cell(self, central, high, keep):
        return {"model": "m", "central": central, "low": central, "high": high,
                "keep_route": keep, "projected": True}

    def test_a_keep_route_ends_the_subject_at_its_cheapest_cell(self):
        s = fc.subject_estimate([self.cell(9, 20, True), self.cell(4, 20, True),
                                 self.cell(15, 20, False)])
        self.assertEqual((s["route"], s["central"], s["high"]), ("keep", 4, 60))

    def test_a_removal_needs_every_cell(self):
        s = fc.subject_estimate([self.cell(9, 20, False), self.cell(15, 20, False)])
        self.assertEqual((s["route"], s["central"], s["high"]), ("remove-or-cap", 24, 40))

    def test_keep_route_prices_only_its_best_cell(self):
        s = fc.subject_estimate([self.cell(10, 20, True), self.cell(15, 20, False)])
        self.assertAlmostEqual(fc.subject_usd(s, {"m": 1.0}, 0.5, "central"), 15.0)
        self.assertAlmostEqual(fc.subject_usd(s, {"m": 1.0}, 0.5, "high"), 60.0)


class WeeksToClear(unittest.TestCase):
    def test_room_after_keep_up(self):
        self.assertEqual(fc.weeks_to_clear(300, 200, 100), 3.0)

    def test_never_when_keep_up_takes_the_capacity(self):
        self.assertTrue(math.isinf(fc.weeks_to_clear(300, 200, 200)))

    def test_nothing_to_clear(self):
        self.assertEqual(fc.weeks_to_clear(0, 100, 500), 0.0)


class PairCost(unittest.TestCase):
    def test_mean_cost_per_pair_by_model(self):
        gates = {"skills": {"a": {"cells": [
            {"model": "x", "pairs": 4, "cost_usd": 4.0},
            {"model": "x", "pairs": 6, "cost_usd": 8.0},
            {"model": "y", "pairs": 0, "cost_usd": 1.0}]}}}
        self.assertEqual(fc.pair_usd(gates), {"x": 1.2})


class Forecast(unittest.TestCase):
    """One keep-route subject and one removal subject, end to end."""

    GATES = {
        "policy": POLICY, "guidance_policy": POLICY, "roster_models": ["m"],
        "skills": {"kept": {"verdict": "keep", "cells": [
            {"model": "m", "pairs": 10, "cost_usd": 10.0, "class": "benefit"}]}},
        "guidance": {"skipped-one": {"verdict": "keep", "cells": []}},
    }
    CELLS = [
        {"skill": "a", "model": "m", "pairs": 0, "class": "insufficient"},
        {"skill": "b", "model": "m", "pairs": 0, "class": "insufficient"},
        {"skill": "b", "model": "m", "pairs": 0, "class": "missing"},
    ]
    BUDGET = {"weekly_cap": 0.25, "legacy_usd_per_point": 1 / 0.15}
    BATCH = {"pairs_per_cell": 15, "rates": {"skill": 1.0, "guidance": 1.0}}

    def run_forecast(self, cells=None, gates=None, budget=None, measured_rate=None,
                     **assumptions):
        def proj(cell, ctx):
            if cell["skill"] == "a":
                return projection(pairs=4, keep=4, remove=math.inf, remaining=20)
            return projection(pairs=10, keep=math.inf, remove=10, remaining=20)
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", side_effect=proj), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            return fc.forecast(gates or self.GATES, cells or self.CELLS, budget or self.BUDGET,
                               self.BATCH, None,
                               {"fire_overhead_usd": 0.0, **assumptions},
                               frozenset({"skipped-one"}),
                               measured_rate=measured_rate)

    def test_automatic_spend_breaks_down_non_eval_points(self):
        automatic = {"as_of": "2026-11-15T18:00:00+00:00", "unmeasured": ["Job x"],
                     "categories": [{"label": "Dashboard", "meter_usd_per_week": 20 / 0.15},
                                    {"label": "Evals", "meter_usd_per_week": 0.0}]}
        budget = {**self.BUDGET, "stop_when_account_above": 0.8}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(self.GATES, self.CELLS, budget, self.BATCH, None,
                              {"fire_overhead_usd": 0.0, "interactive_points_per_week": 50.0},
                              frozenset({"skipped-one"}), None, automatic)
        # $20/0.15 a week at $1/0.15 a point is 20 points; a $0 category is left out.
        self.assertEqual(doc["inputs"]["non_eval_points_breakdown"],
                         {"Dashboard": 20.0, "Interactive threads and local sessions": 50.0})
        self.assertAlmostEqual(doc["inputs"]["assumptions"]["non_eval_points_per_week"], 70.0)
        # The account stop (80) less 70 points of other use leaves evals 10 of their 25.
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 10.0)
        self.assertEqual(doc["inputs"]["automatic_unmeasured_jobs"], 1)

    def test_each_scheduled_task_is_listed_in_points(self):
        # Adam, 2026-11-20: "add individual scheduled tasks".
        automatic = {"categories": [{"id": "dash", "label": "Dashboard",
                                     "meter_points_per_week": 9.0},
                                    {"id": "personal", "label": "Personal",
                                     "meter_points_per_week": 4.0}],
                     "jobs": [
                         {"kind": "scheduled task", "name": "Small job", "category": "dash",
                          "in_loop": True, "lane": "meter", "model": "m",
                          "fires_per_week": 7.0, "points_per_week": 1.0},
                         {"kind": "scheduled task", "name": "Dashboard refresh",
                          "category": "dash", "in_loop": True, "lane": "meter", "model": "m",
                          "fires_per_week": 7.0, "points_per_week": 8.0},
                         {"kind": "scheduled task", "name": "Private errand",
                          "category": "personal", "in_loop": False, "lane": "meter",
                          "model": "m", "fires_per_week": 1.0, "points_per_week": 4.0},
                         {"kind": "scheduled task", "name": "Priced in dollars",
                          "category": "dash", "in_loop": True, "lane": "meter",
                          "fires_per_week": 1.0, "points_per_week": None,
                          "usd_per_week": 3 / 0.15},
                         {"kind": "scheduled task", "name": "Unmeasured", "category": "dash",
                          "in_loop": True, "lane": "meter", "points_per_week": None},
                         {"kind": "scheduled task", "name": "Eval fire", "category": "dash",
                          "in_loop": True, "lane": "eval_cap", "points_per_week": 5.0},
                         {"kind": "workflow", "name": "A workflow", "category": "dash",
                          "in_loop": True, "lane": "meter", "points_per_week": 2.0}]}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(self.GATES, self.CELLS, self.BUDGET, self.BATCH, None,
                              {"fire_overhead_usd": 0.0}, frozenset({"skipped-one"}),
                              None, automatic)
        tasks = doc["inputs"]["scheduled_tasks"]
        self.assertEqual([(t["task"], t["points_per_week"]) for t in tasks], [
            ("Dashboard refresh", 8.0), ("Personal (outside the loop)", 4.0),
            ("Priced in dollars", 3.0), ("Small job", 1.0), ("Unmeasured", None)])
        # Nothing outside the loop is named, nor its model.
        self.assertNotIn("Private errand", json.dumps(doc))
        self.assertIsNone(tasks[1]["model"])

    def test_loop_jobs_spend_from_the_eval_cap(self):
        # Adam, 2026-11-15: the loop's automatic jobs fit in the same 25 points.
        automatic = {"loop_meter_usd_per_week": 15 / 0.15,
                     "categories": [{"label": "Dashboard", "meter_usd_per_week": 15 / 0.15}]}
        for given, cap in [({}, 10.0), ({"loop_jobs_in_cap": 0.0}, 25.0)]:
            with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                    mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
                doc = fc.forecast(self.GATES, self.CELLS, self.BUDGET, self.BATCH, None,
                                  {"fire_overhead_usd": 0.0, **given},
                                  frozenset({"skipped-one"}), None, automatic)
            self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], cap)
            self.assertAlmostEqual(doc["inputs"]["loop_jobs_points_per_week"], 15.0)

    def test_estimated_points_win_over_dollars_at_a_rate(self):
        # A breakdown with points (from each fire's token counts) is read as points, its dollars ignored.
        automatic = {"loop_meter_usd_per_week": 999.0, "loop_meter_points_per_week": 4.0,
                     "categories": [{"label": "Dashboard", "meter_usd_per_week": 999.0,
                                     "meter_points_per_week": 6.0}]}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(self.GATES, self.CELLS, self.BUDGET, self.BATCH, None,
                              {"fire_overhead_usd": 0.0, "interactive_points_per_week": 1.0},
                              frozenset({"skipped-one"}), None, automatic)
        self.assertEqual(doc["inputs"]["non_eval_points_breakdown"],
                         {"Dashboard": 6.0, "Interactive threads and local sessions": 1.0})
        self.assertAlmostEqual(doc["inputs"]["loop_jobs_points_per_week"], 4.0)

    def test_given_non_eval_points_win_over_the_breakdown(self):
        automatic = {"categories": [{"label": "Dashboard", "meter_usd_per_week": 3.0}]}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(self.GATES, self.CELLS, self.BUDGET, self.BATCH, None,
                              {"fire_overhead_usd": 0.0, "non_eval_points_per_week": 5.0,
                               "interactive_points_per_week": 50.0},
                              frozenset({"skipped-one"}), None, automatic)
        self.assertEqual(doc["inputs"]["assumptions"]["non_eval_points_per_week"], 5.0)

    def test_backlog_capacity_and_weeks(self):
        doc = self.run_forecast(new_skills_per_week=0.0, new_sections_per_week=0.0)
        # $1 a pair: subject a keeps at 4 pairs, subject b needs both cells (20).
        self.assertAlmostEqual(doc["backlog_usd"]["central"], 24.0)
        self.assertAlmostEqual(doc["capacity_usd_per_week"]["plan_central"], 25 / 0.15)
        # One kept subject outside the skipped section, re-checked every 8 weeks.
        self.assertEqual(doc["kept_subjects"], 1)
        weeks = doc["scenarios"]["plan_cap_only"]["weeks_central"]
        self.assertAlmostEqual(weeks, 24.0 / (25 / 0.15 - doc["keep_up_usd_per_week"]))

    def test_rechecks_are_priced_per_kept_cell_at_its_projection_and_age(self):
        item = "re-checks of kept subjects"
        # No projection: the cell's re-check is priced at the cap, $1 a pair,
        # every recheck_weeks.
        doc = self.run_forecast()
        self.assertAlmostEqual(doc["keep_up_items"][item],
                               POLICY["max_runs_per_cell"] / POLICY["recheck_weeks"])
        cell = {**self.GATES["skills"]["kept"]["cells"][0], "recheck": {"projected_pairs": 6}}
        gates = {**self.GATES, "skills": {"kept": {"verdict": "keep", "cells": [cell]}}}
        doc = self.run_forecast(gates=gates)
        self.assertAlmostEqual(doc["keep_up_items"][item], 6 / POLICY["recheck_weeks"])
        # A high-stakes subject is re-checked at recheck_weeks_high.
        table = {("skill", "kept"): {"stakes": "high"}}
        got = fc.recheck_usd_per_week(gates, {"m": 1.0}, 0.0, frozenset(), table)
        self.assertAlmostEqual(got, 6 / POLICY["recheck_weeks_high"])

    def test_new_git_hooks_cost_no_eval_dollars(self):
        doc = self.run_forecast(new_hooks_per_week=5.0)
        self.assertEqual(doc["keep_up_items"]["new git hooks"], 0.0)

    def test_never_when_keep_up_exceeds_capacity(self):
        doc = self.run_forecast(new_fixtures_per_week_open=100.0)
        self.assertTrue(math.isinf(doc["scenarios"]["plan_cap_only"]["weeks_central"]))

    def test_a_kept_subjects_open_cells_wait_for_the_recheck(self):
        cells = self.CELLS + [{"skill": "kept", "model": "m", "pairs": 0,
                               "class": "insufficient", "verdict": "keep"}]
        doc = self.run_forecast(new_skills_per_week=0.0, new_sections_per_week=0.0,
                                cells=cells)
        self.assertNotIn("kept", {r["subject"] for r in doc["subjects"]})
        provisional = cells[:-1] + [{**cells[-1], "provisional_keep": True}]
        doc = self.run_forecast(new_skills_per_week=0.0, new_sections_per_week=0.0,
                                cells=provisional)
        self.assertIn("kept", {r["subject"] for r in doc["subjects"]})

    def test_a_standing_keep_needs_no_re_proof_after_a_rest_change(self):
        guidance_cells = [{"skill": "a", "section": "sec", "model": "m", "pairs": 0,
                           "class": "insufficient"}]
        item = "guidance keeps re-proved after a rest change"
        doc = self.run_forecast(guidance_rest_changes_per_week=1.0, cells=guidance_cells)
        self.assertGreater(doc["keep_up_items"][item], 0)
        gates = {**self.GATES, "guidance_policy": {**POLICY, "keep_stands_until_recheck": True}}
        doc = self.run_forecast(guidance_rest_changes_per_week=1.0, cells=guidance_cells,
                                gates=gates)
        self.assertEqual(doc["keep_up_items"][item], 0)

    def test_other_meter_use_can_cap_the_eval_points(self):
        budget = {**self.BUDGET, "stop_when_account_above": 0.80}
        doc = self.run_forecast(non_eval_points_per_week=70.0, budget=budget)
        self.assertAlmostEqual(doc["capacity_usd_per_week"]["plan_central"], 10 / 0.15)
        doc = self.run_forecast(non_eval_points_per_week=100.0, budget=budget)
        self.assertEqual(doc["capacity_usd_per_week"]["plan_central"], 0)
        doc = self.run_forecast(non_eval_points_per_week=20.0, budget=budget)
        self.assertAlmostEqual(doc["capacity_usd_per_week"]["plan_central"], 25 / 0.15)



class Arrivals(unittest.TestCase):
    """The arrival rates come from arrivals/targets.json (scripts/
    target_arrivals.py), never a hand count, unless the run overrides them."""

    NOW = fc.datetime(2026, 11, 16, tzinfo=fc.timezone.utc)

    def doc(self, **kw):
        rate = {"complete": True, "added_per_week": 1.5, "eligible_share": 0.25}
        out = {"schema": 1, "as_of": "2026-11-15T10:00:00Z",
               "rates": {"git-hook": {**rate, "eligible_share": None, "added_per_week": 3.0},
                         "skill": dict(rate),
                         "guidance-section": {**rate, "added_per_week": 1.0,
                                              "eligible_share": 0.4}}}
        out.update(kw)
        return out

    def test_every_rate_is_taken_from_a_fresh_document(self):
        self.assertEqual(fc.arrival_assumptions(self.doc(), self.NOW), {
            "new_hooks_per_week": 3.0, "new_skills_per_week": 1.5, "first_use_share": 0.25,
            "new_sections_per_week": 1.0, "evaluated_section_share": 0.4})

    def test_an_incomplete_kind_or_null_rate_is_left_out(self):
        doc = self.doc()
        doc["rates"]["skill"]["complete"] = False
        got = fc.arrival_assumptions(doc, self.NOW)
        self.assertNotIn("new_skills_per_week", got)
        self.assertNotIn("first_use_share", got)
        self.assertEqual(got["new_sections_per_week"], 1.0)

    def test_a_stale_or_missing_document_gives_nothing(self):
        self.assertEqual(fc.arrival_assumptions(self.doc(as_of="2026-11-01T00:00:00Z"),
                                                self.NOW), {})
        self.assertEqual(fc.arrival_assumptions(None, self.NOW), {})
        self.assertEqual(fc.arrival_assumptions(self.doc(schema=2), self.NOW), {})
        future = self.doc(as_of="2026-11-17T00:00:00Z")
        self.assertEqual(fc.arrival_assumptions(future, self.NOW), {})
        self.assertEqual(fc.arrival_assumptions(self.doc(as_of="2026-11-15T10:00:00"),
                                                self.NOW), {})

    def test_a_non_number_rate_is_left_out(self):
        doc = self.doc()
        doc["rates"]["git-hook"]["added_per_week"] = True
        self.assertNotIn("new_hooks_per_week", fc.arrival_assumptions(doc, self.NOW))

    def test_the_run_overrides_and_sources_are_recorded(self):
        merged, sources = fc.merge_assumptions({"new_skills_per_week": 2.0},
                                               {"new_skills_per_week": 1.5,
                                                "new_hooks_per_week": 3.0})
        self.assertEqual(merged, {"new_skills_per_week": 2.0, "new_hooks_per_week": 3.0})
        self.assertEqual(sources, {"new_skills_per_week": "assumptions",
                                   "new_hooks_per_week": "arrivals/targets.json"})

    def test_every_arrival_key_is_an_assumption(self):
        self.assertLessEqual(set(fc.ARRIVAL_KEYS), set(fc.ASSUMPTION_KEYS))
        import target_arrivals
        self.assertEqual({kind for kind, _ in fc.ARRIVAL_KEYS.values()},
                         set(target_arrivals.KINDS))


class MeterNonEval(unittest.TestCase):
    """The non-eval total measured from the account meter's history."""

    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    END = _dt(2026, 11, 15, 12, tzinfo=_tz.utc)

    def at(self, hours_before):
        return self.END - self._td(hours=hours_before)

    def test_whole_week_less_evals_capped_at_the_rise_while_they_ran(self):
        # Week from the Nov 9 reset to END (Nov 15 noon, 5.79 days). Meter
        # 1 -> 39 while evals ran (calibrated at 50, so only 38 come off),
        # then 39 -> 94; a drop is skipped.
        reset = self._dt(2026, 11, 9, 17, tzinfo=self._tz.utc)
        h = lambda x: reset + self._td(hours=x)  # noqa: E731
        readings = [(h(0), 1.0), (h(57), 39.0), (h(58), 30.0), (h(59), 39.0), (self.END, 94.0)]
        runs = [(h(1), 20.0), (h(55), 30.0), (reset - self._td(hours=2), 99.0)]
        m = fc.meter_non_eval_points(readings, runs, self.END)
        self.assertEqual((m["meter_rise_points"], m["eval_points_calibrated"], m["eval_points"]),
                         (102.0, 50.0, 38.0))
        days = (self.END - reset).total_seconds() / 86400
        self.assertAlmostEqual(m["points_per_week"], 64.0 * 7 / days)

    def test_a_young_week_measures_the_week_before(self):
        reset = self._dt(2026, 11, 9, 17, tzinfo=self._tz.utc)
        readings = [(reset - self._td(days=7), 0.0), (reset - self._td(hours=1), 70.0),
                    (reset + self._td(hours=5), 2.0)]
        m = fc.meter_non_eval_points(readings, [], reset + self._td(days=1))
        self.assertAlmostEqual(m["points_per_week"], 70.0 * 7 / (7 - 1 / 24))

    def test_too_few_readings(self):
        self.assertIsNone(fc.meter_non_eval_points([(self.at(1), 3.0)], [], self.END))

    def test_measured_total_less_automatic_is_interactive(self):
        automatic = {"categories": [{"label": "Dashboard", "meter_usd_per_week": 20 / 0.15}]}
        gates = Forecast.GATES
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(gates, Forecast.CELLS, Forecast.BUDGET, Forecast.BATCH, None,
                              {"fire_overhead_usd": 0.0}, frozenset({"skipped-one"}), None,
                              automatic, {"points_per_week": 75.0})
        self.assertAlmostEqual(
            doc["inputs"]["non_eval_points_breakdown"]["Interactive threads and local sessions"],
            55.0)
        self.assertAlmostEqual(doc["inputs"]["assumptions"]["non_eval_points_per_week"], 75.0)


class PaceHoldReplay(unittest.TestCase):
    """The pace hold lets evals fill the gap whenever other use runs under
    the pace line, so their week depends on when other use comes, not only
    its total (Adam, 2026-11-23)."""

    START = fc.RESET_ANCHOR + fc.timedelta(days=14)  # after the Nov 4 manual reset

    def h(self, hours):
        return self.START + fc.timedelta(hours=hours)

    def curve(self, shape):
        """A week's curve every 5 minutes from `shape(hours) -> points`."""
        steps = int(168 * 12)
        return {"week_start": self.START.isoformat(), "total": shape(168.0),
                "curve": [(k / 12, shape(k / 12)) for k in range(steps)]}

    def test_late_heavy_use_still_leaves_early_room_past_the_stop(self):
        # Nothing for three days, then 90 points: above the 80 stop over the
        # week, yet the line reaches 80 * 72 / 168 = 34.3 before use starts.
        late = self.curve(lambda t: 0.0 if t < 72 else 90.0 * (t - 72) / 96)
        room = fc.pace_hold_room([late], 90.0, 80.0, 25.0)
        self.assertAlmostEqual(room["points"], 25.0)  # the cap binds first
        self.assertLess(room["weeks"][0]["first_eval_hours"], 3)
        uncapped = fc.pace_hold_room([late], 90.0, 80.0, 100.0)
        self.assertAlmostEqual(uncapped["points"], 80.0 * 72 / 168 - 1, delta=0.5)

    def test_steady_use_over_the_line_leaves_nothing(self):
        steady = self.curve(lambda t: 90.0 * t / 168 + 1.0)
        self.assertEqual(fc.pace_hold_room([steady], 90.0, 80.0, 25.0)["points"], 0.0)

    def test_the_week_is_scaled_to_the_other_use_assumed(self):
        late = self.curve(lambda t: 0.0 if t < 72 else 90.0 * (t - 72) / 96)
        heavy = fc.pace_hold_room([late], 180.0, 80.0, 100.0)["points"]
        light = fc.pace_hold_room([late], 45.0, 80.0, 100.0)["points"]
        self.assertLess(heavy, light)
        self.assertEqual(fc.pace_hold_room([], 80.0, 80.0, 25.0), None)

    def test_median_week_with_its_range(self):
        late = self.curve(lambda t: 0.0 if t < 72 else 90.0 * (t - 72) / 96)
        steady = self.curve(lambda t: 90.0 * t / 168 + 1.0)
        room = fc.pace_hold_room([late, steady, late], 90.0, 80.0, 25.0)
        self.assertEqual((room["points"], room["low"], room["high"]), (25.0, 0.0, 25.0))

    def test_curves_take_off_evals_never_fall_and_skip_partial_weeks(self):
        readings = [(self.h(0), 0.0), (self.h(24), 10.0), (self.h(48), 9.0),
                    (self.h(167), 60.0)]
        runs = [(self.h(0), 4.0), (self.h(-1), 50.0)]
        now = self.START + fc.timedelta(days=7, hours=1)
        curves = fc.non_eval_week_curves(readings, runs, now)
        self.assertEqual(len(curves), 1)
        levels = [p for _, p in curves[0]["curve"]]
        self.assertEqual(levels, sorted(levels))
        at = dict(curves[0]["curve"])
        self.assertAlmostEqual(at[12.0], 5.0 - 4.0)  # meter 5 less 4 eval points
        self.assertAlmostEqual(at[24.0], 6.0)
        self.assertEqual(curves[0]["total"], levels[-1])
        # A week whose readings stop a day short is not whole.
        short = [r for r in readings if r[0] < self.h(140)]
        self.assertEqual(fc.non_eval_week_curves(short, runs, now), [])

    def test_a_manual_reset_week_is_left_out(self):
        readings = [(self.h(0), 0.0), (self.h(167), 60.0)]
        with mock.patch.object(fc.allowance_guard, "MANUAL_RESETS", (self.h(30),)):
            self.assertEqual(fc.non_eval_week_curves(readings, [], self.h(169)), [])
        self.assertEqual(len(fc.non_eval_week_curves(readings, [], self.h(169))), 1)

    def test_forecast_replays_the_hold_and_keeps_the_flat_figure(self):
        late = self.curve(lambda t: 0.0 if t < 72 else 90.0 * (t - 72) / 96)
        budget = {**Forecast.BUDGET, "stop_when_account_above": 0.8}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(Forecast.GATES, Forecast.CELLS, budget, Forecast.BATCH, None,
                              {"fire_overhead_usd": 0.0, "non_eval_points_per_week": 90.0},
                              frozenset({"skipped-one"}), week_curves=[late])
        replay = doc["inputs"]["pace_replay"]
        self.assertEqual(replay["flat_points"], 0.0)
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 25.0)
        self.assertAlmostEqual(replay["points"], 25.0)


class EvalRunPoints(unittest.TestCase):
    """Eval runs are counted at what the guard charges them, from tokens."""

    def tree(self, root: Path) -> Path:
        run = root / "routine-results" / "20261117T222133Z-5d1b13"
        run.mkdir(parents=True)
        (run / "cost_estimate.json").write_text(json.dumps({"points": 0.03}), encoding="utf-8")
        return root

    def test_token_points_win_over_the_calibrated_estimate(self):
        with tempfile.TemporaryDirectory() as d:
            tree = self.tree(Path(d))
            self.assertAlmostEqual(fc.eval_run_points(tree)[0][1], 3.0)
            with mock.patch.object(fc.allowance_guard, "run_points",
                                   return_value={"points": 1.1, "usd": 1.0, "from_tokens": True}):
                self.assertAlmostEqual(fc.eval_run_points(tree, 12.35)[0][1], 1.1)
            with mock.patch.object(fc.allowance_guard, "run_points",
                                   return_value={"points": 1.1, "usd": 1.0, "from_tokens": False}):
                self.assertAlmostEqual(fc.eval_run_points(tree, 12.35)[0][1], 3.0)


if __name__ == "__main__":
    unittest.main()


class EvalsRunFirst(unittest.TestCase):
    """Evals spend the fixed cap from the Monday reset, so the account stop
    binds only on other use that accrues while they do."""

    def run_forecast(self, **assumptions):
        budget = {**Forecast.BUDGET, "stop_when_account_above": 0.8}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            return fc.forecast(Forecast.GATES, Forecast.CELLS, budget, Forecast.BATCH, None,
                               {"fire_overhead_usd": 0.0, **assumptions},
                               frozenset({"skipped-one"}))

    def test_heavy_other_use_still_leaves_evals_the_cap_and_squeezes_the_owner(self):
        # 25 points at 1 an hour take 25 hours; 168 other points a week accrue
        # 25 meanwhile; 50 < 80, so the whole cap runs.
        doc = self.run_forecast(non_eval_points_per_week=168.0, eval_points_per_hour=1.0,
                                pace_hold=0.0)
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 25.0)
        sq = doc["inputs"]["owner_squeeze"]
        self.assertAlmostEqual(sq["week_total_points"], 193.0)
        self.assertAlmostEqual(sq["days_at_limit_before_reset"], 93.0 / 24.0)

    def test_slow_evals_meet_the_stop_part_way(self):
        # At 0.1 an hour, E + 168 * E / 16.8 = 80, so E = 80 / 11.
        doc = self.run_forecast(non_eval_points_per_week=168.0, eval_points_per_hour=0.1,
                                pace_hold=0.0)
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 80 / 11)

    def test_the_pace_hold_takes_the_stop_off_the_whole_week(self):
        # allowance_guard.py's pace hold (2026-11-20): evals no longer run
        # first, so 70 points of other use leave them 80 - 70, not the cap.
        doc = self.run_forecast(non_eval_points_per_week=70.0, eval_points_per_hour=1.0)
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 10.0)
        self.assertIsNone(doc["inputs"]["owner_squeeze"])
        self.assertIs(doc["inputs"]["assumptions"]["pace_hold"], True)

    def test_without_a_pace_the_stop_comes_off_the_whole_week(self):
        doc = self.run_forecast(non_eval_points_per_week=70.0)
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 10.0)
        self.assertIsNone(doc["inputs"]["owner_squeeze"])

    def test_pace_is_measured_from_weeks_that_reached_the_cap(self):
        reset = fc.RESET_ANCHOR
        runs = [(reset + fc.timedelta(hours=h), 5.0) for h in (1, 5, 10, 15, 20)]  # 25 by hour 20
        runs += [(reset + fc.timedelta(days=7, hours=1), 3.0)]  # a week that never reached it
        pace = fc.eval_pace(runs, 25.0, reset + fc.timedelta(days=14))
        self.assertEqual(pace, {"points_per_hour": 1.25, "weeks": 1})
        self.assertIsNone(fc.eval_pace(runs[-1:], 25.0, reset + fc.timedelta(days=14)))


class MeterRange(unittest.TestCase):
    """The usage endpoint rounds, so the rise is a range."""

    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    END = _dt(2026, 11, 15, 12, tzinfo=_tz.utc)

    def test_the_rise_is_a_range_beside_the_central_figure(self):
        reset = self._dt(2026, 11, 9, 17, tzinfo=self._tz.utc)
        h = lambda x: reset + self._td(hours=x)  # noqa: E731
        # 10 -> 30 -> 50 never falls (one run, 40 points read, truly 39 to 41);
        # the drop to 20 starts a second run, 20 -> 25 (4 to 6 points).
        readings = [(h(0), 10.0), (h(20), 30.0), (h(40), 50.0), (h(41), 20.0), (self.END, 25.0)]
        m = fc.meter_non_eval_points(readings, [], self.END)
        self.assertEqual(m["meter_rise_points"], 45.0)
        self.assertAlmostEqual(m["meter_rise_points_low"], 39.0 + 4.0)
        self.assertAlmostEqual(m["meter_rise_points_high"], 41.0 + 6.0)
        days = (self.END - reset).total_seconds() / 86400
        self.assertAlmostEqual(m["points_per_week_low"], 43.0 * 7 / days)
        self.assertAlmostEqual(m["points_per_week_high"], 47.0 * 7 / days)
        self.assertLess(m["points_per_week_low"], m["points_per_week"])
        self.assertLess(m["points_per_week"], m["points_per_week_high"])


def _trial_blocks(cost):
    return {"scope": "trial", "agent": {
        "calls": 1, "cost_usd": cost, "models": {"claude-sonnet-5-5": {
            "input_tokens": 1000, "output_tokens": 2000, "cache_read_input_tokens": 3000,
            "cache_creation_input_tokens": 400, "cost_usd": cost}}}}


class MeasuredRate(unittest.TestCase):
    """Eval dollars per point come from the ingested runs' token estimates."""

    def tree(self, runs):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for run_id, measured in runs.items():
            path = root / "routine-results" / run_id / "s" / "t1" / "summary.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"usage": {"measured": measured}}), encoding="utf-8")
        return root

    def test_dollars_over_the_estimates_points_with_its_range(self):
        import allowance_points
        root = self.tree({"20261030T100000Z-aaaaaa": _trial_blocks(2.0),
                          "20261030T110000Z-bbbbbb": _trial_blocks(3.0)})
        got = fc.measured_usd_per_point(root, 1 / 0.15)
        est = [allowance_points.estimate_blocks([_trial_blocks(c)]) for c in (2.0, 3.0)]
        points, low, high = (sum(e[k] for e in est) for k in ("points", "low", "high"))
        self.assertEqual(got["runs"], 2)
        self.assertAlmostEqual(got["central"], 5.0 / points)
        self.assertAlmostEqual(got["low"], 5.0 / high)
        self.assertAlmostEqual(got["high"], 5.0 / low)
        self.assertLessEqual(got["low"], got["central"])
        self.assertLessEqual(got["central"], got["high"])

    def test_a_run_not_priced_wholly_from_tokens_is_left_out_and_none_means_none(self):
        no_tokens = {"scope": "trial", "agent": {"calls": 1, "cost_usd": 1.0}}
        self.assertIsNone(fc.measured_usd_per_point(
            self.tree({"20261030T100000Z-aaaaaa": no_tokens}), 1 / 0.15))
        self.assertIsNone(fc.measured_usd_per_point(self.tree({}), 1 / 0.15))

    def test_forecast_uses_the_measured_rate_and_records_its_source(self):
        measured = {"central": 6.0, "low": 5.0, "high": 8.0, "runs": 3}
        doc = Forecast("run_forecast").run_forecast(measured_rate=measured)
        inputs = doc["inputs"]
        self.assertEqual(inputs["usd_per_point"], [5.0, 8.0])
        self.assertEqual(inputs["usd_per_point_central"], 6.0)
        self.assertIn("3 ingested runs priced from token counts", inputs["points_per_usd_source"])
        # Capacity at the cap's 25 points follows the measured range.
        self.assertAlmostEqual(doc["capacity_usd_per_week"]["plan_central"], 25 * 6.5)

    def test_an_assumption_still_wins_over_the_measured_rate(self):
        measured = {"central": 6.0, "low": 5.0, "high": 8.0, "runs": 3}
        doc = Forecast("run_forecast").run_forecast(
            measured_rate=measured, usd_per_point_low=4.0, usd_per_point_high=9.0)
        self.assertEqual(doc["inputs"]["usd_per_point"], [4.0, 9.0])

    def test_with_no_measured_rate_the_legacy_rate_is_the_fallback(self):
        doc = Forecast("run_forecast").run_forecast()
        self.assertEqual(doc["inputs"]["usd_per_point"], [1 / 0.15, 1 / 0.15])
        self.assertEqual(doc["inputs"]["points_per_usd_source"],
                         "evals/budget.yml legacy_usd_per_point")

