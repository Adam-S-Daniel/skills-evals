#!/usr/bin/env python3
"""G5/G6: the weekly planner (scripts/plan_week.py), improve outcomes
derived from existing evidence (scripts/improve_outcomes.py), and the
allowance guard's improve charge (thresholds doc, plumbing gap 2).

Hermetic: GitHub rows are recorded dicts, `now` is passed in, sleeps and
clocks are injected. Workflows are parsed with PyYAML.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import urllib.parse
import urllib.error
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import allowance_guard as guard  # noqa: E402
import improve_outcomes as io_mod  # noqa: E402
import compute_gates as plan_week_compute_gates  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402

NOW = datetime(2026, 10, 27, 7, 0, 0, tzinfo=timezone.utc)
LIMITS = {"weekly_cap": 0.30, "per_run_cap": 0.03, "per_run_overrun": 0.005,
          "stop_when_account_above": 0.80}


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fire(run_id, title, started, seconds=40, conclusion="success", status="completed"):
    """One row of the workflow runs API, as recorded."""
    return {"id": run_id, "display_title": title, "status": status,
            "conclusion": conclusion, "run_started_at": iso(started),
            "created_at": iso(started), "updated_at": iso(started + timedelta(seconds=seconds))}


def stamp(moment):
    return moment.strftime("%Y%m%dT%H%M%SZ") + "-abc123"


#: routine-eval-fire.yml's one conditional in `run-name`: ` bare` after an
#: eval mode whose `arms` is bare (ADR 0012, bare baseline addendum).
BARE_EXPRESSION = "${{ inputs.mode == 'eval' && inputs.arms == 'bare' && ' bare' || '' }}"
#: The trigger-only conditional (skills-evals#662).
TRIGGER_EXPRESSION = ("${{ inputs.mode == 'improve' && inputs.trigger_only == 'true' "
                      "&& ' trigger' || '' }}")
#: The description trim conditional (skills-evals#687).
TRIM_EXPRESSION = ("${{ inputs.mode == 'improve' && inputs.trim_description == 'true' "
                   "&& ' trim' || '' }}")


def render_title(template, **inputs):
    """The fire workflow's `run-name` as GitHub renders it for `inputs`:
    the bare, trigger and trim conditionals, then each `${{ inputs.<name> }}`."""
    bare = " bare" if inputs.get("mode") == "eval" and inputs.get("arms") == "bare" else ""
    trigger = (" trigger" if inputs.get("mode") == "improve"
               and inputs.get("trigger_only") == "true" else "")
    trim = (" trim" if inputs.get("mode") == "improve"
            and inputs.get("trim_description") == "true" else "")
    text = (template.replace(BARE_EXPRESSION, bare).replace(TRIGGER_EXPRESSION, trigger)
            .replace(TRIM_EXPRESSION, trim))
    return re.sub(r"\$\{\{ inputs\.(\w+) \}\}", lambda m: inputs.get(m.group(1), ""), text)


class TitleAndOutcomeTests(unittest.TestCase):

    def test_titles_parse_strictly(self):
        self.assertEqual(io_mod.parse_title("Fire eval routine: improve writing-adrs "),
                         {"mode": "improve", "target": "writing-adrs", "model": None,
                          "bare": False, "trigger": False, "trim": False})
        self.assertEqual(io_mod.parse_title(
            "Fire eval routine: eval evals/writing-adrs/bootstrap claude-opus-5-5"),
            {"mode": "eval", "target": "evals/writing-adrs/bootstrap",
             "model": "claude-opus-5-5", "bare": False, "trigger": False, "trim": False})
        self.assertEqual(io_mod.parse_title(
            "Fire eval routine: eval bare evals/writing-adrs/bootstrap claude-opus-5-5"),
            {"mode": "eval", "target": "evals/writing-adrs/bootstrap",
             "model": "claude-opus-5-5", "bare": True, "trigger": False, "trim": False})
        # A skill named `bare` is still a skill, not a marker.
        self.assertEqual(io_mod.parse_title("Fire eval routine: improve bare ")["target"],
                         "bare")
        for bad in ("Fire eval routine", "Fire eval routine: improve ",
                    "Fire eval routine: deploy x", "Fire eval routine: improve a;b",
                    "Fire eval routine: improve x y z", None, 3,
                    # ` bare` belongs to eval mode only.
                    "Fire eval routine: improve bare writing-adrs ",
                    "Fire eval routine: scaffold bare a__b__1 ",
                    "Fire eval routine: eval bare  ", "Fire eval routine: evalbare evals/x m"):
            self.assertIsNone(io_mod.parse_title(bad), bad)

    def test_the_fire_workflow_renders_the_title_the_parser_reads(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-fire.yml").read_text())
        template = doc["run-name"]
        self.assertIn(BARE_EXPRESSION, template)

        def render(**inputs):
            inputs.setdefault("arms", "both")
            return render_title(template, **inputs)
        self.assertNotIn("${{", render(mode="eval"))
        self.assertEqual(io_mod.parse_title(render(mode="improve", skill="writing-adrs")),
                         {"mode": "improve", "target": "writing-adrs", "model": None,
                          "bare": False, "trigger": False, "trim": False})
        self.assertEqual(io_mod.parse_title(render(mode="eval", fixture="evals/x",
                                                   model="claude-opus-5-5"))["model"],
                         "claude-opus-5-5")
        self.assertEqual(io_mod.parse_title(render(mode="scaffold", candidate="a__b__1"))["mode"],
                         "scaffold")
        self.assertEqual(io_mod.parse_title(render(mode="eval", arms="bare", fixture="evals/x",
                                                   model="claude-opus-5-5")),
                         {"mode": "eval", "target": "evals/x", "model": "claude-opus-5-5",
                          "bare": True, "trigger": False, "trim": False})
        for arms in ("with", "without"):
            self.assertFalse(io_mod.parse_title(render(mode="eval", arms=arms,
                                                       fixture="evals/x"))["bare"])
        # The workflow refuses bare outside eval mode; its title never says so.
        self.assertEqual(io_mod.parse_title(render(mode="improve", arms="bare",
                                                   skill="writing-adrs"))["bare"], False)

    def test_outcomes_from_fires_and_branches(self):
        t = NOW - timedelta(days=3)
        runs = [fire(1, "Fire eval routine: improve writing-adrs ", t),
                fire(2, "Fire eval routine: improve skills-doctor ", t + timedelta(hours=1)),
                fire(3, "Fire eval routine: improve writing-adrs ", t + timedelta(hours=2),
                     conclusion="failure"),
                fire(4, "Fire eval routine: improve writing-adrs ", NOW - timedelta(hours=1)),
                fire(5, "Fire eval routine: improve writing-adrs ", NOW - timedelta(minutes=1),
                     conclusion=None, status="in_progress"),
                fire(6, "Fire eval routine: eval evals/x claude-opus-5-5", t)]
        branches = [{"run_id": stamp(t + timedelta(seconds=10)), "skill": "writing-adrs"},
                    # A branch whose summary names another skill matches nothing.
                    {"run_id": stamp(t + timedelta(hours=1, seconds=5)), "skill": "other"},
                    {"run_id": "not-a-run-id", "skill": "skills-doctor"}]
        got = [(r["fire_run"], r["outcome"]) for r in io_mod.outcomes(runs, branches, NOW)]
        self.assertEqual(got, [(1, "accepted"), (2, "rejected"), (3, "fire-failed"),
                               (4, "pending"), (5, "pending")])

    def test_an_unreadable_branch_skill_matches_only_a_unique_span(self):
        t = NOW - timedelta(days=1)
        runs = [fire(1, "Fire eval routine: improve a ", t, seconds=120),
                fire(2, "Fire eval routine: improve b ", t + timedelta(seconds=30))]
        branch = [{"run_id": stamp(t + timedelta(seconds=40)), "skill": None}]
        self.assertEqual({r["outcome"] for r in io_mod.outcomes(runs, branch, NOW)},
                         {"rejected"})
        # Fire 2's span (plus slack) ends at t + 2m40s; fire 1's at t + 4m.
        branch = [{"run_id": stamp(t + timedelta(seconds=200)), "skill": None}]
        self.assertEqual([r["outcome"] for r in io_mod.outcomes(runs, branch, NOW)],
                         ["accepted", "rejected"])

    def test_a_window_past_the_api_cap_is_split_not_truncated(self):
        # 2,500 runs, one a minute; like the API, a query returns at most
        # 1,000 results however many pages it is asked for (2026-11-07).
        runs = [fire(i, "t", NOW - timedelta(minutes=i)) for i in range(2500)]
        since = NOW - timedelta(minutes=2499)

        def get(path, token, **kw):
            query = urllib.parse.parse_qs(path.split("?", 1)[1])
            created, page = query["created"][0], int(query["page"][0])
            if created.startswith(">="):
                lo, hi = io_mod.parse_time(created[2:]), None
            else:
                lo, hi = (io_mod.parse_time(x) for x in created.split(".."))
            hits = [r for r in runs if io_mod.parse_time(r["created_at"]) >= lo
                    and (hi is None or io_mod.parse_time(r["created_at"]) <= hi)][:1000]
            return {"workflow_runs": hits[(page - 1) * 100:page * 100]}
        got = io_mod.fetch_fire_runs("Adam-S-Daniel/skills-evals", "t", since,
                                     get=get, until=NOW)
        self.assertEqual(sorted(r["id"] for r in got), list(range(2500)))

    def test_fetchers_page_and_read_branch_summaries_as_data(self):
        pages = {1: [fire(i, "t", NOW) for i in range(100)], 2: [fire(100, "t", NOW)]}
        seen = []

        def get(path, token, **kw):
            seen.append(path)
            return {"workflow_runs": pages[int(path.rsplit("page=", 1)[1])]}
        self.assertEqual(len(io_mod.fetch_fire_runs("Adam-S-Daniel/skills-evals", "t",
                                                    NOW, get=get, until=NOW)), 101)
        self.assertIn("event=workflow_dispatch", seen[0])
        with self.assertRaises(io_mod.EvidenceError):
            io_mod.fetch_fire_runs("Adam-S-Daniel/skills-evals", "t", NOW,
                                   get=lambda p, t, **k: {"workflow_runs": [{}] * 100})
        good, evil = stamp(NOW), stamp(NOW - timedelta(hours=1))

        def refs(path, token, raw=False, cap=None):
            if "matching-refs" in path:
                return [{"ref": f"refs/heads/claude/eval-improve-{good}"},
                        {"ref": f"refs/heads/claude/eval-improve-{evil}"},
                        {"ref": "refs/heads/claude/eval-improve-junk"}]
            return (b'{"skill": "writing-adrs"}' if good in path
                    else b'{"skill": "$(rm -rf /)"}')
        self.assertEqual(io_mod.fetch_improve_branches("Adam-S-Daniel/skills-evals", "t", refs),
                         [{"run_id": good, "skill": "writing-adrs"},
                          {"run_id": evil, "skill": None}])

    def test_github_get_never_prints_a_body(self):
        def failing(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 502, "Bad", {},
                                         io.BytesIO(b"private-body-marker"))
        with self.assertRaises(io_mod.EvidenceError) as caught:
            io_mod.github_get("/x", "t", opener=failing)
        self.assertEqual(str(caught.exception), "the GitHub API answered 502")

        def missing(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 404, "No", {}, io.BytesIO(b""))
        self.assertIsNone(io_mod.github_get("/x", "t", opener=missing))


def measured_summary(run_dir: Path, delta: float, name="k/20261019T100000Z/with_skill"):
    path = run_dir / name / "summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"usage": {"meter_delta": {"windows": {"seven_day": {
        "delta": delta, "window_reset": False}}}, "invocation": name}}))


class GuardImproveChargeTests(unittest.TestCase):

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, ignore_errors=True)

    def test_unmeasured_history_charges_full_reservations(self):
        self.assertAlmostEqual(guard.eval_fire_cost(self.tree, LIMITS), 0.035)
        self.assertAlmostEqual(guard.improve_charge(self.tree, LIMITS),
                               guard.IMPROVE_FIRE_UNITS * 0.035)

    def test_measured_history_sets_the_charge(self):
        old = self.tree / "routine-results" / "20260901T000000Z-aaaaaa"
        measured_summary(old, 0.01)
        new = self.tree / "routine-results" / "20261026T000000Z-bbbbbb"
        measured_summary(new, 0.0)
        # (0.01 + 0.005 + 0.0 + 0.005) / 2 = 0.01 per eval run; eight units
        # since #572 (2026-11-02), twelve before.
        self.assertAlmostEqual(guard.eval_fire_cost(self.tree, LIMITS), 0.01)
        self.assertAlmostEqual(guard.improve_charge(self.tree, LIMITS), 0.08)

    def test_improve_fires_are_held_all_week_and_not_matched_to_runs(self):
        state = guard.account(self.tree, LIMITS, NOW, (3, 0), (2, 0))
        charge = guard.improve_charge(self.tree, LIMITS)
        # One eval fire without results, past the hold: the overrun only.
        self.assertAlmostEqual(state["pending"], 0.005 + 2 * charge)
        self.assertEqual(state["fires"], 1)
        self.assertIn("2 improve fire(s) held at", guard.describe(state))
        # Without the improve counts the same fires looked like cheap evals.
        self.assertAlmostEqual(guard.account(self.tree, LIMITS, NOW, (3, 0))["pending"], 0.015)

    def test_check_needs_room_for_the_improve_charge(self):
        # 2026-11-02 (#572): at eight units the charge is 0.28, so the old
        # 0.30 cap's refusal is kept at Adam's 0.25 goal.
        state = guard.account(self.tree, {**LIMITS, "weekly_cap": 0.25}, NOW, (0, 0))
        self.assertIsNone(guard.check(state, "eval"))
        # 0.28 > 0.25: the room refuses it; nothing is counted, so not the cap.
        self.assertEqual(guard.check(state, "improve"), guard.REFUSAL)
        roomy = dict(state, cap=0.50)
        self.assertIsNone(guard.check(roomy, "improve"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            budget_path = self.tree / "budget.yml"
            budget_path.write_text("weekly_cap: 0.25\nper_run_cap: 0.03\n"
                                   "per_run_overrun: 0.005\nstop_when_account_above: 0.80\n")
            code = guard.main(["check", "--results-tree", str(self.tree), "--mode", "improve",
                               "--budget", str(budget_path)],
                              now=NOW, fire_count=lambda now: (0, 0),
                              improve_count=lambda now: (0, 0))
        self.assertEqual(code, guard.REFUSED_EXIT)
        self.assertIn(guard.REFUSAL, out.getvalue())

    def test_improve_counts_read_titles(self):
        runs = [fire(1, "Fire eval routine: improve a ", NOW - timedelta(minutes=30)),
                fire(2, "Fire eval routine: improve a ", NOW - timedelta(days=3)),
                fire(3, "Fire eval routine: improve a ", NOW - timedelta(days=9)),
                fire(4, "Fire eval routine: improve a ", NOW, conclusion="failure"),
                fire(5, "Fire eval routine: eval evals/x m", NOW)]
        self.assertEqual(guard.improve_counts(runs, NOW), (2, 1))
        self.assertCountEqual(guard.improve_starts(runs, NOW),
                              [NOW - timedelta(minutes=30), NOW - timedelta(days=3)])


def rec(skill, outcome, at):
    return {"skill": skill, "fire_run": 1, "at": iso(at), "outcome": outcome, "run_id": None}


class PauseTests(unittest.TestCase):

    def pause(self, records=(), prs=(), on_hold=(), changed=None, remeasured=False):
        return plan_week.pause("writing-adrs", list(records), list(prs), list(on_hold),
                               NOW, changed, lambda moment: remeasured)

    def test_a_clean_skill_is_not_paused(self):
        self.assertIsNone(self.pause())

    def test_open_pr_on_hold_and_in_flight(self):
        self.assertIn("pull request is open", self.pause(prs=[{
            "skill": "writing-adrs", "state": "open", "created_at": iso(NOW),
            "closed_at": None, "merged_at": None}]))
        self.assertIn("on-hold", self.pause(on_hold=["Pause `writing-adrs` for now"]))
        self.assertIsNone(self.pause(on_hold=["writing-adrs-extra is held", None]))
        self.assertIn("in flight", self.pause([rec("writing-adrs", "pending", NOW)]))

    def test_a_rejection_cools_down_for_14_days(self):
        self.assertIn("cooling down", self.pause([rec("writing-adrs", "rejected",
                                                      NOW - timedelta(days=13))]))
        self.assertIsNone(self.pause([rec("writing-adrs", "rejected",
                                          NOW - timedelta(days=15))]))
        self.assertIsNone(self.pause([rec("other", "rejected", NOW)]))

    def test_three_rejections_stop_until_a_change_or_90_days(self):
        three = [rec("writing-adrs", "rejected", NOW - timedelta(days=d)) for d in (60, 40, 20)]
        self.assertIn("3 rejections in a row", self.pause(three))
        self.assertIsNone(self.pause(three, changed=NOW - timedelta(days=1)))
        self.assertIn("3 rejections", self.pause(three, changed=NOW - timedelta(days=30)))
        old = [rec("writing-adrs", "rejected", NOW - timedelta(days=d)) for d in (130, 110, 91)]
        self.assertIsNone(self.pause(old))
        # Failed fires between them do not break the streak.
        mixed = three[:2] + [rec("writing-adrs", "fire-failed", NOW - timedelta(days=30))] \
            + three[2:]
        self.assertIn("3 rejections", self.pause(mixed))

    def test_a_guidance_section_is_paused_by_its_own_records_and_prs(self):
        def srec(section, outcome, at):
            return {"section": section, "fire_run": 1, "at": iso(at), "outcome": outcome,
                    "run_id": None}

        def spause(records=(), prs=()):
            return plan_week.pause("sec", list(records), list(prs), [], NOW, None,
                                   lambda moment: False, key="section")
        open_pr = {"section": "sec", "state": "open", "created_at": iso(NOW),
                   "closed_at": None, "merged_at": None}
        self.assertIsNone(spause())
        self.assertIn("pull request is open", spause(prs=[open_pr]))
        self.assertIn("in flight", spause([srec("sec", "pending", NOW)]))
        self.assertIn("cooling down", spause([srec("sec", "rejected",
                                                   NOW - timedelta(days=3))]))
        three = [srec("sec", "rejected", NOW - timedelta(days=d)) for d in (60, 40, 20)]
        self.assertIn("3 rejections in a row", spause(three))
        self.assertIsNone(spause([srec("other", "pending", NOW)]))

    def test_the_guidance_lane_holds_one_guidance_edit_at_a_time(self):
        lane = plan_week.guidance_lane
        other_pr = {"section": "other", "state": "open"}
        self.assertIsNone(lane("sec", [], [], []))
        self.assertIsNone(lane("sec", [], [{**other_pr, "state": "closed"}], []))
        self.assertIn("another guidance-loop pull request", lane("sec", [], [other_pr], []))
        self.assertIn("another guidance-loop pull request", lane("sec", [], [], ["other"]))
        self.assertIn("removal pull request for it", lane("sec", [], [], ["sec"]))
        self.assertIn("another guidance-improve attempt",
                      lane("sec", [{"section": "other", "outcome": "pending"}], [], []))
        self.assertIsNone(lane("sec", [{"section": "other", "outcome": "rejected"}], [], []))

    def test_infrastructure_failures_retry_twice(self):
        two = [rec("writing-adrs", "fire-failed", NOW - timedelta(hours=h)) for h in (3, 2)]
        self.assertIsNone(self.pause(two))
        three = two + [rec("writing-adrs", "fire-failed", NOW - timedelta(hours=1))]
        self.assertIn("failed 3 times", self.pause(three))

    def test_after_a_merge_wait_for_the_with_arm(self):
        accepted = [rec("writing-adrs", "accepted", NOW - timedelta(days=5))]
        pr = {"skill": "writing-adrs", "state": "closed", "created_at": iso(NOW - timedelta(days=5)),
              "closed_at": iso(NOW - timedelta(days=4)),
              "merged_at": iso(NOW - timedelta(days=4))}
        self.assertIn("re-measured", self.pause(accepted, [pr]))
        self.assertIsNone(self.pause(accepted, [pr], remeasured=True))
        self.assertIn("no registry pull request", self.pause(accepted))
        closed = dict(pr, merged_at=None)
        self.assertIn("cooling down", self.pause(accepted, [closed]))


def trial(checks, infra=False):
    return {"scored": True, "infrastructure": infra, "errored": False, "checks": checks}


class TrainEvidenceTests(unittest.TestCase):

    def test_headroom_and_targets(self):
        with_trials = [trial({"a": True, "b": i % 2 == 0}) for i in range(6)]
        cells = {("one", "m"): {"with": [{"timestamp": "20261001T000000Z", "trials": with_trials}],
                                "without": []},
                 ("holdout", "m"): {"with": [{"timestamp": "x", "trials": [trial({"z": False})] * 9}],
                                    "without": []}}
        got = plan_week.train_evidence(cells, ["one"])
        self.assertEqual(got["with_trials"], 6)
        self.assertAlmostEqual(got["headroom"], 0.25)
        self.assertEqual(got["targets"], ["one:b"])
        # Five trials are too few; a check that never passed anywhere is broken.
        cells[("one", "m")]["with"][0]["trials"] = with_trials[:5]
        self.assertEqual(plan_week.train_evidence(cells, ["one"])["targets"], [])
        never = [trial({"a": True, "c": False}) for _ in range(6)]
        cells[("one", "m")]["with"][0]["trials"] = never
        self.assertEqual(plan_week.train_evidence(cells, ["one"])["targets"], [])
        cells[("one", "m")]["without"] = [{"timestamp": "x", "trials": [trial({"c": True})]}]
        self.assertEqual(plan_week.train_evidence(cells, ["one"])["targets"], ["one:c"])
        cells[("one", "m")]["with"][0]["trials"] = [trial({"c": False}, infra=True)] * 9
        self.assertIsNone(plan_week.train_evidence(cells, ["one"])["headroom"])

    def test_with_run_after(self):
        cells = {("a", "m"): {"with": [{"timestamp": "20261020T000000Z"}], "without": []}}
        self.assertTrue(plan_week.with_run_after(cells, NOW - timedelta(days=8)))
        self.assertFalse(plan_week.with_run_after(cells, NOW - timedelta(days=6)))


#: The gates document's policy block, as plan_week's context carries it. The
#: near band orders by run count alone (2026-10-31: no fixed looks), so the
#: planner reads no threshold from it.
POLICY = gates.load_gate_policy()["skills"]


def cell(fixture, model, cls, runs=0, newest=None, usd=None, empty=0, skill=None):
    return {"skill": skill or fixture.split("/")[1], "fixture": fixture, "model": model,
            "class": cls, "with_runs": runs, "without_runs": runs, "newest": newest,
            "usd_per_fire": usd, "empty_fires": empty}


def skill(fixtures=4, headroom=0.3, targets=("one:b",), verdict="keep", paused=None,
          registry_ok=True):
    return {"fixtures": fixtures, "holdout": "aaa" if fixtures >= 4 else "",
            "registry_ok": registry_ok, "verdict": verdict, "pause": paused,
            "evidence": {"headroom": headroom, "pass_rate": None, "with_trials": 6,
                         "targets": list(targets)}}


def ctx(**over):
    base = {"policy": POLICY, "reservation": 0.035, "overrun": 0.005,
            "improve_charge": 0.10, "room": 0.30, "points_per_usd": None,
            "model_weights": {"heavy": 0.9, "light": 0.1}, "removal_prs": [],
            "cells": [], "skills": {}, "lessons": []}
    base.update(over)
    return base


class BandTests(unittest.TestCase):

    def test_safety_first_then_minimum_shares_then_leftovers(self):
        cells = [cell(f"evals/m{i}", "heavy", "missing") for i in range(8)] \
            + [cell(f"evals/n{i}", "heavy", "insufficient", runs=4 - i % 3) for i in range(6)] \
            + [cell("evals/r0", "heavy", "benefit", runs=9, newest="20260801T000000Z")] \
            + [cell("evals/r1", "heavy", "benefit", runs=9, newest="20261020T000000Z")] \
            + [cell("evals/s0/x", "light", "benefit", runs=9, skill="gone")]
        plan = plan_week.build_plan(ctx(cells=cells, removal_prs=["gone"], room=1.0,
                                        skills={"writing-adrs": skill()}), NOW)
        bands = [f["band"] for f in plan["fires"]]
        self.assertEqual(bands[0], "safety")
        self.assertEqual(bands[-1], "improve")
        self.assertEqual(plan["fires"][-1]["mode"], "improve")
        self.assertEqual(plan["fires"][-1]["holdout"], "aaa")
        self.assertEqual(plan["fires"][-1]["change_type"], "skill-edit")
        # 1.0 - 0.035 safety = 0.965: missing gets at least 30% (8 x 0.035 =
        # 0.28 fits), near 20% (5 of 6), improve 20% (one 0.10 fire), and the
        # rest goes in band order: the sixth near cell, then the old re-check.
        self.assertEqual(bands.count("missing"), 8)
        self.assertEqual(bands.count("near"), 6)
        self.assertEqual(bands.count("improve"), 1)
        self.assertEqual(bands.count("recheck"), 1)
        self.assertNotIn("evals/r1", [f["fixture"] for f in plan["fires"]])
        self.assertLessEqual(sum(f["cost"] for f in plan["fires"]), 1.0 + 1e-9)
        near = [f["fixture"] for f in plan["fires"] if f["band"] == "near"]
        # Fewest runs lead: any run can decide a cell, and the cells with
        # the least evidence gain the most from one.
        self.assertEqual(near, ["evals/n2", "evals/n5", "evals/n1", "evals/n4",
                                "evals/n0", "evals/n3"])
        self.assertEqual(plan["matrix"]["include"][0]["eval_key"], "s0/x")

    def test_a_tight_room_still_reserves_each_band_its_share(self):
        cells = [cell(f"evals/m{i}", "heavy", "missing") for i in range(20)] \
            + [cell(f"evals/n{i}", "heavy", "insufficient", runs=2) for i in range(20)]
        plan = plan_week.build_plan(ctx(cells=cells, room=0.35), NOW)
        bands = [f["band"] for f in plan["fires"]]
        # 30% of 0.35 holds 3 missing fires, 20% holds 2 near; the rest (0.175,
        # 5 fires) goes to missing first.
        self.assertEqual(bands.count("near"), 2)
        self.assertEqual(bands.count("missing"), 8)

    def test_no_room_plans_one_refresh_eval_fire_when_the_guard_allows_it(self):
        # 2026-11-01: a stale reading left room at -18.6 points; the guard
        # allowed one refresh fire, but the planner planned none, so the loop
        # sat idle with no newer reading coming.
        cells = [cell(f"evals/m{i}", "heavy", "missing") for i in range(3)]
        plan = plan_week.build_plan(ctx(cells=cells, room=-0.186, refresh=True,
                                        skills={"writing-adrs": skill()}), NOW)
        self.assertEqual(len(plan["fires"]), 1)
        self.assertEqual(plan["fires"][0]["mode"], "eval")
        self.assertEqual(plan["fires"][0]["fixture"], "evals/m0")
        self.assertEqual(plan["unplanned"]["missing"], 2)

    def test_no_refresh_fire_without_the_guards_leave_or_when_fires_fit(self):
        cells = [cell(f"evals/m{i}", "heavy", "missing") for i in range(3)]
        self.assertEqual(plan_week.build_plan(ctx(cells=cells, room=-0.186), NOW)["fires"], [])
        roomy = plan_week.build_plan(ctx(cells=cells, room=1.0, refresh=True), NOW)
        self.assertEqual(len(roomy["fires"]), 3)

    def test_near_cells_go_fewest_runs_first_then_heaviest_model(self):
        # No `_next_look` (2026-10-31): the order is the smaller arm's run
        # count, then model weight.
        lopsided = {**cell("evals/c", "heavy", "insufficient", runs=1), "with_runs": 9}
        cells = [cell("evals/a", "light", "insufficient", runs=3),
                 cell("evals/a", "heavy", "insufficient", runs=3),
                 cell("evals/b", "light", "insufficient", runs=1), lopsided]
        plan = plan_week.build_plan(ctx(cells=cells, room=1.0), NOW)
        self.assertEqual([(f["fixture"], f["model"]) for f in plan["fires"]
                          if f["band"] == "near"],
                         [("evals/c", "heavy"), ("evals/b", "light"),
                          ("evals/a", "heavy"), ("evals/a", "light")])

    def test_missing_cells_go_heaviest_model_first_and_broken_ones_leave(self):
        cells = [cell("evals/a", "light", "missing"), cell("evals/a", "heavy", "missing"),
                 cell("evals/b", "heavy", "missing", empty=2)]
        plan = plan_week.build_plan(ctx(cells=cells), NOW)
        self.assertEqual([(f["fixture"], f["model"]) for f in plan["fires"]],
                         [("evals/a", "heavy"), ("evals/a", "light")])
        self.assertEqual(plan["work"], [{"kind": "fixture-broken", "change_type": "fixture",
                                         "skill": "b", "fixture": "evals/b",
                                         "model": "heavy", "route": "issue"}])

    def test_a_kept_subject_plans_no_missing_or_near_fire(self):
        # 2026-10-31: one confident benefit keeps it; more runs cannot
        # change that until the re-check.
        old = "20260801T000000Z"
        kept = [{**cell("evals/k/a", "heavy", "missing", skill="k"), "verdict": "keep"},
                {**cell("evals/k/b", "light", "insufficient", runs=2, skill="k"),
                 "verdict": "keep"},
                {**cell("evals/k/c", "heavy", "benefit", runs=3, newest=old, skill="k"),
                 "verdict": "keep"},
                {**cell("evals/g", "heavy", "insufficient", runs=1, skill=""),
                 "section": "sec", "verdict": "keep"}]
        open_ = [{**cell("evals/o", "heavy", "insufficient", runs=1), "verdict": "insufficient"}]
        plan = plan_week.build_plan(ctx(cells=kept + open_, room=1.0), NOW)
        self.assertEqual([(f["fixture"], f["band"]) for f in plan["fires"]],
                         [("evals/o", "near"), ("evals/k/c", "recheck")])
        # A kept skill with an open removal pull request still gets safety.
        plan = plan_week.build_plan(ctx(cells=kept[:1], removal_prs=["k"], room=1.0), NOW)
        self.assertEqual([f["band"] for f in plan["fires"]], ["safety"])

    def test_a_kept_subject_with_an_unsettled_cell_is_still_rechecked(self):
        # A keep is not forever: an old enough unsettled cell of a kept
        # subject comes back in the recheck band, a recent one does not.
        old, recent = "20260801T000000Z", "20261020T000000Z"
        cells = [{**cell("evals/k/a", "heavy", "insufficient", runs=1, newest=old, skill="k"),
                  "verdict": "keep"},
                 {**cell("evals/r/a", "heavy", "insufficient", runs=1, newest=recent,
                         skill="r"), "verdict": "keep"}]
        plan = plan_week.build_plan(ctx(cells=cells, room=1.0), NOW)
        self.assertEqual([(f["fixture"], f["band"]) for f in plan["fires"]],
                         [("evals/k/a", "recheck")])

    def test_the_cheaper_model_goes_first(self):
        priced = [{**cell("evals/a", "heavy", "insufficient", runs=1), "usd_per_arm_trial": 0.33},
                  {**cell("evals/a", "light", "insufficient", runs=1), "usd_per_arm_trial": 0.11},
                  {**cell("evals/b", "heavy", "missing"), "usd_per_arm_trial": None},
                  {**cell("evals/b", "light", "missing"), "usd_per_arm_trial": None},
                  {**cell("evals/c", "other", "missing")}]
        self.assertEqual(plan_week.model_costs(priced), {"heavy": 0.33, "light": 0.11})
        plan = plan_week.build_plan(ctx(cells=priced, room=1.0), NOW)
        order = [(f["fixture"], f["model"]) for f in plan["fires"]]
        # Within a fixture, the dearer model waits while the cheaper model's
        # cell is open (2026-11-03): only light fires on evals/a and evals/b
        # (the costs are per model). A model with no known cost and no
        # cheaper cell beside it is not held, and goes after the priced ones.
        self.assertEqual(sorted(order), [("evals/a", "light"), ("evals/b", "light"),
                                         ("evals/c", "other")])
        self.assertLess(order.index(("evals/b", "light")), order.index(("evals/c", "other")))
        self.assertEqual(plan_week.cheaper_first(priced, plan_week.model_costs(priced)),
                         {id(priced[0]), id(priced[2])})
        # With no cost known for either model, neither waits.
        unpriced = [cell("evals/b", "heavy", "missing"), cell("evals/b", "light", "missing")]
        self.assertEqual(plan_week.cheaper_first(unpriced, {}), set())

    def test_the_dearer_model_fires_once_the_cheaper_cell_did_not_keep(self):
        # The cheaper cell decided without a keep (no benefit, a ceiling, a
        # cap): the dearer model's cell is free to fire.
        for decided in ("no-benefit", "no-clear-effect", "ceiling"):
            with self.subTest(decided=decided):
                priced = [{**cell("evals/a", "heavy", "insufficient", runs=1),
                           "usd_per_arm_trial": 0.33},
                          {**cell("evals/a", "light", decided, runs=20),
                           "usd_per_arm_trial": 0.11}]
                plan = plan_week.build_plan(ctx(cells=priced, room=1.0), NOW)
                self.assertIn(("evals/a", "heavy"),
                              [(f["fixture"], f["model"]) for f in plan["fires"]])
        # So is one whose cheaper cell's fires keep coming back empty.
        priced = [{**cell("evals/a", "heavy", "insufficient", runs=1), "usd_per_arm_trial": 0.33},
                  {**cell("evals/a", "light", "missing"), "usd_per_arm_trial": 0.11,
                   "empty_fires": plan_week.BROKEN_AFTER_FIRES}]
        self.assertEqual(plan_week.cheaper_first(priced, plan_week.model_costs(priced)), set())

    def test_a_stuck_cheaper_cell_does_not_starve_the_dearer_one(self):
        # Round 1's M3 starvation repro: the cheaper cell is open but more
        # runs cannot move it (an errored-trial block, a cannot-discriminate
        # cell), or it already has CHEAPER_FIRST_MAX_PAIRS pairs without a
        # decision. The dearer cell fires; it is not held behind it.
        errored = ("no-benefit on the numbers, but the cell has 1 agent-errored "
                   "trial(s) or a run skipped as anomalous, so it cannot retire")
        stuck = [{"class": "insufficient", "reason": errored},
                 {"class": "insufficient", "reason": "neither test has rejected yet",
                  "pairs": plan_week.CHEAPER_FIRST_MAX_PAIRS},
                 {"class": "cannot-discriminate"}]
        for blocker in stuck:
            with self.subTest(blocker=blocker):
                priced = [{**cell("evals/a", "heavy", "insufficient", runs=1),
                           "usd_per_arm_trial": 1.0,
                           "reason": "neither test has rejected yet"},
                          {**cell("evals/a", "light", "missing", runs=3),
                           **blocker, "usd_per_arm_trial": 0.1}]
                self.assertEqual(
                    plan_week.cheaper_first(priced, plan_week.model_costs(priced)), set())
        # The bound is 10 pairs, a literal (round 2: a test that read the
        # constant let any value pass): at 9 the cheaper cell still holds.
        for pairs, held in ((9, True), (10, False)):
            priced = [{**cell("evals/a", "heavy", "insufficient", runs=1),
                       "usd_per_arm_trial": 1.0},
                      {**cell("evals/a", "light", "insufficient", runs=3),
                       "usd_per_arm_trial": 0.1, "reason": "neither test has rejected yet",
                       "pairs": pairs}]
            self.assertEqual(plan_week.cheaper_first(priced, plan_week.model_costs(priced)),
                             {id(priced[0])} if held else set(), pairs)

    def test_historical_cost_is_clamped_and_breaks_ties(self):
        c = ctx(points_per_usd=0.01)
        self.assertAlmostEqual(plan_week.fire_cost({"usd_per_fire": 2.0}, c), 0.02)
        self.assertAlmostEqual(plan_week.fire_cost({"usd_per_fire": 100.0}, c), 0.035)
        self.assertAlmostEqual(plan_week.fire_cost({"usd_per_fire": 0.0}, c), 0.005)
        self.assertAlmostEqual(plan_week.fire_cost({"usd_per_fire": None}, c), 0.035)
        cells = [cell("evals/a", "heavy", "missing", usd=3.0),
                 cell("evals/b", "heavy", "missing", usd=1.0)]
        plan = plan_week.build_plan(ctx(cells=cells, points_per_usd=0.01), NOW)
        self.assertEqual([f["fixture"] for f in plan["fires"]], ["evals/b", "evals/a"])

    def test_max_fires_caps_the_plan(self):
        cells = [cell(f"evals/m{i}", "heavy", "missing") for i in range(40)]
        plan = plan_week.build_plan(ctx(cells=cells, room=10.0), NOW, max_fires=30)
        self.assertEqual(len(plan["fires"]), 30)
        self.assertEqual(plan["unplanned"]["missing"], 10)

    def test_improve_eligibility_and_needs_fixtures(self):
        skills = {"ok": skill(), "few": skill(fixtures=2, headroom=0.5),
                  "few-flat": skill(fixtures=1, headroom=0.05),
                  "flat": skill(headroom=0.05), "aimless": skill(targets=()),
                  "retiring": skill(verdict="retire-pending"),
                  "paused": skill(paused="cooling down after a rejection"),
                  "private": skill(registry_ok=False)}
        plan = plan_week.build_plan(ctx(skills=skills, room=1.0), NOW)
        self.assertEqual([f["skill"] for f in plan["fires"]], ["ok"])
        self.assertEqual(sorted((w["kind"], w["skill"], w["change_type"]) for w in plan["work"]),
                         [("needs-fixtures", "few", "fixture"),
                          ("needs-harder-fixtures", "few-flat", "fixture"),
                          ("needs-harder-fixtures", "flat", "fixture")])
        status = plan["skills"]
        self.assertEqual(status["paused"]["reasons"], ["cooling down after a rejection"])
        self.assertIn("owned by retirement (retire-pending)", status["retiring"]["reasons"])
        self.assertIn("no failing check to target", status["aimless"]["reasons"])
        self.assertIn("no train headroom", status["flat"]["reasons"])

    def test_a_skill_above_ninety_percent_wants_harder_fixtures_not_an_edit(self):
        skills = {"high": skill(headroom=0.05), "eligible": skill(headroom=0.3),
                  "retiring": skill(headroom=0.05, verdict="retire"),
                  "private": skill(headroom=0.05, registry_ok=False)}
        plan = plan_week.build_plan(ctx(skills=skills, room=1.0), NOW)
        self.assertEqual([f["skill"] for f in plan["fires"]], ["eligible"])
        self.assertEqual(plan["work"], [{
            "kind": "needs-harder-fixtures", "change_type": "fixture", "skill": "high",
            "fixtures": 4, "headroom": 0.05, "route": "issue"}])

    def test_skill_usage_weight_orders_improvements_unknown_is_neutral(self):
        skills = {"a": skill(headroom=0.5), "b": skill(headroom=0.3), "c": skill(headroom=0.2),
                  "d": skill(fixtures=1, headroom=0.9), "e": skill(fixtures=1, headroom=0.4)}
        weights = {"a": 1.0, "b": None, "c": 50.0, "d": None, "e": 10.0}
        plan = plan_week.build_plan(ctx(skills=skills, room=1.0, improve_charge=0.01,
                                        skill_weights=weights), NOW)
        # Known 1, 10, 50: the neutral weight is their median, 10, never 0.
        self.assertEqual([f["skill"] for f in plan["fires"]], ["c", "b", "a"])
        self.assertEqual([w["skill"] for w in plan["work"]], ["d", "e"])
        self.assertEqual(plan_week.neutral_weights({"x": None}), {"x": 1.0})
        self.assertEqual(plan_week.neutral_weights({"x": None, "y": 0, "z": 0, "w": 4}),
                         {"x": 4, "y": 0, "z": 0, "w": 4})

    def test_skill_weights_use_the_usage_module_or_stay_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            with mock.patch.dict(sys.modules, {"skill_usage": None}):
                self.assertEqual(plan_week.skill_weights(tree, ["a"], NOW), {"a": None})
            seen = []
            fake = mock.Mock()
            fake.load.side_effect = lambda path: seen.append(path) or {"doc": 1}
            fake.weight.side_effect = lambda doc, skill, now: {"a": 7, "b": 0}.get(skill)
            with mock.patch.dict(sys.modules, {"skill_usage": fake}):
                self.assertEqual(plan_week.skill_weights(tree, ["a", "b", "c"], NOW),
                                 {"a": 7, "b": 0, "c": None})
            self.assertEqual(seen, [tree / "usage" / "weekly-local.json"])

    def test_a_private_skill_weight_is_unknown_never_zero(self):
        import skill_usage
        doc = skill_usage.document([], NOW, NOW - timedelta(days=14), 50)
        with tempfile.TemporaryDirectory() as tmp:
            tree, evals = Path(tmp) / "tree", Path(tmp) / "evals"
            (tree / "usage").mkdir(parents=True)
            (tree / "usage" / "weekly-local.json").write_text(json.dumps(doc), encoding="utf-8")
            for name, url in (("zz-private-skill", plan_week.PRIVATE_REGISTRY_URL),
                              ("zz-public-skill", plan_week.REGISTRY_URL)):
                (evals / name).mkdir(parents=True)
                (evals / name / "fixture.yaml").write_text(
                    f"skill: {name}\nregistry: {url}\n", encoding="utf-8")
            private = plan_week.private_skills(evals)
            self.assertEqual(private, {"zz-private-skill"})
            self.assertEqual(
                plan_week.skill_weights(tree, ["zz-private-skill", "zz-public-skill"], NOW,
                                        private),
                {"zz-private-skill": None, "zz-public-skill": 0})


CHECKLIST_SKILL = """---
name: example-checks
description: Rules: never do x.
---

