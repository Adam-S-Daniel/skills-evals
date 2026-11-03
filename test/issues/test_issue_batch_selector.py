#!/usr/bin/env python3
"""The two-week batch of the weekly planner (scripts/plan_week.py, THE
BATCH; Adam's steady-state goal, 2026-11-02 18:57 UTC: at 25% of the weekly
allowance, every two weeks pick a batch of skills and guidance sections
numbering about three times the historical weekly addition rate, bring them
all to a verdict, then start a new batch).

Hermetic: cells are dicts, `now` is passed in, the plan command reads an
empty results tree and recorded evidence.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import explorer_data  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402

START = datetime(2026, 11, 9, 17, 0, 0, tzinfo=timezone.utc)
NOW = START + timedelta(hours=1)
POLICY = {"start": START, "period": timedelta(days=14), "multiplier": 3.0,
          "rates": {"skill": 0.75, "guidance": 0.5}}
GATE_POLICY = gates.load_gate_policy()["skills"]


def stamp(moment):
    return moment.strftime(plan_week.STAMP)


def scell(name, cls="missing", verdict=None, newest=None, model="heavy", **over):
    """A skill cell as plan_week.eval_cells builds it."""
    base = {"skill": name, "section": None, "fixture": f"evals/{name}", "model": model,
            "class": cls, "verdict": verdict, "with_runs": 0, "without_runs": 0,
            "newest": newest, "usd_per_fire": None, "empty_fires": 0}
    base.update(over)
    return base


def gcell(section, cls="missing", verdict="insufficient", newest=None, **over):
    """A guidance in-situ cell."""
    base = {"skill": "", "section": section, "fixture": f"evals/guidance/{section}/a",
            "model": "heavy", "class": cls, "verdict": verdict, "with_runs": 0,
            "without_runs": 0, "newest": newest, "usd_per_fire": None, "empty_fires": 0,
            "objective": None, "judge": None, "judge_carried": False, "reason": None,
            "with_counted": 0, "without_counted": 0}
    base.update(over)
    return base


def ctx(cells, previous=None, policy=POLICY, **over):
    base = {"policy": GATE_POLICY, "reservation": 0.035, "overrun": 0.005,
            "improve_charge": 0.10, "room": 1.0, "points_per_usd": None,
            "model_weights": {"heavy": 0.9}, "removal_prs": [], "cells": cells,
            "skills": {}, "lessons": [], "batch_policy": policy,
            "previous_batch": previous}
    base.update(over)
    return base


def record(number, members, started=NOW, period=timedelta(days=14)):
    return {"schema_version": 1, "number": number, "started_at": plan_week._iso(started),
            "due_at": plan_week._iso(started + period), "sizes": {"skill": 2, "guidance": 2},
            "multiplier": 3.0, "rates": {"skill": 0.75, "guidance": 0.5},
            "members": [{"kind": k, "subject": s, "joined": j} for k, s, j in members],
            "previous": None}


def names(batch):
    return [(m["kind"], m["subject"]) for m in batch["record"]["members"]]


class PolicyTests(unittest.TestCase):

    def test_the_committed_policy_sizes_two_skills_and_two_sections(self):
        policy = plan_week.load_batch_policy(ROOT / "evals/batch-policy.yml")
        self.assertEqual(policy["start"], START)
        self.assertEqual(policy["period"], timedelta(days=14))
        # 3 x 0.75 = 2.25 -> 2; 3 x 0.5 = 1.5 -> 2 (half rounded up).
        self.assertEqual(plan_week.batch_sizes(policy), {"skill": 2, "guidance": 2})

    def test_a_size_is_at_least_one(self):
        policy = {**POLICY, "rates": {"skill": 0.0, "guidance": 0.1}}
        self.assertEqual(plan_week.batch_sizes(policy), {"skill": 1, "guidance": 1})

    def test_a_malformed_policy_stops_the_plan(self):
        good = yaml.safe_load((ROOT / "evals/batch-policy.yml").read_text())
        bad = [{**good, "extra": 1}, {k: v for k, v in good.items() if k != "rates"},
               {**good, "start": "soon"}, {**good, "period_days": 0},
               {**good, "period_days": True}, {**good, "multiplier": 0},
               {**good, "rates": {"skill": 1}}, {**good, "rates": {"skill": -1, "guidance": 1}},
               {**good, "multiplier": float("nan")}, ["start"]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "batch-policy.yml"
            for doc in bad:
                path.write_text(yaml.safe_dump(doc))
                with self.subTest(doc=doc), self.assertRaises(plan_week.PlanError):
                    plan_week.load_batch_policy(path)
            self.assertIsNone(plan_week.load_batch_policy(Path(tmp) / "absent.yml"))


class RecordTests(unittest.TestCase):

    def write(self, tree, doc):
        (tree / "batches").mkdir(exist_ok=True)
        (tree / plan_week.BATCH_RECORD).write_text(json.dumps(doc))

    def test_a_record_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            self.assertIsNone(plan_week.read_batch(tree))
            doc = record(2, [("skill", "a", 1), ("guidance", "g", 2)])
            self.write(tree, doc)
            self.assertEqual(plan_week.read_batch(tree), doc)

    def test_a_malformed_record_stops_the_plan(self):
        good = record(2, [("skill", "a", 1)])
        bad = [{**good, "schema_version": 2}, {**good, "number": 0},
               {**good, "number": True}, {**good, "due_at": "later"},
               {**good, "members": [{"kind": "other", "subject": "a", "joined": 1}]},
               {**good, "members": [{"kind": "skill", "subject": "../x", "joined": 1}]},
               {**good, "members": [{"kind": "skill", "subject": "a", "joined": 3}]},
               {**good, "members": "a"}]
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            for doc in bad:
                self.write(tree, doc)
                with self.subTest(doc=doc), self.assertRaises(plan_week.PlanError):
                    plan_week.read_batch(tree)
            (tree / plan_week.BATCH_RECORD).write_text("{")
            with self.assertRaises(plan_week.PlanError):
                plan_week.read_batch(tree)


class StatusTests(unittest.TestCase):

    def status(self, cells, **over):
        return {k: v["status"] for k, v in plan_week.batch_subjects(ctx(cells, **over)).items()}

    def test_each_status(self):
        blocking = plan_week.BLOCKING_REASON + " an errored trial"
        cells = [scell("open"), scell("kept", cls="keep", verdict="keep"),
                 scell("removing"), scell("blocked", cls="insufficient", reason=blocking),
                 scell("broken", empty_fires=plan_week.BROKEN_AFTER_FIRES),
                 scell("checked", stakes="none"),
                 gcell("ceiling", cls="ceiling", with_counted=3, without_counted=3),
                 gcell("retired", verdict="retire")]
        self.assertEqual(self.status(cells, removal_prs=["removing"]), {
            ("skill", "open"): "open", ("skill", "kept"): "decided",
            ("skill", "removing"): "decided", ("skill", "blocked"): "blocked",
            ("skill", "broken"): "stalled", ("skill", "checked"): "stalled",
            ("guidance", "ceiling"): "blocked", ("guidance", "retired"): "decided"})

    def test_private_and_held_subjects_are_never_listed(self):
        cells = [scell("secret"), scell("held", schedulable=False), scell("public")]
        self.assertEqual(self.status(cells, private_skills=frozenset({"secret"})),
                         {("skill", "public"): "open"})

    def test_a_guidance_removal_pr_decides_its_section(self):
        self.assertEqual(self.status([gcell("g")], guidance_removal_prs=["g"]),
                         {("guidance", "g"): "decided"})


class SelectionTests(unittest.TestCase):

    def test_no_batch_before_the_start_or_without_a_policy(self):
        cells = [scell("a")]
        self.assertIsNone(plan_week.batch_state(ctx(cells), START - timedelta(seconds=1)))
        self.assertIsNone(plan_week.batch_state(ctx(cells, policy=None), NOW))

    def test_the_first_batch_fills_each_kind_in_order(self):
        old = stamp(NOW - timedelta(days=30))
        recent = stamp(NOW - timedelta(days=1))
        cells = [scell("recent", cls="insufficient", newest=recent),
                 scell("never"), scell("old", cls="insufficient", newest=old),
                 scell("high", cls="insufficient", newest=recent, stakes="high"),
                 gcell("g-b"), gcell("g-a"), gcell("g-c", newest=old),
                 scell("done", cls="keep", verdict="keep")]
        batch = plan_week.batch_state(ctx(cells), NOW)
        self.assertTrue(batch["started"])
        # High stakes first, then never run, then the oldest newest run.
        self.assertEqual(names(batch), [("skill", "high"), ("skill", "never"),
                                        ("guidance", "g-a"), ("guidance", "g-b")])
        rec = batch["record"]
        self.assertEqual((rec["number"], rec["started_at"], rec["due_at"]),
                         (1, "2026-11-09T18:00:00Z", "2026-11-23T18:00:00Z"))
        self.assertEqual({m["joined"] for m in rec["members"]}, {1})
        self.assertIsNone(rec["previous"])
        self.assertEqual(rec["sizes"], {"skill": 2, "guidance": 2})

    def test_an_open_batch_stays_until_due(self):
        previous = record(1, [("skill", "a", 1), ("skill", "b", 1)], started=NOW)
        cells = [scell("a", cls="keep", verdict="keep"), scell("b"), scell("c")]
        later = NOW + timedelta(days=13)
        batch = plan_week.batch_state(ctx(cells, previous), later)
        self.assertFalse(batch["started"])
        self.assertIs(batch["record"], previous)
        self.assertEqual(batch["status"], [
            {"kind": "skill", "subject": "a", "status": "decided"},
            {"kind": "skill", "subject": "b", "status": "open"}])

    def test_a_finished_batch_is_replaced_at_once(self):
        previous = record(1, [("skill", "a", 1), ("guidance", "g", 1)], started=NOW)
        cells = [scell("a", cls="keep", verdict="keep"), gcell("g", verdict="retire"),
                 scell("b"), gcell("h")]
        later = NOW + timedelta(days=3)
        batch = plan_week.batch_state(ctx(cells, previous), later)
        self.assertTrue(batch["started"])
        self.assertEqual(names(batch), [("skill", "b"), ("guidance", "h")])
        rec = batch["record"]
        self.assertEqual(rec["number"], 2)
        self.assertEqual(rec["due_at"], plan_week._iso(later + timedelta(days=14)))
        self.assertEqual(rec["previous"], {"number": 1, "members": [
            {"kind": "skill", "subject": "a", "status": "decided"},
            {"kind": "guidance", "subject": "g", "status": "decided"}]})

    def test_a_due_batch_carries_its_open_members_first(self):
        previous = record(3, [("skill", "slow", 2), ("skill", "done", 3),
                              ("guidance", "g", 3)], started=NOW)
        cells = [scell("slow", cls="insufficient"), scell("done", cls="keep", verdict="keep"),
                 scell("new"), scell("newer"), gcell("g", cls="insufficient"), gcell("h")]
        due = NOW + timedelta(days=14)
        batch = plan_week.batch_state(ctx(cells, previous), due)
        self.assertTrue(batch["started"])
        rec = batch["record"]
        self.assertEqual(rec["number"], 4)
        # Carried first, keeping when they joined; then picks fill each kind.
        self.assertEqual([(m["kind"], m["subject"], m["joined"]) for m in rec["members"]], [
            ("skill", "slow", 2), ("guidance", "g", 3), ("skill", "new", 4),
            ("guidance", "h", 4)])

    def test_carried_members_can_fill_the_batch(self):
        previous = record(1, [("skill", "a", 1), ("skill", "b", 1)], started=NOW)
        cells = [scell("a"), scell("b"), scell("c")]
        batch = plan_week.batch_state(ctx(cells, previous), NOW + timedelta(days=14))
        self.assertEqual(names(batch), [("skill", "a"), ("skill", "b")])
        self.assertEqual(batch["record"]["number"], 2)

    def test_stalled_blocked_and_gone_members_are_not_carried(self):
        previous = record(1, [("skill", "broken", 1), ("skill", "gone", 1)], started=NOW)
        cells = [scell("broken", empty_fires=plan_week.BROKEN_AFTER_FIRES), scell("c")]
        batch = plan_week.batch_state(ctx(cells, previous), NOW + timedelta(hours=1))
        # Neither member is open, so the batch is finished and replaced.
        self.assertEqual(names(batch), [("skill", "c")])
        self.assertEqual(batch["record"]["previous"]["members"], [
            {"kind": "skill", "subject": "broken", "status": "stalled"},
            {"kind": "skill", "subject": "gone", "status": "gone"}])

    def test_nothing_to_start_keeps_the_old_record(self):
        previous = record(5, [("skill", "a", 5)], started=NOW)
        cells = [scell("a", cls="keep", verdict="keep")]
        batch = plan_week.batch_state(ctx(cells, previous), NOW + timedelta(days=20))
        self.assertFalse(batch["started"])
        self.assertIs(batch["record"], previous)

    def test_an_empty_first_batch_is_recorded_once(self):
        first = plan_week.batch_state(ctx([]), NOW)
        self.assertTrue(first["started"])
        self.assertEqual(first["record"]["members"], [])
        again = plan_week.batch_state(ctx([], first["record"]), NOW + timedelta(hours=1))
        self.assertFalse(again["started"])


class PlanTests(unittest.TestCase):
    """What a batch does to the bands."""

    def plan(self, cells, previous, **over):
        return plan_week.build_plan(ctx(cells, previous, **over), NOW)

    def test_only_members_get_missing_near_focus_and_rest_fires(self):
        previous = record(1, [("skill", "in", 1), ("guidance", "g-in", 1)], started=NOW)
        recheck = stamp(NOW - timedelta(weeks=9))
        cells = [scell("in"), scell("out"), scell("near-out", cls="insufficient"),
                 gcell("g-in"), gcell("g-out"), gcell("g-out2", cls="insufficient"),
                 scell("kept-out", cls="keep", verdict="keep", newest=recheck),
                 scell("removing")]
        plan = self.plan(cells, previous, removal_prs=["removing"])
        planned = {(f["band"], f["fixture"]) for f in plan["fires"]}
        self.assertEqual(planned, {
            ("missing", "evals/in"), ("focus", "evals/guidance/g-in/a"),
            # Re-checks and safety are not the batch's.
            ("recheck", "evals/kept-out"), ("safety", "evals/removing")})
        self.assertEqual([f["section"] for f in plan["guidance_focus"]], ["g-in"])
        self.assertEqual(plan["batch"]["outside"], 4)
        self.assertFalse(plan["batch"]["started"])

    def test_every_guidance_member_is_in_the_focus(self):
        members = [("guidance", f"g{i}", 1) for i in range(4)]
        cells = [gcell(f"g{i}") for i in range(5)]
        plan = self.plan(cells, record(1, members, started=NOW))
        self.assertEqual(sorted(f["section"] for f in plan["guidance_focus"]),
                         ["g0", "g1", "g2", "g3"])

    def test_no_policy_plans_as_before(self):
        cells = [scell("a"), scell("b"), gcell("g")]
        with_none = plan_week.build_plan(ctx(cells, policy=None), NOW)
        self.assertIsNone(with_none["batch"])
        self.assertEqual({f["fixture"] for f in with_none["fires"]},
                         {"evals/a", "evals/b", "evals/guidance/g/a"})

    def test_the_summary_names_the_batch(self):
        plan = self.plan([scell("a"), scell("b"), scell("c")], None)
        lines = "\n".join(plan_week.summary_lines(plan))
        self.assertIn("Batch 1 (started now), due 2026-11-23T18:00:00Z: a (open), b (open); "
                      "1 cell(s) outside it wait", lines)


class ExplorerTests(unittest.TestCase):

    def test_the_queue_follows_the_published_batch(self):
        cells = [scell("in"), scell("out"), gcell("g-in"), gcell("g-out")]
        batch = record(1, [("skill", "in", 1), ("guidance", "g-in", 1)], started=NOW)
        queued = explorer_data.test_queue(cells, {"heavy": 1.0}, NOW, None, batch)
        self.assertEqual({k for k, v in queued.items() if v["position"] is not None},
                         {("skill", "in"), ("guidance", "g-in")})
        unbatched = explorer_data.test_queue(cells, {"heavy": 1.0}, NOW)
        self.assertEqual(sum(1 for v in unbatched.values() if v["position"] is not None), 4)


class CommandTests(unittest.TestCase):

    def run_plan(self, base, extra):
        evidence = base / "evidence.json"
        evidence.write_text(json.dumps({"fire_runs": [], "improve_branches": [],
                                        "registry_prs": [], "on_hold": []}))
        output, plan_file = base / "output", base / "plan.json"
        output.write_text("")
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output),
                                          "GITHUB_STEP_SUMMARY": ""}), \
             mock.patch.object(plan_week, "_utcnow", return_value=NOW), \
             contextlib.redirect_stdout(out):
            code = plan_week.main(["plan", "--results-tree", str(base / "tree"),
                                   "--as-of", "2026-11-09T18:00:00+00:00",
                                   "--evidence", str(evidence), "--out", str(plan_file),
                                   *extra])
        self.assertEqual(code, 0, out.getvalue())
        return output.read_text().splitlines(), json.loads(plan_file.read_text())

    def test_a_started_batch_is_written_and_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            batch_out = base / "batch.json"
            lines, plan = self.run_plan(base, ["--batch-policy",
                                               str(ROOT / "evals/batch-policy.yml"),
                                               "--batch-out", str(batch_out)])
            self.assertIn("batch_started=true", lines)
            written = json.loads(batch_out.read_text())
            self.assertEqual(written, plan["batch"]["record"])
            self.assertEqual(written["number"], 1)
            self.assertEqual(len(written["members"]), 4)
            # The next plan reads it from the tree and keeps it.
            (base / "tree" / "batches").mkdir()
            (base / "tree" / plan_week.BATCH_RECORD).write_text(batch_out.read_text())
            batch_out.unlink()
            lines, plan = self.run_plan(base, ["--batch-policy",
                                               str(ROOT / "evals/batch-policy.yml"),
                                               "--batch-out", str(batch_out)])
            self.assertIn("batch_started=false", lines)
            self.assertFalse(batch_out.exists())
            self.assertEqual(plan["batch"]["record"], written)

    def test_without_the_flag_there_is_no_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            lines, plan = self.run_plan(base, [])
            self.assertIsNone(plan["batch"])
            self.assertIn("batch_started=false", lines)


class WorkflowTests(unittest.TestCase):

    def test_the_weekly_workflow_plans_within_the_batch_and_publishes_it(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-weekly.yml").read_text())
        jobs = doc["jobs"]
        steps = jobs["plan"]["steps"]
        plan_step = next(s for s in steps if s.get("id") == "plan")
        self.assertIn("--batch-policy evals/batch-policy.yml", plan_step["run"])
        self.assertIn('--batch-out "$RUNNER_TEMP/batch.json"', plan_step["run"])
        self.assertEqual(jobs["plan"]["outputs"]["batch_started"],
                         "${{ steps.plan.outputs.batch_started }}")
        upload = next(s for s in steps if s.get("name") == "Upload the new batch record")
        self.assertEqual(upload["if"], "steps.plan.outputs.batch_started == 'true'")
        self.assertEqual(upload["with"]["name"], "batch")
        publish = jobs["batch-publish"]
        self.assertEqual(publish["needs"], "plan")
        self.assertEqual(publish["permissions"], {"contents": "write"})
        self.assertEqual(publish["if"], jobs["plan"]["if"]
                         + " && needs.plan.outputs.batch_started == 'true'")
        run = publish["steps"][-1]["run"]
        self.assertIn("push origin HEAD:refs/heads/persistent/eval-results", run)
        self.assertIn("cp \"$source\" batches/current.json", run)
        self.assertNotIn("--force", run)
        self.assertNotIn("${{", run)
        self.assertEqual(plan_week.BATCH_RECORD, "batches/current.json")


if __name__ == "__main__":
    unittest.main()
