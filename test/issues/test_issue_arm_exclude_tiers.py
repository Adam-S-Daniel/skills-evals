"""`arm_exclude_tiers` keeps a family off the arm set (2026-11-23).

The owner keeps Fable off the arms on cost while roster updates go on
merging automatically. A model of an excluded family that meets a seating
rule is listed under `excluded` instead, and stays eligible as the judge.
The key is optional; without it the roster seats exactly as before.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

import test_issue_202 as base  # noqa: E402

roster = base.roster

FABLE = "claude-fable-5-1"


class ArmExcludeTiersTests(base._RosterFixture):

    def _fable_heavy(self):
        """A census where Fable carries far more than the entry bar."""
        return self._census(extra={FABLE: {w: 600 for w in self.ENTER}})

    def _without_key(self, **overrides):
        policy = self._policy()
        policy.pop("arm_exclude_tiers", None)
        policy.update(overrides)
        return policy

    def test_without_the_key_a_qualifying_fable_model_is_seated(self):
        result, _ = self._compute(census=self._fable_heavy(), policy=self._without_key())
        self.assertIn(FABLE, self._arms(result))

    def test_an_excluded_tier_takes_no_arm_seat(self):
        policy = self._without_key(arm_exclude_tiers=["fable", "mythos"])
        roster.validate_policy(policy)
        result, _ = self._compute(census=self._fable_heavy(), policy=policy)
        self.assertNotIn(FABLE, self._arms(result))
        reason = self._reason(result, FABLE, section="excluded")
        self.assertIn("arm_exclude_tiers", reason)
        self.assertIn("would otherwise be seated", reason)
        self.assertTrue(self._arms(result), "the other arms remain")

    def test_an_excluded_tier_can_still_judge(self):
        policy = self._without_key(arm_exclude_tiers=["fable", "mythos"])
        result, _ = self._compute(census=self._fable_heavy(), policy=policy)
        self.assertEqual(result["judge"]["id"], FABLE)
        self.assertFalse(result["judge"]["is_arm"])

    def test_other_tiers_are_unchanged(self):
        plain, _ = self._compute(policy=self._without_key())
        excluded, _ = self._compute(
            policy=self._without_key(arm_exclude_tiers=["fable", "mythos"]))
        self.assertEqual(self._arms(plain), self._arms(excluded))

    def test_a_bad_value_is_refused_by_name(self):
        for bad in ("fable", ["gpt"], [1], None):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    ValueError, "arm_exclude_tiers"):
                roster.validate_policy(self._without_key(arm_exclude_tiers=bad))

    def test_the_shipped_policy_keeps_fable_off_the_arms(self):
        policy = roster.load_policy(base.POLICY)
        roster.validate_policy(policy)
        self.assertEqual(sorted(policy["arm_exclude_tiers"]), ["fable", "mythos"])


if __name__ == "__main__":
    unittest.main()
