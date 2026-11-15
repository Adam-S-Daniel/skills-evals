#!/usr/bin/env python3
"""THE CAP EXTENSION (harness/gates.py; Adam, 2026-11-15).

A cell whose first `max_runs_per_cell` pairs decided nothing, but whose
nearer test is projected from them to cross within `max_runs_extension`
times the cap, gets that larger cap; the planner plans toward it.

Hermetic and deterministic: canned pairs, no network, no clock.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import gates  # noqa: E402
from test_issue_70_retirement import TEST_POLICY  # noqa: E402

POLICY = gates.load_gate_policy()["skills"]
CAP = POLICY["max_runs_per_cell"]


def pairs(ds, key=None):
    return [({"numbers": {"run_mean": max(d, 0.0)}, "pair_key": key},
             {"numbers": {"run_mean": max(-d, 0.0)}}) for d in ds]


def repeat(base):
    return (base * CAP)[:CAP]


class CellCapTests(unittest.TestCase):

    def test_an_undecided_cell_near_a_verdict_gets_the_longer_cap(self):
        longer = int(CAP * POLICY["max_runs_extension"])
        self.assertGreater(longer, CAP)
        for base in ([0.5, -0.2, 0.3, 0.0], [0.0, -0.1, 0.2, 0.0]):
            with self.subTest(base=base):
                self.assertEqual(gates.cell_cap(pairs(repeat(base)), POLICY), longer)

    def test_a_cell_far_from_either_test_keeps_the_cap(self):
        self.assertEqual(gates.cell_cap(pairs(repeat([0.8, -0.6, 0.5, -0.4])), POLICY), CAP)

    def test_a_cell_whose_test_crossed_keeps_the_cap(self):
        self.assertEqual(gates.cell_cap(pairs(repeat([0.6, 0.4, 0.5, 0.3])), POLICY), CAP)

    def test_only_a_full_window_is_judged(self):
        near = repeat([0.5, -0.2, 0.3, 0.0])
        self.assertEqual(gates.cell_cap(pairs(near[:CAP - 1]), POLICY), CAP)

    def test_off_at_one(self):
        near = pairs(repeat([0.5, -0.2, 0.3, 0.0]))
        self.assertEqual(gates.cell_cap(near, {**POLICY, "max_runs_extension": 1.0}), CAP)

    def test_pooled_reads_the_current_rest_only(self):
        near = repeat([0.5, -0.2, 0.3, 0.0])
        old = pairs(near, key="old")
        self.assertEqual(gates.cell_cap(old, POLICY, current="new", pooled=True), CAP)
        self.assertGreater(gates.cell_cap(old + pairs(near, key="new"), POLICY,
                                          current="new", pooled=True), CAP)


class PolicyTests(unittest.TestCase):

    def test_committed_and_checked(self):
        committed = gates.load_gate_policy()
        self.assertEqual(committed["skills"]["max_runs_extension"], 1.5)
        self.assertEqual(committed["guidance"]["max_runs_extension"], 1.5)
        base = "".join(f"  {k}: {v}\n" for k, v in TEST_POLICY.items()
                       if k not in ("recheck_window", "recheck_carry", "max_runs_extension"))
        self.assertEqual(gates.parse_gate_policy(f"skills:\n{base}")["skills"]
                         ["max_runs_extension"], 1.0)
        for bad in ("0.5", "3", "true", "'1.5'", "null"):
            with self.subTest(bad=bad), self.assertRaises(gates.GatePolicyError):
                gates.parse_gate_policy(f"skills:\n{base}  max_runs_extension: {bad}\n")


if __name__ == "__main__":
    unittest.main()
