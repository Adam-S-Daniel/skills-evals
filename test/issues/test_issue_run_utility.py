#!/usr/bin/env python3
"""Run utility (Adam, 2026-11-07): which arm runs helped decide a subject's
disposition and which bought nothing, over time (harness/gates.py, RUN
UTILITY; scripts/compute_gates.py; the explorer's `run_utility` and
`decisions`).

Each class gets a test, the decision point gets a boundary test (the last
decisive pair against the first after it), a change of content gets both
the superseded path (the old version decided) and the stranded one (it
never did), and the ledger's reasons always equal `discarded_runs`.

Hermetic and deterministic: canned runs and a temporary results tree, no
network, no clock.
"""

from __future__ import annotations

import sys
import unittest
from collections import Counter
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
import test_issue_discarded_runs as tdr  # noqa: E402
from test_issue_70_retirement import (  # noqa: E402
    EXPECT, FLAT, FLAT_DECIDES, FLAT_JUDGE, GAIN, TEST_POLICY, series)
from test_issue_557_stratified_verdict import MAIN, OLD, stratum  # noqa: E402

MODELS = ["model-a"]


def flat(n, start=0, **kw):
    return (series("with", FLAT[:n], FLAT_JUDGE, start=start, **kw)
            + series("without", FLAT[:n], FLAT_JUDGE, start=start, **kw))


def verdict(runs, policy=TEST_POLICY, expect=EXPECT):
    return gates.retirement({"runs": runs}, MODELS, "demo", policy, expect)


def by_class(v, reason=False):
    """{class: runs} (or {(class, reason): runs}) of a verdict's ledger."""
    out = Counter()
    for row in v["run_utility"]:
        out[(row["class"], row["reason"]) if reason else row["class"]] += row["runs"]
    return dict(out)


def check_reasons(test, v):
    """The ledger's reasons are exactly `discarded_runs`, run for run."""
    got = Counter()
    for row in v["run_utility"]:
        test.assertIn(row["class"], gates.UTILITY_CLASSES)
        if row["reason"]:
            got[row["reason"]] += row["runs"]
    test.assertEqual(dict(got), {k: r["runs"] for k, r in v["discarded_runs"]["by_reason"].items()})


class ClassTests(unittest.TestCase):

    def test_decisive_and_after_decision_split_at_the_decision_point(self):
        v = verdict(flat(20))
        cell = v["cells"][0]
        self.assertEqual((cell["class"], cell["decided_at"]), ("no-benefit", FLAT_DECIDES))
        self.assertEqual(by_class(v), {"decisive": 2 * FLAT_DECIDES,
                                       "after_decision": 2 * (20 - FLAT_DECIDES)})
        check_reasons(self, v)

    def test_the_boundary_is_the_decision_pairs_last_decisive_run(self):
        runs = flat(FLAT_DECIDES + 1)
        cell = gates.classify_cell(runs[:FLAT_DECIDES + 1], runs[FLAT_DECIDES + 1:],
                                   TEST_POLICY, family=1)
        rows, day = gates.cell_utility(runs[:FLAT_DECIDES + 1], runs[FLAT_DECIDES + 1:],
                                       TEST_POLICY, cell)
        cls = {r["timestamp"]: c for r, c, _ in rows}
        stamps = sorted(cls)
        # Pair 18 (the decision point) is decisive, pair 19 is not.
        self.assertEqual(cls[stamps[FLAT_DECIDES - 1]], "decisive")
        self.assertEqual(cls[stamps[FLAT_DECIDES]], "after_decision")
        self.assertEqual(day, gates.run_day(stamps[FLAT_DECIDES - 1]))

    def test_a_keep_decides_at_its_crossing(self):
        runs = (series("with", GAIN * 4, FLAT_JUDGE * 2)
                + series("without", FLAT[:20] * 2, FLAT_JUDGE * 2))
        v = verdict(runs)
        cell = v["cells"][0]
        self.assertEqual(cell["class"], "benefit")
        at = cell["decided_at"]
        self.assertEqual(at, cell["objective"]["keep_at"])
        self.assertEqual(by_class(v), {"decisive": 2 * at, "after_decision": 2 * (40 - at)})

    def test_building(self):
        v = verdict(flat(5))
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIsNone(v["cells"][0]["decided_at"])
        self.assertEqual(by_class(v), {"building": 10})
        self.assertEqual(v["decisions"], [{"fixture": None, "model": "model-a", "current": True,
                                           "from": "2026-10-01", "to": "2026-10-01",
                                           "class": "insufficient", "decided": None}])

    def test_discarded_carries_its_reason(self):
        lone = series("with", FLAT[:2], FLAT_JUDGE, start=10)
        v = verdict(flat(3) + lone)
        self.assertEqual(by_class(v, reason=True), {("building", None): 6,
                                                    ("discarded", "unpaired"): 2})
        check_reasons(self, v)

    def test_an_errored_cell_turned_insufficient_has_no_decision_point(self):
        runs = flat(20)
        runs[0]["trials"][0]["errored"] = True
        v = verdict(runs)
        self.assertEqual(v["cells"][0]["class"], "insufficient")
        self.assertIsNone(v["cells"][0]["decided_at"])
        self.assertNotIn("decisive", by_class(v))

    def test_an_unknown_class_or_reason_is_refused(self):
        with self.assertRaises(ValueError):
            gates.utility_entry({"trials": []}, "useful")
        with self.assertRaises(ValueError):
            gates.utility_entry({"trials": []}, "discarded", "stale")


