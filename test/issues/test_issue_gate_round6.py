#!/usr/bin/env python3
"""PR 649's sixth adversarial round on the betting gate (2026-11-03).

Each class pins one finding of
/mnt/project-files/reports/pr649-adversarial-round6.md:

  * M1: a subject whose verdict is `ceiling` because its cells are
    scope-paused has no planner cell, so it is a `paused-ceiling` work item
    asking for a harder fixture (skills and guidance alike);
  * M2: the scope pass's text no longer says a pause drops a skill
    fixture's cells from the gate (they stay, parked);
  * m1: a paused cell whose no-harm test rejected shows the ceiling at
    exactly the policy's `high_stop_min_without`;
  * m2: a paused `no-clear-effect` cell stays parked.

Hermetic and deterministic: canned runs, temporary directories, no network,
no clock.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import eval_scope  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402
import run_eval  # noqa: E402
from test_issue_70_retirement import POLICY  # noqa: E402
from test_issue_gate_round3 import CAP, MODELS, expect, pairs  # noqa: E402

REAL_MODELS = ["claude-sonnet-5-5", "claude-opus-5-5"]
NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def verdict(runs, expected):
    return gates.retirement({"runs": runs}, MODELS, "demo", POLICY, expected)


def both(n, without, with_):
    return pairs("a", n, without, with_) + pairs("a", n, without, with_, start=1000,
                                                  model=MODELS[1])


class PausedCeilingItemTests(unittest.TestCase):
    """M1, end to end: `compute_gates.compute` over a real `evals/` copy
    holding a new skill of four fixtures, all scope-paused at the ceiling,
    whose cells show the ceiling on their own runs (25 pairs a model at
    97/97). The verdict is `ceiling`; the paused fixtures are off
    evals/scheduled.yml, so the planner has no cell and no `fixture-ceiling`
    item, and the skill is no `skill_contexts` entry for an
    improve item either. Only the work item can ask for the harder fixture."""

    FIXTURES = ("a", "b", "c", "d")

    def build(self, paused):
        root = Path(tempfile.mkdtemp(prefix="round6-"))
        self.addCleanup(shutil.rmtree, root)
        shutil.copytree(ROOT / "evals", root / "evals")
        for f in self.FIXTURES:
            d = root / "evals" / "zz-demo" / f
            d.mkdir(parents=True)
            (d / "fixture.yaml").write_text(
                f"skill: zz-demo\nregistry: {plan_week.REGISTRY_URL}\nprompt: {f}\n"
                "context:\n  repo: Adam-S-Daniel/example\n  ref: abc\n"
                "  guidance_revision: abc\n")
        rows = "".join(f"  - path: evals/zz-demo/{f}\n    rule: \"ceiling\"\n" for f in paused)
        sa = root / "evals" / "scope-auto.yml"
        sa.write_text(sa.read_text() + rows)
        un = root / "evals" / "unscheduled.yml"
        un.write_text(un.read_text() + "".join(
            f"  - path: evals/zz-demo/{f}\n    reason: \"Auto scope (ceiling), "
            "2026-11-03: x\"\n" for f in paused))
        sch = root / "evals" / "scheduled.yml"
        sch.write_text(sch.read_text() + "".join(
            f"  - path: evals/zz-demo/{f}\n    readiness: \"x\"\n"
            for f in self.FIXTURES if f not in paused))
        for args in (["init", "-q"], ["add", "-A"]):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        digests = {f: run_eval.fixture_digest(root / "evals" / "zz-demo" / f)
                   for f in self.FIXTURES}
        runs = []
        for i, m in enumerate(REAL_MODELS):
            for j, f in enumerate(self.FIXTURES):
                runs += pairs(f, 25, 97, 97, start=1000 * i + 100 * j, model=m, skill="zz-demo")
        runs = [{**r, "fixture_digest": digests[r["fixture"]]} for r in runs]
        return root, {"runs": runs, "skills": ["zz-demo"], "skipped": {}, "bare_runs": [],
                      "guidance_runs": [], "sections": []}

    def plan(self, paused):
        root, index = self.build(paused)
        ev = root / "evals"
        with mock.patch.object(compute_gates, "build_index", return_value=index), \
                mock.patch.object(compute_gates, "tested_digest", return_value="t1"):
            doc = compute_gates.compute(root / "results", ev / "roster.yml",
                                        ev / "gate-policy.yml", ev, "20261104T000000Z")
        cells, _, _ = plan_week.eval_cells_and_outages(ev, doc, [], NOW)
        mine = [c for c in cells if c["skill"] == "zz-demo"]
        private = plan_week.private_skills(ev)
        items = plan_week.unmeasured_items(doc, private) \
            + plan_week.paused_ceiling_items(doc, private)
        ctx = {"cells": mine, "removal_prs": [], "model_weights": {}, "guidance_policy": None,
               "reservation": 1.0, "overrun": 1.0, "points_per_usd": None, "batch": None,
               "unmeasured": items}
        _, work = plan_week.eval_items(ctx, NOW)
        return doc["skills"]["zz-demo"], mine, [w for w in work if w.get("skill") == "zz-demo"]

    def test_an_all_paused_ceiling_skill_asks_for_a_harder_fixture(self):
        v, cells, work = self.plan(paused=self.FIXTURES)
        self.assertEqual(v["verdict"], "ceiling", v["reason"])
        self.assertEqual({c["class"] for c in v["cells"]}, {"paused"})
        self.assertEqual(cells, [], "paused fixtures are off the schedule")
        self.assertIs(v["paused_ceiling"], True)
        self.assertNotIn("unmeasured", v)
        self.assertEqual([(w["kind"], w["change_type"], w["route"], w["fixtures"])
                          for w in work],
                         [("paused-ceiling", "fixture", plan_week.SUMMARY_ROUTE,
                           list(self.FIXTURES))])

    def test_an_unpaused_ceiling_skill_is_not_a_paused_ceiling(self):
        v, cells, work = self.plan(paused=())
        self.assertEqual(v["verdict"], "ceiling", v["reason"])
        self.assertNotIn("paused_ceiling", v)
        self.assertTrue(cells)
        self.assertEqual({w["kind"] for w in work}, {"fixture-ceiling"})

    def test_one_paused_cell_beside_ceiling_cells_still_asks(self):
        v, _, work = self.plan(paused=("a",))
        self.assertEqual(v["verdict"], "ceiling", v["reason"])
        self.assertIs(v["paused_ceiling"], True)
        self.assertEqual({w["kind"] for w in work}, {"fixture-ceiling", "paused-ceiling"})

    def test_a_guidance_section_carries_the_flag_into_the_planner(self):
        """`guidance_verdict` copies the flag, as it does `unmeasured`: runs
        in the harness's own shape, every fixture scope-paused after its
        cells showed the ceiling."""
        runs = []
        for i, m in enumerate(MODELS):
            runs += pairs("fx", 25, 97, 97, start=1000 * i, model=m, skill="sec",
                          in_situ=True)
        expected = {"fx": {"fixture_digest": "f1", "tested_digest": "t1",
                           "rest_digest": "rest", "scope_paused": "ceiling"}}
        v = gates.guidance_verdict({"runs": runs}, MODELS, "sec", POLICY, expected)
        self.assertEqual(v["in_situ_verdict"], "ceiling", v["reason"])
        self.assertIs(v["paused_ceiling"], True)
        items = plan_week.paused_ceiling_items({"skills": {}, "guidance": {"sec": v}})
        self.assertEqual(items, [{"kind": "paused-ceiling", "change_type": "fixture",
                                  "skill": "", "route": plan_week.SUMMARY_ROUTE,
                                  "fixtures": ["fx"], "section": "sec"}])

    def test_private_skills_get_none(self):
        v = {"verdict": "ceiling", "paused_ceiling": True,
             "cells": [{"class": "paused", "fixture": "a"}]}
        doc = {"skills": {"pub": v, "secret": v}, "guidance": {}}
        self.assertEqual([i["skill"] for i in
                          plan_week.paused_ceiling_items(doc, frozenset({"secret"}))],
                         ["pub"])

    def test_the_new_kind_is_summary_routed_and_files_no_issue(self):
        import work_item_issues
        self.assertNotIn("paused-ceiling", work_item_issues.KINDS)


class ScopeTextTests(unittest.TestCase):
    """M2: no text says the gate drops a paused skill fixture's cells."""

    def test_no_text_says_a_pause_drops_cells_from_the_gate(self):
        for path in (ROOT / "docs" / "how-it-works.md", ROOT / "scripts" / "eval_scope.py"):
            text = " ".join(path.read_text().split())
            for old in ("pause drops its cells from the gate",
                        "pause drops the fixture's cells from the gate",
                        "a pause could drop the cells that carry it"):
                self.assertNotIn(old, text, path.name)
        resume = " ".join(Path(eval_scope.__file__).read_text().split())
        self.assertIn("parked", resume)


