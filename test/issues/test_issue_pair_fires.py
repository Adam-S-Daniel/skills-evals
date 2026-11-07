#!/usr/bin/env python3
"""Pair fires: one eval routine fire runs a fixture on both roster models.

A routine session's own overhead (about $0.67 a fire) is counted nowhere,
and firing once per (fixture, model) paid it twice per fixture. Now:

  * scripts/plan_week.py makes two planned eval cells of one fixture with
    the same arms (both, bare or in-situ) on two roster models ONE leg whose
    model is "m1,m2", in roster order (`pair_fires`, PAIR FIRES); a lone
    cell, an improve leg and a hand-built ctx without the roster stay as
    they were, and `validate-fire` checks each model of a pair;
  * routine-eval-fire.yml takes `model: m1,m2` (two distinct roster arms,
    each also in the payload contract's ^claude-[a-z0-9][a-z0-9.-]{0,62}$),
    sends `models: [m1, m2]`, never beside `model`, and titles the run
    `... <fixture> m1,m2`;
  * every title reader counts that title for BOTH cells
    (`improve_outcomes.title_models`): a pending pair fire holds both
    cells, its two runs are judged each on its own model, a bare pair fire
    covers both bare cells, the explorer counts it per model, and the
    allowance guard and wait-slot count it as one fire;
  * a pair run's results, two run_eval invocations under one run id,
    ingest with each summary's model intact; the guard charges each
    invocation, and the planner's cost per observation splits the run's
    points per model.

Hermetic: recorded API rows, injected `now`, temporary trees and
repositories (example.com only). No network, clock or sleep. Workflows are
parsed with PyYAML.
"""

from __future__ import annotations

from datetime import timedelta
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import allowance_guard as guard  # noqa: E402
import compute_gates  # noqa: E402
import explorer_data  # noqa: E402
import improve_outcomes as io_mod  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import plan_week  # noqa: E402
import routine_deadlines  # noqa: E402
import run_eval  # noqa: E402

import test_issue_routine_eval_fire as fire_base  # noqa: E402
from test_issue_555_fires_without_results import (  # noqa: E402
    EMPTY_INDEX, World, counts as fire_counts_of, record as index_record)
from test_issue_559_empty_fires import (  # noqa: E402
    NOW, ROUTINE_GIT, SKILL_FIXTURE, ctx as base_ctx, planned, skill_ctx, stamp)
from test_issue_closed_loop_planner import render_title  # noqa: E402
from test_issue_routine_eval_ingest import GitCase, REPORT, RUN_ID, STAMP, summary  # noqa: E402

#: The two roster arms, in evals/roster.yml's order.
ROSTER = [arm["id"] for arm in yaml.safe_load(
    (ROOT / "evals" / "roster.yml").read_text(encoding="utf-8"))["arms"]]
A, B = ROSTER[:2]
PAIR = f"{A},{B}"
GUIDANCE_FIXTURE = "evals/guidance/anything-you-name-gets-its-link/handoff"
FIXED_REFUSAL = "input 'model' is not an arm of the committed evals/roster.yml"


def fire(run_id, fixture, started, model, *, bare=False, conclusion="success",
         status="completed"):
    """One routine-eval-fire.yml run row, as the runs API records it."""
    at = started.strftime("%Y-%m-%dT%H:%M:%SZ")
    arms = " bare" if bare else ""
    return {"id": run_id, "display_title": f"Fire eval routine: eval{arms} {fixture} {model}",
            "status": status, "conclusion": conclusion, "run_started_at": at,
            "created_at": at, "updated_at": at}


class RosterTests(unittest.TestCase):

    def test_the_roster_has_two_arms_in_the_pair_contracts_pattern(self):
        # The pair contract holds exactly two ids; the planner pairs the
        # first two of the roster's order.
        self.assertGreaterEqual(len(ROSTER), 2)
        for arm in ROSTER:
            with self.subTest(arm=arm):
                self.assertRegex(arm, plan_week.PAIR_MODEL_RE.pattern)


