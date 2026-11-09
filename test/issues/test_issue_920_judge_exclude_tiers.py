"""skills-evals#920: `judge_exclude_tiers` keeps a family off the judge seat.

On Pro, Fable is billed as usage credits from the first call, so an adopter
on that plan needs a judge outside the fable/mythos rung. The key is
optional; without it the roster picks exactly as before.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

import test_issue_202 as base  # noqa: E402

roster = base.roster


class JudgeExcludeTiersTests(base._RosterFixture):

    def test_without_the_key_the_judge_is_unchanged(self):
        result, _ = self._compute()
        self.assertTrue(result["judge"]["id"].startswith("claude-fable-"))
        self.assertNotIn("judge_exclude_tiers", result["judge"]["reason"])

    def test_an_excluded_tier_never_takes_the_judge_seat(self):
        policy = self._policy(judge_exclude_tiers=["fable", "mythos"])
        roster.validate_policy(policy)
        result, _ = self._compute(policy=policy)
        judge = result["judge"]
        self.assertIsNotNone(judge["id"])
        self.assertNotIn("fable", judge["id"])
        self.assertFalse(judge["is_arm"])
        self.assertIn("judge_exclude_tiers", judge["reason"])

    def test_the_arms_do_not_change(self):
        plain, _ = self._compute()
        excluded, _ = self._compute(policy=self._policy(judge_exclude_tiers=["fable"]))
        self.assertEqual(self._arms(plain), self._arms(excluded))

    def test_a_bad_value_is_refused_by_name(self):
        for bad in ("fable", ["gpt"], [1], None):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    ValueError, "judge_exclude_tiers"):
                roster.validate_policy(self._policy(judge_exclude_tiers=bad))


if __name__ == "__main__":
    unittest.main()