class BoundaryTests(unittest.TestCase):
    def test_exactly_the_high_stop_mean_shows_the_ceiling(self):
        """m1: `without >= high_stop_min_without`, not `>`."""
        base = {"class": "paused", "scope_paused": "ceiling",
                "class_before_pause": "insufficient", "noharm_at": 18}
        policy = gates.load_gate_policy()["skills"]
        at = policy["high_stop_min_without"]
        self.assertTrue(gates._shows_ceiling({**base, "without_mean": at}, policy))
        self.assertFalse(gates._shows_ceiling({**base, "without_mean": at - 1e-9}, policy))

    def test_a_paused_no_clear_effect_cell_stays_parked(self):
        """m2: only `benefit` and `no-benefit` keep their class through a
        pause; a capped `no-clear-effect` cell is `paused`."""
        self.assertEqual(gates.PAUSE_KEEPS_CLASS, frozenset({"benefit", "no-benefit"}))
        runs = pairs("a", CAP, 88, 84) + pairs("a", CAP, 88, 84, start=1000, model=MODELS[1])
        free = verdict(runs, expect("a"))
        self.assertEqual({c["class"] for c in free["cells"]}, {"no-clear-effect"})
        held = verdict(runs, expect("a", paused="a"))
        self.assertEqual([(c["class"], c["class_before_pause"]) for c in held["cells"]],
                         [("paused", "no-clear-effect")] * 2)
        self.assertNotEqual(held.get("removal"), "auto")


if __name__ == "__main__":
    unittest.main()