class TitleTests(unittest.TestCase):

    def test_a_pair_title_parses_and_names_both_models_in_order(self):
        title = io_mod.parse_title(f"Fire eval routine: eval {SKILL_FIXTURE} {PAIR}")
        self.assertEqual(title, {"mode": "eval", "target": SKILL_FIXTURE, "model": PAIR,
                                 "bare": False, "trigger": False, "trim": False})
        self.assertEqual(io_mod.title_models(title), (A, B))
        bare = io_mod.parse_title(f"Fire eval routine: eval bare {SKILL_FIXTURE} {B},{A}")
        self.assertTrue(bare["bare"])
        self.assertEqual(io_mod.title_models(bare), (B, A))

    def test_title_models_of_one_model_or_none(self):
        self.assertEqual(io_mod.title_models(
            io_mod.parse_title(f"Fire eval routine: eval {SKILL_FIXTURE} {A}")), (A,))
        self.assertEqual(io_mod.title_models(
            io_mod.parse_title("Fire eval routine: improve writing-adrs ")), ())
        self.assertEqual(io_mod.title_models(None), ())

    def test_a_malformed_pair_title_is_no_title(self):
        for bad in (f"Fire eval routine: eval {SKILL_FIXTURE} {A},{A}",
                    f"Fire eval routine: eval {SKILL_FIXTURE} {A},{B},{A}",
                    f"Fire eval routine: eval {SKILL_FIXTURE} {A},",
                    f"Fire eval routine: eval {SKILL_FIXTURE} ,{A}",
                    f"Fire eval routine: eval {SKILL_FIXTURE} {A}, {B}",
                    # A pair is an eval fire's only.
                    f"Fire eval routine: improve writing-adrs {PAIR}",
                    f"Fire eval routine: scaffold a__b__1 {PAIR}"):
            with self.subTest(bad=bad):
                self.assertIsNone(io_mod.parse_title(bad))

    def test_the_fire_workflow_renders_the_pair_title_the_parser_reads(self):
        template = fire_base.load(fire_base.WORKFLOW)["run-name"]
        for arms, bare in (("both", False), ("bare", True), ("in-situ", False)):
            with self.subTest(arms=arms):
                title = io_mod.parse_title(render_title(
                    template, mode="eval", arms=arms, fixture=SKILL_FIXTURE, model=PAIR))
                self.assertEqual((title["target"], title["bare"]), (SKILL_FIXTURE, bare))
                self.assertEqual(io_mod.title_models(title), (A, B))

    def test_a_pair_fire_is_one_eval_fire_to_the_guard_never_an_improve_fire(self):
        runs = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=5), PAIR)]
        self.assertEqual(io_mod.charged_fires(runs), [])
        self.assertEqual(guard.improve_counts(runs, NOW), (0, 0))
        self.assertEqual(len(guard.eval_fire_starts(runs, NOW)), 1)
        self.assertEqual(plan_week._fire_pair(runs, NOW), (1, 1))

    def test_wait_slot_counts_a_pair_fire_once(self):
        started = NOW - timedelta(minutes=5)
        self.assertEqual(plan_week.in_flight([fire(1, SKILL_FIXTURE, started, PAIR)], NOW), 1)
        self.assertEqual(plan_week.in_flight(
            [fire(1, SKILL_FIXTURE, started, PAIR, conclusion=None, status="in_progress")],
            NOW), 1)

    def test_a_pair_fire_is_in_flight_for_two_flights(self):
        # Its two run_eval commands run one after the other.
        def count(model, minutes):
            return plan_week.in_flight(
                [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=minutes), model)], NOW)
        self.assertEqual(plan_week.EVAL_FLIGHT, timedelta(minutes=10))
        self.assertEqual((count(PAIR, 19), count(PAIR, 20)), (1, 0))
        self.assertEqual((count(A, 9), count(A, 10)), (1, 0))

    def test_the_guard_holds_a_pair_fire_in_full_until_its_deadline(self):
        # A pair fire with no results may still be running its second model
        # an hour in: it is held at the full reservation, not the overrun.
        self.assertEqual(guard.PENDING_FULL_HOLD, routine_deadlines.deadline("eval", 2))
        runs = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=60), PAIR)]
        self.assertEqual(plan_week._fire_pair(runs, NOW), (1, 1))


