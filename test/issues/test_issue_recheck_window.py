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
#: its re-check.
ON = {**TEST_POLICY, "recheck_window": True, "recheck_weeks": 1}
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
        policy = gates.load_gate_policy()["skills"]
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


if __name__ == "__main__":
    unittest.main()
