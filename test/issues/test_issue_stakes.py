#!/usr/bin/env python3
"""Stakes levels (evals/stakes.yml, scripts/stakes.py; Adam, 2026-11-01):
the committed file loads, malformed rows are refused, and the planner tests
high-stakes subjects first, re-checks them sooner and plans nothing for a
`none` subject.

Hermetic: temporary directories, `now` passed in, no network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import plan_week  # noqa: E402
import stakes  # noqa: E402

NOW = datetime(2026, 11, 1, 7, 0, 0, tzinfo=timezone.utc)


def cell(fixture, cls, runs=0, newest=None, level="normal", skill=None):
    return {"skill": skill or fixture.split("/")[1], "fixture": fixture, "model": "m",
            "class": cls, "with_runs": runs, "without_runs": runs, "newest": newest,
            "usd_per_fire": None, "empty_fires": 0, "stakes": level}


def ctx(cells):
    return {"cells": cells, "model_weights": {"m": 1.0}, "removal_prs": [],
            "reservation": 0.035, "overrun": 0.005, "points_per_usd": None}


class CommittedFileTests(unittest.TestCase):

    def test_the_committed_file_loads(self):
        self.assertEqual(stakes.main(["--check"]), 0)
        table = stakes.load(stakes.DEFAULT_PATH, ROOT / "evals")
        self.assertTrue(table)
        for (kind, _name), entry in table.items():
            self.assertIn(kind, ("skill", "guidance"))
            self.assertTrue(entry["reason"])


class LoadTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.evals = Path(self.tmp.name) / "evals"
        (self.evals / "alpha").mkdir(parents=True)
        (self.evals / "guidance" / "beta").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, text):
        path = self.evals / "stakes.yml"
        path.write_text(textwrap.dedent(text), encoding="utf-8")
        return stakes.load(path, self.evals)

    def test_rows_load_and_unlisted_subjects_are_normal(self):
        table = self.load("""\
            skills:
              - {skill: alpha, stakes: high, reason: it guards secrets}
            sections:
              - {section: beta, stakes: none, reason: a hook refuses it,
                 covered_by: "Adam-S-Daniel/example:hooks/check.sh"}
            """)
        self.assertEqual(stakes.level_of(table, "skill", "alpha"), "high")
        self.assertEqual(stakes.level_of(table, "guidance", "beta"), "none")
        self.assertEqual(stakes.level_of(table, "skill", "other"), "normal")
        self.assertEqual(stakes.load(self.evals / "absent.yml", self.evals), {})

    def test_malformed_rows_are_refused(self):
        bad = {
            "unknown field": "skills:\n  - {skill: alpha, stakes: high, reason: r, extra: 1}\n",
            "no fixture dir": "skills:\n  - {skill: private-thing, stakes: high, reason: r}\n",
            "section dir checked": "sections:\n  - {section: alpha, stakes: high, reason: r}\n",
            "bad level": "skills:\n  - {skill: alpha, stakes: low, reason: r}\n",
            "no reason": "skills:\n  - {skill: alpha, stakes: high}\n",
            "none without check": "skills:\n  - {skill: alpha, stakes: none, reason: r}\n",
            "check outside the fleet": "skills:\n  - {skill: alpha, stakes: none, reason: r, "
                                       "covered_by: 'someone/else:x.sh'}\n",
            "check without a path": "skills:\n  - {skill: alpha, stakes: none, reason: r, "
                                    "covered_by: 'jodidaniel/repo'}\n",
            "check on a high row": "skills:\n  - {skill: alpha, stakes: high, reason: r, "
                                   "covered_by: 'jodidaniel/repo:x.sh'}\n",
            "duplicate": "skills:\n  - {skill: alpha, stakes: high, reason: r}\n"
                         "  - {skill: alpha, stakes: normal, reason: r}\n",
            "unknown top level": "people: []\n",
        }
        for label, text in bad.items():
            with self.subTest(label):
                with self.assertRaises(stakes.StakesError):
                    self.load(text)

    def test_check_exits_1_on_a_bad_file(self):
        path = self.evals / "stakes.yml"
        path.write_text("skills:\n  - {skill: alpha, stakes: low, reason: r}\n", encoding="utf-8")
        self.assertEqual(stakes.main(["--check", "--path", str(path)]), 1)


class PlannerTests(unittest.TestCase):

    def test_high_stakes_go_first_within_a_band(self):
        cells = [cell("evals/a/x", "insufficient", runs=1),
                 cell("evals/b/x", "insufficient", runs=5, level="high"),
                 cell("evals/c/x", "missing"),
                 cell("evals/d/x", "missing", level="high")]
        bands, _ = plan_week.eval_items(ctx(cells), NOW)
        plan_week.allocate(bands, 0.0, 0)  # sorts each band in place
        self.assertEqual([i["skill"] for i in bands["near"]], ["b", "a"])
        self.assertEqual([i["skill"] for i in bands["missing"]], ["d", "c"])

    def test_high_stakes_are_rechecked_after_four_weeks(self):
        five_weeks = "20260927T070000Z"
        cells = [cell("evals/a/x", "benefit", runs=6, newest=five_weeks),
                 cell("evals/b/x", "benefit", runs=6, newest=five_weeks, level="high")]
        bands, _ = plan_week.eval_items(ctx(cells), NOW)
        self.assertEqual([i["skill"] for i in bands["recheck"]], ["b"])
        self.assertEqual(plan_week.recheck_after({"stakes": "high"}).days, 28)
        self.assertEqual(plan_week.recheck_after({}).days, 56)

    def test_a_none_subject_plans_no_eval_fire(self):
        cells = [cell("evals/a/x", "missing", level="none"),
                 cell("evals/a/y", "insufficient", runs=2, level="none"),
                 cell("evals/a/z", "benefit", runs=6, newest="20260101T000000Z", level="none")]
        bands, work = plan_week.eval_items(ctx(cells), NOW)
        self.assertFalse(any(bands.values()))
        self.assertEqual(work, [])

    def test_eval_cells_carry_each_subjects_stakes(self):
        # The committed tree: a scheduled fixture of a high-stakes skill in
        # evals/stakes.yml carries `high`, and every cell carries a level.
        doc = {"roster_models": ["m"], "skills": {}, "guidance": {}}
        cells = plan_week.eval_cells(ROOT / "evals", doc, [], NOW)
        table = stakes.load(stakes.DEFAULT_PATH, ROOT / "evals")
        self.assertTrue(cells)
        for c in cells:
            kind, name = ("guidance", c["section"]) if c["section"] else ("skill", c["skill"])
            self.assertEqual(c["stakes"], stakes.level_of(table, kind, name))


if __name__ == "__main__":
    unittest.main()