# Example checks

Intro line.

## Checklist

### 1. Pipes

```bash
# not a heading: inside a fence
cmd | tail
```

- Never pipe a watch into tail.
- Always read PIPESTATUS.
"""

PROSE_SKILL = """---
name: example-prose
description: Write things.
---

# Example prose

Read the room first, then decide.

## How to write

Open with the point.
Say why it matters.
Close with the next step.

## Rules

- Keep it short.
"""


class TriggerLaneTests(unittest.TestCase):
    """Skills that almost never trigger (usage tracking, 2026-10-26): a
    trigger-only improve fire when a reviewed trigger set exists
    (skills-evals#662), a fixture item to write one when not, and hook
    candidates in the summary."""

    @staticmethod
    def triggers(**sets):
        return {name: {"trigger_set": has, "hook_candidate": name == "rules"}
                for name, has in sets.items()}

    def test_fresh_near_zero_usage_gets_a_trigger_fire_or_item_unknown_gets_none(self):
        triggers = self.triggers(quiet=True, silent=False, rules=False, unknown=True,
                                 busy=True, retiring=True)
        weights = {"quiet": 1, "silent": 0, "rules": 0, "unknown": None, "busy": 2,
                   "retiring": 0}
        skills = {"few": skill(fixtures=2), "retiring": skill(verdict="retire")}
        plan = plan_week.build_plan(ctx(skills=skills, triggers=triggers,
                                        skill_weights=weights, room=1.0,
                                        cells=[cell("evals/b", "heavy", "missing", empty=2)]),
                                    NOW)
        got = [(w["kind"], w["skill"], w["change_type"], w.get("route")) for w in plan["work"]]
        self.assertEqual(got, [
            ("needs-trigger-set", "rules", "fixture", "issue"),
            ("needs-trigger-set", "silent", "fixture", "issue"),
            ("needs-fixtures", "few", "fixture", "issue"),
            ("fixture-broken", "b", "fixture", "issue")])
        self.assertEqual(plan["work"][1]["trigger_set"], "evals/silent/trigger-eval-set.json")
        self.assertTrue(plan["work"][0]["hook_candidate"])
        [trigger] = [f for f in plan["fires"] if f["mode"] == "improve"]
        self.assertEqual({k: trigger[k] for k in ("band", "skill", "holdout", "trigger_only",
                                                  "change_type", "cost", "value")},
                         {"band": "improve", "skill": "quiet", "holdout": "",
                          "trigger_only": "true", "change_type": "trigger", "cost": 0.10,
                          "value": None})
        leg = next(r for r in plan["matrix"]["include"] if r["mode"] == "improve")
        self.assertEqual((leg["skill"], leg["holdout"], leg["trigger_only"]),
                         ("quiet", "", "true"))
        self.assertTrue(all(r["trigger_only"] == "false" for r in plan["matrix"]["include"]
                            if r["mode"] != "improve"))
        # Every skill with a known weight is judged; an unknown one is not.
        self.assertEqual(sorted(plan["triggers"]),
                         ["busy", "quiet", "retiring", "rules", "silent"])
        self.assertEqual(plan["triggers"]["quiet"], {"eligible": True, "reasons": [],
                                                     "weight": 1})
        self.assertFalse(plan["triggers"]["busy"]["eligible"])
        self.assertEqual(plan["triggers"]["retiring"]["reasons"],
                         ["owned by retirement (retire)"])
        self.assertEqual(plan["triggers"]["silent"]["reasons"], ["no reviewed trigger set yet"])
        self.assertEqual(plan["hook_candidates"], ["rules"])
        lines = "\n".join(plan_week.summary_lines(plan))
        self.assertIn("Hook candidates (mostly checklist or rules sections): rules", lines)
        self.assertIn("improve quiet (trigger only)", lines)
        self.assertIn("Trigger-only eligible skills: quiet", lines)
        self.assertIn("needs-trigger-set 2", lines)

    def test_no_trigger_fire_when_paused_private_or_already_improving(self):
        weights = {"t": 0}
        cases = {
            "paused": (dict(triggers={"t": {"trigger_set": True, "hook_candidate": False,
                                            "pause": "cooling down after a rejection"}}),
                       ["cooling down after a rejection"]),
            # An ordinary improve fire of the same skill would share its branch.
            "improving": (dict(triggers=self.triggers(t=True), skills={"t": skill()}),
                          ["an ordinary improve fire is planned for it"]),
        }
        for name, (over, reasons) in cases.items():
            with self.subTest(name=name):
                plan = plan_week.build_plan(ctx(skill_weights=weights, room=1.0, **over), NOW)
                self.assertFalse([f for f in plan["fires"] if f["trigger_only"] == "true"])
                self.assertEqual(plan["triggers"]["t"]["reasons"], reasons)
                self.assertFalse([w for w in plan["work"] if w["kind"] == "needs-trigger-set"])
        # A private skill is never judged, so never named.
        plan = plan_week.build_plan(ctx(skill_weights=weights, room=1.0,
                                        triggers=self.triggers(t=True, u=False),
                                        private_skills=frozenset({"t", "u"})), NOW)
        self.assertEqual((plan["fires"], plan["work"], plan["triggers"]), ([], [], {}))

    def test_trigger_fires_follow_improve_fires_least_used_first_under_the_cap(self):
        plan = plan_week.build_plan(ctx(
            skills={"a": skill()}, triggers=self.triggers(x=True, y=True),
            skill_weights={"a": 0.5, "x": 1, "y": 0}, improve_charge=0.06, room=1.0), NOW)
        self.assertEqual([(f["skill"], f["trigger_only"]) for f in plan["fires"]],
                         [("a", "false"), ("y", "true"), ("x", "true")])
        # The improve cap counts trigger fires as improve fires: one left.
        capped = plan_week.build_plan(ctx(
            triggers=self.triggers(x=True, y=True), skill_weights={"x": 1, "y": 0},
            improve_charge=0.06, room=1.0,
            improve_state=ImproveCapPlanTests.cap_state()), NOW)
        self.assertEqual([f["skill"] for f in capped["fires"]], ["y"])
        self.assertEqual(capped["unplanned"]["improve"], 1)

    def test_the_routine_outage_holds_trigger_fires(self):
        plan = plan_week.build_plan(ctx(
            triggers=self.triggers(x=True), skill_weights={"x": 0}, room=1.0,
            routine_down=NOW - timedelta(hours=1),
            cells=[cell("evals/m", "heavy", "missing")]), NOW)
        self.assertEqual([f["mode"] for f in plan["fires"]], ["eval"])
        self.assertEqual(plan["unplanned"]["improve"], 1)

    def test_trigger_skills_do_not_move_the_improve_neutral_weight(self):
        skills = {"a": skill(headroom=0.5), "b": skill(headroom=0.3)}
        weights = {"a": 2.0, "b": None, "c": 50.0, "d": 60.0}
        plan = plan_week.build_plan(ctx(skills=skills, room=1.0, improve_charge=0.01,
                                        skill_weights=weights,
                                        triggers=self.triggers(c=False, d=False)), NOW)
        # The neutral weight is the median of a and b's known weights (2), so
        # b's tie breaks on headroom; c's 50 would have put b first.
        self.assertEqual([f["skill"] for f in plan["fires"]], ["a", "b"])

    def test_hook_candidate_heuristic(self):
        self.assertTrue(plan_week.hook_candidate(CHECKLIST_SKILL))
        self.assertFalse(plan_week.hook_candidate(PROSE_SKILL))
        self.assertFalse(plan_week.hook_candidate(""))
        # A fenced line that looks like a heading does not close the section.
        fenced = "## Rules\n\n```\n# comment\n```\n- a\n- b\n\n## Notes\n\nc\n"
        self.assertTrue(plan_week.hook_candidate(fenced))
        # A ruleset is not a rules section.
        self.assertFalse(plan_week.hook_candidate("## Ruleset\n\n- a\n- b\n"))

    def test_trigger_contexts_read_the_registry_and_the_evals_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skills = base / "registry" / "plugins" / "p" / "skills"
            for name, text in (("example-checks", CHECKLIST_SKILL),
                               ("example-prose", PROSE_SKILL)):
                (skills / name).mkdir(parents=True)
                (skills / name / "SKILL.md").write_text(text)
            (skills / "linked").mkdir()
            (skills / "linked" / "SKILL.md").symlink_to(skills / "example-prose" / "SKILL.md")
            evals = base / "evals"
            (evals / "example-prose").mkdir(parents=True)
            (evals / "example-prose" / "trigger-eval-set.json").write_text("[]")
            got = plan_week.trigger_contexts(
                evals, {"adam-agentskills": {"path": str(base / "registry")}})
            self.assertEqual(got, {
                "example-checks": {"trigger_set": False, "hook_candidate": True},
                "example-prose": {"trigger_set": True, "hook_candidate": False}})
            self.assertEqual(plan_week.trigger_contexts(evals, {}), {})

    def test_the_trigger_lane_is_documented(self):
        text = (ROOT / "docs" / "how-it-works.md").read_text()
        self.assertIn("### The trigger lane", text)
        self.assertIn("`trigger_only=true`", text)
        self.assertNotIn("needs routine prompt change", text)
        self.assertIn("--trigger-eval-set evals/<skill>/trigger-eval-set.json", text)

    def test_trigger_pauses_use_rule_c_with_a_usage_cooldown(self):
        merged = NOW - timedelta(days=3)
        records = [{"skill": "t", "outcome": "accepted", "at": iso(merged - timedelta(hours=1))}]
        prs = [{"skill": "t", "state": "closed", "created_at": iso(merged - timedelta(minutes=30)),
                "closed_at": iso(merged), "merged_at": iso(merged)}]
        with tempfile.TemporaryDirectory() as tmp:
            triggers = self.triggers(t=True, n=False)
            plan_week.trigger_pauses(triggers, Path(tmp) / "evals", {}, records, prs, [], NOW)
            self.assertEqual(triggers["t"]["pause"],
                             "an improvement merged; waiting for the with arm to be re-measured")
            self.assertIsNone(triggers["n"]["pause"])
            later = NOW + plan_week.COOLDOWN
            plan_week.trigger_pauses(triggers, Path(tmp) / "evals", {}, records, prs, [], later)
            self.assertIsNone(triggers["t"]["pause"])


# These tests fill a cap of three; MAX_IN_FLIGHT itself is a spending lever.
@mock.patch.object(plan_week, "MAX_IN_FLIGHT", 3)
class DispatchLegTests(unittest.TestCase):

    def test_in_flight_and_waiting(self):
        runs = [fire(1, "Fire eval routine: eval evals/x m", NOW - timedelta(minutes=5)),
                fire(2, "Fire eval routine: improve a ", NOW - timedelta(hours=2)),
                fire(3, "t", NOW - timedelta(minutes=1), conclusion=None, status="queued"),
                fire(4, "Fire eval routine: eval evals/x m", NOW - timedelta(hours=1)),
                fire(5, "Fire eval routine: improve a ", NOW - timedelta(hours=4)),
                fire(6, "t", NOW, conclusion="failure")]
        self.assertEqual(plan_week.in_flight(runs, NOW), 3)
        clock = [NOW]
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            clock[0] += timedelta(seconds=seconds)
        fetched = []

        def fetch(since):
            fetched.append(since)
            return runs
        self.assertTrue(plan_week.wait_slot(fetch, 1500, lambda: clock[0], sleep))
        # Run 1 leaves its 20-minute flight 15 minutes on.
        self.assertEqual(slept, [60] * 15)
        self.assertEqual(fetched[0], NOW - plan_week.IMPROVE_FLIGHT)
        slept.clear()
        clock[0] = NOW
        self.assertFalse(plan_week.wait_slot(fetch, 240, lambda: clock[0], sleep))
        self.assertEqual(slept, [60] * 4)

    def full_cap(self):
        """Three improve fires in flight for the next three hours."""
        return [fire(n, "Fire eval routine: improve a ", NOW - timedelta(minutes=1))
                for n in (1, 2, 3)]

    def test_the_sweep_shares_one_wait_budget(self):
        # Regression: the 2026-11-02 22:50 UTC sweep waited 25 minutes in
        # each of its serial legs and ran until 04:30. Legs share
        # SWEEP_MAX_WAIT from the plan; once it is spent a leg checks once.
        runs = self.full_cap()
        clock = [NOW]
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            clock[0] += timedelta(seconds=seconds)
        started = NOW
        legs = []
        for _ in range(5):
            slept.clear()
            legs.append(plan_week.wait_slot(lambda since: runs, 1500, lambda: clock[0],
                                            sleep, sweep_started=started))
            legs[-1] = (legs[-1], sum(slept))
        self.assertEqual([ok for ok, _ in legs], [False] * 5)
        self.assertEqual(legs[0][1], 1500)
        self.assertEqual([waited for _, waited in legs[1:]], [0] * 4)
        self.assertEqual(clock[0] - NOW, timedelta(seconds=plan_week.SWEEP_MAX_WAIT))
        # Partway into the budget, a leg gets only what is left.
        clock[0] = NOW + timedelta(seconds=1000)
        slept.clear()
        self.assertFalse(plan_week.wait_slot(lambda since: runs, 1500, lambda: clock[0],
                                             sleep, sweep_started=started))
        self.assertEqual(sum(slept), 480)
        # A free slot past the budget still dispatches.
        clock[0] = NOW + timedelta(hours=1)
        self.assertTrue(plan_week.wait_slot(lambda since: [], 1500, lambda: clock[0],
                                            sleep, sweep_started=started))

    def test_a_full_cap_is_a_green_hold(self):
        # Regression: legs 4, 9 and 10 of run 41540618531 exited 1 on a full
        # cap. It is a hold: exit 0, a notice, and open=false so the
        # dispatch and spacing steps skip.
        # main() reads the real clock, so the fires start just before it.
        recent = datetime.now(timezone.utc) - timedelta(minutes=1)
        full = [fire(n, "Fire eval routine: improve a ", recent) for n in (1, 2, 3)]
        for runs, expected in ((full, "false"), ([], "true")):
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "out"
                output.write_text("")
                stdout = io.StringIO()
                with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output), "GH_TOKEN": "t"}), \
                        mock.patch.object(io_mod, "fetch_fire_runs", return_value=runs), \
                        mock.patch.object(plan_week.time, "sleep"), \
                        contextlib.redirect_stdout(stdout):
                    code = plan_week.main(["wait-slot", "--max-wait", "0",
                                           "--sweep-started", "2026-11-02T22:50:00Z"])
                self.assertEqual(code, 0)
                self.assertEqual(output.read_text(), f"open={expected}\n")
                if expected == "false":
                    self.assertIn("::notice::", stdout.getvalue())
                    self.assertNotIn("::error::", stdout.getvalue())

    def test_a_malformed_sweep_start_is_refused(self):
        with mock.patch.object(io_mod, "fetch_fire_runs", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(plan_week.main(["wait-slot", "--sweep-started", "soon"]), 0)

    def test_validate_fire_accepts_only_planned_shapes(self):
        good = {"MODE": "eval", "ARMS": "both", "FIXTURE": "evals/writing-adrs/bootstrap",
                "EVAL_KEY": "writing-adrs/bootstrap", "MODEL": "claude-opus-5-5",
                "SKILL": "", "HOLDOUT": ""}
        plan_week.validate_fire(good)
        # A bare leg on a scheduled fixture that runs in place.
        plan_week.validate_fire({**good, "ARMS": "bare"})
        guidance = {"FIXTURE": GUIDANCE_FIXTURE, "EVAL_KEY": GUIDANCE_FIXTURE[len("evals/"):]}
        plan_week.validate_fire({**good, **guidance})
        # A guidance cell not leaning toward removal: its in-situ pair alone.
        plan_week.validate_fire({**good, **guidance, "ARMS": "in-situ"})
        for change in ({"EVAL_KEY": "writing-adrs/supersede"}, {"MODEL": "claude-fable-5-1"},
                       # The in-situ pair is a guidance fixture's only.
                       {"ARMS": "in-situ"},
                       # An unscheduled fixture (evals/unscheduled.yml).
                       {"FIXTURE": "evals/browser-testing", "EVAL_KEY": "browser-testing"},
                       {"SKILL": "writing-adrs"}, {"MODE": "scaffold"},
                       {"ARMS": ""}, {"ARMS": "with"}, {"ARMS": "without"},
                       # A scheduled fixture with no `context` mapping.
                       {**guidance, "ARMS": "bare"}):
            with self.assertRaises(plan_week.PlanError, msg=change):
                plan_week.validate_fire({**good, **change})
        improve = {"MODE": "improve", "ARMS": "", "FIXTURE": "", "EVAL_KEY": "", "MODEL": "",
                   "SKILL": "writing-adrs", "HOLDOUT": "bootstrap"}
        plan_week.validate_fire(improve)
        for change in ({"HOLDOUT": ""}, {"HOLDOUT": "nope"}, {"SKILL": "skills-doctor"},
                       {"MODEL": "claude-opus-5-5"}, {"ARMS": "bare"}, {"ARMS": "both"}):
            with self.assertRaises(plan_week.PlanError, msg=change):
                plan_week.validate_fire({**improve, **change})
        # A section on an improve or eval leg is refused; only guidance-improve
        # legs carry one.
        for leg in (good, improve):
            with self.assertRaises(plan_week.PlanError):
                plan_week.validate_fire({**leg, "SECTION": GUIDANCE_SECTION})
        gleg = {"MODE": "guidance-improve", "ARMS": "", "FIXTURE": "", "EVAL_KEY": "",
                "MODEL": "", "SKILL": "", "SECTION": GUIDANCE_SECTION,
                "HOLDOUT": GUIDANCE_FIXTURE[len("evals/"):]}
        plan_week.validate_fire(gleg)
        # A planned leg always names its holdout, as an improve leg does.
        for change in ({"HOLDOUT": ""}, {"SECTION": ""}, {"SECTION": "_delivery"},
                       {"SECTION": "two-setup-gaps", "HOLDOUT": ""},
                       {"HOLDOUT": "handoff"}, {"HOLDOUT": "guidance/x/handoff"},
                       {"SKILL": "writing-adrs"}, {"MODEL": "claude-opus-5-5"},
                       {"ARMS": "both"}, {"FIXTURE": GUIDANCE_FIXTURE}):
            with self.assertRaises(plan_week.PlanError, msg=change):
                plan_week.validate_fire({**gleg, **change})

    def test_validate_fire_takes_a_trigger_only_improve_leg(self):
        # skills-evals#662: no holdout, and improve_gate's trigger-only check.
        import improve_gate
        leg = {"MODE": "improve", "ARMS": "", "FIXTURE": "", "EVAL_KEY": "", "MODEL": "",
               "SKILL": "writing-adrs", "HOLDOUT": "", "TRIGGER_ONLY": "true"}
        with mock.patch.object(improve_gate, "fire_check") as check:
            plan_week.validate_fire(leg)
            check.assert_called_once_with("writing-adrs", "", trigger_only=True)
            for change in ({"HOLDOUT": "bootstrap"}, {"SKILL": "a;b"}, {"ARMS": "both"},
                           {"MODEL": "claude-opus-5-5"}, {"TRIGGER_ONLY": "yes"},
                           {"TRIGGER_ONLY": "True"}):
                with self.assertRaises(plan_week.PlanError, msg=change):
                    plan_week.validate_fire({**leg, **change})
            # Only an improve leg may be trigger-only.
            for other in ({**self.GOOD_LEG, "TRIGGER_ONLY": "true"},
                          {"MODE": "guidance-improve", "SECTION": GUIDANCE_SECTION,
                           "HOLDOUT": GUIDANCE_FIXTURE[len("evals/"):],
                           "TRIGGER_ONLY": "true"}):
                with self.assertRaises(plan_week.PlanError):
                    plan_week.validate_fire(other)
            self.assertEqual(check.call_count, 1)
            check.side_effect = improve_gate.Rejected("x")
            with self.assertRaises(plan_week.PlanError):
                plan_week.validate_fire(leg)
        # Unmocked: writing-adrs commits a trigger set; an unknown skill has none.
        plan_week.validate_fire(leg)
        with self.assertRaises(plan_week.PlanError):
            plan_week.validate_fire({**leg, "SKILL": "no-trigger-set-skill"})
        # "false" and absent are the ordinary improve leg, holdout required.
        improve = {**leg, "HOLDOUT": "bootstrap", "TRIGGER_ONLY": "false"}
        plan_week.validate_fire(improve)
        plan_week.validate_fire({k: v for k, v in improve.items() if k != "TRIGGER_ONLY"})
        with self.assertRaises(plan_week.PlanError):
            plan_week.validate_fire({**improve, "HOLDOUT": ""})

    def test_the_dispatch_legs_carry_trigger_only(self):
        doc = yaml.safe_load(
            (ROOT / ".github/workflows/routine-eval-weekly.yml").read_text())
        steps = {s["name"]: s for s in doc["jobs"]["dispatch"]["steps"]}
        for name in ("Revalidate the planned fire", "Dispatch the validated fire"):
            self.assertEqual(steps[name]["env"]["TRIGGER_ONLY"], "${{ matrix.trigger_only }}")
        # The dispatch script itself is run in test_issue_scheduled_fixtures.py.

    GOOD_LEG = {"MODE": "eval", "ARMS": "both", "FIXTURE": "evals/writing-adrs/bootstrap",
                "EVAL_KEY": "writing-adrs/bootstrap", "MODEL": "claude-opus-5-5",
                "SKILL": "", "HOLDOUT": ""}
    # Committed under evals/ but listed in evals/unscheduled.yml.
    UNSCHEDULED_LEG = {"FIXTURE": "evals/browser-testing", "EVAL_KEY": "browser-testing"}

    def run_validate_fire(self, leg):
        """main(["validate-fire"]) under `leg`'s env: (exit code, GITHUB_OUTPUT, stdout)."""
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.write_text("")
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, {**leg, "GITHUB_OUTPUT": str(output)}), \
                    contextlib.redirect_stdout(stdout):
                code = plan_week.main(["validate-fire"])
            return code, output.read_text(), stdout.getvalue()

    def test_a_fixture_unscheduled_after_the_plan_is_stale_not_an_error(self):
        leg = {**self.GOOD_LEG, **self.UNSCHEDULED_LEG}
        with self.assertRaises(plan_week.PlanStale):
            plan_week.validate_fire(leg)
        code, output, stdout = self.run_validate_fire(leg)
        self.assertEqual(code, 0)
        self.assertEqual(output, "fire=false\n")
        self.assertIn("::notice::", stdout)
        self.assertNotIn("::error::", stdout)

    def test_a_valid_leg_writes_fire_true(self):
        code, output, _ = self.run_validate_fire(self.GOOD_LEG)
        self.assertEqual((code, output), (0, "fire=true\n"))

    def test_an_unknown_fixture_is_still_a_plain_plan_error(self):
        leg = {**self.GOOD_LEG, "FIXTURE": "evals/no-such-skill/x", "EVAL_KEY": "no-such-skill/x"}
        with self.assertRaises(plan_week.PlanError) as caught:
            plan_week.validate_fire(leg)
        self.assertNotIsInstance(caught.exception, plan_week.PlanStale)
        code, output, stdout = self.run_validate_fire(leg)
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("::error::", stdout)

    def test_the_dispatch_steps_follow_the_revalidation_output(self):
        doc = yaml.safe_load(
            (ROOT / ".github/workflows/routine-eval-weekly.yml").read_text())
        steps = {s["name"]: s for s in doc["jobs"]["dispatch"]["steps"]}
        self.assertEqual(steps["Revalidate the planned fire"].get("id"), "valid")
        gate = "steps.valid.outputs.fire == 'true'"
        self.assertIn(gate, steps["Wait until a fire slot is free"]["if"])
        self.assertIn(gate, steps["Dispatch the validated fire"]["if"])
        self.assertIn("steps.slot.outputs.open == 'true'",
                      steps["Dispatch the validated fire"]["if"])
        # The spacing step needs the slot step's output, which a skipped slot
        # step never sets.
        self.assertEqual(steps["Space the next fire"]["if"], "steps.slot.outputs.open == 'true'")


