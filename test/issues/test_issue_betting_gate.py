#!/usr/bin/env python3
"""The 2026-11-03 gate rule: a betting confidence sequence on paired fires.

The statistics review of 2026-11-03 found the old normal-mixture bound
invalid where it decided (four identical runs per arm removed a skill), and a
threshold sweep the same day chose the replacement, which harness/gates.py
documents (THE PAIR IS THE UNIT, THE BOUNDS, THE VERDICT, THE BET PRIOR).
Covered here, beside the module's own suites:

  * a seeded coverage simulation: under each test's null the rejection rate
    stays within alpha plus a tolerance, with the neutral bet prior and with
    deliberately wrong learned priors at the clamps;
  * the review's repro: identical runs never give `no-benefit` before the
    bound can show it, whatever prior the clamps allow;
  * ceiling parking, in the gate and in the planner;
  * the run cap: `no-clear-effect`, which counts as headroom for a removal;
  * the removal mode: one headroom cell proposes, two or more no-benefit
    cells may remove automatically;
  * the judge is reported and does not vote;
  * the learned bet prior: its clamps, its version and what it may read.

Hermetic and deterministic: seeded generators, canned runs, no network, no
clock.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import gates  # noqa: E402
import plan_week  # noqa: E402
from test_issue_70_retirement import (CLIS, EXPECT, FLAT, FLAT_DECIDES, GAIN,  # noqa: E402
                                      LOSS, POLICY, cell, series, trial)

MARGIN = POLICY["objective_margin"]
KEEP_ALPHA = 1 - POLICY["benefit_confidence"]
REMOVE_ALPHA = 1 - POLICY["retire_confidence"]
CAP = POLICY["max_runs_per_cell"]
#: Learned priors at the clamps, each as wrong as the clamps allow for the
#: null it is tested under.
EAGER_KEEP = {"mean": gates.PRIOR_MEAN_RANGE[1], "variance": gates.PRIOR_MIN_VARIANCE,
              "n": gates.PRIOR_PSEUDO_RUNS}
EAGER_REMOVE = {"mean": gates.PRIOR_MEAN_RANGE[0], "variance": gates.PRIOR_MIN_VARIANCE,
                "n": gates.PRIOR_PSEUDO_RUNS}


def binary_pairs(rng, n, base, delta):
    """`n` paired differences of {0, 1} outcomes: the without arm passes
    with probability `base`; the with arm is an independent draw from the
    same distribution, lifted to 1 with the probability that makes
    E[with] - E[without] exactly `delta` (the threshold sweep's model)."""
    lift = delta / (1 - base)
    out = []
    for _ in range(n):
        without = 1.0 if rng.random() < base else 0.0
        with_ = 1.0 if rng.random() < base or rng.random() < lift else 0.0
        out.append(with_ - without)
    return out


def spread_pairs(rng, n, mean, width):
    """`n` differences `mean` +/- a uniform draw up to `width`: symmetric, so
    E[D] is exactly `mean`."""
    return [mean + rng.choice((-1, 1)) * rng.uniform(0, width) for _ in range(n)]


def rejection_rate(draw, test, alpha, reps=400, seed=20261103):
    rng = random.Random(seed)
    hits = sum(gates.first_crossing(test(draw(rng)), alpha) is not None for _ in range(reps))
    return hits / reps


def tolerance(alpha, reps=400):
    """Three standard errors of a rate of `alpha` over `reps` draws."""
    return 3 * (alpha * (1 - alpha) / reps) ** 0.5


class CoverageTests(unittest.TestCase):
    """Ville's inequality bounds each test's rejection rate under its null by
    its alpha, at every pair count, whatever the bets, as long as each bet
    uses only earlier pairs. A rate over alpha plus three standard errors
    over 400 seeded paths would mean the bound is not valid."""

    def check(self, draw, test, alpha):
        rate = rejection_rate(draw, test, alpha)
        self.assertLessEqual(rate, alpha + tolerance(alpha), f"rate {rate} at alpha {alpha}")
        return rate

    def test_the_keep_test_holds_its_level_when_nothing_helps(self):
        for base in (0.3, 0.6):
            with self.subTest(base=base):
                self.check(lambda rng, b=base: binary_pairs(rng, CAP, b, 0.0),
                           gates.keep_wealth, KEEP_ALPHA)
        self.check(lambda rng: spread_pairs(rng, CAP, 0.0, 0.9), gates.keep_wealth, KEEP_ALPHA)

    def test_the_remove_test_holds_its_level_at_the_margin(self):
        # A subject that helps by exactly the margin is the hardest case the
        # removal rule must not call no-benefit.
        for base in (0.3, 0.6):
            with self.subTest(base=base):
                self.check(lambda rng, b=base: binary_pairs(rng, CAP, b, MARGIN),
                           lambda ds: gates.remove_wealth(ds, MARGIN), REMOVE_ALPHA)
        self.check(lambda rng: spread_pairs(rng, CAP, MARGIN, 0.8),
                   lambda ds: gates.remove_wealth(ds, MARGIN), REMOVE_ALPHA)

    def test_a_wrong_learned_prior_cannot_break_the_level(self):
        # The prior only seeds the bets, so a prior as wrong as the clamps
        # allow costs power, never validity.
        self.check(lambda rng: binary_pairs(rng, CAP, 0.5, 0.0),
                   lambda ds: gates.keep_wealth(ds, EAGER_KEEP), KEEP_ALPHA)
        self.check(lambda rng: binary_pairs(rng, CAP, 0.5, MARGIN),
                   lambda ds: gates.remove_wealth(ds, MARGIN, EAGER_REMOVE), REMOVE_ALPHA)

    def test_the_simulation_can_fail(self):
        # The negative control: a test run at 1/alpha too low a wealth, or
        # under the wrong null, rejects far more often than alpha.
        rate = rejection_rate(lambda rng: binary_pairs(rng, CAP, 0.5, MARGIN),
                              lambda ds: gates.remove_wealth(ds, MARGIN + 0.15),
                              REMOVE_ALPHA)
        self.assertGreater(rate, REMOVE_ALPHA + tolerance(REMOVE_ALPHA))

    def test_the_tests_find_a_real_effect(self):
        # Power, so the level is not met by never deciding: within the cap,
        # a clear gain keeps and a null effect of moderate spread is found
        # under the margin. (Arms that only pass or fail, D in {-1, 0, 1},
        # are far slower to remove: about a quarter of such cells reach the
        # cap undecided, which is what `no-clear-effect` is for.)
        keep = rejection_rate(lambda rng: binary_pairs(rng, CAP, 0.4, 0.4),
                              gates.keep_wealth, KEEP_ALPHA, reps=100)
        remove = rejection_rate(lambda rng: spread_pairs(rng, CAP, 0.0, 0.3),
                                lambda ds: gates.remove_wealth(ds, MARGIN),
                                REMOVE_ALPHA, reps=100)
        self.assertGreater(keep, 0.9)
        self.assertGreater(remove, 0.9)


class IdenticalRunsTests(unittest.TestCase):
    """The review's repro: four identical runs per arm removed a skill,
    because a variance prior read their zero spread as certainty."""

    def test_four_identical_runs_never_give_no_benefit(self):
        priors = (None, EAGER_KEEP, EAGER_REMOVE,
                  {"mean": 0.0, "variance": gates.PRIOR_MIN_VARIANCE,
                   "n": gates.PRIOR_PSEUDO_RUNS})
        for passed in (0, 50, 80):
            for prior in priors:
                for n in range(1, 5):
                    with self.subTest(passed=passed, prior=prior, n=n):
                        pattern = [(passed,) * 3] * n
                        result = cell(series("with", pattern), series("without", pattern),
                                      bet_prior=prior)
                        self.assertNotEqual(result["class"], "no-benefit", result["reason"])
                        self.assertIsNone(result["objective"]["remove_at"]
                                          if result["objective"] else None)

    def test_identical_flat_arms_take_eighteen_pairs_on_neutral_bets(self):
        for n, want in ((FLAT_DECIDES - 1, "insufficient"), (FLAT_DECIDES, "no-benefit")):
            with self.subTest(n=n):
                result = cell(series("with", FLAT[:n]), series("without", FLAT[:n]))
                self.assertEqual(result["class"], want, result["reason"])


class VerdictTests(unittest.TestCase):

    def verdict(self, runs, models=("model-a", "model-b")):
        return gates.retirement({"runs": runs}, list(models), "demo", POLICY, EXPECT)

    @staticmethod
    def arms(with_patterns, without_patterns, model):
        return (series("with", with_patterns, model=model)
                + series("without", without_patterns, model=model))

    def test_a_ceiling_cell_is_parked_and_an_all_ceiling_subject_is_ceiling(self):
        top = [(96, 96, 96), (96, 96, 95)] * 12
        result = self.verdict(self.arms(top, top, "model-a") + self.arms(top, top, "model-b"))
        self.assertEqual([c["class"] for c in result["cells"]], ["ceiling", "ceiling"])
        self.assertEqual(result["verdict"], "ceiling")
        self.assertNotIn("removal", result)
        self.assertFalse(result["cells"][0]["headroom"])
        # Until the ceiling test rejects, a high without arm is not parked...
        early = self.verdict(self.arms(top[:19], top[:19], "model-a"), ["model-a"])
        self.assertEqual(early["cells"][0]["class"], "insufficient")
        # ...and at `max_runs_high_cell` pairs undecided it stops as
        # `ceiling-unconfirmed` (round 2's M2), which does not vote either.
        stop = self.verdict(self.arms(top[:20], top[:20], "model-a")
                            + self.arms(top[:20], top[:20], "model-b"))
        self.assertEqual([c["class"] for c in stop["cells"]],
                         ["ceiling-unconfirmed"] * 2)
        self.assertEqual(stop["verdict"], "ceiling")

    def test_a_three_pair_ceiling_never_parks_a_cell_or_frees_a_removal(self):
        # Round 1's C1, the reviewer's direct repro: three perfect pairs on
        # fixture a, eighteen flat pairs on b and c. A sample mean once
        # parked a for good and let b and c remove the subject automatically.
        def pairs(fixture, n, without, with_, start):
            return (series("with", [(with_,)] * n, start=start, fixture=fixture)
                    + series("without", [(without,)] * n, start=start, fixture=fixture))
        expect = {k: dict(EXPECT[""]) for k in "abc"}
        runs = pairs("a", 3, 100, 100, 0) + pairs("b", 18, 50, 50, 10) \
            + pairs("c", 18, 50, 50, 40)
        result = gates.retirement({"runs": runs}, ["model-a"], "demo", POLICY, expect)
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["insufficient", "no-benefit", "no-benefit"])
        self.assertEqual(result["verdict"], "insufficient")
        self.assertNotEqual(result.get("removal"), "auto")
        # Even once a's ceiling is confirmed, it parks and does not vote.
        runs = pairs("a", 18, 100, 100, 70) + pairs("b", 18, 50, 50, 10) \
            + pairs("c", 18, 50, 50, 40)
        result = gates.retirement({"runs": runs}, ["model-a"], "demo", POLICY, expect)
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["ceiling", "no-benefit", "no-benefit"])
        self.assertEqual((result["verdict"], result["removal"]), ("retire", "auto"))

    def test_harm_at_the_ceiling_is_not_hidden(self):
        # Round 1's M1, the reviewer's repro: without 95/100, with 40/100 on
        # two cells, 40 pairs. The harm test needs no headroom.
        def pairs(fixture, n):
            return (series("with", [(40,)] * n, fixture=fixture)
                    + series("without", [(95,)] * n, fixture=fixture))
        expect = {k: dict(EXPECT[""]) for k in "ab"}
        result = gates.retirement({"runs": pairs("a", 40) + pairs("b", 40)}, ["model-a"],
                                  "demo", POLICY, expect)
        self.assertEqual([c["class"] for c in result["cells"]], ["no-benefit", "no-benefit"])
        self.assertIn("harm test decided at pair 7", result["cells"][0]["reason"])
        self.assertEqual(result["verdict"], "retire")
        self.assertIn(result["removal"], ("auto", "proposal"))
        # It is found long before the ceiling test could park the cell, at
        # the retire level 0.90 (a looser level would cross sooner), and it
        # needs no ceiling bound: at 10 pairs the ceiling has not rejected.
        self.assertEqual(result["cells"][0]["harm_at"], 7)
        self.assertEqual(result["cells"][0]["harm_at"],
                         gates.first_crossing(gates.harm_wealth([-0.55] * 40), 0.10))
        self.assertGreater(gates.first_crossing(gates.harm_wealth([-0.55] * 40), 0.10),
                           gates.first_crossing(gates.harm_wealth([-0.55] * 40), 0.5))
        short = gates.retirement({"runs": pairs("a", 10) + pairs("b", 10)}, ["model-a"],
                                 "demo", POLICY, expect)
        self.assertIsNone(short["cells"][0]["ceiling_at"])
        self.assertEqual([c["class"] for c in short["cells"]], ["no-benefit", "no-benefit"])

    def test_a_keep_and_remove_tie_keeps(self):
        # Both tests rejecting at the same pair: the keep wins (the review's
        # surviving mutation). With margin 0.6, a constant D = 0.4 is a gain
        # above 0 and under the margin, and both tests reach 1/alpha at pair 9.
        policy = {**POLICY, "objective_margin": 0.6, "benefit_confidence": 0.9}
        block = gates.sequence_block([0.4] * 12, 0.6, 0.1, 0.1)
        self.assertEqual((block["keep_at"], block["remove_at"]), (9, 9))
        result = cell(series("with", [(60,)] * 12), series("without", [(20,)] * 12),
                      policy=policy)
        self.assertEqual(result["objective"]["keep_at"], result["objective"]["remove_at"])
        self.assertEqual(result["class"], "benefit", result["reason"])

    def test_the_cap_gives_no_clear_effect_which_still_retires_automatically(self):
        # A swing of D = +0.3, -0.2 (a gain of 0.05): neither test decides
        # in the cap's 40 pairs.
        swing = [(50, 50, 50), (0, 0, 0)] * 20
        mid = [(20, 20, 20), (20, 20, 20)] * 20
        capped = self.arms(swing, mid, "model-a")
        result = self.verdict(capped + self.arms(FLAT, FLAT, "model-b"))
        classes = {c["model"]: c["class"] for c in result["cells"]}
        self.assertEqual(classes, {"model-a": "no-clear-effect", "model-b": "no-benefit"})
        # Adam, 2026-11-13: every retire is automatic.
        self.assertEqual((result["verdict"], result["removal"]), ("retire", "auto"))
        self.assertIn("run cap", result["removal_reason"])
        # One pair short of the cap, it is still open.
        short = self.verdict(self.arms(swing[:CAP - 1], mid[:CAP - 1], "model-a"),
                             ["model-a"])
        self.assertEqual(short["cells"][0]["class"], "insufficient")

    def test_an_errored_capped_cell_cannot_propose_a_removal(self):
        # Round 1's m4: at the cap, a cell with an agent-errored trial is
        # insufficient, as an errored no-benefit cell already was.
        swing = [(50, 50, 50), (0, 0, 0)] * 20
        mid = [(20, 20, 20), (20, 20, 20)] * 20
        with_runs = series("with", swing)
        with_runs[1]["trials"][0] = gates.trial_record(trial(error="timeout"))
        result = cell(with_runs, series("without", mid), policy=POLICY)
        self.assertEqual(result["class"], "insufficient", result["reason"])
        self.assertTrue(result["reason"].startswith(
            "no-clear-effect on the numbers, but the cell has"), result["reason"])
        # The planner sees it as blocking: more runs cannot move it.
        self.assertTrue(plan_week._blocking({**result, "class": "insufficient"}))

    def test_a_removal_decides_at_a_stopping_time_over_cli_versions(self):
        # Round 2's C1, replacing round 1's m1 test that enshrined the bug: a
        # removal decides at the first pair where the test's wealth is at
        # its level AND the pairs so far span 2 CLI versions. Ville bounds
        # that stopping time as it bounds the first crossing.
        def run(cells):
            with_runs = [series("with", [(w,)], start=i, cli=c)[0]
                         for i, (w, _, c) in enumerate(cells)]
            without_runs = [series("without", [(o,)], start=i, cli=c)[0]
                            for i, (_, o, c) in enumerate(cells)]
            return cell(with_runs, without_runs, policy=POLICY)
        v1 = [(80, 80, CLIS[0])] * FLAT_DECIDES
        # A flat pair on the second version, wealth still at the level: decided.
        decided = run(v1 + [(80, 80, CLIS[1])])
        self.assertEqual((decided["class"], decided["objective"]["remove_at"],
                          decided["remove_decided_at"]), ("no-benefit", FLAT_DECIDES, 19))
        self.assertIn("decided at pair 19 (crossed at 18)", decided["reason"])
        # A D = +1 pair on the second version knocks the wealth under its
        # level: round 1's m1 worry, a late pair rescuing a one-version
        # decision, still cannot happen.
        knocked = run(v1 + [(100, 0, CLIS[1])])
        self.assertEqual(knocked["class"], "insufficient", knocked["reason"])
        self.assertIsNone(knocked["remove_decided_at"])

    def test_round_two_cli_repros_reach_no_benefit(self):
        # Round 2's C1 repros: each stayed `insufficient` (and was fired)
        # forever because its first crossing was on one CLI version.
        def pairs(fixture, n, without, with_, cli, start=0):
            return [r for i in range(start, start + n) for r in
                    (series("without", [(without,)], start=i, fixture=fixture, cli=cli(i))[0],
                     series("with", [(with_,)], start=i, fixture=fixture, cli=cli(i))[0])]
        two = {k: dict(EXPECT[""]) for k in "ab"}
        # Flat, 65 pairs, v1 for the first 25.
        flat = (pairs("a", 65, 50, 50, lambda i: CLIS[i >= 25])
                + pairs("b", 65, 50, 50, lambda i: CLIS[i >= 125], start=100))
        result = gates.retirement({"runs": flat}, ["model-a"], "demo", POLICY, two)
        self.assertEqual([(c["class"], c["remove_decided_at"]) for c in result["cells"]],
                         [("no-benefit", 26)] * 2)
        self.assertEqual(result["verdict"], "retire")
        # Clearly harmful (D = -0.5), v1 for the first 10 pairs, then mixed.
        mixed = lambda i: CLIS[0] if i % 100 < 10 else CLIS[i % 2 == 0]  # noqa: E731
        harmful = pairs("a", 40, 70, 20, mixed) + pairs("b", 40, 70, 20, mixed, start=100)
        result = gates.retirement({"runs": harmful}, ["model-a"], "demo", POLICY, two)
        self.assertEqual([(c["class"], c["remove_decided_at"]) for c in result["cells"]],
                         [("no-benefit", 11)] * 2)
        # Harm at the ceiling (100 vs 40), v1 for 30 pairs then v2: the harm
        # test decides on the first v2 pair, never earlier.
        one = {"a": dict(EXPECT[""])}
        for n, want in ((30, ("insufficient", None)), (60, ("no-benefit", 31))):
            runs = pairs("a", n, 100, 40, lambda i: CLIS[i >= 30])
            got = gates.retirement({"runs": runs}, ["model-a"], "demo", POLICY, one)
            c = got["cells"][0]
            self.assertEqual((c["class"], c["harm_decided_at"]), want, c["reason"])

    def test_a_ceiling_parks_only_when_the_no_harm_test_rejects(self):
        # Round 2's M1, the reviewer's repro: without 100/100, with 85/100
        # (D = -0.15). The ceiling test rejects at pair 18, but the no-harm
        # test (H0: E[D] <= -margin) cannot, so the cell is fired on and the
        # harm test decides at pair 20.
        def runs(n):
            return series("with", [(85,)] * n) + series("without", [(100,)] * n)
        for n, want in ((18, "insufficient"), (19, "insufficient"), (20, "no-benefit")):
            c = cell(runs(n)[:n], runs(n)[n:], policy=POLICY)
            self.assertEqual(c["class"], want, (n, c["reason"]))
            self.assertIsNone(c["noharm_at"])
        self.assertEqual(cell(runs(20)[:20], runs(20)[20:], policy=POLICY)["ceiling_at"], 18)
        # Equal arms at the top park at pair 18, the no-harm test with them.
        top = series("with", [(100,)] * 18) + series("without", [(100,)] * 18)
        c = cell(top[:18], top[18:], policy=POLICY)
        self.assertEqual((c["class"], c["ceiling_at"], c["noharm_at"]), ("ceiling", 18, 18))

    def test_a_ceiling_unconfirmed_cell_does_not_vote_beside_a_removal(self):
        # Round 2's M2: beside two no-benefit cells, a stopped high cell
        # does not vote, as a ceiling cell does (the removal is automatic
        # all the same since 2026-11-13).
        def pairs(fixture, n, without, with_, start):
            return (series("with", [(with_,)] * n, start=start, fixture=fixture)
                    + series("without", [(without,)] * n, start=start, fixture=fixture))
        expect = {k: dict(EXPECT[""]) for k in "abc"}
        runs = pairs("a", 20, 90, 90, 0) + pairs("b", 18, 50, 50, 30) \
            + pairs("c", 18, 50, 50, 60)
        result = gates.retirement({"runs": runs}, ["model-a"], "demo", POLICY, expect)
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["ceiling-unconfirmed", "no-benefit", "no-benefit"])
        self.assertEqual((result["verdict"], result["removal"]), ("retire", "auto"))
        self.assertIn("parked cell", result["removal_reason"])

    def test_one_headroom_cell_and_two_both_remove_automatically(self):
        one = self.verdict(self.arms(FLAT, FLAT, "model-a"), ["model-a"])
        self.assertEqual((one["verdict"], one["removal"]), ("retire", "auto"))
        self.assertIn("only 1 cell with headroom", one["removal_reason"])
        top = [(100, 100, 100)] * 18
        beside_a_ceiling = self.verdict(self.arms(FLAT, FLAT, "model-a")
                                        + self.arms(top, top, "model-b"))
        self.assertEqual((beside_a_ceiling["verdict"], beside_a_ceiling["removal"]),
                         ("retire", "auto"))
        two = self.verdict(self.arms(FLAT, FLAT, "model-a") + self.arms(FLAT, FLAT, "model-b"))
        self.assertEqual((two["verdict"], two["removal"]), ("retire", "auto"))

    def test_the_judge_is_reported_and_does_not_vote(self):
        # A judge that loves the with arm cannot keep a flat objective...
        loved = (series("with", FLAT, [9.5] * 20) + series("without", FLAT, [3.0] * 20))
        result = cell(loved[:20], loved[20:])
        self.assertEqual(result["class"], "no-benefit", result["reason"])
        self.assertGreater(result["judge"]["helps_confidence"], 0.99)
        self.assertIs(result["judge"]["votes"], False)
        self.assertEqual([t["route"] for t in result["keep_tests"]], ["objective"])
        # ...and a judge that sees nothing cannot block a clear objective gain.
        unmoved = (series("with", GAIN, [7.0] * 10) + series("without", LOSS, [7.0] * 10))
        result = cell(unmoved[:10], unmoved[10:])
        self.assertEqual(result["class"], "benefit", result["reason"])
        self.assertEqual(result["judge"]["delta"], 0.0)


