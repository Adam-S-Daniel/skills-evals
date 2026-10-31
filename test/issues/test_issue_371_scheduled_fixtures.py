"""#371 item 5 and ADR 0012: the scheduled fixtures follow the roster and
declare the context an in-place pair runs in.

Everything here reads committed files only: the schedule and each fixture are
parsed as YAML, and a `context:` block goes through the resolver's own schema
check. No repository is resolved, no network is used and no model is called.
Run with: python3 -m pytest test/issues/test_issue_371_scheduled_fixtures.py -q
"""

from __future__ import annotations

import argparse
import math
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

# A scheduled fixture with no provable `guidance_revision`, or no `context`
# at all, stays an isolation pair and is named here with the reason.
_NO_CONTEXT_YET = ("Merged hermetic before in-place pairs existed and declares no `context`; scheduled as an isolation pair until a context is scaffolded and measured.")
_PRIVATE = ("A private-registry skill (adam-agentskills-private): no public "
            "context repository carries it, so it runs as an isolation pair.")
ISOLATION_ONLY: dict[str, str] = {
    "evals/rename-pdfs": _NO_CONTEXT_YET,
    "evals/pdf-ocr-audit": _NO_CONTEXT_YET,
    "evals/cms-stuck-pr-triage": _NO_CONTEXT_YET,
    "evals/post-failure-comment": _NO_CONTEXT_YET,
    "evals/admin-config-render": _NO_CONTEXT_YET,
    "evals/code-quality": _NO_CONTEXT_YET,
    "evals/ci-watcher-loops": _NO_CONTEXT_YET,
    "evals/editorial-label-audit": _NO_CONTEXT_YET,
    "evals/consumer-repo-provisioning": _NO_CONTEXT_YET,
    # In place would mean a context repository holding the private skill;
    # its results stay in the private repository (#81).
    "evals/adam-writing-style/proposal-bio": _PRIVATE,
    "evals/adam-writing-style/recruiter-reply": _PRIVATE,
    "evals/adam-writing-style/self-appraisal-opening": _PRIVATE,
}

# What each in-place arm measured on 2026-10-10, as (guidance, catalog,
# payload) bytes: the context alone, then the `with` arm. The two differ only
# where the context does not hold the skill and `with` adds the registry's
# copy; the harness checks that larger arm against the same limits
# (`run_eval._check_with_budget`). Measured through `run_eval._in_place_plan`
# against clones of the context repositories, which no test here can reach,
# so these are recorded figures: re-measure and update them with the budget.
_CMS_PLATFORM = (25099, 6082, 685637)
_ADAMDANIEL_AI = (25099, 14017, 885455)
MEASURED: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "evals/workflow-path-audit/required-check-routing": (_CMS_PLATFORM, _CMS_PLATFORM),
    "evals/embeddable-tool-pages": (_ADAMDANIEL_AI, (25099, 14646, 892334)),
    "evals/review-bash-ci-reliability/release-pipeline": (_CMS_PLATFORM, _CMS_PLATFORM),
    "evals/skills-doctor/bucketed-account-store": ((25099, 6115, 644882),) * 2,
    "evals/github-actions-sha-pinning": (_ADAMDANIEL_AI, _ADAMDANIEL_AI),
    "evals/writing-adrs/bootstrap": (_CMS_PLATFORM, _CMS_PLATFORM),
    "evals/disarm-inherited-reach": (_CMS_PLATFORM, _CMS_PLATFORM),
    # wsl-automation's lock resolves to the same skills as cms-platform's.
    "evals/windows-elevation-from-wsl": (_CMS_PLATFORM, (25099, 7180, 695580)),
    # Not re-measured: the largest figures the fixture's committed budget
    # (set when it was scaffolded) allows under HEADROOM. The context's
    # adamdaniel.ai lock already carries the cms-platform skill, so both arms
    # match.
    "evals/platform-release-and-bump": ((25099, 14017, 882787),) * 2,
}
MEASURED_KEYS = ("guidance_bytes", "skill_catalog_bytes", "skill_payload_bytes")
HEADROOM = 1.25


def scheduled() -> list[dict]:
    """The reviewed entries this module's recorded figures cover. An entry
    `scaffold_real_work.py promote` appended (its readiness note starts
    "Promoted automatically") is a real-work or other draft promoted after
    clean runs; test_issue_scheduled_fixtures.py checks those."""
    return [row for row in yaml.safe_load(SCHEDULE.read_text(encoding="utf-8"))["fixtures"]
            if not row["readiness"].startswith("Promoted automatically")]


def all_fixtures() -> dict[str, dict]:
    return {row["path"]: run_eval.load_fixture(ROOT / row["path"]) for row in scheduled()}


def fixtures() -> dict[str, dict]:
    """The scheduled SKILL fixtures, the ones a context and an in-place pair
    apply to. A guidance section fixture (#124) runs its own four arms
    against the guidance alone: test_issue_124_guidance_gates.py covers it."""
    return {path: fixture for path, fixture in all_fixtures().items()
            if fixture.get("subject") != "guidance"}


class ScheduledFixturesFollowTheRoster(unittest.TestCase):
    def test_the_schedule_names_twenty_one_skill_and_thirty_two_guidance_fixtures(self):
        paths = [row["path"] for row in scheduled()]
        self.assertEqual(len(paths), 53)
        self.assertEqual(len(set(paths)), 53)
        self.assertEqual(len(fixtures()), 21)
        self.assertEqual(sorted(set(all_fixtures()) - set(fixtures())),
                         sorted(str(p.parent.relative_to(ROOT)) for p in
                                (ROOT / "evals/guidance").glob("[!_]*/*/fixture.yaml")))

    def test_no_fixture_pins_a_model_without_a_stated_reason(self):
        for path, fixture in all_fixtures().items():
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
        for path, fixture in all_fixtures().items():
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

    def test_each_limit_leaves_a_quarter_of_headroom_on_the_larger_arm(self):
        # A limit sized on the context alone leaves the `with` arm of an
        # added skill short: 7603 against 7180 catalog bytes was 5.9%.
        self.assertEqual(set(MEASURED), set(fixtures()) - set(ISOLATION_ONLY))
        self.assertEqual(set(MEASURED_KEYS), set(context.BUDGET_KEYS))
        for path, fixture in fixtures().items():
            if path in ISOLATION_ONLY:
                continue
            context_only, with_arm = MEASURED[path]
            for index, key in enumerate(MEASURED_KEYS):
                with self.subTest(fixture=path, key=key):
                    self.assertGreaterEqual(with_arm[index], context_only[index])
                    self.assertEqual(fixture["context"]["budget"][key],
                                     math.ceil(with_arm[index] * HEADROOM))

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
                # Either pairing and any model: the first in-place baseline
                # must not need this test edited.
                self.assertRegex(note, r"(?i)\b(isolation|in-place) pair\b")
                self.assertRegex(note, r"\bclaude-[a-z]+-[0-9]")


if __name__ == "__main__":
    unittest.main()
