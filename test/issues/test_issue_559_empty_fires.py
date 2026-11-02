#!/usr/bin/env python3
"""skills-evals#559, the planner half: empty fires and pending fires.

Runs now test main's copy of a skill subject, which adds refusals an
upstream edit can trigger at any time. A refused run still concludes its
fire `success`, so the planner judges a cell by the fires that produced no
run: two such fires turn a missing, near or recheck cell into a
`fixture-broken` work item, and a fire whose run may still land holds the
cell. Both are counted against gates' output-only `newest_on_model` (the
newest run of ANY role or digest), never the pooled newest, so a fire that
landed a run that does not pool is not empty.

Outages (2026-11-01: six fixtures fired, none produced anything): each
fire is classified once, young, delivered (a run stamped inside its
window, gates' `run_stamps_on_model`) or empty; every classified fire is
grouped into sweeps, and a sweep with no delivered or young fire whose
empties cover three cells excuses each cell's earliest such fire, one per
cell, so fixtures broken together still go fixture-broken.

Deterministic: every `now` is injected; no network, clock or sleep.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import gates  # noqa: E402
import plan_week  # noqa: E402

#: Over RETRY_AFTER past EMPTY_FIRES_SINCE, so only the rule under test excludes a fire.
NOW = plan_week.EMPTY_FIRES_SINCE + timedelta(days=20)
SKILL_FIXTURE = "evals/writing-adrs/bootstrap"
SECTION = "anything-you-name-gets-its-link"
GUIDANCE_FIXTURE = f"evals/guidance/{SECTION}/handoff"
MODEL = "m1"
POLICY = gates.load_gate_policy()["skills"]


def stamp(moment: datetime) -> str:
    """A run timestamp as compute_gates indexes it."""
    return moment.strftime(plan_week.STAMP)


def fire(run_id, fixture, started, *, bare=False, conclusion="success", status="completed",
         model=MODEL):
    """One routine-eval-fire.yml run row, as the runs API records it."""
    arms = " bare" if bare else ""
    at = started.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": run_id, "display_title": f"Fire eval routine: eval{arms} {fixture} {model}",
            "status": status, "conclusion": conclusion, "run_started_at": at, "created_at": at}


def arm_run(skill, fixture, role, moment, *, tested="t-main", pair=None):
    """One index arm run in compute_gates.build_index's shape."""
    path = f"routine-results/{stamp(moment)}-000001/{skill}/{stamp(moment)}"
    trial = {"error": None, "agent": {"cost_usd": 0.25},
             "objective_checks": [{"id": "c0", "passed": True, "detail": "ok"}],
             "judge": None, "judge_conditional": False}
    return {"skill": skill, "fixture": fixture, "model": MODEL, "role": role,
            "timestamp": stamp(moment), "path": path, "report": f"{path}/report.md",
            "tested_digest": tested, "fixture_digest": "f-main",
            "arm_context_digest": f"{role}-ctx", "pair_key": "p", "pair": pair,
            "cli_versions": ["1.0.0 (Claude Code)"], "run": {"id": stamp(moment)},
            "judge_carried": False, "judge_conditional": False,
            "trials": [gates.trial_record(trial)]}


def cell(fixture, cls, *, empty=0, pending=False, newest=None, verdict=None, skill="s"):
    """An eval_cells row, for routing tests."""
    return {"skill": skill, "section": None, "fixture": fixture, "model": MODEL,
            "class": cls, "verdict": verdict, "with_runs": 0, "without_runs": 0,
            "newest": newest, "usd_per_fire": None, "empty_fires": empty, "pending": pending}


def ctx(cells, removal=()):
    return {"model_weights": {MODEL: 1.0}, "removal_prs": list(removal), "cells": cells,
            "reservation": 0.035, "overrun": 0.005, "points_per_usd": None}


