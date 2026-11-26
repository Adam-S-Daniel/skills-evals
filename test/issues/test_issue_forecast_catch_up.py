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
        m = fc.meter_non_eval_points(readings, runs, self.END, 7)
        self.assertEqual((m["meter_rise_points"], m["eval_points_calibrated"], m["eval_points"]),
                         (102.0, 50.0, 38.0))
        days = (self.END - reset).total_seconds() / 86400
        self.assertAlmostEqual(m["points_per_week"], 64.0 * 7 / days)

    def test_the_window_spans_a_weekly_reset_and_skips_its_fall(self):
        # 70 points the week before the reset, the fall to 0, then 2: a young
        # allowance week no longer stands alone for the whole rate.
        reset = self._dt(2026, 11, 9, 17, tzinfo=self._tz.utc)
        readings = [(reset - self._td(days=7), 0.0), (reset - self._td(hours=1), 70.0),
                    (reset + self._td(hours=5), 2.0)]
        m = fc.meter_non_eval_points(readings, [], reset + self._td(days=1), 28)
        self.assertEqual(m["meter_rise_points"], 72.0)
        self.assertAlmostEqual(m["days_covered"], 7 + 5 / 24)
        self.assertAlmostEqual(m["points_per_week"], 72.0 * 7 / (7 + 5 / 24))

    def test_readings_before_the_window_are_left_out(self):
        reset = self._dt(2026, 11, 9, 17, tzinfo=self._tz.utc)
        readings = [(reset - self._td(days=7), 0.0), (reset - self._td(hours=1), 70.0),
                    (reset + self._td(hours=5), 2.0), (reset + self._td(days=1), 9.0)]
        m = fc.meter_non_eval_points(readings, [], reset + self._td(days=1), 7)
        # 0 -> 70 starts before the window; inside, the reset's 0 -> 2 -> 9.
        self.assertEqual(m["meter_rise_points"], 9.0)
        self.assertEqual(m["readings"], 3)

    def test_too_few_readings(self):
        self.assertIsNone(fc.meter_non_eval_points([(self.at(1), 3.0)], [], self.END, 28))

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

    def test_mean_week_with_its_range(self):
        # The mean, not the median: a week changing moves the figure by its
        # share instead of a jump between middle weeks (2026-11-26).
        late = self.curve(lambda t: 0.0 if t < 72 else 90.0 * (t - 72) / 96)
        steady = self.curve(lambda t: 90.0 * t / 168 + 1.0)
        room = fc.pace_hold_room([late, steady, late], 90.0, 80.0, 25.0)
        self.assertAlmostEqual(room["points"], 50.0 / 3)
        self.assertEqual((room["low"], room["high"]), (0.0, 25.0))

    def test_curves_take_off_evals_never_fall_and_skip_partial_weeks(self):
        readings = [(self.h(0), 0.0), (self.h(24), 10.0), (self.h(48), 9.0),
                    (self.h(167), 60.0)]
        runs = [(self.h(0), 4.0), (self.h(-1), 50.0)]
        now = self.START + fc.timedelta(days=7, hours=1)
        curves = fc.non_eval_week_curves(readings, runs, now, 4)
        self.assertEqual(len(curves), 1)
        levels = [p for _, p in curves[0]["curve"]]
        self.assertEqual(levels, sorted(levels))
        at = dict(curves[0]["curve"])
        self.assertAlmostEqual(at[12.0], 5.0 - 4.0)  # meter 5 less 4 eval points
        self.assertAlmostEqual(at[24.0], 6.0)
        self.assertEqual(curves[0]["total"], levels[-1])
        # A week whose readings stop a day short is not whole.
        short = [r for r in readings if r[0] < self.h(140)]
        self.assertEqual(fc.non_eval_week_curves(short, runs, now, 4), [])

    def test_a_manual_reset_week_is_left_out(self):
        readings = [(self.h(0), 0.0), (self.h(167), 60.0)]
        with mock.patch.object(fc.allowance_guard, "MANUAL_RESETS", (self.h(30),)):
            self.assertEqual(fc.non_eval_week_curves(readings, [], self.h(169), 4), [])
        self.assertEqual(len(fc.non_eval_week_curves(readings, [], self.h(169), 4)), 1)

    def test_only_the_basis_windows_weeks_are_replayed(self):
        # Two whole weeks of readings; a one-week window replays the newer
        # only, and looks no further back when that week is left out.
        readings = [(self.h(0), 0.0), (self.h(167), 60.0), (self.h(168), 0.0),
                    (self.h(335), 30.0)]
        now = self.h(337)
        self.assertEqual([c["week_start"] for c in fc.non_eval_week_curves(readings, [], now, 2)],
                         [self.h(0).isoformat(), self.h(168).isoformat()])
        self.assertEqual([c["week_start"] for c in fc.non_eval_week_curves(readings, [], now, 1)],
                         [self.h(168).isoformat()])
        with mock.patch.object(fc.allowance_guard, "MANUAL_RESETS", (self.h(200),)):
            self.assertEqual(fc.non_eval_week_curves(readings, [], now, 1), [])

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
        self.assertEqual(doc["inputs"]["cap_steps"],
                         {"weekly_cap_points": 25.0, "after_loop_jobs_points": 25.0,
                          "after_account_stop_points": 25.0, "account_stop_basis": "pace_replay",
                          "account_stop_points": 80.0})
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 25.0)
        self.assertAlmostEqual(replay["points"], 25.0)

    def test_forecast_with_only_quiet_weeks_falls_back_to_the_flat_figure(self):
        # Every measured week under one point of other use: pace_hold_room
        # has no week to replay and returns None; the forecast must use the
        # flat stop-less-other figure, not fail on the missing replay.
        quiet = self.curve(lambda t: 0.5 * t / 168)
        budget = {**Forecast.BUDGET, "stop_when_account_above": 0.8}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            doc = fc.forecast(Forecast.GATES, Forecast.CELLS, budget, Forecast.BATCH, None,
                              {"fire_overhead_usd": 0.0, "non_eval_points_per_week": 60.0},
                              frozenset({"skipped-one"}), week_curves=[quiet])
        self.assertIsNone(doc["inputs"]["pace_replay"])
        self.assertAlmostEqual(doc["inputs"]["weekly_cap_points"], 20.0)


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


