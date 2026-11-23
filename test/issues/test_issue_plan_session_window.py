"""The 5-hour stop follows the plan, and working hours lower it.

`claude_plan` in evals/budget.yml is required. A plan Anthropic documents a
5-hour window for must set `stop_when_session_above`; one it documents none
for must not. `working_hours` lowers that stop from 5 hours before the owner's
day starts until it ends, in both the in-run stop and the pre-fire guard.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

import test_issue_68_allowance_guard as base  # noqa: E402

budget, guard, run_eval = base.budget, base.guard, base.run_eval
BASE = base.VALID_BUDGET.replace("claude_plan: ultra\n", "")
HOURS = ('working_hours:\n  timezone: America/New_York\n  days: [mon, tue, wed, thu, fri]\n'
         '  start: "09:00"\n  end: "18:00"\n  session_stop: 0.50\n')
PRO = BASE + "claude_plan: pro\nstop_when_session_above: 0.90\n"


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# 2026-11-20 is a Friday; New York is UTC-5 then.
FRI_10AM_NY = utc(2026, 11, 20, 15, 0)
FRI_5AM_NY = utc(2026, 11, 20, 10, 0)      # inside the 5-hour lead-in
FRI_3AM_NY = utc(2026, 11, 20, 8, 0)       # before it
FRI_7PM_NY = utc(2026, 11, 21, 0, 0)       # after end
SUN_10PM_NY = utc(2026, 11, 23, 3, 0)      # before Monday's 4 AM lead-in


class PlanTests(unittest.TestCase):

    def test_the_plan_is_required(self):
        with self.assertRaisesRegex(budget.BudgetError, "missing claude_plan"):
            budget.parse_budget(BASE)

    def test_an_unknown_plan_is_refused(self):
        with self.assertRaisesRegex(budget.BudgetError, "claude_plan must be one of"):
            budget.parse_budget(BASE + "claude_plan: max20x\n")

    def test_a_plan_with_a_window_needs_the_stop(self):
        for plan in ("pro", "max5x"):
            with self.subTest(plan=plan), self.assertRaisesRegex(
                    budget.BudgetError, "has a 5-hour window: set stop_when_session_above"):
                budget.parse_budget(BASE + f"claude_plan: {plan}\n")
        self.assertEqual(budget.parse_budget(PRO)["stop_when_session_above"], 0.90)

    def test_each_supported_plan_maps_to_its_allowance_scale(self):
        self.assertEqual(budget.ALLOWANCE_SCALE, {"pro": 10, "max5x": 2, "ultra": 1})
        for plan, scale in budget.ALLOWANCE_SCALE.items():
            with self.subTest(plan=plan):
                text = BASE + f"claude_plan: {plan}\n" \
                    + ("stop_when_session_above: 0.9\n" if plan != "ultra" else "")
                parsed = budget.parse_budget(text)
                self.assertEqual(parsed["allowance_scale"], scale)
                self.assertEqual(budget.allowance_scale(parsed), scale)
        self.assertEqual(budget.allowance_scale(None), 1)

    def test_a_plan_with_no_scale_is_refused_naming_the_supported_ones(self):
        for plan in ("team_standard", "team_premium", "enterprise_seat", "enterprise_usage"):
            with self.subTest(plan=plan), self.assertRaisesRegex(
                    budget.BudgetError, "not supported.*pro, max5x, ultra"):
                budget.parse_budget(BASE + f"claude_plan: {plan}\n")

    def test_ultra_may_set_the_stop_or_not(self):
        self.assertNotIn("stop_when_session_above", budget.parse_budget(BASE + "claude_plan: ultra\n"))
        self.assertEqual(budget.parse_budget(
            BASE + "claude_plan: ultra\nstop_when_session_above: 0.9\n")["stop_when_session_above"], 0.9)

    def test_the_committed_budget_is_ultra_without_a_session_stop(self):
        committed = budget.load_budget()
        self.assertEqual(committed["claude_plan"], "ultra")
        self.assertNotIn("stop_when_session_above", committed)
        self.assertNotIn("working_hours", committed)


class WorkingHoursFileTests(unittest.TestCase):

    def test_valid_hours_parse(self):
        hours = budget.parse_budget(PRO + HOURS)["working_hours"]
        self.assertEqual(hours["session_stop"], 0.50)
        self.assertEqual(hours["days"], frozenset(range(5)))

    def test_hours_need_a_session_stop(self):
        with self.assertRaisesRegex(budget.BudgetError, "working_hours needs stop_when_session_above"):
            budget.parse_budget(BASE + "claude_plan: ultra\n" + HOURS)

    def test_each_rule_is_checked(self):
        cases = {
            "timezone": HOURS.replace("America/New_York", "Mars/Olympus"),
            "days must": HOURS.replace("[mon, tue, wed, thu, fri]", "[mon, mon]"),
            "start must be HH:MM": HOURS.replace('"09:00"', '"9am"'),
            "start must be before end": HOURS.replace('"18:00"', '"08:00"'),
            "session_stop must": HOURS.replace("0.50", "0.95"),
            "takes exactly the keys": HOURS + "  lunch: 1\n",
        }
        for message, hours in cases.items():
            with self.subTest(message=message), self.assertRaisesRegex(budget.BudgetError, message):
                budget.parse_budget(PRO + hours)


class SessionLimitTests(unittest.TestCase):

    def setUp(self):
        self.limits = budget.parse_budget(PRO + HOURS)

    def test_inside_working_hours_and_the_lead_in_the_lower_stop_applies(self):
        for at in (FRI_10AM_NY, FRI_5AM_NY):
            with self.subTest(at=at):
                self.assertEqual(budget.session_limit(self.limits, at), 0.50)

    def test_outside_them_the_plain_stop_applies(self):
        for at in (FRI_3AM_NY, FRI_7PM_NY, SUN_10PM_NY):
            with self.subTest(at=at):
                self.assertEqual(budget.session_limit(self.limits, at), 0.90)

    def test_the_lead_in_can_start_the_evening_before(self):
        limits = budget.parse_budget(PRO + HOURS.replace('"09:00"', '"03:00"'))
        # Monday 3 AM New York less 5 hours is Sunday 10 PM.
        self.assertEqual(budget.session_limit(limits, SUN_10PM_NY), 0.50)
        self.assertEqual(budget.session_limit(limits, utc(2026, 11, 23, 2, 59)), 0.90)

    def test_the_lead_in_is_five_real_hours_across_a_clock_change(self):
        # Sunday 6 AM New York on the spring-forward day is 10:00 UTC; five
        # real hours before is 05:00 UTC (midnight EST), not 06:00 UTC
        # (1 AM EST, five hours of wall clock). On the fall-back day 6 AM is
        # 11:00 UTC, so the lead-in starts at 06:00 UTC, not 05:00 UTC.
        limits = budget.parse_budget(PRO + HOURS.replace(
            "[mon, tue, wed, thu, fri]", "[sun]").replace('"09:00"', '"06:00"'))
        self.assertEqual(budget.session_limit(limits, utc(2026, 3, 8, 5, 30)), 0.50)
        self.assertEqual(budget.session_limit(limits, utc(2026, 3, 8, 4, 59)), 0.90)
        self.assertEqual(budget.session_limit(limits, utc(2026, 11, 1, 6, 0)), 0.50)
        self.assertEqual(budget.session_limit(limits, utc(2026, 11, 1, 5, 30)), 0.90)

    def test_without_hours_or_now_the_plain_stop_applies(self):
        self.assertEqual(budget.session_limit(budget.parse_budget(PRO), FRI_10AM_NY), 0.90)
        self.assertEqual(budget.session_limit(self.limits, None), 0.90)
        self.assertIsNone(budget.session_limit(base.LIMITS, FRI_10AM_NY))

    def test_the_in_run_stop_uses_the_stop_in_force(self):
        stop = run_eval.budget_stop_reading([(0.40, 1)], self.limits, session=0.60,
                                            now=FRI_10AM_NY)
        self.assertEqual(stop, {"reason": "session_above", "utilization": 0.60,
                                "moved": 0, "limit": 0.50})
        self.assertIsNone(run_eval.budget_stop_reading([(0.40, 1)], self.limits,
                                                       session=0.60, now=FRI_3AM_NY))

    def test_the_guard_holds_in_working_hours_only(self):
        reading = {"at": "2026-11-20T07:59:00Z", "info": {"unifiedWindows": {
            "five_hour": {"utilization": 0.60, "resetsAt": utc(2026, 11, 21).timestamp()}}}}
        original = guard.newest_snapshot
        guard.newest_snapshot = lambda runs: (utc(2026, 11, 20, 7, 59), reading)
        try:
            self.assertTrue(guard.session_hold([], self.limits, FRI_10AM_NY))
            self.assertFalse(guard.session_hold([], self.limits, FRI_3AM_NY))
        finally:
            guard.newest_snapshot = original


if __name__ == "__main__":
    unittest.main()