class PlanCommandTests(unittest.TestCase):
    """The step's own command on the real evals directory, an empty results
    tree and recorded evidence: every planned leg passes its revalidation."""

    def test_plan_writes_a_matrix_whose_legs_revalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            evidence = base / "evidence.json"
            evidence.write_text(json.dumps({"fire_runs": [], "improve_branches": [],
                                            "registry_prs": [], "on_hold": []}))
            output, summary, plan_file = base / "output", base / "summary", base / "plan.json"
            argv = ["plan", "--results-tree", str(base / "tree"), "--as-of",
                    "2026-10-26T12:00:00+00:00", "--evidence", str(evidence),
                    "--out", str(plan_file)]
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output),
                                              "GITHUB_STEP_SUMMARY": str(summary)}), \
                 contextlib.redirect_stdout(out):
                self.assertEqual(plan_week.main(argv), 0, out.getvalue())
            lines = output.read_text().splitlines()
            matrix = json.loads(lines[0].removeprefix("matrix="))
            self.assertEqual(lines[1], f"count={len(matrix['include'])}")
            self.assertGreater(len(matrix["include"]), 0)
            # On an empty tree every cell is missing: a skill's goes to the
            # missing band, a guidance section's to the focus (two sections)
            # or the guidance rest, never to missing.
            guided: dict = {}
            for row in matrix["include"]:
                guided.setdefault(row["eval_key"].startswith("guidance/"), set()).add(
                    row["band"])
            self.assertEqual(guided.get(False), {"missing"})
            self.assertLessEqual(guided.get(True, set()), {"focus", "guidance-rest"})
            for row in matrix["include"]:
                plan_week.validate_fire({"MODE": row["mode"], "ARMS": row["arms"],
                                         "FIXTURE": row["fixture"],
                                         "EVAL_KEY": row["eval_key"], "MODEL": row["model"],
                                         "SKILL": row["skill"], "HOLDOUT": row["holdout"]})
            self.assertIn("### Weekly plan:", summary.read_text())
            plan = json.loads(plan_file.read_text())
            self.assertEqual(plan["schema_version"], 1)
            # gather hands build_plan the guard's improve counts (#572):
            # none used, so each kind's floor is open.
            self.assertEqual(plan["improve_allowed"],
                             {"improve": True, "guidance-improve": True})
            # Every in-place cell is a bare candidate on an empty tree; the
            # missing band takes the room first, so none is planned yet.
            roster = yaml.safe_load((ROOT / "evals" / "roster.yml").read_text())
            in_place = [f for f in plan_week.schedule.scheduled_fixtures(
                            ROOT / "evals" / "scheduled.yml",
                            plan_week.schedule.committed_fixtures(ROOT))
                        if plan_week.schedule.declares_context(ROOT / f)]
            self.assertTrue(in_place)
            self.assertEqual(plan["unplanned"]["bare"], len(in_place) * len(roster["arms"]))

    def test_an_unreadable_evidence_file_plans_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "evidence.json").write_text("{")
            output = base / "output"
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}), \
                 contextlib.redirect_stdout(out):
                code = plan_week.main(["plan", "--results-tree", str(base), "--as-of",
                                       "2026-10-26T12:00:00+00:00",
                                       "--evidence", str(base / "evidence.json")])
            self.assertEqual(code, 1)
            self.assertFalse(output.exists())
            self.assertEqual(out.getvalue(), "::error::weekly plan: the plan could not be made\n")

    def test_registry_prs_split_improve_and_removal(self):
        rows = [{"head": {"ref": "eval-improve/writing-adrs"}, "state": "open",
                 "created_at": "a", "closed_at": None, "merged_at": None},
                {"head": {"ref": "retire-skill/old-skill"}, "state": "open"},
                {"head": {"ref": "retire-skill/done"}, "state": "closed"},
                {"head": {"ref": "eval-improve/$(x)"}, "state": "open"}, {"head": None}]
        improve, removal = plan_week.registry_prs(rows)
        self.assertEqual([p["skill"] for p in improve], ["writing-adrs"])
        self.assertEqual(removal, ["old-skill"])

    def test_model_weights_from_the_census(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertEqual(plan_week.model_weights(base, ["a", "b"]), {"a": 0.5, "b": 0.5})
            (base / "usage").mkdir()
            (base / "usage" / "latest.json").write_text(json.dumps(
                {"a": {"2026-W42": 3}, "b": {"2026-W42": 1, "2026-W43": True}, "weeks": 2}))
            self.assertEqual(plan_week.model_weights(base, ["a", "b"]), {"a": 0.75, "b": 0.25})


GUIDANCE_FIXTURE = "evals/guidance/anything-you-name-gets-its-link/handoff"
GUIDANCE_SECTION = "anything-you-name-gets-its-link"


class GuidanceFixtureTests(unittest.TestCase):
    """Scheduled guidance-section fixtures (#124) are eval cells keyed by
    their section, never a skill: the verdict document's `guidance` half is
    their evidence, and skill-only logic skips them."""

    def test_guidance_cells_read_the_section_verdict_and_name_no_skill(self):
        self.assertIn(GUIDANCE_FIXTURE, plan_week.schedule.scheduled_fixtures(
            ROOT / "evals" / "scheduled.yml",
            plan_week.schedule.committed_fixtures(ROOT)))
        run = {"timestamp": "20261020T100000Z-abc123"}
        gates_doc = {"roster_models": ["m"], "skills": {}, "guidance": {
            "anything-you-name-gets-its-link": {"cells": [
                {"fixture": "handoff", "model": "m", "class": "insufficient",
                 "cost_usd": 2.0, "runs": {"with": [run], "without": [run]}}]}}}
        cells = plan_week.eval_cells(ROOT / "evals", gates_doc, [], NOW)
        mine = [c for c in cells if c["fixture"] == GUIDANCE_FIXTURE]
        self.assertEqual(len(mine), 1)
        self.assertEqual((mine[0]["skill"], mine[0]["section"], mine[0]["class"],
                          mine[0]["with_runs"], mine[0]["usd_per_fire"]),
                         ("", "anything-you-name-gets-its-link", "insufficient", 1, 2.0))
        other = next(c for c in cells if c["fixture"].startswith("evals/guidance/")
                     and c["fixture"] != GUIDANCE_FIXTURE)
        self.assertEqual((other["skill"], other["class"]), ("", "missing"))
        self.assertTrue(all(c["section"] is None and c["skill"] for c in cells
                            if not c["fixture"].startswith("evals/guidance/")))

    def test_guidance_cells_plan_eval_fires_and_skip_skill_logic(self):
        section = "anything-you-name-gets-its-link"
        cells = [{**cell(GUIDANCE_FIXTURE, "heavy", "missing"), "skill": "",
                  "section": section},
                 {**cell("evals/guidance/s/x", "heavy", "missing", empty=2), "skill": "",
                  "section": "s"}]
        # A removal PR named like the section is a skill's, not this cell's.
        # A missing guidance cell enters the focus, never the missing band.
        plan = plan_week.build_plan(ctx(cells=cells, removal_prs=[section, ""]), NOW)
        self.assertEqual([(f["band"], f["mode"], f["fixture"], f["eval_key"])
                          for f in plan["fires"]],
                         [("focus", "eval", GUIDANCE_FIXTURE,
                           "guidance/anything-you-name-gets-its-link/handoff")])
        self.assertEqual(plan["matrix"]["include"][0]["skill"], "")
        self.assertEqual(plan["work"], [{"kind": "fixture-broken", "change_type": "fixture",
                                         "skill": "", "section": "s",
                                         "fixture": "evals/guidance/s/x", "model": "heavy",
                                         "route": "issue"}])

    def test_the_plan_command_names_no_guidance_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            evidence = base / "evidence.json"
            evidence.write_text(json.dumps({"fire_runs": [], "improve_branches": [],
                                            "registry_prs": [], "on_hold": []}))
            plan_file = base / "plan.json"
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": "",
                                              "GITHUB_STEP_SUMMARY": ""}), \
                 contextlib.redirect_stdout(out):
                code = plan_week.main(["plan", "--results-tree", str(base / "tree"),
                                       "--as-of", "2026-10-26T12:00:00+00:00",
                                       "--evidence", str(evidence), "--max-fires", "30",
                                       "--out", str(plan_file)])
            self.assertEqual(code, 0, out.getvalue())
            plan = json.loads(plan_file.read_text())
            self.assertNotIn("guidance", plan["skills"])
            self.assertFalse(any(w.get("skill") == "guidance" for w in plan["work"]))