def planned(cells, removal=()):
    """{band: [fixture, ...]} of the fires, and the fixture-broken fixtures."""
    bands, work = plan_week.eval_items(ctx(cells, removal), NOW)
    return ({b: [i["fixture"] for i in items] for b, items in bands.items() if items},
            [w["fixture"] for w in work if w["kind"] == "fixture-broken"])


def one(cells, fixture):
    return next(c for c in cells if c["fixture"] == fixture)


class GatesTests(unittest.TestCase):
    """gates computes `newest_on_model` and reaches guidance cells with it."""

    def test_newest_on_model_counts_every_run_whatever_its_digest(self):
        older, newer = NOW - timedelta(days=3), NOW - timedelta(days=2)
        runs = [arm_run("demo", None, "with", newer, tested="t-stale"),
                arm_run("demo", None, "without", older)]
        expected = {"": {"fixture_digest": "f-main", "tested_digest": "t-main"}}
        pools = gates.pool_cells(runs, "demo", [MODEL, "m2"], expected)
        self.assertEqual(pools[("", MODEL)]["newest_on_model"], stamp(newer))
        self.assertIsNone(pools[("", "m2")]["newest_on_model"])
        self.assertEqual(pools[("", MODEL)]["run_stamps_on_model"],
                         [stamp(older), stamp(newer)])
        self.assertEqual(pools[("", "m2")]["run_stamps_on_model"], [])
        cells = gates.retirement({"runs": runs}, [MODEL, "m2"], "demo", POLICY,
                                 expected)["cells"]
        # The stale with run does not pool, but it is still the newest run.
        self.assertEqual([(c["model"], c["class"], c["newest_on_model"]) for c in cells],
                         [(MODEL, "insufficient", stamp(newer)), ("m2", "missing", None)])
        self.assertEqual([c["run_stamps_on_model"] for c in cells],
                         [[stamp(older), stamp(newer)], []])

    def test_guidance_cells_carry_the_run_stamps(self):
        moment = NOW - timedelta(days=2)
        runs = [arm_run(SECTION, "handoff", "with", moment, pair="in_situ")]
        expected = {"handoff": {"fixture_digest": "f-main", "tested_digest": "t-main"}}
        got = gates.guidance_verdict({"runs": runs}, [MODEL], SECTION, POLICY, expected)
        self.assertEqual(got["cells"][0]["run_stamps_on_model"], [stamp(moment)])


