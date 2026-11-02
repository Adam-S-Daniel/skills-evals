#!/usr/bin/env python3
"""skills-evals#557: in-situ guidance cells pooled by rest of guidance.

Covered here: harness/gates.py `pool_cells(strata=True)`, `cell_priors`
and `classify_strata` through `guidance_verdict`, with no separate
confirmation beside the rest on main (Adam, 2026-11-02). Skills and the
alone pair keep their own tests (test_issue_70_retirement.py,
test_issue_124_guidance_gates.py), which this change leaves green.

Hermetic and deterministic: canned runs, no network, no clock.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import gates  # noqa: E402
from test_issue_70_retirement import (FLAT, FLAT_JUDGE, GAIN, TEST_POLICY,  # noqa: E402
                                      series)

MAIN, OLD, OLDER = "rest-main", "rest-old", "rest-older"
EXPECT = {"fx": {"fixture_digest": "f1", "tested_digest": "t1"}}
CEILING = [(96, 96, 96), (96, 96, 95)] * 10


def stratum(rest, with_patterns, without_patterns, judges=(FLAT_JUDGE, FLAT_JUDGE),
            start=0, model="model-a", pair="in_situ", conditional=False):
    """In-situ runs of section `sec`, fixture `fx`, beside rest `rest`."""
    runs = (series("with", with_patterns, judges[0], start=start, skill="sec",
                   fixture="fx", ctx=rest, pair=rest, model=model, conditional=conditional)
            + series("without", without_patterns, judges[1], start=start, skill="sec",
                     fixture="fx", ctx=rest, pair=rest, model=model,
                     conditional=conditional))
    for run in runs:
        run["pair"] = pair
        run["path"] = f"{run['path']}#{rest}#{pair}"
    return runs


def verdict(runs, models=("model-a",), expect=EXPECT):
    return gates.guidance_verdict({"runs": runs}, list(models), "sec", TEST_POLICY, expect)


class PoolingTests(unittest.TestCase):

    def test_cells_hold_every_rest_and_their_own_key(self):
        runs = (stratum(OLD, FLAT[:4], FLAT[:4]) + stratum(MAIN, FLAT[:3], FLAT[:3], start=4)
                + stratum(OLD, FLAT[:2], FLAT[:2], model="model-b"))
        cells = gates.pool_cells(runs, "sec", ["model-a", "model-b"], EXPECT, strata=True)
        a, b = cells[("fx", "model-a")], cells[("fx", "model-b")]
        self.assertEqual(sorted(a["strata"]), [MAIN, OLD])
        self.assertEqual((len(a["with"]), len(a["without"])), (7, 7))
        self.assertEqual(a["key"], {"tested_digest": "t1", "fixture_digest": "f1"})
        self.assertIsNot(a["key"], b["key"])
        self.assertEqual(sorted(b["strata"]), [OLD])

    def test_other_content_never_enters_a_stratum(self):
        runs = stratum(MAIN, FLAT[:2], FLAT[:2])
        for run in runs[:1]:
            run["tested_digest"] = "t0"  # an older section text
        cells = gates.pool_cells(runs, "sec", ["model-a"], EXPECT, strata=True)
        self.assertEqual(len(cells[("fx", "model-a")]["with"]), 1)

    def test_without_the_section_on_main_the_key_is_incomplete(self):
        expect = {"fx": {"fixture_digest": "f1", "tested_digest": None}}
        v = verdict(stratum(MAIN, FLAT, FLAT), expect=expect)
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIn("tested_digest", v["cells"][0]["reason"])


class ClassifyTests(unittest.TestCase):

    def test_one_rest_retires(self):
        v = verdict(stratum(MAIN, FLAT, FLAT))
        cell = v["cells"][0]
        self.assertEqual((v["verdict"], cell["class"]), ("retire", "no-benefit"), cell["reason"])
        self.assertEqual(cell["key"]["strata"], [MAIN])

    def test_rests_pool_toward_a_verdict(self):
        # Ten runs per arm beside each of two rests: neither alone decides
        # (its own prior is the fallback), together they retire.
        one = verdict(stratum(OLD, FLAT[:10], FLAT[:10]))
        self.assertEqual(one["verdict"], "insufficient")
        both = verdict(stratum(OLD, FLAT[:10], FLAT[:10])
                       + stratum(MAIN, FLAT[10:], FLAT[10:], start=10))
        self.assertEqual(both["verdict"], "retire", both["cells"][0]["reason"])
        self.assertEqual(sorted(both["cells"][0]["key"]["strata"]), [MAIN, OLD])
        self.assertEqual(both["cells"][0]["objective"]["strata"], 2)

    def test_a_benefit_in_an_old_rest_keeps(self):
        runs = stratum(OLD, GAIN + GAIN, FLAT) + stratum(MAIN, FLAT[:2], FLAT[:2], start=20)
        v = verdict(runs)
        self.assertEqual(v["verdict"], "keep", v["cells"][0]["reason"])
        self.assertEqual(v["cells"][0]["objective"]["strata"], 2)

    def test_an_unused_stratum_is_dropped(self):
        runs = stratum(MAIN, FLAT, FLAT) + series(
            "with", FLAT[:2], FLAT_JUDGE, start=30, skill="sec", fixture="fx", ctx=OLD,
            pair=OLD)
        for run in runs[-2:]:
            run["pair"] = "in_situ"
            run["path"] += "#old-only"
        v = verdict(runs)
        cell = v["cells"][0]
        self.assertEqual(cell["key"]["strata"], [MAIN])
        self.assertEqual(len(cell["runs"]["with"]), 20)
        self.assertEqual(len(v["runs_used"]), 40)
        self.assertEqual(v["verdict"], "retire")

    def test_an_errored_trial_in_an_unused_stratum_still_blocks_removal(self):
        lone = series("with", [(80, 80, 80)], FLAT_JUDGE, start=30, skill="sec",
                      fixture="fx", ctx=OLD, pair=OLD)[0]
        lone["trials"][0] = {**lone["trials"][0], "scored": False, "errored": True,
                             "checks": {}, "judge": None}
        lone["pair"], lone["path"] = "in_situ", lone["path"] + "#err"
        v = verdict(stratum(MAIN, FLAT, FLAT) + [lone])
        self.assertEqual(v["cells"][0]["class"], "insufficient")

    def test_a_judge_unusable_in_one_rest_is_unusable(self):
        skipped = stratum(OLD, FLAT[:4], FLAT[:4], judges=(None, None), conditional=True)
        v = verdict(stratum(MAIN, FLAT, FLAT, start=4) + skipped)
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIn("judge", v["cells"][0]["reason"])

    def test_pooled_ceiling_is_decided_on_pooled_counts(self):
        v = verdict(stratum(MAIN, CEILING, CEILING))
        self.assertEqual(v["cells"][0]["class"], "ceiling")

    def test_a_retire_that_helps_alone_is_shorten_or_merge(self):
        alone = stratum("none", GAIN + GAIN, FLAT, judges=([8.0] * 20, FLAT_JUDGE),
                        pair="alone")
        v = verdict(stratum(OLD, FLAT[:10], FLAT[:10])
                    + stratum(MAIN, FLAT[10:], FLAT[10:], start=10) + alone)
        self.assertEqual((v["in_situ_verdict"], v["alone"]["verdict"], v["verdict"]),
                         ("retire", "keep", "shorten-or-merge"))


class CellPriorTests(unittest.TestCase):

    def test_few_runs_give_the_fallback(self):
        # Five runs per arm: 8 degrees of freedom for the run mean and the
        # judge; the per-check figure pools 100 checks, so it has its own.
        priors = gates.cell_priors(stratum(MAIN, FLAT[:5], FLAT[:5]))
        self.assertEqual((priors["objective"], priors["judge"]), (0.25, 25.0))
        self.assertNotEqual(priors["check"], 0.25)

    def test_enough_runs_give_their_own_spread(self):
        runs = stratum(MAIN, FLAT, FLAT)
        priors = gates.cell_priors(runs)
        means = [gates.run_numbers(r["trials"], True)["run_mean"] for r in runs]
        self.assertAlmostEqual(priors["objective"],
                               gates.pooled_variance([means[:20], means[20:]]), places=12)


class ConfidenceInfoTests(unittest.TestCase):

    def test_matches_confidence_reached_for_one_stratum(self):
        a, b = [0.8, 0.6, 1.0], [0.6, 0.4, 0.6, 0.5]
        d, info = gates.stratified_estimate([(a, b)], 0.05, 4)
        for distance in (d, 0.4 - d, -0.1):
            self.assertAlmostEqual(gates.confidence_reached_info(info, 0.05, distance),
                                   gates.confidence_reached(a, b, 0.05, 4, distance), places=12)


if __name__ == "__main__":
    unittest.main()