def gsection(fixtures=4, headroom=0.4, verdict="keep"):
    """A guidance section's context, as plan_week.guidance_contexts builds it."""
    return {"fixtures": fixtures, "holdout": "zzz" if fixtures >= 4 else "",
            "verdict": verdict,
            "evidence": {"headroom": headroom, "pass_rate": None, "with_trials": 6,
                         "targets": []}}


@mock.patch.object(plan_week, "GUIDANCE_IMPROVE_HELD", False)
class ImproveValueTests(unittest.TestCase):
    """The improve candidates, skills and guidance sections, ranked by
    value = use x headroom / cost."""

    def test_the_value_formula_and_what_makes_it_unknown(self):
        self.assertAlmostEqual(plan_week.value_of(10, 0.5, 0.25), 20.0)
        self.assertEqual(plan_week.value_of(0, 0.5, 0.25), 0.0)
        for args in ((None, 0.5, 0.25), (10, None, 0.25), (10, 0.5, None), (10, 0.5, 0)):
            self.assertIsNone(plan_week.value_of(*args), args)

    def test_cost_is_improve_trials_times_each_fixtures_mean_fire_cost(self):
        # usd 1 and 3 on one fixture: points 0.01 and 0.03, mean 0.02; the
        # second fixture 0.02; an unknown cell adds nothing.
        cells = [cell("evals/a/f1", "heavy", "missing", usd=1.0),
                 cell("evals/a/f1", "light", "missing", usd=3.0),
                 cell("evals/a/f2", "heavy", "missing", usd=2.0),
                 cell("evals/a/f3", "heavy", "missing"),
                 cell("evals/b/f1", "heavy", "missing")]
        c = ctx(cells=cells, points_per_usd=0.01)
        self.assertAlmostEqual(plan_week.cost_estimate(c, "skill", "a"),
                               plan_week.IMPROVE_TRIALS * 0.04)
        self.assertIsNone(plan_week.cost_estimate(c, "skill", "b"))
        self.assertIsNone(plan_week.cost_estimate(ctx(cells=cells), "skill", "a"))
        guidance = {**cell("evals/guidance/s/x", "heavy", "missing", usd=2.0), "skill": "",
                    "section": "s"}
        c = ctx(cells=[guidance], points_per_usd=0.01)
        self.assertAlmostEqual(plan_week.cost_estimate(c, "guidance", "s"),
                               plan_week.IMPROVE_TRIALS * 0.02)
        self.assertIsNone(plan_week.cost_estimate(c, "skill", "s"))

    def test_ranking_rows_carry_value_use_and_cost(self):
        cells = [cell("evals/a/f1", "heavy", "missing", usd=2.0)]
        plan = plan_week.build_plan(ctx(
            skills={"a": skill(headroom=0.5)}, skill_weights={"a": 4}, cells=cells,
            points_per_usd=0.01, room=1.0), NOW)
        cost = plan_week.IMPROVE_TRIALS * 0.02
        self.assertEqual(plan["improve_ranking"], [{
            "subject": "skill", "name": "a", "value": 4 * 0.5 / cost, "use": 4,
            "use_known": True, "headroom": 0.5, "cost": cost, "cost_known": True,
            "eligible": True, "reasons": [], "lesson_evidence": 0}])
        improve = [f for f in plan["fires"] if f["mode"] == "improve"]
        self.assertEqual([f["value"] for f in improve], [4 * 0.5 / cost])
        self.assertIsNone(plan["fires"][0]["value"] if plan["fires"][0]["mode"] == "eval"
                          else None)
        self.assertNotIn("value", plan["matrix"]["include"][0])

    def test_unknown_use_and_cost_are_neutral_and_a_known_zero_stays_zero(self):
        skills = {"known": skill(), "unknown": skill(), "unused": skill()}
        plan = plan_week.build_plan(ctx(
            skills=skills, skill_weights={"known": 8, "unknown": None, "unused": 0},
            improve_charge=0.2, room=1.0, guidance_use=None,
            guidance={"sec": gsection(headroom=0.5)}), NOW)
        rows = {r["name"]: r for r in plan["improve_ranking"]}
        self.assertEqual((rows["unknown"]["use"], rows["unknown"]["use_known"]), (8, False))
        self.assertEqual((rows["unused"]["use"], rows["unused"]["use_known"],
                          rows["unused"]["value"]), (0, True, 0.0))
        # Guidance's unknown use is the same neutral value; no cost known
        # anywhere, so the improve charge stands in.
        self.assertEqual((rows["sec"]["use"], rows["sec"]["use_known"]), (8, False))
        self.assertTrue(all(r["cost"] == 0.2 and not r["cost_known"] for r in rows.values()))
        self.assertAlmostEqual(rows["sec"]["value"], 8 * 0.5 / 0.2)

    def test_an_unknown_cost_is_the_median_of_the_known_ones(self):
        cells = [cell("evals/a/f1", "heavy", "missing", usd=1.0),
                 cell("evals/b/f1", "heavy", "missing", usd=3.0)]
        plan = plan_week.build_plan(ctx(
            skills={"a": skill(), "b": skill(), "c": skill()}, cells=cells,
            points_per_usd=0.01, improve_charge=0.9, room=1.0), NOW)
        rows = {r["name"]: r for r in plan["improve_ranking"]}
        self.assertAlmostEqual(rows["c"]["cost"], plan_week.IMPROVE_TRIALS * 0.02)
        self.assertFalse(rows["c"]["cost_known"])
        self.assertTrue(rows["a"]["cost_known"] and rows["b"]["cost_known"])

    def test_the_improve_band_is_ordered_by_value_not_usage(self):
        # The heavier skill used to lead; the one with far more headroom now does.
        skills = {"heavy": skill(headroom=0.12), "light": skill(headroom=0.9)}
        plan = plan_week.build_plan(ctx(skills=skills, room=1.0, improve_charge=0.01,
                                        skill_weights={"heavy": 10, "light": 5}), NOW)
        self.assertEqual([f["skill"] for f in plan["fires"]], ["light", "heavy"])
        self.assertEqual([r["name"] for r in plan["improve_ranking"]], ["light", "heavy"])
        self.assertGreater(plan["fires"][0]["value"], plan["fires"][1]["value"])

    def test_ties_break_on_name(self):
        plan = plan_week.build_plan(ctx(skills={"b": skill(), "a": skill()}, room=1.0,
                                        improve_charge=0.01,
                                        skill_weights={"a": 3, "b": 3}), NOW)
        self.assertEqual([f["skill"] for f in plan["fires"]], ["a", "b"])

    def test_an_eligible_guidance_section_is_an_improve_band_fire(self):
        plan = plan_week.build_plan(ctx(
            guidance={"sec": {**gsection(headroom=0.4),
                              "holdout_fixture": "guidance/sec/zzz"}},
            guidance_use=100.0, improve_charge=0.1, room=1.0), NOW)
        self.assertEqual(plan["work"], [])
        [fire] = plan["fires"]
        self.assertAlmostEqual(fire.pop("value"), 100.0 * 0.4 / 0.1)
        self.assertEqual(fire, {
            "slot": 0, "band": "improve", "mode": "guidance-improve", "arms": "",
            "fixture": "", "eval_key": "", "model": "", "skill": "", "section": "sec",
            "holdout": "guidance/sec/zzz", "trigger_only": "false",
            "trim_description": "false", "change_type": "guidance-edit", "cost": 0.1})
        self.assertEqual(plan["matrix"]["include"], [{
            "slot": 0, "band": "improve", "mode": "guidance-improve", "arms": "", "fixture": "", "eval_key": "",
            "model": "", "skill": "", "section": "sec", "holdout": "guidance/sec/zzz",
            "trigger_only": "false", "trim_description": "false"}])
        self.assertEqual(plan["guidance"], {"sec": {
            "eligible": True, "reasons": [], "headroom": 0.4, "fixtures": 4}})
        self.assertEqual(plan["skills"], {})

    def test_one_guidance_fire_per_plan_the_highest_value_first(self):
        plan = plan_week.build_plan(ctx(
            guidance={"low": gsection(headroom=0.2), "high": gsection(headroom=0.8)},
            guidance_use=10.0, improve_charge=0.1, room=1.0), NOW)
        self.assertEqual([f["section"] for f in plan["fires"]], ["high"])
        self.assertTrue(plan["guidance"]["low"]["eligible"])
        self.assertIn("high ranks higher", plan["guidance"]["low"]["deferred"])
        self.assertEqual(plan["work"], [])

    def test_a_paused_section_gets_no_fire_and_no_work_item(self):
        for pause in ("an attempt is in flight",
                      "another guidance-loop pull request is open in _agent-guidance"):
            with self.subTest(pause=pause):
                plan = plan_week.build_plan(ctx(
                    guidance={"sec": {**gsection(headroom=0.5), "pause": pause}},
                    guidance_use=10.0, improve_charge=0.1, room=1.0), NOW)
                self.assertEqual(plan["fires"], [])
                self.assertEqual(plan["work"], [])
                self.assertEqual(plan["guidance"]["sec"]["reasons"], [pause])
                self.assertFalse(plan["guidance"]["sec"]["eligible"])
        plan = plan_week.build_plan(ctx(
            guidance={"sec": {**gsection(headroom=0.5), "row_ok": False}},
            guidance_use=10.0, improve_charge=0.1, room=1.0), NOW)
        self.assertEqual((plan["fires"], plan["work"]), ([], []))
        self.assertEqual(plan["guidance"]["sec"]["reasons"],
                         ["its eval-coverage.yml row is skipped or missing"])

    def test_a_section_id_the_fire_workflow_refuses_stays_a_work_item(self):
        # `Sec_1` is a manifest id the fire workflow's section pattern
        # refuses, so it keeps the local route instead of a fire.
        plan = plan_week.build_plan(ctx(
            guidance={"Sec_1": gsection(headroom=0.4)}, guidance_use=100.0,
            improve_charge=0.1, room=1.0), NOW)
        self.assertEqual(plan["fires"], [])
        [item] = plan["work"]
        self.assertAlmostEqual(item.pop("value"), 100.0 * 0.4 / 0.1)
        self.assertEqual(item, {
            "kind": "guidance-improve", "change_type": "guidance-edit", "section": "Sec_1",
            "fixtures": 4, "headroom": 0.4, "route": plan_week.GUIDANCE_IMPROVE_ROUTE})

    def test_guidance_sections_that_are_not_eligible(self):
        plan = plan_week.build_plan(ctx(
            guidance={"few": gsection(fixtures=2, headroom=0.5),
                      "flat": gsection(headroom=0.05),
                      "retiring": gsection(verdict="retire"),
                      "pending": gsection(verdict="retire-pending", headroom=0.01),
                      "blank": gsection(headroom=None)},
            guidance_use=10.0, room=1.0), NOW)
        by_section = {w["section"]: w for w in plan["work"]}
        self.assertEqual(sorted(by_section), ["few", "flat"])
        self.assertEqual((by_section["few"]["kind"], by_section["few"]["skill"],
                          by_section["few"]["fixtures"], by_section["few"]["headroom"]),
                         ("needs-fixtures", "", 2, 0.5))
        self.assertEqual((by_section["flat"]["kind"], by_section["flat"]["skill"]),
                         ("needs-harder-fixtures", ""))
        status = plan["guidance"]
        self.assertEqual(status["few"]["reasons"], ["2 fixture(s), under 4"])
        self.assertIn("owned by retirement (retire)", status["retiring"]["reasons"])
        self.assertIn("no train headroom", status["blank"]["reasons"])
        self.assertFalse(any(s["eligible"] for s in status.values()))
        self.assertEqual(plan["fires"], [])

    def test_a_tracked_section_with_no_fixtures_asks_for_its_first(self):
        plan = plan_week.build_plan(ctx(
            guidance={"few": gsection(fixtures=2, headroom=0.5)},
            guidance_gaps=["few", "new-section", "retiring", "removing", "Bad_Id"],
            gate_verdicts=None, guidance_removal_prs=["removing"],
            guidance_use=10.0, room=1.0), NOW)
        by_section = {w["section"]: w for w in plan["work"]}
        # `few` has fixtures, so the ordinary rule answers for it; a retiring
        # or removing section and an id the issue key cannot carry get none.
        self.assertEqual(sorted(by_section), ["few", "new-section", "retiring"])
        self.assertEqual(by_section["new-section"], {
            "kind": "needs-fixtures", "change_type": "fixture", "skill": "",
            "section": "new-section", "fixtures": 0, "headroom": None, "value": None,
            "route": "issue"})
        self.assertEqual(plan["guidance"]["new-section"],
                         {"eligible": False, "reasons": ["no fixtures yet"],
                          "headroom": None, "fixtures": 0})
        self.assertNotIn("removing", plan["guidance"])

    def test_guidance_gaps_reads_the_manifest(self):
        root = Path(tempfile.mkdtemp(prefix="gaps-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.assertEqual(plan_week.guidance_gaps(None), [])
        self.assertEqual(plan_week.guidance_gaps(root), [])
        path = root / plan_week.BATCH_GUIDANCE_HISTORY
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump([
            {"id": "b-gap", "status": "gap"}, {"id": "a-gap", "status": "gap"},
            {"id": "covered", "status": "covered", "fixture": "evals/guidance/covered/"},
            {"id": "skipped", "status": "skipped"}, {"id": "_delivery", "status": "gap"},
            "not a row"]), encoding="utf-8")
        self.assertEqual(plan_week.guidance_gaps(root), ["a-gap", "b-gap"])
        path.write_text("[\n", encoding="utf-8")
        self.assertEqual(plan_week.guidance_gaps(root), [])

    def test_the_ranking_is_by_value_with_unknown_headroom_last(self):
        skills = {"blank": skill(headroom=None), "low": skill(headroom=0.2),
                  "high": skill(headroom=0.8)}
        plan = plan_week.build_plan(ctx(
            skills=skills, skill_weights={"blank": 99, "low": 5, "high": 5},
            guidance={"sec": gsection(headroom=0.5)}, guidance_use=5.0,
            improve_charge=0.1, room=1.0), NOW)
        ranking = plan["improve_ranking"]
        self.assertEqual([(r["subject"], r["name"]) for r in ranking],
                         [("skill", "high"), ("guidance", "sec"), ("skill", "low"),
                          ("skill", "blank")])
        self.assertIsNone(ranking[-1]["value"])
        self.assertIsNone(ranking[-1]["headroom"])
        self.assertIn("no train headroom", ranking[-1]["reasons"])
        self.assertTrue(ranking[0]["eligible"] and ranking[1]["eligible"])
        self.assertEqual([r["value"] for r in ranking[:3]],
                         sorted((r["value"] for r in ranking[:3]), reverse=True))

    def test_the_summary_lists_the_top_ten_with_rounding_only_there(self):
        skills = {f"s{i:02d}": skill(headroom=0.3 + i / 100) for i in range(12)}
        skills["blank"] = skill(headroom=None)
        plan = plan_week.build_plan(ctx(skills=skills, room=1.0, improve_charge=0.07,
                                        skill_weights={n: 2 for n in skills}), NOW)
        lines = plan_week.summary_lines(plan)
        at = lines.index("Improve ranking (value = use × headroom ÷ cost)")
        rows = [line for line in lines[at:] if line.startswith("- ")]
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0], "- skill s11: value 11.7 (use 2.0, headroom 0.41, "
                                  "cost 7.00 points), eligible")
        self.assertNotEqual(plan["improve_ranking"][0]["value"], 11.7)
        blank = plan_week.summary_lines({**plan, "improve_ranking": plan["improve_ranking"][-1:]})
        self.assertIn("- skill blank: value unknown (use 2.0, headroom unknown, cost 7.00 "
                      "points): no train headroom", blank)

    def test_session_rate_scales_the_transcript_window_to_28_days(self):
        import skill_usage
        doc = skill_usage.document([], NOW, NOW - timedelta(days=14), 50)
        self.assertAlmostEqual(skill_usage.session_rate(doc, NOW), 100.0)
        self.assertAlmostEqual(skill_usage.session_rate(doc, NOW, days=7), 25.0)
        self.assertIsNone(skill_usage.session_rate(None, NOW))
        self.assertIsNone(skill_usage.session_rate(doc, NOW + timedelta(days=15)))
        for change in ({"sessions_scanned": -1}, {"sessions_scanned": True},
                       {"from": "yesterday"}, {"to": doc["sources"][0]["from"]},
                       {"scope": "hooks"}, {"surface": "cloud"}):
            bad = {**doc, "sources": [{**doc["sources"][0], **change}]}
            self.assertIsNone(skill_usage.session_rate(bad, NOW), change)
        self.assertIsNone(skill_usage.session_rate({**doc, "sources": []}, NOW))
        # A known zero is zero, not unknown.
        zero = skill_usage.document([], NOW, NOW - timedelta(days=14), 0)
        self.assertEqual(skill_usage.session_rate(zero, NOW), 0.0)

    def test_guidance_use_reads_the_census_or_stays_unknown(self):
        import skill_usage
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            self.assertIsNone(plan_week.guidance_use(tree, NOW))
            (tree / "usage").mkdir()
            path = tree / "usage" / "weekly-local.json"
            path.write_text(json.dumps(skill_usage.document(
                [], NOW - timedelta(days=1), NOW - timedelta(days=15), 56)))
            self.assertAlmostEqual(plan_week.guidance_use(tree, NOW), 112.0)
            self.assertIsNone(plan_week.guidance_use(tree, NOW + timedelta(days=30)))
            path.write_text("{")
            self.assertIsNone(plan_week.guidance_use(tree, NOW))
            with mock.patch.dict(sys.modules, {"skill_usage": None}):
                self.assertIsNone(plan_week.guidance_use(tree, NOW))

    def test_guidance_contexts_need_the_checkout_and_pool_the_in_situ_full_arm(self):
        section = "anything-you-name-gets-its-link"
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            doc = {"roster_models": ["m"], "guidance": {section: {"verdict": "keep"}}}
            self.assertEqual(plan_week.guidance_contexts(
                ROOT / "evals", tree, "20261026T120000Z", doc, None), {})
            # done-summary, handoff, no-url are train; waiting-on-review (last
            # in name order) is the holdout and must not count.
            expected = {n: {"fixture_digest": f"fd-{n}", "tested_digest": "t",
                            "rest_digest": "rest"}
                        for n in ("done-summary", "handoff", "no-url", "waiting-on-review")}

            def run(name, role, checks):
                return {"skill": section, "fixture": name, "model": "m", "role": role,
                        "pair": "in_situ", "tested_digest": "t",
                        "fixture_digest": f"fd-{name}", "arm_context_digest": "rest",
                        "pair_key": "rest", "timestamp": "20261020T000000Z", "path": name,
                        "trials": [trial(checks)]}
            runs = [run("done-summary", "with", {"a": True, "b": False}),
                    run("done-summary", "without", {"a": False, "b": False}),
                    run("handoff", "with", {"a": True, "b": True}),
                    run("handoff", "without", {"a": False, "b": True}),
                    run("waiting-on-review", "with", {"a": False, "b": False}),
                    run("waiting-on-review", "without", {"a": False, "b": False})]
            index = {"guidance_runs": runs + [{**runs[0], "pair": "alone"}]}
            with mock.patch.object(plan_week_compute_gates, "build_index",
                                   return_value=index), \
                 mock.patch.object(plan_week_compute_gates, "expected_guidance",
                                   return_value=expected):
                got = plan_week.guidance_contexts(ROOT / "evals", tree, "20261026T120000Z",
                                                  doc, tree)
        self.assertEqual(got[section]["fixtures"], 4)
        self.assertEqual(got[section]["holdout"], "waiting-on-review")
        self.assertEqual(got[section]["verdict"], "keep")
        # 3 of 4 train checks passed: headroom 0.25, the holdout's failures left out.
        self.assertAlmostEqual(got[section]["evidence"]["headroom"], 0.25)
        # A section with one fixture keeps no holdout and an unknown verdict.
        self.assertEqual(got["git-practices"]["holdout"], "")
        self.assertEqual(got["git-practices"]["verdict"], "insufficient")
        self.assertNotIn("_delivery", got)

    def test_guidance_contexts_pool_the_current_rest_as_the_gate_does(self):
        # 2026-11-03: the gate decides an in-situ cell on its current-content
        # runs beside the rest of the guidance on main, ignoring older rests,
        # so the improve evidence must count those runs, even when they are
        # the minority, and not `_joint_context`'s largest same-rest group.
        section = "anything-you-name-gets-its-link"
        expected = {n: {"fixture_digest": f"fd-{n}", "tested_digest": "t",
                        "rest_digest": "rest-2"}
                    for n in ("done-summary", "handoff", "no-url", "waiting-on-review")}

        def run(name, role, checks, rest, stamp):
            return {"skill": section, "fixture": name, "model": "m", "role": role,
                    "pair": "in_situ", "tested_digest": "t",
                    "fixture_digest": f"fd-{name}", "arm_context_digest": rest,
                    "pair_key": rest, "timestamp": stamp, "path": f"{name}-{stamp}",
                    "trials": [trial(checks)]}
        runs = [run("done-summary", "with", {"a": True, "b": True}, "rest-1", "20261020T000000Z"),
                run("done-summary", "without", {"a": False, "b": False}, "rest-1",
                    "20261020T000000Z"),
                run("done-summary", "with", {"a": True, "b": True}, "rest-1", "20261021T000000Z"),
                run("done-summary", "without", {"a": False, "b": False}, "rest-1",
                    "20261021T000000Z"),
                # The minority rest: its with-arm run fails both checks.
                run("done-summary", "with", {"a": False, "b": False}, "rest-2",
                    "20261022T000000Z"),
                run("done-summary", "without", {"a": False, "b": False}, "rest-2",
                    "20261022T000000Z")]
        doc = {"roster_models": ["m"], "guidance": {section: {"verdict": "insufficient"}}}
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            with mock.patch.object(plan_week_compute_gates, "build_index",
                                   return_value={"guidance_runs": runs}), \
                 mock.patch.object(plan_week_compute_gates, "expected_guidance",
                                   return_value=expected):
                got = plan_week.guidance_contexts(ROOT / "evals", tree, "20261026T120000Z",
                                                  doc, tree)
        # 0 of 2 with-arm checks passed beside rest-2, the rest on main:
        # headroom 1. Pooling every rest would read 1/3, and the largest
        # group alone (rest-1) 0.
        self.assertAlmostEqual(got[section]["evidence"]["headroom"], 1.0)

    def test_the_fire_check_refuses_a_section_with_no_train_headroom(self):
        # 2026-10-28: a hand-dispatched guidance-improve fire on a section at
        # 72/72 ran its whole loop before rejecting. The fire workflow now
        # asks the plan's own rule A first.
        section = "anything-you-name-gets-its-link"

        def check(headroom, present=True):
            ctx = ({section: {"evidence": {"headroom": headroom}}} if present else {})
            out = io.StringIO()
            with mock.patch.object(plan_week_compute_gates, "compute",
                                   return_value={"roster_models": ["m"]}), \
                 mock.patch.object(plan_week, "guidance_contexts", return_value=ctx), \
                 contextlib.redirect_stdout(out):
                code = plan_week.main(["guidance-headroom", section, "--results-tree", "t",
                                       "--as-of", "2026-10-28T18:07:56+00:00",
                                       "--guidance", "g"])
            return code, out.getvalue()

        code, out = check(0.0)
        self.assertEqual(code, 1, out)
        self.assertIn("::error::", out)
        self.assertIn("needs harder fixtures", out)
        code, out = check(plan_week.MIN_GAIN - 0.01)
        self.assertEqual(code, 1, out)
        self.assertEqual(check(plan_week.MIN_GAIN)[0], 0)
        self.assertEqual(check(0.25)[0], 0)
        # Unknown headroom passes: the proposer measures before it decides.
        self.assertEqual(check(None)[0], 0)
        self.assertEqual(check(None, present=False)[0], 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = plan_week.main(["guidance-headroom", "../x", "--results-tree", "t",
                                   "--as-of", "2026-10-28T18:07:56+00:00", "--guidance", "g"])
        self.assertEqual(code, 1)

    def test_ranking_out_writes_the_ranking_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tree").mkdir()
            evidence = base / "evidence.json"
            evidence.write_text(json.dumps({"fire_runs": [], "improve_branches": [],
                                            "registry_prs": [], "on_hold": []}))
            plan_file, ranking_file = base / "plan.json", base / "ranking.json"
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": "", "GITHUB_STEP_SUMMARY": ""}), \
                 contextlib.redirect_stdout(out):
                code = plan_week.main(["plan", "--results-tree", str(base / "tree"),
                                       "--as-of", "2026-10-26T12:00:00+00:00",
                                       "--evidence", str(evidence), "--out", str(plan_file),
                                       "--ranking-out", str(ranking_file)])
            self.assertEqual(code, 0, out.getvalue())
            plan = json.loads(plan_file.read_text())
            ranking = json.loads(ranking_file.read_text())
            self.assertEqual(sorted(ranking), ["generated_at", "improve_ranking",
                                               "schema_version"])
            self.assertEqual(ranking["schema_version"], 1)
            self.assertEqual(ranking["generated_at"], plan["generated_at"])
            self.assertEqual(ranking["improve_ranking"], plan["improve_ranking"])
            self.assertTrue(ranking["improve_ranking"])
            self.assertTrue(all(r["subject"] == "skill" and r["value"] is None
                                for r in ranking["improve_ranking"]))
            self.assertIn("Improve ranking (value = use × headroom ÷ cost)", out.getvalue())

    def test_the_weekly_workflow_uploads_the_ranking(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-weekly.yml").read_text())
        steps = doc["jobs"]["plan"]["steps"]
        at = next(i for i, step in enumerate(steps) if step.get("id") == "plan")
        self.assertIn('--ranking-out "$RUNNER_TEMP/improve-ranking.json"', steps[at]["run"])
        upload = steps[at + 1]
        # The tag is Dependabot's to move; actions.lock keeps it exact.
        self.assertTrue(upload["uses"].startswith("actions/upload-artifact@"))
        self.assertEqual(upload["with"], {
            "name": "improve-ranking", "path": "${{ runner.temp }}/improve-ranking.json",
            "retention-days": 30, "if-no-files-found": "error"})
        lock = (ROOT / ".github/workflows/actions.lock").read_text()
        self.assertIn(f"'{upload['uses']}'", lock)


BARE_FIXTURES = ("evals/writing-adrs/bootstrap", "evals/disarm-inherited-reach",
                 "evals/embeddable-tool-pages", "evals/github-actions-sha-pinning",
                 "evals/windows-elevation-from-wsl")


class BareBaselineTests(unittest.TestCase):
    """ADR 0012's 2026-10-27 addendum: one bare fire per (scheduled in-place
    fixture, roster model), once, after every other band, reserved as one
    arm; never an empty fire of the cell's pair, and one run to the guard."""

    def scheduled_in_place(self):
        committed = plan_week.schedule.committed_fixtures(ROOT)
        return [f for f in plan_week.schedule.scheduled_fixtures(
                    ROOT / "evals" / "scheduled.yml", committed)
                if plan_week.schedule.declares_context(ROOT / f)]

    def test_the_scheduled_in_place_fixtures(self):
        in_place = self.scheduled_in_place()
        # The eval scope pass (evals/scope-auto.yml) may pause one; it is
        # then off the schedule by rule, not missing.
        auto = yaml.safe_load((ROOT / "evals/scope-auto.yml").read_text(encoding="utf-8")) or {}
        paused = {row["path"] for row in auto.get("rows") or []}
        for fixture in BARE_FIXTURES:
            if fixture not in paused:
                self.assertIn(fixture, in_place)
        # Guidance fixtures declare no context: their arms are their own.
        self.assertFalse([f for f in in_place if f.startswith("evals/guidance/")])

    def test_bare_cells_are_the_in_place_cells_with_no_bare_run(self):
        bootstrap, disarm, embeddable, pinning, windows = BARE_FIXTURES
        gates_doc = {"roster_models": ["m1", "m2"], "skills": {}, "bare_runs": [
            # Ingested: done, on m1 only.
            {"skill": "writing-adrs", "fixture": "bootstrap", "model": "m1"},
            {"skill": "disarm-inherited-reach", "fixture": None, "model": "m2"}]}
        t = NOW - timedelta(days=2)
        runs = [fire(1, f"Fire eval routine: eval bare {embeddable} m1", t),
                fire(2, f"Fire eval routine: eval bare {pinning} m1", NOW,
                     conclusion=None, status="in_progress"),
                # Refused or failed: not done.
                fire(3, f"Fire eval routine: eval bare {windows} m1", t, conclusion="failure"),
                # A pair fire is not a bare run.
                fire(4, f"Fire eval routine: eval {windows} m2", t),
                # A bare fire with no model names no cell.
                fire(5, f"Fire eval routine: eval bare {windows} ", t)]
        every = {(f, m) for f in self.scheduled_in_place() for m in ("m1", "m2")}
        got = plan_week.bare_cells(ROOT / "evals", gates_doc, runs)
        self.assertEqual(len(got), len({(c["fixture"], c["model"]) for c in got}))
        self.assertEqual({(c["fixture"], c["model"]) for c in got},
                         every - {(bootstrap, "m1"), (disarm, "m2"), (embeddable, "m1"),
                                  (pinning, "m1")})
        self.assertEqual(next(c for c in got if c["fixture"] == bootstrap)["skill"],
                         "writing-adrs")
        # Once done, never again; a new model id on the roster gets its own.
        done = [{"skill": c["skill"], "fixture": c["fixture"].split("/")[2]
                 if c["fixture"].count("/") == 2 else None, "model": c["model"]}
                for c in got] + gates_doc["bare_runs"]
        later = {**gates_doc, "bare_runs": done}
        self.assertEqual(plan_week.bare_cells(ROOT / "evals", later, runs), [])
        later["roster_models"] = ["m1", "m2", "m3"]
        self.assertEqual({(c["fixture"], c["model"])
                          for c in plan_week.bare_cells(ROOT / "evals", later, runs)},
                         {(f, "m3") for f in self.scheduled_in_place()})

    def test_bare_fires_take_only_the_room_left_and_cost_one_arm(self):
        c = ctx(points_per_usd=0.005)
        self.assertAlmostEqual(plan_week.bare_cost({"usd_per_arm_trial": 1.0}, c),
                               1.0 * plan_week.BARE_TRIALS * 0.005)
        self.assertAlmostEqual(plan_week.bare_cost({"usd_per_arm_trial": 100.0}, c), 0.035)
        self.assertAlmostEqual(plan_week.bare_cost({"usd_per_arm_trial": 0.0}, c), 0.005)
        self.assertAlmostEqual(plan_week.bare_cost(None, c), 0.035)
        self.assertAlmostEqual(plan_week.bare_cost({"usd_per_arm_trial": 1.0}, ctx()), 0.035)
        cells = [{**cell("evals/a", "heavy", "missing", usd=2.0), "usd_per_arm_trial": 1.0},
                 cell("evals/b", "light", "missing")]
        bare = [{"fixture": "evals/a", "model": "heavy", "skill": "a"},
                {"fixture": "evals/a", "model": "light", "skill": "a"}]
        # Room for the two missing fires (0.01 + 0.035) and one bare fire.
        plan = plan_week.build_plan(ctx(cells=cells, bare=bare, points_per_usd=0.005,
                                        room=0.045 + 0.015 + 0.01,
                                        skills={"writing-adrs": skill()},
                                        improve_charge=1.0), NOW)
        got = [(f["band"], f["mode"], f["arms"], f["fixture"], f["model"]) for f in plan["fires"]]
        self.assertEqual(got, [("missing", "eval", "both", "evals/a", "heavy"),
                               ("missing", "eval", "both", "evals/b", "light"),
                               ("bare", "eval", "bare", "evals/a", "heavy")])
        self.assertAlmostEqual(plan["fires"][2]["cost"], 0.015)
        self.assertEqual(plan["unplanned"]["bare"], 1)
        leg = plan["matrix"]["include"][2]
        self.assertEqual((leg["mode"], leg["arms"], leg["skill"], leg["holdout"]),
                         ("eval", "bare", "", ""))
        self.assertIn("- bare: eval bare evals/a heavy, 1.50 points",
                      plan_week.summary_lines(plan))
        # Bare goes after every other band, improve included, but an improve
        # fire is still dispatched last.
        plan = plan_week.build_plan(ctx(bare=bare, room=1.0, improve_charge=0.10,
                                        skills={"writing-adrs": skill()}), NOW)
        self.assertEqual([(f["band"], f["arms"]) for f in plan["fires"]],
                         [("bare", "bare"), ("bare", "bare"), ("improve", "")])

    def test_a_bare_fire_is_not_an_empty_fire_of_the_cells_pair(self):
        fixture = "evals/writing-adrs/bootstrap"
        gates_doc = {"roster_models": ["m1"], "skills": {}}
        # NOW is before EMPTY_FIRES_SINCE (#559), which would count neither.
        now = plan_week.EMPTY_FIRES_SINCE + timedelta(days=2)
        old = now - timedelta(days=1)
        bare = [fire(i, f"Fire eval routine: eval bare {fixture} m1", old) for i in (1, 2)]
        pair = [fire(i, f"Fire eval routine: eval {fixture} m1", old) for i in (3, 4)]

        def empty(runs):
            cells = plan_week.eval_cells(ROOT / "evals", gates_doc, runs, now)
            return next(c for c in cells if c["fixture"] == fixture)["empty_fires"]
        self.assertEqual(empty(bare), 0)
        self.assertEqual(empty(pair), 2)

    def test_a_bare_fire_is_one_run_to_the_allowance_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            runs = [fire(1, "Fire eval routine: eval bare evals/writing-adrs/bootstrap m1",
                         NOW - timedelta(minutes=10))]
            # Not an improve fire, so never held at improve_charge.
            self.assertEqual(guard.improve_counts(runs, NOW), (0, 0))
            state = guard.account(tree, LIMITS, NOW, plan_week._fire_pair(runs, NOW),
                                  guard.improve_counts(runs, NOW))
            # One fire in the hold: one reservation, as an eval fire of both arms.
            self.assertAlmostEqual(state["pending"], guard.budget_file.run_reservation(LIMITS))
            pair = [fire(1, "Fire eval routine: eval evals/writing-adrs/bootstrap m1",
                         NOW - timedelta(minutes=10))]
            self.assertEqual(state, guard.account(tree, LIMITS, NOW,
                                                  plan_week._fire_pair(pair, NOW),
                                                  guard.improve_counts(pair, NOW)))
            self.assertIsNone(guard.check(state, "eval"))

    def test_evidence_start_times_bound_a_covered_improve_fire(self):
        # The planner passes the same evidence rows' start times to `account`.
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            run = tree / "routine-results" / "20261026T000000Z-abc123"
            path = run / "k" / "with_skill" / "summary.json"
            path.parent.mkdir(parents=True)
            snap_at = NOW - timedelta(hours=1)
            doc = {"usage": {"measured": {"meter": {"snapshots": [{
                "at": iso(snap_at), "info": {"unifiedWindows": {"seven_day": {
                    "utilization": 0.05,
                    "resetsAt": int((NOW + timedelta(days=1)).timestamp())}}}}]}}}}
            path.write_text(json.dumps(doc))
            runs = [fire(1, "Fire eval routine: improve a ", NOW - timedelta(days=1))]
            state = guard.account(tree, LIMITS, NOW, plan_week._fire_pair(runs, NOW),
                                  guard.improve_counts(runs, NOW),
                                  since=NOW - guard.WINDOW,
                                  improve_started=guard.improve_starts(runs, NOW))
            self.assertEqual(state["improve_covered"], 1)
            self.assertGreater(state["improve_charge"], 0.05)
            self.assertAlmostEqual(
                state["pending"], min(state["improve_charge"], 0.05), places=12)


class WatchdogTests(unittest.TestCase):
    """routine-eval-watchdog.yml: re-plan when a guard hold ends or a sweep
    has been idle WATCHDOG_IDLE, without overlapping sweeps (2026-11-01: a
    fire that never pushed results stalled evals 16:11 to 18:33 UTC)."""

    ANCHOR = datetime(2026, 11, 1, 16, 11, tzinfo=timezone.utc)

    def held_until(self, ends):
        """The start of a fire whose guard hold ends at `ends`."""
        return ends - guard.PENDING_FULL_HOLD

    @staticmethod
    def fire(started, conclusion="success"):
        return {"status": "completed", "conclusion": conclusion,
                "run_started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ")}

    @staticmethod
    def sweep(created, ended=None, status="completed"):
        stamp = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
        return {"status": status, "created_at": stamp(created),
                "updated_at": stamp(ended or created)}

    def test_the_stalled_fire_re_plans_two_minutes_after_its_hold(self):
        # The 2026-11-01 fire's hold ended at 16:40 (it started at 15:55,
        # under the 45-minute hold of the time).
        fires = [self.fire(self.held_until(datetime(2026, 11, 1, 16, 40, tzinfo=timezone.utc)))]
        due = plan_week.watchdog_due(self.ANCHOR, fires)
        self.assertEqual(due, datetime(2026, 11, 1, 16, 42, tzinfo=timezone.utc))
        self.assertEqual(plan_week.watchdog_decide([], fires, due, self.ANCHOR),
                         ("dispatch", due))
        self.assertEqual(plan_week.watchdog_decide([], fires, due - timedelta(seconds=1),
                                                   self.ANCHOR), ("wait", due))

    def test_ended_failed_and_unparsable_fires_fall_back_to_the_idle_limit(self):
        fires = [self.fire(self.held_until(self.ANCHOR)),
                 self.fire(self.ANCHOR - timedelta(minutes=5), conclusion="failure"),
                 {"conclusion": "success", "run_started_at": "not a time"}, "junk"]
        self.assertEqual(plan_week.watchdog_due(self.ANCHOR, fires),
                         self.ANCHOR + timedelta(minutes=50))

    def test_the_earliest_hold_wins(self):
        fires = [self.fire(self.held_until(self.ANCHOR + timedelta(minutes=35))),
                 self.fire(self.held_until(self.ANCHOR + timedelta(minutes=15)))]
        self.assertEqual(plan_week.watchdog_due(self.ANCHOR, fires),
                         self.ANCHOR + timedelta(minutes=17))

    def test_a_newer_sweep_stands_the_timer_down(self):
        newer = [self.sweep(self.ANCHOR + timedelta(minutes=3), status="queued")]
        self.assertEqual(plan_week.watchdog_decide(newer, [], self.ANCHOR + timedelta(hours=1),
                                                   self.ANCHOR), ("stand-down", None))

    def test_check_mode_anchors_on_the_newest_finished_sweep(self):
        sweeps = [self.sweep(self.ANCHOR - timedelta(minutes=5), self.ANCHOR),
                  self.sweep(self.ANCHOR - timedelta(hours=2), self.ANCHOR - timedelta(hours=1))]
        late = self.ANCHOR + timedelta(minutes=50)
        self.assertEqual(plan_week.watchdog_decide(sweeps, [], late), ("dispatch", late))
        self.assertEqual(plan_week.watchdog_decide(sweeps, [], late - timedelta(minutes=1)),
                         ("wait", late))
        running = [self.sweep(self.ANCHOR, status="in_progress"), *sweeps]
        self.assertEqual(plan_week.watchdog_decide(running, [], late), ("stand-down", None))
        self.assertEqual(plan_week.watchdog_decide([], [], late), ("dispatch", late))

    def test_wait_mode_sleeps_until_due_then_dispatches(self):
        clock = [self.ANCHOR]
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            clock[0] += timedelta(seconds=seconds)
        fires = [self.fire(self.held_until(self.ANCHOR + timedelta(minutes=29)))]
        go, reason = plan_week.watchdog("wait", lambda since: [], lambda since: fires,
                                        lambda: self.fail("wait mode reads no timers"),
                                        3300, lambda: clock[0], sleep)
        self.assertTrue(go, reason)
        self.assertEqual(slept, [31 * 60])

    def test_wait_mode_stands_down_when_a_sweep_starts_while_it_sleeps(self):
        clock = [self.ANCHOR]
        sweeps = []

        def sleep(seconds):
            clock[0] += timedelta(seconds=seconds)
            sweeps.append(self.sweep(self.ANCHOR + timedelta(minutes=1), status="in_progress"))
        go, _ = plan_week.watchdog("wait", lambda since: list(sweeps), lambda since: [],
                                   lambda: False, 3300, lambda: clock[0], sleep)
        self.assertFalse(go)

    def test_wait_mode_gives_up_at_max_wait(self):
        clock = [self.ANCHOR]

        def sleep(seconds):
            clock[0] += timedelta(seconds=seconds)
        go, reason = plan_week.watchdog("wait", lambda since: [], lambda since: [],
                                        lambda: False, 600, lambda: clock[0], sleep)
        self.assertFalse(go)
        self.assertIn("waited 600s", reason)

    def test_check_mode_stands_down_while_a_timer_is_armed_and_never_sleeps(self):
        never = lambda seconds: self.fail("check mode sleeps")  # noqa: E731
        go, reason = plan_week.watchdog("check", lambda since: [], lambda since: [],
                                        lambda: True, 3300, lambda: self.ANCHOR, never)
        self.assertFalse(go)
        self.assertIn("armed", reason)
        old = [self.sweep(self.ANCHOR - timedelta(hours=2), self.ANCHOR - timedelta(hours=1))]
        go, _ = plan_week.watchdog("check", lambda since: old, lambda since: [],
                                   lambda: False, 3300, lambda: self.ANCHOR, never)
        self.assertTrue(go)
        fresh = [self.sweep(self.ANCHOR - timedelta(minutes=5), self.ANCHOR)]
        go, _ = plan_week.watchdog("check", lambda since: fresh, lambda since: [],
                                   lambda: False, 3300, lambda: self.ANCHOR, never)
        self.assertFalse(go)

    def test_fetch_runs_reads_one_page_and_fails_closed(self):
        seen = []

        def get(path, token):
            seen.append(path)
            return {"workflow_runs": [{"id": 1}]}
        self.assertEqual(plan_week.fetch_runs("routine-eval-weekly.yml", "t",
                                              {"created": ">=2026-11-01T00:00:00Z"}, get),
                         [{"id": 1}])
        self.assertIn("/actions/workflows/routine-eval-weekly.yml/runs?created=%3E%3D2026",
                      seen[0])
        self.assertIn("per_page=100", seen[0])
        with self.assertRaises(io_mod.EvidenceError):
            plan_week.fetch_runs("routine-eval-weekly.yml", "t", {}, lambda p, t: {})

    def test_the_sweep_arms_the_watchdog_last_whatever_it_concluded(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-weekly.yml").read_text())
        job = doc["jobs"]["watchdog"]
        self.assertEqual(job["needs"], ["plan", "dispatch"])
        self.assertTrue(job["if"].startswith("always() && "))
        self.assertEqual(job["permissions"], {"actions": "write"})
        self.assertIn("gh workflow run routine-eval-watchdog.yml", job["steps"][0]["run"])
        self.assertEqual(doc["concurrency"], {"group": "routine-eval-weekly",
                                              "cancel-in-progress": False})

    def test_the_watchdog_workflow_shape(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-watchdog.yml").read_text())
        triggers = doc.get("on", doc.get(True))
        # workflow_run would be a fourth level after push, ingest and sweep.
        self.assertEqual(sorted(triggers), ["schedule", "workflow_dispatch"])
        self.assertEqual(doc["concurrency"], {
            "group": "routine-eval-watchdog-${{ github.event_name }}",
            "cancel-in-progress": True})
        self.assertEqual(doc["permissions"], {})
        job = doc["jobs"]["watch"]
        self.assertEqual(job["permissions"], {"contents": "read", "actions": "write"})
        self.assertGreater(job["timeout-minutes"] * 60, plan_week.WATCHDOG_MAX_WAIT)
        steps = {s.get("id"): s for s in job["steps"]}
        self.assertEqual(steps["watch"]["env"]["MODE"],
                         "${{ github.event_name == 'schedule' && 'check' || 'wait' }}")
        self.assertIn('plan_week.py watchdog --mode "$MODE"', steps["watch"]["run"])
        replan = job["steps"][-1]
        self.assertEqual(replan["if"], "steps.watch.outputs.dispatch == 'true'")
        self.assertIn("gh workflow run routine-eval-weekly.yml", replan["run"])
        for step in job["steps"]:
            self.assertNotIn("${{", step.get("run", ""))
        lock = (ROOT / ".github/workflows/actions.lock").read_text()
        self.assertIn("'.github/workflows/routine-eval-watchdog.yml':", lock)

    def test_main_writes_the_dispatch_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "out"
            out_file.write_text("")
            with mock.patch.object(plan_week, "watchdog", return_value=(True, "due")), \
                 mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(out_file), "GH_TOKEN": ""}), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plan_week.main(["watchdog", "--mode", "check"]), 0)
            self.assertEqual(out_file.read_text(), "dispatch=true\n")


