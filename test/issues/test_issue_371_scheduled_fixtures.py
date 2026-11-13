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
import shutil
import sys
import tempfile
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
_PRIVATE = ("A private-registry skill (adam-agentskills-private): no public "
            "context repository carries it, so it runs as an isolation pair.")
ISOLATION_ONLY: dict[str, str] = {}

# The ratchet: ISOLATION_ONLY may only shrink. Each conversion PR removes its
# own entry here and in ISOLATION_ONLY and adds its MEASURED row, so a
# converted fixture cannot go back; nothing may be added except a _PRIVATE
# fixture (no public context repository carries its skill). skills-evals#574
# converted sixteen of the last eighteen hermetic fixtures; the two PDF
# skills stayed, with a reason of their own.
LEGACY_ISOLATION: frozenset[str] = frozenset()

# What each in-place arm measured on 2026-10-10, as (guidance, catalog,
# payload) bytes: the context alone, then the `with` arm. The two differ only
# where the context does not hold the skill and `with` adds the registry's
# copy; the harness checks that larger arm against the same limits
# (`run_eval._check_with_budget`). Measured through `run_eval._in_place_plan`
# against clones of the context repositories, which no test here can reach,
# so these are recorded figures: re-measure and update them with the budget.
_CMS_PLATFORM = (25099, 6082, 685637)
_ADAMDANIEL_AI = (25099, 14017, 885455)
# skills-evals#574: adamdaniel.ai 2a994ee0 (guidance 6a1ca565), and
# cms-platform dfb0fddf and _agent-guidance 0295fa86 (both guidance
# 0295fa86), which deploy the same two adam-agentskills bundles.
_ADAMDANIEL_AI_574 = (25528, 14803, 875774)
_FLEET_574 = (25528, 7447, 688780)
# 2026-11-03: the two PDF skills (adam-non-coding-local, which no fleet lock
# adopts) are added to wsl-automation 50d66105 (guidance 570544a8), as
# windows-elevation-from-wsl is: a session on the owner's machine loads the
# same base guidance and both cloud-safe bundles. Their own bundle's other
# skills (ocr-pdfs, compare-pdfpairs) are not in the context, a gap the
# owner's machine does not have; without a context they could never reach a
# verdict (adversarial gap review, 2026-11-03, item 5). Measured by
# scripts/contextualize_fixtures.py's Measurer with main's copy at
# adam-agentskills 6dd9b1e.
_WSL_1103 = (25528, 7447, 688780)
MEASURED: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "evals/rename-pdfs": (_WSL_1103, (25528, 8105, 709885)),
    "evals/pdf-ocr-audit": (_WSL_1103, (25528, 7983, 699500)),
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
    # Not re-measured either (context repo-settings): the largest figures
    # its committed budget allows under HEADROOM, recorded for both arms.
    "evals/github-actions-repo-settings/drift-diagnosis": ((24478, 6107, 672169),) * 2,
    # Measured 2026-11-02 through `run_eval._in_place_plan` against the local
    # clones; both arms match because the context already carries the skill.
    **{f"evals/review-bash-ci-reliability/{name}": (_CMS_PLATFORM, _CMS_PLATFORM)
       for name in ("drift-report-capture", "nightly-snapshot",
                    "test-runner-assertions")},
    "evals/skills-doctor/personal-copy-outranks-repo": ((25099, 6115, 644882),) * 2,
    # skills-evals#574, measured 2026-11-02 through `run_eval._in_place_plan`
    # against the local clones, with main's copy from registry checkouts at
    # adam-agentskills 6e6373cc and cms-platform cd59b51f. Every one is
    # adopted and matches in both arms: each context deploys main's digest
    # of its subject.
    **{path: (_ADAMDANIEL_AI_574, _ADAMDANIEL_AI_574)
       for path in ("evals/cms-stuck-pr-triage", "evals/post-failure-comment",
                    "evals/consumer-repo-provisioning")},
    **{path: (_FLEET_574, _FLEET_574)
       for path in ("evals/ci-job-performance/browser-cache",
                    *(f"evals/vendor-release-impact-issues/{name}"
                      for name in ("closed-duplicate", "closing-keywords",
                                   "issue-hygiene", "stamps-skip-quotes")))},
}
# Re-measured 2026-11-02 after the cms-platform fixtures were re-pinned from
# 28f2b6ed to its `main` at 6c8eca12 (the lock there deploys adam-agentskills
# main's digest of each subject; at 28f2b6ed it deployed an older copy, so
# those runs never tested the shipped skill), guidance proven at a13d5dab.
# Through `run_eval._in_place_plan`, both arms equal because the context
# adopts the skill. MEASURED above stays what each budget was sized on
# (`sized_on`); this is what the pinned context measures today (`measured`).
# The larger arm fits the committed budget, so no budget moved.
_CMS_PLATFORM_NOW = (25188, 7447, 688780)
REMEASURED: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    path: (_CMS_PLATFORM_NOW, _CMS_PLATFORM_NOW)
    for path in (
        "evals/disarm-inherited-reach",
        "evals/review-bash-ci-reliability/drift-report-capture",
        "evals/review-bash-ci-reliability/nightly-snapshot",
        "evals/review-bash-ci-reliability/release-pipeline",
        "evals/review-bash-ci-reliability/test-runner-assertions",
        "evals/writing-adrs/bootstrap")}