class EndToEndTests(unittest.TestCase):
    """gates.retirement and gates.guidance_verdict output through
    plan_week.eval_cells with fire rows."""

    RUN = NOW - timedelta(days=3)

    def gates_doc(self):
        skill_runs = [arm_run("writing-adrs", "bootstrap", "with", self.RUN, tested="t-stale"),
                      arm_run("writing-adrs", "bootstrap", "without", self.RUN)]
        guidance_runs = [arm_run(SECTION, "handoff", "with", self.RUN, tested="t-stale",
                                 pair="in_situ"),
                         arm_run(SECTION, "handoff", "without", self.RUN, pair="in_situ")]
        expected = {"fixture_digest": "f-main", "tested_digest": "t-main"}
        return {"roster_models": [MODEL],
                "skills": {"writing-adrs": gates.retirement(
                    {"runs": skill_runs}, [MODEL], "writing-adrs", POLICY,
                    {"bootstrap": expected})},
                "guidance": {SECTION: gates.guidance_verdict(
                    {"runs": guidance_runs}, [MODEL], SECTION, POLICY,
                    {"handoff": expected})}}

    def cells(self, doc, fires):
        cells = plan_week.eval_cells(ROOT / "evals", doc, fires, NOW)
        return one(cells, SKILL_FIXTURE), one(cells, GUIDANCE_FIXTURE)

    def fires(self, started):
        return [fire(i, f, started) for i, f in enumerate([SKILL_FIXTURE, GUIDANCE_FIXTURE] * 2)]

    def test_a_stale_run_newer_than_the_fires_leaves_none_empty(self):
        # The only with run is stale, so nothing pools (pooled newest None),
        # yet it landed after both fires: they produced something.
        for got in self.cells(self.gates_doc(), self.fires(self.RUN - timedelta(days=1))):
            with self.subTest(fixture=got["fixture"]):
                self.assertEqual((got["class"], got["with_runs"], got["newest"]),
                                 ("insufficient", 0, None))
                self.assertEqual(got["empty_fires"], 0)

    def test_two_fires_after_the_newest_run_are_empty_and_break_the_cell(self):
        doc = self.gates_doc()
        cells = plan_week.eval_cells(ROOT / "evals", doc,
                                     self.fires(self.RUN + timedelta(days=1)), NOW)
        for fixture in (SKILL_FIXTURE, GUIDANCE_FIXTURE):
            with self.subTest(fixture=fixture):
                self.assertEqual(one(cells, fixture)["empty_fires"], 2)
        mine = [one(cells, SKILL_FIXTURE), one(cells, GUIDANCE_FIXTURE)]
        self.assertTrue(all(c["schedulable"] and c.get("stakes") != "none" for c in mine))
        bands, work = plan_week.eval_items(ctx(mine), NOW)
        self.assertEqual(sum(len(v) for v in bands.values()), 0)
        self.assertEqual(sorted((w["fixture"], w.get("section")) for w in work),
                         [(GUIDANCE_FIXTURE, SECTION), (SKILL_FIXTURE, None)])

    def test_an_absent_field_counts_no_empty_fire(self):
        for field in ("newest_on_model", "run_stamps_on_model"):
            doc = self.gates_doc()
            for c in doc["skills"]["writing-adrs"]["cells"] + doc["guidance"][SECTION]["cells"]:
                del c[field]
            for got in self.cells(doc, self.fires(self.RUN + timedelta(days=1))):
                with self.subTest(field=field, fixture=got["fixture"]):
                    self.assertEqual((got["empty_fires"], got["outage_fires"]), (0, 0))

    def test_an_unreadable_field_counts_no_empty_fire(self):
        for field, value in (("newest_on_model", "not a stamp"),
                             ("run_stamps_on_model", ["not a stamp"]),
                             ("run_stamps_on_model", None)):
            doc = self.gates_doc()
            for c in doc["skills"]["writing-adrs"]["cells"]:
                c[field] = value
            skill_cell, _ = self.cells(doc, self.fires(self.RUN + timedelta(days=1)))
            with self.subTest(field=field, value=value):
                self.assertEqual(skill_cell["empty_fires"], 0)


class CountingTests(unittest.TestCase):
    """Which finished fires count as empty."""

    MISSING = {"roster_models": [MODEL], "skills": {"writing-adrs": {"cells": [
        {"fixture": "bootstrap", "model": MODEL, "class": "missing", "newest_on_model": None,
         "run_stamps_on_model": [], "runs": {"with": [], "without": []}}]}}}

    def empty(self, fires, now=NOW):
        cells = plan_week.eval_cells(ROOT / "evals", self.MISSING, fires, now)
        return one(cells, SKILL_FIXTURE)["empty_fires"]

    def test_a_missing_cell_with_two_15_day_old_fires_stays_in_missing(self):
        old = NOW - timedelta(days=15)
        fires = [fire(i, SKILL_FIXTURE, old) for i in (1, 2)]
        self.assertEqual(self.empty(fires), 0)
        cells = plan_week.eval_cells(ROOT / "evals", self.MISSING, fires, NOW)
        self.assertEqual(planned([one(cells, SKILL_FIXTURE)]),
                         ({"missing": [SKILL_FIXTURE]}, []))
        # The same two fires inside RETRY_AFTER do break it.
        recent = [fire(i, SKILL_FIXTURE, NOW - timedelta(days=13)) for i in (1, 2)]
        self.assertEqual(self.empty(recent), 2)

    def test_fires_before_empty_fires_since_are_not_counted(self):
        self.assertEqual(plan_week.EMPTY_FIRES_SINCE.isoformat(), "2026-11-03T00:00:00+00:00")
        now = plan_week.EMPTY_FIRES_SINCE + timedelta(days=1)
        before = [fire(i, SKILL_FIXTURE, plan_week.EMPTY_FIRES_SINCE - timedelta(hours=1))
                  for i in (1, 2)]
        self.assertEqual(self.empty(before, now), 0)
        at = [fire(i, SKILL_FIXTURE, plan_week.EMPTY_FIRES_SINCE) for i in (1, 2)]
        self.assertEqual(self.empty(at, now), 2)

    def test_young_failed_and_bare_fires_are_not_empty(self):
        fires = [fire(1, SKILL_FIXTURE, NOW - timedelta(hours=1)),
                 fire(2, SKILL_FIXTURE, NOW - timedelta(days=1), conclusion="failure"),
                 fire(3, SKILL_FIXTURE, NOW - timedelta(days=1), bare=True)]
        self.assertEqual(self.empty(fires), 0)


