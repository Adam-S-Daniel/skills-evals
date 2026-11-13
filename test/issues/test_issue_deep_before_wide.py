#!/usr/bin/env python3
"""DEEP BEFORE WIDE in the weekly planner (scripts/plan_week.py; Adam,
2026-11-08): of 3,010 eval runs, 1,354 sat in cells near zero confidence
either way, because sweeps spread a few runs over every subject. The
verdict-seeking bands now order cells by projected pairs to a verdict
(`pairs_to_verdict`), finish partly decided subjects first, rank a cell
projected past its cap last (a `cell-projected-past-cap` work item), and
hold a guidance section whose eval-coverage.yml row is `skipped`.

Hermetic: cells are dicts, `now` is passed in, the one file read is a
throwaway eval-coverage.yml; no network and no sleeps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import statistics
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import gates  # noqa: E402
import plan_week  # noqa: E402

NOW = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
# These orderings were calibrated at the 40-pair cap the policy had before
# 2026-11-12 (Adam cut it to 20); pin the cap they assume.
POLICY = {**gates.load_gate_policy()["skills"], "max_runs_per_cell": 40}
GUIDANCE_POLICY = {**gates.load_gate_policy()["guidance"], "max_runs_per_cell": 40}
MARGIN = POLICY["objective_margin"]
KEEP_ALPHA = 1 - POLICY["benefit_confidence"]
REMOVE_ALPHA = 1 - POLICY["retire_confidence"]


def measured_cell(ds, skill="s", fixture="a", model="heavy", cls="insufficient", **over):
    """A skill cell as plan_week.eval_cells builds it, its gate state computed
    by harness/gates.py over the paired differences `ds`."""
    block = gates.sequence_block(ds, MARGIN, KEEP_ALPHA, REMOVE_ALPHA, None)
    base = {"skill": skill, "section": None, "fixture": f"evals/{skill}/{fixture}",
            "model": model, "class": cls, "verdict": "insufficient",
            "with_runs": len(ds), "without_runs": len(ds), "newest": None,
            "usd_per_fire": None, "empty_fires": 0, "pairs": len(ds),
            "objective": block, "keep_tests": [{"route": "objective", "p": block["keep_p"]}],
            "keep_family": 1, "bet_prior": None,
            "d_variance": statistics.variance(ds) if len(ds) > 1 else None}
    base.update(over)
    return base


def plain_cell(skill, fixture="a", model="heavy", cls="missing", runs=0, **over):
    base = {"skill": skill, "section": None, "fixture": f"evals/{skill}/{fixture}",
            "model": model, "class": cls, "verdict": "insufficient", "with_runs": runs,
            "without_runs": runs, "newest": None, "usd_per_fire": None, "empty_fires": 0}
    base.update(over)
    return base


def gcell(section, name="a", cls="missing", model="heavy", **over):
    base = {"skill": "", "section": section, "fixture": f"evals/guidance/{section}/{name}",
            "model": model, "class": cls, "verdict": "insufficient", "with_runs": 0,
            "without_runs": 0, "newest": None, "usd_per_fire": None, "empty_fires": 0,
            "objective": None, "judge": None, "judge_carried": False, "reason": None,
            "with_counted": 0, "without_counted": 0}
    base.update(over)
    return base


def ctx(cells, **over):
    base = {"policy": POLICY, "guidance_policy": GUIDANCE_POLICY, "reservation": 0.035,
            "overrun": 0.005, "improve_charge": 0.10, "room": 1.0, "points_per_usd": None,
            "model_weights": {"heavy": 0.9}, "removal_prs": [], "cells": cells,
            "skills": {}, "lessons": []}
    base.update(over)
    return base


#: Paired differences: a strong effect (about 4 pairs to a keep), one near a
#: keep on more runs (about 5), a slow one on few runs (about 27) and a noisy
#: one whose projection (about 106) is past its cap.
STRONG = [0.6, 0.2, 0.6, 0.2]
CLOSE = [0.4, 0.0, 0.2, 0.4, 0.0, 0.2, 0.4, 0.0]
SLOW = [0.3, -0.1, 0.1, 0.2]
NOISY = [0.6, -0.4] * 6


class ProjectionTests(unittest.TestCase):

    def test_no_measured_d_has_no_projection(self):
        self.assertIsNone(plan_week.pairs_to_verdict(plain_cell("s"), ctx([])))

    def test_the_projection_tracks_the_gates_own_crossing(self):
        # The test sequences the gate would see, repeated: the projection
        # from the first six pairs lands within a factor of two of the pair
        # at which harness/gates.py's keep or remove test actually rejects.
        for pattern in ([0.6, 0.2], [0.4, 0.0, 0.2], [0.3, -0.1, 0.1, 0.2],
                        [0.0, 0.1, -0.1, 0.05], [0.1, 0.0]):
            with self.subTest(pattern=pattern):
                ds = (pattern * 200)[:400]
                crossings = [gates.first_crossing(gates.keep_wealth(ds), KEEP_ALPHA),
                             gates.first_crossing(gates.remove_wealth(ds, MARGIN),
                                                  REMOVE_ALPHA)]
                actual = min(c for c in crossings if c is not None) - 6
                projected = plan_week.pairs_to_verdict(measured_cell(ds[:6]), ctx([]))
                self.assertLessEqual(projected["pairs"], 2 * actual + 2)
                self.assertGreaterEqual(projected["pairs"], actual / 2)

    def test_a_strong_effect_needs_fewer_pairs_than_a_weak_one(self):
        strong = plan_week.pairs_to_verdict(measured_cell(STRONG), ctx([]))
        slow = plan_week.pairs_to_verdict(measured_cell(SLOW), ctx([]))
        self.assertLess(strong["pairs"], slow["pairs"])
        self.assertFalse(slow["past_cap"])

    def test_a_weak_noisy_cell_is_projected_past_its_cap(self):
        projection = plan_week.pairs_to_verdict(measured_cell(NOISY), ctx([]))
        self.assertTrue(projection["past_cap"])
        self.assertEqual(projection["remaining"], POLICY["max_runs_per_cell"] - len(NOISY))

    def test_too_few_pairs_are_never_past_the_cap(self):
        few = NOISY[:plan_week.PROJECTION_MIN_PAIRS - 1]
        projection = plan_week.pairs_to_verdict(measured_cell(few), ctx([]))
        self.assertGreater(projection["pairs"], projection["remaining"])
        self.assertFalse(projection["past_cap"])

    def test_a_provisional_keep_with_only_its_lapse_left_is_past_the_cap(self):
        # Its lapse at the cap is no keep (test_issue_planner_leaks.py): with
        # neither route under the cap it ranks last, not as a near verdict.
        cell = measured_cell(NOISY, provisional_keep=True, **{"class": "benefit"})
        self.assertTrue(plan_week.pairs_to_verdict(cell, ctx([]))["past_cap"])

    def test_the_betting_constants_match_the_gate(self):
        self.assertEqual(plan_week.BET_CAP, gates.BET_CAP)
        self.assertEqual(plan_week.NEUTRAL_BET_PRIOR, gates.NEUTRAL_BET_PRIOR)
        self.assertEqual(plan_week.MIN_BET_VARIANCE, gates.MIN_BET_VARIANCE)
        self.assertEqual(plan_week.PROJECTION_MIN_PAIRS, gates.PRIOR_PSEUDO_RUNS)


class OrderTests(unittest.TestCase):

    def near(self, cells, **over):
        bands, work = plan_week.eval_items(ctx(cells, **over), NOW)
        for band in bands.values():
            band.sort(key=lambda i: (*i["order"], i["cost"], i["fixture"], i["model"],
                                     i["skill"]))
        return [i["skill"] for i in bands["near"]], work

    def test_fewer_projected_pairs_go_first_not_fewer_runs(self):
        # The old order took the cell with the fewest runs first: the slow
        # one with four. Now the one nearer a verdict, on eight, leads.
        order, _work = self.near([measured_cell(SLOW, skill="slow"),
                                  measured_cell(CLOSE, skill="close")])
        self.assertEqual(order, ["close", "slow"])

    def test_a_cell_projected_past_its_cap_ranks_last_and_is_listed(self):
        order, work = self.near([measured_cell(NOISY, skill="hopeless"),
                                 plain_cell("fresh", cls="insufficient", runs=1),
                                 measured_cell(STRONG, skill="close")])
        self.assertEqual(order, ["close", "fresh", "hopeless"])
        flagged = [w for w in work if w["kind"] == "cell-projected-past-cap"]
        self.assertEqual([(w["skill"], w["route"], w["change_type"]) for w in flagged],
                         [("hopeless", plan_week.SUMMARY_ROUTE, "fixture")])
        self.assertGreater(flagged[0]["pairs"], flagged[0]["remaining"])

    def test_a_partly_decided_subject_is_finished_first(self):
        cells = [measured_cell(STRONG, skill="fresh"),
                 measured_cell(SLOW, skill="started", fixture="open"),
                 plain_cell("started", fixture="done", cls="no-benefit", runs=12)]
        self.assertEqual(plan_week.partly_decided(cells), {("skill", "started")})
        order, _work = self.near(cells)
        self.assertEqual(order, ["started", "fresh"])

    def test_a_blocked_subject_is_not_finished_first(self):
        cells = [measured_cell(STRONG, skill="fresh"),
                 measured_cell(SLOW, skill="blocked", fixture="open"),
                 plain_cell("blocked", fixture="done", cls="cannot-discriminate", runs=3,
                            with_counted=3, without_counted=3)]
        self.assertEqual(plan_week.partly_decided(cells), set())
        order, _work = self.near(cells)
        self.assertEqual(order, ["fresh", "blocked"])

    def test_use_weighs_projected_points(self):
        # Same evidence, so the same projection: the more used skill first.
        cells = [measured_cell(STRONG, skill="rare"),
                 measured_cell(STRONG, skill="used")]
        order, _work = self.near(cells, skill_weights={"rare": 0.0, "used": 9.0})
        self.assertEqual(order, ["used", "rare"])
        order, _work = self.near(cells, skill_weights={"rare": 9.0, "used": 0.0})
        self.assertEqual(order, ["rare", "used"])

    def test_high_stakes_still_go_first(self):
        order, _work = self.near([measured_cell(CLOSE, skill="normal"),
                                  measured_cell(SLOW, skill="high", stakes="high")])
        self.assertEqual(order, ["high", "normal"])


class ScopeTests(unittest.TestCase):

    def coverage(self, text):
        root = Path(tempfile.mkdtemp())
        (root / "agents-md").mkdir()
        (root / "agents-md" / "eval-coverage.yml").write_text(text, encoding="utf-8")
        return root

    def test_skipped_rows_are_read(self):
        root = self.coverage("- id: covered-one\n  status: covered\n"
                             "- id: skills-ecosystem\n  status: skipped\n  reason: no sessions\n"
                             "- id: new-one\n  status: gap\n")
        self.assertEqual(plan_week.guidance_skipped(root), frozenset({"skills-ecosystem"}))
        self.assertIsNone(plan_week.guidance_skipped(Path(tempfile.mkdtemp())))
        self.assertIsNone(plan_week.guidance_skipped(None))

    def test_a_skipped_section_gets_no_fire(self):
        cells = [gcell("skills-ecosystem", "a"), gcell("skills-ecosystem", "b")]
        # The control: in scope, its cells are fired.
        self.assertTrue(plan_week.build_plan(ctx(cells), NOW, 10)["fires"])
        plan = plan_week.build_plan(ctx(cells, guidance_skipped=frozenset(
            {"skills-ecosystem"})), NOW, 10)
        self.assertEqual(plan["fires"], [])
        self.assertEqual(plan["guidance_focus"], [])

    def test_a_skipped_section_is_never_a_probe(self):
        # Never fired, the skipped cell would be the first probe (oldest
        # last fire first) if it were in scope.
        down = NOW - timedelta(hours=1)
        cells = [gcell("skills-ecosystem", "a"),
                 plain_cell("live", last_fire=NOW - timedelta(hours=3))]
        self.assertEqual([f["fixture"] for f in plan_week.build_plan(
            ctx(cells, routine_down=down), NOW, 10)["fires"]],
            ["evals/guidance/skills-ecosystem/a"])
        plan = plan_week.build_plan(ctx(cells, routine_down=down,
                                        guidance_skipped=frozenset({"skills-ecosystem"})),
                                    NOW, 10)
        self.assertEqual([f["fixture"] for f in plan["fires"]], ["evals/live/a"])

    def test_the_batch_never_lists_a_skipped_section(self):
        cells = [gcell("skills-ecosystem"), gcell("security")]
        held = plan_week.scope_holds(ctx(cells, guidance_skipped=frozenset(
            {"skills-ecosystem"})))
        self.assertEqual(set(plan_week.batch_subjects(held)), {("guidance", "security")})


class AlonePairTests(unittest.TestCase):
    """THE ALONE PAIR: the section-alone pair is fired only for a section
    leaning toward removal; every other guidance fire is `in-situ`."""

    def arms(self, cells):
        return {f["fixture"]: f["arms"] for f in
                plan_week.build_plan(ctx(cells), NOW, 10)["fires"]}

    def test_a_section_not_leaning_toward_removal_runs_in_situ_only(self):
        cell = gcell("open", cls="insufficient",
                     objective={"no_help_confidence": 0.3 * GUIDANCE_POLICY["retire_confidence"]})
        self.assertEqual(self.arms([cell]), {"evals/guidance/open/a": "in-situ"})

    def test_a_section_halfway_to_removal_runs_the_alone_pair(self):
        level = plan_week.ALONE_PAIR_FROM_PROGRESS * GUIDANCE_POLICY["retire_confidence"]
        cell = gcell("leaning", cls="insufficient", objective={"no_help_confidence": level})
        self.assertEqual(self.arms([cell]), {"evals/guidance/leaning/a": "both"})

    def test_an_in_situ_retire_runs_the_alone_pair(self):
        cell = gcell("retiring", cls="insufficient", in_situ_verdict="retire")
        self.assertEqual(self.arms([cell]), {"evals/guidance/retiring/a": "both"})

    def test_a_skill_cell_runs_both_arms(self):
        self.assertEqual(self.arms([plain_cell("s")]), {"evals/s/a": "both"})


class BatchFitTests(unittest.TestCase):
    """The batch already caps open subjects; DEEP BEFORE WIDE only reorders
    its candidates."""

    START = datetime(2026, 11, 9, 17, 0, 0, tzinfo=timezone.utc)

    def picks(self, cells, weights):
        policy = {"start": self.START, "period": timedelta(days=14), "multiplier": 3.0,
                  "rates": {"skill": 0.75, "guidance": 0.5},
                  "rate_window": timedelta(days=28), "pairs_per_cell": 4.0,
                  "cost_window": timedelta(days=14)}
        c = ctx(cells, batch_policy=policy, previous_batch=None, batch_budget=None,
                batch_pair_costs=None, skill_weights=weights)
        fit = plan_week.fit_batch(c, plan_week.batch_subjects(c), [],
                                  {"skill": 1, "guidance": 1}, 1)
        return [m["subject"] for m in fit["picks"]]

    def test_a_subject_projected_past_its_caps_waits_behind_the_rest(self):
        cells = [measured_cell(NOISY, skill="hopeless"), measured_cell(CLOSE, skill="close")]
        # Most used first would pick `hopeless`; it cannot decide in its cap.
        self.assertEqual(self.picks(cells, {"hopeless": 9.0, "close": 1.0}), ["close"])

    def test_a_partly_decided_subject_joins_before_a_fresh_one(self):
        cells = [measured_cell(STRONG, skill="fresh"),
                 measured_cell(STRONG, skill="started", fixture="open"),
                 plain_cell("started", fixture="done", cls="no-benefit", runs=12)]
        self.assertEqual(self.picks(cells, {"fresh": 1.0, "started": 1.0}), ["started"])


if __name__ == "__main__":
    unittest.main()
