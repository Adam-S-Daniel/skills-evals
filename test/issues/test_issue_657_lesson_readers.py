#!/usr/bin/env python3
"""#657: session-miner lessons other than `new-skill` get a reader.

Pinned here:

  * scripts/lesson_evidence.py reads only the newest day's proposals of one
    kind, keeps `skill:<name>` subjects only, skips anything off the schema,
    and returns `{skill: evidence_count}` and nothing else;
  * `fixture-candidate` lessons rank scaffold_real_work.py `pick` candidates
    for that skill first, and `supply_plan` keeps only the public skills
    SUBJECT_BY_TOUCH names;
  * `skill-edit` lessons multiply a public skill's improve value in
    plan_week.py by at most 2, never touching eligibility or an unknown
    value, and a skill the planner does not rank (a private one) appears
    nowhere in the plan;
  * plan_week.py no longer plans `agent-check` work items: _agent-guidance's
    fleet worker reads those (its ADR 0027);
  * routine-eval-weekly.yml and routine-fixture-supply.yml read
    persistent/lessons with the read-only registry App token, as data.

Every proposal here is invented: example skill names, example.com.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import gates  # noqa: E402
import lesson_evidence  # noqa: E402
import plan_week  # noqa: E402
import scaffold_real_work as scaffold  # noqa: E402

NOW = datetime(2026, 11, 3, 7, 0, 0, tzinfo=timezone.utc)
PRIVATE_REPO = "Adam-S-Daniel/adam-agentskills-private"


def proposal(subject, kind, count=2, **changes):
    doc = {"schema_version": 1, "id": "0123456789ab", "subject": subject, "kind": kind,
           "evidence_count": count, "first_seen": "2026-10-01", "last_seen": "2026-10-02",
           "examples": ["2026-10-02 example-repo [correction] invented excerpt, example.com"],
           "repos": ["example-repo"]}
    doc.update(changes)
    return doc


class Proposals:
    """A throwaway lessons/proposals/ tree."""

    def __init__(self, test):
        self.root = Path(tempfile.mkdtemp(prefix="lessons-657-")) / "proposals"
        self.root.mkdir()
        test.addCleanup(shutil.rmtree, self.root.parent, ignore_errors=True)

    def write(self, day, doc, name=None):
        folder = self.root / day
        folder.mkdir(exist_ok=True)
        name = name or (doc["subject"].replace(":", "-") + "__" + doc["kind"] + ".json")
        path = folder / name
        path.write_text(json.dumps(doc) if isinstance(doc, dict) else doc, encoding="utf-8")
        return path


class LessonEvidenceTests(unittest.TestCase):
    def test_reads_the_newest_day_only_and_skill_subjects_only(self):
        tree = Proposals(self)
        tree.write("2026-10-30", proposal("skill:old-skill", "skill-edit", 7))
        tree.write("2026-11-02", proposal("skill:example-skill", "skill-edit", 3))
        tree.write("2026-11-02", proposal("guidance:example-section", "skill-edit", 4))
        tree.write("2026-11-02", proposal("memory", "skill-edit", 4))
        tree.write("2026-11-02", proposal("skill:other-skill", "fixture-candidate", 5))
        (tree.root / "2026-11-02" / "DIGEST.md").write_text("# invented\n", encoding="utf-8")
        (tree.root / "not-a-day").mkdir()
        self.assertEqual(lesson_evidence.skill_evidence(tree.root, "skill-edit"),
                         {"example-skill": 3})
        self.assertEqual(lesson_evidence.skill_evidence(tree.root, "fixture-candidate"),
                         {"other-skill": 5})

    def test_skips_anything_off_the_schema(self):
        tree = Proposals(self)
        day = "2026-11-02"
        tree.write(day, proposal("skill:a-ok", "skill-edit", 2))
        tree.write(day, proposal("skill:bool-count", "skill-edit", True))
        tree.write(day, proposal("skill:zero-count", "skill-edit", 0))
        tree.write(day, proposal("skill:v2", "skill-edit", schema_version=2))
        tree.write(day, proposal("skill:Bad_Name", "skill-edit"))
        tree.write(day, proposal("skill:wrong-kind", "new-skill"),
                   name="skill-wrong-kind__skill-edit.json")
        tree.write(day, "{", name="skill-broken__skill-edit.json")
        tree.write(day, "[]", name="skill-list__skill-edit.json")
        tree.write(day, json.dumps(proposal("skill:huge", "skill-edit"))
                   + " " * lesson_evidence.MAX_FILE, name="skill-huge__skill-edit.json")
        target = tree.write(day, proposal("skill:linked", "skill-edit", 9),
                            name="target.txt")
        os.symlink(target, tree.root / day / "skill-linked__skill-edit.json")
        self.assertEqual(lesson_evidence.skill_evidence(tree.root, "skill-edit"), {"a-ok": 2})

    def test_nothing_to_read_is_empty_and_an_unknown_kind_is_refused(self):
        self.assertEqual(lesson_evidence.skill_evidence(None, "skill-edit"), {})
        self.assertEqual(lesson_evidence.skill_evidence(Path("/nonexistent-657"),
                                                        "skill-edit"), {})
        for kind in ("new-skill", "agent-check", "memory-note", "guidance-edit"):
            with self.assertRaises(ValueError):
                lesson_evidence.skill_evidence(None, kind)


def candidate(key, **changes):
    row = {"key": key, "answer_leak": {"flag": False}, "closing_issues": [1],
           "files_truncated": False, "touches": [], "merged_at": "2026-09-01T00:00:00Z"}
    row.update(changes)
    return row


class FixtureCandidateTests(unittest.TestCase):
    def setUp(self):
        self.evals = Path(tempfile.mkdtemp(prefix="evals-657-"))
        self.addCleanup(shutil.rmtree, self.evals, ignore_errors=True)
        self.rows = [candidate("example-org__adr__1", touches=["adr"],
                               merged_at="2026-09-01T00:00:00Z"),
                     candidate("example-org__sh__2", touches=["shell"],
                               merged_at="2026-09-02T00:00:00Z"),
                     candidate("example-org__none__3", merged_at="2026-09-09T00:00:00Z")]

    def test_lesson_evidence_ranks_its_skill_first(self):
        without = scaffold.pick(self.rows, self.evals, set(), set(), 10)
        self.assertEqual(without, ["example-org__sh__2", "example-org__adr__1",
                                   "example-org__none__3"])
        steered = scaffold.pick(self.rows, self.evals, set(), set(), 10,
                                lessons={"writing-adrs": 2})
        self.assertEqual(steered, ["example-org__adr__1", "example-org__sh__2",
                                   "example-org__none__3"])
        # Evidence outranks usage, which outranks the fixture count.
        self.assertEqual(scaffold.pick(self.rows, self.evals, set(), set(), 1,
                                       usage={"review-bash-ci-reliability": 9},
                                       lessons={"writing-adrs": 1}),
                         ["example-org__adr__1"])

    def test_supply_plan_reads_only_public_subject_skills_and_logs_a_count(self):
        tree = Proposals(self)
        tree.write("2026-11-02", proposal("skill:writing-adrs", "fixture-candidate", 4))
        tree.write("2026-11-02", proposal("skill:example-private-skill",
                                          "fixture-candidate", 50))
        tmp = tree.root.parent
        (tmp / "candidates.json").write_text(json.dumps({"candidates": self.rows}),
                                             encoding="utf-8")
        (tmp / "branches.txt").write_text("", encoding="utf-8")
        (tmp / "fired.txt").write_text("", encoding="utf-8")
        state = {"cap": 1.0, "spent": 0.0, "pending": 0.0, "reservation": 0.035,
                 "runs": 0, "fires": 0, "recent": 0}
        seen = {}
        real_pick = scaffold.pick

        def spy(*args, **kwargs):
            seen.update(kwargs.get("lessons") or {})
            return real_pick(*args, **kwargs)

        with mock.patch.object(scaffold, "allowance_state", return_value=state), \
                mock.patch.object(scaffold, "pick", side_effect=spy):
            plan = scaffold.supply_plan(tmp / "candidates.json", tmp / "branches.txt",
                                        tmp / "fired.txt", tmp, 1, lessons=tree.root)
        self.assertEqual(seen, {"writing-adrs": 4})
        self.assertEqual([r["candidate"] for r in plan["include"]], ["example-org__adr__1"])
        self.assertTrue(plan["line"].endswith("; fixture-candidate lessons for 1 skill(s)"))
        self.assertNotIn("private", plan["line"])

    def test_cli_takes_lessons(self):
        tree = Proposals(self)
        tmp = tree.root.parent
        (tmp / "candidates.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
        for name in ("branches.txt", "fired.txt"):
            (tmp / name).write_text("", encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        state = {"cap": 1.0, "spent": 0.0, "pending": 0.0, "reservation": 0.035,
                 "runs": 0, "fires": 0, "recent": 0}
        with mock.patch.object(scaffold, "allowance_state", return_value=state), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scaffold.main(["pick", "--candidates", str(tmp / "candidates.json"),
                                  "--branches", str(tmp / "branches.txt"),
                                  "--fired", str(tmp / "fired.txt"),
                                  "--results-tree", str(tmp), "--lessons", str(tree.root)])
        self.assertEqual(code, 0)
        self.assertIn("count=0", out.getvalue())
        self.assertIn("fixture-candidate lessons for 0 skill(s)", err.getvalue())


def skill(headroom=0.3, fixtures=4):
    return {"fixtures": fixtures, "holdout": "aaa" if fixtures >= 4 else "",
            "registry_ok": True, "verdict": "keep", "pause": None,
            "evidence": {"headroom": headroom, "pass_rate": None, "with_trials": 6,
                         "targets": ["one:b"]}}


def ctx(**over):
    base = {"policy": gates.load_gate_policy()["skills"], "reservation": 0.035,
            "overrun": 0.005, "improve_charge": 0.01, "room": 1.0, "points_per_usd": None,
            "model_weights": {"heavy": 0.9, "light": 0.1}, "removal_prs": [],
            "cells": [], "skills": {}}
    base.update(over)
    return base


class SkillEditTests(unittest.TestCase):
    def test_the_boost_doubles_at_most(self):
        self.assertEqual(plan_week.lesson_boost(0), 1.0)
        self.assertAlmostEqual(plan_week.lesson_boost(1), 1 + 1 / plan_week.SKILL_EDIT_BOOST_CAP)
        self.assertEqual(plan_week.lesson_boost(plan_week.SKILL_EDIT_BOOST_CAP), 2.0)
        self.assertEqual(plan_week.lesson_boost(10 ** 6), 2.0)

    def test_skill_edit_evidence_reorders_the_improve_band(self):
        skills = {"alpha-skill": skill(headroom=0.5), "beta-skill": skill(headroom=0.3)}
        weights = {"alpha-skill": 2, "beta-skill": 2}
        plain = plan_week.build_plan(ctx(skills=skills, skill_weights=weights), NOW)
        self.assertEqual([r["name"] for r in plain["improve_ranking"]],
                         ["alpha-skill", "beta-skill"])
        boosted = plan_week.build_plan(ctx(skills=skills, skill_weights=weights,
                                           skill_edit_lessons={"beta-skill": 3}), NOW)
        rows = {r["name"]: r for r in boosted["improve_ranking"]}
        self.assertEqual([r["name"] for r in boosted["improve_ranking"]],
                         ["beta-skill", "alpha-skill"])
        self.assertEqual((rows["beta-skill"]["lesson_evidence"],
                          rows["alpha-skill"]["lesson_evidence"]), (3, 0))
        base = {r["name"]: r["value"] for r in plain["improve_ranking"]}
        self.assertAlmostEqual(rows["beta-skill"]["value"], 2 * base["beta-skill"])
        self.assertEqual(rows["alpha-skill"]["value"], base["alpha-skill"])
        improve = [f["skill"] for f in boosted["fires"] if f["mode"] == "improve"]
        self.assertEqual(improve, ["beta-skill", "alpha-skill"])

    def test_evidence_never_makes_a_skill_eligible_or_a_value_known(self):
        skills = {"no-room": skill(headroom=0.05), "unknown": skill(headroom=None)}
        plan = plan_week.build_plan(ctx(skills=skills, skill_edit_lessons={
            "no-room": 9, "unknown": 9}), NOW)
        rows = {r["name"]: r for r in plan["improve_ranking"]}
        self.assertFalse(rows["no-room"]["eligible"])
        self.assertIsNone(rows["unknown"]["value"])
        self.assertEqual([f for f in plan["fires"] if f["mode"] == "improve"], [])

    def test_a_skill_the_planner_does_not_rank_appears_nowhere(self):
        plan = plan_week.build_plan(ctx(skills={"alpha-skill": skill()}, skill_edit_lessons={
            "example-private-skill": 5}), NOW)
        text = json.dumps(plan)
        self.assertNotIn("example-private-skill", text)
        self.assertNotIn("example-private-skill", "\n".join(plan_week.summary_lines(plan)))

    def test_agent_check_lessons_are_not_planned_here(self):
        self.assertFalse(hasattr(plan_week, "lesson_items"))
        plan = plan_week.build_plan(ctx(skills={"alpha-skill": skill(fixtures=2)}), NOW)
        self.assertNotIn("agent-check", {w["kind"] for w in plan["work"]})


def steps(workflow, job):
    doc = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    return doc["jobs"][job]["steps"]


def named(all_steps, name):
    return next(s for s in all_steps if s.get("name") == name)


class WorkflowTests(unittest.TestCase):
    def test_weekly_plan_reads_skill_edit_lessons_as_data(self):
        plan = steps("routine-eval-weekly.yml", "plan")
        ids = [s.get("id") for s in plan]
        lookup = named(plan, "Look for the lessons branch")
        self.assertEqual(lookup["env"], {"PRIVATE_READ_TOKEN":
                                         "${{ steps.private-token.outputs.token }}"})
        self.assertIn("branches/persistent/lessons", lookup["run"])
        checkout = named(plan, "Check out the lessons (data only)")
        self.assertEqual(checkout["if"], "steps.lessons-branch.outputs.exists == 'true'")
        self.assertEqual(checkout["with"]["repository"], PRIVATE_REPO)
        self.assertEqual(checkout["with"]["ref"], "persistent/lessons")
        self.assertEqual(checkout["with"]["sparse-checkout"], "lessons/proposals")
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertEqual(checkout["with"]["token"], "${{ steps.private-token.outputs.token }}")
        self.assertLess(ids.index("private-token"), ids.index("lessons-branch"))
        run = named(plan, "Plan the week's fires by band within the weekly allowance")["run"]
        self.assertIn('--lessons "$GITHUB_WORKSPACE/private-lessons/lessons/proposals"', run)
        for step in plan:
            if "upload-artifact" in str(step.get("uses", "")):
                self.assertNotIn("lessons", str(step["with"]["path"]))

    def test_fixture_supply_no_longer_picks_scaffold_candidates(self):
        # The scaffold lane, the one place pick read fixture-candidate
        # lessons, is paused and its jobs removed (skills-evals#656), so no
        # job of the workflow reads the private lessons branch any more.
        doc = yaml.safe_load((WORKFLOWS / "routine-fixture-supply.yml")
                             .read_text(encoding="utf-8"))
        self.assertNotIn("plan", doc["jobs"])
        self.assertNotIn("dispatch", doc["jobs"])
        text = (WORKFLOWS / "routine-fixture-supply.yml").read_text(encoding="utf-8")
        self.assertNotIn("--lessons", text)

    def test_no_workflow_passes_lessons_to_a_reader_of_other_kinds(self):
        # draft_new_skill.py keeps new-skill; plan_week and pick read counts;
        # explorer_data.py publishes only public proposals' safe fields.
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            if "--lessons" in text:
                with self.subTest(workflow=path.name):
                    self.assertIn(path.name, {"explorer-data.yml",
                                              "routine-draft-skill.yml",
                                              "routine-eval-fire.yml",
                                              "routine-eval-weekly.yml",
                                              "routine-fixture-supply.yml"})


if __name__ == "__main__":
    unittest.main()