# Re-measured 2026-11-02 the same way after the skills-doctor fixtures moved
# from adam-agentskills 2a322dde to its `main` at 064652db, the repo-settings
# fixture from 19378e8d to 56c9dac9, and github-actions-sha-pinning from
# adamdaniel.ai 8074d5a3 to 67b5e002, guidance proven at 5ca459fc. Each
# context now deploys adam-agentskills main's digest of its subject.
_ADAM_AGENTSKILLS_NOW = (25512, 7447, 688780)
_REPO_SETTINGS_NOW = (25512, 7447, 688780)
_ADAMDANIEL_AI_NOW = (25512, 14803, 861762)
REMEASURED.update({
    **{f"evals/skills-doctor/{name}": (_ADAM_AGENTSKILLS_NOW,) * 2
       for name in ("bucketed-account-store", "personal-copy-outranks-repo")},
    "evals/github-actions-repo-settings/drift-diagnosis": (_REPO_SETTINGS_NOW,) * 2,
    "evals/github-actions-sha-pinning": (_ADAMDANIEL_AI_NOW,) * 2,
    # adamdaniel.ai ddf1c992 -> da05fc6b (after its #4569 lock re-pin).
    "evals/platform-release-and-bump": ((25512, 14803, 875774),) * 2,
})
# Re-measured 2026-11-03 through `run_eval._in_place_plan` after the three
# added-skill fixtures moved off pins older than the fleet hook runner:
# embeddable-tool-pages to adamdaniel.ai 2dcf61ff, windows-elevation-from-wsl
# to wsl-automation 50d66105 and finding-unknowns to skills-evals e6e9496b,
# guidance proven at 570544a8 for all three, main's copy from adam-agentskills
# 6dd9b1ef. No budget moved.
REMEASURED.update({
    "evals/embeddable-tool-pages": ((25528, 14803, 875774), (25528, 15395, 882224)),
    "evals/windows-elevation-from-wsl": ((25528, 7447, 688780), (25528, 7987, 698461)),
})
# REMEASURED is a recorded snapshot, not something this module can recompute.
# Since skills-evals#559 the with arm tests main's copy of an adopted subject,
# not the deployed one. Re-measured 2026-11-02 through `run_eval._in_place_plan`
# against the local clones, at each fixture's pinned context revision, with
# main's copy from registry checkouts at adam-agentskills d5f3da19 and
# cms-platform cd59b51f: drift-diagnosis, github-actions-sha-pinning,
# platform-release-and-bump and the four skills-doctor fixtures. Each pinned
# context already deploys main's digest of its subject, so main's copy changed
# no figure above.
# The adopted fixtures: the with arm swaps the deployed copy for main's,
# which can be smaller than the copy the context measured, so the with arm
# may measure below the context alone. The added ones only add a skill.
ADOPTED = frozenset({
    "evals/disarm-inherited-reach",
    "evals/github-actions-repo-settings/drift-diagnosis",
    "evals/github-actions-sha-pinning",
    "evals/platform-release-and-bump",
    *(f"evals/review-bash-ci-reliability/{name}"
      for name in ("drift-report-capture", "nightly-snapshot",
                   "release-pipeline", "test-runner-assertions")),
    *(f"evals/skills-doctor/{name}"
      for name in ("bucketed-account-store", "personal-copy-outranks-repo")),
    "evals/writing-adrs/bootstrap",
    # skills-evals#574.
    "evals/ci-job-performance/browser-cache",
    "evals/cms-stuck-pr-triage",
    "evals/consumer-repo-provisioning",
    "evals/post-failure-comment",
    *(f"evals/vendor-release-impact-issues/{name}"
      for name in ("closed-duplicate", "closing-keywords", "issue-hygiene",
                   "stamps-skip-quotes")),
})
MEASURED_KEYS = ("guidance_bytes", "skill_catalog_bytes", "skill_payload_bytes")
HEADROOM = 1.25