class CellReaderTests(unittest.TestCase):
    """The planner's per-cell readers expand a pair title to both cells."""

    def doc(self, landed=None):
        """Both models' cells of SKILL_FIXTURE, known, with `landed`'s runs."""
        rows = []
        for model in (A, B):
            times = sorted((landed or {}).get(model, []))
            rows.append({"fixture": "bootstrap", "model": model, "class": "missing",
                         "runs": {"with": [], "without": []},
                         "newest_on_model": stamp(times[-1]) if times else None,
                         "run_stamps_on_model": [stamp(t) for t in times]})
        return {"roster_models": [A, B], "skills": {"writing-adrs": {"cells": rows}},
                "guidance": {}, "bare_runs": []}

    def cells(self, fires, doc=None):
        cells = plan_week.eval_cells(ROOT / "evals", doc or self.doc(), fires, NOW, ROUTINE_GIT)
        return {c["model"]: c for c in cells if c["fixture"] == SKILL_FIXTURE}

    def test_a_pending_pair_fire_holds_both_cells(self):
        got = self.cells([fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=10), PAIR)])
        self.assertEqual({m: c["pending"] for m, c in got.items()}, {A: True, B: True})
        # Neither cell is planned again while the pair fire may still land.
        self.assertEqual(planned(list(got.values())), ({}, []))

    def test_a_lone_fire_holds_only_its_own_cell(self):
        got = self.cells([fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=10), A)])
        self.assertEqual({m: c["pending"] for m, c in got.items()}, {A: True, B: False})

    def test_a_pair_fire_holds_its_cells_for_both_models_stops(self):
        started = NOW - timedelta(minutes=60)
        # Another cell delivered since, so the routine is up: only a fire's
        # own window keeps it pending.
        doc = self.doc()
        landed = stamp(started + timedelta(minutes=5))
        doc["skills"]["disarm-inherited-reach"] = {"cells": [
            {"fixture": None, "model": A, "class": "missing",
             "runs": {"with": [], "without": []},
             "newest_on_model": landed, "run_stamps_on_model": [landed]}]}
        pair = self.cells([fire(1, SKILL_FIXTURE, started, PAIR)], doc)
        self.assertEqual({m: c["pending"] for m, c in pair.items()}, {A: True, B: True})
        lone = self.cells([fire(1, SKILL_FIXTURE, started, A)], doc)
        self.assertEqual({m: c["pending"] for m, c in lone.items()}, {A: False, B: False})

    def test_each_cell_of_a_pair_fire_is_judged_on_its_own_models_runs(self):
        started = NOW - timedelta(hours=3)
        fires = [fire(1, SKILL_FIXTURE, started, PAIR)]
        got = self.cells(fires, self.doc({A: [started + timedelta(minutes=8)]}))
        # A's run landed: delivered. B's never did: one empty fire.
        self.assertEqual({m: (c["empty_fires"], c["pending"], c["last_fire"])
                          for m, c in got.items()},
                         {A: (0, False, started), B: (1, False, started)})

    def test_a_bare_pair_fire_covers_both_bare_cells(self):
        def missing(fires):
            return {(e["fixture"], e["model"]) for e in plan_week.bare_cells(
                ROOT / "evals", self.doc(), fires) if e["fixture"] == SKILL_FIXTURE}
        self.assertEqual(missing([]), {(SKILL_FIXTURE, A), (SKILL_FIXTURE, B)})
        self.assertEqual(missing([fire(1, SKILL_FIXTURE, NOW, B, bare=True)]),
                         {(SKILL_FIXTURE, A)})
        self.assertEqual(missing([fire(1, SKILL_FIXTURE, NOW, PAIR, bare=True)]), set())
        # A bare pair fire is never a paired eval fire: no cell is pending.
        got = self.cells([fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=10), PAIR,
                               bare=True)])
        self.assertEqual({c["pending"] for c in got.values()}, {False})


class ExplorerFireCountTests(unittest.TestCase):

    def setUp(self):
        self.w = World(self)

    def test_a_pair_fire_counts_once_per_model(self):
        fired = 10
        delivered = index_record("pub", "fx", NOW_555(fired - 0.2),
                                 f"routine-results/R1/pub/{stamp(NOW_555(fired - 0.2))}",
                                 model="model-a")
        index = {**EMPTY_INDEX, "runs": [delivered]}
        pair = {"id": 1, "display_title": "Fire eval routine: eval evals/pub/fx model-a,model-b",
                "run_started_at": NOW_555(fired).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "conclusion": "success", "status": "completed"}
        out = fire_counts_of(self.w, [pair], index)
        # model-a's cell delivered; model-b's has no results.
        self.assertEqual((out["without_results"], out["rejected"]), (1, 0))
        self.assertEqual(fire_counts_of(self.w, [pair])["without_results"], 2)


def NOW_555(hours_ago: float):
    """test_issue_555's clock: `hours_ago` before its NOW."""
    from test_issue_555_fires_without_results import at
    return at(hours_ago)


