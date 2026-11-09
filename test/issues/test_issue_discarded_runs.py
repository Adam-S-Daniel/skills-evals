#!/usr/bin/env python3
"""Discarded runs (Adam, 2026-11-07): every subject's verdict reports the
recorded arm runs it does not count, by reason, with their cost
(harness/gates.py, DISCARDED RUNS; scripts/compute_gates.py; the explorer's
`discarded_runs`).

Each reason slug gets a test that a run dropped for it is counted under it,
and that the runs the verdict does count are not counted as discarded (the
two always add up to every run given).

Hermetic and deterministic: canned runs and a temporary results tree, no
network, no clock.
"""

from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import explorer_data  # noqa: E402
import gates  # noqa: E402
import test_issue_70_retirement as t70  # noqa: E402
from test_issue_70_retirement import (  # noqa: E402
    EXPECT, FLAT, FLAT_JUDGE, TEST_POLICY, arm_run, series, stamp, trial)
from test_issue_557_stratified_verdict import EXPECT as SECTION, MAIN, OLD, stratum  # noqa: E402
from test_issue_72_explorer_data import MANIFEST, Tree  # noqa: E402

MODELS = ["model-a"]
POOLED = {**TEST_POLICY, "rest_policy": "pooled-with-current-guard", "rest_guard_min_pairs": 6}
CURRENT = {**TEST_POLICY, "rest_policy": "current"}


def pairs(n, start=0, **kw):
    """`n` counted pairs of one cell (both arms FLAT)."""
    return (series("with", FLAT[:n], FLAT_JUDGE, start=start, **kw)
            + series("without", FLAT[:n], FLAT_JUDGE, start=start, **kw))


def skill_verdict(runs, policy=TEST_POLICY, expect=EXPECT, models=MODELS):
    return gates.retirement({"runs": runs}, list(models), "demo", policy, expect)


def section_verdict(runs, policy=POOLED, expect=SECTION):
    return gates.guidance_verdict({"runs": runs}, MODELS, "sec", policy, expect)


def counted(verdict):
    """The runs the verdict counts: both runs of each pair in a cell's window
    that has a run mean on both arms, in a cell the verdict reads."""
    cells = verdict["cells"] + ((verdict.get("alone") or {}).get("cells") or [])
    return sum(2 * len(c["with"]["run_means"]) for c in cells
               if "pairs_used" in c and c["class"] != "cannot-discriminate")


def reasons(verdict):
    return {slug: row["runs"] for slug, row in verdict["discarded_runs"]["by_reason"].items()}