@mock.patch.object(plan_week, "GUIDANCE_IMPROVE_HELD", False)
class ImproveCapPlanTests(unittest.TestCase):
    """#572, 2026-11-02: the planner applies the guard's improve cap
    (`allowance_guard.improve_cap`) to the improve band before allocation,
    item by item in allocate's order, so it never plans a fire the guard
    would refuse."""

    @staticmethod
    def cap_state(by_kind=None, in_flight=None):
        # 0.20 x 0.30 / 0.06 = 1 fire of both kinds together.
        return {"cap": 0.30, "improve_charge": 0.06, "improve_by_kind": by_kind or {},
                "improve_in_flight": in_flight or {}}

    @staticmethod
    def item(mode, name, rank):
        return {"mode": mode, "skill": name if mode == "improve" else "", "fixture": "",
                "model": "", "cost": 0.06, "order": (False, -rank, name)}

    def test_the_walk_counts_each_kept_item_as_the_guard_would(self):
        # The share allows 1 at week start: the first skill goes, the second
        # does not, and the guidance section takes its kind's floor.
        items = [self.item("guidance-improve", "sec", 1.0), self.item("improve", "b", 2.0),
                 self.item("improve", "a", 3.0)]
        kept, cut = plan_week.improve_capped(items, self.cap_state())
        self.assertEqual([(i["mode"], i["skill"]) for i in kept],
                         [("improve", "a"), ("guidance-improve", "")])
        self.assertEqual([i["skill"] for i in cut], ["b"])
        # The ctx's counts are copied, not changed.
        state = self.cap_state()
        plan_week.improve_capped(items, state)
        self.assertEqual(state["improve_by_kind"], {})

    def test_a_used_skill_floor_plans_the_guidance_fire_only(self):
        plan = plan_week.build_plan(ctx(
            skills={"a": skill()}, guidance={"sec": gsection(headroom=0.4)},
            guidance_use=100.0, improve_charge=0.06, room=1.0,
            improve_state=self.cap_state({"improve": 1})), NOW)
        self.assertEqual([f["mode"] for f in plan["fires"]], ["guidance-improve"])
        self.assertEqual(plan["improve_allowed"],
                         {"improve": False, "guidance-improve": True})
        # The cut skill fire is unplanned, not lost.
        self.assertEqual(plan["unplanned"]["improve"], 1)

    def test_an_in_flight_fire_uses_its_kind_floor(self):
        plan = plan_week.build_plan(ctx(
            skills={"a": skill()}, guidance={"sec": gsection(headroom=0.4)},
            guidance_use=100.0, improve_charge=0.06, room=1.0,
            improve_state=self.cap_state(in_flight={"guidance-improve": 1})), NOW)
        self.assertEqual([f["mode"] for f in plan["fires"]], ["improve"])

    def test_no_improve_state_means_no_cap(self):
        plan = plan_week.build_plan(ctx(skills={"a": skill(), "b": skill(), "c": skill()},
                                        improve_charge=0.06, room=1.0), NOW)
        self.assertEqual(len([f for f in plan["fires"] if f["mode"] == "improve"]), 3)
        self.assertIsNone(plan["improve_allowed"])
        self.assertEqual(plan["unplanned"]["improve"], 0)


