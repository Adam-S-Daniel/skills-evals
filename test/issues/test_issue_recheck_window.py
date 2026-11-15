#!/usr/bin/env python3
"""THE RE-CHECK WINDOW (harness/gates.py; Adam, 2026-11-15).

Before it, a keep was final once its keep test crossed, so a re-check's
pairs could never change a skill's keep. Now a kept cell's re-check is
tested on the pairs made since it fell due: a removal over them overrides
the keep; a gain over them clearing the margin ends it early; otherwise it
ends at `max_runs_per_cell` pairs.

Hermetic and deterministic: canned runs, no network, no clock.
"""

from __future__ import annotations

import math
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402
import test_issue_70_retirement  # noqa: E402
from test_issue_70_retirement import FLAT, GAIN, LOSS, TEST_POLICY, series  # noqa: E402

#: One-week re-checks, so a canned month of hourly runs holds a keep and
#: its re-check; without THE RE-CHECK CARRY (RecheckCarryTests has it).
ON = {**TEST_POLICY, "recheck_window": True, "recheck_window_fire": True, "recheck_weeks": 1,
      "recheck_carry": False}
WEEK = 7 * 24


def cell(with_patterns, without_patterns, policy=ON):
    """A skill cell: GAIN/LOSS pairs from hour 0, then the given pairs a
    week and a day later."""
    late = WEEK + 24
    runs_with = series("with", GAIN, None) + series("with", with_patterns, None, start=late)
    runs_without = series("without", LOSS, None) + series("without", without_patterns,
                                                          None, start=late)
    return gates.classify_cell(runs_with, runs_without, policy)