class GateReasonTests(unittest.TestCase):
    """The reasons harness/gates.py decides: pooling and inside a cell."""

    def check(self, runs, want, verdict=None, **kw):
        verdict = verdict or skill_verdict(runs, **kw)
        self.assertEqual(reasons(verdict), want)
        self.assertEqual(verdict["discarded_runs"]["total"], sum(want.values()))
        # Counted and discarded never overlap and cover every run given.
        self.assertEqual(counted(verdict) + verdict["discarded_runs"]["total"], len(runs))
        for slug in want:
            self.assertIn(slug, gates.DISCARD_REASONS)
        return verdict

    def test_counted_runs_are_not_discarded(self):
        verdict = self.check(pairs(4), {})
        self.assertEqual(counted(verdict), 8)
        self.assertEqual(verdict["discarded_runs"],
                         {"total": 0, "cost_usd": 0.0, "cost_unknown": 0, "by_reason": {}})

    def test_fixture_off_main(self):
        self.check(pairs(3) + pairs(2, start=10, fixture="gone"), {"fixture_off_main": 4})

    def test_model_off_roster(self):
        self.check(pairs(3) + pairs(1, start=10, model="model-old"), {"model_off_roster": 2})

    def test_content_unknown(self):
        # No registry copy: the with arms are not pooled and the cell's key is
        # incomplete, so its without arms are not counted either.
        unknown = {"": {"fixture_digest": "f1", "tested_digest": None}}
        verdict = self.check(pairs(3), {"content_unknown": 6}, expect=unknown)
        self.assertEqual(verdict["cells"][0]["class"], "insufficient")

    def test_fixture_changed(self):
        self.check(pairs(3) + pairs(2, start=10, fdig="f0"), {"fixture_changed": 4})

    def test_subject_changed(self):
        # Only the with arm holds the subject; its without partner then has
        # no counted partner.
        old = series("with", FLAT[:2], FLAT_JUDGE, start=10, tested="t0")
        partners = series("without", FLAT[:2], FLAT_JUDGE, start=10)
        self.check(pairs(3) + old + partners, {"subject_changed": 2, "unpaired": 2})

    def test_context_unknown(self):
        runs = pairs(1, start=10)
        for run in runs:
            run["arm_context_digest"] = None
        self.check(pairs(3) + runs, {"context_unknown": 2})

    def test_context_unmatched(self):
        # A smaller group under another pair key loses the joint choice.
        self.check(pairs(3) + pairs(2, start=10, pair="q"), {"context_unmatched": 4})

    def test_no_check_results(self):
        bare = [arm_run("with", [trial(0, 0)], 10), arm_run("without", [trial(80, 100)], 10)]
        # The cell's skip reason, and the without arm left without a partner.
        self.check(pairs(3) + bare, {"no_check_results": 1, "unpaired": 1})

    def test_no_scored_trials(self):
        infra = [arm_run("with", [trial(80, 100, infra=True)], 10),
                 arm_run("without", [trial(80, 100)], 10)]
        self.check(pairs(3) + infra, {"no_scored_trials": 1, "unpaired": 1})

    def test_unpaired(self):
        lone = series("with", FLAT[:2], FLAT_JUDGE, start=10)
        self.check(pairs(3) + lone, {"unpaired": 2})

    def test_over_cap(self):
        policy = {**TEST_POLICY, "max_runs_per_cell": 3}
        verdict = self.check(pairs(5), {"over_cap": 4}, policy=policy)
        self.assertEqual(verdict["cells"][0]["pairs_used"], 3)

    def test_no_objective_score(self):
        # A judge-only cell: counted runs, but no run mean to bet on.
        judge_only = [arm_run(role, [trial(0, 0, overall=7.0)], r)
                      for r in range(3) for role in ("with", "without")]
        self.check(judge_only, {"no_objective_score": 6})

    def test_cannot_discriminate(self):
        zero = [(0, 0, 0)] * 4
        verdict = self.check(series("with", zero, start=0) + series("without", zero, start=0),
                             {"cannot_discriminate": 8})
        self.assertEqual(verdict["cells"][0]["class"], "cannot-discriminate")

    def test_rest_changed_only_under_the_current_rest_policy(self):
        runs = stratum(OLD, FLAT[:4], FLAT[:4]) + stratum(MAIN, FLAT[:3], FLAT[:3], start=4)
        self.check(runs, {"rest_changed": 8}, verdict=section_verdict(runs, CURRENT))
        # Pooled (the default since #831), the older rest counts again.
        self.check(runs, {}, verdict=section_verdict(runs, POOLED))

    def test_hooked_run(self):
        hooked = stratum(MAIN, FLAT[:2], FLAT[:2], start=10)
        for run in hooked:
            # As compute_gates keys a hooked run: its pair key carries the set.
            run["fleet_hooks_digest"] = "h" * 64
            run["pair_key"] = run["arm_context_digest"] = f"{MAIN}:{'h' * 64}"
        runs = stratum(MAIN, FLAT[:3], FLAT[:3]) + hooked
        self.check(runs, {"hooked_run": 4}, verdict=section_verdict(runs, POOLED))
        self.check(runs, {"hooked_run": 4}, verdict=section_verdict(runs, CURRENT))

    def test_alone_pair_runs_count_beside_in_situ_ones(self):
        alone = stratum("alone", FLAT[:2], FLAT[:2], start=20, pair="alone")
        runs = stratum(MAIN, FLAT[:3], FLAT[:3]) + alone + stratum(
            "alone", FLAT[:1], FLAT[:1], start=30, pair="alone", model="model-old")
        self.check(runs, {"model_off_roster": 2}, verdict=section_verdict(runs))

    def test_the_first_reason_wins(self):
        # Off the roster AND an old fixture digest: the pooling order names it.
        self.check(pairs(3) + pairs(1, start=10, model="model-old", fdig="f0"),
                   {"model_off_roster": 2})

    def test_every_slug_is_tested(self):
        tested = {name[len("test_"):] for name in dir(self) if name.startswith("test_")}
        tested |= {name[len("test_"):] for name in dir(IndexReasonTests)
                   if name.startswith("test_")}
        tested.add("rest_changed")  # test_rest_changed_only_under_the_current_rest_policy
        self.assertEqual(set(gates.DISCARD_REASONS) - tested, set())


