"""The catch-up forecast prices subjects deep-first from the planner's own
projection (scripts/forecast_catch_up.py). Synthetic verdict documents only:
no results tree, no network, no clock."""

from __future__ import annotations

import math
import sys
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
    BUDGET = {"weekly_cap": 0.25, "points_per_usd": 0.0015}
    BATCH = {"pairs_per_cell": 15, "rates": {"skill": 1.0, "guidance": 1.0}}

    def run_forecast(self, cells=None, gates=None, budget=None, **assumptions):
        def proj(cell, ctx):
            if cell["skill"] == "a":
                return projection(pairs=4, keep=4, remove=math.inf, remaining=20)
            return projection(pairs=10, keep=math.inf, remove=10, remaining=20)
        with mock.patch.object(fc.plan_week, "pairs_to_verdict", side_effect=proj), \
                mock.patch.object(fc.plan_week, "_produces_item", return_value=True):
            return fc.forecast(gates or self.GATES, cells or self.CELLS, budget or self.BUDGET,
                               self.BATCH, None,
                               {"fire_overhead_usd": 0.0, **assumptions},
                               frozenset({"skipped-one"}))

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

    def test_eval_free_span_after_the_last_eval_run(self):
        # Meter 10 -> 40 (a reset drop to 5 is skipped, then 5 -> 25); an eval
        # run 4 days back leaves 3+ eval-free days, so its points never count.
        readings = [(self.at(150), 0.0), (self.at(96), 10.0), (self.at(72), 30.0),
                    (self.at(48), 40.0), (self.at(47), 5.0), (self.at(0), 25.0)]
        m = fc.meter_non_eval_points(readings, [(self.at(97), 9.0)], self.END, 7)
        self.assertEqual(m["method"], "eval-free")
        self.assertEqual((m["meter_rise_points"], m["eval_points"]), (50.0, 0.0))
        self.assertAlmostEqual(m["points_per_week"], 50.0 * 7 / 4)

    def test_recent_eval_run_is_subtracted(self):
        readings = [(self.at(168), 0.0), (self.at(0), 70.0)]
        m = fc.meter_non_eval_points(readings, [(self.at(10), 14.0)], self.END, 7)
        self.assertEqual(m["method"], "less eval points")
        self.assertAlmostEqual(m["points_per_week"], 56.0)

    def test_too_few_readings(self):
        self.assertIsNone(fc.meter_non_eval_points([(self.at(1), 3.0)], [], self.END, 7))

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


if __name__ == "__main__":
    unittest.main()