class RoutingTests(unittest.TestCase):
    """Which bands a cell with empty fires leaves."""

    OLD = stamp(NOW - timedelta(weeks=9))

    def test_a_recheck_cell_with_two_empty_fires_becomes_fixture_broken(self):
        due = cell("evals/s/a", "no-benefit", newest=self.OLD)
        self.assertEqual(planned([due]), ({"recheck": ["evals/s/a"]}, []))
        self.assertEqual(planned([{**due, "empty_fires": 2}]), ({}, ["evals/s/a"]))

    def test_a_near_cell_with_two_empty_fires_becomes_fixture_broken(self):
        self.assertEqual(planned([cell("evals/s/a", "insufficient", empty=2)]),
                         ({}, ["evals/s/a"]))

    def test_a_kept_subjects_unsettled_cell_due_for_recheck_breaks_too(self):
        kept = cell("evals/s/a", "insufficient", newest=self.OLD, verdict="keep")
        self.assertEqual(planned([kept]), ({"recheck": ["evals/s/a"]}, []))
        self.assertEqual(planned([{**kept, "empty_fires": 2}]), ({}, ["evals/s/a"]))

    def test_a_safety_cell_keeps_its_slot_but_obeys_the_pending_rule(self):
        safety = cell("evals/s/a", "no-benefit", empty=2)
        self.assertEqual(planned([safety], removal=["s"]), ({"safety": ["evals/s/a"]}, []))
        self.assertEqual(planned([{**safety, "pending": True}], removal=["s"]), ({}, []))


class PendingTests(unittest.TestCase):
    """A fire whose run may still land holds the cell in every band."""

    def doc(self, newest_on_model):
        row = {"fixture": "bootstrap", "model": MODEL, "class": "missing",
               "runs": {"with": [], "without": []}}
        if newest_on_model is not ...:
            row["newest_on_model"] = newest_on_model
            row["run_stamps_on_model"] = [newest_on_model] if newest_on_model else []
        return {"roster_models": [MODEL], "skills": {"writing-adrs": {"cells": [row]}}}

    def cell(self, doc, fires):
        return one(plan_week.eval_cells(ROOT / "evals", doc, fires, NOW), SKILL_FIXTURE)

    def test_a_pending_fire_blocks_a_re_fire_and_a_landed_run_releases_it(self):
        started = NOW - timedelta(minutes=30)
        fires = [fire(1, SKILL_FIXTURE, started)]
        held = self.cell(self.doc(None), fires)
        self.assertTrue(held["pending"])
        self.assertEqual(planned([held]), ({}, []))
        # A run of any role or digest landed after the fire started.
        landed = self.cell(self.doc(stamp(started + timedelta(minutes=10))), fires)
        self.assertFalse(landed["pending"])
        self.assertEqual(planned([landed]), ({"missing": [SKILL_FIXTURE]}, []))

    def test_a_running_fire_is_pending(self):
        fires = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=5), conclusion=None,
                      status="in_progress")]
        self.assertTrue(self.cell(self.doc(None), fires)["pending"])

    def test_a_failed_bare_or_old_fire_is_not_pending(self):
        young = NOW - timedelta(minutes=30)
        for fires in ([fire(1, SKILL_FIXTURE, young, conclusion="failure")],
                      [fire(1, SKILL_FIXTURE, young, bare=True)],
                      [fire(1, SKILL_FIXTURE, NOW - plan_week.FIRE_RESULT_WINDOW)]):
            with self.subTest(fires=fires[0]["display_title"], conclusion=fires[0]["conclusion"]):
                self.assertFalse(self.cell(self.doc(None), fires)["pending"])

    def test_without_the_field_a_young_fire_is_pending(self):
        # Fail safe the cheap way: at most FIRE_RESULT_WINDOW of waiting.
        fires = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=30))]
        self.assertTrue(self.cell(self.doc(...), fires)["pending"])