class CostTests(unittest.TestCase):

    def test_cost_is_summed_at_full_precision_and_unknown_runs_are_counted(self):
        lone = [arm_run("with", [trial(80, 100, cost=0.1), trial(80, 100, cost=0.2)], 10),
                arm_run("with", [trial(80, 100, cost=1 / 3), trial(80, 100, cost=None)], 11),
                arm_run("with", [trial(80, 100, cost=None)], 12)]
        verdict = skill_verdict(pairs(3) + lone)
        row = verdict["discarded_runs"]["by_reason"]["unpaired"]
        self.assertEqual(row["runs"], 3)
        # math.fsum of the known trial costs, never rounded.
        self.assertEqual(row["cost_usd"], 0.1 + 0.2 + 1 / 3)
        self.assertEqual(row["cost_unknown"], 2)
        self.assertEqual(verdict["discarded_runs"]["cost_usd"], row["cost_usd"])
        self.assertEqual(verdict["discarded_runs"]["cost_unknown"], 2)

    def test_merge_adds_counts_and_dollars(self):
        a = gates.discard_summary([("unpaired", 0.5, False), ("over_cap", 0.25, True)])
        b = gates.discard_summary([("unpaired", 0.125, False)])
        self.assertEqual(gates.merge_discards(a, None, b), {
            "total": 3, "cost_usd": 0.875, "cost_unknown": 1,
            "by_reason": {"over_cap": {"runs": 1, "cost_usd": 0.25, "cost_unknown": 1},
                          "unpaired": {"runs": 2, "cost_usd": 0.625, "cost_unknown": 0}}})

    def test_an_unknown_reason_is_refused(self):
        with self.assertRaises(ValueError):
            gates.discard_entry({"trials": []}, "stale")


class IndexReasonTests(unittest.TestCase):
    """The reasons scripts/compute_gates.py decides before any cell, through
    the real tree, as compute_gates.main writes them."""

    SKILLS = t70.ComputeGatesTests.SKILLS
    setUp = t70.ComputeGatesTests.setUp
    _fixture = staticmethod(t70.ComputeGatesTests._fixture)
    _skill = t70.ComputeGatesTests._skill
    digest_of = t70.ComputeGatesTests.digest_of
    write = t70.ComputeGatesTests.write
    run_gates = t70.ComputeGatesTests.run_gates
    edit = t70.ComputeGatesTests.edit
    in_place_fixture = t70.ComputeGatesTests.in_place_fixture
    bare = t70.ComputeGatesTests.bare

    def discards(self, doc, skill):
        return reasons(doc["skills"][skill])

    def test_invalid_run(self):
        # setUp writes one older-shape `flat` summary with no aggregate.
        self.write("flat", FLAT[:3], FLAT_JUDGE)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"], {"no aggregate block": 1})
        self.assertEqual(self.discards(doc, "flat"), {"invalid_run": 1})
        # It has no trial cost to read: unknown, never zero.
        self.assertEqual(doc["skills"]["flat"]["discarded_runs"]["cost_unknown"], 1)
        self.assertEqual(counted(doc["skills"]["flat"]), 6)

    def test_after_as_of(self):
        self.write("gain", FLAT[:4], FLAT_JUDGE)
        _, doc = self.run_gates("a.json", as_of=stamp(2))
        self.assertEqual(self.discards(doc, "gain"), {"after_as_of": 2})
        self.assertEqual(counted(doc["skills"]["gain"]), 6)
        # Three trials per arm: 0.25 each on the with arm, 0.5 on the without.
        self.assertEqual(doc["skills"]["gain"]["discarded_runs"]["cost_usd"], 3 * 0.25 + 3 * 0.5)

    def test_duplicate(self):
        (run_id,) = self.write("gain", FLAT[:1], FLAT_JUDGE)
        self.write("gain", FLAT[1:3], FLAT_JUDGE, start=1)
        source = self.tree / "routine-results" / run_id / "gain"
        shutil.copytree(source, self.tree / "results" / "gain")
        _, doc = self.run_gates("a.json")
        self.assertEqual(self.discards(doc, "gain"), {"duplicate": 2})
        self.assertEqual(counted(doc["skills"]["gain"]), 6)

    def test_bare_run(self):
        self.in_place_fixture("ctxbot")
        self.bare("ctxbot", 40)
        _, doc = self.run_gates("a.json")
        self.assertEqual(self.discards(doc, "ctxbot"), {"bare_run": 1})
        self.assertEqual(len(doc["bare_runs"]), 1)

    def test_verdict_raised(self):
        self.write("gain", FLAT[:2], FLAT_JUDGE)
        with mock.patch.object(compute_gates.gates, "retirement", side_effect=MemoryError):
            _, doc = self.run_gates("a.json")
        self.assertEqual(self.discards(doc, "gain"), {"verdict_raised": 4})
        # Its build_index reasons still count beside it.
        self.assertEqual(self.discards(doc, "flat"), {"invalid_run": 1})