class DocsTests(unittest.TestCase):

    def test_adr_0012_records_the_bare_baseline_addendum(self):
        text = (ROOT / "docs/decisions/0012-ab-runs-in-the-deployed-context-minus-the-subject.md"
                ).read_text()
        self.assertIn("## Bare baseline addendum (Adam, 2026-10-27)", text)
        self.assertIn("one time per model\nper version of model", text)
        self.assertIn("Ablation, the in-place pair of decision 1, stays the main approach", text)
        doc = (ROOT / "docs/how-it-works.md").read_text()
        self.assertIn("7. **Bare baselines**", doc)
        self.assertIn("bare-baseline-addendum-adam-2026-10-27", doc)

    def test_adr_0010_records_the_2026_10_26_addendum(self):
        text = (ROOT / "docs/decisions/0010-run-ai-eval-steps-in-a-routine-fired-by-actions.md"
                ).read_text()
        self.assertIn("Decision 4 addendum (2026-10-26)", text)
        self.assertIn("getting the closed loop completed and working for all aspects of "
                      "self-improvement", text)

    def test_agents_md_table_names_the_planner(self):
        text = (ROOT / "docs" / "workflows.md").read_text()
        row = next(line for line in text.splitlines()
                   if line.startswith("| `routine-eval-weekly.yml`"))
        self.assertIn("plan_week.py", row)

    def test_agents_md_table_names_the_watchdog(self):
        text = (ROOT / "docs" / "workflows.md").read_text()
        row = next(line for line in text.splitlines()
                   if line.startswith("| `routine-eval-watchdog.yml`"))
        self.assertIn("plan_week.py watchdog", row)

