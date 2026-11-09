#!/usr/bin/env python3
"""PR 649's ninth adversarial round on the betting gate (2026-11-03).

Each class pins one finding of
/mnt/project-files/reports/pr649-adversarial-round9.md:

  * m1: the improve lane files no `needs-fixtures` or `needs-harder-
    fixtures` item for a guidance section with an open
    `retire-guidance/<section>` pull request, as it already does for a
    skill with an open `retire-skill/<skill>` one;
  * m2: an open removal pull request suppresses a skill's
    `needs-harder-fixtures` item, not only its `needs-fixtures` one (the
    `harder_verdict_only` mutation survived without this).

Hermetic and deterministic: canned contexts, no network, no clock.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import plan_week  # noqa: E402

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)
SECTION = "demo-section"


def skill(verdict, fixtures, headroom):
    return {"fixtures": fixtures, "holdout": "a", "registry_ok": True, "verdict": verdict,
            "evidence": {"headroom": headroom, "targets": ["t1"]}, "pause": None}


class SkillRemovalPrSuppressesHarderFixturesTests(unittest.TestCase):
    """m2: the case the round-8 tests missed."""

    def run_ctx(self, removal):
        ctx = {"skills": {"zz-demo": skill("insufficient", 4, 0.05)},
               "skill_weights": {"zz-demo": 0}, "removal_prs": set(removal),
               "private_skills": [], "improve_charge": 0.05}
        return plan_week.improve_items(ctx, NOW)

    def test_an_open_removal_pr_files_no_needs_harder_fixtures(self):
        fires, work, status, *_ = self.run_ctx({"zz-demo"})
        self.assertEqual((fires, work), ([], []))
        self.assertIn("owned by retirement (open removal PR)", status["zz-demo"]["reasons"])

    def test_control_without_the_pr_files_needs_harder_fixtures(self):
        _, work, *_ = self.run_ctx(())
        self.assertEqual([(w["kind"], w["route"]) for w in work],
                         [("needs-harder-fixtures", "issue")])


class GuidanceRemovalPrOwnsTheSectionTests(unittest.TestCase):
    """m1: ctx shaped as round 9's `guidance_removal_pr.py` builds it."""

    def run_ctx(self, verdict, fixtures, headroom, removal):
        removals = [SECTION] if removal else []
        ctx = {"skills": {}, "skill_weights": {}, "removal_prs": [], "private_skills": [],
               "improve_charge": 0.05, "guidance_removal_prs": removals,
               "guidance": {SECTION: {
                   "fixtures": fixtures, "holdout": "d", "holdout_fixture": "d",
                   "verdict": verdict, "evidence": {"headroom": headroom, "targets": ["t"]},
                   "row_ok": True,
                   "pause": plan_week.guidance_lane(SECTION, [], [], removals)}}}
        fires, work, _, gstatus, _ = plan_week.improve_items(ctx, NOW)
        return fires, [(w["kind"], w["route"]) for w in work], gstatus[SECTION]["reasons"]

    def test_an_open_removal_pr_files_no_needs_fixtures(self):
        for verdict in ("insufficient", "keep"):
            fires, work, reasons = self.run_ctx(verdict, 3, 0.4, removal=True)
            self.assertEqual((fires, work), ([], []), verdict)
            self.assertIn("owned by retirement (open removal PR)", reasons, verdict)

    def test_an_open_removal_pr_files_no_needs_harder_fixtures(self):
        for verdict in ("insufficient", "keep"):
            fires, work, reasons = self.run_ctx(verdict, 4, 0.05, removal=True)
            self.assertEqual((fires, work), ([], []), verdict)
            self.assertIn("owned by retirement (open removal PR)", reasons, verdict)

    def test_a_retire_verdict_still_names_the_verdict(self):
        for verdict in ("retire", "retire-pending"):
            fires, work, reasons = self.run_ctx(verdict, 3, 0.4, removal=True)
            self.assertEqual((fires, work), ([], []), verdict)
            self.assertIn(f"owned by retirement ({verdict})", reasons, verdict)

    def test_controls_without_the_pr_still_file_the_items(self):
        self.assertEqual(self.run_ctx("insufficient", 3, 0.4, removal=False)[1],
                         [("needs-fixtures", "issue")])
        self.assertEqual(self.run_ctx("insufficient", 4, 0.05, removal=False)[1],
                         [("needs-harder-fixtures", "issue")])

    def test_the_helper_reads_the_guidance_half(self):
        ctx = {"guidance_removal_prs": [SECTION], "removal_prs": [],
               "guidance": {SECTION: {"verdict": "keep"}}}
        self.assertEqual(plan_week.retirement_owner(ctx, SECTION, subject="guidance"),
                         "owned by retirement (open removal PR)")
        ctx["guidance_removal_prs"] = []
        self.assertIsNone(plan_week.retirement_owner(ctx, SECTION, subject="guidance"))
        ctx["guidance"][SECTION]["verdict"] = "retire-pending"
        self.assertEqual(plan_week.retirement_owner(ctx, SECTION, subject="guidance"),
                         "owned by retirement (retire-pending)")


if __name__ == "__main__":
    unittest.main()
