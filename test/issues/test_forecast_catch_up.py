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

POLICY = {"max_runs_per_cell": 20, "recheck_weeks": 8}
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


if __name__ == "__main__":
    unittest.main()