def scheduled() -> list[dict]:
    """The reviewed entries this module's recorded figures cover. An entry
    `scaffold_real_work.py promote` appended (its readiness note starts
    "Promoted automatically") is a real-work or other draft promoted after
    clean runs; test_issue_scheduled_fixtures.py checks those."""
    rows = yaml.safe_load(SCHEDULE.read_text(encoding="utf-8"))["fixtures"]
    # A fixture the eval scope pass paused (evals/scope-auto.yml keeps its
    # readiness note) is still one of these: it comes back by rule, so its
    # recorded figures must keep holding while it is off the schedule.
    auto = yaml.safe_load((ROOT / "evals/scope-auto.yml").read_text(encoding="utf-8")) or {}
    rows = rows + [{"path": row["path"], "readiness": row["readiness"]}
                   for row in auto.get("rows") or []]
    # A fixture pull request's row ("Added by a fixture pull request",
    # scripts/fixture_pr_gate.py) is checked there too.
    return [row for row in rows
            if not row["readiness"].startswith(("Promoted automatically",
                                                "Added by a fixture pull request"))]


def all_fixtures() -> dict[str, dict]:
    return {row["path"]: run_eval.load_fixture(ROOT / row["path"]) for row in scheduled()}


def fixtures() -> dict[str, dict]:
    """The scheduled SKILL fixtures, the ones a context and an in-place pair
    apply to. A guidance section fixture (#124) runs its own four arms
    against the guidance alone: test_issue_124_guidance_gates.py covers it."""
    return {path: fixture for path, fixture in all_fixtures().items()
            if fixture.get("subject") != "guidance"}


class ScheduledFixturesFollowTheRoster(unittest.TestCase):
    def test_the_schedule_names_twenty_three_skill_and_twenty_eight_guidance_fixtures(self):
        paths = [row["path"] for row in scheduled()]
        self.assertEqual(len(paths), 51)
        self.assertEqual(len(set(paths)), 51)
        self.assertEqual(len(fixtures()), 23)
        # Guidance fixtures off the schedule (2026-11-03 scope decision) need
        # no unscheduled.yml row; they are simply not scheduled.
        scheduled_guidance = sorted(set(all_fixtures()) - set(fixtures()))
        self.assertEqual(len(scheduled_guidance), 28)
        on_disk = {str(p.parent.relative_to(ROOT)) for p in
                   (ROOT / "evals/guidance").glob("[!_]*/*/fixture.yaml")}
        self.assertLessEqual(set(scheduled_guidance), on_disk)

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


