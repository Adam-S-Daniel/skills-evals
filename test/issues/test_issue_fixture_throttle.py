#!/usr/bin/env python3
"""skills-evals#1046: fixture requests for subjects with no verdict yet are
throttled (plan_week.throttle_fixture_work).

Hermetic and deterministic: canned contexts, no network, no clock.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import plan_week  # noqa: E402

POLICY = {"pairs_per_cell": 10.0}
COSTS = {"m1": 0.02, "m2": 0.01}
# One request: 10 pairs x (0.02 + 0.01) = 0.30.
PRICE = 0.30


def item(kind, skill="", section="", fixtures=1):
    return {"kind": kind, "change_type": "fixture", "skill": skill, "section": section,
            "fixtures": fixtures, "headroom": 0.5, "route": "issue"}


def cell(klass, skill="", section=None):
    return {"skill": skill, "section": section, "class": klass}


def ctx(verdicts=None, cells=(), allowance=None, costs=COSTS, guidance=None):
    return {"skills": {}, "gate_verdicts": verdicts or {}, "guidance": guidance or {},
            "cells": list(cells), "roster_models": ["m1", "m2"],
            "batch_policy": POLICY, "batch_pair_costs": costs, "fixture_allowance": allowance}


def reasons(withheld):
    return [(w["kind"], w["skill"] or w["section"]) for w in withheld]


class KeptSubjectTests(unittest.TestCase):

    def test_a_keep_subject_is_never_throttled(self):
        work = [item("needs-fixtures", "a"), item("needs-harder-fixtures", "a")]
        kept, withheld = plan_week.throttle_fixture_work(
            ctx({"a": "keep"}, allowance=0.0), work)
        self.assertEqual((kept, withheld), (work, []))

    def test_other_work_items_pass_through(self):
        work = [{"kind": "needs-trigger-set", "skill": "a"}]
        self.assertEqual(plan_week.throttle_fixture_work(ctx(allowance=0.0), work), (work, []))


class UndecidedSubjectTests(unittest.TestCase):

    def test_needs_fixtures_waits_for_a_keep(self):
        kept, withheld = plan_week.throttle_fixture_work(
            ctx({"a": "insufficient"}, allowance=9.0), [item("needs-fixtures", "a")])
        self.assertEqual(kept, [])
        self.assertEqual(reasons(withheld), [("needs-fixtures", "a")])

    def test_a_subject_with_no_fixture_goes_to_the_allowance(self):
        work = [item("needs-fixtures", section="s", fixtures=0)]
        kept, withheld = plan_week.throttle_fixture_work(ctx(allowance=PRICE), work)
        self.assertEqual((kept, withheld), (work, []))

    def test_harder_fixtures_need_every_counted_cell_at_the_ceiling(self):
        work = [item("needs-harder-fixtures", "a")]
        for cells, filed in (
                ([cell("ceiling", "a"), cell("ceiling-unconfirmed", "a")], True),
                ([cell("ceiling", "a"), cell("cannot-discriminate", "a")], True),
                ([cell("ceiling", "a"), cell("insufficient", "a")], False),
                ([cell("ceiling", "b")], False),
                ([], False)):
            with self.subTest(cells=cells):
                kept, _ = plan_week.throttle_fixture_work(
                    ctx({"a": "insufficient"}, cells, allowance=9.0), work)
                self.assertEqual(kept == work, filed)

    def test_a_cell_scope_paused_at_the_ceiling_counts_as_parked(self):
        paused = {"class": "paused", "scope_paused": "ceiling"}
        work = [item("needs-harder-fixtures", section="s", fixtures=3)]
        for cells, filed in (
                ([dict(paused, section="s")], True),
                ([dict(paused, section="s"), cell("ceiling", section="s")], True),
                ([dict(paused, section="s", scope_paused="floor")], False),
                ([cell("paused", section="s")], False)):
            with self.subTest(cells=cells):
                context = ctx(cells=cells, allowance=9.0,
                              guidance={"s": {"verdict": "insufficient"}})
                kept, _ = plan_week.throttle_fixture_work(context, work)
                self.assertEqual(kept == work, filed)

    def test_a_guidance_section_is_judged_on_its_own_cells(self):
        work = [item("needs-harder-fixtures", section="s", fixtures=3)]
        context = ctx(cells=[cell("ceiling", section="s")], allowance=9.0,
                      guidance={"s": {"verdict": "insufficient"}})
        self.assertEqual(plan_week.throttle_fixture_work(context, work), (work, []))
        context["cells"].append(cell("missing", section="s"))
        self.assertEqual(plan_week.throttle_fixture_work(context, work)[0], [])


class AllowanceTests(unittest.TestCase):

    def parked(self, *names):
        return [cell("ceiling", n) for n in names]

    def test_requests_are_filed_while_their_priced_total_fits(self):
        work = [item("needs-harder-fixtures", n) for n in "abc"]
        context = ctx({n: "insufficient" for n in "abc"}, self.parked(*"abc"),
                      allowance=2 * PRICE + 0.01)
        kept, withheld = plan_week.throttle_fixture_work(context, work)
        self.assertEqual([i["skill"] for i in kept], ["a", "b"])
        self.assertEqual(reasons(withheld), [("needs-harder-fixtures", "c")])
        self.assertIn("allowance", withheld[0]["reason"])

    def test_an_exact_fit_is_filed(self):
        work = [item("needs-harder-fixtures", "a")]
        kept, _ = plan_week.throttle_fixture_work(
            ctx({"a": "insufficient"}, self.parked("a"), allowance=PRICE), work)
        self.assertEqual(kept, work)

    def test_a_price_follows_pairs_per_cell_and_roster(self):
        self.assertAlmostEqual(plan_week.fixture_request_price(ctx()), PRICE)
        # A roster model with no measured cost is priced at the dearest.
        context = {**ctx(), "roster_models": ["m1", "m2", "m3"]}
        self.assertAlmostEqual(plan_week.fixture_request_price(context), PRICE + 0.02 * 10)

    def test_no_measured_cost_files_nothing_under_an_allowance(self):
        work = [item("needs-harder-fixtures", "a")]
        context = ctx({"a": "insufficient"}, self.parked("a"), allowance=9.0, costs={})
        kept, withheld = plan_week.throttle_fixture_work(context, work)
        self.assertEqual(kept, [])
        self.assertIn("no pair cost", withheld[0]["reason"])

    def test_no_allowance_applies_only_the_first_two_rules(self):
        work = [item("needs-harder-fixtures", n) for n in "ab"]
        context = ctx({n: "insufficient" for n in "ab"}, self.parked("a"),
                      allowance=None, costs={})
        kept, withheld = plan_week.throttle_fixture_work(context, work)
        self.assertEqual([i["skill"] for i in kept], ["a"])
        self.assertEqual(reasons(withheld), [("needs-harder-fixtures", "b")])

    def test_a_keep_subject_does_not_spend_the_allowance(self):
        work = [item("needs-fixtures", "k"), item("needs-harder-fixtures", "a")]
        context = ctx({"k": "keep", "a": "insufficient"}, self.parked("a"), allowance=PRICE)
        kept, _ = plan_week.throttle_fixture_work(context, work)
        self.assertEqual(kept, work)


class PlanTests(unittest.TestCase):

    def test_the_plan_lists_what_it_withheld(self):
        from datetime import datetime, timezone
        now = datetime(2026, 11, 20, tzinfo=timezone.utc)
        skills = {"zz-demo": {"fixtures": 2, "holdout": "", "registry_ok": True,
                              "verdict": "insufficient",
                              "evidence": {"headroom": 0.5, "targets": []}, "pause": None}}
        context = {"skills": skills, "skill_weights": {"zz-demo": 0}, "removal_prs": set(),
                   "private_skills": [], "improve_charge": 0.05}
        _, needs, *_ = plan_week.improve_items(context, now)
        self.assertEqual([n["kind"] for n in needs], ["needs-fixtures"])
        kept, withheld = plan_week.throttle_fixture_work(
            {**context, "gate_verdicts": {"zz-demo": "insufficient"}}, needs)
        self.assertEqual((kept, reasons(withheld)), ([], [("needs-fixtures", "zz-demo")]))


class PolicyTests(unittest.TestCase):

    def test_the_committed_share_is_a_fraction(self):
        policy = plan_week.load_batch_policy(ROOT / "evals/batch-policy.yml")
        self.assertTrue(0 <= policy["undecided_fixture_share"] <= 1)

    def test_a_malformed_share_stops_the_plan(self):
        good = yaml.safe_load((ROOT / "evals/batch-policy.yml").read_text())
        bad = [{k: v for k, v in good.items() if k != "undecided_fixture_share"},
               {**good, "undecided_fixture_share": -0.1}, {**good, "undecided_fixture_share": 1.5},
               {**good, "undecided_fixture_share": "half"},
               {**good, "undecided_fixture_share": True}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "batch-policy.yml"
            for doc in bad:
                path.write_text(yaml.safe_dump(doc))
                with self.subTest(doc=doc), self.assertRaises(plan_week.PlanError):
                    plan_week.load_batch_policy(path)


if __name__ == "__main__":
    unittest.main()