class OutageTests(unittest.TestCase):
    """A routine outage empties a whole sweep; that says nothing about fixtures."""

    FIXTURES = ["evals/github-actions-sha-pinning", "evals/writing-adrs/bootstrap",
                "evals/disarm-inherited-reach", "evals/windows-elevation-from-wsl",
                "evals/embeddable-tool-pages", "evals/workflow-path-audit/required-check-routing"]
    DAY = plan_week.EMPTY_FIRES_SINCE + timedelta(days=2)  # 2026-11-05
    LATER = DAY + timedelta(days=3)  # inside RETRY_AFTER, past FIRE_RESULT_WINDOW
    # The 2026-11-01 burst's clock times, shifted past EMPTY_FIRES_SINCE.
    BURST = [(5, 43, 29), (5, 44, 42), (5, 45, 55), (6, 4, 12), (6, 5, 23), (6, 6, 37)]
    MINUTE = timedelta(minutes=1)

    def at(self, hour, minute, second=0, day=0):
        return (self.DAY + timedelta(days=day)).replace(hour=hour, minute=minute,
                                                        second=second)

    def doc(self, landed=None, unknown=()):
        """A verdict document with a cell for each fixture in `landed`
        ({fixture: [run times]}, as gates writes them) and one without
        `run_stamps_on_model` for each fixture in `unknown`. Any other
        scheduled fixture has no cell: known, with no run."""
        doc = {"roster_models": [MODEL], "skills": {}, "guidance": {}}
        for fixture in set(landed or {}) | set(unknown):
            skill = plan_week._fixture_subject(ROOT / "evals", fixture)[1]
            parts = fixture.split("/")
            times = sorted((landed or {}).get(fixture, []))
            row = {"fixture": parts[2] if len(parts) == 3 else None, "model": MODEL,
                   "class": "missing", "runs": {"with": [], "without": []},
                   "newest_on_model": stamp(times[-1]) if times else None,
                   "run_stamps_on_model": [stamp(t) for t in times]}
            if fixture in unknown:
                del row["run_stamps_on_model"]
            doc["skills"].setdefault(skill, {"cells": []})["cells"].append(row)
        return doc

    def counts(self, fires, now=None, doc=None, fixtures=None):
        """[(empty_fires, outage_fires)] per fixture, and the outage sweeps."""
        cells, outages = plan_week.eval_cells_and_outages(
            ROOT / "evals", doc or self.doc(), fires, now or self.LATER)
        return ([(one(cells, f)["empty_fires"], one(cells, f)["outage_fires"])
                 for f in fixtures or self.FIXTURES], outages)

    def test_the_november_first_burst_is_an_outage(self):
        fires = [fire(i, f, self.at(*clock))
                 for i, (f, clock) in enumerate(zip(self.FIXTURES, self.BURST))]
        got, outages = self.counts(fires)
        self.assertEqual(got, [(0, 1)] * 6)
        self.assertEqual(outages, [{"start": self.at(*self.BURST[0]), "fires": 6}])

    def test_three_cells_make_an_outage_and_two_do_not(self):
        three = self.FIXTURES[:3]
        fires = [fire(i, f, self.at(5, 10 * i)) for i, f in enumerate(three)]
        self.assertEqual(self.counts(fires, fixtures=three)[0], [(0, 1)] * 3)
        got, outages = self.counts(fires[:2], fixtures=three)
        self.assertEqual((got, outages), ([(1, 0), (1, 0), (0, 0)], []))

    def test_one_delivered_fire_makes_the_sweep_count(self):
        # Review C: three empties plus one fire that landed its run is a
        # sweep the routine could deliver in, so the empties are the fixtures'.
        four = self.FIXTURES[:4]
        fires = [fire(i, f, self.at(5, 10 * i)) for i, f in enumerate(four)]
        doc = self.doc({four[3]: [self.at(5, 40)]})
        got, outages = self.counts(fires, doc=doc, fixtures=four)
        self.assertEqual((got, outages), ([(1, 0), (1, 0), (1, 0), (0, 0)], []))

    def test_recovered_cells_leave_the_others_excused(self):
        # Review A1/A3: four of the six deliver in a later sweep. The burst's
        # fires stay empty (their runs fall outside its window), so the
        # burst stays an outage and the two leftovers stay excused.
        fires = [fire(i, f, self.at(*clock))
                 for i, (f, clock) in enumerate(zip(self.FIXTURES, self.BURST))]
        retried = self.FIXTURES[:4]
        fires += [fire(10 + i, f, self.at(5, 10 * i, day=1)) for i, f in enumerate(retried)]
        doc = self.doc({f: [self.at(5, 10 * i + 8, day=1)] for i, f in enumerate(retried)})
        got, outages = self.counts(fires, doc=doc)
        self.assertEqual(got, [(0, 0)] * 4 + [(0, 1)] * 2)
        self.assertEqual(len(outages), 1)

    def test_outage_after_outage_still_breaks_the_cells(self):
        three = self.FIXTURES[:3]

        def sweep(day, base):
            return [fire(base + i, f, self.at(5, 10 * i, day=day)) for i, f in enumerate(three)]
        twice = sweep(0, 0) + sweep(1, 10)
        self.assertEqual(self.counts(twice, fixtures=three)[0], [(1, 1)] * 3)
        thrice = twice + sweep(2, 20)
        cells, outages = plan_week.eval_cells_and_outages(ROOT / "evals", self.doc(), thrice,
                                                          self.LATER)
        mine = [one(cells, f) for f in three]
        self.assertEqual([(c["empty_fires"], c["outage_fires"]) for c in mine], [(2, 1)] * 3)
        self.assertEqual(len(outages), 3)
        _, work = plan_week.eval_items(ctx(mine), self.LATER)
        self.assertEqual(sorted(w["fixture"] for w in work if w["kind"] == "fixture-broken"),
                         sorted(three))

    def test_the_span_cap_splits_a_long_chain(self):
        four = self.FIXTURES[:4]
        # 50 minutes apart: one chain by gap, but the fourth is 150 minutes
        # after the first, past OUTAGE_SPAN.
        fires = [fire(i, f, self.at(5, 0) + 50 * i * self.MINUTE) for i, f in enumerate(four)]
        got, outages = self.counts(fires, fixtures=four)
        self.assertEqual(got, [(0, 1), (0, 1), (0, 1), (1, 0)])
        self.assertEqual(outages, [{"start": self.at(5, 0), "fires": 3}])

    def test_a_young_fire_leaves_the_sweep_undecided(self):
        three, now = self.FIXTURES[:3], self.at(12, 0)
        empties = [fire(i, f, now - timedelta(minutes=150 - 10 * i))
                   for i, f in enumerate(three)]
        self.assertEqual(self.counts(empties, now, fixtures=three)[0], [(0, 1)] * 3)
        young = fire(9, self.FIXTURES[3], now - timedelta(minutes=90))
        got, outages = self.counts(empties + [young], now, fixtures=self.FIXTURES[:4])
        self.assertEqual((got, outages), ([(0, 0)] * 4, []))

    def test_an_unknown_cells_fire_takes_no_part(self):
        three = self.FIXTURES[:3]
        fires = [fire(i, f, self.at(5, 10 * i)) for i, f in enumerate(three)]
        got, outages = self.counts(fires, doc=self.doc(unknown=[three[2]]), fixtures=three)
        self.assertEqual((got, outages), ([(1, 0), (1, 0), (0, 0)], []))

    def test_a_sweep_aging_out_of_retry_after_keeps_its_outage(self):
        three = self.FIXTURES[:3]
        t0 = self.at(5, 0)
        fires = [fire(i, f, t0 + 30 * i * self.MINUTE) for i, f in enumerate(three)]
        # The first fire is past RETRY_AFTER, the others are not: grouping
        # still sees it, so the sweep still covers three cells.
        now = t0 + plan_week.RETRY_AFTER + 10 * self.MINUTE
        got, outages = self.counts(fires, now, fixtures=three)
        self.assertEqual(got, [(0, 0), (0, 1), (0, 1)])
        self.assertEqual(len(outages), 1)

    def test_a_recent_outage_is_a_work_item_and_an_old_one_is_not(self):
        fires = [fire(i, f, self.at(*clock))
                 for i, (f, clock) in enumerate(zip(self.FIXTURES, self.BURST))]
        start = self.at(*self.BURST[0])
        for now, expected in ((start + timedelta(hours=3), 1),
                              (start + timedelta(hours=25), 0)):
            cells, outages = plan_week.eval_cells_and_outages(ROOT / "evals", self.doc(),
                                                              fires, now)
            _, work = plan_week.eval_items({**ctx(cells), "outages": outages}, now)
            items = [w for w in work if w["kind"] == "routine-outage"]
            with self.subTest(now=now):
                self.assertEqual(len(items), expected)
                if expected:
                    self.assertEqual(items[0], {"kind": "routine-outage", "change_type": None,
                                                "route": "issue",
                                                "sweep_start": "2026-11-05T05:43:29Z",
                                                "fires": 6})
                    lines = plan_week.summary_lines({"fires": [], "room": 0.5, "work": work,
                                                     "skills": {}})
                    self.assertIn("Work items: routine-outage 1", lines)

    def test_two_isolated_fires_on_one_fixture_still_break_it(self):
        fixture = self.FIXTURES[0]
        fires = [fire(1, fixture, self.at(5, 0)), fire(2, fixture, self.at(9, 0))]
        got, _ = self.counts(fires, fixtures=[fixture])
        self.assertEqual(got, [(2, 0)])