class SupersededTests(unittest.TestCase):
    """CELL VERSIONS: runs a later change dropped, by their old version."""

    def test_an_old_version_that_decided_is_superseded_then_after_decision(self):
        old = flat(20, tested="t0")  # the skill's text before an edit
        v = verdict(old + flat(3, start=48))
        # The old with arms are `subject_changed`; their without partners
        # are left unpaired in today's cell, and join their old version.
        self.assertEqual(by_class(v, reason=True), {
            ("building", None): 6,
            ("decisive_superseded", "subject_changed"): FLAT_DECIDES,
            ("decisive_superseded", "unpaired"): FLAT_DECIDES,
            ("after_decision", "subject_changed"): 20 - FLAT_DECIDES,
            ("after_decision", "unpaired"): 20 - FLAT_DECIDES})
        check_reasons(self, v)
        self.assertEqual([(d["current"], d["class"], d["decided"], d["from"], d["to"])
                          for d in v["decisions"]],
                         [(False, "no-benefit", "2026-10-01", "2026-10-01", "2026-10-01"),
                          (True, "insufficient", None, "2026-10-03", "2026-10-03")])

    def test_an_old_version_that_never_decided_is_stranded(self):
        v = verdict(flat(4, fdig="f0") + flat(3, start=48))
        self.assertEqual(by_class(v, reason=True), {("building", None): 6,
                                                    ("stranded", "fixture_changed"): 8})
        check_reasons(self, v)
        self.assertEqual([(d["current"], d["class"]) for d in v["decisions"]],
                         [(False, "insufficient"), (True, "insufficient")])

    def test_each_stranding_reason_regroups(self):
        for name, runs in {
            "fixture_off_main": flat(3, fixture="gone"),
            "model_off_roster": flat(3, model="model-old"),
            "context_unmatched": flat(2, start=10, pair="q"),
        }.items():
            with self.subTest(name):
                v = verdict(flat(3) + runs)
                self.assertEqual(by_class(v, reason=True).get(("stranded", name)), len(runs))
                check_reasons(self, v)

    def test_rest_changed_regroups_by_rest(self):
        runs = stratum(OLD, FLAT[:4], FLAT[:4]) + stratum(MAIN, FLAT[:3], FLAT[:3], start=4)
        v = tdr.section_verdict(runs, tdr.CURRENT)
        self.assertEqual(by_class(v, reason=True).get(("stranded", "rest_changed")), 8)
        check_reasons(self, v)
        self.assertEqual({d["pair"] for d in v["decisions"]}, {"in_situ"})

    def test_a_reason_that_is_not_a_change_is_never_regrouped(self):
        lone = series("with", FLAT[:2], FLAT_JUDGE, start=10)
        for run in lone:
            run["arm_context_digest"] = None
        v = verdict(flat(3) + lone)
        self.assertEqual(by_class(v, reason=True).get(("discarded", "context_unknown")), 2)
        self.assertNotIn("stranded", by_class(v))


