#!/usr/bin/env python3
"""PR 649's seventh adversarial round on the betting gate (2026-11-03).

Each class pins one finding of
/mnt/project-files/reports/pr649-adversarial-round7.md:

  * M1: the trigger lane's "owned by retirement" guard reads the gates
    document, so a skill whose fixtures are all scope-paused (which
    `skill_contexts` drops, and the gate keeps) is not trigger-eligible when
    its verdict is `retire`, nor while a `retire-skill/<skill>` PR is open;
  * M2: how-it-works lists exactly `work_item_issues.KINDS` as issue-filed;
  * m1: `gather` hands `paused_ceiling_items` to the plan (behavioral);
  * m3: a `paused-ceiling` item names only the paused fixtures.

Hermetic and deterministic: canned runs, temporary directories, no network,
no clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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
import work_item_issues  # noqa: E402
from test_issue_gate_round3 import pairs  # noqa: E402

REAL_MODELS = ["claude-sonnet-5-5", "claude-opus-5-5"]
NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)
FIXTURES = ("a", "b", "c", "d")


def build(paused, rule, without, with_):
    """A temporary `evals/` copy holding skill zz-demo (four fixtures, those
    in `paused` scope-paused by `rule`) and 25 canned pairs per cell."""
    root = Path(tempfile.mkdtemp(prefix="round7-"))
    shutil.copytree(ROOT / "evals", root / "evals")
    for f in FIXTURES:
        d = root / "evals" / "zz-demo" / f
        d.mkdir(parents=True)
        (d / "fixture.yaml").write_text(
            f"skill: zz-demo\nregistry: {plan_week.REGISTRY_URL}\nprompt: {f}\n"
            "context:\n  repo: Adam-S-Daniel/example\n  ref: abc\n  guidance_revision: abc\n")
    sa = root / "evals" / "scope-auto.yml"
    sa.write_text(sa.read_text() + "".join(
        f"  - path: evals/zz-demo/{f}\n    rule: \"{rule}\"\n" for f in paused))
    un = root / "evals" / "unscheduled.yml"
    un.write_text(un.read_text() + "".join(
        f"  - path: evals/zz-demo/{f}\n    reason: \"Auto scope ({rule}), "
        "2026-11-03: x\"\n" for f in paused))
    sch = root / "evals" / "scheduled.yml"
    sch.write_text(sch.read_text() + "".join(
        f"  - path: evals/zz-demo/{f}\n    readiness: \"x\"\n"
        for f in FIXTURES if f not in paused))
    for args in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    digests = {f: run_eval.fixture_digest(root / "evals" / "zz-demo" / f) for f in FIXTURES}
    runs = []
    for i, m in enumerate(REAL_MODELS):
        for j, f in enumerate(FIXTURES):
            runs += pairs(f, 25, without, with_, start=1000 * i + 100 * j, model=m,
                          skill="zz-demo")
    runs = [{**r, "fixture_digest": digests[r["fixture"]]} for r in runs]
    return root, {"runs": runs, "skills": ["zz-demo"], "skipped": {}, "bare_runs": [],
                  "guidance_runs": [], "sections": []}


class TriggerOwnedByRetirementTests(unittest.TestCase):
    """M1, end to end through `compute_gates.compute`."""

    def gate(self, paused):
        root, index = build(paused, "zero-use", 50, 50)
        self.addCleanup(shutil.rmtree, root)
        ev = root / "evals"
        with mock.patch.object(compute_gates, "build_index", return_value=index), \
                mock.patch.object(compute_gates, "tested_digest", return_value="t1"):
            doc = compute_gates.compute(root / "results", ev / "roster.yml",
                                        ev / "gate-policy.yml", ev, "20261104T000000Z")
            skills = plan_week.skill_contexts(ev, root / "results", "20261104T000000Z", {},
                                              doc, [], [], [], NOW)
        return doc, skills

    def trigger(self, doc, skills, trigger_set, removal=()):
        ctx = {"triggers": {"zz-demo": {"trigger_set": trigger_set, "hook_candidate": False,
                                        "pause": None}},
               "skill_weights": {"zz-demo": 0}, "skills": skills, "private_skills": [],
               "gate_verdicts": plan_week.gate_verdicts(doc),
               "removal_prs": set(removal), "improve_charge": 0.05}
        fires, work, _, status = plan_week.trigger_items(ctx)
        return fires, work, status["zz-demo"]

    def test_an_all_paused_retire_skill_is_not_trigger_eligible(self):
        doc, skills = self.gate(paused=FIXTURES)
        v = doc["skills"]["zz-demo"]
        self.assertEqual((v["verdict"], v.get("removal")), ("retire", "auto"))
        self.assertNotIn("zz-demo", skills, "skill_contexts drops it: the premise")
        for has_set in (True, False):
            fires, work, status = self.trigger(doc, skills, has_set)
            self.assertEqual((fires, work), ([], []), has_set)
            self.assertFalse(status["eligible"])
            self.assertEqual(status["reasons"], ["owned by retirement (retire)"])

    def test_the_unpaused_control_is_still_owned_by_retirement(self):
        doc, skills = self.gate(paused=())
        self.assertEqual(doc["skills"]["zz-demo"]["verdict"], "retire")
        fires, work, status = self.trigger(doc, skills, True)
        self.assertEqual((fires, work, status["eligible"]), ([], [], False))

    def test_an_open_removal_pr_owns_the_skill(self):
        fires, work, status = self.trigger(
            {"skills": {"zz-demo": {"verdict": "insufficient"}}}, {}, True,
            removal={"zz-demo"})
        self.assertEqual((fires, work, status["eligible"]), ([], [], False))
        self.assertEqual(status["reasons"], ["owned by retirement (open removal PR)"])

    def test_a_kept_skill_without_a_removal_pr_stays_eligible(self):
        fires, _, status = self.trigger(
            {"skills": {"zz-demo": {"verdict": "keep"}}}, {}, True)
        self.assertTrue(status["eligible"])
        self.assertEqual([(f["mode"], f["trigger_only"]) for f in fires], [("improve", True)])

    def test_gather_hands_the_gate_verdicts_to_the_plan(self):
        """`gather` must put `gate_verdicts(gates_doc)` on the context: a
        stubbed verdict `retire` makes an otherwise eligible skill ineligible."""
        info = {"trigger_set": True, "hook_candidate": False, "pause": None}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            (base / "evidence.json").write_text(json.dumps({
                "fire_runs": [], "improve_branches": [], "registry_prs": [],
                "on_hold": []}))
            argv = ["plan", "--results-tree", str(base / "tree"), "--as-of",
                    "2026-10-26T12:00:00+00:00", "--evidence", str(base / "evidence.json"),
                    "--out", str(base / "plan.json")]
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(base / "output"),
                                              "GITHUB_STEP_SUMMARY": str(base / "summary")}), \
                    mock.patch.object(plan_week, "trigger_contexts",
                                      return_value={"zz-demo": info}), \
                    mock.patch.object(plan_week, "skill_weights",
                                      return_value={"zz-demo": 0}), \
                    mock.patch.object(plan_week, "gate_verdicts",
                                      return_value={"zz-demo": "retire"}), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plan_week.main(argv), 0)
            plan = json.loads((base / "plan.json").read_text())
        self.assertFalse(plan["triggers"]["zz-demo"]["eligible"])
        self.assertEqual(plan["triggers"]["zz-demo"]["reasons"],
                         ["owned by retirement (retire)"])


class HowItWorksKindsTests(unittest.TestCase):
    def test_issue_filed_kinds_match_work_item_issues(self):
        text = " ".join((ROOT / "docs" / "how-it-works.md").read_text().split())
        m = re.search(r"files only ((?:`[a-z-]+`(?:, | and )?)+)\)", text)
        self.assertIsNotNone(m, "the Where work items go bullet names the filed kinds")
        listed = set(re.findall(r"`([a-z-]+)`", m.group(1)))
        self.assertEqual(listed, set(work_item_issues.KINDS))


class PausedCeilingWiringTests(unittest.TestCase):
    def test_gather_hands_paused_ceiling_items_to_the_plan(self):
        item = {"kind": "paused-ceiling", "change_type": "fixture", "skill": "demo",
                "route": plan_week.SUMMARY_ROUTE, "fixtures": ["a"]}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            (base / "evidence.json").write_text(json.dumps({
                "fire_runs": [], "improve_branches": [], "registry_prs": [],
                "on_hold": []}))
            argv = ["plan", "--results-tree", str(base / "tree"), "--as-of",
                    "2026-10-26T12:00:00+00:00", "--evidence", str(base / "evidence.json"),
                    "--out", str(base / "plan.json")]
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(base / "output"),
                                              "GITHUB_STEP_SUMMARY": str(base / "summary")}), \
                    mock.patch.object(plan_week, "paused_ceiling_items", return_value=[item]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plan_week.main(argv), 0)
            plan = json.loads((base / "plan.json").read_text())
        self.assertEqual([w for w in plan["work"] if w["kind"] == "paused-ceiling"], [item])


class PausedCeilingFixturesTests(unittest.TestCase):
    def test_only_the_paused_cells_fixtures_are_named(self):
        doc = {"skills": {"pub": {"verdict": "ceiling", "paused_ceiling": True, "cells": [
            {"class": "paused", "fixture": "p2"}, {"class": "ceiling", "fixture": "live"},
            {"class": "paused", "fixture": "p1"}, {"class": "paused", "fixture": "p1"}]}},
            "guidance": {}}
        self.assertEqual([i["fixtures"] for i in plan_week.paused_ceiling_items(doc)],
                         [["p1", "p2"]])


if __name__ == "__main__":
    unittest.main()
