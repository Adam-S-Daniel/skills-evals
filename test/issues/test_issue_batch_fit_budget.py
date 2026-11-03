#!/usr/bin/env python3
"""The two-week batch fitted to its budget (scripts/plan_week.py, THE
BATCH; Adam's 2026-11-03 decision, "Fit the batch to the budget": "The rate
is measured each period. The batch takes as many subjects as fit 50 points,
most-used first. The rest wait. No new spend.").

Hermetic: invented subjects, histories in throwaway local git repositories
with fixed commit times, `now` passed in; no network and no sleeps.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import gates  # noqa: E402
import plan_week  # noqa: E402

START = datetime(2026, 11, 9, 17, 0, 0, tzinfo=timezone.utc)
NOW = START + timedelta(hours=1)
WEEK = timedelta(weeks=1)
# Exact binary fractions, so sums at the budget compare exactly.
PAIR = 1 / 64          # allowance fraction per pair on model "heavy"
PAIRS = 4.0            # pairs per cell
CELL = PAIR * PAIRS    # 0.0625: one cell with headroom
POLICY = {"start": START, "period": timedelta(days=14), "multiplier": 3.0,
          "rates": {"skill": 0.75, "guidance": 0.5}, "rate_window": timedelta(days=28),
          "pairs_per_cell": PAIRS, "cost_window": timedelta(days=14)}
GATE_POLICY = gates.load_gate_policy()["skills"]


def scell(name, fixture="a", model="heavy", cls="missing", verdict=None, **over):
    base = {"skill": name, "section": None, "fixture": f"evals/{name}/{fixture}",
            "model": model, "class": cls, "verdict": verdict, "with_runs": 0,
            "without_runs": 0, "newest": None, "usd_per_fire": None, "empty_fires": 0}
    base.update(over)
    return base


def gcell(section, fixture="a", model="heavy", **over):
    base = {"skill": "", "section": section, "fixture": f"evals/guidance/{section}/{fixture}",
            "model": model, "class": "missing", "verdict": "insufficient", "with_runs": 0,
            "without_runs": 0, "newest": None, "usd_per_fire": None, "empty_fires": 0,
            "objective": None, "judge": None, "judge_carried": False, "reason": None,
            "with_counted": 0, "without_counted": 0}
    base.update(over)
    return base


def measured(skill=3.0, guidance=1.0):
    return {"skill": {"rate": skill, "source": "measured", "added": 6, "weeks": 2.0,
                      "since": "2026-10-26T18:00:00Z"},
            "guidance": {"rate": guidance, "source": "measured", "added": 2, "weeks": 2.0,
                         "since": "2026-10-26T18:00:00Z"}}


def ctx(cells, budget=4 * CELL, previous=None, weights=None, costs=None, rates=None):
    return {"policy": GATE_POLICY, "reservation": 0.035, "overrun": 0.005,
            "improve_charge": 0.10, "room": 1.0, "points_per_usd": None,
            "model_weights": {"heavy": 0.9}, "removal_prs": [], "cells": cells,
            "skills": {}, "lessons": [], "batch_policy": POLICY, "previous_batch": previous,
            "batch_rates": rates or measured(), "batch_budget": budget,
            "batch_pair_costs": {"heavy": PAIR} if costs is None else costs,
            "skill_weights": weights or {}}


def record(number, members, started=NOW):
    return {"schema_version": 1, "number": number, "started_at": plan_week._iso(started),
            "due_at": plan_week._iso(started + timedelta(days=14)),
            "sizes": {"skill": 2, "guidance": 2}, "multiplier": 3.0,
            "rates": {"skill": 0.75, "guidance": 0.5},
            "members": [{"kind": k, "subject": s, "joined": j} for k, s, j in members],
            "previous": None}


def names(batch):
    return [(m["kind"], m["subject"]) for m in batch["record"]["members"]]


def git(repo, *args, when=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "Example", "GIT_AUTHOR_EMAIL": "a@example.com",
           "GIT_COMMITTER_NAME": "Example", "GIT_COMMITTER_EMAIL": "a@example.com",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    if when is not None:
        stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
        env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout


def history_repo(base: Path, path: str, versions: list) -> Path:
    """A local repository whose main branch commits `path` with each
    (time, text) of `versions` in turn."""
    repo = base / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    for when, text in versions:
        target.write_text(text)
        git(repo, "add", path)
        git(repo, "commit", "-q", "-m", "update", when=when)
    return repo


def layout(*skills):
    return json.dumps({"plugins": {"one": {"skills": sorted(skills)}}}, indent=2) + "\n"


def coverage(*ids):
    return yaml.safe_dump([{"id": i, "heading": i, "status": "gap"} for i in ids])


class RateTests(unittest.TestCase):
    """The addition rate, measured from a synthetic history."""

    def test_additions_over_the_window_per_week(self):
        versions = [(NOW - timedelta(days=60), frozenset({"a", "b"})),
                    (NOW - timedelta(days=30), frozenset({"a", "b", "c"})),
                    (NOW - timedelta(days=10), frozenset({"a", "b", "c", "d", "e"}))]
        rate = plan_week.addition_rate(versions, NOW, timedelta(days=28))
        # Baseline: the version at the window's start ({a, b, c}); 2 added in 4 weeks.
        self.assertEqual(rate, {"rate": 0.5, "added": 2, "weeks": 4.0,
                                "since": plan_week._iso(NOW - timedelta(days=28))})

    def test_a_file_younger_than_the_window_is_measured_from_its_first_version(self):
        # A bulk import is the baseline, never a burst of additions.
        versions = [(NOW - timedelta(days=14), frozenset({"a", "b", "c", "d"})),
                    (NOW - timedelta(days=3), frozenset({"a", "b", "c", "d", "e", "f"}))]
        rate = plan_week.addition_rate(versions, NOW, timedelta(days=28))
        self.assertEqual((rate["added"], rate["weeks"], rate["rate"]), (2, 2.0, 1.0))

    def test_removals_are_not_subtracted_and_later_versions_are_ignored(self):
        versions = [(NOW - timedelta(days=40), frozenset({"a", "b"})),
                    (NOW - timedelta(days=7), frozenset({"b", "c"})),
                    (NOW + timedelta(days=1), frozenset({"b", "c", "d", "e"}))]
        rate = plan_week.addition_rate(versions, NOW, timedelta(days=28))
        self.assertEqual(rate["added"], 1)

    def test_too_short_a_history_is_no_rate(self):
        versions = [(NOW - timedelta(days=6), frozenset({"a"})), (NOW, frozenset({"a", "b"}))]
        self.assertIsNone(plan_week.addition_rate(versions, NOW, timedelta(days=28)))
        self.assertIsNone(plan_week.addition_rate(
            [(NOW + timedelta(days=1), frozenset({"a"}))], NOW, timedelta(days=28)))

    def test_versions_are_read_from_the_first_parent_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = history_repo(Path(tmp), plan_week.BATCH_SKILL_HISTORY, [
                (NOW - timedelta(days=21), layout("a", "b")),
                (NOW - timedelta(days=7), layout("a", "b", "c"))])
            # A side branch's commit lands on main at its merge's time.
            git(repo, "checkout", "-q", "-b", "side")
            (repo / plan_week.BATCH_SKILL_HISTORY).write_text(layout("a", "b", "c", "d"))
            git(repo, "commit", "-q", "-am", "add d", when=NOW - timedelta(days=6))
            git(repo, "checkout", "-q", "main")
            git(repo, "merge", "-q", "--no-ff", "-m", "merge", "side",
                when=NOW - timedelta(days=2))
            versions = plan_week.history_versions(repo, plan_week.BATCH_SKILL_HISTORY,
                                                  plan_week.layout_skills)
        self.assertEqual([t for t, _ in versions], [NOW - timedelta(days=21),
                                                    NOW - timedelta(days=7),
                                                    NOW - timedelta(days=2)])
        self.assertEqual(versions[-1][1], frozenset({"a", "b", "c", "d"}))
        rate = plan_week.addition_rate(versions, NOW, timedelta(days=28))
        self.assertEqual((rate["added"], rate["weeks"]), (2, 3.0))

    def test_guidance_sections_are_the_coverage_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = history_repo(Path(tmp), plan_week.BATCH_GUIDANCE_HISTORY, [
                (NOW - timedelta(days=35), coverage("s-one", "s-two")),
                (NOW - timedelta(days=5), coverage("s-one", "s-two", "s-three"))])
            histories = plan_week.addition_histories({}, repo)
        rates = plan_week.batch_rates(POLICY, histories, NOW)
        self.assertEqual(rates["guidance"]["source"], "measured")
        self.assertEqual(rates["guidance"]["rate"], 0.25)  # 1 added over 4 weeks

    def test_the_measured_rate_sets_the_target_size(self):
        rates = {"skill": 3.4, "guidance": 0.75}
        self.assertEqual(plan_week.batch_sizes(POLICY, rates), {"skill": 10, "guidance": 2})
        self.assertEqual(plan_week.batch_sizes(POLICY, {"skill": 0.0, "guidance": 0.1}),
                         {"skill": 1, "guidance": 1})


class FallbackTests(unittest.TestCase):
    """An unreadable history falls back to the policy's constant, and says so."""

    def test_no_checkout_uses_the_policy_constant(self):
        histories = plan_week.addition_histories({}, None)
        self.assertEqual(set(histories), {"skill", "guidance"})
        rates = plan_week.batch_rates(POLICY, histories, NOW)
        for kind in ("skill", "guidance"):
            self.assertEqual(rates[kind]["source"], "policy")
            self.assertEqual(rates[kind]["rate"], POLICY["rates"][kind])
            self.assertIn("no checkout holds", rates[kind]["reason"])

    def test_a_shallow_checkout_is_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = history_repo(Path(tmp), plan_week.BATCH_SKILL_HISTORY, [
                (NOW - timedelta(days=21), layout("a")),
                (NOW - timedelta(days=7), layout("a", "b"))])
            shallow = Path(tmp) / "shallow"
            git(Path(tmp), "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow))
            histories = plan_week.addition_histories(
                {"adam-agentskills": {"path": shallow}}, None)
        rates = plan_week.batch_rates(POLICY, histories, NOW)
        self.assertEqual(rates["skill"], {
            "rate": 0.75, "source": "policy",
            "reason": "the history of scripts/plugin_layout.json is unreadable"})

    def test_a_malformed_version_or_absent_file_is_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = history_repo(Path(tmp), plan_week.BATCH_SKILL_HISTORY, [
                (NOW - timedelta(days=21), "{not json")])
            with self.assertRaises(plan_week.PlanError):
                plan_week.history_versions(repo, plan_week.BATCH_SKILL_HISTORY,
                                           plan_week.layout_skills)
            with self.assertRaises(plan_week.PlanError):
                plan_week.history_versions(repo, "absent.json", plan_week.layout_skills)

    def test_a_short_history_falls_back(self):
        rates = plan_week.batch_rates(POLICY, {
            "skill": [(NOW - timedelta(days=2), frozenset({"a"}))],
            "guidance": "the history of agents-md/eval-coverage.yml is unreadable"}, NOW)
        self.assertEqual(rates["skill"]["source"], "policy")
        self.assertIn("shorter", rates["skill"]["reason"])
        self.assertEqual(rates["guidance"]["reason"],
                         "the history of agents-md/eval-coverage.yml is unreadable")

    def test_the_fallback_is_recorded_in_the_batch(self):
        rates = plan_week.batch_rates(POLICY, plan_week.addition_histories({}, None), NOW)
        batch = plan_week.batch_state(ctx([scell("a")], rates=rates), NOW)
        rec = batch["record"]
        self.assertEqual(rec["rates"], {"skill": 0.75, "guidance": 0.5})
        self.assertEqual(rec["sizes"], {"skill": 2, "guidance": 2})
        self.assertEqual(rec["rate_basis"]["skill"]["source"], "policy")


class FitTests(unittest.TestCase):
    """Most-used first, within the budget, skipping what alone overflows."""

    def test_most_used_first_within_the_budget(self):
        cells = [scell("light"), scell("heavy-use"), scell("mid"), scell("unknown")]
        weights = {"light": 1, "heavy-use": 9, "mid": 5, "unknown": None}
        batch = plan_week.batch_state(ctx(cells, budget=3 * CELL, weights=weights), NOW)
        # Unknown use is neutral (the median known weight, 5): it ties with
        # "mid" and loses on name.
        self.assertEqual(names(batch), [("skill", "heavy-use"), ("skill", "mid"),
                                        ("skill", "unknown")])
        self.assertEqual([(w["subject"], w["reason"]) for w in batch["record"]["waiting"]],
                         [("light", "budget")])

    def test_a_subject_too_dear_for_the_room_is_skipped_for_a_cheaper_one(self):
        dear = [scell("dear", fixture=f) for f in ("a", "b", "c")]  # 3 cells
        cells = [scell("first"), *dear, scell("cheap")]
        weights = {"first": 9, "dear": 8, "cheap": 1}
        batch = plan_week.batch_state(ctx(cells, budget=2 * CELL, weights=weights), NOW)
        self.assertEqual(names(batch), [("skill", "first"), ("skill", "cheap")])
        self.assertEqual(batch["record"]["waiting"], [
            {"kind": "skill", "subject": "dear", "cost": 3 * CELL, "reason": "budget"}])

    def test_the_target_size_still_caps_a_kind(self):
        cells = [scell(f"s{i}") for i in range(4)] + [gcell("g1"), gcell("g2")]
        rates = measured(skill=0.5, guidance=0.1)  # targets 2 and 1
        batch = plan_week.batch_state(ctx(cells, budget=10 * CELL, rates=rates), NOW)
        self.assertEqual(names(batch), [("skill", "s0"), ("skill", "s1"),
                                        ("guidance", "g1")])
        self.assertEqual({w["reason"] for w in batch["record"]["waiting"]}, {"size"})

    def test_the_kinds_take_turns(self):
        # A long list of skills cannot spend the budget before a section.
        cells = [scell(f"s{i}") for i in range(5)] + [gcell("g1")]
        batch = plan_week.batch_state(ctx(cells, budget=2 * CELL), NOW)
        self.assertEqual(names(batch), [("skill", "s0"), ("guidance", "g1")])

    def test_only_cells_with_headroom_are_priced(self):
        cells = [scell("x", fixture="a"), scell("x", fixture="b", cls="ceiling",
                                                verdict="insufficient"),
                 scell("x", fixture="c", model="light"),
                 scell("x", fixture="d", empty_fires=plan_week.BROKEN_AFTER_FIRES)]
        costs = {"heavy": PAIR, "light": PAIR / 4}
        self.assertEqual(plan_week.subject_cost(cells, costs, PAIRS), CELL + CELL / 4)
        # A model with no measured cost is priced at the dearest measured one.
        self.assertEqual(plan_week.subject_cost([scell("y", model="new")], costs, PAIRS), CELL)
        self.assertIsNone(plan_week.subject_cost(cells, {}, PAIRS))

    def test_nothing_fits_so_the_cheapest_joins(self):
        cells = [scell("big", fixture="a"), scell("big", fixture="b"), scell("small")]
        batch = plan_week.batch_state(ctx(cells, budget=CELL / 2,
                                          weights={"big": 9, "small": 1}), NOW)
        self.assertEqual(names(batch), [("skill", "small")])
        self.assertTrue(batch["record"]["fit"]["floor"])
        self.assertEqual(batch["record"]["fit"]["total"], CELL)

    def test_no_measured_cost_picks_by_size_alone(self):
        cells = [scell("a"), scell("b"), scell("c")]
        batch = plan_week.batch_state(ctx(cells, budget=CELL, costs={},
                                          rates=measured(skill=0.5)), NOW)
        self.assertEqual(names(batch), [("skill", "a"), ("skill", "b")])
        fit = batch["record"]["fit"]
        self.assertFalse(fit["priced"])
        self.assertIsNone(fit["total"])
        self.assertEqual(fit["reason"], "no cost per pair measured for any roster model")


class BoundaryTests(unittest.TestCase):

    def test_a_total_equal_to_the_budget_fits_and_one_more_does_not(self):
        cells = [scell("a"), scell("b"), scell("c")]
        weights = {"a": 3, "b": 2, "c": 1}
        batch = plan_week.batch_state(ctx(cells, budget=2 * CELL, weights=weights), NOW)
        self.assertEqual(names(batch), [("skill", "a"), ("skill", "b")])
        self.assertEqual(batch["record"]["fit"]["total"], 2 * CELL)
        self.assertEqual([w["subject"] for w in batch["record"]["waiting"]], ["c"])
        # One pair short of the second subject's cost: it waits.
        short = plan_week.batch_state(ctx(cells, budget=2 * CELL - PAIR, weights=weights), NOW)
        self.assertEqual(names(short), [("skill", "a")])


class CarryTests(unittest.TestCase):

    def test_carried_members_join_first_and_their_cost_counts(self):
        previous = record(1, [("skill", "slow", 1), ("guidance", "g-slow", 1),
                              ("skill", "done", 1)])
        cells = [scell("slow", cls="insufficient"), gcell("g-slow", cls="insufficient"),
                 scell("done", cls="keep", verdict="keep"), scell("popular"), scell("other")]
        due = NOW + timedelta(days=14)
        batch = plan_week.batch_state(ctx(cells, budget=3 * CELL, previous=previous,
                                          weights={"popular": 9, "slow": 0, "other": 1}),
                                      due)
        rec = batch["record"]
        self.assertTrue(batch["started"])
        self.assertEqual([(m["kind"], m["subject"], m["joined"]) for m in rec["members"]], [
            ("skill", "slow", 1), ("guidance", "g-slow", 1), ("skill", "popular", 2)])
        self.assertEqual(rec["fit"]["total"], 3 * CELL)
        self.assertEqual(rec["waiting"], [
            {"kind": "skill", "subject": "other", "cost": CELL, "reason": "budget"}])

    def test_carried_members_stay_even_over_budget(self):
        previous = record(1, [("skill", "slow", 1)])
        cells = [scell("slow", fixture=f) for f in ("a", "b", "c")] + [scell("new")]
        batch = plan_week.batch_state(ctx(cells, budget=CELL, previous=previous),
                                      NOW + timedelta(days=14))
        self.assertEqual(names(batch), [("skill", "slow")])
        self.assertEqual(batch["record"]["fit"]["total"], 3 * CELL)
        self.assertFalse(batch["record"]["fit"]["floor"])
        self.assertEqual(batch["record"]["waiting"][0]["subject"], "new")


class RecordTests(unittest.TestCase):

    def test_the_record_carries_the_audit_fields(self):
        cells = [scell("a"), scell("b", fixture="x"), scell("b", fixture="y"), gcell("g")]
        batch = plan_week.batch_state(ctx(cells, budget=2 * CELL,
                                          weights={"a": 2, "b": 1}), NOW)
        rec = batch["record"]
        self.assertEqual(rec["rates"], {"skill": 3.0, "guidance": 1.0})
        self.assertEqual(rec["rate_basis"], measured())
        self.assertEqual(rec["sizes"], {"skill": 9, "guidance": 3})
        self.assertEqual(rec["fit"], {"budget": 2 * CELL, "pairs_per_cell": PAIRS,
                                      "pair_costs": {"heavy": PAIR}, "priced": True,
                                      "total": 2 * CELL, "floor": False})
        self.assertEqual(rec["members"], [
            {"kind": "skill", "subject": "a", "joined": 1, "cost": CELL},
            {"kind": "guidance", "subject": "g", "joined": 1, "cost": CELL}])
        self.assertEqual(rec["waiting"], [
            {"kind": "skill", "subject": "b", "cost": 2 * CELL, "reason": "budget"}])
        # The record is valid JSON and the planner reads it back.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "batches").mkdir()
            (Path(tmp) / plan_week.BATCH_RECORD).write_text(json.dumps(rec))
            self.assertEqual(plan_week.read_batch(Path(tmp)), rec)

    def test_the_summary_names_the_fit(self):
        plan = plan_week.build_plan(ctx([scell("a"), scell("b"), scell("c")],
                                        budget=2 * CELL), NOW)
        lines = "\n".join(plan_week.summary_lines(plan))
        self.assertIn("Batch fit: rates skill 3.00/week (measured), guidance 1.00/week "
                      "(measured); target sizes skill 9, guidance 3; 12.5 of 12.5 points; "
                      "1 subject(s) wait", lines)


class CostTests(unittest.TestCase):
    """Each roster model's measured cost per pair, from cost_estimate.json."""

    def run_record(self, run_id, model, role, scored, stamp="20261105T120000Z"):
        return {"path": f"routine-results/{run_id}/skill/{stamp}", "model": model,
                "role": role, "timestamp": stamp,
                "trials": [{"scored": True}] * scored + [{"scored": False}]}

    def test_points_over_pairs_per_model(self):
        records = [self.run_record("r1", "heavy", "with", 3),
                   self.run_record("r1", "heavy", "without", 3),
                   self.run_record("r2", "heavy", "with", 1),
                   self.run_record("r2", "heavy", "without", 1),
                   self.run_record("r3", "light", "with", 2),
                   self.run_record("r3", "light", "without", 2),
                   # Two models in one run: not attributable.
                   self.run_record("r4", "heavy", "with", 1),
                   self.run_record("r4", "light", "without", 1),
                   # Outside the window.
                   self.run_record("r5", "heavy", "with", 1, stamp="20261001T120000Z"),
                   # No points in its estimate.
                   self.run_record("r6", "light", "with", 1),
                   # No estimate at all.
                   self.run_record("r7", "light", "with", 1),
                   # Not a routine run.
                   {**self.run_record("r8", "heavy", "with", 1),
                    "path": "results/r8/skill/x"}]
        points = {"r1": 0.006, "r2": 0.002, "r3": 0.001, "r4": 0.5, "r5": 0.5, "r6": None,
                  "r8": 0.5}
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            for run_id, value in points.items():
                (tree / "routine-results" / run_id).mkdir(parents=True)
                (tree / "routine-results" / run_id / "cost_estimate.json").write_text(
                    json.dumps({"schema_version": 1, "points": value}))
            costs = plan_week.pair_costs(records, tree, NOW, timedelta(days=14))
        self.assertEqual(set(costs), {"heavy", "light"})
        self.assertAlmostEqual(costs["heavy"], 0.008 / 4)
        self.assertAlmostEqual(costs["light"], 0.001 / 2)


class PolicyTests(unittest.TestCase):

    def test_the_committed_policy_carries_the_fit_settings(self):
        policy = plan_week.load_batch_policy(ROOT / "evals/batch-policy.yml")
        self.assertEqual(policy["rate_window"], timedelta(days=28))
        self.assertEqual(policy["cost_window"], timedelta(days=14))
        self.assertEqual(policy["pairs_per_cell"], 45.0)
        self.assertEqual(policy["rates"], {"skill": 0.75, "guidance": 0.5})

    def test_malformed_fit_settings_stop_the_plan(self):
        good = yaml.safe_load((ROOT / "evals/batch-policy.yml").read_text())
        bad = [{**good, "rate_window_days": 3}, {**good, "rate_window_days": 1.5},
               {**good, "cost_window_days": 0}, {**good, "pairs_per_cell": 0},
               {**good, "pairs_per_cell": "many"},
               {k: v for k, v in good.items() if k != "pairs_per_cell"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "batch-policy.yml"
            for doc in bad:
                path.write_text(yaml.safe_dump(doc))
                with self.subTest(doc=doc), self.assertRaises(plan_week.PlanError):
                    plan_week.load_batch_policy(path)


class GatherTests(unittest.TestCase):
    """What the weekly plan feeds the batch, from checkouts on disk."""

    def test_batch_inputs_measure_rates_budget_and_costs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "skills").mkdir()
            (base / "guide").mkdir()
            skills = history_repo(base / "skills", plan_week.BATCH_SKILL_HISTORY, [
                (NOW - timedelta(days=40), layout("a", "b")),
                (NOW - timedelta(days=4), layout("a", "b", "c", "d"))])
            guide = history_repo(base / "guide", plan_week.BATCH_GUIDANCE_HISTORY, [
                (NOW - timedelta(days=40), coverage("s1"))])
            (base / "tree").mkdir()
            (base / "evals").mkdir()
            args = argparse.Namespace(batch_policy=ROOT / "evals/batch-policy.yml",
                                      guidance=guide, results_tree=base / "tree",
                                      evals_dir=base / "evals",
                                      as_of="2026-11-09T18:00:00+00:00")
            inputs = plan_week.batch_inputs(
                args, {"adam-agentskills": {"path": skills}}, {"weekly_cap": 0.25}, NOW)
        self.assertEqual(inputs["batch_budget"], 0.5)
        self.assertEqual(inputs["batch_rates"]["skill"]["rate"], 0.5)  # 2 in 4 weeks
        self.assertEqual(inputs["batch_rates"]["guidance"]["rate"], 0.0)
        self.assertEqual(inputs["batch_pair_costs"], {})
        self.assertIsNone(inputs["previous_batch"])

    def test_without_the_policy_there_are_no_batch_inputs(self):
        args = argparse.Namespace(batch_policy=None)
        self.assertEqual(plan_week.batch_inputs(args, {}, {"weekly_cap": 0.25}, NOW), {
            "batch_policy": None, "previous_batch": None, "batch_rates": None,
            "batch_budget": None, "batch_pair_costs": None})


if __name__ == "__main__":
    unittest.main()
