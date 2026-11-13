#!/usr/bin/env python3
"""PR 649's fourth adversarial round on the betting gate (2026-11-03).

Each class pins one finding of
/mnt/project-files/reports/pr649-adversarial-round4.md:

  * M1: a scope pause never hides a decided `no-benefit` cell (it votes),
    and an all-parked subject is `ceiling` only when each paused cell shows
    the ceiling on its own runs; otherwise it is `insufficient`;
  * M2: `compute_gates.compute`, over a real `evals/` tree with a scope
    pause, keeps the paused fixture's cells (its `keep_paused=True` call),
    so a kept subject stays kept and nothing gets `removal: auto`;
  * M1 too: such a subject is a `paused-unmeasured` work item, since a
    paused fixture has no planner cell;
  * m1: `fixture-ceiling`, `cell-at-cap` and `paused-unmeasured` items are
    routed to the step summary, which is where they go (no issue is filed
    for them);
  * m2: a keep at or before the removal's stopping time wins over a harm
    the harm test decides later;
  * m4: a malformed `evals/scope-auto.yml` or `evals/unscheduled.yml` fails
    the weekly plan with a plain PlanError, on the guidance path as on the
    skill path.

Hermetic and deterministic: canned runs, temporary directories, no network,
no clock.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402
import retire_skill  # noqa: E402
import run_eval  # noqa: E402
import work_item_issues  # noqa: E402
from test_issue_70_retirement import POLICY  # noqa: E402
import test_issue_gate_round3 as round3  # noqa: E402
from test_issue_gate_round3 import MODELS, classify, expect, pairs  # noqa: E402


def verdict(runs, expected):
    return gates.retirement({"runs": runs}, MODELS, "demo", POLICY, expected)


def harmful(n):
    """`n` pairs a model of fixture a: with 50, without 95 (D = -0.45)."""
    out = []
    for i, model in enumerate(MODELS):
        out += pairs("a", n, 95, 50, start=1000 * i, model=model)
    return out


class PausedHarmTests(unittest.TestCase):
    """M1: the reviewer's repro_paused_harm.py."""

    def test_a_decided_harm_keeps_its_class_and_votes_through_a_pause(self):
        free = verdict(harmful(40), expect("a"))
        self.assertEqual((free["verdict"], free["removal"]), ("retire", "auto"))
        held = verdict(harmful(40), expect("a", paused="a"))
        self.assertEqual(held["verdict"], "retire", held["reason"])
        self.assertEqual([(c["class"], c["scope_paused"]) for c in held["cells"]],
                         [("no-benefit", "ceiling")] * 2)
        self.assertTrue(all(c["harm_decided_at"] for c in held["cells"]))
        # The same evidence as unpaused: the pause only stopped the firing.
        self.assertEqual(held["removal"], free["removal"])

    def test_an_early_pause_is_insufficient_not_ceiling(self):
        # The scope pass pauses at 4 runs, long before the harm can decide.
        v = verdict(harmful(2), expect("a", paused="a"))
        self.assertEqual(v["verdict"], "insufficient", v["reason"])
        self.assertEqual([(c["class"], c["class_before_pause"]) for c in v["cells"]],
                         [("paused", "insufficient")] * 2)
        self.assertNotIn("removal", v)

    def test_a_pooled_pause_does_not_hide_a_headroom_cells_no_benefit(self):
        # One model at 99/99, the other at 75/75: pooled without 0.87.
        runs = pairs("a", 40, 99, 99, model=MODELS[0]) \
            + pairs("a", 40, 75, 75, start=1000, model=MODELS[1])
        v = verdict(runs, expect("a", paused="a"))
        self.assertEqual((v["verdict"], v["removal"]), ("retire", "auto"), v["reason"])
        self.assertEqual([c["class"] for c in v["cells"]], ["paused", "no-benefit"])
        self.assertEqual(v["cells"][0]["class_before_pause"], "ceiling")

    def test_a_section_with_real_headroom_is_not_called_ceiling(self):
        # The real `watch-finished-is-not-ci-passed` shape: one cell at 4
        # pairs, 100/100, and one at 3 pairs whose without arm is 0.667.
        runs = pairs("a", 4, 100, 100, model=MODELS[0]) \
            + pairs("a", 3, lambda r: 100 if r % 3 else 0, 100, start=1000, model=MODELS[1])
        v = verdict(runs, expect("a", paused="a"))
        self.assertEqual(v["verdict"], "insufficient", v["reason"])
        self.assertEqual({c["class"] for c in v["cells"]}, {"paused"})
        for cell in v["cells"]:
            self.assertFalse(gates._shows_ceiling(cell), cell)

    def test_ceiling_from_a_pause_needs_the_cells_own_evidence(self):
        # 20 pairs at 96/96: each cell was `ceiling-unconfirmed` itself.
        top = verdict(pairs("a", 20, 96, 96) + pairs("a", 20, 96, 96, start=1000,
                                                     model=MODELS[1]),
                      expect("a", paused="a"))
        self.assertEqual(top["verdict"], "ceiling", top["reason"])
        self.assertEqual({c["class_before_pause"] for c in top["cells"]},
                         {"ceiling-unconfirmed"})
        # 19 pairs: still `insufficient` before the pause, but the no-harm
        # test has rejected (pair 18) and the without arm is 0.96.
        near = verdict(pairs("a", 19, 96, 96) + pairs("a", 19, 96, 96, start=1000,
                                                      model=MODELS[1]),
                       expect("a", paused="a"))
        self.assertEqual(near["verdict"], "ceiling", near["reason"])
        self.assertEqual({(c["class_before_pause"], c["noharm_at"]) for c in near["cells"]},
                         {("insufficient", 18)})
        # 12 pairs: the no-harm test has not rejected, so no ceiling.
        short = verdict(pairs("a", 12, 96, 96) + pairs("a", 12, 96, 96, start=1000,
                                                       model=MODELS[1]),
                        expect("a", paused="a"))
        self.assertEqual(short["verdict"], "insufficient", short["reason"])
        # The without arm under HIGH_STOP_MIN_WITHOUT is no ceiling, even
        # where the no-harm test rejected.
        low = verdict(pairs("a", 30, 88, 88) + pairs("a", 30, 88, 88, start=1000,
                                                     model=MODELS[1]),
                      expect("a", paused="a"))
        self.assertTrue(all(c["noharm_at"] for c in low["cells"]))
        self.assertEqual(low["verdict"], "insufficient", low["reason"])
        # Only a ceiling pause can be read as a ceiling.
        for rule in ("zero-use", "floor"):
            v = verdict(pairs("a", 20, 96, 96) + pairs("a", 20, 96, 96, start=1000,
                                                       model=MODELS[1]),
                        expect("a", paused="a", rule=rule))
            self.assertEqual(v["verdict"], "insufficient", rule)