class PlannerPairTests(unittest.TestCase):
    """build_plan's PAIR FIRES, on the real evals/ with no runs (every cell
    missing) and room for every cell."""

    def setUp(self):
        real = plan_week.schedule.scheduled_fixtures

        def scheduled(path, committed):
            listed = real(path, committed)
            return listed + [f for f in (SKILL_FIXTURE, GUIDANCE_FIXTURE) if f not in listed]

        patcher = mock.patch.object(plan_week.schedule, "scheduled_fixtures", scheduled)
        patcher.start()
        self.addCleanup(patcher.stop)

    def plan(self, fires=(), *, roster=(A, B), bare=False):
        doc = {"roster_models": [A, B], "skills": {}, "guidance": {}}
        cells, outages, down = plan_week.eval_cells_and_outages(
            ROOT / "evals", doc, list(fires), NOW, ROUTINE_GIT)
        ctx = {**base_ctx(cells), "room": 100.0, "refresh": False, "improve_charge": 0.10,
               "skills": {"writing-adrs": skill_ctx()}, "lessons": [], "outages": outages,
               "routine_down": down,
               "bare": [{"fixture": SKILL_FIXTURE, "model": m, "skill": "writing-adrs"}
                        for m in (A, B)] if bare else []}
        if roster is not None:
            ctx["roster_models"] = list(roster)
        return plan_week.build_plan(ctx, NOW, max_fires=10_000)

    @staticmethod
    def legs(plan, fixture):
        return sorted((f["arms"], f["model"]) for f in plan["fires"] if f["fixture"] == fixture)

    def test_a_fixtures_two_cells_are_one_leg_in_roster_order(self):
        plan = self.plan()
        self.assertEqual(self.legs(plan, SKILL_FIXTURE), [("both", PAIR)])
        self.assertEqual(self.legs(self.plan(roster=(B, A)), SKILL_FIXTURE),
                         [("both", f"{B},{A}")])
        leg = next(f for f in plan["fires"] if f["fixture"] == SKILL_FIXTURE)
        single = {f["model"]: f for f in self.plan(roster=None)["fires"]
                  if f["fixture"] == SKILL_FIXTURE}
        self.assertEqual(leg["cost"], single[A]["cost"] + single[B]["cost"])
        self.assertEqual(leg["cells"], [{"model": m, "band": single[m]["band"],
                                         "cost": single[m]["cost"]} for m in (A, B)])
        self.assertEqual(leg["band"], min((single[A], single[B]),
                                          key=lambda f: f["slot"])["band"])
        # The matrix leg: the pair as one model input, eval_key per fixture.
        row = next(r for r in plan["matrix"]["include"] if r["fixture"] == SKILL_FIXTURE)
        self.assertEqual((row["model"], row["eval_key"]), (PAIR, "writing-adrs/bootstrap"))
        self.assertNotIn("cells", row)
        self.assertEqual([r["slot"] for r in plan["matrix"]["include"]],
                         list(range(len(plan["fires"]))))

    def test_without_the_roster_order_nothing_is_paired(self):
        self.assertEqual(self.legs(self.plan(roster=None), SKILL_FIXTURE),
                         sorted([("both", A), ("both", B)]))

    @mock.patch.object(plan_week, "PAIR_EVERY_FIRE", False)
    def test_a_lone_cell_stays_a_single_leg(self):
        # B's cell has a pending fire, so only A's is planned.
        held = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=10), B)]
        self.assertEqual(self.legs(self.plan(held), SKILL_FIXTURE), [("both", A)])

    def test_a_pending_pair_fire_is_not_refired(self):
        held = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=10), PAIR)]
        self.assertEqual(self.legs(self.plan(held), SKILL_FIXTURE), [])

    def test_bare_legs_pair_apart_from_the_paired_arms(self):
        self.assertEqual(self.legs(self.plan(bare=True), SKILL_FIXTURE),
                         [("bare", PAIR), ("both", PAIR)])

    def test_in_situ_legs_pair(self):
        self.assertEqual(self.legs(self.plan(), GUIDANCE_FIXTURE), [("in-situ", PAIR)])

    def test_improve_legs_are_untouched_and_last(self):
        paired, single = self.plan(), self.plan(roster=None)

        def improve(plan):
            return [{k: v for k, v in f.items() if k != "slot"} for f in plan["fires"]
                    if f["mode"] in plan_week.IMPROVE_MODES]
        self.assertTrue(improve(paired))
        self.assertEqual(improve(paired), improve(single))
        modes = [f["mode"] in plan_week.IMPROVE_MODES for f in paired["fires"]]
        self.assertEqual(modes, sorted(modes))
        # Pairing only shortens the matrix: each pair leg holds two cells.
        pairs = sum(1 for f in paired["fires"] if "," in f["model"])
        self.assertGreater(pairs, 0)
        self.assertEqual(len(paired["fires"]) + pairs, len(single["fires"]))

    def test_the_planned_legs_revalidate(self):
        for row in self.plan(bare=True)["matrix"]["include"]:
            if row["mode"] != "eval" or row["fixture"] not in (SKILL_FIXTURE, GUIDANCE_FIXTURE):
                continue
            with self.subTest(row=row["fixture"], arms=row["arms"]):
                plan_week.validate_fire({"MODE": "eval", "ARMS": row["arms"],
                                         "FIXTURE": row["fixture"], "EVAL_KEY": row["eval_key"],
                                         "MODEL": row["model"], "SKILL": row["skill"],
                                         "HOLDOUT": row["holdout"]})