class PlannerTests(unittest.TestCase):

    def test_a_ceiling_cell_is_not_fired_and_asks_for_a_fixture(self):
        from test_issue_closed_loop_planner import NOW, cell as pcell, ctx
        cells = [pcell("evals/a", "heavy", "ceiling", runs=5),
                 pcell("evals/a", "light", "insufficient", runs=1)]
        plan = plan_week.build_plan(ctx(cells=cells, room=1.0), NOW)
        self.assertEqual([(f["fixture"], f["model"]) for f in plan["fires"]],
                         [("evals/a", "light")])
        self.assertIn({"kind": "fixture-ceiling", "change_type": "fixture", "skill": "a",
                       "fixture": "evals/a", "model": "heavy", "route": "summary"},
                      plan["work"])

    def test_parked_and_frozen_cells_are_not_fired(self):
        from test_issue_closed_loop_planner import NOW, cell as pcell, ctx
        item = {"kind": "fixture-ceiling", "change_type": "fixture", "skill": "a",
                "fixture": "evals/a", "model": "heavy", "route": "summary"}
        # Round 2's M2: a stopped high cell is parked as a ceiling cell is.
        cells = [pcell("evals/a", "heavy", "ceiling-unconfirmed", runs=20),
                 pcell("evals/a", "light", "insufficient", runs=1)]
        plan = plan_week.build_plan(ctx(cells=cells, room=1.0), NOW)
        self.assertEqual([(f["fixture"], f["model"]) for f in plan["fires"]],
                         [("evals/a", "light")])
        self.assertIn(item, plan["work"])
        # Round 2's m6: a kept subject's parked cell asks for nothing.
        for cls in ("ceiling", "ceiling-unconfirmed"):
            kept = [{**pcell("evals/a", "heavy", cls, runs=20), "verdict": "keep"}]
            self.assertNotIn(item, plan_week.build_plan(ctx(cells=kept, room=1.0),
                                                        NOW)["work"])
        # Round 2's C1: an undecided cell at `max_runs_per_cell` pairs is
        # frozen: it is not fired and it blocks its subject.
        frozen = {**pcell("evals/a", "heavy", "insufficient", runs=CAP), "at_cap": True,
                  "pairs": CAP}
        plan = plan_week.build_plan(ctx(cells=[frozen], room=1.0), NOW)
        self.assertEqual(plan["fires"], [])
        self.assertTrue(plan_week._blocking(frozen))
        self.assertFalse(plan_week._blocking({**frozen, "at_cap": False}))
        self.assertEqual(plan_week.batch_subjects({"cells": [frozen]})
                         [("skill", "a")]["status"], "blocked")