class OpenSubjectsSkipWhatTheRulesDoNotTest(unittest.TestCase):
    """Open subjects are only those a fire can still move (Adam, 2026-11-23)."""

    def test_a_subject_whose_only_cell_is_at_its_cap_is_not_open(self):
        cells = [{"skill": "capped", "model": "m", "pairs": 20, "class": "insufficient"},
                 {"skill": "open", "model": "m", "pairs": 3, "class": "insufficient"},
                 {"skill": "half", "model": "m", "pairs": 20, "class": "insufficient"},
                 {"skill": "half", "model": "n", "pairs": 2, "class": "insufficient"}]
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", return_value=None):
            got = fc.open_subjects(CTX, cells, prior_pairs=15)
        self.assertEqual(sorted(got), [("skill", "half"), ("skill", "open")])
        self.assertEqual(got[("skill", "half")]["cells"][0]["model"], "n")

    def test_a_cap_extension_keeps_the_cell_open(self):
        cell = {"skill": "ext", "model": "m", "pairs": 20, "class": "insufficient"}
        with mock.patch.object(fc.plan_week, "pairs_to_verdict",
                               return_value=projection(remaining=10)):
            self.assertIn(("skill", "ext"), fc.open_subjects(CTX, [cell], prior_pairs=15))

    def test_an_unreadable_guidance_checkout_fails_and_says_why(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch("sys.stderr") as err:
            with self.assertRaises(SystemExit) as raised:
                fc.main(["--gates", str(Path(d) / "g.json"), "--results-tree", d,
                         "--as-of", "2026-11-23T00:00:00Z", "--guidance", d,
                         "--out-json", str(Path(d) / "o.json")])
        self.assertEqual(raised.exception.code, 2)
        said = "".join(str(c.args[0]) for c in err.write.call_args_list)
        self.assertIn("agents-md/eval-coverage.yml", said)
        self.assertIn("would count as open subjects", said)

    def test_guidance_is_required(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            fc.main(["--gates", "g", "--results-tree", ".", "--as-of", "2026-11-23T00:00:00Z",
                     "--out-json", "o"])


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
        m = fc.meter_non_eval_points(readings, [], self.END, 7)
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



class BasisWindow(unittest.TestCase):
    """Every measured rate is averaged over a basis window set once in
    evals/forecast.yml (Adam, 2026-11-26: Keep-up and eval capacity were too
    jumpy; "consider allowing choosing duration of basis")."""

    # Mid-week (four days after a Monday reset), with 35 days of readings
    # that start after the 2026-11-04 manual reset.
    END = fc.RESET_ANCHOR + fc.timedelta(days=53)

    def config(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        if text is not None:
            (Path(tmp.name) / "forecast.yml").write_text(text, encoding="utf-8")
        return Path(tmp.name)

    def test_the_default_window_is_one_of_the_choices_in_evals_forecast_yml(self):
        basis = fc.load_basis(ROOT / "evals")
        self.assertIn(basis["days"], basis["choices"])
        self.assertEqual(basis["choices"], sorted(basis["choices"]))
        self.assertTrue(all(fc.basis_days_ok(d) for d in basis["choices"]))

    def test_a_missing_or_bad_setting_fails_and_says_which(self):
        cases = {None: "cannot read the basis window",
                 "basis_window_choices: [14, 28]\n": "basis_window_days is missing",
                 "basis_window_days: 28\n": "basis_window_choices is missing",
                 "basis_window_days: 3\nbasis_window_choices: [3]\n": "7 to 999",
                 "basis_window_days: 28\nbasis_window_choices: [28, 1000]\n": "7 to 999",
                 "basis_window_days: 28\nbasis_window_choices: [7, 8, 9, 10, 11, 12, 13, 28, 56]\n":
                     "at most 8",
                 "basis_window_days: 28.5\nbasis_window_choices: [14]\n": "whole number",
                 "basis_window_days: 28\nbasis_window_choices: [14, 56]\n": "not one of",
                 "basis_window_days: 28\nbasis_window_choices: [28, 28]\n": "distinct",
                 "- 28\n": "not a mapping"}
        for text, said in cases.items():
            with self.subTest(text=text), self.assertRaises(fc.BasisError) as raised:
                fc.load_basis(self.config(text))
            self.assertIn(said, str(raised.exception))
            self.assertIn("forecast.yml", str(raised.exception))

    def test_main_fails_descriptively_without_the_setting(self):
        evals = self.config("basis_window_choices: [28]\n")
        with mock.patch("sys.stderr") as err, self.assertRaises(SystemExit) as raised:
            fc.main(["--gates", "g", "--results-tree", ".", "--as-of", "2026-11-23T00:00:00Z",
                     "--guidance", ".", "--evals-dir", str(evals), "--out-json", "o"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("basis_window_days is missing",
                      "".join(str(c.args[0]) for c in err.write.call_args_list))

    def test_the_flag_must_be_whole_days_of_at_least_a_week(self):
        with mock.patch("sys.stderr") as err, self.assertRaises(SystemExit) as raised:
            fc.main(["--gates", "g", "--results-tree", ".", "--as-of", "2026-11-23T00:00:00Z",
                     "--guidance", ".", "--basis-days", "3", "--out-json", "o"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--basis-days 3", "".join(str(c.args[0]) for c in err.write.call_args_list))

    # --- the meter: steady use with a daily burst, read every 5 minutes ----

    def readings(self, end, burst_at=None, burst=0.0):
        """Whole-percent `seven_day` readings every 5 minutes for 35 days to
        `end`: 6 points between 18:00 and 22:00 UTC each day, 0.1 an hour
        otherwise (about 59 a week), restarting from 0 at each weekly reset;
        `burst` more points in the hour after `burst_at`."""
        out, used, t = [], 0.0, end - fc.timedelta(days=35)
        step = fc.timedelta(minutes=5)
        while t <= end:
            hour = t.hour
            used += (1.5 if 18 <= hour < 22 else 0.1) / 12
            if burst_at is not None and burst_at <= t < burst_at + fc.timedelta(hours=1):
                used += burst / 12
            if (t - fc.RESET_ANCHOR) % fc.WEEK < step:
                used = 0.0
            out.append((t, float(math.floor(used + 0.5))))
            t += step
        return out

    def figures(self, readings, end, days):
        other = fc.meter_non_eval_points(readings, [], end, days)["points_per_week"]
        curves = fc.non_eval_week_curves(readings, [], end, days // 7)
        return other, fc.pace_hold_room(curves, other, 80.0, 25.0)["points"]

    def test_one_new_reading_moves_neither_rate_nor_capacity_by_more_than_its_share(self):
        before = self.readings(self.END)
        later = self.END + fc.timedelta(minutes=5)
        after = before + [(later, before[-1][1] + 1.0)]  # one reading, a point higher
        other0, cap0 = self.figures(before, self.END, 28)
        other1, cap1 = self.figures(after, later, 28)
        self.assertGreater(other0, 50)
        self.assertGreater(cap0, 1)
        # A point over 28 days is 0.25 a week; the window's edge moves a few
        # minutes' use. The partial-week rate this replaced moved by up to
        # 7 / days-gone points a week per point (2026-11-26).
        self.assertLess(abs(other1 - other0), 0.3)
        self.assertLess(abs(other1 - other0) / other0, 0.006)
        self.assertLess(abs(cap1 - cap0) / cap0, 0.03)

    def test_a_burst_late_in_a_young_week_moves_the_rate_by_its_share(self):
        # 40 points in one night, 2 days into the allowance week: the old
        # current-week rate took 40 * 7 / 2 = 140 a week of it.
        end = fc.RESET_ANCHOR + fc.timedelta(days=49, hours=2 * 24)
        quiet = self.readings(end)
        loud = self.readings(end, burst_at=end - fc.timedelta(hours=3), burst=40.0)
        jump = self.figures(loud, end, 28)[0] - self.figures(quiet, end, 28)[0]
        self.assertAlmostEqual(jump, 40.0 * 7 / 28, delta=0.6)

    def test_the_window_is_honored(self):
        # A burst 20 days back counts in a 28-day window, not a 14-day one.
        burst_at = self.END - fc.timedelta(days=20)
        loud = self.readings(self.END, burst_at=burst_at, burst=60.0)
        quiet = self.readings(self.END)
        for days, share in ((28, 60.0 * 7 / 28), (14, 0.0)):
            with self.subTest(days=days):
                jump = (fc.meter_non_eval_points(loud, [], self.END, days)["points_per_week"]
                        - fc.meter_non_eval_points(quiet, [], self.END, days)["points_per_week"])
                self.assertAlmostEqual(jump, share, delta=0.6)
        self.assertEqual(len(fc.non_eval_week_curves(quiet, [], self.END, 28 // 7)), 4)
        self.assertEqual(len(fc.non_eval_week_curves(quiet, [], self.END, 14 // 7)), 2)

    def test_a_fall_without_a_reset_is_a_misread_not_a_restart(self):
        t = fc.RESET_ANCHOR + fc.timedelta(days=15)
        span = [(t, 10.0), (t + fc.timedelta(hours=1), 8.0), (t + fc.timedelta(hours=2), 11.0)]
        self.assertEqual(fc.with_resets(span), span)
        reset = fc.RESET_ANCHOR + fc.timedelta(days=21)
        across = [(reset - fc.timedelta(minutes=5), 70.0), (reset + fc.timedelta(minutes=5), 1.0)]
        self.assertEqual(fc.with_resets(across), [across[0], (reset, 0.0), across[1]])
        # A collector gap across the reset: 3 before, 5 after is 5 of new use.
        gap = [(reset - fc.timedelta(hours=2), 3.0), (reset + fc.timedelta(hours=2), 5.0)]
        self.assertEqual(fc.meter_non_eval_points(gap, [], gap[-1][0], 7)["meter_rise_points"], 5.0)
        # A reading exactly at the reset is already the restart.
        on = [(reset - fc.timedelta(minutes=5), 70.0), (reset, 0.0), (reset + fc.timedelta(hours=1), 2.0)]
        self.assertEqual(fc.with_resets(on), on)

    def test_readings_at_one_instant_cover_no_time(self):
        t = fc.RESET_ANCHOR + fc.timedelta(days=15)
        self.assertIsNone(fc.meter_non_eval_points([(t, 1.0), (t, 2.0)], [], t, 7))

    # --- the other windowed rates ------------------------------------------

    def test_measured_rate_counts_only_runs_in_the_window(self):
        root = MeasuredRate.tree(self, {"20261030T100000Z-aaaaaa": _trial_blocks(2.0),
                                          "20261120T110000Z-bbbbbb": _trial_blocks(3.0)})
        since = fc.datetime(2026, 11, 1, tzinfo=fc.timezone.utc)
        self.assertEqual(fc.measured_usd_per_point(root, 1 / 0.15)["runs"], 2)
        self.assertEqual(fc.measured_usd_per_point(root, 1 / 0.15, since=since)["usd"], 3.0)
        self.assertIsNone(fc.measured_usd_per_point(
            root, 1 / 0.15, since=fc.datetime(2026, 11, 25, tzinfo=fc.timezone.utc)))

    def test_eval_pace_starts_at_the_windows_first_reset(self):
        reset = fc.RESET_ANCHOR
        runs = [(reset + fc.timedelta(hours=h), 5.0) for h in (1, 5, 10, 15, 20)]
        runs += [(reset + fc.timedelta(days=7, hours=h), 12.5) for h in (1, 2)]
        now = reset + fc.timedelta(days=14)
        self.assertEqual(fc.eval_pace(runs, 25.0, now)["weeks"], 2)
        got = fc.eval_pace(runs, 25.0, now, since=reset + fc.timedelta(days=1))
        self.assertEqual(got, {"points_per_hour": 12.5, "weeks": 1})

    def arrivals(self):
        def item(days_ago, kind="skill", eligible=True):
            at = fc.datetime(2026, 11, 15, 10, tzinfo=fc.timezone.utc) - fc.timedelta(days=days_ago)
            return {"kind": kind, "event": "added", "eligible": eligible,
                    "at": at.strftime("%Y-%m-%dT%H:%M:%SZ")}
        rate = {"complete": True, "added_per_week": 9.0, "eligible_share": 0.9}
        return {"schema": 1, "as_of": "2026-11-15T10:00:00Z",
                "rates": {"git-hook": dict(rate), "skill": dict(rate),
                          "guidance-section": dict(rate)},
                "sources": [{"kind": "skill", "since": "2026-01-01T00:00:00Z"},
                            {"kind": "guidance-section", "since": "2026-11-05T10:00:00Z"},
                            {"kind": "git-hook", "since": "2026-01-01T00:00:00Z"}],
                "items": [item(3), item(10, eligible=False), item(20), item(40),
                          item(2, "guidance-section"), item(15, "guidance-section")]}

    def test_arrival_rates_are_recounted_over_the_window(self):
        now = Arrivals.NOW
        got28 = fc.arrival_assumptions(self.arrivals(), now, 28)
        got14 = fc.arrival_assumptions(self.arrivals(), now, 14)
        self.assertAlmostEqual(got28["new_skills_per_week"], 3 / 4)
        self.assertAlmostEqual(got28["first_use_share"], 2 / 3)
        self.assertAlmostEqual(got14["new_skills_per_week"], 2 / 2)
        self.assertAlmostEqual(got14["first_use_share"], 1 / 2)
        # Sections are tracked only for 10 days: the window is cut to them.
        self.assertAlmostEqual(got28["new_sections_per_week"], 1 / (10 / 7))
        self.assertEqual(got28["new_hooks_per_week"], 0.0)
        # Without a window, the document's own rates as before.
        self.assertEqual(fc.arrival_assumptions(self.arrivals(), now)["new_skills_per_week"], 9.0)

    def test_an_unreadable_or_incomplete_kind_is_unknown_over_a_window(self):
        doc = self.arrivals()
        doc["rates"]["skill"]["complete"] = False
        self.assertNotIn("new_skills_per_week", fc.arrival_assumptions(doc, Arrivals.NOW, 28))
        doc = self.arrivals()
        doc["sources"][1]["since"] = "2026-11-12T10:00:00Z"  # under a week of sections
        self.assertNotIn("new_sections_per_week", fc.arrival_assumptions(doc, Arrivals.NOW, 28))
        doc = self.arrivals()
        del doc["items"]
        self.assertEqual(fc.arrival_assumptions(doc, Arrivals.NOW, 28), {})