class PairFiresUnitTests(unittest.TestCase):

    @staticmethod
    def item(model, fixture="evals/x", arms="both", mode="eval", band="missing", cost=0.01):
        return {"mode": mode, "arms": arms, "fixture": fixture, "model": model,
                "skill": "x", "holdout": "", "cost": cost, "band": band, "order": ()}

    def models(self, chosen, roster=(A, B)):
        return [(i["fixture"], i["arms"], i["model"])
                for i in plan_week.pair_fires(chosen, list(roster))]

    def test_the_pair_takes_the_first_ones_place(self):
        chosen = [self.item(B, band="near"), self.item(A, "evals/y"), self.item(A)]
        out = plan_week.pair_fires(chosen, [A, B])
        self.assertEqual([(i["fixture"], i["model"], i["band"]) for i in out],
                         [("evals/x", PAIR, "near"), ("evals/y", A, "missing")])
        self.assertEqual(out[0]["cells"], [{"model": A, "band": "missing", "cost": 0.01},
                                           {"model": B, "band": "near", "cost": 0.01}])
        # The input is left as it was.
        self.assertNotIn("cells", chosen[0])

    def test_only_same_fixture_and_arms_on_two_roster_models_pair(self):
        third = "claude-other-1"
        cases = {
            "different arms": [self.item(A), self.item(B, arms="bare")],
            "different fixtures": [self.item(A), self.item(B, "evals/y")],
            "one model twice": [self.item(A), self.item(A)],
            "a model off the roster": [self.item(A), self.item(third)],
            "an id outside the contract": [self.item(A), self.item("m2")],
            "improve legs": [self.item("", mode="improve", arms=""),
                             self.item("", mode="improve", arms="")],
        }
        for label, chosen in cases.items():
            with self.subTest(case=label):
                roster = (A, B, "m2")
                self.assertEqual(self.models(chosen, roster),
                                 [(i["fixture"], i["arms"], i["model"]) for i in chosen])
        self.assertEqual(plan_week.pair_fires([self.item(A), self.item(B)], None),
                         [self.item(A), self.item(B)])

    def test_a_three_model_roster_pairs_the_first_two_and_leaves_the_third(self):
        third = "claude-other-1"
        chosen = [self.item(third), self.item(B), self.item(A)]
        self.assertEqual(self.models(chosen, (A, B, third)),
                         [("evals/x", "both", third), ("evals/x", "both", PAIR)])


class PairEveryFireTests(unittest.TestCase):
    """PAIR_EVERY_FIRE (off since 2026-11-07 17:51 UTC; the switch is kept)."""

    item = staticmethod(PairFiresUnitTests.item)

    def test_a_single_skill_both_leg_gains_the_other_model(self):
        for model in (A, B):
            with self.subTest(model=model):
                (leg,) = plan_week.pair_every_fire([self.item(model, cost=0.05)], [A, B])
                self.assertEqual((leg["model"], leg["cost"]), (PAIR, 0.05))
                self.assertEqual(leg["cells"], [{"model": model, "band": "missing",
                                                 "cost": 0.05}])

    def test_other_legs_are_kept(self):
        legs = [self.item(PAIR), self.item(A, arms="bare"),
                self.item(A, GUIDANCE_FIXTURE, arms="both"),
                self.item(A, GUIDANCE_FIXTURE, arms="in-situ"),
                self.item("", mode="improve", arms=""), self.item("claude-other-1")]
        self.assertEqual(plan_week.pair_every_fire(legs, [A, B]), legs)
        self.assertEqual(plan_week.pair_every_fire([self.item(A)], [A]), [self.item(A)])
        self.assertEqual(plan_week.pair_every_fire([self.item(A)], None), [self.item(A)])

    @mock.patch.object(plan_week, "PAIR_EVERY_FIRE", True)
    def test_the_planner_pairs_a_lone_cell(self):
        case = PlannerPairTests("test_a_lone_cell_stays_a_single_leg")
        case.setUp()
        try:
            held = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=10), B)]
            self.assertEqual(case.legs(case.plan(held), SKILL_FIXTURE), [("both", PAIR)])
        finally:
            case.doCleanups()