class RecheckWindowTests(unittest.TestCase):

    def test_off_a_recheck_cannot_change_a_keep(self):
        off = {**ON, "recheck_window": False}
        got = cell(FLAT * 2, FLAT * 2, off)
        self.assertEqual(got["class"], "benefit", got["reason"])
        self.assertNotIn("recheck", got)

    def test_a_recheck_that_shows_no_gain_removes(self):
        got = cell(FLAT * 2, FLAT * 2)
        self.assertEqual(got["class"], "no-benefit", got["reason"])
        self.assertIsNotNone(got["recheck"]["removed_at"])
        self.assertIn("re-check", got["reason"])
        self.assertLessEqual(got["recheck"]["pairs"], ON["max_runs_per_cell"])

    def test_a_recheck_that_still_helps_stops_early(self):
        got = cell(GAIN * 2, LOSS * 2)
        self.assertEqual(got["class"], "benefit", got["reason"])
        recheck = got["recheck"]
        self.assertEqual(len(recheck["passed"]), 1)
        self.assertIsNone(recheck["removed_at"])
        # The next re-check falls due a week after the pass, with no pairs.
        passed = gates._stamp(recheck["passed"][0])
        self.assertEqual(gates._stamp(recheck["due"]), passed + timedelta(weeks=1))
        self.assertEqual(recheck["pairs"], 0)
        # It passed well before the cap.
        late = gates._stamp(series("with", FLAT[:1], None, start=WEEK + 24)[0]["timestamp"])
        self.assertLess((passed - late) / timedelta(hours=1) + 1, ON["max_runs_per_cell"])

    def test_an_open_recheck_reports_when_it_fell_due(self):
        got = cell(GAIN[:2], LOSS[:2])
        recheck = got["recheck"]
        self.assertEqual((recheck["passed"], recheck["pairs"]), ([], 2))
        self.assertIsNotNone(recheck["due"])
        # Pairs before it fell due are not the re-check's.
        none_yet = gates.classify_cell(series("with", GAIN, None),
                                       series("without", LOSS, None), ON)
        self.assertEqual(none_yet["recheck"]["pairs"], 0)
        self.assertEqual(none_yet["recheck"]["due"], recheck["due"])

    def test_a_flat_recheck_runs_to_the_cap(self):
        # A gain exactly at the margin neither removes nor clears it.
        at_margin = [(p[0] + 15, p[1] + 15, p[2] + 15) for p in FLAT]
        got = cell(at_margin * 2, FLAT * 2)
        recheck = got["recheck"]
        self.assertEqual(got["class"], "benefit", got["reason"])
        self.assertEqual(len(recheck["passed"]), 1)
        first = series("with", FLAT[:1], None, start=WEEK + 24)[0]["timestamp"]
        hours = (gates._stamp(recheck["passed"][0]) - gates._stamp(first)) / timedelta(hours=1)
        self.assertEqual(hours + 1, ON["max_runs_per_cell"])

    def test_the_early_stop_rarely_cuts_a_removal_short(self):
        # Seeded: a gain of about 0.09, under the 0.15 margin, passes early
        # at most about 1 - retire_confidence of the time.
        policy = {**gates.load_gate_policy()["skills"], "recheck_carry": False}
        rng = random.Random(7)
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        early, sims = 0, 300
        for _ in range(sims):
            pairs = []
            for h in range(policy["max_runs_per_cell"]):
                d = rng.choice([1.0, 0.0, 0.0, -0.4, 0.0, 0.0, 0.0])
                ts = (t0 + timedelta(weeks=9, hours=h)).strftime("%Y%m%dT%H%M%SZ")
                w = {"timestamp": ts, "numbers": {"run_mean": max(d, 0.0)},
                     "cli_versions": ["1"]}
                o = {"timestamp": ts, "numbers": {"run_mean": max(-d, 0.0)},
                     "cli_versions": ["1"]}
                pairs.append((w, o))
            got = gates._recheck(pairs, [t0.strftime("%Y%m%dT%H%M%SZ")], policy, None)
            first_pass = gates._stamp(got["passed"][0]) if got["passed"] else None
            early += first_pass is not None and first_pass < t0 + timedelta(
                weeks=9, hours=policy["max_runs_per_cell"] - 1)
        self.assertLessEqual(early / sims, 1 - policy["retire_confidence"])

    def test_a_confirmation_inside_a_recheck_does_not_move_it(self):
        # The review's 2: a keep test crossing on a re-check's own pairs
        # would push the due time on and drop its evidence.
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        fmt = "%Y%m%dT%H%M%SZ"
        before, inside = t0 + timedelta(days=3), t0 + timedelta(days=12)
        got = gates._recheck([], [t.strftime(fmt) for t in (t0, before, inside)], ON, None)
        self.assertEqual(gates._stamp(got["due"]), before + timedelta(weeks=1))

    def test_an_errored_trial_blocks_a_recheck_removal_and_ends_it(self):
        # The review's 4: the keep stands rather than turning insufficient.
        late = WEEK + 24
        runs_with = series("with", GAIN, None) + series("with", FLAT * 2, None, start=late)
        runs_without = series("without", LOSS, None) + series("without", FLAT * 2, None,
                                                              start=late)
        runs_with[0]["trials"].append(gates.trial_record(
            test_issue_70_retirement.trial(error="agent_failed")))
        got = gates.classify_cell(runs_with, runs_without, ON)
        self.assertEqual(got["class"], "benefit", got["reason"])
        self.assertIsNone(got["recheck"]["removed_at"])
        self.assertIsNone(got["recheck"]["due"])
        self.assertIn("blocked", got["recheck"])

    def test_a_recheck_removal_has_a_decision_point(self):
        got = cell(FLAT * 2, FLAT * 2)
        self.assertEqual(got["class"], "no-benefit")
        self.assertIsInstance(got["decided_at"], int)

    def test_a_projection_prices_a_recheck(self):
        policy = gates.load_gate_policy()["skills"]
        cap = policy["max_runs_per_cell"]
        self.assertLess(gates._recheck_projection([0.7] * 10, policy, None), cap)
        self.assertEqual(gates._recheck_projection([0.0] * 10, policy, None), cap)
        self.assertEqual(gates._recheck_projection([], policy, None), cap)


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stream(draw, weeks, every_hours=4, key=None, start=T0):
    """Pairs every `every_hours` from `start` for `weeks` weeks, each with
    difference `draw(i)` (the with run's mean minus the without run's)."""
    out = []
    for i in range(weeks * 7 * 24 // every_hours):
        d = draw(i)
        ts = (start + timedelta(hours=every_hours * i)).strftime("%Y%m%dT%H%M%SZ")
        w = {"timestamp": ts, "numbers": {"run_mean": max(d, 0.0)},
             "cli_versions": [str(i % 2)], "pair_key": key}
        o = {"timestamp": ts, "numbers": {"run_mean": max(-d, 0.0)},
             "cli_versions": [str(i % 2)], "pair_key": key}
        out.append((w, o))
    return out


def weekly(policy, carry):
    return {**policy, "recheck_window": True, "recheck_weeks": 1, "recheck_carry": carry}


KEEP = [T0.strftime("%Y%m%dT%H%M%SZ")]


class RecheckCarryTests(unittest.TestCase):
    """THE RE-CHECK CARRY (harness/gates.py; Adam, 2026-11-15)."""

    def setUp(self):
        self.policy = gates.load_gate_policy()["skills"]

    def test_a_slipped_gain_is_removed_sooner_with_the_carry(self):
        # Seeded: a gain of 0.06, under the 0.15 margin. Fresh re-checks
        # each start from scratch; the carried test keeps the evidence.
        rng = random.Random(11)
        sooner = later = 0
        for _ in range(20):
            pairs = stream(lambda i: rng.choice([0.3, 0.0, -0.1, 0.1, 0.0]), 30)
            fresh = gates._recheck(pairs, KEEP, weekly(self.policy, False), None)
            carried = gates._recheck(pairs, KEEP, weekly(self.policy, True), None)
            when = [gates._stamp(g["removed_at"]) if g["removed_at"] else None
                    for g in (carried, fresh)]
            if when[0] is None:
                later += when[1] is not None
            elif when[1] is None or when[0] < when[1]:
                sooner += 1
            elif when[0] > when[1]:
                later += 1
        self.assertGreater(sooner, 3 * later)

    def test_a_strong_cell_passes_its_later_rechecks_in_a_few_pairs(self):
        pairs = stream(lambda i: [0.8, 0.4, 0.6][i % 3], 6)
        carried = gates._recheck(pairs, KEEP, weekly(self.policy, True), None)
        fresh = gates._recheck(pairs, KEEP, weekly(self.policy, False), None)
        self.assertGreater(carried["carry"]["keep"], 0)
        self.assertNotIn("carry", fresh)

        def lengths(got):
            # Pairs each passed re-check took: from its due time to its pass.
            out, since = [], T0
            for passed in got["passed"]:
                due = since + timedelta(weeks=1)
                out.append(sum(1 for w, _ in pairs if due <= gates._stamp(w["timestamp"])
                               <= gates._stamp(passed)))
                since = gates._stamp(passed)
            return out
        self.assertEqual(lengths(carried)[0], lengths(fresh)[0])
        self.assertLess(lengths(carried)[-1], lengths(fresh)[-1])
        self.assertGreaterEqual(min(lengths(carried)), gates.CARRY_MIN_OWN_PAIRS)

    def test_a_carried_early_stop_needs_its_own_pairs_at_the_margin(self):
        # Strong for two weeks, then a gain of 0.10: the carried keep
        # evidence alone cannot pass a re-check whose own pairs average
        # under the margin.
        draw = lambda i: [0.8, 0.4, 0.6][i % 3] if i < 84 else [0.4, -0.2, 0.1][i % 3]
        pairs = stream(draw, 5)
        got = gates._recheck(pairs, KEEP, weekly(self.policy, True), None)
        late = [p for p in got["passed"] if gates._stamp(p) >= T0 + timedelta(weeks=2)]
        for passed in late:
            due = max(gates._stamp(q) for q in got["passed"]
                      if gates._stamp(q) < gates._stamp(passed)) + timedelta(weeks=1)
            own = [w for w, _ in pairs
                   if due <= gates._stamp(w["timestamp"]) <= gates._stamp(passed)]
            self.assertGreater(len(own), gates.CARRY_MIN_OWN_PAIRS)

    def test_a_recheck_that_cannot_remove_ends_before_the_cap(self):
        # THE FUTILE STOP: a gain at the margin neither removes nor clears
        # it; once the pairs left could not carry the remove test across,
        # the re-check passes without them.
        pairs = stream(lambda i: [0.45, -0.15, 0.15][i % 3], 2)
        carried = gates._recheck(pairs, KEEP, weekly(self.policy, True), None)
        fresh = gates._recheck(pairs, KEEP, weekly(self.policy, False), None)
        due = T0 + timedelta(weeks=1)
        took = [sum(1 for w, _ in pairs if due <= gates._stamp(w["timestamp"])
                    <= gates._stamp(g["passed"][0])) for g in (carried, fresh)]
        self.assertEqual(took[1], self.policy["max_runs_per_cell"])
        self.assertLess(took[0], took[1])

    def test_a_long_healthy_history_does_not_block_a_later_removal(self):
        # THE FLOOR: a bet prior near the margin bets on removal in each
        # strong re-check and loses a little; a year of that must not leave
        # a gain that falls to 0 unremovable.
        prior = {"mean": 0.136, "variance": 0.0118, "n": 3.0}
        rng = random.Random(5)
        healthy = 52 * 42
        pairs = stream(lambda i: rng.choice([0.6, 0.3, 0.0, 0.4]) if i < healthy
                       else rng.choice([0.3, -0.3, 0.0, 0.0]), 60)
        got = gates._recheck(pairs, KEEP, weekly(self.policy, True), prior)
        self.assertIsNotNone(got["removed_at"])
        self.assertGreaterEqual(got["carry"]["remove"],
                                -gates.CARRY_REMOVE_FLOOR * -math.log(
                                    1 - self.policy["retire_confidence"]))

    def test_pairs_beside_an_older_rest_carry_nothing(self):
        old = stream(lambda i: 0.8, 2, key="old")
        new = stream(lambda i: 0.8, 2, key="new", start=T0 + timedelta(weeks=2))
        got = gates._recheck(old + new, KEEP, weekly(self.policy, True), None,
                             current="new", min_pairs=1)
        only_new = gates._recheck(new, KEEP, weekly(self.policy, True), None,
                                  current="new", min_pairs=1)
        self.assertEqual(got["carry"], only_new["carry"])

    def test_the_lifetime_false_removal_rate_stays_under_the_level(self):
        # Seeded: a gain exactly at the margin (0.15) re-checked 26 times.
        # Fresh re-checks spend alpha at each; the carry bounds the chance of
        # ever removing it at 1 - retire_confidence.
        policy = weekly(self.policy, True)
        rng = random.Random(99)
        removed, sims = 0, 200
        for _ in range(sims):
            pairs = stream(lambda i: rng.choice([1.0, 0.0, 0.0, 0.0, -0.4, 0.0, 0.45]), 26)
            removed += gates._recheck(pairs, KEEP, policy, None)["removed_at"] is not None
        self.assertLessEqual(removed / sims, 1 - policy["retire_confidence"])

    def test_the_projection_reads_the_keep_carry(self):
        policy = {**self.policy, "recheck_carry": True}
        ds = [0.6, 0.4, 0.5] * 4
        cold = gates._recheck_projection(ds, policy, None, 0.0)
        warm = gates._recheck_projection(ds, policy, None, 10.0)
        self.assertLess(warm, cold)
        self.assertGreaterEqual(warm, gates.CARRY_MIN_OWN_PAIRS)
        self.assertEqual(gates._recheck_projection(ds, {**policy, "recheck_carry": False},
                                                   None, 10.0), cold)


class PolicyAndPlumbingTests(unittest.TestCase):

    def test_the_setting_is_checked_and_on_in_both_blocks(self):
        committed = gates.load_gate_policy()
        self.assertIs(committed["skills"]["recheck_window"], True)
        self.assertIs(committed["guidance"]["recheck_window"], True)
        base = "".join(f"  {k}: {v}\n" for k, v in TEST_POLICY.items()
                       if k != "recheck_window")
        self.assertIs(gates.parse_gate_policy(f"skills:\n{base}")["skills"]["recheck_window"],
                      False)
        for bad in ("1", "'true'", "null"):
            with self.subTest(bad=bad), self.assertRaises(gates.GatePolicyError):
                gates.parse_gate_policy(f"skills:\n{base}  recheck_window: {bad}\n")

    def test_the_carry_is_checked_and_on_in_both_blocks(self):
        committed = gates.load_gate_policy()
        self.assertIs(committed["skills"]["recheck_carry"], True)
        self.assertIs(committed["guidance"]["recheck_carry"], True)
        base = "".join(f"  {k}: {v}\n" for k, v in TEST_POLICY.items()
                       if k not in ("recheck_window", "recheck_carry"))
        self.assertIs(gates.parse_gate_policy(f"skills:\n{base}")["skills"]["recheck_carry"],
                      False)
        for bad in ("1", "'true'", "null"):
            with self.subTest(bad=bad), self.assertRaises(gates.GatePolicyError):
                gates.parse_gate_policy(f"skills:\n{base}  recheck_carry: {bad}\n")

    def test_high_stakes_subjects_recheck_sooner(self):
        policy = gates.load_gate_policy()["skills"]
        table = {("skill", "hot"): {"stakes": "high"}}
        self.assertEqual(compute_gates.recheck_policy(policy, table, "skill", "hot")
                         ["recheck_after_weeks"], policy["recheck_weeks_high"])
        self.assertEqual(compute_gates.recheck_policy(policy, table, "skill", "cold")
                         ["recheck_after_weeks"], policy["recheck_weeks"])

    def test_a_kept_skill_is_fired_from_its_recheck_due_time(self):
        got = cell(GAIN[:2], LOSS[:2])
        due = gates._stamp(got["recheck"]["due"])
        planner = {"skill": "demo", "fixture": "evals/demo/fx", "model": "model-a",
                   "class": "benefit", "verdict": "keep", "in_situ_verdict": None,
                   "with_runs": 12, "without_runs": 12, "newest": None,
                   "usd_per_fire": None, "empty_fires": 0, "objective": got["objective"],
                   "judge": None, "judge_carried": False, "reason": got["reason"],
                   "with_counted": 12, "without_counted": 12, "pairs": got["pairs"],
                   "at_cap": True, "recheck": got["recheck"]}
        ctx = {"cells": [planner], "model_weights": {"model-a": 1.0}, "removal_prs": [],
               "guidance_policy": None, "policy": ON, "reservation": 1.0, "overrun": 1.0,
               "points_per_usd": None, "lessons": [], "skills": {}, "batch": None}
        before, _ = plan_week.eval_items(ctx, due - timedelta(hours=1))
        self.assertFalse(any(before.values()))
        after, _ = plan_week.eval_items(ctx, due)
        self.assertEqual([i["fixture"] for i in after["recheck"]], ["evals/demo/fx"])
        # Held while the stopping rules are redesigned (Adam, 2026-11-15).
        held, _ = plan_week.eval_items({**ctx, "policy": {**ON, "recheck_window_fire": False}},
                                       due)
        self.assertFalse(any(held.values()))
        # An age-based re-check of a kept subject's unsettled cell is held too.
        aged = {**planner, "class": "insufficient", "at_cap": False, "recheck": None,
                "newest": "20200101T000000Z"}
        fired, _ = plan_week.eval_items({**ctx, "cells": [aged]}, due)
        self.assertTrue(fired["recheck"], fired)
        held, _ = plan_week.eval_items({**ctx, "cells": [aged],
                                        "policy": {**ON, "recheck_window_fire": False}}, due)
        self.assertFalse(any(held.values()))

    def test_the_fire_switch_is_checked_and_on_in_both_blocks(self):
        committed = gates.load_gate_policy()
        self.assertIs(committed["skills"]["recheck_window_fire"], True)
        self.assertIs(committed["guidance"]["recheck_window_fire"], True)
        base = "".join(f"  {k}: {v}\n" for k, v in TEST_POLICY.items()
                       if k != "recheck_window_fire")
        self.assertIs(gates.parse_gate_policy(f"skills:\n{base}")["skills"]
                      ["recheck_window_fire"], True)
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(f"skills:\n{base}  recheck_window_fire: 'no'\n")


if __name__ == "__main__":
    unittest.main()