class SchedulabilityTests(unittest.TestCase):
    """Adam, 2026-11-02: an isolation cell (no `context:`), a null-pin cell and
    a private-registry cell are held: listed in eval_cells, in no band."""

    PRIVATE = "https://github.com/Adam-S-Daniel/adam-agentskills-private"
    IN_PLACE = {"revision": "a" * 40, "guidance_revision": "b" * 40}

    def setUp(self):
        import subprocess
        tmp = tempfile.TemporaryDirectory(prefix="schedulable-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        rows = {
            "iso": {"skill": "iso"},
            "pin": {"skill": "pin", "context": {**self.IN_PLACE, "guidance_revision": None}},
            "place": {"skill": "place", "context": self.IN_PLACE},
            "priv": {"skill": "priv", "registry": self.PRIVATE, "context": self.IN_PLACE},
            "rw": {"subject": "any", "draft": False, "prompt": "p"}}
        for name, doc in rows.items():
            path = self.root / "evals" / name / "a" / "fixture.yaml"
            path.parent.mkdir(parents=True)
            path.write_text(yaml.safe_dump(doc), encoding="utf-8")
        (self.root / "evals" / "scheduled.yml").write_text(yaml.safe_dump({"fixtures": [
            {"path": f"evals/{name}/a", "readiness": "invented"} for name in rows]}),
            encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "evals"], cwd=self.root, check=True)
        self.gates_doc = {"roster_models": ["m"], "skills": {}}

    def cells(self):
        return plan_week.eval_cells(self.root / "evals", self.gates_doc, [], NOW)

    def bands(self, cells, **over):
        return plan_week.eval_items(ctx(cells=cells, model_weights={"m": 1.0}, **over), NOW)[0]

    def test_held_cells_stay_in_the_list_with_a_reason(self):
        got = {c["skill"]: (c["schedulable"], c["hold_reason"]) for c in self.cells()}
        self.assertEqual(got, {"iso": (False, "no context"), "pin": (False, "null pin"),
                               "place": (True, None), "priv": (False, "private, paused")})

    def test_held_cells_enter_no_band_but_an_in_place_cell_does(self):
        bands = self.bands(self.cells())
        queued = [i["skill"] for items in bands.values() for i in items]
        self.assertEqual(queued, ["place"])

    def test_an_isolation_cell_of_a_skill_with_a_removal_pr_enters_no_band(self):
        bands = self.bands(self.cells(), removal_prs=["iso", "place"])
        self.assertEqual([(b, i["skill"]) for b, items in bands.items() for i in items],
                         [("safety", "place")])

    def test_a_bare_fire_is_kept_for_a_held_cell(self):
        cells = self.cells()
        plan = plan_week.build_plan(ctx(cells=cells, model_weights={"m": 1.0}, room=1.0,
                                        bare=[{"fixture": "evals/iso/a", "model": "m",
                                               "skill": "iso"}]), NOW)
        self.assertEqual([(f["band"], f["arms"], f["fixture"]) for f in plan["fires"]],
                         [("missing", "both", "evals/place/a"),
                          ("bare", "bare", "evals/iso/a")])

    def test_a_subject_any_row_neither_crashes_nor_plans_and_is_listed(self):
        self.assertFalse([c for c in self.cells() if c["fixture"] == "evals/rw/a"])
        self.assertEqual(plan_week.real_work_rows(self.root / "evals"), ["evals/rw/a"])
        plan = plan_week.build_plan(ctx(real_work=["evals/rw/a"]), NOW)
        lines = [l for l in plan_week.summary_lines(plan) if "evals/rw/a" in l]
        self.assertEqual(len(lines), 1)
        self.assertIn("Real-work row, not planned by the skill planner", lines[0])

    def test_validate_fire_refuses_a_held_both_arms_leg_only(self):
        def leg(name, arms="both"):
            return {"MODE": "eval", "ARMS": arms, "FIXTURE": f"evals/{name}/a",
                    "EVAL_KEY": f"{name}/a", "MODEL": "claude-opus-5-5", "SKILL": "",
                    "HOLDOUT": ""}
        roster = mock.patch.object(plan_week.roster_arm, "is_arm", return_value=True) \
            if hasattr(plan_week, "roster_arm") else mock.patch("roster_arm.is_arm",
                                                                 return_value=True)
        with roster:
            plan_week.validate_fire(leg("place"), self.root)
            plan_week.validate_fire(leg("iso", "bare") | {"FIXTURE": "evals/place/a",
                                                          "EVAL_KEY": "place/a"}, self.root)
            for name in ("iso", "pin", "priv"):
                with self.assertRaises(plan_week.PlanError, msg=name):
                    plan_week.validate_fire(leg(name), self.root)

    def test_a_private_cell_leaves_no_name_in_a_public_output(self):
        cells = self.cells()
        plan = plan_week.build_plan(ctx(cells=cells, model_weights={"m": 1.0}, room=1.0,
                                        real_work=plan_week.real_work_rows(self.root / "evals")),
                                    NOW)
        text = json.dumps(plan) + "\n".join(plan_week.summary_lines(plan))
        self.assertNotIn("priv", text)
        self.assertNotIn("private", text)


if __name__ == "__main__":
    unittest.main()
