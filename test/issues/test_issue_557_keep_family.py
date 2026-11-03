#!/usr/bin/env python3
"""The keep applied per subject, not per cell (#557 follow-up).

A subject keeps only when some cell's keep test rejects at
(1 - benefit_confidence) / m, m = fixtures on main x roster models, fixed
before any run (harness/gates.py `retirement`, the `keep_tests` of
`_classify`). Since 2026-11-03 the keep test is the betting test of the
paired difference D > 0, and the objective is its only route: the judge is
reported and does not vote, and single checks no longer keep. Covered: the
one route, the fixed family (a missing cell still counts), the alone pair's
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
from test_issue_70_retirement import (EXPECT, FLAT_JUDGE, GAIN, LOSS, TEST_POLICY,  # noqa: E402
                                      series)

#: Pairs of GAIN against LOSS (D about 0.4): the keep test rejects at
#: alpha 0.20 (m = 1), not yet at 0.10 (m = 2). Measured on the committed
#: policy: m = 1 keeps at pair 7, m = 2 at pair 9.
MARGINAL = 7


def gain_runs(n=MARGINAL):
    return (series("with", GAIN[:n], FLAT_JUDGE)
            + series("without", LOSS[:n], FLAT_JUDGE))


def verdict(runs, models, **kw):
    return gates.retirement({"runs": runs}, models, "demo", TEST_POLICY, EXPECT, **kw)


class KeepPTests(unittest.TestCase):

    def test_keep_p_is_villes_p_of_the_keep_test(self):
        ds = [0.4, 0.3, 0.5, 0.4]
        wealth = gates.keep_wealth(ds)
        block = gates.sequence_block(ds, 0.15, 0.2, 0.1)
        self.assertAlmostEqual(block["keep_p"], gates.ville_p(wealth), places=12)
        self.assertAlmostEqual(block["keep_p"], 1 - block["helps_confidence"], places=12)
        self.assertEqual(gates.sequence_block([-0.1] * 4, 0.15, 0.2, 0.1)["keep_p"], 1.0)
        self.assertEqual(gates.sequence_block([0.0] * 4, 0.15, 0.2, 0.1)["keep_p"], 1.0)

    def test_the_objective_is_the_only_keep_route(self):
        runs = gain_runs()
        cell = gates.classify_cell(runs[:MARGINAL], runs[MARGINAL:], TEST_POLICY)
        self.assertEqual([t["route"] for t in cell["keep_tests"]], ["objective"])
        self.assertAlmostEqual(cell["keep_tests"][0]["p"],
                               1 - cell["objective"]["helps_confidence"], places=12)
        # The judge is reported beside it, marked as not voting.
        self.assertIs(cell["judge"]["votes"], False)


class FamilyTests(unittest.TestCase):

    def test_one_model_keeps_two_models_do_not(self):
        one = verdict(gain_runs(), ["model-a"])
        self.assertEqual((one["verdict"], one["keep_family"]), ("keep", 1))
        two = verdict(gain_runs(), ["model-a", "model-b"])
        # model-b has no run, yet its cell counts: m is fixed at 2.
        self.assertEqual(two["keep_family"], 2)
        self.assertEqual(two["verdict"], "insufficient")
        cell = next(c for c in two["cells"] if c["model"] == "model-a")
        self.assertEqual(cell["class"], "insufficient")
        self.assertEqual(cell["objective"]["keep_at"], None)
        self.assertAlmostEqual(two["keep_alpha"], 0.20, places=12)

    def test_a_strong_benefit_keeps_whatever_the_family(self):
        v = verdict(gain_runs(10), ["model-a", "model-b"])
        self.assertEqual(v["verdict"], "keep")
        cell = next(c for c in v["cells"] if c["model"] == "model-a")
        self.assertEqual(cell["objective"]["keep_at"], 9)

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
        expect = {"fx": {"fixture_digest": "f1", "tested_digest": "t1", "rest_digest": "rest"}}
        alone = self.runs("alone", GAIN[:MARGINAL], LOSS[:MARGINAL], ([8.0] * 10, FLAT_JUDGE))
        in_situ = self.runs("in_situ", LOSS[:3], LOSS[:3])
        v = gates.guidance_verdict({"runs": in_situ + alone},
                                   ["model-a", "model-b"], "sec", TEST_POLICY, expect)
        self.assertEqual(v["keep_family"], 2)
        # The alone cell is its own family of one, so its benefit at alpha
        # 0.20 still counts for the twist.
        self.assertTrue(any(c["class"] == "benefit" for c in v["alone"]["cells"]))
        self.assertNotIn("keep_family", v["alone"])


class ExplorerTests(unittest.TestCase):

    def test_helps_is_the_family_level(self):
        v = verdict(gain_runs(), ["model-a", "model-b"])
        p = min(t["p"] for c in v["cells"] for t in c.get("keep_tests", []))
        helps = explorer_data.subject_confidence(v)["helps"]
        self.assertAlmostEqual(helps, max(0.0, 1 - 2 * p), places=12)
        self.assertLess(helps, TEST_POLICY["benefit_confidence"])
        kept = verdict(gain_runs(), ["model-a"])
        self.assertGreaterEqual(explorer_data.subject_confidence(kept)["helps"],
                                TEST_POLICY["benefit_confidence"])
        self.assertTrue(math.isfinite(helps))


if __name__ == "__main__":
    unittest.main()
