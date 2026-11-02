#!/usr/bin/env python3
"""The 85% keep applied per subject, not per cell (#557 follow-up).

A subject keeps only when some `benefit` cell has a keep test with
p <= (1 - benefit_confidence) / m, m = fixtures on main x roster models x 3
routes, fixed before any run (harness/gates.py `retirement`, `keep_p`, the
`keep_tests` of `_classify`). Covered: the tests per route, the fixed family
(a missing cell still counts), demotion to insufficient, the alone pair's
exemption (shorten-or-merge unchanged), the guidance document carrying the
family, and the explorer's `helps` level.

Hermetic and deterministic: canned runs, no network, no clock.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import explorer_data  # noqa: E402
import gates  # noqa: E402
from test_issue_70_retirement import (EXPECT, FLAT, FLAT_JUDGE, GAIN, TEST_POLICY,  # noqa: E402
                                      series)

#: Priors that make three GAIN runs a per-cell benefit at p of about 0.037:
#: confident at 85% in the cell, but not at 0.15 / 6.
MARGINAL = {"objective": 0.002, "judge": 0.4, "check": 0.1}


def gain_runs(n=3):
    return series("with", GAIN[:n], FLAT_JUDGE) + series("without", FLAT[:n], FLAT_JUDGE)


def verdict(runs, models, priors=MARGINAL, **kw):
    return gates.retirement({"runs": runs}, models, "demo", TEST_POLICY, EXPECT, priors, **kw)


class KeepPTests(unittest.TestCase):

    def test_keep_p_inverts_confidence_reached(self):
        a, b = [0.9, 0.8, 0.85], [0.7, 0.75, 0.7]
        d, info = gates._stratum(a, b, 0.01, 4)
        self.assertAlmostEqual(1 - gates.keep_p(d, info, 0.01),
                               gates.confidence_reached(a, b, 0.01, 4, d), places=12)
        self.assertEqual(gates.keep_p(-0.1, info, 0.01), 1.0)
        self.assertEqual(gates.keep_p(0.0, info, 0.01), 1.0)

    def test_every_benefit_route_has_a_test(self):
        runs = gain_runs()
        cell = gates.classify_cell(runs[:3], runs[3:], TEST_POLICY, False, MARGINAL)
        self.assertEqual([t["route"] for t in cell["keep_tests"]],
                         ["objective", "checks", "judge"])
        self.assertAlmostEqual(cell["keep_tests"][0]["p"],
                               1 - cell["objective"]["helps_confidence"], places=12)
        # The judge test exists although the objective decided the class
        # and out["judge"] stays unset.
        self.assertIsNone(cell["judge"])


class FamilyTests(unittest.TestCase):

    def test_one_model_keeps_two_models_do_not(self):
        one = verdict(gain_runs(), ["model-a"])
        self.assertEqual((one["verdict"], one["keep_family"]), ("keep", 3))
        two = verdict(gain_runs(), ["model-a", "model-b"])
        # model-b has no run, yet its cell counts: m is fixed at 6.
        self.assertEqual(two["keep_family"], 6)
        self.assertEqual(two["verdict"], "insufficient")
        cell = next(c for c in two["cells"] if c["model"] == "model-a")
        self.assertEqual(cell["class"], "insufficient")
        self.assertIn("Holm", cell["reason"])
        self.assertIn("lower bound is above 0", cell["cell_reason"])
        self.assertAlmostEqual(two["keep_alpha"], 0.15, places=12)

    def test_a_strong_benefit_keeps_whatever_the_family(self):
        v = verdict(gain_runs(10), ["model-a", "model-b"], priors=gates.run_priors(gain_runs(10)))
        self.assertEqual(v["verdict"], "keep")

    def test_without_the_family_each_cell_keeps_alone(self):
        v = verdict(gain_runs(), ["model-a", "model-b"], family=False)
        self.assertEqual(v["verdict"], "keep")
        self.assertNotIn("keep_family", v)


class GuidanceTests(unittest.TestCase):

    def runs(self, pair, with_patterns, without_patterns, judges=(FLAT_JUDGE, FLAT_JUDGE)):
        runs = (series("with", with_patterns, judges[0], skill="sec", fixture="fx",
                       ctx="rest", pair="rest")
                + series("without", without_patterns, judges[1], skill="sec",
                         fixture="fx", ctx="rest", pair="rest"))
        for run in runs:
            run["pair"] = pair
            run["path"] = f"{run['path']}#{pair}"
        return runs

    def test_the_alone_pair_is_exempt_and_the_document_carries_the_family(self):
        expect = {"fx": {"fixture_digest": "f1", "tested_digest": "t1"}}
        alone = self.runs("alone", GAIN[:3], FLAT[:3], ([8.0] * 3, FLAT_JUDGE))
        v = gates.guidance_verdict({"runs": self.runs("in_situ", FLAT, FLAT) + alone},
                                   ["model-a", "model-b"], "sec", TEST_POLICY, expect)
        self.assertEqual(v["keep_family"], 6)
        # The alone cell's own benefit still counts for the twist.
        self.assertTrue(any(c["class"] == "benefit" for c in v["alone"]["cells"]))
        self.assertNotIn("keep_family", v["alone"])


class ExplorerTests(unittest.TestCase):

    def test_helps_is_the_family_level(self):
        v = verdict(gain_runs(), ["model-a", "model-b"])
        p = min(t["p"] for c in v["cells"] for t in c.get("keep_tests", []))
        helps = explorer_data.subject_confidence(v)["helps"]
        self.assertAlmostEqual(helps, max(0.0, 1 - 6 * p), places=12)
        self.assertLess(helps, TEST_POLICY["benefit_confidence"])
        kept = verdict(gain_runs(), ["model-a"])
        self.assertGreaterEqual(explorer_data.subject_confidence(kept)["helps"],
                                TEST_POLICY["benefit_confidence"])
        self.assertTrue(math.isfinite(helps))


if __name__ == "__main__":
    unittest.main()