class IsolationExemptionIsAOneWayRatchet(unittest.TestCase):
    PRIVATE_REGISTRY = "https://github.com/Adam-S-Daniel/adam-agentskills-private"

    def test_isolation_only_never_grows_past_the_legacy_set(self):
        self.assertLessEqual(ISOLATION_ONLY.keys(), LEGACY_ISOLATION)

    def test_the_legacy_set_shrinks_with_each_conversion(self):
        # A conversion removes its path from both, so no converted fixture
        # can silently go back to isolation-only.
        self.assertEqual(LEGACY_ISOLATION, set(ISOLATION_ONLY) - {
            path for path, reason in ISOLATION_ONLY.items()
            if reason == _PRIVATE and path not in LEGACY_ISOLATION})

    def test_only_private_fixtures_may_be_outside_the_legacy_set(self):
        for path, reason in ISOLATION_ONLY.items():
            if reason != _PRIVATE:
                with self.subTest(fixture=path):
                    self.assertIn(path, LEGACY_ISOLATION)

    def test_each_private_entry_names_the_private_registry(self):
        for path, reason in ISOLATION_ONLY.items():
            if reason == _PRIVATE:
                with self.subTest(fixture=path):
                    doc = yaml.safe_load((ROOT / path / "fixture.yaml").read_text(encoding="utf-8"))
                    self.assertEqual(doc.get("registry"), self.PRIVATE_REGISTRY)


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
        self.assertLessEqual(set(REMEASURED), set(MEASURED))
        added = {"evals/embeddable-tool-pages",
                 "evals/windows-elevation-from-wsl", "evals/rename-pdfs",
                 "evals/pdf-ocr-audit"}
        self.assertFalse(added & ADOPTED)
        # A new in-place fixture is classified, never exempted by default.
        self.assertEqual(ADOPTED | added, set(MEASURED))
        for path, (measured_context, measured) in REMEASURED.items():
            if any(arm < alone for arm, alone in zip(measured, measured_context)):
                self.assertIn(path, ADOPTED)
        for path, fixture in fixtures().items():
            if path in ISOLATION_ONLY:
                continue
            sized_on_context, sized_on = MEASURED[path]
            measured_context, measured = REMEASURED.get(path, MEASURED[path])
            for index, key in enumerate(MEASURED_KEYS):
                with self.subTest(fixture=path, key=key):
                    budget = fixture["context"]["budget"][key]
                    self.assertGreaterEqual(sized_on[index], sized_on_context[index])
                    if path not in ADOPTED:
                        self.assertGreaterEqual(measured[index], measured_context[index])
                    self.assertEqual(budget, math.ceil(sized_on[index] * HEADROOM))
                    # What the pinned context measures today must fit.
                    self.assertLessEqual(measured[index], budget)

    def test_each_fixture_still_declares_its_isolation_pair(self):
        # --pairing isolation stays runnable: the skill alone against nothing.
        for path, fixture in fixtures().items():
            with self.subTest(fixture=path):
                # No `arms` key is the same pair: run_eval takes a skill
                # fixture's arms from --arm (`arm_names`), never from it.
                arms = fixture.get("arms", {"with_skill": {"install": "copy"},
                                            "without_skill": {"install": "none"}})
                self.assertEqual(list(arms), ["with_skill", "without_skill"])
                self.assertEqual(arms["with_skill"]["install"], "copy")
                self.assertEqual(arms["without_skill"]["install"], "none")


class ScheduleReadinessNotes(unittest.TestCase):
    def test_recorded_baselines_say_which_pair_and_models_produced_them(self):
        for row in scheduled():
            with self.subTest(fixture=row["path"]):
                note = row["readiness"]
                # Either pairing and any model: the first in-place baseline
                # must not need this test edited.
                self.assertRegex(note, r"(?i)\b(isolation|in-place) pair\b")
                self.assertRegex(note, r"\bclaude-[a-z]+-[0-9]")


UNSCHEDULED = ROOT / "evals/unscheduled.yml"