class ComputeTests(unittest.TestCase):
    """Through scripts/compute_gates.py, as main writes it."""

    setUp = tdr.IndexReasonTests.setUp
    SKILLS = tdr.IndexReasonTests.SKILLS
    _fixture = staticmethod(tdr.IndexReasonTests._fixture)
    _skill = tdr.IndexReasonTests._skill
    digest_of = tdr.IndexReasonTests.digest_of
    write = tdr.IndexReasonTests.write
    run_gates = tdr.IndexReasonTests.run_gates

    def test_index_drops_are_dated_discards_and_add_up(self):
        self.write("gain", FLAT[:3], FLAT_JUDGE)
        _, doc = self.run_gates("a.json")
        for skill, v in doc["skills"].items():
            check_reasons(self, v)
        flat_rows = doc["skills"]["flat"]["run_utility"]
        invalid = [r for r in flat_rows if r["reason"] == "invalid_run"]
        self.assertEqual(len(invalid), 1)
        # Its day is its directory's; its model is unknown, never guessed.
        self.assertIsNotNone(invalid[0]["date"])
        self.assertIsNone(invalid[0]["model"])

    def test_a_raised_verdict_discards_every_run(self):
        self.write("gain", FLAT[:2], FLAT_JUDGE)
        with mock.patch.object(compute_gates.gates, "retirement", side_effect=MemoryError):
            _, doc = self.run_gates("a.json")
        v = doc["skills"]["gain"]
        self.assertEqual(by_class(v, reason=True), {("discarded", "verdict_raised"): 4})
        self.assertEqual(v["decisions"], [])


class ExplorerTests(unittest.TestCase):

    ROW = {"date": "2026-11-02", "model": "model-a", "class": "decisive", "reason": None,
           "runs": 2, "cost_usd": 0.5, "cost_unknown": 0}

    def test_rows_and_decisions_are_published_and_validate(self):
        stranded = {**self.ROW, "class": "stranded", "reason": "fixture_changed", "runs": 1,
                    "cost_usd": 0.125}
        decision = {"fixture": "task-a", "model": "model-a", "current": True, "from": "2026-11-01",
                    "to": "2026-11-02", "class": "benefit", "decided": "2026-11-02"}
        doc = tdr.ExplorerTests.build(self, {
            "skills": {"alpha": {"verdict": "keep", "cells": [],
                                 "discarded_runs": gates.discard_summary(
                                     [("fixture_changed", 0.125, False)]),
                                 "run_utility": [self.ROW, stranded],
                                 "decisions": [decision]}},
            "guidance": {"sec-one": {"verdict": "keep", "cells": [],
                                     "discarded_runs": gates.discard_summary([]),
                                     "run_utility": [], "decisions": [
                                         {**decision, "pair": "alone"}]}}})
        alpha = next(s for s in doc["skills"] if s["name"] == "alpha")
        self.assertEqual(alpha["run_utility"], [self.ROW, stranded])
        self.assertEqual(alpha["decisions"], [{**decision, "pair": None}])
        one, two = doc["guidance"]["sections"]
        self.assertEqual(one["decisions"][0]["pair"], "alone")
        # No verdict: unknown, not empty.
        self.assertIsNone(two["run_utility"])
        self.assertIsNone(two["decisions"])
        explorer_data.validate(doc)
        explorer_data.finish(doc)

    def test_unknown_classes_slugs_and_identifiers_are_dropped(self):
        rows = [self.ROW, {**self.ROW, "class": "useful"},
                {**self.ROW, "class": "discarded", "reason": "a-session-title"},
                {**self.ROW, "model": "/root/x", "path": "results/x"}]
        got = explorer_data.run_utility({"run_utility": rows})
        # A model that is not an id is published as unknown, never as given.
        self.assertEqual([(r["model"], r["class"]) for r in got],
                         [(None, "decisive"), ("model-a", "decisive")])
        self.assertNotIn("path", got[0])

    def test_the_schema_holds_the_classes_and_slugs(self):
        import json
        schema = json.loads(explorer_data.SCHEMA_PATH.read_text(encoding="utf-8"))
        row = schema["$defs"]["utility_row"]["properties"]
        self.assertEqual(row["class"]["enum"], list(gates.UTILITY_CLASSES))
        self.assertEqual(row["reason"]["anyOf"][0]["enum"], list(gates.DISCARD_REASONS))
        doc = tdr.ExplorerTests.build(self, tdr.ExplorerTests.GATES)
        alpha = next(s for s in doc["skills"] if s["name"] == "alpha")
        for bad in ({**self.ROW, "class": "useful"}, {**self.ROW, "runs": 0},
                    {**self.ROW, "date": "Nov 2"}, {**self.ROW, "extra": 1}):
            alpha["run_utility"] = [bad]
            with self.subTest(bad=bad), self.assertRaises(explorer_data.Refused):
                explorer_data.validate(doc)


if __name__ == "__main__":
    unittest.main()
