"""skills-evals#921: an optional stop on the CLI's 5-hour window.

`stop_when_session_above` in evals/budget.yml stops a run from starting more
work, and the pre-fire guard from firing, once the 5-hour window reads at or
above it. Absent (the committed budget), nothing changes.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

import test_issue_68_allowance_guard as base  # noqa: E402

budget, guard, run_eval, ingest = base.budget, base.guard, base.run_eval, base.ingest
LIMITS, NOW = base.LIMITS, base.NOW
SESSION = {**LIMITS, "stop_when_session_above": 0.90}


class SessionBudgetFileTests(unittest.TestCase):

    def test_the_key_is_optional_and_checked(self):
        parsed = budget.parse_budget(base.VALID_BUDGET + "stop_when_session_above: 0.9\n")
        self.assertEqual(parsed["stop_when_session_above"], 0.9)
        self.assertNotIn("stop_when_session_above", budget.parse_budget(base.VALID_BUDGET))
        with self.assertRaisesRegex(budget.BudgetError, "stop_when_session_above"):
            budget.parse_budget(base.VALID_BUDGET + "stop_when_session_above: 1.5\n")

    def test_the_committed_budget_does_not_set_it(self):
        self.assertNotIn("stop_when_session_above", budget.load_budget())


class SessionStopReadingTests(unittest.TestCase):

    def test_the_session_limit_stops_the_run(self):
        self.assertEqual(
            run_eval.budget_stop_reading([(0.40, 1)], SESSION, session=0.92),
            {"reason": "session_above", "utilization": 0.92, "moved": 0,
             "limit": 0.90})

    def test_below_the_session_limit_nothing_stops(self):
        self.assertIsNone(run_eval.budget_stop_reading([(0.40, 1)], SESSION, session=0.89))

    def test_without_the_key_the_session_reading_is_ignored(self):
        self.assertIsNone(run_eval.budget_stop_reading([(0.40, 1)], LIMITS, session=1.0))

    def test_the_account_limit_still_wins(self):
        self.assertEqual(
            run_eval.budget_stop_reading([(0.80, 1)], SESSION, session=0.95)["reason"],
            "account_above")

    def test_the_five_hour_reading_comes_from_the_cli_meter(self):
        self.assertEqual(run_eval._five_hour(base.meter(0.4)), 0.01)
        self.assertIsNone(run_eval._five_hour({"unifiedWindows": {"five_hour": {}}}))
        self.assertIsNone(run_eval._five_hour(None))


class SessionStopIngestTests(unittest.TestCase):

    def test_ingest_accepts_a_session_stop(self):
        self.assertIn("session_above", ingest.BUDGET_STOP_REASONS)


class SessionHoldGuardTests(unittest.TestCase):

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, ignore_errors=True)

    def metered(self, session, resets_in=timedelta(hours=2)):
        snap = base.snapshot(0.30)
        snap["info"]["unifiedWindows"]["five_hour"] = {
            "utilization": session, "resetsAt": int((NOW + resets_in).timestamp())}
        stamp = "20261020T100000Z"
        path = (self.tree / "routine-results" / f"{stamp}-a1b2c3" / "k" / stamp
                / "with_skill" / "summary.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        block = base.usage_block(0.02)
        block["measured"]["meter"] = {"snapshots": [snap], "omitted": 0}
        path.write_text(json.dumps({"arm": "x", "usage": block}), encoding="utf-8")

    def state(self, limits):
        return guard.account(self.tree, limits, NOW, (0, 0))

    def test_a_full_window_refuses_every_mode(self):
        self.metered(0.95)
        state = self.state(SESSION)
        self.assertTrue(state["session_hold"])
        self.assertEqual(guard.fits(state), 0)
        for mode in ("eval", *guard.IMPROVE_MODES):
            with self.subTest(mode=mode):
                self.assertEqual(guard.check(state, mode), guard.SESSION_REFUSAL)

    def test_a_window_that_has_reset_does_not_hold(self):
        self.metered(0.95, resets_in=-timedelta(minutes=5))
        self.assertFalse(self.state(SESSION)["session_hold"])

    def test_below_the_limit_or_without_the_key_nothing_holds(self):
        self.metered(0.50)
        self.assertFalse(self.state(SESSION)["session_hold"])
        self.metered(0.99)
        self.assertFalse(self.state(LIMITS)["session_hold"])
        self.assertGreater(guard.fits(self.state(LIMITS)), 0)


if __name__ == "__main__":
    unittest.main()