class ExplorerTests(unittest.TestCase):

    GATES = {"skills": {"alpha": {"verdict": "keep", "cells": [], "discarded_runs":
                                  gates.discard_summary([("unpaired", 0.5, False),
                                                         ("over_cap", 0.25, True)])}},
             "guidance": {"sec-one": {"verdict": "keep", "cells": [], "discarded_runs":
                                      gates.discard_summary([("unpaired", 0.125, False)])}}}

    def build(self, gates_doc):
        t = Tree(self)
        t.pair("alpha", "20261030T100000Z", [Tree.trial(4, 5, 8.0, 0.25)],
               [Tree.trial(1, 5, 4.0, 0.125)])
        gates_doc = {"policy": {"benefit_confidence": 0.85, "retire_confidence": 0.95,
                                "min_cli_versions": 2, "objective_margin": 0.05},
                     **gates_doc}
        with mock.patch.object(explorer_data.compute_gates, "compute", return_value=gates_doc):
            return t.build(manifest=MANIFEST)

    def test_each_subject_and_the_fleet_carry_discarded_runs(self):
        doc = self.build(self.GATES)
        alpha = next(s for s in doc["skills"] if s["name"] == "alpha")
        one, two = doc["guidance"]["sections"]
        self.assertEqual(alpha["discarded_runs"], self.GATES["skills"]["alpha"]["discarded_runs"])
        self.assertEqual(one["discarded_runs"]["by_reason"],
                         {"unpaired": {"runs": 1, "cost_usd": 0.125, "cost_unknown": 0}})
        # No verdict: unknown, not zero.
        self.assertIsNone(two["discarded_runs"])
        self.assertEqual(doc["discarded_runs"]["skills"]["total"], 2)
        self.assertEqual(doc["discarded_runs"]["guidance"]["total"], 1)
        self.assertEqual(doc["discarded_runs"]["all"], {
            "total": 3, "cost_usd": 0.875, "cost_unknown": 1,
            "by_reason": {"over_cap": {"runs": 1, "cost_usd": 0.25, "cost_unknown": 1},
                          "unpaired": {"runs": 2, "cost_usd": 0.625, "cost_unknown": 0}}})
        # The public gates pass: the schema and `finish`.
        explorer_data.validate(doc)
        explorer_data.finish(doc)

    def test_only_counts_dollars_and_known_slugs_are_published(self):
        summary = gates.discard_summary([("unpaired", 0.5, False)])
        summary["by_reason"]["unpaired"]["paths"] = ["results/x/20261030T100000Z"]
        summary["by_reason"]["a-session-title"] = {"runs": 1, "cost_usd": 1.0,
                                                   "cost_unknown": 0}
        doc = self.build({"skills": {"alpha": {"verdict": "keep", "cells": [],
                                               "discarded_runs": summary}},
                          "guidance": {}})
        alpha = next(s for s in doc["skills"] if s["name"] == "alpha")
        self.assertEqual(alpha["discarded_runs"], gates.discard_summary(
            [("unpaired", 0.5, False)]))
        explorer_data.validate(doc)
        self.assertNotIn("results/x", json.dumps(doc["discarded_runs"]))


if __name__ == "__main__":
    unittest.main()
