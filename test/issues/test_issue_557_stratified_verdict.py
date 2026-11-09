#!/usr/bin/env python3
"""skills-evals#557: in-situ guidance cells and the rest of the guidance.

#557 pooled an in-situ cell's runs across every rest of the guidance they
ran beside, as inverse-variance weighted strata. The statistics review of
2026-11-03 found that weighting favored removal, so since then an in-situ
cell decides on the runs beside the CURRENT rest of the guidance only
(`expected`'s `rest_digest`); runs beside an older rest are ignored. Covered
here: harness/gates.py `pool_cells(strata=True)` and `guidance_verdict` on
that rule, errored trials (which do not block a guidance removal), ceiling
parking and the shorten-or-merge twist. With the judge reported but not
voting, a skipped or missing judge figure no longer blocks anything.

Since 2026-11-07 that rule is `rest_policy: current` in the guidance block
of evals/gate-policy.yml, kept so the gate can be switched back; the tests
here run under it, and pin that it reproduces the old outputs. The default,
`pooled-with-current-guard`, is tested in test_issue_pooled_rest_guard.py.

Skills and the alone pair keep their own tests (test_issue_70_retirement.py,
test_issue_124_guidance_gates.py).

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
from test_issue_70_retirement import (FLAT, FLAT_DECIDES, FLAT_JUDGE, GAIN, LOSS,  # noqa: E402
                                      TEST_POLICY, series, trial)

MAIN, OLD = "rest-main", "rest-old"
EXPECT = {"fx": {"fixture_digest": "f1", "tested_digest": "t1", "rest_digest": MAIN}}
CEILING = [(100, 100, 100)] * 20


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


#: This module pins the 2026-11-03 rule, which `rest_policy: current` keeps
#: (the pooled rule of 2026-11-07 is test_issue_pooled_rest_guard.py's).
CURRENT_POLICY = {**TEST_POLICY, "rest_policy": "current"}


def verdict(runs, models=("model-a",), expect=EXPECT, policy=CURRENT_POLICY):
    return gates.guidance_verdict({"runs": runs}, list(models), "sec", policy, expect)


class PoolingTests(unittest.TestCase):

    def test_cells_hold_only_the_current_rest_and_their_own_key(self):
        runs = (stratum(OLD, FLAT[:4], FLAT[:4]) + stratum(MAIN, FLAT[:3], FLAT[:3], start=4)
                + stratum(OLD, FLAT[:2], FLAT[:2], model="model-b"))
        cells = gates.pool_cells(runs, "sec", ["model-a", "model-b"], EXPECT, strata=True,
                                 rest_policy="current")
        a, b = cells[("fx", "model-a")], cells[("fx", "model-b")]
        self.assertEqual(list(a["strata"]), [MAIN])
        self.assertEqual((len(a["with"]), len(a["without"])), (3, 3))
        self.assertEqual(a["key"], {"tested_digest": "t1", "fixture_digest": "f1",
                                    "rest_digest": MAIN})
        self.assertIsNot(a["key"], b["key"])
        # model-b ran only beside an older rest: nothing of it is pooled.
        self.assertEqual((b["strata"], b["with"], b["without"]), ({}, [], []))
        # Its runs still show the planner that fires landed.
        self.assertEqual(len(b["run_stamps_on_model"]), 4)

    def test_other_content_never_enters_a_cell(self):
        runs = stratum(MAIN, FLAT[:2], FLAT[:2])
        for run in runs[:1]:
            run["tested_digest"] = "t0"  # an older section text
        cells = gates.pool_cells(runs, "sec", ["model-a"], EXPECT, strata=True,
                                 rest_policy="current")
        self.assertEqual(len(cells[("fx", "model-a")]["with"]), 1)

    def test_without_the_section_on_main_the_key_is_incomplete(self):
        expect = {"fx": {**EXPECT["fx"], "tested_digest": None}}
        v = verdict(stratum(MAIN, FLAT, FLAT), expect=expect)
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIn("tested_digest", v["cells"][0]["reason"])

    def test_without_the_rest_on_main_nothing_pools(self):
        expect = {"fx": {**EXPECT["fx"], "rest_digest": None}}
        v = verdict(stratum(MAIN, FLAT, FLAT), expect=expect)
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIn("rest_digest", v["cells"][0]["reason"])


class ClassifyTests(unittest.TestCase):

    def test_the_current_rest_retires(self):
        v = verdict(stratum(MAIN, FLAT, FLAT))
        cell = v["cells"][0]
        self.assertEqual((v["verdict"], cell["class"]), ("retire", "no-benefit"), cell["reason"])
        self.assertEqual(cell["key"]["rest_digest"], MAIN)
        # One cell with headroom: a removal can only be proposed.
        self.assertEqual(v["removal"], "proposal")

    def test_older_rests_are_ignored(self):
        # Ten pairs beside an old rest and ten beside main: only main's ten
        # count, short of the eighteen identical pairs a removal needs. The
        # same twenty beside main retire.
        split = verdict(stratum(OLD, FLAT[:10], FLAT[:10])
                        + stratum(MAIN, FLAT[10:], FLAT[10:], start=10))
        self.assertEqual(split["verdict"], "insufficient")
        self.assertEqual(split["cells"][0]["pairs"], 10)
        self.assertEqual(verdict(stratum(MAIN, FLAT, FLAT))["verdict"], "retire")

    def test_a_benefit_beside_an_old_rest_no_longer_keeps(self):
        runs = stratum(OLD, GAIN, LOSS) + stratum(MAIN, FLAT[:2], FLAT[:2], start=20)
        v = verdict(runs)
        self.assertEqual(v["verdict"], "insufficient", v["cells"][0]["reason"])
        self.assertEqual(v["cells"][0]["pairs"], 2)
        # Beside main, the same runs keep.
        self.assertEqual(verdict(stratum(MAIN, GAIN, LOSS))["verdict"], "keep")

    def test_runs_beside_an_old_rest_are_not_used(self):
        runs = stratum(MAIN, FLAT, FLAT) + series(
            "with", FLAT[:2], FLAT_JUDGE, start=30, skill="sec", fixture="fx", ctx=OLD,
            pair=OLD)
        for run in runs[-2:]:
            run["pair"] = "in_situ"
            run["path"] += "#old-only"
        v = verdict(runs)
        cell = v["cells"][0]
        self.assertEqual(cell["key"]["rest_digest"], MAIN)
        self.assertEqual(len(cell["runs"]["with"]), 20)
        self.assertEqual(len(v["runs_used"]), 40)
        self.assertEqual(v["verdict"], "retire")

    def test_an_errored_trial_scores_zero_and_does_not_block_removal(self):
        # T3's review: at the run counts a guidance verdict needs, one errored
        # trial must not block a cell for good. It scores 0 on every check of
        # its arm, so it is a bad result, never one left out.
        runs = stratum(MAIN, FLAT, FLAT)
        lone = runs[0]
        lone["trials"][0] = {**lone["trials"][0], "scored": False, "errored": True,
                             "checks": {}, "judge": None}
        v = verdict(runs)
        cell = v["cells"][0]
        self.assertEqual(cell["errored_trials"], 1)
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertLess(cell["with"]["mean_of_run_means"], cell["without"]["mean_of_run_means"])

    def test_an_anomalous_run_still_blocks_removal(self):
        runs = stratum(MAIN, FLAT, FLAT)
        runs[0]["trials"][0] = {**runs[0]["trials"][0], "checks": {}}
        runs[0]["fixture_checks"] = True
        self.assertEqual(verdict(runs)["cells"][0]["class"], "insufficient")

    def test_a_ceiling_cell_is_parked(self):
        # The review's C2 (2026-11-03): a without arm above 1 - margin cannot
        # show the margin, so the cell parks and the section is `ceiling`,
        # never removed for it.
        v = verdict(stratum(MAIN, CEILING, CEILING))
        self.assertEqual((v["cells"][0]["class"], v["verdict"]), ("ceiling", "ceiling"))
        self.assertNotIn("removal", v)

    def test_a_retire_that_helps_alone_is_shorten_or_merge(self):
        alone = stratum("none", GAIN, LOSS, judges=([8.0] * 20, FLAT_JUDGE), pair="alone")
        v = verdict(stratum(MAIN, FLAT, FLAT) + alone)
        self.assertEqual((v["in_situ_verdict"], v["alone"]["verdict"], v["verdict"]),
                         ("retire", "keep", "shorten-or-merge"))
        self.assertNotIn("removal", v)


class JudgeDoesNotBlockTests(unittest.TestCase):
    """T3's review (#557) found that requiring every run's judge figure, when
    guidance runs skip the judge whenever the with arm is ahead, meant a cell
    could never retire. Since 2026-11-03 the judge does not vote, so no
    missing figure, skipped or otherwise, holds a removal back; the judge is
    reported only when every figure is there."""

    def skipped(self, runs, which):
        for run in runs:
            if run["timestamp"] in which:
                run["trials"] = [gates.trial_record(trial(80, skipped=True))
                                 for _ in run["trials"]]
        return runs

    def runs(self):
        return stratum(MAIN, FLAT, FLAT, conditional=True)

    def test_with_ahead_skips_let_the_objective_retire(self):
        runs = self.runs()
        stamps = sorted({r["timestamp"] for r in runs})[:5]
        v = verdict(self.skipped(runs, stamps))
        cell = v["cells"][0]
        self.assertEqual((v["verdict"], cell["class"]), ("retire", "no-benefit"), cell["reason"])
        self.assertIsNone(cell["judge"])

    def test_a_judge_missing_for_another_reason_does_not_block(self):
        runs = self.runs()
        stamps = sorted({r["timestamp"] for r in runs})
        runs = self.skipped(runs, stamps[:5])
        other = next(r for r in runs if r["timestamp"] == stamps[6])
        other["trials"] = [gates.trial_record(trial(80)) for _ in other["trials"]]  # no judge
        cell = verdict(runs)["cells"][0]
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])

    def test_skills_do_not_need_every_judge_figure_either(self):
        runs = self.skipped(self.runs(), sorted({r["timestamp"] for r in self.runs()})[:5])
        with_runs = [r for r in runs if r["role"] == "with"]
        without_runs = [r for r in runs if r["role"] == "without"]
        cell = gates.classify_cell(with_runs, without_runs, TEST_POLICY)
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertGreaterEqual(cell["pairs"], FLAT_DECIDES)


if __name__ == "__main__":
    unittest.main()
