#!/usr/bin/env python3
"""The guidance focus band of the weekly planner (scripts/plan_week.py, band
4; Adam's rule, 2026-11-02 18:42 UTC: remove a guidance section at 90%
confidence it does not improve results by 0.15 or more).

Undecided guidance cells no longer enter the missing or near bands: the two
eligible sections nearest a verdict get `focus` (at least 15% of the room),
every other section `guidance-rest` (only what every other band leaves).

Hermetic: cells are dicts, `now` is passed in, the plan command reads an
empty results tree and recorded evidence.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import explorer_data  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402

NOW = datetime(2026, 11, 2, 19, 0, 0, tzinfo=timezone.utc)
POLICY = gates.load_gate_policy()["skills"]
GUIDANCE_FIXTURE = "evals/guidance/anything-you-name-gets-its-link/handoff"


def conf(no_help=None, helps=None):
    """A gates confidence block (objective or judge)."""
    block = {}
    if no_help is not None:
        block["no_help_confidence"] = no_help
    if helps is not None:
        block["helps_confidence"] = helps
    return block


def gcell(section, name, cls="insufficient", model="heavy", objective=None, judge=None,
          carried=False, reason=None, counted=(1, 1), verdict="insufficient", runs=1,
          empty=0, **over):
    """A guidance in-situ cell as plan_week.eval_cells builds it."""
    base = {"skill": "", "section": section, "fixture": f"evals/guidance/{section}/{name}",
            "model": model, "class": cls, "verdict": verdict, "with_runs": runs,
            "without_runs": runs, "newest": None, "usd_per_fire": None,
            "empty_fires": empty, "objective": objective, "judge": judge,
            "judge_carried": carried, "reason": reason, "with_counted": counted[0],
            "without_counted": counted[1]}
    base.update(over)
    return base


def scell(name, cls, runs=0):
    """A skill cell."""
    return {"skill": name, "section": None, "fixture": f"evals/{name}", "model": "heavy",
            "class": cls, "verdict": None, "with_runs": runs, "without_runs": runs,
            "newest": None, "usd_per_fire": None, "empty_fires": 0}


def near(section, value, name="a", **over):
    """A cell whose retire progress is `value` at the default level: a
    non-judge-carried cell whose objective and judge are both at `value` x
    the default retire confidence."""
    level = value * plan_week.DEFAULT_RETIRE_CONFIDENCE
    return gcell(section, name, objective=conf(level), judge=conf(level), **over)


def missing(section, name):
    """A guidance cell with no run."""
    return gcell(section, name, cls="missing", counted=(0, 0), runs=0)


def ctx(**over):
    base = {"policy": POLICY, "reservation": 0.035, "overrun": 0.005,
            "improve_charge": 0.10, "room": 1.0, "points_per_usd": None,
            "model_weights": {"heavy": 0.9, "light": 0.1}, "removal_prs": [],
            "cells": [], "skills": {}, "lessons": []}
    base.update(over)
    return base


def focus_of(**over):
    return [f["section"] for f in plan_week.guidance_focus(ctx(**over))[0]]


class ScoreTests(unittest.TestCase):

    def score(self, cells, **over):
        focus = plan_week.guidance_focus(ctx(cells=cells, **over))[0]
        return focus[0]["score"] if focus else None

    def test_a_judge_carried_cell_reads_its_judge_mind_its_objective(self):
        # Judge alone when it has no objective block.
        self.assertAlmostEqual(self.score([gcell("s", "a", carried=True,
                                                 judge=conf(0.45))]), 0.45 / 0.90, 12)
        # The smaller of the two when it has one.
        self.assertAlmostEqual(self.score([gcell("s", "a", carried=True, judge=conf(0.72),
                                                 objective=conf(0.36))]), 0.36 / 0.90, 12)
        # No judge block: 0.
        self.assertEqual(self.score([gcell("s", "a", carried=True,
                                           objective=conf(0.8))]), 0.0)

    def test_a_cell_that_is_not_judge_carried_needs_a_judge_to_retire(self):
        # A tight objective with no judge block, whose reason says the judge
        # is still needed, cannot retire (gates._classify), so it scores 0.
        needed = plan_week.JUDGE_NEEDED_REASON + ": the judge figure needs ..."
        self.assertEqual(self.score([gcell("s", "a", objective=conf(0.89),
                                           reason=needed)]), 0.0)
        self.assertAlmostEqual(self.score([gcell("s", "a", objective=conf(0.81),
                                                 judge=conf(0.63))]), 0.63 / 0.90, 12)
        # An absent field in a present block counts as 0.
        self.assertEqual(self.score([gcell("s", "a", objective={}, judge=conf(0.63))]), 0.0)

    def test_a_with_ahead_judge_skip_is_decided_on_the_objective(self):
        # #557: every missing judge figure was a with-ahead skip, so
        # gates._classify decides on the objective and gives the plain
        # "not tight enough" reason; retire progress reads the objective.
        self.assertAlmostEqual(self.score([gcell(
            "s", "a", objective=conf(0.72),
            reason="the interval is not tight enough yet")]), 0.72 / 0.90, 12)

    def test_the_judge_needed_reason_is_gates_own_text(self):
        # The planner matches gates._classify's reason by its start, so the
        # literal must still be in harness/gates.py (read with ast, so a
        # comment or docstring does not count).
        import ast
        source = (Path(plan_week.__file__).resolve().parent.parent
                  / "harness" / "gates.py").read_text(encoding="utf-8")
        texts = []
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.JoinedStr):
                texts.append("".join(v.value for v in node.values
                                     if isinstance(v, ast.Constant)))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                texts.append(node.value)
        self.assertTrue(any(t.startswith(plan_week.JUDGE_NEEDED_REASON) for t in texts))

    def test_retire_is_the_weakest_cell_and_keep_the_strongest(self):
        cells = [near("s", 0.8, "a"), near("s", 0.3, "b")]
        self.assertAlmostEqual(self.score(cells), 0.3, 12)
        cells.append(gcell("s", "c", objective=conf(helps=0.68)))
        # The new cell has no judge: retire progress 0, keep 0.68 / 0.85.
        self.assertAlmostEqual(self.score(cells), 0.68 / 0.85, 12)
        cells.append(gcell("s", "d", objective=conf(helps=0.1), judge=conf(helps=0.765)))
        self.assertAlmostEqual(self.score(cells), 0.765 / 0.85, 12)

    def test_the_levels_come_from_the_guidance_policy(self):
        retire = [near("r", 0.95)]  # no-help 0.855 on both figures
        keep = [gcell("k", "a", objective=conf(helps=0.8))]
        # Defaults (0.90, 0.85): r 0.95, k 0.941..., so r leads.
        focus = plan_week.guidance_focus(ctx(cells=retire + keep))[0]
        self.assertEqual([f["section"] for f in focus], ["r", "k"])
        self.assertAlmostEqual(focus[0]["score"], 0.855 / 0.90, 12)
        self.assertAlmostEqual(focus[1]["score"], 0.8 / 0.85, 12)
        policy = {"retire_confidence": 0.99, "benefit_confidence": 0.80}
        focus = plan_week.guidance_focus(ctx(cells=retire + keep, guidance_policy=policy))[0]
        self.assertEqual([f["section"] for f in focus], ["k", "r"])
        self.assertAlmostEqual(focus[0]["score"], 1.0, 12)
        self.assertAlmostEqual(focus[1]["score"], 0.855 / 0.99, 12)
        # The plan document records the focus at full precision.
        plan = plan_week.build_plan(ctx(cells=retire + keep, guidance_policy=policy), NOW)
        self.assertEqual(plan["guidance_focus"], focus)

    def test_ties_go_to_fewer_cells_then_more_counted_runs_then_the_id(self):
        cells = [gcell("big", "a"), gcell("big", "b"), gcell("small", "a"),
                 gcell("busy", "a", counted=(4, 3)), gcell("idle-b", "a"),
                 gcell("idle-a", "a")]
        # Every score is 0: one-cell sections first; among them the one with
        # the most counted runs, then by id; the two-cell section last.
        focus = plan_week.guidance_focus(ctx(cells=cells))[0]
        self.assertEqual([f["section"] for f in focus], ["busy", "idle-a"])
        with mock.patch.object(plan_week, "GUIDANCE_FOCUS_SECTIONS", 5):
            self.assertEqual(focus_of(cells=cells), ["busy", "idle-a", "idle-b", "small", "big"])


class EligibilityTests(unittest.TestCase):

    def test_decided_verdicts_and_removal_prs_are_not_focused(self):
        for verdict in ("keep", "retire", "retire-pending", "retire-unconfirmed",
                        "shorten-or-merge", "ceiling", "cannot-discriminate"):
            with self.subTest(verdict=verdict):
                self.assertEqual(focus_of(cells=[near("s", 0.9, verdict=verdict)]), [])
        self.assertEqual(focus_of(cells=[near("s", 0.9, verdict=None)]), ["s"])
        self.assertEqual(focus_of(cells=[near("s", 0.9)]), ["s"])
        self.assertEqual(focus_of(cells=[near("s", 0.9), near("t", 0.1)],
                                  guidance_removal_prs=["s"]), ["t"])

    def test_a_section_with_no_undecided_cell_is_not_focused(self):
        self.assertEqual(focus_of(cells=[gcell("s", "a", cls="no-benefit")]), [])

    def test_the_errored_reason_blocks(self):
        reason = ("no-benefit on the numbers, but the cell has 1 agent-errored trial(s) "
                  "or a run skipped as anomalous, so it cannot retire")
        cells = [near("s", 0.9), gcell("s", "b", reason=reason)]
        self.assertEqual(focus_of(cells=cells), [])

    def test_ceiling_and_cannot_discriminate_block_only_at_three_counted_runs(self):
        for cls in ("ceiling", "cannot-discriminate"):
            for counted, blocked in (((3, 3), True), ((2, 3), False), ((3, 2), False),
                                     ((9, 4), True)):
                with self.subTest(cls=cls, counted=counted):
                    cells = [near("s", 0.5), gcell("s", "b", cls=cls, counted=counted)]
                    self.assertEqual(focus_of(cells=cells), [] if blocked else ["s"])

    def test_a_held_cell_produces_no_item_but_still_blocks(self):
        held = {"schedulable": False, "hold_reason": "no context"}
        # Its only undecided cell is held: no fire to plan, so not focused.
        self.assertEqual(focus_of(cells=[near("s", 0.9, **held),
                                         gcell("s", "b", cls="no-benefit")]), [])
        # A held blocking cell still blocks a section with a fireable cell.
        self.assertEqual(focus_of(cells=[near("s", 0.9), gcell("s", "b", cls="ceiling",
                                                               counted=(3, 3), **held)]), [])
        # A stakes `none` section plans nothing at all.
        self.assertEqual(focus_of(cells=[near("s", 0.9, stakes="none")]), [])

    def test_a_broken_missing_cell_produces_no_item(self):
        broken = {**missing("s", "a"), "empty_fires": plan_week.BROKEN_AFTER_FIRES}
        plan = plan_week.build_plan(ctx(cells=[broken, near("t", 0.1)]), NOW)
        self.assertEqual([f["section"] for f in plan["guidance_focus"]], ["t"])
        self.assertEqual([(w["kind"], w["section"]) for w in plan["work"]],
                         [("fixture-broken", "s")])
        # One fire short of broken, it still counts.
        self.assertEqual(focus_of(cells=[{**broken, "empty_fires": 1}]), ["s"])

    def test_nothing_eligible_leaves_the_focus_empty(self):
        cells = [near("s", 0.9, verdict="keep"), near("t", 0.9, verdict="shorten-or-merge"),
                 near("u", 0.9), gcell("u", "b", cls="ceiling", counted=(3, 3))]
        plan = plan_week.build_plan(ctx(cells=cells), NOW)
        self.assertEqual(plan["guidance_focus"], [])
        self.assertEqual({f["band"] for f in plan["fires"]}, {"guidance-rest"})
        # A decided verdict other than keep plans its undecided cells in the
        # rest; a kept one plans none until its re-check.
        self.assertEqual([f["fixture"] for f in plan["fires"]],
                         ["evals/guidance/t/a", "evals/guidance/u/a"])


class BandTests(unittest.TestCase):

    def test_focused_sections_go_to_focus_the_rest_to_guidance_rest(self):
        cells = [scell("m", "missing"), scell("n", "insufficient", runs=1),
                 near("a", 0.9), missing("a", "b"), near("b", 0.5), near("c", 0.1),
                 missing("c", "b")]
        plan = plan_week.build_plan(ctx(cells=cells), NOW)
        # a and c score 0 (each has a missing cell); a wins the tie by id.
        self.assertEqual([f["section"] for f in plan["guidance_focus"]], ["b", "a"])
        got = [(f["band"], f["fixture"]) for f in plan["fires"]]
        self.assertEqual(got, [("missing", "evals/m"), ("near", "evals/n"),
                               ("focus", "evals/guidance/b/a"), ("focus", "evals/guidance/a/b"),
                               ("focus", "evals/guidance/a/a"),
                               ("guidance-rest", "evals/guidance/c/b"),
                               ("guidance-rest", "evals/guidance/c/a")])
        self.assertTrue(all(f["section"] == "" for f in plan["fires"]))

    def test_focus_goes_binding_cell_first_then_the_cheaper_model(self):
        # Retire side: lowest retire progress first; within a cell, the
        # cheaper model (the one with the lower known cost per arm trial).
        cells = [{**near("s", 0.7, "a", model="heavy"), "usd_per_arm_trial": 2.0},
                 {**near("s", 0.7, "a", model="light"), "usd_per_arm_trial": 1.0},
                 near("s", 0.4, "b", model="heavy")]
        plan = plan_week.build_plan(ctx(cells=cells), NOW)
        self.assertEqual([(f["fixture"][-1], f["model"]) for f in plan["fires"]],
                         [("b", "heavy"), ("a", "light"), ("a", "heavy")])

    def test_a_keep_side_section_orders_by_keep_progress_descending(self):
        cells = [gcell("k", "a", objective=conf(helps=0.2)),
                 gcell("k", "b", objective=conf(helps=0.8)),
                 gcell("k", "c", objective=conf(0.85, helps=0.5), judge=conf(0.85))]
        plan = plan_week.build_plan(ctx(cells=cells), NOW)
        self.assertAlmostEqual(plan["guidance_focus"][0]["score"], 0.8 / 0.85, 12)
        self.assertEqual([f["fixture"][-1] for f in plan["fires"]], ["b", "c", "a"])

    def test_a_kept_section_is_still_only_rechecked(self):
        cells = [near("k", 0.9, verdict="keep", newest="20260801T000000Z")]
        plan = plan_week.build_plan(ctx(cells=cells), NOW)
        self.assertEqual([f["band"] for f in plan["fires"]], ["recheck"])


class AllocateTests(unittest.TestCase):

    def test_focus_gets_its_share_and_guidance_rest_only_leftovers(self):
        cells = [scell(f"m{i}", "missing") for i in range(20)] \
            + [scell(f"n{i}", "insufficient", runs=2) for i in range(20)] \
            + [near("f", 0.9, f"x{i}") for i in range(10)] \
            + [missing("r", f"x{i}") for i in range(10)]
        with mock.patch.object(plan_week, "GUIDANCE_FOCUS_SECTIONS", 1):
            plan = plan_week.build_plan(ctx(cells=cells, room=0.35), NOW)
        bands = [f["band"] for f in plan["fires"]]
        # 0.35: missing 30% holds 3 fires, near 20% 2, focus 15% one (0.0525),
        # and the rest (4 fires) goes to missing first: none to the rest.
        self.assertEqual((bands.count("missing"), bands.count("near"), bands.count("focus"),
                          bands.count("guidance-rest")), (7, 2, 1, 0))
        # Room for everything: the rest comes last, after every other band.
        with mock.patch.object(plan_week, "GUIDANCE_FOCUS_SECTIONS", 1):
            plan = plan_week.build_plan(ctx(cells=cells, room=10.0), NOW, max_fires=60)
        bands = [f["band"] for f in plan["fires"]]
        self.assertEqual(len(bands), 60)
        self.assertEqual(bands[-10:], ["guidance-rest"] * 10)
        self.assertEqual(bands.count("focus"), 10)

    def test_the_cap_starves_the_rest_before_the_focus(self):
        cells = [near("f", 0.9, f"x{i}") for i in range(5)] \
            + [missing("r", f"x{i}") for i in range(5)]
        with mock.patch.object(plan_week, "GUIDANCE_FOCUS_SECTIONS", 1):
            plan = plan_week.build_plan(ctx(cells=cells, room=10.0), NOW, max_fires=6)
        self.assertEqual([f["band"] for f in plan["fires"]], ["focus"] * 5 + ["guidance-rest"])

    def test_a_refresh_fire_is_picked_from_the_focus(self):
        # Refresh allocation takes missing and near first, so they are empty.
        cells = [missing("r", "a"), near("f", 0.9, "b"), missing("r", "b"),
                 near("g", 0.5, "c"), near("f", 0.9, "c")]
        with mock.patch.object(plan_week, "GUIDANCE_FOCUS_SECTIONS", 1):
            plan = plan_week.build_plan(ctx(cells=cells, room=-0.2, refresh=True), NOW)
        self.assertEqual([(f["band"], f["fixture"]) for f in plan["fires"]],
                         [("focus", "evals/guidance/f/b")])


class EvalCellsTests(unittest.TestCase):

    def test_guidance_cells_carry_the_focus_fields(self):
        run = {"timestamp": "20261020T100000Z-abc123"}
        objective, judge = conf(0.4, 0.1), conf(0.6, 0.2)
        gates_doc = {"roster_models": ["m"], "skills": {}, "guidance": {
            "anything-you-name-gets-its-link": {"verdict": "insufficient", "cells": [
                {"fixture": "handoff", "model": "m", "class": "insufficient",
                 "runs": {"with": [run, run], "without": [run]},
                 "with": {"runs": 1}, "without": {"runs": 1},
                 "objective": objective, "judge": judge, "judge_carried": True,
                 "reason": "the interval is not tight enough yet"}]}}}
        cells = plan_week.eval_cells(ROOT / "evals", gates_doc, [], NOW)
        mine = next(c for c in cells if c["fixture"] == GUIDANCE_FIXTURE)
        self.assertEqual({k: mine[k] for k in ("objective", "judge", "judge_carried", "reason",
                                               "with_counted", "without_counted", "with_runs",
                                               "verdict")},
                         {"objective": objective, "judge": judge, "judge_carried": True,
                          "reason": "the interval is not tight enough yet",
                          "with_counted": 1, "without_counted": 1, "with_runs": 2,
                          "verdict": "insufficient"})
        other = next(c for c in cells if c["fixture"].startswith("evals/guidance/")
                     and c["fixture"] != GUIDANCE_FIXTURE)
        self.assertEqual({k: other[k] for k in ("objective", "judge", "judge_carried", "reason",
                                                "with_counted", "without_counted")},
                         {"objective": None, "judge": None, "judge_carried": False,
                          "reason": None, "with_counted": 0, "without_counted": 0})
        skill = next(c for c in cells if not c["fixture"].startswith("evals/guidance/"))
        self.assertNotIn("with_counted", skill)


class GatherTests(unittest.TestCase):
    """The plan command passes the guidance policy and the open removal pull
    requests to the focus."""

    def run_plan(self, guidance_prs):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            evidence = base / "evidence.json"
            evidence.write_text(json.dumps({"fire_runs": [], "improve_branches": [],
                                            "registry_prs": [], "on_hold": [],
                                            "guidance_prs": guidance_prs}))
            plan_file = base / "plan.json"
            seen = []
            real = plan_week.guidance_focus

            def spy(context):
                seen.append((context.get("guidance_policy"),
                             context.get("guidance_removal_prs")))
                return real(context)

            out = io.StringIO()
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": "", "GITHUB_STEP_SUMMARY": ""}), \
                 mock.patch.object(plan_week, "guidance_focus", side_effect=spy), \
                 contextlib.redirect_stdout(out):
                code = plan_week.main(["plan", "--results-tree", str(base / "tree"),
                                       "--as-of", "2026-10-26T12:00:00+00:00",
                                       "--evidence", str(evidence), "--out", str(plan_file)])
            self.assertEqual(code, 0, out.getvalue())
            return json.loads(plan_file.read_text()), seen

    def test_the_policy_and_removal_prs_reach_the_focus(self):
        plan, seen = self.run_plan([])
        policy = gates.load_gate_policy(ROOT / "evals" / "gate-policy.yml")["guidance"]
        self.assertTrue(seen)
        self.assertEqual(seen[0], (policy, []))
        first = plan["guidance_focus"][0]["section"]
        plan, seen = self.run_plan([{"head": {"ref": f"retire-guidance/{first}"},
                                     "state": "open"}])
        self.assertEqual(seen[0][1], [first])
        self.assertNotIn(first, [f["section"] for f in plan["guidance_focus"]])
        self.assertEqual(len(plan["guidance_focus"]), plan_week.GUIDANCE_FOCUS_SECTIONS)


class ExplorerQueueTests(unittest.TestCase):

    def test_a_focused_section_gets_a_queue_place_before_the_rest(self):
        cells = [scell("m", "missing"), near("a", 0.9), near("b", 0.5), near("c", 0.1)]
        queue = explorer_data.test_queue(cells, {"heavy": 1.0}, NOW)
        self.assertEqual({k: (v["position"], v["band"]) for k, v in queue.items()},
                         {("skill", "m"): (1, "missing"), ("guidance", "a"): (2, "focus"),
                          ("guidance", "b"): (3, "focus"),
                          ("guidance", "c"): (4, "guidance-rest")})
        self.assertEqual(explorer_data.QUEUE_BANDS,
                         tuple(b for b in plan_week.BANDS if b not in ("improve", "bare")))

    def test_the_queue_uses_the_guidance_policy(self):
        cells = [near("r", 0.95), gcell("k", "a", objective=conf(helps=0.8)),
                 gcell("z", "a")]
        policy = {"retire_confidence": 0.99, "benefit_confidence": 0.80}
        default = explorer_data.test_queue(cells, {"heavy": 1.0}, NOW)
        tuned = explorer_data.test_queue(cells, {"heavy": 1.0}, NOW, policy)
        self.assertEqual((default[("guidance", "r")]["position"],
                          default[("guidance", "k")]["position"]), (1, 2))
        self.assertEqual((tuned[("guidance", "k")]["position"],
                          tuned[("guidance", "r")]["position"]), (1, 2))
        self.assertEqual(tuned[("guidance", "z")]["band"], "guidance-rest")


class DocsTests(unittest.TestCase):

    def test_the_weekly_plan_documents_the_focus(self):
        doc = (ROOT / "docs/how-it-works.md").read_text()
        for phrase in ("4. **Guidance focus**", "8. **Guidance rest**", "BLOCKING",
                       "one trial"):
            self.assertIn(phrase, doc)


if __name__ == "__main__":
    unittest.main()