class FireSweepsTests(unittest.TestCase):
    """fire_sweeps' grouping, which #573's explorer reuses with span=None."""

    T0 = plan_week.EMPTY_FIRES_SINCE
    MINUTE = timedelta(minutes=1)

    def test_the_gap_is_inclusive(self):
        t0, minute = self.T0, self.MINUTE
        self.assertEqual(plan_week.fire_sweeps([t0 + 60 * minute, t0]),
                         [[t0, t0 + 60 * minute]])
        self.assertEqual(plan_week.fire_sweeps([t0, t0 + 61 * minute]),
                         [[t0], [t0 + 61 * minute]])

    def test_the_span_caps_a_sweep_from_its_first_start(self):
        t0, minute = self.T0, self.MINUTE
        chain = [t0 + 40 * i * minute for i in range(5)]  # 0, 40, 80, 120, 160
        self.assertEqual(plan_week.fire_sweeps(chain, span=timedelta(hours=2)),
                         [chain[:4], chain[4:]])

    def test_without_a_span_a_chain_has_no_limit(self):
        chain = [self.T0 + 50 * i * self.MINUTE for i in range(10)]  # 7.5 hours
        self.assertEqual(plan_week.fire_sweeps(chain), [chain])
        self.assertEqual(plan_week.fire_sweeps(chain, span=None), [chain])


if __name__ == "__main__":
    unittest.main()
