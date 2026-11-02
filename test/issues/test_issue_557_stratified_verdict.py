#!/usr/bin/env python3
"""skills-evals#557: in-situ guidance cells pooled by rest of guidance.

Covered here: harness/gates.py `pool_cells(strata=True)`, `cell_priors`,
`classify_strata` and the `retire-unconfirmed` verdict through
`guidance_verdict`; scripts/retire_skill.py's guidance re-check; and
scripts/explorer_data.py's no-help figure for a stratified cell. Skills and
the alone pair keep their own tests (test_issue_70_retirement.py,
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

import explorer_data  # noqa: E402
import gates  # noqa: E402
import retire_skill as rs  # noqa: E402
from test_issue_70_retirement import (FLAT, FLAT_JUDGE, GAIN, TEST_POLICY,  # noqa: E402
                                      series)

MAIN, OLD, OLDER = "rest-main", "rest-old", "rest-older"
EXPECT = {"fx": {"fixture_digest": "f1", "tested_digest": "t1", "main_rest": MAIN}}
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
        self.assertEqual(a["key"], {"tested_digest": "t1", "fixture_digest": "f1",
                                    "main_rest": MAIN})
        self.assertIsNot(a["key"], b["key"])
        self.assertEqual(sorted(b["strata"]), [OLD])

    def test_other_content_never_enters_a_stratum(self):
        runs = stratum(MAIN, FLAT[:2], FLAT[:2])
        for run in runs[:1]:
            run["tested_digest"] = "t0"  # an older section text
        cells = gates.pool_cells(runs, "sec", ["model-a"], EXPECT, strata=True)
        self.assertEqual(len(cells[("fx", "model-a")]["with"]), 1)

    def test_without_main_rest_the_key_is_incomplete(self):
        expect = {"fx": {"fixture_digest": "f1", "tested_digest": None, "main_rest": None}}
        v = verdict(stratum(MAIN, FLAT, FLAT), expect=expect)
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIn("main_rest", v["cells"][0]["reason"])


class ClassifyTests(unittest.TestCase):

    def test_one_rest_on_main_retires_confirmed(self):
        v = verdict(stratum(MAIN, FLAT, FLAT))
        cell = v["cells"][0]
        self.assertEqual((v["verdict"], cell["class"], cell["confirmed"]),
                         ("retire", "no-benefit", True), cell["reason"])
        self.assertEqual(cell["key"]["strata"], [MAIN])
        self.assertEqual(cell["main_rest"]["runs"], {"with": 20, "without": 20})

    def test_old_rests_alone_are_unconfirmed(self):
        runs = stratum(OLD, FLAT, FLAT) + stratum(MAIN, FLAT[:1], FLAT[:1], start=20)
        v = verdict(runs)
        cell = v["cells"][0]
        self.assertEqual((cell["class"], cell["confirmed"]), ("no-benefit", False))
        self.assertEqual(v["verdict"], "retire-unconfirmed")
        self.assertEqual(sorted(cell["key"]["strata"]), [MAIN, OLD])

    def test_no_run_beside_main_is_unconfirmed(self):
        v = verdict(stratum(OLD, FLAT, FLAT))
        self.assertEqual(v["verdict"], "retire-unconfirmed")
        self.assertIn("beside the guidance on main", v["cells"][0]["confirm_reason"])

    def test_a_benefit_in_an_old_rest_keeps(self):
        runs = stratum(OLD, GAIN + GAIN, FLAT) + stratum(MAIN, FLAT[:2], FLAT[:2], start=20)
        v = verdict(runs)
        self.assertEqual(v["verdict"], "keep", v["cells"][0]["reason"])
        self.assertEqual(v["cells"][0]["objective"]["strata"], 2)

    def test_main_rest_at_the_ceiling_does_not_confirm(self):
        runs = stratum(OLD, FLAT, FLAT) + stratum(MAIN, CEILING, CEILING, start=20)
        cell = verdict(runs)["cells"][0]
        self.assertEqual((cell["class"], cell["confirmed"]), ("no-benefit", False),
                         cell["reason"])
        self.assertEqual(cell["main_rest"]["class"], "ceiling")

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

    def test_unconfirmed_never_becomes_shorten_or_merge(self):
        alone = stratum("none", GAIN + GAIN, FLAT, judges=([8.0] * 20, FLAT_JUDGE),
                        pair="alone")
        v = verdict(stratum(OLD, FLAT, FLAT) + alone)
        self.assertEqual(v["alone"]["verdict"], "keep")
        self.assertEqual((v["in_situ_verdict"], v["verdict"]),
                         ("retire-unconfirmed", "retire-unconfirmed"))
        confirmed = verdict(stratum(MAIN, FLAT, FLAT) + alone)
        self.assertEqual(confirmed["verdict"], "shorten-or-merge")


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
        self.assertNotEqual(priors["objective"], 0.25)
        means = [gates.run_numbers(r["trials"], True)["run_mean"] for r in runs]
        self.assertAlmostEqual(priors["objective"],
                               gates.pooled_variance([means[:20], means[20:]]), places=12)


class ConsumerTests(unittest.TestCase):

    def gates_doc(self, runs):
        return {"guidance": {"sec": verdict(runs)}, "roster_models": ["model-a"], "skills": {}}

    def test_retire_skill_refuses_an_unconfirmed_cell(self):
        doc = self.gates_doc(stratum(MAIN, FLAT, FLAT))
        self.assertEqual(rs.guidance_retiring(doc), "sec")
        doc["guidance"]["sec"]["cells"][0]["confirmed"] = False
        with self.assertRaises(rs.RetireError):
            rs.guidance_retiring(doc)
        doc["guidance"]["sec"]["cells"][0]["confirmed"] = True
        doc["guidance"]["sec"]["cells"][0]["key"]["main_rest"] = None
        with self.assertRaises(rs.RetireError):
            rs.guidance_retiring(doc)

    def test_retire_unconfirmed_is_not_a_retirement(self):
        doc = self.gates_doc(stratum(OLD, FLAT, FLAT))
        self.assertEqual(doc["guidance"]["sec"]["verdict"], "retire-unconfirmed")
        self.assertIsNone(rs.guidance_retiring(doc))

    def test_the_explorer_shows_no_removal_confidence_until_confirmed(self):
        unconfirmed = verdict(stratum(OLD, FLAT, FLAT))
        self.assertEqual(explorer_data.subject_confidence(unconfirmed)["no_help"], 0.0)
        confirmed = verdict(stratum(MAIN, FLAT, FLAT))
        cell = confirmed["cells"][0]
        self.assertEqual(explorer_data.subject_confidence(confirmed)["no_help"],
                         min(cell["objective"]["no_help_confidence"],
                             cell["main_rest"]["objective"]["no_help_confidence"],
                             cell["main_rest"]["judge"]["no_help_confidence"]))


if __name__ == "__main__":
    unittest.main()