class UnmeasuredItemTests(unittest.TestCase):
    """M1: an all-parked subject the pause leaves unmeasured is a
    `paused-unmeasured` work item. A paused fixture is off the schedule, so
    it has no planner cell and so no `fixture-ceiling` item to carry one."""

    def test_the_gate_marks_it_and_the_planner_lists_it(self):
        v = verdict(harmful(2), expect("a", paused="a"))
        self.assertIs(v["unmeasured"], True)
        top = verdict(pairs("a", 20, 96, 96) + pairs("a", 20, 96, 96, start=1000,
                                                     model=MODELS[1]),
                      expect("a", paused="a"))
        self.assertNotIn("unmeasured", top)
        doc = {"skills": {"demo": v, "secret": v, "ceil": top},
               "guidance": {"sec": v}}
        items = plan_week.unmeasured_items(doc, frozenset({"secret"}))
        self.assertEqual(items, [
            {"kind": "paused-unmeasured", "change_type": "fixture", "skill": "demo",
             "route": plan_week.SUMMARY_ROUTE, "fixtures": ["a"]},
            {"kind": "paused-unmeasured", "change_type": "fixture", "skill": "",
             "route": plan_week.SUMMARY_ROUTE, "fixtures": ["a"], "section": "sec"}])
        from test_issue_closed_loop_planner import NOW, ctx
        plan = plan_week.build_plan({**ctx(cells=[], room=1.0), "unmeasured": items}, NOW)
        self.assertEqual([w for w in plan["work"] if w["kind"] == "paused-unmeasured"],
                         items)
        self.assertIn("paused-unmeasured 2", "\n".join(plan_week.summary_lines(plan)))

    def test_a_guidance_section_carries_the_flag_into_the_planner(self):
        """Round 5's M1: `guidance_verdict` copied only `removal` from the
        in-situ verdict, so no section ever got a `paused-unmeasured` item.
        Every fixture scope-paused, no runs: the end-to-end path."""
        expected = {"fx": {"fixture_digest": "d", "tested_digest": "t",
                           "rest_digest": "r", "scope_paused": "ceiling"}}
        v = gates.guidance_verdict({"runs": []}, MODELS, "sec", POLICY, expected)
        self.assertEqual(v["in_situ_verdict"], "insufficient")
        self.assertIs(v["unmeasured"], True)
        self.assertEqual(plan_week.unmeasured_items({"skills": {}, "guidance": {"sec": v}}),
                         [{"kind": "paused-unmeasured", "change_type": "fixture",
                           "skill": "", "route": plan_week.SUMMARY_ROUTE,
                           "fixtures": ["fx"], "section": "sec"}])

    def test_gather_hands_the_items_to_the_plan(self):
        """Round 5's m2: `gather` must call `unmeasured_items`; replacing
        its call with `[]` drops every item."""
        import contextlib
        import io
        import json
        import os
        item = {"kind": "paused-unmeasured", "change_type": "fixture", "skill": "demo",
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
                 mock.patch.object(plan_week, "unmeasured_items", return_value=[item]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plan_week.main(argv), 0)
            plan = json.loads((base / "plan.json").read_text())
            self.assertEqual([w for w in plan["work"] if w["kind"] == "paused-unmeasured"],
                             [item])

    def test_a_crossed_harm_test_is_not_a_ceiling_once_paused(self):
        """Round 5's m1: 18 clean pairs (the no-harm test crosses), then 8
        harm pairs, one CLI version. Unpaused it is `insufficient` (harm
        crossed, undecided); a ceiling pause must not turn it `ceiling`."""
        rr = []
        for i, m in enumerate(MODELS):
            rr += pairs("a", 18, 100, 100, start=1000 * i, model=m, cli=lambda r: "2.1.0")
            rr += pairs("a", 8, 100, 0, start=1000 * i + 18, model=m, cli=lambda r: "2.1.0")
        unpaused = verdict(rr, expect("a"))
        paused = verdict(rr, expect("a", paused="a"))
        self.assertEqual(unpaused["verdict"], "insufficient")
        self.assertEqual(paused["verdict"], "insufficient")
        cell = paused["cells"][0]
        self.assertEqual(cell["class"], "paused")
        self.assertIsNotNone(cell["harm_at"])
        self.assertIsNotNone(cell["noharm_at"])
        self.assertFalse(gates._shows_ceiling(cell))

    def test_a_ceiling_class_before_the_pause_shows_the_ceiling_by_itself(self):
        """Round 5's m3: the `class_before_pause` branch is kept, and named
        here. No real cell was found that only it admits, so the pin is on
        the function's contract (a paused-for-ceiling cell whose class before
        the pause was a ceiling class, whatever else the cell records)."""
        base = {"class": "paused", "scope_paused": "ceiling"}
        for before in gates.CEILING_CLASSES:
            self.assertTrue(gates._shows_ceiling({**base, "class_before_pause": before}))
        self.assertFalse(gates._shows_ceiling({**base, "class_before_pause": "insufficient"}))
        self.assertFalse(gates._shows_ceiling({**base, "class_before_pause": "ceiling",
                                               "scope_paused": "floor"}))


class ComputeScopePauseTests(unittest.TestCase):
    """M2: `compute` over a temporary evals/ tree. Fixture a helps (without
    80, with 100), fixture b is flat (50/50), two roster models; the scope
    pass paused a at the ceiling, recorded as eval_scope writes it. Only
    the run index is canned (build_index reads a results tree), and the
    tested digest (no registry checkout here)."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="round4-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.evals = self.root / "evals"
        for name in ("a", "b"):
            fixture = self.evals / "demo" / name
            fixture.mkdir(parents=True)
            (fixture / "fixture.yaml").write_text(f"skill: demo\nprompt: {name}\n",
                                                  encoding="utf-8")
        # A fixture digest is read from what Git has staged.
        for args in (["init", "-q"], ["add", "-A"]):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        self.digests = {name: run_eval.fixture_digest(self.evals / "demo" / name)
                        for name in ("a", "b")}
        self.assertTrue(all(self.digests.values()))
        (self.evals / "scope-auto.yml").write_text(
            "rows:\n  - path: evals/demo/a\n    rule: \"ceiling\"\n", encoding="utf-8")
        (self.evals / "unscheduled.yml").write_text(
            "fixtures:\n  - path: evals/demo/a\n    reason: \"Auto scope (ceiling), "
            "2026-11-03: the without arm passed 0.88 of its checks.\"\n", encoding="utf-8")
        self.roster = self.root / "roster.yml"
        self.roster.write_text(yaml.safe_dump({"arms": [{"id": m} for m in MODELS],
                                               "judge": {"id": "model-j"}}),
                               encoding="utf-8")

    def compute(self, a_pairs):
        runs = [{**r, "fixture_digest": self.digests[r["fixture"]]}
                for r in round3.ScopePauseTests.runs(a_pairs)]
        index = {"runs": runs, "skills": ["demo"], "skipped": [], "bare_runs": [],
                 "guidance_runs": [], "sections": []}
        with mock.patch.object(compute_gates, "build_index", return_value=index), \
                mock.patch.object(compute_gates, "tested_digest", return_value="t1"):
            return compute_gates.compute(self.root / "results", self.roster,
                                         ROOT / "evals" / "gate-policy.yml", self.evals,
                                         "20261103T000000Z")["skills"]["demo"]

    def test_a_kept_subject_stays_kept_through_a_pause(self):
        got = self.compute(40)
        self.assertEqual(got["verdict"], "keep", got["reason"])
        a = [c for c in got["cells"] if c["fixture"] == "a"]
        self.assertEqual([(c["class"], c["scope_paused"]) for c in a],
                         [("benefit", "ceiling")] * 2)

    def test_a_pause_before_the_keep_parks_its_cells_beside_an_auto_removal(self):
        got = self.compute(3)
        self.assertEqual((got["verdict"], got.get("removal")), ("retire", "auto"),
                         got["reason"])
        self.assertIn("parked cell", got["removal_reason"])
        self.assertEqual({c["class"] for c in got["cells"] if c["fixture"] == "a"},
                         {"paused"})


class WorkItemRouteTests(unittest.TestCase):
    """m1: the two items no workflow files an issue for say so."""

    def test_summary_routed_kinds_are_not_issue_kinds(self):
        from test_issue_closed_loop_planner import NOW, cell as pcell, ctx
        cells = [pcell("evals/a", "heavy", "paused", runs=3),
                 {**pcell("evals/b", "heavy", "insufficient", runs=40), "at_cap": True,
                  "reason": "why"}]
        work = plan_week.build_plan(ctx(cells=cells, room=1.0), NOW)["work"]
        got = {w["kind"]: w["route"] for w in work
               if w["kind"] in ("fixture-ceiling", "cell-at-cap")}
        self.assertEqual(got, {"fixture-ceiling": plan_week.SUMMARY_ROUTE,
                               "cell-at-cap": plan_week.SUMMARY_ROUTE})
        self.assertNotEqual(plan_week.SUMMARY_ROUTE, "issue")
        for kind in (*got, "paused-unmeasured"):
            self.assertNotIn(kind, work_item_issues.KINDS)
        # Every issue-routed kind the planner emits here is one the issue
        # script files.
        for item in work:
            if item["route"] == "issue":
                self.assertIn(item["kind"], work_item_issues.KINDS, item)


class KeepOverHarmTests(unittest.TestCase):
    """m2: the keep is checked first. Four pairs of a large gain (with 100,
    without 0) keep at pair 4; then the subject harms (with 50, without
    100), the remove test decides at pair 20 and the harm test at 26. The
    keep came first, so it holds: its own crossing bounds its error."""

    def test_a_keep_wins_over_a_harm_decided_later(self):
        got = classify(40, lambda r: 100 if r < 4 else 50, lambda r: 0 if r < 4 else 100)
        self.assertEqual((got["objective"]["keep_at"], got["remove_decided_at"],
                          got["harm_decided_at"]), (4, 20, 26))
        self.assertEqual(got["class"], "benefit", got["reason"])


class MalformedScopeFileTests(unittest.TestCase):
    """m4: the planner fails with a plain PlanError on a malformed scope or
    unscheduled file, on both of its paths."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="round4-plan-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.evals = self.root / "evals"
        shutil.copytree(ROOT / "evals" / "guidance", self.evals / "guidance")
        fixture = self.evals / "demo" / "a"
        fixture.mkdir(parents=True)
        (fixture / "fixture.yaml").write_text("skill: demo\n", encoding="utf-8")
        self.index = {"runs": [], "guidance_runs": [], "skills": [], "sections": [],
                      "skipped": [], "bare_runs": []}
        self.doc = {"roster_models": MODELS, "skills": {}, "guidance": {}}

    def test_the_guidance_path(self):
        (self.evals / "scope-auto.yml").write_text("rows: [1, 2]\n", encoding="utf-8")
        with mock.patch.object(compute_gates, "build_index", return_value=self.index), \
                self.assertRaises(plan_week.PlanError) as caught:
            plan_week.guidance_contexts(self.evals, self.root, "20261103T000000Z",
                                        self.doc, self.root)
        self.assertEqual(str(caught.exception), plan_week.SCHEDULE_FILES_MALFORMED)

    def test_the_skill_path(self):
        (self.evals / "unscheduled.yml").write_text("fixtures: [1]\n", encoding="utf-8")
        with mock.patch.object(compute_gates, "build_index", return_value=self.index), \
                self.assertRaises(plan_week.PlanError) as caught:
            plan_week.skill_contexts(self.evals, self.root, "20261103T000000Z", {},
                                     self.doc, [], [], [], None)
        self.assertEqual(str(caught.exception), plan_week.SCHEDULE_FILES_MALFORMED)


if __name__ == "__main__":
    unittest.main()