def skill_fixture_paths(root: Path) -> dict[str, dict]:
    """Every non-draft skill fixture under `root`/evals, by its
    `evals/...` path: a fixture.yaml with a string `skill:` key and no
    guidance `subject`. Parsed as YAML."""
    out = {}
    for file in sorted((root / "evals").glob("**/fixture.yaml")):
        doc = yaml.safe_load(file.read_text(encoding="utf-8"))
        if (isinstance(doc, dict) and isinstance(doc.get("skill"), str)
                and doc.get("subject") != "guidance" and doc.get("draft") is not True):
            out[file.parent.relative_to(root).as_posix()] = doc
    return out


def schedule_problems(root: Path) -> list[str]:
    """Violations of Adam's 2026-11-02 rule (require a reason to leave a
    fixture out) in `root`/evals/scheduled.yml and unscheduled.yml."""
    scheduled_rows = yaml.safe_load((root / "evals/scheduled.yml").read_text(encoding="utf-8"))["fixtures"]
    scheduled_paths = [row["path"] for row in scheduled_rows]
    listed = yaml.safe_load((root / "evals/unscheduled.yml").read_text(encoding="utf-8"))["fixtures"]
    listed_paths = [row["path"] for row in listed]
    skill_fixtures = skill_fixture_paths(root)
    problems = []
    for path in sorted(set(listed_paths)):
        if listed_paths.count(path) > 1:
            problems.append(f"{path}: listed twice")
    for row in listed:
        path, reason = row["path"], row.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"{path}: no reason")
        if path not in skill_fixtures:
            problems.append(f"{path}: not a non-draft skill fixture")
        if path in scheduled_paths:
            problems.append(f"{path}: both scheduled and unscheduled")
    for path in skill_fixtures:
        if path not in scheduled_paths and path not in listed_paths:
            problems.append(f"{path}: neither scheduled nor listed in unscheduled.yml")
    return problems


class EveryFixtureIsScheduledOrExplained(unittest.TestCase):
    def test_the_committed_tree_follows_the_rule(self):
        self.assertEqual(schedule_problems(ROOT), [])

    def _tree(self, scheduled, unscheduled, fixtures):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        for path, doc in fixtures.items():
            (tmp / path).mkdir(parents=True)
            (tmp / path / "fixture.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
        for name, rows in (("scheduled", scheduled), ("unscheduled", unscheduled)):
            (tmp / f"evals/{name}.yml").write_text(yaml.safe_dump({"fixtures": rows}), encoding="utf-8")
        return tmp

    def test_a_synthetic_unlisted_unscheduled_fixture_is_a_problem(self):
        skill = {"skill": "demo", "prompt": "x"}
        tmp = self._tree([{"path": "evals/demo/a", "readiness": "n"}], [],
                         {"evals/demo/a": skill, "evals/demo/b": skill,
                          "evals/demo/c": dict(skill, draft=True)})
        self.assertEqual(schedule_problems(tmp),
                         ["evals/demo/b: neither scheduled nor listed in unscheduled.yml"])

    def test_listed_rows_need_a_reason_a_real_unscheduled_skill_fixture_and_no_repeat(self):
        skill = {"skill": "demo", "prompt": "x"}
        tmp = self._tree([{"path": "evals/demo/a", "readiness": "n"}],
                         [{"path": "evals/demo/a", "reason": "r"},
                          {"path": "evals/demo/b", "reason": "  "},
                          {"path": "evals/demo/b", "reason": "r"},
                          {"path": "evals/demo/gone", "reason": "r"}],
                         {"evals/demo/a": skill, "evals/demo/b": skill})
        problems = schedule_problems(tmp)
        for expected in ("evals/demo/b: listed twice", "evals/demo/a: both scheduled and unscheduled",
                         "evals/demo/b: no reason", "evals/demo/gone: not a non-draft skill fixture"):
            self.assertIn(expected, problems)


if __name__ == "__main__":
    unittest.main()
