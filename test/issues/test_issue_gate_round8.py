#!/usr/bin/env python3
"""PR 649's eighth adversarial round on the betting gate (2026-11-03).

Each class pins one finding of
/mnt/project-files/reports/pr649-adversarial-round8.md:

  * M1: the improve lane files no `needs-fixtures` (or `needs-harder-
    fixtures`) item for a skill the gate owns for retirement, including a
    skill whose scope pauses drop it under MIN_IMPROVE_FIXTURES;
  * m1: the improve and description-trim lanes skip a skill with an open
    `retire-skill/<skill>` pull request, as the trigger lane does;
  * m2: the trigger lane treats `retire-pending` as owned by retirement.

Hermetic and deterministic: canned runs, temporary directories, no network,
no clock.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import plan_week  # noqa: E402
import run_eval  # noqa: E402
from test_issue_gate_round3 import pairs  # noqa: E402

REAL_MODELS = ["claude-sonnet-5-5", "claude-opus-5-5"]
NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def build(fixtures, paused):
    """A temporary `evals/` copy holding skill zz-demo with `fixtures`, those
    in `paused` scope-paused by the zero-use rule, and 25 canned 50/50 pairs
    per cell (a `retire`/`auto` skill)."""
    root = Path(tempfile.mkdtemp(prefix="round8-"))
    shutil.copytree(ROOT / "evals", root / "evals")
    for f in fixtures:
        d = root / "evals" / "zz-demo" / f
        d.mkdir(parents=True)
        (d / "fixture.yaml").write_text(
            f"skill: zz-demo\nregistry: {plan_week.REGISTRY_URL}\nprompt: {f}\n"
            "context:\n  repo: Adam-S-Daniel/example\n  ref: abc\n  guidance_revision: abc\n")
    sa = root / "evals" / "scope-auto.yml"
    sa.write_text(sa.read_text() + "".join(
        f"  - path: evals/zz-demo/{f}\n    rule: \"zero-use\"\n" for f in paused))
    un = root / "evals" / "unscheduled.yml"
    un.write_text(un.read_text() + "".join(
        f"  - path: evals/zz-demo/{f}\n    reason: \"Auto scope (zero-use), "
        "2026-11-03: x\"\n" for f in paused))
    sch = root / "evals" / "scheduled.yml"
    sch.write_text(sch.read_text() + "".join(
        f"  - path: evals/zz-demo/{f}\n    readiness: \"x\"\n"
        for f in fixtures if f not in paused))
    for args in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    digests = {f: run_eval.fixture_digest(root / "evals" / "zz-demo" / f) for f in fixtures}
    runs = []
    for i, m in enumerate(REAL_MODELS):
        for j, f in enumerate(fixtures):
            runs += pairs(f, 25, 50, 50, start=1000 * i + 100 * j, model=m, skill="zz-demo")
    runs = [{**r, "fixture_digest": digests[r["fixture"]]} for r in runs]
    return root, {"runs": runs, "skills": ["zz-demo"], "skipped": {}, "bare_runs": [],
                  "guidance_runs": [], "sections": []}


def skill(verdict="insufficient", fixtures=4):
    return {"fixtures": fixtures, "holdout": "a", "registry_ok": True, "verdict": verdict,
            "evidence": {"headroom": 0.4, "targets": ["t1"]}, "pause": None}


class ImproveNeedsFixturesOwnedByRetirementTests(unittest.TestCase):
    """M1, end to end through `compute_gates.compute`."""

    def improve(self, fixtures, paused):
        root, index = build(fixtures, paused)
        self.addCleanup(shutil.rmtree, root)
        ev = root / "evals"
        with mock.patch.object(compute_gates, "build_index", return_value=index), \
                mock.patch.object(compute_gates, "tested_digest", return_value="t1"):
            doc = compute_gates.compute(root / "results", ev / "roster.yml",
                                        ev / "gate-policy.yml", ev, "20261104T000000Z")
            skills = plan_week.skill_contexts(ev, root / "results", "20261104T000000Z", {},
                                              doc, [], [], [], NOW)
        self.assertEqual(
            (doc["skills"]["zz-demo"]["verdict"], doc["skills"]["zz-demo"].get("removal")),
            ("retire", "auto"))
        ctx = {"skills": skills, "skill_weights": {"zz-demo": 0}, "removal_prs": set(),
               "gate_verdicts": plan_week.gate_verdicts(doc), "private_skills": [],
               "improve_charge": 0.05}
        fires, work, status, *_ = plan_week.improve_items(ctx, NOW)
        return skills["zz-demo"], fires, work, status["zz-demo"]

    def test_three_fixtures_retire_skill_files_no_needs_fixtures(self):
        s, fires, work, status = self.improve(("a", "b", "c"), ())
        self.assertEqual(s["fixtures"], 3)
        self.assertEqual((fires, work), ([], []))
        self.assertIn("owned by retirement (retire)", status["reasons"])

    def test_a_scope_pause_that_drops_the_count_files_no_needs_fixtures(self):
        s, fires, work, status = self.improve(("a", "b", "c", "d"), ("d",))
        self.assertEqual(s["fixtures"], 3, "the pause shrinks the count: the premise")
        self.assertEqual((fires, work), ([], []))
        self.assertIn("owned by retirement (retire)", status["reasons"])

    def test_control_four_fixtures_plans_nothing(self):
        _, fires, work, status = self.improve(("a", "b", "c", "d"), ())
        self.assertEqual((fires, work), ([], []))
        self.assertIn("owned by retirement (retire)", status["reasons"])

    def run_ctx(self, verdict, removal=(), gate=None, fixtures=3, headroom=0.4):
        s = skill(verdict, fixtures)
        s["evidence"]["headroom"] = headroom
        ctx = {"skills": {"zz-demo": s}, "skill_weights": {"zz-demo": 0},
               "removal_prs": set(removal), "private_skills": [], "improve_charge": 0.05}
        if gate is not None:
            ctx["gate_verdicts"] = gate
        return plan_week.improve_items(ctx, NOW)

    def test_a_kept_skill_with_three_fixtures_still_gets_the_item(self):
        _, work, *_ = self.run_ctx("insufficient")
        self.assertEqual([(w["kind"], w["route"]) for w in work], [("needs-fixtures", "issue")])

    def test_needs_harder_fixtures_is_unchanged_for_a_kept_skill(self):
        _, work, *_ = self.run_ctx("insufficient", fixtures=4, headroom=0.0)
        self.assertEqual([w["kind"] for w in work], ["needs-harder-fixtures"])

    def test_the_gate_document_verdict_beats_the_context_one(self):
        _, work, *_ = self.run_ctx("insufficient", gate={"zz-demo": "retire-pending"})
        self.assertEqual(work, [])

    def test_retire_pending_files_no_item(self):
        _, work, *_ = self.run_ctx("retire-pending")
        self.assertEqual(work, [])

    def test_an_open_removal_pr_files_no_item(self):
        fires, work, status, *_ = self.run_ctx("insufficient", removal={"zz-demo"})
        self.assertEqual((fires, work), ([], []))
        self.assertIn("owned by retirement (open removal PR)", status["zz-demo"]["reasons"])


class ImproveSkipsAZeroUseSkillTests(unittest.TestCase):
    """2026-11-12: a skill whose `zero_use` is True is not improved."""

    def run_ctx(self, zero):
        ctx = {"skills": {"zz-demo": skill()}, "skill_weights": {"zz-demo": 0},
               "removal_prs": set(), "gate_verdicts": {"zz-demo": "insufficient"},
               "private_skills": [], "improve_charge": 0.05, "zero_use_skills": zero}
        return plan_week.improve_items(ctx, NOW)

    def test_a_zero_use_skill_is_ineligible(self):
        fires, _, status, *_ = self.run_ctx(frozenset({"zz-demo"}))
        self.assertEqual(fires, [])
        self.assertFalse(status["zz-demo"]["eligible"])
        self.assertTrue(any("zero use" in r for r in status["zz-demo"]["reasons"]))

    def test_the_control_without_it_is_eligible(self):
        fires, _, status, *_ = self.run_ctx(frozenset())
        self.assertEqual([f["skill"] for f in fires], ["zz-demo"])
        self.assertTrue(status["zz-demo"]["eligible"])


class ZeroUseSkillsTests(unittest.TestCase):
    """`plan_week.zero_use_skills`: True only, and never an exempt skill."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="zero-use-skills-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "evals").mkdir()
        (self.tmp / "usage").mkdir()

    def census(self, sessions):
        import skill_usage
        floor = NOW - timedelta(weeks=20)
        label = "2026-W45"
        rows = [skill_usage.listing_row(label, "full", sessions),
                skill_usage.listing_row(label, "full", sessions, skill_usage.SURFACE_CLOUD)]
        doc = skill_usage.document(
            rows, NOW, floor, sessions_scanned=1,
            cloud_guidance={"from": floor, "records_scanned": 1, "listing_recorded": True},
            skill_keys=["zz-demo", "zz-exempt"])
        skill_usage.add_rows(doc, [], skill_usage.digest_source(
            floor, NOW, 0, surface=skill_usage.SURFACE_CLOUD))
        (self.tmp / "usage" / "weekly-local.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_only_an_unexempt_zero_use_skill_is_listed(self):
        self.census(300)
        (self.tmp / "evals" / "usage-unknown.yml").write_text(
            'skills:\n  - skill: zz-exempt\n    reason: "x"\n', encoding="utf-8")
        self.assertEqual(plan_week.zero_use_skills(self.tmp, ["zz-demo", "zz-exempt"], NOW, {},
                                                   self.tmp / "evals"), frozenset({"zz-demo"}))

    def test_too_few_sessions_or_no_census_is_unknown_so_eligible(self):
        self.assertEqual(plan_week.zero_use_skills(self.tmp, ["zz-demo"], NOW, {},
                                                   self.tmp / "evals"), frozenset())
        self.census(10)
        self.assertEqual(plan_week.zero_use_skills(self.tmp, ["zz-demo"], NOW, {},
                                                   self.tmp / "evals"), frozenset())


class LanesSkipAnOpenRemovalPrTests(unittest.TestCase):
    """m1: ctx shaped as `lanes_removal_pr.py` of round 8 builds it."""

    def ctx(self, **extra):
        return {"skills": {"zz-demo": skill()}, "skill_weights": {"zz-demo": 0},
                "removal_prs": {"zz-demo"}, "gate_verdicts": {"zz-demo": "insufficient"},
                "private_skills": [], "improve_charge": 0.05,
                "triggers": {"zz-demo": {"trigger_set": True, "hook_candidate": False,
                                         "pause": None}},
                "trims": {"zz-demo": {"chars": 520, "plugin": "demo-plugin", "busy": False}},
                **extra}

    def test_improve_skips_it(self):
        fires, _, status, *_ = plan_week.improve_items(self.ctx(), NOW)
        self.assertEqual(fires, [])
        self.assertEqual(status["zz-demo"]["reasons"], ["owned by retirement (open removal PR)"])

    def test_trim_skips_it(self):
        fires, status, _ = plan_week.trim_items(self.ctx())
        self.assertEqual(fires, [])
        self.assertEqual(status["zz-demo"]["reasons"], ["owned by retirement (open removal PR)"])

    def test_the_controls_without_the_pr_still_plan(self):
        ctx = self.ctx(removal_prs=set())
        self.assertEqual([f["skill"] for f in plan_week.improve_items(ctx, NOW)[0]], ["zz-demo"])
        self.assertEqual([f["skill"] for f in plan_week.trim_items(ctx)[0]], ["zz-demo"])

    def test_trigger_still_skips_it(self):
        fires, _, _, status = plan_week.trigger_items(self.ctx())
        self.assertEqual(fires, [])
        self.assertEqual(status["zz-demo"]["reasons"], ["owned by retirement (open removal PR)"])


class TriggerRetirePendingTests(unittest.TestCase):
    """m2: `retire-pending` from `gate_verdicts` owns the skill for the trigger lane."""

    def test_retire_pending_is_owned_by_retirement(self):
        for has_set in (True, False):
            ctx = {"skills": {}, "skill_weights": {"zz-demo": 0}, "removal_prs": set(),
                   "gate_verdicts": {"zz-demo": "retire-pending"}, "private_skills": [],
                   "improve_charge": 0.05,
                   "triggers": {"zz-demo": {"trigger_set": has_set, "hook_candidate": False,
                                            "pause": None}}}
            fires, work, _, status = plan_week.trigger_items(ctx)
            self.assertEqual((fires, work), ([], []), has_set)
            self.assertEqual(status["zz-demo"]["reasons"],
                             ["owned by retirement (retire-pending)"])


if __name__ == "__main__":
    unittest.main()