class ValidateFireTests(unittest.TestCase):

    GOOD = {"MODE": "eval", "ARMS": "both", "FIXTURE": SKILL_FIXTURE,
            "EVAL_KEY": "writing-adrs/bootstrap", "MODEL": PAIR, "SKILL": "", "HOLDOUT": ""}

    def test_a_pair_leg_is_accepted_like_a_lone_one(self):
        plan_week.validate_fire(self.GOOD)
        plan_week.validate_fire({**self.GOOD, "MODEL": f"{B},{A}"})
        plan_week.validate_fire({**self.GOOD, "ARMS": "bare"})
        plan_week.validate_fire({**self.GOOD, "FIXTURE": GUIDANCE_FIXTURE,
                                 "EVAL_KEY": GUIDANCE_FIXTURE[len("evals/"):],
                                 "ARMS": "in-situ"})

    def test_each_model_of_a_pair_is_checked(self):
        judge = yaml.safe_load((ROOT / "evals" / "roster.yml").read_text())["judge"]["id"]
        for model in (f"{A},{A}", f"{A},{B},{A}", f"{A},", f",{A}", f"{A}, {B}",
                      f"{A},{judge}", f"{A},claude-nonexistent-9", f"-h,{A}",
                      f"{A},{B.upper()}", f"{A};{B}"):
            with self.subTest(model=model):
                with self.assertRaises(plan_week.PlanError):
                    plan_week.validate_fire({**self.GOOD, "MODEL": model})

    def test_a_pair_is_an_eval_legs_only(self):
        improve = {"MODE": "improve", "ARMS": "", "FIXTURE": "", "EVAL_KEY": "",
                   "MODEL": PAIR, "SKILL": "writing-adrs", "HOLDOUT": "bootstrap"}
        with self.assertRaises(plan_week.PlanError):
            plan_week.validate_fire(improve)

    def test_the_weekly_dispatch_passes_the_leg_model_through_env(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-weekly.yml").read_text())
        steps = {s["name"]: s for s in doc["jobs"]["dispatch"]["steps"]}
        for name in ("Revalidate the planned fire", "Dispatch the validated fire"):
            with self.subTest(step=name):
                self.assertEqual(steps[name]["env"]["MODEL"], "${{ matrix.model }}")
                self.assertNotIn("${{", steps[name]["run"])


@unittest.skipUnless(shutil.which("jq") and shutil.which("git"), "needs jq and git on PATH")
class FireValidateStepTests(unittest.TestCase):
    """routine-eval-fire.yml's validation step, run under bash."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.script = fire_base.step_script("Validate the dispatch inputs")

    def run_step(self, inputs, path=None):
        event = self.tmp / "event.json"
        event.write_text(json.dumps({"inputs": inputs}), encoding="utf-8")
        output = self.tmp / "output"
        output.write_text("", encoding="utf-8")
        env = {"PATH": path or os.environ["PATH"], "HOME": str(self.tmp),
               "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
               "GITHUB_EVENT_PATH": str(event), "GITHUB_OUTPUT": str(output)}
        proc = subprocess.run(["bash", "-c", self.script], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=60)
        values = dict(line.split("=", 1) for line in
                      output.read_text(encoding="utf-8").splitlines())
        return proc, values

    def eval_inputs(self, **extra):
        return {"mode": "eval", "fixture": fire_base.FIXTURE, "arms": "both", "trials": "1",
                **extra}

    def test_a_pair_of_roster_arms_passes_in_either_order(self):
        for model in (PAIR, f"{B},{A}"):
            for arms in ("both", "bare"):
                with self.subTest(model=model, arms=arms):
                    proc, values = self.run_step(self.eval_inputs(model=model, arms=arms))
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                    self.assertEqual(values["model"], model)

    def test_any_other_comma_is_refused_with_the_fixed_message(self):
        judge = yaml.safe_load((ROOT / "evals" / "roster.yml").read_text())["judge"]["id"]
        for bad in (f"{A},{A}", f"{A},{B},{A}", f"{A},", f",{A}", ",", f"{A}, {B}",
                    f"{A},{judge}", f"{A},claude-nonexistent-9", f"-h,{A}", f"{A},--help",
                    f"{A},{B.upper()}", f"{A},{B}\u0301", 'x", "evil": "1'):
            with self.subTest(bad=bad):
                proc, values = self.run_step(self.eval_inputs(model=bad))
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(FIXED_REFUSAL, proc.stdout)
                self.assertNotIn("run_id", values)
                if bad not in (f"{A},{A}", f"{A},", f",{A}", f"{A},{judge}",
                               f"{A},claude-nonexistent-9", f"{A},{B.upper()}"):
                    self.assertNotIn(bad, proc.stdout + proc.stderr)

    def test_a_pair_member_outside_the_contract_never_reaches_the_script(self):
        # A stand-in `python3` that calls every model an arm, and records
        # each one that reached scripts/roster_arm.py.
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        reached = self.tmp / "reached"
        stand_in = bin_dir / "python3"
        stand_in.write_text(
            f"#!{sys.executable}\nimport os, sys\n"
            "if sys.argv[1:2] == ['scripts/roster_arm.py']:\n"
            f"    open({str(reached)!r}, 'a').write(sys.argv[2] + '\\n')\n"
            "    sys.exit(0)\n"
            "os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n", encoding="utf-8")
        stand_in.chmod(0o755)
        path = f"{bin_dir}:{os.environ['PATH']}"
        proc, values = self.run_step(self.eval_inputs(model=PAIR), path)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(reached.read_text().split(), [A, B])
        reached.unlink()
        for bad in (f"-h,{A}", f"{A},-x", f"{A},Model-B", f"{A},{A}", f"{A},a/b"):
            with self.subTest(bad=bad):
                proc, values = self.run_step(self.eval_inputs(model=bad), path)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout.strip(), "::error::" + FIXED_REFUSAL)
                self.assertFalse(reached.exists())

    def test_a_pair_is_refused_outside_eval_mode(self):
        improve = {"mode": "improve", "skill": fire_base.SKILL, "holdout": fire_base.HOLDOUT,
                   "arms": "both", "trials": "1", "model": PAIR}
        proc, values = self.run_step(improve)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("'model' must be empty unless the mode is eval", proc.stdout)
        self.assertNotIn("run_id", values)


@unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
class FireStepPayloadTests(unittest.TestCase):
    """routine-eval-fire.yml's fire step, with a stand-in curl."""

    SESSION = "session_01TestOnlyAbc"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(fire_base.FAKE_CURL, encoding="utf-8")
        curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
        self.bin = bin_dir
        self.log = self.tmp / "log"
        self.log.mkdir()
        self.summary = self.tmp / "summary.md"
        self.script = fire_base.step_script("Fire the eval routine")
        steps = fire_base.load(fire_base.WORKFLOW)["jobs"]["fire"]["steps"]
        self.url = next(s for s in steps
                        if s.get("name") == "Fire the eval routine")["env"]["FIRE_URL"]

    def fire(self, model):
        self.summary.write_text("", encoding="utf-8")
        env = {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "HOME": str(self.tmp),
               "FIRE_URL": self.url, "EVAL_ROUTINE_FIRE_BEARER": "sk-ant-oat01-FAKE-FOR-TESTS",
               "RUN_ID": "20261106T120000Z-a1b2c3", "FIXTURE": fire_base.FIXTURE,
               "ARMS": "both", "TRIALS": "1", "MODE": "eval", "MODEL": model,
               "GITHUB_STEP_SUMMARY": str(self.summary),
               "FAKE_CURL_LOG": str(self.log), "FAKE_CURL_STATUS": "200",
               "FAKE_CURL_BODY": json.dumps({
                   "type": "routine_fire", "claude_code_session_id": self.SESSION,
                   "claude_code_session_url": f"https://claude.ai/code/{self.SESSION}"})}
        proc = subprocess.run(["bash", "-c", self.script], cwd=self.tmp, env=env,
                              capture_output=True, text=True, timeout=60)
        sent = self.log / "argv.json"
        if not sent.exists():
            return proc, None
        argv = json.loads(sent.read_text())
        return proc, json.loads(json.loads(argv[argv.index("--data-binary") + 1])["text"])

    def test_a_pair_is_sent_as_models_in_its_order_and_never_with_model(self):
        for model, models in ((PAIR, [A, B]), (f"{B},{A}", [B, A])):
            with self.subTest(model=model):
                proc, text = self.fire(model)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(list(text), ["mode", "run_id", "fixture", "arms", "trials",
                                              "models"])
                self.assertEqual(text["models"], models)
                self.assertIn(f"- Models: `{model}`", self.summary.read_text())

    def test_one_model_is_still_sent_as_model(self):
        proc, text = self.fire(A)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(text["model"], A)
        self.assertNotIn("models", text)
        self.assertIn(f"- Model: `{A}`", self.summary.read_text())

    def test_a_comma_that_is_not_a_pair_stops_before_the_api(self):
        for bad in (f"{A},{A}", f"{A},{B},{A}", f"{A},", 'x", "evil": "1', f"{A},Model-B"):
            with self.subTest(bad=bad):
                proc, text = self.fire(bad)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIsNone(text)
                self.assertFalse((self.log / "calls").exists())

    def test_the_guard_step_says_a_pair_reserves_one_fire(self):
        steps = fire_base.load(fire_base.WORKFLOW)["jobs"]["fire"]["steps"]
        guard_step = next(s for s in steps if s.get("name") == "Check the weekly allowance")
        self.assertNotIn("MODEL", guard_step["env"])
        text = fire_base.WORKFLOW.read_text(encoding="utf-8")
        before = text[:text.index("- name: Check the weekly allowance")]
        self.assertIn("pair fire", before[before.rindex("- name:"):])


#: A second invocation's directory, after the first's (STAMP).
STAMP_2 = "20261006T195512Z"


class IngestTests(GitCase):
    """One run id holding two run_eval invocations on two models."""

    MODELS = {STAMP: "model-a", STAMP_2: "model-b"}

    def files(self):
        out = {}
        for when, model in self.MODELS.items():
            base = f"{ingest.SOURCE_ROOT}/{RUN_ID}/writing-adrs/{when}"
            out[f"{base}/report.md"] = REPORT.replace(STAMP, when).encode()
            for arm in ("with_skill", "without_skill"):
                doc = summary(arm, timestamp=when)
                doc["cross_model"]["model"] = model
                out[f"{base}/bootstrap/{arm}/summary.json"] = json.dumps(doc, indent=2).encode()
        return out

    def test_two_invocations_ingest_with_their_own_models(self):
        sha = self.commit(self.files())
        staged = self.tmp / "staged"
        self.assertEqual(self.validate(expect=sha, out=staged),
                         {"run_id": RUN_ID, "sha": sha, "files": "6"})
        tree = self.tmp / "tree"
        self.assertEqual(ingest.place(staged, tree), {"changed": "true", "added": "6"})
        found = {}
        for (run_dir, key, when, fixture, arm), entry in compute_gates._summaries(tree).items():
            doc = json.loads(entry["summary"].read_text(encoding="utf-8"))
            found[(run_dir, arm)] = run_eval._arm_model([doc])
        self.assertEqual(found, {
            (f"routine-results/{RUN_ID}/writing-adrs/{when}", arm): model
            for when, model in self.MODELS.items() for arm in ("with_skill", "without_skill")})


def usage(tag: str, usd: float, delta: float) -> dict:
    """One run_eval invocation's run-level `usage` block (only what is read)."""
    return {"tag": tag, "cost_estimate": {"usd": usd, "reasons": {}},
            "meter_delta": {"windows": {"seven_day": {"delta": delta, "window_reset": False}}}}


class PairRunCostTests(unittest.TestCase):
    """The guard and the planner read a pair run per invocation."""

    RUN = "20261106T100000Z-abc123"
    WHEN = {A: "20261106T100100Z", B: "20261106T101400Z"}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tree = Path(tmp.name)
        self.usage = {A: usage("a", 0.30, 0.004), B: usage("b", 0.10, 0.002)}
        for model, when in self.WHEN.items():
            for arm in ("with_skill", "without_skill"):
                path = (self.tree / "routine-results" / self.RUN / "writing-adrs" / when
                        / "bootstrap" / arm / "summary.json")
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"cross_model": {"model": model},
                                            "usage": self.usage[model]}))

    def records(self):
        return [{"path": f"routine-results/{self.RUN}/writing-adrs/{when}", "model": model,
                 "role": role, "timestamp": when, "pair": None}
                for model, when in self.WHEN.items() for role in ("with", "without")]

    def estimate(self, points, usd):
        (self.tree / "routine-results" / self.RUN / "cost_estimate.json").write_text(
            json.dumps({"schema_version": 1, "points": points, "usd": usd}))

    def test_the_guard_charges_each_invocation(self):
        limits = {"per_run_cap": 0.03, "per_run_overrun": 0.005}
        self.assertAlmostEqual(guard.run_cost(self.tree / "routine-results" / self.RUN, limits),
                               (0.004 + 0.005) + (0.002 + 0.005))

    def test_the_estimate_lists_both_invocations(self):
        self.assertEqual(ingest.estimate(self.tree, self.RUN), {"estimated": "true"})
        doc = json.loads((self.tree / "routine-results" / self.RUN / "cost_estimate.json")
                         .read_text())
        self.assertEqual(sorted(i["usd"] for i in doc["invocations"]), [0.10, 0.30])
        self.assertAlmostEqual(doc["usd"], 0.40)

    def test_the_planners_cost_per_observation_splits_the_runs_points(self):
        self.estimate(0.008, 0.40)
        costs = plan_week.pair_costs(self.records(), self.tree, NOW_PAIR, timedelta(days=14))
        # A spent 0.30 of the run's 0.40 dollars, B 0.10; one observation each.
        self.assertAlmostEqual(costs[A], 0.008 * 0.75)
        self.assertAlmostEqual(costs[B], 0.008 * 0.25)

    def test_a_pair_run_that_does_not_add_up_is_left_out(self):
        # An invocation's dollars missing from the summaries: unknown, never a guess.
        self.estimate(0.008, 0.50)
        self.assertEqual(plan_week.pair_costs(self.records(), self.tree, NOW_PAIR,
                                              timedelta(days=14)), {})
        self.estimate(0.008, 0.40)
        broken = self.tree / "routine-results" / self.RUN / "writing-adrs" / self.WHEN[B]
        (broken / "bootstrap" / "with_skill" / "summary.json").write_text("{")
        self.assertEqual(plan_week.pair_costs(self.records(), self.tree, NOW_PAIR,
                                              timedelta(days=14)), {})


#: Inside PairRunCostTests' cost window.
NOW_PAIR = NOW.replace(year=2026, month=11, day=7)


if __name__ == "__main__":
    unittest.main()
