#!/usr/bin/env python3
"""skills-evals#546: the stratified statistics and their seeded simulation.

Covered here, and nothing is wired into a verdict yet (the wiring is the
follow-up issue the PR names):

  * harness/gates.py `stratified_estimate`, `stratified_sequence` and
    `stratified_confident_checks`: one stratum is exactly today's
    `confidence_sequence` / `confident_checks`, and two strata combine by
    precision weight;
  * `pooled_variance`'s `min_df` and `fallback`, whose defaults keep
    today's numbers;
  * scripts/simulate_stratified_pooling.py: one seeded rep of each kind is
    deterministic, and a run with few reps reports every scenario.

Hermetic and deterministic: fixed seeds, no network, no clock.
"""

from __future__ import annotations

import io
import math
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from harness import gates  # noqa: E402
import simulate_stratified_pooling as sim  # noqa: E402

PRIOR, STRENGTH = 0.05, 4


class StratifiedSequenceTests(unittest.TestCase):
    A = [0.8, 0.6, 1.0, 0.8]
    B = [0.6, 0.4, 0.6]

    def test_one_stratum_is_todays_sequence(self):
        for level in (0.85, 0.95):
            self.assertEqual(
                gates.stratified_sequence([(self.A, self.B)], level, PRIOR, STRENGTH),
                gates.confidence_sequence(self.A, self.B, level, PRIOR, STRENGTH))

    def test_two_strata_weight_by_precision(self):
        c, d = [0.2, 0.4], [0.4, 0.4, 0.2]
        d1, p1 = gates._stratum(self.A, self.B, PRIOR, STRENGTH)
        d2, p2 = gates._stratum(c, d, PRIOR, STRENGTH)
        delta, info = gates.stratified_estimate([(self.A, self.B), (c, d)], PRIOR, STRENGTH)
        self.assertAlmostEqual(info, p1 + p2, places=12)
        self.assertAlmostEqual(delta, (p1 * d1 + p2 * d2) / (p1 + p2), places=12)
        lower, upper = gates.stratified_sequence([(self.A, self.B), (c, d)], 0.95,
                                                 PRIOR, STRENGTH)
        self.assertAlmostEqual((lower + upper) / 2, delta, places=12)
        rho = 1 / PRIOR
        half = math.sqrt((info + rho) * math.log((info + rho) / (rho * 0.05 ** 2))) / info
        self.assertAlmostEqual(upper - delta, half, places=12)

    def test_identical_strata_add_information(self):
        one = gates.stratified_estimate([(self.A, self.B)], PRIOR, STRENGTH)
        two = gates.stratified_estimate([(self.A, self.B), (self.A, self.B)], PRIOR, STRENGTH)
        self.assertAlmostEqual(two[0], one[0], places=12)
        self.assertAlmostEqual(two[1], 2 * one[1], places=12)

    def test_needs_a_stratum(self):
        with self.assertRaises(ValueError):
            gates.stratified_estimate([], PRIOR, STRENGTH)


class StratifiedChecksTests(unittest.TestCase):
    WITH = {"a": [1.0] * 6, "b": [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]}
    WITHOUT = {"a": [0.0] * 6, "b": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]}

    def test_one_stratum_is_todays_checks(self):
        priors = {"a": 0.1, "b": 0.1}
        self.assertEqual(
            gates.stratified_confident_checks([(self.WITH, self.WITHOUT)], 0.85, priors,
                                              STRENGTH),
            gates.confident_checks(self.WITH, self.WITHOUT, 0.85, priors, STRENGTH))
        self.assertEqual(gates.confident_checks(self.WITH, self.WITHOUT, 0.85, priors,
                                                STRENGTH), ["a"])

    def test_a_check_confident_over_two_strata(self):
        priors = {"a": 0.1, "b": 0.1}
        both = [(self.WITH, self.WITHOUT), (self.WITH, self.WITHOUT)]
        self.assertEqual(gates.stratified_confident_checks(both, 0.85, priors, STRENGTH),
                         ["a"])

    def test_a_check_in_one_stratum_only_uses_that_stratum(self):
        priors = {"a": 0.1, "b": 0.1, "c": 0.1}
        other = ({"c": [1.0, 1.0]}, {"c": [1.0, 1.0]})
        self.assertEqual(gates.stratified_confident_checks(
            [(self.WITH, self.WITHOUT), other], 0.85, priors, STRENGTH), ["a"])

    def test_no_check_in_common_is_none(self):
        self.assertEqual(gates.stratified_confident_checks(
            [({"a": [1.0]}, {"b": [0.0]}), ({"c": [1.0]}, {"d": [0.0]})], 0.85, {}, STRENGTH),
            [])


class PooledVarianceGuardTests(unittest.TestCase):
    GROUPS = [[0.2, 0.4, 0.6], [0.5, 0.7]]

    def test_defaults_keep_todays_numbers(self):
        ss = (0.04 + 0 + 0.04) + (0.01 + 0.01)
        self.assertAlmostEqual(gates.pooled_variance(self.GROUPS), ss / 3, places=12)
        self.assertEqual(gates.pooled_variance([[0.5]]), gates.FALLBACK_PRIOR_VARIANCE)

    def test_too_few_degrees_of_freedom_give_the_fallback(self):
        self.assertEqual(gates.pooled_variance(self.GROUPS, 4, 0.25), 0.25)
        self.assertAlmostEqual(gates.pooled_variance(self.GROUPS, 3, 0.25),
                               gates.pooled_variance(self.GROUPS), places=12)
        self.assertEqual(gates.pooled_variance([], gates.GUIDANCE_PRIOR_MIN_DF,
                                               gates.GUIDANCE_FALLBACK_PRIOR_VARIANCE), 0.25)


class SimulationTests(unittest.TestCase):
    def test_a_rep_is_deterministic(self):
        retire = (546, 3, (0.75, 0.70), [(0.70, 0.70, 3)], 4)
        keep = (546, 2, [0.6, 0.9], 6)
        self.assertEqual(sim.retire_rep(retire), sim.retire_rep(retire))
        self.assertEqual(sim.keep_rep(keep), sim.keep_rep(keep))
        self.assertEqual(len(sim.retire_rep(retire)), 4)
        self.assertEqual(len(sim.keep_rep(keep)), 4)

    def test_wilson_interval_brackets_the_estimate(self):
        lo, hi = sim.wilson(25, 1000)
        self.assertLess(lo, 0.025)
        self.assertGreater(hi, 0.025)

    def test_main_reports_every_scenario(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = sim.main(["--reps", "8", "--jobs", "1"])
        self.assertIn(code, (0, 1))  # 8 reps decide nothing; the report is the point
        text = out.getvalue()
        for name, *_ in sim.RETIRE + sim.POWER + sim.KEEP:
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
