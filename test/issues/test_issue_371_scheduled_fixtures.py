"""#371 item 5 and ADR 0012: the scheduled fixtures follow the roster and
declare the context an in-place pair runs in.

Everything here reads committed files only: the schedule and each fixture are
parsed as YAML, and a `context:` block goes through the resolver's own schema
check. No repository is resolved, no network is used and no model is called.
Run with: python3 -m pytest test/issues/test_issue_371_scheduled_fixtures.py -q
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import context  # noqa: E402
import run_eval  # noqa: E402

SCHEDULE = ROOT / "evals/scheduled.yml"
ROSTER = ROOT / "evals/roster.yml"
SHA = re.compile(r"[0-9a-f]{40}\Z")

# A scheduled fixture that keeps a `model:` or `judge.model:` pin is named
# here with the reason the pin still holds. Empty: the roster picks both.
PINNED_WITH_REASON: dict[str, str] = {}

# A scheduled fixture with no provable `guidance_revision` stays an isolation
# pair and is named here with the reason. Empty: all eight resolve.
ISOLATION_ONLY: dict[str, str] = {}


def scheduled() -> list[dict]:
    return yaml.safe_load(SCHEDULE.read_text(encoding="utf-8"))["fixtures"]


def fixtures() -> dict[str, dict]:
    return {row["path"]: run_eval.load_fixture(ROOT / row["path"]) for row in scheduled()}


class ScheduledFixturesFollowTheRoster(unittest.TestCase):
    def test_the_schedule_names_eight_fixtures(self):
        paths = [row["path"] for row in scheduled()]
        self.assertEqual(len(paths), 8)
        self.assertEqual(len(set(paths)), 8)

    def test_no_fixture_pins_a_model_without_a_stated_reason(self):
        for path, fixture in fixtures().items():
            pins = [key for key, pinned in (("model", "model" in fixture),
                                            ("judge.model", "model" in (fixture.get("judge") or {})))
                    if pinned]
            with self.subTest(fixture=path):
                if path in PINNED_WITH_REASON:
                    self.assertTrue(pins, "listed as pinned, but the fixture pins nothing")
                    self.assertTrue(PINNED_WITH_REASON[path].strip())
                else:
                    self.assertEqual(pins, [], "a pin needs a reason in PINNED_WITH_REASON")

    def test_the_committed_roster_selects_both_models(self):
        roster = yaml.safe_load(ROSTER.read_text(encoding="utf-8"))
        arms = [arm["id"] for arm in roster["arms"]]
        for path, fixture in fixtures().items():
            if path in PINNED_WITH_REASON:
                continue
            with self.subTest(fixture=path):
                agent, judge, problem = run_eval.select_models(fixture, argparse.Namespace(
                    model=None, no_judge=False, roster=ROSTER))
                self.assertIsNone(problem)
                self.assertIn(agent, arms)
                self.assertIsInstance(judge, str)


class ScheduledFixturesDeclareTheirContext(unittest.TestCase):
    def test_each_fixture_has_a_context_or_a_stated_reason_for_none(self):
        for path, fixture in fixtures().items():
            with self.subTest(fixture=path):
                if path in ISOLATION_ONLY:
                    self.assertNotIn("context", fixture,
                                     "listed as isolation-only, but the fixture has a context")
                    self.assertTrue(ISOLATION_ONLY[path].strip())
                else:
                    self.assertIn("context", fixture,
                                  "no context needs a reason in ISOLATION_ONLY")
                    # The resolver's schema check; load_fixture already ran it,
                    # and it is called again here so the requirement is stated.
                    context.validate_context(fixture, ROOT / path / "fixture.yaml")

    def test_both_revisions_are_full_commit_shas(self):
        for path, fixture in fixtures().items():
            if path in ISOLATION_ONLY:
                continue
            for key in ("revision", "guidance_revision"):
                with self.subTest(fixture=path, key=key):
                    value = fixture["context"][key]
                    # The schema allows a null guidance pin (a blocked
                    # fixture); a scheduled fixture may not carry one.
                    self.assertIsInstance(value, str)
                    self.assertRegex(value, SHA)

    def test_every_budget_limit_is_present(self):
        for path, fixture in fixtures().items():
            if path in ISOLATION_ONLY:
                continue
            with self.subTest(fixture=path):
                budget = fixture["context"]["budget"]
                self.assertEqual(set(budget), set(context.BUDGET_KEYS))
                for key, value in budget.items():
                    self.assertIs(type(value), int, key)
                    # 1 is the scaffolder's unmeasured placeholder.
                    self.assertGreater(value, 1, key)

    def test_each_fixture_still_declares_its_isolation_pair(self):
        # --pairing isolation stays runnable: the skill alone against nothing.
        for path, fixture in fixtures().items():
            with self.subTest(fixture=path):
                self.assertEqual(list(fixture["arms"]), ["with_skill", "without_skill"])
                self.assertEqual(fixture["arms"]["with_skill"]["install"], "copy")
                self.assertEqual(fixture["arms"]["without_skill"]["install"], "none")


class ScheduleReadinessNotes(unittest.TestCase):
    def test_recorded_baselines_say_which_pair_and_models_produced_them(self):
        for row in scheduled():
            with self.subTest(fixture=row["path"]):
                note = row["readiness"]
                self.assertIn("isolation pair", note.lower())
                self.assertIn("claude-sonnet-5", note)


if __name__ == "__main__":
    unittest.main()
