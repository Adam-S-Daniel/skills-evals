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
window, gates' `run_stamps_on_model`) or empty; each empty fire is judged
on its own window of OUTAGE_GAP either side (#583), and one with no
delivered or young fire there whose window's empties cover three cells is
an outage fire, excusing each cell's earliest, one per cell, so fixtures
broken together still go fixture-broken. While the routine is down (from
an outage fire until a paired eval fire delivers), the planner sends one
paired eval probe at a time, and probes never count (#583's circuit
breaker).

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


class OutageFixture:
    """Fixtures, clock and verdict-document helpers the outage tests share."""

    FIXTURES = ["evals/github-actions-sha-pinning", "evals/writing-adrs/bootstrap",
                "evals/disarm-inherited-reach", "evals/windows-elevation-from-wsl",
                "evals/embeddable-tool-pages", "evals/review-bash-ci-reliability/release-pipeline"]
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
            subject, ident = plan_week._fixture_subject(ROOT / "evals", fixture)
            parts = fixture.split("/")
            times = sorted((landed or {}).get(fixture, []))
            name = parts[3] if subject == "guidance" else parts[2] if len(parts) == 3 else None
            row = {"fixture": name, "model": MODEL,
                   "class": "missing", "runs": {"with": [], "without": []},
                   "newest_on_model": stamp(times[-1]) if times else None,
                   "run_stamps_on_model": [stamp(t) for t in times]}
            if fixture in unknown:
                del row["run_stamps_on_model"]
            half = "guidance" if subject == "guidance" else "skills"
            doc[half].setdefault(ident, {"cells": []})["cells"].append(row)
        return doc

    def counts(self, fires, now=None, doc=None, fixtures=None):
        """[(empty_fires, outage_fires)] per fixture, and the outages."""
        cells, outages, _ = plan_week.eval_cells_and_outages(
            ROOT / "evals", doc or self.doc(), fires, now or self.LATER)
        return ([(one(cells, f)["empty_fires"], one(cells, f)["outage_fires"])
                 for f in fixtures or self.FIXTURES], outages)

    def downs(self, fires, now=None, doc=None, fixtures=None):
        """[down_fires] per fixture."""
        cells, _, _ = plan_week.eval_cells_and_outages(
            ROOT / "evals", doc or self.doc(), fires, now or self.LATER)
        return [one(cells, f)["down_fires"] for f in fixtures or self.FIXTURES]


class OutageTests(OutageFixture, unittest.TestCase):
    """A routine outage empties every fire at once; that says nothing about fixtures."""

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

    def test_one_delivered_fire_makes_the_window_count(self):
        # Review C: three empties beside one fire that landed its run, inside
        # each one's window: the routine could deliver, so the empties are
        # the fixtures'.
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
        # The backstop: three fixtures that break together, while a healthy
        # cell delivers between their sweeps (so the routine is up again
        # each time and none of their fires is a down fire).
        three, healthy = self.FIXTURES[:3], self.FIXTURES[5]
        delivered = [self.at(12, 0, day=day) for day in range(3)]
        doc = self.doc({healthy: [t + 10 * self.MINUTE for t in delivered]})

        def sweep(day, base):
            return [fire(base + i, f, self.at(5, 10 * i, day=day)) for i, f in enumerate(three)] \
                + [fire(base + 9, healthy, delivered[day])]
        twice = sweep(0, 0) + sweep(1, 10)
        self.assertEqual(self.counts(twice, doc=doc, fixtures=three)[0], [(1, 1)] * 3)
        thrice = twice + sweep(2, 20)
        cells, outages, _ = plan_week.eval_cells_and_outages(ROOT / "evals", doc,
                                                             thrice, self.LATER)
        mine = [one(cells, f) for f in three]
        self.assertEqual([(c["empty_fires"], c["outage_fires"]) for c in mine], [(2, 1)] * 3)
        self.assertEqual(len(outages), 3)
        _, work = plan_week.eval_items(ctx(mine), self.LATER)
        self.assertEqual(sorted(w["fixture"] for w in work if w["kind"] == "fixture-broken"),
                         sorted(three))

    def test_a_long_chain_is_judged_fire_by_fire(self):
        # Was test_the_span_cap_splits_a_long_chain: the 2-hour span cap is
        # gone (#583). Four cells 50 minutes apart: the end fires' windows
        # hold two cells each, the middle two three, so the middle two are
        # outage fires; the chain absorbs the first (slow onset), which
        # opens the down span. The second and third,
        # outage fires PROBE_WAIT into the span, and the fourth, a counted
        # fire inside it, are down fires.
        four = self.FIXTURES[:4]
        fires = [fire(i, f, self.at(5, 0) + 50 * i * self.MINUTE) for i, f in enumerate(four)]
        got, outages = self.counts(fires, fixtures=four)
        self.assertEqual(got, [(0, 1), (0, 0), (0, 0), (0, 0)])
        self.assertEqual(self.downs(fires, fixtures=four), [0, 1, 1, 1])
        self.assertEqual(outages, [{"start": self.at(5, 0), "fires": 3}])

    def test_a_young_fire_leaves_the_window_undecided(self):
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

    def test_a_window_aging_out_of_retry_after_keeps_its_outage(self):
        three = self.FIXTURES[:3]
        t0 = self.at(5, 0)
        fires = [fire(i, f, t0 + 30 * i * self.MINUTE) for i, f in enumerate(three)]
        # The first fire is past RETRY_AFTER, the others are not: the fires
        # gathered reach OUTAGE_GAP further back, so their windows still
        # cover three cells.
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
            cells, outages, _ = plan_week.eval_cells_and_outages(ROOT / "evals", self.doc(),
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


class WindowTests(OutageFixture, unittest.TestCase):
    """#583's centered window: an outage's edges beside delivered fires,
    and verdicts that depend only on fires near them."""

    def burst(self, start, fixtures):
        """One empty fire per fixture, a minute apart from `start`."""
        return [fire(i, f, start + i * self.MINUTE) for i, f in enumerate(fixtures)]

    def test_an_outages_first_round_beside_an_earlier_delivered_fire(self):
        # Issue item 1. A delivered fire more than OUTAGE_GAP before the
        # first round leaves it excused; one at most OUTAGE_GAP before (the
        # window is inclusive) puts it in that round's window, so that round
        # is counted on the first pass; then the outage fire a minute later,
        # no delivery between, absorbs it (slow onset).
        burst, other, start = self.FIXTURES[:5], self.FIXTURES[5], self.at(6, 0)
        for gap, first in ((61, (0, 1)), (60, (0, 1))):
            delivered = start - gap * self.MINUTE
            fires = [fire(99, other, delivered)] + self.burst(start, burst)
            doc = self.doc({other: [delivered + 10 * self.MINUTE]})
            got, outages = self.counts(fires, doc=doc, fixtures=burst)
            with self.subTest(gap=gap):
                self.assertEqual(got, [first] + [(0, 1)] * 4)
                self.assertEqual(outages[0]["fires"], 5)

    def test_an_outages_last_round_beside_a_later_delivered_fire(self):
        burst, other, start = self.FIXTURES[:5], self.FIXTURES[5], self.at(6, 0)
        # A delivered fire inside the windows vetoes the outage only when it
        # started before the burst's first fire + PROBE_WAIT: a later one
        # may be the breaker's own probe and says nothing about the burst.
        for after, each in ((45, (0, 1)), (44, (1, 0))):
            delivered = start + after * self.MINUTE
            fires = self.burst(start, burst) + [fire(99, other, delivered)]
            doc = self.doc({other: [delivered + 10 * self.MINUTE]})
            got, _ = self.counts(fires, doc=doc, fixtures=burst)
            with self.subTest(after=after):
                self.assertEqual(got, [each] * 5)
                self.assertEqual(self.downs(fires, doc=doc, fixtures=burst), [0] * 5)

    def test_removing_an_early_fire_changes_no_later_verdict(self):
        # Issue item 2: under the 2-hour span, dropping a chain's first fire
        # moved every later sweep boundary. A 10-hour chain every 30
        # minutes over four cells, two delivered fires in it.
        t0, gap = self.at(5, 0), plan_week.OUTAGE_GAP
        fires = [(t0 + 30 * i * self.MINUTE, "delivered" if i in (9, 11) else "empty", i % 4)
                 for i in range(21)]
        since = t0 - timedelta(days=1)
        full = plan_week.judge_empty_fires(fires, since)
        self.assertEqual({"outage", "counted", None}, set(full))  # not vacuous
        for drop in (fires[0], fires[1]):
            cut = plan_week.judge_empty_fires([f for f in fires if f != drop], since)
            kept = [(f, v) for f, v in zip(fires, full) if f != drop]
            for (fire_, before), after in zip(kept, cut):
                if fire_[0] - drop[0] > gap:
                    with self.subTest(dropped=drop[0], fire=fire_[0]):
                        self.assertEqual(before, after)

    def test_an_issue_probe_beside_a_delivered_fire_still_counts(self):
        # The issue's probe (one fire delivered at 05:00, empties at
        # 05:30-05:34 on five cells) is inside each empty's window, so it
        # still counts: the ambiguity the window cannot remove.
        burst, other = self.FIXTURES[:5], self.FIXTURES[5]
        fires = [fire(99, other, self.at(5, 0))] + self.burst(self.at(5, 30), burst)
        doc = self.doc({other: [self.at(5, 10)]})
        got, outages = self.counts(fires, doc=doc, fixtures=burst)
        self.assertEqual((got, outages), ([(1, 0)] * 5, []))


def skill_ctx():
    """A skill improve_items makes an improve fire of."""
    return {"fixtures": 4, "holdout": "aaa", "registry_ok": True, "verdict": "keep",
            "pause": None, "evidence": {"headroom": 0.3, "pass_rate": None,
                                        "with_trials": 6, "targets": ["one:b"]}}


class BreakerTests(OutageFixture, unittest.TestCase):
    """#583's circuit breaker: while the routine is down a plan sends one
    paired eval probe at a time, none while a younger one may still land,
    probes never count, and a delivery reopens the queue."""

    BURST_AT = OutageFixture.DAY.replace(hour=5)
    CADENCE = timedelta(minutes=50)

    def plan(self, fires, now, doc=None, *, room=100.0, refresh=False, max_fires=10_000,
             edit=None):
        cells, outages, down = plan_week.eval_cells_and_outages(ROOT / "evals",
                                                                doc or self.doc(), fires, now)
        if edit:
            edit(cells)
        # Room for every cell, so the control shows each kind of fire.
        plan_ctx = {**ctx(cells), "room": room, "refresh": refresh, "improve_charge": 0.10,
                    "skills": {"writing-adrs": skill_ctx()}, "lessons": [],
                    "outages": outages, "routine_down": down,
                    "bare": [{"fixture": SKILL_FIXTURE, "model": MODEL, "skill": "writing-adrs"}]}
        return plan_week.build_plan(plan_ctx, now, max_fires=max_fires), cells, down

    def outage(self):
        return [fire(i, f, self.BURST_AT + i * self.MINUTE) for i, f in enumerate(self.FIXTURES)]

    def kinds(self, plan):
        return {(f["mode"], f["arms"]) for f in plan["fires"]}

    def only_six(self, cells):
        """Hold every cell but FIXTURES', so probes must come back to a cell."""
        for c in cells:
            c["schedulable"] = c["schedulable"] and c["fixture"] in self.FIXTURES

    def simulate(self, fires, start, hours, doc=None, max_fires=3):
        """Plan every CADENCE from `start` for `hours` over the six FIXTURES
        cells, every fire empty (no run lands): the fires sent, and the last
        plan's cells and plan."""
        now, end = start, start + timedelta(hours=hours)
        while now <= end:
            plan, cells, down = self.plan(fires, now, doc, max_fires=max_fires,
                                          edit=self.only_six)
            for f in plan["fires"]:
                self.assertEqual(f["mode"], "eval")
                if f["arms"] == "both":
                    fires.append(fire(1000 + len(fires), f["fixture"], now))
            now += self.CADENCE
        return fires, cells, plan

    def test_up_the_plan_sends_eval_improve_and_bare_fires(self):
        # The control: the same context before any outage plans all kinds.
        plan, _, down = self.plan([], self.BURST_AT)
        self.assertIsNone(down)
        self.assertFalse(plan["routine_down"])
        self.assertEqual(self.kinds(plan), {("eval", "both"), ("eval", "bare"), ("improve", "")})
        self.assertNotIn("Routine down", "\n".join(plan_week.summary_lines(plan)))
        self.assertNotIn("routine-down", {w["kind"] for w in plan["work"]})

    def test_a_burst_trips_the_breaker_by_the_next_plan(self):
        # Item 4: provisional, long before FIRE_RESULT_WINDOW decides a fire.
        fires = self.outage()
        early, _, down = self.plan(fires, self.BURST_AT + 30 * self.MINUTE)
        self.assertIsNone(down)  # younger than PROBE_WAIT: not yet
        plan, cells, down = self.plan(fires, self.BURST_AT + self.CADENCE)
        self.assertEqual(down, self.BURST_AT)
        self.assertTrue(plan["routine_down"])
        self.assertEqual(self.kinds(plan), {("eval", "both")})
        self.assertEqual(len(plan["fires"]), 1)
        # For the breaker only: nothing is counted yet.
        self.assertEqual({(c["empty_fires"], c["outage_fires"], c["down_fires"])
                          for c in cells}, {(0, 0, 0)})

    def test_a_healthy_sweep_never_trips(self):
        fires = self.outage()
        doc = self.doc({f: [self.BURST_AT + (i + 6) * self.MINUTE]
                        for i, f in enumerate(self.FIXTURES)})
        for minutes in (10, 50, 100, 150, 300):
            plan, _, down = self.plan(fires, self.BURST_AT + minutes * self.MINUTE, doc)
            with self.subTest(minutes=minutes):
                self.assertIsNone(down)
                self.assertGreater(len(plan["fires"]), 1)

    def test_a_few_slow_cells_beside_landed_runs_do_not_trip(self):
        # Two of six land nothing: a window of two stale cells is not three.
        fires = self.outage()
        doc = self.doc({f: [self.BURST_AT + 8 * self.MINUTE] for f in self.FIXTURES[2:]})
        _, _, down = self.plan(fires, self.BURST_AT + self.CADENCE, doc)
        self.assertIsNone(down)

    def test_probe_wait_cadence(self):
        probe_at = self.BURST_AT + timedelta(hours=2, minutes=10)
        fires = self.outage() + [fire(50, self.FIXTURES[0], probe_at)]
        self.assertEqual(plan_week.PROBE_WAIT, timedelta(minutes=45))
        for minutes, sent in ((30, 0), (44, 0), (45, 1), (50, 1)):
            plan, _, down = self.plan(fires, probe_at + minutes * self.MINUTE)
            with self.subTest(minutes=minutes):
                self.assertTrue(down)
                self.assertEqual(len(plan["fires"]), sent)
                if sent:  # never the cell whose probe may still land
                    self.assertNotEqual(plan["fires"][0]["fixture"], self.FIXTURES[0])
                else:
                    self.assertGreater(sum(plan["unplanned"].values()), 0)

    def test_the_routine_down_item_is_listed_while_down_only(self):
        fires = self.outage()
        plan, _, _ = self.plan(fires, self.BURST_AT + timedelta(hours=3))
        self.assertEqual(plan["work"][0], {"kind": "routine-down", "change_type": None,
                                           "route": "issue", "since": "2026-11-05T05:00:00Z"})
        self.assertIn("routine-outage", {w["kind"] for w in plan["work"]})
        self.assertIn("Routine down: probe only (until a paired eval fire on a known "
                      "cell delivers)", plan_week.summary_lines(plan))
        # A day later, past OUTAGE_REPORT_WINDOW, still down: routine-down
        # stays, routine-outage is gone.
        later, _, _ = self.plan(fires, self.BURST_AT + timedelta(hours=26))
        self.assertEqual([w["kind"] for w in later["work"]
                          if w["kind"].startswith("routine-")], ["routine-down"])
        up, _, _ = self.plan([], self.BURST_AT)
        self.assertNotIn("routine-down", {w["kind"] for w in up["work"]})

    def test_a_delivered_probe_reopens_the_queue(self):
        probe_at = self.BURST_AT + timedelta(hours=2, minutes=10)
        fires = self.outage() + [fire(50, self.FIXTURES[0], probe_at)]
        doc = self.doc({self.FIXTURES[0]: [probe_at + 20 * self.MINUTE]})
        # Still young, but its run is in; and once decided, delivered.
        for now in (probe_at + 30 * self.MINUTE, probe_at + 3 * timedelta(hours=1)):
            plan, _, down = self.plan(fires, now, doc=doc)
            with self.subTest(now=now):
                self.assertIsNone(down)
                self.assertGreater(len(plan["fires"]), 1)
                self.assertIn(("improve", ""), self.kinds(plan))
                self.assertNotIn("routine-down", {w["kind"] for w in plan["work"]})

    def test_an_empty_probe_keeps_it_down_and_never_counts(self):
        probe_at = self.BURST_AT + timedelta(hours=2, minutes=10)
        fires = self.outage() + [fire(50, self.FIXTURES[0], probe_at)]
        plan, cells, down = self.plan(fires, probe_at + 3 * timedelta(hours=1))
        self.assertTrue(down)
        self.assertEqual(len(plan["fires"]), 1)
        self.assertNotEqual(plan["fires"][0]["fixture"], self.FIXTURES[0])
        got = one(cells, self.FIXTURES[0])
        self.assertEqual((got["empty_fires"], got["outage_fires"], got["down_fires"]), (0, 1, 1))

    def test_no_outage_no_breaker(self):
        # Two cells empty together is not an outage, so nothing is held.
        fires = self.outage()[:2]
        plan, _, down = self.plan(fires, self.BURST_AT + timedelta(hours=3))
        self.assertIsNone(down)
        self.assertGreater(len(plan["fires"]), 1)

    def test_the_probe_is_a_paired_eval_fire_when_no_eval_band_has_one(self):
        # Every cell settled: the eval bands are empty, improve and bare are not.
        def settle(cells):
            for c in cells:
                c["class"] = "no-benefit"
        fires = self.outage()
        up, _, _ = self.plan([], self.BURST_AT, edit=settle)
        self.assertEqual(self.kinds(up), {("eval", "bare"), ("improve", "")})
        plan, _, down = self.plan(fires, self.BURST_AT + timedelta(hours=3), edit=settle)
        self.assertTrue(down)
        self.assertEqual([(f["mode"], f["arms"], f["band"]) for f in plan["fires"]],
                         [("eval", "both", "probe")])

    def test_a_stall_still_probes_a_settled_cell_and_a_delivery_clears_it(self):
        # Three empty cells, every other settled, one improve eligible.
        trio = self.FIXTURES[:3]

        def settle(cells):
            for c in cells:
                if c["fixture"] not in trio:
                    c["class"] = "no-benefit"
        fires = [fire(i, f, self.BURST_AT + i * self.MINUTE) for i, f in enumerate(trio)]
        now = self.BURST_AT + timedelta(hours=3)
        plan, _, down = self.plan(fires, now, edit=settle)
        self.assertTrue(down)
        self.assertEqual(len(plan["fires"]), 1)
        probe = plan["fires"][0]
        self.assertEqual((probe["mode"], probe["arms"], probe["band"]), ("eval", "both", "probe"))
        self.assertNotIn(probe["fixture"], trio)
        fires.append(fire(50, probe["fixture"], now))
        doc = self.doc({probe["fixture"]: [now + 9 * self.MINUTE]})
        after, _, down = self.plan(fires, now + 15 * self.MINUTE, doc, edit=settle)
        self.assertIsNone(down)
        self.assertIn(("improve", ""), self.kinds(after))
        self.assertTrue(set(trio) <= {f["fixture"] for f in after["fires"]})

    def test_room_below_the_head_candidates_cost_takes_the_next_that_fits(self):
        fires = self.outage()
        now = self.BURST_AT + timedelta(hours=3)
        head = next(c["fixture"] for c in self.plan(fires, now)[1]
                    if c["schedulable"] and c["fixture"] not in self.FIXTURES)

        def price(cells):
            # The head ranks first on its last fire (never), the dearest.
            for c in cells:
                c["usd_per_fire"] = 0.03 if c["fixture"] == head else 0.01
                if c["fixture"] != head:
                    c["last_fire"] = now - timedelta(days=1)

        def priced(room, refresh=False):
            cells, outages, down = plan_week.eval_cells_and_outages(ROOT / "evals", self.doc(),
                                                                    fires, now)
            price(cells)
            plan_ctx = {**ctx(cells), "points_per_usd": 1.0, "room": room, "refresh": refresh,
                        "improve_charge": 0.10, "skills": {}, "lessons": [],
                        "outages": outages, "routine_down": down}
            return plan_week.build_plan(plan_ctx, now)["fires"]
        self.assertEqual([f["fixture"] for f in priced(1.0)], [head])
        got = priced(0.02)
        self.assertEqual(len(got), 1)
        self.assertNotEqual(got[0]["fixture"], head)
        self.assertLessEqual(got[0]["cost"], 0.02)
        # Room for nothing: none, or with the guard's refresh at most one
        # fire of at most one reservation.
        self.assertEqual(priced(0.0), [])
        refreshed = priced(0.0, refresh=True)
        self.assertEqual(len(refreshed), 1)
        self.assertLessEqual(refreshed[0]["cost"], 0.035)
        self.assertEqual((refreshed[0]["mode"], refreshed[0]["arms"]), ("eval", "both"))

    def test_with_no_schedulable_cell_the_queue_is_not_held(self):
        def hold(cells):
            for c in cells:
                c["schedulable"] = False
        plan, _, down = self.plan(self.outage(), self.BURST_AT + timedelta(hours=3), edit=hold)
        self.assertTrue(down)
        self.assertFalse(plan["probe_only"])
        self.assertIn(("improve", ""), self.kinds(plan))
        self.assertIn("Routine down: no schedulable eval cell to probe, planned normally",
                      plan_week.summary_lines(plan))

    def test_back_to_back_outages_with_empty_probes_bench_no_cell(self):
        # The reviewer's replay: two outages a day apart, inside RETRY_AFTER,
        # each with a burst from the head of the band and empty probes.
        fires, _, _ = self.simulate([], self.BURST_AT, 6)
        # The routine comes back: one probe delivers.
        healthy = self.FIXTURES[5]
        back = self.BURST_AT + timedelta(hours=7)
        fires.append(fire(999, healthy, back))
        doc = self.doc({healthy: [back + 8 * self.MINUTE]})
        _, _, down = self.plan(fires, back + 20 * self.MINUTE, doc, edit=self.only_six)
        self.assertIsNone(down)
        fires, _, _ = self.simulate(fires, self.BURST_AT + timedelta(days=1), 6, doc)
        now = self.BURST_AT + timedelta(days=1, hours=9)
        plan, cells, _ = self.plan(fires, now, doc, max_fires=3, edit=self.only_six)
        self.assertEqual([w for w in plan["work"] if w["kind"] == "fixture-broken"], [])
        self.assertLessEqual(max(c["empty_fires"] for c in cells), 1)
        self.assertGreater(sum(c["down_fires"] for c in cells), 4)  # the probes, excused
        # Probes came back to cells: the rule, not a large pool, kept them unbenched.
        self.assertGreater(len(fires), 2 * len(self.FIXTURES))

    def test_an_outage_from_its_first_fire_benches_no_healthy_cell(self):
        # From the outage's first fire, a plan every 50 minutes, at most
        # three fires each, for ten hours, every fire empty.
        fires, cells, plan = self.simulate([], self.BURST_AT, 10)
        self.assertTrue(plan["routine_down"])
        first = [f for f in fires if plan_week.outcomes_mod.parse_time(f["run_started_at"])
                 == self.BURST_AT]
        self.assertEqual(len(first), 3)  # the burst, before anything is known
        self.assertGreaterEqual(len(fires) - 3, 10)  # then one probe a plan
        self.assertGreater(len(fires), len(self.FIXTURES))  # probes came back to cells
        self.assertLessEqual(max(c["empty_fires"] for c in cells), 1)
        self.assertEqual(sum(c["empty_fires"] for c in cells), 0)


    def test_a_probe_delivering_after_probe_wait_does_not_veto_its_burst(self):
        # Flapping: six healthy cells empty at 05:00-05:05, the breaker's
        # probe at 05:50 delivers, the six are fired again into a second
        # short outage at 07:10 whose probe delivers at 08:00. Each probe
        # sits in its own burst's window, after PROBE_WAIT: it says nothing
        # about the burst, so both bursts stay outages.
        fires = self.outage()
        plan, _, _ = self.plan(fires, self.BURST_AT + 50 * self.MINUTE)
        first = plan["fires"][0]["fixture"]
        fires.append(fire(77, first, self.BURST_AT + 50 * self.MINUTE))
        again = self.BURST_AT + timedelta(hours=2, minutes=10)
        fires += [fire(200 + i, f, again + i * self.MINUTE) for i, f in enumerate(self.FIXTURES)]
        landed = {first: [self.BURST_AT + 58 * self.MINUTE]}
        plan, _, _ = self.plan(fires, again + 50 * self.MINUTE, self.doc(landed))
        second = plan["fires"][0]["fixture"]
        fires.append(fire(300, second, again + 50 * self.MINUTE))
        landed.setdefault(second, []).append(again + 58 * self.MINUTE)
        plan, cells, _ = self.plan(fires, again + timedelta(hours=4), self.doc(landed))
        self.assertEqual([w for w in plan["work"] if w["kind"] == "fixture-broken"], [])
        six = [c for c in cells if c["fixture"] in self.FIXTURES]
        self.assertEqual([c["outage_fires"] for c in six], [1] * 6)

    def test_a_slow_onset_excuses_the_outages_leading_fire(self):
        # One fire per plan, 50 minutes apart, all empty: the first fire's
        # window holds two cells, so only the chain makes it an outage
        # fire. Then the routine flaps: one probe delivers and the next
        # outage starts slowly the same way, from the same head cell.
        fires, _, _ = self.simulate([], self.BURST_AT, 8, max_fires=1)
        head = fires[0]["display_title"].split()[-2]  # the slow onset's first cell
        healthy = self.FIXTURES[5]
        back = self.BURST_AT + timedelta(hours=8, minutes=20)
        fires.append(fire(999, healthy, back))
        doc = self.doc({healthy: [back + 8 * self.MINUTE]})
        fires, _, _ = self.simulate(fires, back + 50 * self.MINUTE, 6, doc, max_fires=1)
        plan, cells, _ = self.plan(fires, back + timedelta(hours=10), doc, max_fires=1,
                                   edit=self.only_six)
        self.assertEqual([w for w in plan["work"] if w["kind"] == "fixture-broken"], [])
        self.assertEqual(next(c for c in cells if c["fixture"] == head)["outage_fires"], 1)
        self.assertLessEqual(max(c["empty_fires"] for c in cells), 1)

class ConstantsTests(unittest.TestCase):
    """The outage rule's numbers, pinned by value: a change is a decision."""

    def test_the_constants(self):
        self.assertEqual(plan_week.OUTAGE_GAP, timedelta(minutes=60))
        self.assertEqual(plan_week.OUTAGE_CELLS, 3)
        self.assertEqual(plan_week.OUTAGE_EXCUSES, 1)
        self.assertEqual(plan_week.OUTAGE_REPORT_WINDOW, timedelta(hours=24))
        self.assertEqual(plan_week.FIRE_RESULT_WINDOW, timedelta(hours=2))
        self.assertEqual(plan_week.BROKEN_AFTER_FIRES, 2)
        self.assertEqual(plan_week.RETRY_AFTER, timedelta(days=14))
        self.assertEqual(plan_week.PROBE_WAIT, timedelta(minutes=45))


class FireSweepsTests(unittest.TestCase):
    """fire_sweeps' grouping, which chains the planner's outage fires and
    #573's explorer reuses."""

    T0 = plan_week.EMPTY_FIRES_SINCE
    MINUTE = timedelta(minutes=1)

    def test_the_gap_is_inclusive(self):
        t0, minute = self.T0, self.MINUTE
        self.assertEqual(plan_week.fire_sweeps([t0 + 60 * minute, t0]),
                         [[t0, t0 + 60 * minute]])
        self.assertEqual(plan_week.fire_sweeps([t0, t0 + 61 * minute]),
                         [[t0], [t0 + 61 * minute]])

    def test_a_chain_has_no_limit(self):
        # The span cap (and its parameter) is gone with #583: nothing called
        # it once outages stopped being judged by sweep.
        chain = [self.T0 + 50 * i * self.MINUTE for i in range(10)]  # 7.5 hours
        self.assertEqual(plan_week.fire_sweeps(chain), [chain])
        self.assertFalse(hasattr(plan_week, "OUTAGE_SPAN"))


if __name__ == "__main__":
    unittest.main()