class BetPriorTests(unittest.TestCase):

    @staticmethod
    def history_cell(ds, without=0.5):
        return {"ds": ds, "without_mean": without}

    def test_the_fit_is_clamped(self):
        high = [self.history_cell([0.9, 0.9, 0.9]) for _ in range(3)]
        prior = gates.fit_bet_prior(high, MARGIN, "2026-11-02")
        self.assertEqual((prior["mean"], prior["variance"], prior["n"], prior["version"]),
                         (gates.PRIOR_MEAN_RANGE[1], gates.PRIOR_MIN_VARIANCE,
                          gates.PRIOR_PSEUDO_RUNS, "2026-11-02"))
        low = [self.history_cell([-0.9, -0.5]) for _ in range(3)]
        self.assertEqual(gates.fit_bet_prior(low, MARGIN)["mean"], gates.PRIOR_MEAN_RANGE[0])
        self.assertEqual(gates.PRIOR_PSEUDO_RUNS, 3.0)  # fixed, so within the n <= 5 clamp

    def test_too_few_cells_or_ceiling_cells_give_no_prior(self):
        two = [self.history_cell([0.1, 0.2]) for _ in range(2)]
        self.assertIsNone(gates.fit_bet_prior(two, MARGIN))
        # One-pair cells measure no spread, and ceiling cells are left out.
        self.assertIsNone(gates.fit_bet_prior(two + [self.history_cell([0.3])], MARGIN))
        self.assertIsNone(gates.fit_bet_prior(two + [self.history_cell([0.1, 0.0], 0.95)],
                                              MARGIN))
        self.assertIsNotNone(gates.fit_bet_prior(two + [self.history_cell([0.1, 0.0])],
                                                 MARGIN))

    def history(self):
        """Three other subjects' cells of two pairs each, in October, and the
        subject's own pairs, which the prior must never read."""
        out = []
        for i, subject in enumerate(("x", "y", "z")):
            for day, d in (("20261005T100000Z", 0.1 * i), ("20261006T100000Z", 0.2)):
                out.append({"subject": subject, "timestamp": day, "d": d, "without": 0.5,
                            "cell": (subject, "f", "m", None, "fd", "td", "pk", None)})
        for day in ("20261005T100000Z", "20261006T100000Z"):
            out.append({"subject": "demo", "timestamp": day, "d": 1.0, "without": 0.5,
                        "cell": ("demo", "f", "m", None, "fd", "td", "pk", None)})
        return out

    def test_the_prior_reads_only_other_subjects_before_the_monday(self):
        prior = gates.prior_from_history(self.history(), "demo", MARGIN)
        # A cell whose first pair is on Wednesday 2026-10-07 reads the pairs
        # before Monday 2026-10-05: none.
        self.assertIsNone(prior("20261007T120000Z"))
        # From the next week on, the other subjects' pairs; never demo's 1.0.
        fitted = prior("20261014T120000Z")
        self.assertEqual(fitted["version"], "2026-10-12")
        self.assertEqual(fitted["cells"], 3)
        self.assertAlmostEqual(fitted["mean"], (0.0 + 0.1 + 0.2 + 0.2 * 3) / 6, places=12)
        self.assertIsNone(prior("not a stamp"))

    def test_the_verdict_records_the_prior_it_bet_with(self):
        prior = {"mean": 0.1, "variance": 0.05, "n": 3.0, "cells": 4, "version": "2026-10-26"}
        runs = series("with", FLAT) + series("without", FLAT)
        result = gates.retirement({"runs": runs}, ["model-a"], "demo", POLICY, EXPECT,
                                  lambda first: prior)
        self.assertEqual(result["cells"][0]["bet_prior"], prior)


if __name__ == "__main__":
    unittest.main()
