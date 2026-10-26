#!/usr/bin/env python3
"""Issue #70, part 1: the skill retirement verdict and `gates/latest.json`.

Adam's decisions: the thresholds (2026-10-10, #70) and pooled evidence
(2026-10-25), which replaced #70's four weekly sweeps, with the review rounds
of the same day: the run is the unit, the arms are independent samples pooled
by their own keys, cells come from the fixtures on main and pool only runs of
the content on main up to `--as-of`, duplicate runs count once, a run with an
errored trial does not count, floors under every standard error, zero
variance decides nothing, `cannot-discriminate`, a stricter retire side with
Holm-corrected checks, stateless confirmation at the two largest looks, and
one retirement per evaluation. harness/gates.py classifies each cell and
takes the verdict; scripts/compute_gates.py writes the artifact.

Hermetic: canned trial summaries, results trees, a fixture tree and a registry
checkout in a temporary directory, no network, no clock.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import itertools
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent.parent
ROOT = TEST_DIR.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import compute_gates  # noqa: E402
import context  # noqa: E402
import delivery  # noqa: E402
import gates  # noqa: E402
import harness_repo  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import routine_ingest_times  # noqa: E402
import run_eval  # noqa: E402
import write_vouch  # noqa: E402

POLICY_FILE = ROOT / "evals" / "gate-policy.yml"
POLICY = gates.parse_gate_policy(POLICY_FILE.read_text(encoding="utf-8"))["skills"]
#: The committed objective margin, under a floor of p(1 - p) over the scored
#: trials, needs hundreds of trials per arm before an objective delta can be
#: no-benefit (`test_the_committed_margin_needs_more_than_twenty_runs_of_three`).
#: The cell rules are tested at a wider margin; the compute_gates tests use
#: the committed policy on judge-carried fixtures.
TEST_POLICY = {**POLICY, "objective_margin": 0.4}
CLIS = ["1.0.0 (Claude Code)", "1.0.1 (Claude Code)"]
T = 100
#: Runs that differ a little from run to run, the same on both arms.
FLAT = [(80, 80, 80), (80, 80, 79)] * 10
FLAT_JUDGE = [7.0, 7.2] * 10
GAIN = [(90, 90, 90), (90, 90, 89)] * 5
LOSS = [(50, 50, 50), (50, 50, 49)] * 5
NOISY = [(100, 100, 100), (20, 20, 20)] * 5
NOISY_BACK = [(20, 20, 20), (100, 100, 100)] * 5
#: The content on main the canned runs were made of: one flat fixture.
EXPECT = {"": {"fixture_digest": "f1", "tested_digest": "t1"}}
AS_OF = "20261231T000000Z"
#: The test VOUCH_KEY (#70, round 6); a real one is a repository secret.
VOUCH_KEY = "test-only-vouch-key-example"
#: `git -c` flags committing as routine-eval-ingest.yml's identity.
INGEST_IDENTITY = ["-c", "user.name=skills-evals routine-ingest bot",
                   "-c", f"user.email={routine_ingest_times.INGEST_COMMITTER}"]


def trial(passed=80, total=T, offset=0, overall=None, *, fail=None, error=None,
          infra=False, skipped=False, pairwise=None, cost=0.25):
    """One trial summary in the shape harness/run_eval.py writes. The failing
    checks rotate with `offset` (so no check fails in every trial) unless
    `fail` names them. `error` is an error type."""
    failing = (set(fail) if fail is not None
               else {(offset * (total - passed) + i) % total for i in range(total - passed)})
    checks = [{"id": f"c{i}", "passed": i not in failing, "detail": "ok"}
              for i in range(total)]
    if infra:
        checks[0] = {"id": "c0", "passed": False,
                     "detail": "scorer_sandbox_unavailable exit=1"}
    if skipped:
        judge = {"status": "skipped", "reason": "objective-decided"}
    elif pairwise is not None:
        judge = {"mode": "pairwise", "rank": 1, "score": 1, "dimensions_mean": pairwise}
    elif overall is not None:
        judge = {"dimensions": [], "overall": overall}
    else:
        judge = None
    return {"error": {"type": error, "detail": ""} if error else None,
            "agent": {"cost_usd": cost}, "objective_checks": checks, "judge": judge,
            "judge_conditional": False}


def stamp(r: int) -> str:
    return f"202610{1 + r // 24:02d}T{r % 24:02d}0000Z"


def arm_run(role, trials, r, *, model="model-a", fixture=None, cli=None,
            tested="t1", fdig="f1", ctx=None, carried=False, skill="demo",
            conditional=False, pair="p"):
    """One index arm run, as compute_gates.build_index produces it."""
    path = f"routine-results/{stamp(r)}-00000{r % 10}/{skill}/{stamp(r)}"
    return {"skill": skill, "fixture": fixture, "model": model, "role": role,
            "timestamp": stamp(r), "path": path, "report": f"{path}/report.md",
            "tested_digest": tested, "fixture_digest": fdig,
            "arm_context_digest": ctx or f"{role}-ctx", "pair_key": pair,
            "cli_versions": [cli or CLIS[r % 2]], "run": {"id": stamp(r)},
            "judge_carried": carried, "judge_conditional": conditional,
            "trials": [gates.trial_record(t) for t in trials]}


def figures(figure, spread=True, k=3):
    """A run's trial judge figures around `figure`: spread a little within
    the run unless `spread` is false."""
    if figure is None:
        return [None] * k
    return [figure + ((i - 1) / 10 if spread else 0) for i in range(k)]


def series(role, patterns, judges=None, *, total=T, start=0, pairwise=False,
           spread=True, **kw):
    """One arm run per pattern (passed counts of its trials)."""
    out = []
    for i, pattern in enumerate(patterns):
        r = start + i
        marks = figures(judges[i] if judges else None, spread, len(pattern))
        trials = [trial(p, total, 3 * r + k, None if pairwise else marks[k],
                        pairwise=marks[k] if pairwise else None)
                  for k, p in enumerate(pattern)]
        out.append(arm_run(role, trials, r, **kw))
    return out


def cell(with_runs, without_runs, *, carried=False, policy=TEST_POLICY):
    return gates.classify_cell(with_runs, without_runs, policy, carried)


def flat_cell(n=10, **kw):
    return (series("with", FLAT[:n], FLAT_JUDGE, **kw)
            + series("without", FLAT[:n], FLAT_JUDGE, **kw))


class PolicyTests(unittest.TestCase):

    def test_committed_policy_loads_with_its_numbers(self):
        self.assertEqual(POLICY, {
            "objective_margin": 0.05, "judge_margin": 0.5, "benefit_confidence": 0.90,
            "retire_confidence": 0.975, "check_confidence": 0.90, "min_runs": 5,
            "min_cli_versions": 2, "ceiling_fraction": 0.90, "judge_ceiling": 9.0,
            "floor_fraction": 0.10, "bootstrap_resamples": 2000,
            "retire_looks": [5, 10, 20],
            # Round 6: proposal until part 2's update restriction and App exist.
            "retirement_mode": "proposal",
            "unlanded_fire_grace_hours": 72, "waived_fires": [],
            # Round 7, R7-1: the fire workflow's run numbers are read from 1.
            "fire_sequence_from": 1, "waived_fire_numbers": []})

    def _text(self, **changes):
        values = {**POLICY, **changes}
        return "skills:\n" + "".join(f"  {k}: {v}\n" for k, v in values.items()
                                     if v is not None)

    def _mode(self, text):
        return gates.parse_gate_policy(text)["skills"]["retirement_mode"]

    def test_missing_mode_is_proposal(self):
        self.assertEqual(self._mode(self._text(retirement_mode=None)), "proposal")

    def test_invalid_mode_is_proposal(self):
        for bad in ("automatic", "[auto]", "1", "true"):
            self.assertEqual(self._mode(self._text(retirement_mode=bad)), "proposal", bad)

    def test_proposal_mode_loads(self):
        self.assertEqual(self._mode(self._text(retirement_mode="proposal")), "proposal")

    def test_bad_values_are_refused(self):
        for key, bad in (("ceiling_fraction", 1.5), ("retire_confidence", 1),
                         ("benefit_confidence", 0.4), ("min_runs", 1),
                         ("min_runs", 2.5), ("bootstrap_resamples", "true"),
                         ("judge_ceiling", 11), ("objective_margin", -0.1),
                         ("floor_fraction", 1), ("retire_looks", "[10, 5]"),
                         ("retire_looks", "[3, 10]"), ("retire_looks", "[]")):
            with self.assertRaises(gates.GatePolicyError, msg=f"{key}={bad}"):
                gates.parse_gate_policy(self._text(**{key: bad}))

    def test_the_fire_sequence_keys(self):
        # Round 7, R7-1: fire_sequence_from is required (no safe default);
        # waived_fire_numbers is optional and empty by default.
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(self._text(fire_sequence_from=None))
        skills = gates.parse_gate_policy(self._text(waived_fire_numbers=None))["skills"]
        self.assertEqual((skills["fire_sequence_from"], skills["waived_fire_numbers"]),
                         (1, []))
        good = '[{number: 7, reason: "deleted by mistake", date: 2026-10-05}]'
        self.assertEqual(gates.parse_gate_policy(self._text(waived_fire_numbers=good))
                         ["skills"]["waived_fire_numbers"],
                         [{"number": 7, "reason": "deleted by mistake", "date": "2026-10-05"}])
        for key, bad in (("fire_sequence_from", 0), ("fire_sequence_from", "true"),
                         ("fire_sequence_from", 1.5), ("fire_sequence_from", "x"),
                         ("waived_fire_numbers", "{}"),
                         ("waived_fire_numbers", "[{number: 0, reason: r, date: 2026-10-05}]"),
                         ("waived_fire_numbers", "[{number: x, reason: r, date: 2026-10-05}]"),
                         ("waived_fire_numbers", "[{number: 7, reason: r}]"),
                         ("waived_fire_numbers", '[{number: 7, reason: " ", date: 2026-10-05}]'),
                         ("waived_fire_numbers", "[{number: 7, reason: r, date: 2026-10-05}, "
                                                 "{number: 7, reason: r, date: 2026-10-06}]")):
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(gates.GatePolicyError):
                    gates.parse_gate_policy(self._text(**{key: bad}))

    def test_the_unlanded_fire_keys(self):
        # Round 6, R6-2: optional, 72 hours and no waiver by default.
        text = self._text(unlanded_fire_grace_hours=None, waived_fires=None)
        skills = gates.parse_gate_policy(text)["skills"]
        self.assertEqual((skills["unlanded_fire_grace_hours"], skills["waived_fires"]),
                         (72, []))
        good = ('[{run_id: 20261001T000000Z-abcdef, reason: "session died", '
                'date: 2026-10-05}]')
        self.assertEqual(gates.parse_gate_policy(self._text(waived_fires=good))
                         ["skills"]["waived_fires"],
                         [{"run_id": "20261001T000000Z-abcdef", "reason": "session died",
                           "date": "2026-10-05"}])
        for key, bad in (("unlanded_fire_grace_hours", 0), ("unlanded_fire_grace_hours", -1),
                         ("unlanded_fire_grace_hours", "true"),
                         ("waived_fires", "{}"), ("waived_fires", "[x]"),
                         ("waived_fires", "[{run_id: 20261001T000000Z-abcdef, reason: r}]"),
                         ("waived_fires", '[{run_id: nope, reason: r, date: 2026-10-05}]'),
                         ("waived_fires", '[{run_id: 20261001T000000Z-abcdef, reason: " ", '
                                          'date: 2026-10-05}]'),
                         ("waived_fires", '[{run_id: 20261001T000000Z-abcdef, reason: r, '
                                          'date: 2026-13-05}]'),
                         ("waived_fires", '[{run_id: 20261001T000000Z-abcdef, reason: r, '
                                          'date: 2026-10-05, x: 1}]'),
                         ("waived_fires", '[{run_id: 20261001T000000Z-abcdef, reason: r, '
                                          'date: 2026-10-05}, {run_id: '
                                          '20261001T000000Z-abcdef, reason: r, '
                                          'date: 2026-10-06}]')):
            with self.subTest(key=key, bad=bad):
                with self.assertRaises(gates.GatePolicyError):
                    gates.parse_gate_policy(self._text(**{key: bad}))

    def test_missing_and_unknown_keys_are_refused(self):
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(self._text(judge_margin=None))
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(self._text() + "  sweeps: 4\n")
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy("- not a mapping\n")


class StatisticsTests(unittest.TestCase):

    def test_t_quantiles_match_the_standard_table(self):
        for p, df, value in ((0.95, 1, 6.314), (0.95, 5, 2.015), (0.95, 30, 1.697),
                             (0.975, 5, 2.571), (0.975, 10, 2.228), (0.995, 3, 5.841)):
            self.assertAlmostEqual(gates.t_quantile(p, df), value, places=3)

    def test_bootstrap_is_deterministic_and_order_free(self):
        rng = random.Random(1)
        a = [rng.random() for _ in range(9)]
        b = [rng.random() for _ in range(7)]
        first = gates.bootstrap_deltas(a, b, 2000)
        self.assertEqual(first, gates.bootstrap_deltas(a, b, 2000))
        self.assertEqual(first, gates.bootstrap_deltas(a[::-1], b[::-1], 2000))
        self.assertEqual(gates.bounds(a, b, 0.95, 2000), gates.bounds(a, b, 0.95, 2000))

    def test_welch_by_hand(self):
        # a: mean 3.5, sample variance 3.5; b: mean 2, variance 0. se =
        # sqrt(3.5 / 6); Welch df = 5 exactly; delta 1.5.
        delta, se, df = gates.welch([1, 2, 3, 4, 5, 6], [2] * 6)
        self.assertEqual((delta, df), (1.5, 5))
        self.assertAlmostEqual(se, (3.5 / 6) ** 0.5, places=12)
        low, high = gates.bounds([1, 2, 3, 4, 5, 6], [2] * 6, 0.95, 2000)
        self.assertAlmostEqual(low, 1.5 - 2.0150484 * (3.5 / 6) ** 0.5, places=6)
        self.assertAlmostEqual(high, 1.5 + 2.0150484 * (3.5 / 6) ** 0.5, places=6)

    def test_welch_df_falls_back_when_its_denominator_underflows(self):
        # Round 4, B3: variances near 1e-200 square to 0.0, and the
        # Welch-Satterthwaite ratio divided by zero. The fallback is the
        # smaller arm's n - 1.
        a, b = [0.0, 1e-100, 2e-100], [0.0, 1e-100, 2e-100, 3e-100, 0.0]
        delta, se, df = gates.welch(a, b)
        self.assertEqual(df, 2)
        self.assertGreater(se, 0)
        self.assertEqual(gates.welch(b, a)[2], 2)
        # A denominator that overflows to infinity takes the same fallback.
        self.assertEqual(gates.welch([0.0, 1e85, -1e85], [0.0, 1e85, -1e85, 5.0])[2], 2)

    def test_welch_df_is_floored_with_a_minimum_of_one(self):
        # Unequal variances: df = 1.83, floored to 1.
        self.assertEqual(gates.welch([0, 10], [0, 1, 0, 1, 0, 1])[2], 1)

    def test_the_binomial_floor_by_hand(self):
        # p = 0.8 over 30 scored trials: p(1 - p)/n = 0.16/30.
        self.assertAlmostEqual(gates.binomial_floor(0.8, 30), 0.16 / 30, places=15)
        # p is clipped to [1/(2n), 1 - 1/(2n)]: all passed is not zero.
        self.assertAlmostEqual(gates.binomial_floor(1.0, 30),
                               (1 / 60) * (1 - 1 / 60) / 30, places=15)
        self.assertEqual(gates.binomial_floor(None, 0), 0.0)

    def test_the_judge_floor_by_hand(self):
        # Within-run deviations: (7, 7, 7.5) has sum of squares 1/6 on 2 df,
        # (7, 7, 7) none on 2: pooled variance (2/6)/10 over five runs.
        figures_ = [[7, 7, 7.5]] * 2 + [[7, 7, 7]] * 3
        self.assertAlmostEqual(gates.judge_floor(figures_), (2 / 6) / 10 / 5, places=15)

    def test_the_floor_raises_each_arms_standard_error(self):
        a, b = [0.8] * 9 + [0.81], [0.8] * 10
        bare = gates.welch(a, b)
        floored = gates.welch(a, b, floors=(0.16 / 300, 0.16 / 300))
        self.assertAlmostEqual(floored[1], (2 * 0.16 / 300) ** 0.5, places=12)
        self.assertGreater(floored[1], bare[1])
        # Welch-Satterthwaite over the floored variances: two equal arms of
        # ten values each give 18.
        self.assertEqual(floored[2], 18)

    def test_reported_bounds_are_at_least_as_wide_as_the_bootstrap(self):
        a = [0.9, 0.7, 1.0, 0.6, 0.8, 0.9]
        b = [0.5, 0.8, 0.4, 0.7, 0.6, 0.3]
        deltas = gates.bootstrap_deltas(a, b, 2000)
        boot = (gates._percentile(deltas, 0.05), gates._percentile(deltas, 0.95))
        low, high = gates.bounds(a, b, 0.95, 2000)
        self.assertLess(low, boot[0])
        self.assertGreaterEqual(high, boot[1])

    def test_holm_correction_across_checks(self):
        a, b = [1, 2 / 3, 1, 2 / 3, 1], [2 / 3, 1 / 3, 2 / 3, 1, 1 / 3]
        self.assertEqual(gates.confident_checks({"x": a}, {"x": b}, 0.90, 2000), ["x"])
        null = {f"n{i}": [0.5, 0.6, 0.5, 0.6, 0.5] for i in range(19)}
        self.assertEqual(gates.confident_checks({"x": a, **null}, {"x": b, **null},
                                                0.90, 2000), [])

    def test_a_zero_variance_check_is_never_confident(self):
        self.assertEqual(gates.confident_checks({"x": [1.0] * 5}, {"x": [0.0] * 5},
                                                0.90, 2000), [])

    def test_a_checks_floor_can_withhold_confidence(self):
        a, b = [1, 2 / 3, 1, 2 / 3, 1], [2 / 3, 1 / 3, 2 / 3, 1, 1 / 3]
        wide = {"x": (0.05, 0.05)}
        self.assertEqual(gates.confident_checks({"x": a}, {"x": b}, 0.90, 2000,
                                                floors=wide), [])


class TrialTests(unittest.TestCase):

    def test_infrastructure_detail_makes_the_trial_an_error(self):
        record = gates.trial_record(trial(infra=True))
        self.assertFalse(record["scored"])
        self.assertTrue(record["infrastructure"])
        self.assertTrue(gates.trial_record(trial())["scored"])
        self.assertTrue(gates.trial_record(trial(error="scorer_unavailable"))
                        ["infrastructure"])
        self.assertFalse(gates.trial_record(trial(error="agent_failed"))["infrastructure"])
        self.assertTrue(gates.trial_record(trial(error="scorer_sandbox_unavailable"))
                        ["infrastructure"])

    def test_only_a_failed_checks_leading_marker_is_infrastructure(self):
        def with_detail(detail, passed=False):
            doc = trial()
            doc["objective_checks"][0] = {"id": "c0", "passed": passed, "detail": detail}
            return gates.trial_record(doc)
        self.assertTrue(with_detail("scorer_sandbox_unavailable exit=-1")["infrastructure"])
        # The agent's own text, anywhere but the start, or on a passed check,
        # is an ordinary check result.
        for detail, passed in (("command_nonzero exit=1 scorer_sandbox_unavailable", False),
                               ("x scorer_sandbox_unavailable exit=1", False),
                               ("scorer_sandbox_unavailable exit=1", True)):
            with self.subTest(detail=detail, passed=passed):
                record = with_detail(detail, passed)
                self.assertTrue(record["scored"])
                self.assertFalse(record["infrastructure"])

    def test_pairwise_is_read_from_dimensions_mean(self):
        self.assertEqual(gates.trial_record(trial(pairwise=8.0))["judge"], 8.0)
        self.assertEqual(gates.trial_record(trial(overall=6.5))["judge"], 6.5)
        self.assertIsNone(gates.trial_record(trial(skipped=True))["judge"])

    def test_a_malformed_trial_is_refused_by_name(self):
        good = trial()
        for name, doc in (
                ("checks not a list", {**good, "objective_checks": 5}),
                ("check not a mapping", {**good, "objective_checks": [5]}),
                ("passed not a bool", {**good, "objective_checks": [{"id": "c", "passed": 1}]}),
                ("judge not a mapping", {**good, "judge": [7]}),
                ("judge out of range", {**good, "judge": {"overall": 1e308}}),
                ("agent not a mapping", {**good, "agent": "x"})):
            with self.subTest(name=name), self.assertRaises(gates.MalformedSummary):
                gates.trial_record(doc)

    def test_an_unusable_cost_is_unknown_and_a_huge_sum_stays_finite(self):
        for bad in (-1, float("inf"), "1", True):
            self.assertIsNone(gates.trial_record(trial(cost=bad))["cost_usd"], bad)
        numbers = gates.run_numbers([gates.trial_record(trial(cost=1e308))] * 3, True)
        self.assertIsNone(numbers["cost_usd"])
        self.assertEqual(numbers["cost_unknown_trials"], 3)

    def test_an_agent_errored_trial_scores_zero_and_the_run_counts(self):
        good = [gates.trial_record(trial(overall=7.0)) for _ in range(2)]
        checks = sorted(good[0]["checks"])
        errored = good + [gates.trial_record(trial(error="timeout"))]
        numbers = gates.run_numbers(errored, True, checks)
        self.assertIsNone(numbers["skip_reason"])
        self.assertEqual((numbers["scored_trials"], numbers["errored_trials"]), (3, 1))
        self.assertAlmostEqual(numbers["run_mean"], (0.8 + 0.8 + 0) / 3)
        self.assertEqual((numbers["passed"], numbers["total"]), (160, 300))
        # No judge figure for the errored trial, so none for the run.
        self.assertIsNone(numbers["judge_mean"])
        # An infrastructure error is left out; two trials still count
        # (MIN_TRIALS_PER_RUN is 1, round 5), and none do not.
        infra = good + [gates.trial_record(trial(infra=True))]
        self.assertIsNone(gates.run_numbers(infra, True, checks)["skip_reason"])
        self.assertEqual(gates.run_numbers(infra[2:], True, checks)["skip_reason"],
                         "fewer than 1 scored or errored trials")

    def test_a_scored_trial_without_checks_on_a_fixture_with_checks_is_skipped(self):
        good = [gates.trial_record(trial()) for _ in range(3)]
        empty = gates.trial_record({**trial(), "objective_checks": []})
        self.assertTrue(empty["scored"])
        numbers = gates.run_numbers(good[:2] + [empty], True, sorted(good[0]["checks"]))
        self.assertEqual(numbers["skip_reason"], gates.NO_CHECKS_REASON)
        # The fixture's own checks count even when no trial reports one.
        self.assertEqual(gates.run_numbers([empty] * 3, True, (), True)["skip_reason"],
                         gates.NO_CHECKS_REASON)
        self.assertIsNone(gates.run_numbers([empty] * 3, True)["skip_reason"])

    def test_the_judge_counts_only_when_every_trial_was_judged_unconditionally(self):
        judged = [gates.trial_record(trial(overall=f)) for f in (7.0, 7.1, 7.2)]
        self.assertAlmostEqual(gates.run_numbers(judged, True)["judge_mean"], 7.1)
        self.assertTrue(gates.run_numbers(judged, True)["judge_spread"])
        self.assertIsNone(gates.run_numbers(judged, False)["judge_mean"])
        one_skipped = judged[:2] + [gates.trial_record(trial(skipped=True))]
        self.assertIsNone(gates.run_numbers(one_skipped * 2, True)["judge_mean"])
        same = [gates.trial_record(trial(overall=7.0))] * 3
        self.assertFalse(gates.run_numbers(same, True)["judge_spread"])


class CellTests(unittest.TestCase):

    def test_clear_gain_at_five_runs_is_benefit(self):
        self.assertEqual(cell(series("with", GAIN[:5]), series("without", LOSS[:5]))["class"],
                         "benefit")

    def test_flat_runs_are_no_benefit_only_at_two_looks(self):
        runs = flat_cell(5)
        result = cell(runs[:5], runs[5:])
        self.assertEqual((result["class"], [lk["class"] for lk in result["looks"]]),
                         ("no-benefit-pending", ["no-benefit"]))
        runs = flat_cell(10)
        result = cell(runs[:10], runs[10:])
        self.assertEqual((result["class"], [lk["n"] for lk in result["looks"]]),
                         ("no-benefit", [5, 10]))

    def test_the_committed_margin_needs_more_than_twenty_runs_of_three(self):
        runs = flat_cell(20)
        result = cell(runs[:20], runs[20:], policy=POLICY)
        self.assertEqual((result["class"], result["looks"][-1]["n"]), ("insufficient", 20))

    def test_one_flipped_check_in_thirty_identical_trials_is_not_no_benefit(self):
        # Ten runs per arm, every trial passing 8 of 10 checks; one with-arm
        # trial passes one more. The run means barely vary, so without a
        # floor the bound is tight and this would be no-benefit.
        def runs(role):
            out = []
            for r in range(10):
                marks = figures(FLAT_JUDGE[r])
                trials = [trial(8, 10, 3 * r + k, j) for k, j in enumerate(marks)]
                if role == "with" and r == 9:
                    trials[0] = trial(9, 10, 27, marks[0])
                out.append(arm_run(role, trials, r))
            return out
        result = cell(runs("with"), runs("without"), policy=POLICY)
        self.assertEqual(result["class"], "insufficient")
        self.assertEqual(result["looks"][-1]["n"], 10)

    def test_four_runs_are_insufficient(self):
        runs = flat_cell(4)
        self.assertEqual(cell(runs[:4], runs[4:])["class"], "insufficient")

    def test_one_cli_version_is_insufficient(self):
        runs = flat_cell(cli=CLIS[0])
        self.assertEqual(cell(runs[:10], runs[10:])["class"], "insufficient")

    def test_a_run_needs_one_scored_trial(self):
        runs = flat_cell(5)
        runs[0]["trials"] = [gates.trial_record(trial(infra=True))] * 3
        result = cell(runs[:5], runs[5:])
        self.assertEqual(result["class"], "insufficient")
        self.assertEqual(result["with"]["runs"], 4)
        self.assertEqual(result["skipped"], {"fewer than 1 scored or errored trials": 1})
        # One infrastructure error among three leaves two trials: it counts.
        runs = flat_cell(5)
        runs[0]["trials"][0] = gates.trial_record(trial(infra=True))
        self.assertEqual(cell(runs[:5], runs[5:])["with"]["runs"], 5)

    def test_errored_trials_are_never_scored_around(self):
        # Round 2's reproducer: the without arm errors in 2 of 5 trials per
        # run. Scored around, only the trials that went well would compare.
        with_runs = series("with", [(80,) * 5] * 10, FLAT_JUDGE)
        without_runs = series("without", [(80,) * 5] * 10, FLAT_JUDGE)
        for run in without_runs:
            run["trials"][:2] = [gates.trial_record(trial(error="agent_failed"))] * 2
        result = cell(with_runs, without_runs)
        self.assertNotIn(result["class"], ("no-benefit", "no-benefit-pending"))
        self.assertEqual((result["without"]["runs"], result["skipped"]), (10, {}))

    def test_without_arm_timeouts_censoring_its_failures_cannot_retire(self):
        # Round 3's reproducer (p2.py): twelve clean with runs; twenty-four
        # without runs, half of them with a timed-out trial. Dropping those
        # runs left only the without arm's good runs, level with the skill.
        with_runs = series("with", [(80, 80, 80)] * 12, [7.0, 7.2] * 6, carried=True)
        without_runs = []
        for r in range(24):
            if r % 2:
                trials = [trial(80, T, 3 * r + k, 7.0 + (k - 1) / 10) for k in range(2)] \
                    + [trial(0, T, 0, None, error="timeout")]
                without_runs.append(arm_run("without", trials, 100 + r, carried=True))
            else:
                without_runs += series("without", [(80, 80, 80)], [7.0 if r % 4 else 7.2],
                                       start=100 + r, carried=True)
        result = cell(with_runs, without_runs, carried=True, policy=POLICY)
        self.assertNotIn(result["class"], ("no-benefit", "no-benefit-pending"))
        self.assertEqual(result["without"]["runs"], 24)

    def test_without_arm_timeouts_can_show_benefit(self):
        def runs(role):
            out = []
            for r in range(10):
                marks = figures(FLAT_JUDGE[r])
                trials = [trial(p, T, 3 * r + k, marks[k]) for k, p in enumerate(FLAT[r])]
                if role == "without":
                    trials[2] = trial(0, T, 0, None, error="timeout")
                out.append(arm_run(role, trials, r))
            return out
        self.assertEqual(cell(runs("with"), runs("without"))["class"], "benefit")

    def test_an_errored_trial_blocks_no_benefit_at_the_looks(self):
        # One budget stop in one with run: that run has no judge figure,
        # the other nine do, and the numbers are still no-benefit.
        runs = flat_cell(10)
        runs[0]["trials"].append(gates.trial_record(trial(error="budget_exceeded")))
        result = cell(runs[:10], runs[10:])
        self.assertEqual(result["full_class"], "no-benefit")
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("agent-errored", result["reason"])

    def test_a_run_without_check_results_keeps_the_cell_from_retiring(self):
        runs = flat_cell(10)
        runs[3]["trials"][0] = gates.trial_record({**trial(), "objective_checks": []})
        result = cell(runs[:10], runs[10:])
        self.assertEqual(result["skipped"], {gates.NO_CHECKS_REASON: 1})
        self.assertEqual(result["class"], "insufficient")

    def test_noisy_runs_are_insufficient(self):
        result = cell(series("with", NOISY[:5], FLAT_JUDGE),
                      series("without", NOISY_BACK[:5], FLAT_JUDGE))
        self.assertEqual(result["class"], "insufficient")

    def test_zero_variance_decides_nothing(self):
        same = [(80, 80, 80)] * 10
        self.assertEqual(cell(series("with", same, FLAT_JUDGE),
                              series("without", same, FLAT_JUDGE))["class"], "insufficient")
        # Constant but apart: still no decision.
        self.assertEqual(cell(series("with", [(90, 90, 90)] * 5),
                              series("without", [(40, 40, 40)] * 5))["class"], "insufficient")

    def test_pass_rate_exactly_point_nine_is_ceiling(self):
        same = [(90, 90, 90)] * 5
        self.assertEqual(cell(series("with", same), series("without", same))["class"],
                         "ceiling")

    def test_pass_rate_point_eight_nine_is_not_ceiling(self):
        same = [(89, 89, 89)] * 5
        result = cell(series("with", same), series("without", same))
        self.assertEqual(result["class"], "insufficient")

    def test_a_check_failing_everywhere_cannot_discriminate(self):
        def runs(role):
            return [arm_run(role, [trial(8, 10, fail={9, (3 * r + k) % 9}) for k in range(3)], r)
                    for r in range(5)]
        self.assertEqual(cell(runs("with"), runs("without"))["class"], "cannot-discriminate")

    def test_both_arms_near_the_floor_cannot_discriminate(self):
        low = [(1, 1, 1), (1, 1, 0)] * 3
        self.assertEqual(cell(series("with", low[:5], total=10),
                              series("without", low[:5], total=10))["class"],
                         "cannot-discriminate")

    def test_insufficient_runs_come_before_cannot_discriminate(self):
        low = [(1, 1, 1), (1, 1, 0)] * 3
        self.assertEqual(cell(series("with", low[:4], total=10),
                              series("without", low[:4], total=10))["class"],
                         "insufficient")

    def test_retire_side_uses_the_stricter_bound(self):
        wide = [(80, 80, 80), (70, 70, 70)] * 3
        runs = (series("with", wide[:5], FLAT_JUDGE), series("without", wide[:5], FLAT_JUDGE))
        strict = {**POLICY, "objective_margin": 0.2}
        self.assertEqual(cell(*runs, policy=strict)["class"], "insufficient")
        loose = {**strict, "retire_confidence": 0.6}
        self.assertEqual(cell(*runs, policy=loose)["class"], "no-benefit-pending")

    def test_one_confidently_better_check_is_benefit(self):
        # Overall the arms are level; check A is better with the skill and B
        # worse, by the same amount, and C varies on both.
        def runs(role):
            out = []
            for r in range(5):
                even = r % 2 == 0
                a, b = ((3, 0) if even else (2, 1)) if role == "with" else \
                    ((0, 3) if even else (1, 2))
                c = 3 if even else 2
                trials = [trial(fail={i for i, n in enumerate((a, b, c)) if k >= n},
                                total=3, overall=7.0) for k in range(3)]
                out.append(arm_run(role, trials, r))
            return out
        result = cell(runs("with"), runs("without"))
        self.assertEqual(result["class"], "benefit")
        self.assertEqual(result["confident_checks"], ['"c0"'])

    def test_judge_needed_needs_five_judged_runs(self):
        judges = FLAT_JUDGE[:4] + [None]
        result = cell(series("with", FLAT[:5], judges), series("without", FLAT[:5], judges))
        self.assertEqual(result["class"], "insufficient")

    def test_a_conditionally_judged_run_has_no_judge_figure(self):
        result = cell(*[series(role, FLAT[:10], FLAT_JUDGE, conditional=True)
                        for role in ("with", "without")])
        self.assertEqual(result["class"], "insufficient")
        self.assertEqual(result["with"]["judge_runs"], 0)

    def test_the_judge_needs_spread_within_two_runs_per_arm(self):
        result = cell(*[series(role, FLAT[:10], FLAT_JUDGE, spread=False)
                        for role in ("with", "without")])
        self.assertEqual(result["class"], "insufficient")
        # Spread in two runs of each arm is enough.
        runs = [series(role, FLAT[:10], FLAT_JUDGE, spread=False)
                for role in ("with", "without")]
        for arm in runs:
            for run in arm[:2]:
                run["trials"] = [{**t, "judge": t["judge"] + (k - 1) / 10}
                                 for k, t in enumerate(run["trials"])]
        self.assertEqual(cell(*runs)["class"], "no-benefit")

    def test_the_judge_standard_error_is_floored_by_the_within_run_spread(self):
        # The reproducer: judge figures (7, 7, 7.5) twice and (7, 7, 7) three
        # times, on both arms.
        def runs(role):
            return [arm_run(role, [trial(80, T, 3 * r + k, j)
                                   for k, j in enumerate(marks)], r)
                    for r, marks in enumerate([[7, 7, 7.5]] * 2 + [[7, 7, 7]] * 3)]
        result = cell(runs("with"), runs("without"), carried=True)
        self.assertNotEqual(result["class"], "no-benefit")
        wj, oj = result["with"]["judge_run_means"], result["without"]["judge_run_means"]
        floor = gates.judge_floor([[7, 7, 7.5]] * 2 + [[7, 7, 7]] * 3)
        floored = gates.bounds(wj, oj, POLICY["retire_confidence"], 2000,
                               floors=(floor, floor))[1]
        self.assertAlmostEqual(result["judge"]["retire_upper"], floored, places=12)
        self.assertGreater(floored, gates.bounds(wj, oj, POLICY["retire_confidence"],
                                                 2000)[1])

    def test_skipped_judge_is_not_needed_when_the_objective_gains(self):
        def runs(role, pattern):
            return [arm_run(role, [trial(p, offset=3 * r + k, skipped=True)
                                   for k, p in enumerate(pattern[r])], r)
                    for r in range(5)]
        self.assertEqual(cell(runs("with", GAIN), runs("without", LOSS))["class"], "benefit")

    def test_saturated_objective_with_judge_gain_is_benefit(self):
        full = [(100, 100, 100)] * 5
        self.assertEqual(cell(series("with", full, [9.6, 9.4] * 3),
                              series("without", full, [8.0, 7.8] * 3))["class"], "benefit")

    def test_class_c_keeps_on_its_objective_checks_too(self):
        # Round 3's reproducer (p1.py): a pairwise fixture whose objective
        # checks pass 0.948 with the skill and 0.398 without, the judge level.
        result = cell(series("with", [(95, 95, 95), (95, 95, 94)] * 5, [7.0, 7.2] * 5,
                             pairwise=True, carried=True),
                      series("without", [(40, 40, 40), (40, 40, 39)] * 5, [7.0, 7.2] * 5,
                             pairwise=True, carried=True), carried=True, policy=POLICY)
        self.assertEqual(result["class"], "benefit")
        self.assertIn("objective", result["reason"])
        # And a judge gain alone still keeps.
        result = cell(series("with", LOSS[:5], [9.0, 8.8] * 3),
                      series("without", GAIN[:5], [6.0, 6.2] * 3), carried=True)
        self.assertEqual(result["class"], "benefit")

    def test_class_c_is_no_benefit_only_when_its_objective_is_too(self):
        runs = flat_cell(10)
        self.assertEqual(cell(runs[:10], runs[10:], carried=True)["class"], "no-benefit")
        # The committed objective margin is not met by thirty trials per arm.
        result = cell(runs[:10], runs[10:], carried=True, policy=POLICY)
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("objective", result["looks"][-1]["reason"])
        # Without objective checks the judge alone decides.
        def judge_only(role):
            return [arm_run(role, [{**trial(overall=j), "objective_checks": []}
                                   for j in figures(FLAT_JUDGE[r])], r) for r in range(10)]
        result = cell(judge_only("with"), judge_only("without"), carried=True, policy=POLICY)
        self.assertEqual(result["class"], "no-benefit")

    def test_class_c_ceiling_on_the_judge_figure(self):
        high = [9.2, 9.4] * 3
        self.assertEqual(cell(series("with", FLAT[:5], high),
                              series("without", FLAT[:5], high), carried=True)["class"],
                         "ceiling")

    def test_pairwise_class_c_reads_dimensions_mean(self):
        result = cell(series("with", FLAT[:5], [8.0, 8.2] * 3, pairwise=True),
                      series("without", FLAT[:5], [6.0, 6.2] * 3, pairwise=True),
                      carried=True)
        self.assertEqual(result["class"], "benefit")

    def test_pairwise_without_a_judge_figure_is_insufficient(self):
        self.assertEqual(cell(series("with", FLAT[:5]), series("without", FLAT[:5]),
                              carried=True)["class"], "insufficient")


class LookTests(unittest.TestCase):

    def test_a_later_look_that_is_not_no_benefit_decides(self):
        swing = [(100, 100, 100), (0, 0, 0)] * 3
        with_runs = (series("with", FLAT[:5], FLAT_JUDGE)
                     + series("with", swing[:5], FLAT_JUDGE, start=5))
        without_runs = (series("without", FLAT[:5], FLAT_JUDGE)
                        + series("without", swing[1:6], FLAT_JUDGE, start=5))
        result = cell(with_runs, without_runs)
        self.assertEqual([lk["class"] for lk in result["looks"]],
                         ["no-benefit", "insufficient"])
        self.assertEqual(result["class"], "insufficient")

    def test_no_benefit_needs_both_of_the_two_largest_looks(self):
        # The first five runs show one CLI version, so the five-run look is
        # insufficient; the ten-run look alone is not enough.
        def runs(role, n):
            return (series(role, FLAT[:5], FLAT_JUDGE, cli=CLIS[0])
                    + series(role, FLAT[5:n], FLAT_JUDGE[5:n], start=5, cli=CLIS[1]))
        result = cell(runs("with", 10), runs("without", 10))
        self.assertEqual(([lk["class"] for lk in result["looks"]], result["class"]),
                         (["insufficient", "no-benefit"], "no-benefit-pending"))
        # At twenty runs the two largest looks are ten and twenty.
        result = cell(runs("with", 20), runs("without", 20))
        self.assertEqual(([lk["class"] for lk in result["looks"]], result["class"]),
                         (["insufficient", "no-benefit", "no-benefit"], "no-benefit"))

    def test_benefit_is_declared_at_any_count(self):
        result = cell(series("with", GAIN[:7]), series("without", LOSS[:7]))
        self.assertEqual((result["class"], [lk["n"] for lk in result["looks"]]),
                         ("benefit", [5]))

    def test_the_looks_use_the_first_runs_in_timestamp_order(self):
        with_runs = series("with", FLAT[:10], FLAT_JUDGE) + series(
            "with", NOISY[:3], FLAT_JUDGE, start=10)
        without_runs = series("without", FLAT[:10], FLAT_JUDGE) + series(
            "without", NOISY_BACK[:3], FLAT_JUDGE, start=10)
        result = cell(with_runs[::-1], without_runs[::-1])
        self.assertEqual(result["class"], "no-benefit")


class VerdictTests(unittest.TestCase):
    MODELS = ["model-a", "model-b", "model-c"]

    def verdict(self, runs, models=None, expected=None):
        return gates.retirement({"runs": runs}, models or self.MODELS, "demo", TEST_POLICY,
                                expected if expected is not None else EXPECT)

    @staticmethod
    def expect(*fixtures, tested="t1", fdig="f1"):
        return {f: {"fixture_digest": fdig, "tested_digest": tested} for f in fixtures}

    def flat(self, model, n=10, **kw):
        return flat_cell(n, model=model, **kw)

    def gain(self, model, **kw):
        return series("with", GAIN[:5], model=model, **kw) + series(
            "without", LOSS[:5], model=model, **kw)

    def ceiling(self, model, **kw):
        same = [(90, 90, 90)] * 5
        return series("with", same, model=model, **kw) + series(
            "without", same, model=model, **kw)

    def low(self, model, **kw):
        low = [(1, 1, 1), (1, 1, 0)] * 3
        return series("with", low[:5], model=model, total=10, **kw) + series(
            "without", low[:5], model=model, total=10, **kw)

    def test_every_cell_no_benefit_retires(self):
        runs = [r for m in self.MODELS for f in ("one", "two")
                for r in self.flat(m, fixture=f)]
        self.assertEqual(self.verdict(runs, expected=self.expect("one", "two"))["verdict"],
                         "retire")

    def test_a_cell_with_one_look_makes_the_verdict_pending(self):
        runs = [r for m in self.MODELS[1:] for r in self.flat(m)] + self.flat("model-a", 5)
        self.assertEqual(self.verdict(runs)["verdict"], "retire-pending")

    def test_one_benefit_cell_keeps(self):
        runs = [r for m in self.MODELS[1:] for r in self.flat(m)] + self.gain("model-a")
        self.assertEqual(self.verdict(runs)["verdict"], "keep")

    def test_one_ceiling_cell_among_no_benefit_is_ceiling(self):
        runs = [r for m in self.MODELS[1:] for r in self.flat(m, 5)] + self.ceiling("model-a")
        self.assertEqual(self.verdict(runs)["verdict"], "ceiling")

    def test_all_ceiling_cells_never_retire(self):
        fixtures = ("one", "two", "three", "four")
        runs = [r for m in self.MODELS for f in fixtures for r in self.ceiling(m, fixture=f)]
        self.assertEqual(self.verdict(runs, expected=self.expect(*fixtures))["verdict"],
                         "ceiling")

    def test_cannot_discriminate_outranks_ceiling(self):
        runs = self.ceiling("model-a") + self.low("model-b") + self.flat("model-c")
        self.assertEqual(self.verdict(runs)["verdict"], "cannot-discriminate")

    def test_insufficient_outranks_cannot_discriminate(self):
        runs = self.low("model-a") + self.flat("model-b") + self.flat("model-c", 4)
        self.assertEqual(self.verdict(runs)["verdict"], "insufficient")

    def test_a_roster_model_with_no_runs_is_insufficient(self):
        result = self.verdict([r for m in self.MODELS[:2] for r in self.flat(m)])
        self.assertEqual(result["verdict"], "insufficient")
        self.assertEqual([c["model"] for c in result["cells"] if c["class"] == "missing"],
                         ["model-c"])

    def test_a_model_off_the_roster_is_ignored(self):
        runs = [r for m in self.MODELS for r in self.flat(m)] + self.gain("model-old")
        self.assertEqual(self.verdict(runs)["verdict"], "retire")

    def test_no_runs_is_insufficient(self):
        self.assertEqual(self.verdict([])["verdict"], "insufficient")

    def test_an_empty_roster_never_retires(self):
        # Round 3's reproducer: no roster model, so no cell, so nothing
        # failed "every cell shows no benefit" and the verdict was retire.
        for runs in ([], [r for r in self.flat("model-a")]):
            with self.subTest(runs=len(runs)):
                result = gates.retirement({"runs": runs}, [], "demo", POLICY, EXPECT)
                self.assertEqual((result["verdict"], result["cells"]), ("insufficient", []))

    def test_cells_come_from_the_fixtures_on_main(self):
        # A writing-adrs-like skill: four fixtures, runs on only one.
        fixtures = ("a", "b", "c", "d")
        runs = self.flat("model-a", fixture="a") + self.gain("model-a", fixture="gone")
        result = self.verdict(runs, ["model-a"], self.expect(*fixtures))
        self.assertEqual(result["verdict"], "insufficient")
        self.assertEqual([(c["fixture"], c["class"]) for c in result["cells"]],
                         [("a", "no-benefit"), ("b", "missing"), ("c", "missing"),
                          ("d", "missing")])

    def test_runs_of_a_fixture_no_longer_on_main_are_dropped(self):
        runs = self.flat("model-a", fixture="a") + self.gain("model-a", fixture="gone")
        result = self.verdict(runs, ["model-a"], self.expect("a"))
        self.assertEqual(result["verdict"], "retire")
        self.assertEqual(len(result["runs_used"]), 20)

    def test_a_skill_with_no_fixture_on_main_is_insufficient(self):
        result = self.verdict(self.flat("model-a"), ["model-a"], {})
        self.assertEqual((result["verdict"], result["cells"]), ("insufficient", []))
        self.assertIn("no fixture", result["reason"])

    def test_the_without_arm_pools_across_skill_content(self):
        runs = (series("with", FLAT[:10], FLAT_JUDGE, tested="new")
                + series("without", FLAT[:10], FLAT_JUDGE, tested="old"))
        self.assertEqual(self.verdict(runs, ["model-a"], self.expect("", tested="new"))
                         ["verdict"], "retire")

    def test_new_skill_content_starts_confirmation_over(self):
        old = series("with", FLAT[:10], FLAT_JUDGE, tested="old")
        new = series("with", FLAT[10:15], FLAT_JUDGE[10:15], start=10, tested="new")
        without = series("without", FLAT[:15], FLAT_JUDGE)
        result = self.verdict(old + new + without, ["model-a"], self.expect("", tested="new"))
        self.assertEqual(result["verdict"], "retire-pending")
        self.assertEqual(result["cells"][0]["with"]["runs"], 5)

    def test_a_stale_run_of_old_content_does_not_choose_the_pool(self):
        # Ten flat runs of content A, three of B (on main), then one late run
        # of A stamped newest. The newest run is not what is current.
        a = series("with", FLAT[:10], FLAT_JUDGE, tested="A")
        b = series("with", FLAT[10:13], FLAT_JUDGE[10:13], start=10, tested="B")
        stale = series("with", FLAT[:1], FLAT_JUDGE, start=13, tested="A")
        without = series("without", FLAT[:14], FLAT_JUDGE)
        result = self.verdict(a + b + stale + without, ["model-a"],
                              self.expect("", tested="B"))
        self.assertEqual(result["verdict"], "insufficient")
        self.assertEqual(result["cells"][0]["with"]["runs"], 3)

    def test_runs_of_another_fixture_or_arm_context_are_not_pooled(self):
        for field in ("fdig", "ctx"):
            with self.subTest(field=field):
                old = series("with", FLAT[:2], FLAT_JUDGE, **{field: "older"})
                new = series("with", FLAT[2:5], FLAT_JUDGE, start=2)
                without = series("without", FLAT[:5], FLAT_JUDGE)
                result = self.verdict(old + new + without, ["model-a"])
                self.assertEqual(result["verdict"], "insufficient")
                self.assertEqual(result["cells"][0]["with"]["runs"], 3)

    def test_the_arms_are_paired_on_one_guidance_and_skill_set(self):
        # Round 5's reproducer (test_ctx.py): twenty without runs from old
        # guidance G1, then fifteen of each arm from new guidance G2, which
        # lowers both arms; the skill still adds 0.1. Pooled independently,
        # the without arm took G1's runs (it had the most), and the cell
        # compared G2 with against G1 without: retire. Chosen jointly, only
        # G2 with G2 counts.
        lower = [(50, 50, 50), (50, 50, 49)] * 10
        without_g1 = series("without", FLAT[:20], FLAT_JUDGE, ctx="skills0:G1",
                            pair="others:G1")
        with_g2 = series("with", FLAT[:20], FLAT_JUDGE, ctx="skills1:G2", start=30,
                         pair="others:G2")
        without_g2 = series("without", lower[:15], FLAT_JUDGE, ctx="skills0:G2", start=30,
                            pair="others:G2")
        matched = self.verdict(with_g2 + without_g2, ["model-a"])
        self.assertEqual(matched["verdict"], "keep")
        mixed = self.verdict(without_g1 + with_g2 + without_g2, ["model-a"])
        self.assertEqual(mixed["verdict"], "keep")
        self.assertEqual(mixed["cells"][0]["key"]["without_context"], "skills0:G2")
        self.assertEqual((mixed["cells"][0]["with"]["runs"],
                          mixed["cells"][0]["without"]["runs"]), (20, 15))

    def test_no_shared_pair_or_a_tie_is_insufficient(self):
        unpaired = (series("with", FLAT[:10], FLAT_JUDGE, pair="others:G2")
                    + series("without", FLAT[:10], FLAT_JUDGE, pair="others:G1"))
        result = self.verdict(unpaired, ["model-a"])
        self.assertEqual(result["verdict"], "insufficient")
        self.assertIn("pooling key incomplete", result["cells"][0]["reason"])
        # No pair key at all (a summary from before others_digest).
        result = self.verdict(flat_cell(pair=None), ["model-a"])
        self.assertEqual(result["verdict"], "insufficient")
        # Two pairs with as many runs in their smaller arms: neither.
        tie = (flat_cell(6, pair="others:G1")
               + series("with", FLAT[:6], FLAT_JUDGE, start=40, ctx="w2", pair="others:G2")
               + series("without", FLAT[:6], FLAT_JUDGE, start=40, ctx="o2",
                        pair="others:G2"))
        self.assertEqual(self.verdict(tie, ["model-a"])["cells"][0]["key"]["with_context"],
                         None)
        # The pair with more runs in its SMALLER arm wins, not the larger.
        lopsided = (series("with", FLAT[:20], FLAT_JUDGE, pair="others:G1")
                    + series("without", FLAT[:5], FLAT_JUDGE, pair="others:G1")
                    + series("with", FLAT[:6], FLAT_JUDGE, start=40, ctx="w2",
                             pair="others:G2")
                    + series("without", FLAT[:6], FLAT_JUDGE, start=40, ctx="o2",
                             pair="others:G2"))
        key = self.verdict(lopsided, ["model-a"])["cells"][0]["key"]
        self.assertEqual((key["with_context"], key["without_context"]), ("w2", "o2"))

    def test_one_trial_runs_count_and_retire_only_at_the_same_looks(self):
        # Round 5, N1: the weekly sweep fires one trial per run. Such a run
        # counts, and no-benefit still needs both of the two largest looks.
        one = [(80,), (79,)] * 10
        judges = [7.0, 7.2] * 10

        def runs(n):
            return (series("with", one[:n], judges, spread=False)
                    + series("without", one[:n], judges, spread=False))
        for n, want in ((4, "insufficient"), (9, "insufficient"),
                        (10, "no-benefit-pending"), (19, "no-benefit-pending"),
                        (20, "no-benefit")):
            with self.subTest(n=n):
                result = cell(*(lambda r: (r[:n], r[n:]))(runs(n)), carried=True)
                self.assertEqual(result["class"], want, result["reason"])
                self.assertEqual(result["with"]["runs"], n)
        # Its bounds are the run-level ones: the judge floor is 0 (no run has
        # two trials) and the objective floor is binomial over its trials.
        result = cell(*(lambda r: (r[:20], r[20:]))(runs(20)), carried=True)
        self.assertEqual((result["with"]["judge_floor"], result["without"]["judge_floor"]),
                         (0.0, 0.0))
        self.assertEqual([look["n"] for look in result["looks"]], [5, 10, 20])
        rates = [r / T for r in (80, 79) * 10]
        _, upper = gates.bounds(
            rates, rates, TEST_POLICY["retire_confidence"],
            TEST_POLICY["bootstrap_resamples"],
            floors=tuple(gates.binomial_floor(sum(rates) / 20, 20) for _ in "ab"))
        self.assertAlmostEqual(result["objective"]["retire_upper"], upper)
        # Equal judge figures in every one-trial run of an arm cannot bound
        # a delta, even when the other arm's vary: there is no spread to
        # stand in for the missing within-run floor.
        flat = (series("with", one, [7.0] * 20, spread=False)
                + series("without", one, [7.0] * 20, spread=False))
        self.assertEqual(cell(flat[:20], flat[20:], carried=True)["class"], "insufficient")
        half = (series("with", one, [7.0] * 20, spread=False)
                + series("without", one, judges, spread=False))
        result = cell(half[:20], half[20:], carried=True)
        self.assertEqual(result["class"], "insufficient", result["reason"])
        self.assertIn("run judge figures that are not all equal", result["reason"])

    def test_the_arm_context_is_the_newest_among_runs_of_the_content_on_main(self):
        # The newest with run is of other content and another context; the
        # context comes from the newest run of the content on main.
        runs = flat_cell() + series("with", FLAT[:1], FLAT_JUDGE, start=19,
                                    tested="other", ctx="other-ctx")
        result = self.verdict(runs, ["model-a"])
        self.assertEqual(result["cells"][0]["key"]["with_context"], "with-ctx")
        self.assertEqual(result["verdict"], "retire")

    def test_unknown_content_on_main_is_insufficient(self):
        for field in ("tested_digest", "fixture_digest"):
            with self.subTest(field=field):
                expected = {"": {**EXPECT[""], field: None}}
                result = self.verdict(flat_cell(), ["model-a"], expected)
                self.assertEqual(result["verdict"], "insufficient")
                self.assertIn("pooling key incomplete", result["cells"][0]["reason"])
                self.assertIn(field, result["cells"][0]["reason"])

    def test_cells_record_runs_reports_and_cost(self):
        result = self.verdict(self.flat("model-a"), ["model-a"])
        c = result["cells"][0]
        self.assertEqual(len(c["runs"]["with"]), 10)
        entry = c["runs"]["with"][0]
        self.assertEqual(entry["run"], {"id": stamp(0)})
        self.assertEqual(entry["report"]["url"],
                         "https://github.com/Adam-S-Daniel/skills-evals/blob/"
                         "persistent/eval-results/" + entry["report"]["path"])
        self.assertAlmostEqual(c["cost_usd"], 20 * 3 * 0.25, places=12)
        self.assertEqual(len(result["runs_used"]), 20)
        self.assertEqual(result["runs_used"][0].split("#")[1:], ["", "with"])

    def test_the_run_key_names_the_fixture(self):
        one, two = (series("with", FLAT[:1], fixture=f)[0] for f in ("one", "two"))
        self.assertEqual(one["path"], two["path"])
        self.assertNotEqual(gates.run_key(one), gates.run_key(two))
        self.assertEqual(gates.run_key(one), f"{one['path']}#one#with")


class RunEvalRecordTests(unittest.TestCase):
    """What harness/run_eval.py records for the verdict to key on."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def git(self, *args, cwd):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    def repo(self):
        """A Git checkout holding one fixture, everything staged."""
        repo = self.tmp / "repo"
        fixture = repo / "evals" / "demo"
        (fixture / "seed").mkdir(parents=True)
        (fixture / "references").mkdir()
        (fixture / "fixture.yaml").write_text("skill: demo\n", encoding="utf-8")
        (fixture / "seed" / "a.txt").write_text("a", encoding="utf-8")
        (fixture / "references" / "r.md").write_text("r", encoding="utf-8")
        (repo / "shared.txt").write_text("s", encoding="utf-8")
        (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        self.git("init", "-q", cwd=repo)
        self.git("add", "-A", cwd=repo)
        return repo, fixture

    def test_the_requested_model_is_recorded_apart_from_models_used(self):
        run_eval._write_summary(self.tmp, "demo", "with_skill", "20261001T000000Z",
                                None, None, [], None, None,
                                models=["model-sub", "model-x"], agent_model="model-x",
                                agent_usage={"tokens": {"model-sub": {}, "model-x": {}},
                                             "dropped": 0, "complete": True})
        doc = json.loads((self.tmp / "demo" / "20261001T000000Z" / "with_skill"
                          / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["cross_model"]["model"], "model-x")
        self.assertEqual(run_eval._arm_model([doc]), "model-x")

    def test_fixture_digest_covers_tracked_fixture_files_only(self):
        repo, fixture = self.repo()
        first = run_eval.fixture_digest(fixture)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        # An ignored node_modules does not move it.
        (fixture / "seed" / "node_modules" / "pkg").mkdir(parents=True)
        (fixture / "seed" / "node_modules" / "pkg" / "index.js").write_text("x",
                                                                           encoding="utf-8")
        self.assertEqual(first, run_eval.fixture_digest(fixture))
        # The same tracked content elsewhere gives the same digest.
        copy = self.tmp / "copy"
        shutil.copytree(repo, copy, symlinks=True)
        self.assertEqual(first, run_eval.fixture_digest(copy / "evals" / "demo"))
        for rel in ("fixture.yaml", "seed/a.txt", "references/r.md"):
            with self.subTest(rel=rel):
                path = fixture / rel
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "!", encoding="utf-8")
                self.git("add", "--", rel, cwd=fixture)
                self.assertNotEqual(first, run_eval.fixture_digest(fixture))
                path.write_text(original, encoding="utf-8")
                self.git("add", "--", rel, cwd=fixture)
        self.assertEqual(first, run_eval.fixture_digest(fixture))
        # A file outside the fixture directory does not count.
        (repo / "evals" / "other.txt").write_text("o", encoding="utf-8")
        self.git("add", "--", "evals/other.txt", cwd=repo)
        self.assertEqual(first, run_eval.fixture_digest(fixture))

    def test_no_digest_outside_git_or_for_a_dirty_fixture(self):
        repo, fixture = self.repo()
        outside = self.tmp / "plain"
        shutil.copytree(fixture, outside)
        self.assertIsNone(run_eval.fixture_digest(outside))
        # A tracked file changed but not staged.
        (fixture / "seed" / "a.txt").write_text("changed", encoding="utf-8")
        self.assertIsNone(run_eval.fixture_digest(fixture))
        self.git("checkout", "--", "evals/demo/seed/a.txt", cwd=repo)
        self.assertIsNotNone(run_eval.fixture_digest(fixture))
        # An untracked file that is not ignored.
        (fixture / "seed" / "scratch.txt").write_text("x", encoding="utf-8")
        self.assertIsNone(run_eval.fixture_digest(fixture))

    def test_a_symlinks_digest_folds_in_its_tracked_target(self):
        repo, fixture = self.repo()
        os.symlink("../../../shared.txt", fixture / "seed" / "link")
        self.git("add", "-A", cwd=repo)
        first = run_eval.fixture_digest(fixture)
        (repo / "shared.txt").write_text("changed", encoding="utf-8")
        self.git("add", "-A", cwd=repo)
        self.assertNotEqual(first, run_eval.fixture_digest(fixture))

    def test_a_path_that_is_not_utf_8_is_hashed_not_decoded_by_locale(self):
        repo, fixture = self.repo()
        name = os.fsencode(str(fixture / "seed")) + b"/caf\xe9.txt"
        with open(name, "wb") as stream:
            stream.write(b"x")
        self.git("-c", "core.quotepath=false", "add", "-A", cwd=repo)
        first = run_eval.fixture_digest(fixture)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        self.assertEqual(first, run_eval.fixture_digest(fixture))

    def test_a_checkouts_clean_filter_never_runs(self):
        # Round 3's reproducer: `ls-files -m` ran `filter.evil.clean`, named
        # by the fixture's own .gitattributes.
        repo, fixture = self.repo()
        marker = self.tmp / "PWNED"
        (fixture / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
        self.git("add", "-A", cwd=repo)
        self.git("config", "filter.evil.clean", f"sh -c 'touch {marker}; cat'", cwd=repo)
        marker.unlink(missing_ok=True)
        attributes = self.tmp / "attributes"
        attributes.write_text("* filter=evil\n", encoding="utf-8")
        self.git("config", "core.attributesFile", str(attributes), cwd=repo)
        self.assertIsNotNone(run_eval.fixture_digest(fixture))
        (fixture / "seed" / "a.txt").write_text("changed", encoding="utf-8")
        self.assertIsNone(run_eval.fixture_digest(fixture))
        self.assertFalse(marker.exists())

    def test_a_symlink_to_a_directory_has_no_digest(self):
        repo, fixture = self.repo()
        (repo / "shared").mkdir()
        (repo / "shared" / "f.txt").write_text("f", encoding="utf-8")
        os.symlink("../../../shared", fixture / "seed" / "dir")
        self.git("add", "-A", cwd=repo)
        self.assertIsNone(run_eval.fixture_digest(fixture))
        # Checked out as text, the target is still a tracked directory.
        (fixture / "seed" / "dir").unlink()
        (fixture / "seed" / "dir").write_text("../../../shared", encoding="utf-8")
        self.assertIsNone(run_eval.fixture_digest(fixture))

    def test_a_symlink_to_anything_git_does_not_pin_has_no_digest(self):
        # Round 4, N4: the target must be a regular file tracked in the
        # checkout, or a change to it is no change to the digest.
        repo, fixture = self.repo()
        (repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (repo / "ignored.txt").write_text("i", encoding="utf-8")
        (repo / "loose.txt").write_text("l", encoding="utf-8")
        (self.tmp / "outside.txt").write_text("o", encoding="utf-8")
        os.symlink("shared.txt", repo / "alias.txt")
        self.git("add", ".gitignore", "alias.txt", cwd=repo)
        link = fixture / "seed" / "link"
        for target in ("../../../alias.txt", "../../../ignored.txt", "../../../loose.txt",
                       os.path.relpath(self.tmp / "outside.txt", link.parent),
                       str(self.tmp / "outside.txt"), "../../../missing.txt"):
            with self.subTest(target=target):
                link.unlink(missing_ok=True)
                os.symlink(target, link)
                self.git("add", "-f", str(link.relative_to(repo)), cwd=repo)
                self.assertIsNone(run_eval.fixture_digest(fixture))
        link.unlink()
        os.symlink("../../../shared.txt", link)
        self.git("add", str(link.relative_to(repo)), cwd=repo)
        self.assertIsNotNone(run_eval.fixture_digest(fixture))

    def test_a_working_file_that_is_not_its_staged_blob_has_no_digest(self):
        repo, fixture = self.repo()
        self.assertIsNotNone(run_eval.fixture_digest(fixture))
        # Same size, other bytes: only a content hash tells them apart.
        (fixture / "seed" / "a.txt").write_text("b", encoding="utf-8")
        self.assertIsNone(run_eval.fixture_digest(fixture))
        (fixture / "seed" / "a.txt").write_text("a", encoding="utf-8")
        self.assertIsNotNone(run_eval.fixture_digest(fixture))
        (fixture / "seed" / "a.txt").chmod(0o755)
        self.assertIsNone(run_eval.fixture_digest(fixture))
        (fixture / "seed" / "a.txt").chmod(0o644)
        (fixture / "seed" / "a.txt").unlink()
        self.assertIsNone(run_eval.fixture_digest(fixture))

    def test_a_repository_fsmonitor_never_runs(self):
        repo, fixture = self.repo()
        marker = self.tmp / "fsmonitor-ran"
        hook = self.tmp / "fsmonitor.sh"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
        hook.chmod(0o755)
        self.git("config", "core.fsmonitor", str(hook), cwd=repo)
        self.assertIsNotNone(run_eval.fixture_digest(fixture))
        self.assertFalse(marker.exists())
        harness_repo._git_out("rev-parse", "--path-format=absolute", "--git-common-dir",
                              cwd=repo)
        self.assertFalse(marker.exists())

    def _run_trials(self, fixture, hold=None):
        args = argparse.Namespace(results_dir=self.tmp, trials=2)
        item = {"fixture": fixture, "seed": self.tmp, "name": None}
        arm_dir = self.tmp / "demo" / "20261001T000000Z" / "with_skill"
        for k in (1, 2):
            run_eval._run_arm("with_skill", fixture, self.tmp, {}, args,
                              "20261001T000000Z", ("model-x", None, "no judge"),
                              out_dir=arm_dir / f"trial-{k}", extra={"trial": k},
                              hold=hold)
        run_eval._aggregate_arm("with_skill", item, args, "20261001T000000Z")
        return [json.loads(p.read_text(encoding="utf-8"))
                for p in (arm_dir / "trial-1" / "summary.json", arm_dir / "summary.json")]

    def test_each_arm_summary_carries_the_fixture_digest(self):
        digest = "ab" * 32
        for doc in self._run_trials({"skill": "demo", "prompt": "p",
                                     "_fixture_digest": digest}):
            self.assertEqual(doc["fixture_digest"], digest)

    def test_no_fixture_digest_means_no_field(self):
        for doc in self._run_trials({"skill": "demo", "prompt": "p"}):
            self.assertNotIn("fixture_digest", doc)

    def test_each_arm_summary_says_whether_its_judge_was_conditional(self):
        fixture = {"skill": "demo", "prompt": "p"}
        for doc in self._run_trials(fixture):
            self.assertIs(doc["judge_conditional"], False)
        shutil.rmtree(self.tmp / "demo")
        for doc in self._run_trials(fixture, hold=[]):
            self.assertIs(doc["judge_conditional"], True)

    def test_the_ingester_checks_the_new_fields(self):
        tokens = {"model-x": {"input_tokens": 1, "output_tokens": 1,
                              "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 0,
                              "canonical_model": "model-x"}}

        def summary(**extra):
            out = self.tmp / "s" / str(len(list(self.tmp.glob("s/*"))))
            run_eval._write_summary(out, "demo", "with_skill", "20261001T000000Z",
                                    None, None, [], None, None, models=["model-x"],
                                    agent_model="model-x", extra={"n": 1, **extra},
                                    agent_usage={"tokens": tokens, "dropped": 0,
                                                 "complete": True})
            return json.loads((out / "demo" / "20261001T000000Z" / "with_skill"
                               / "summary.json").read_text(encoding="utf-8"))
        parts = ingest.parse_result_path("demo/20261001T000000Z/with_skill/summary.json")
        ingest.check_summary(summary(fixture_digest="ab" * 32, judge_conditional=False),
                             "ok", parts)
        for name, extra in (("short digest", {"fixture_digest": "ab"}),
                            ("upper-case digest", {"fixture_digest": "AB" * 32}),
                            ("digest not a string", {"fixture_digest": 7}),
                            ("conditional not a bool", {"judge_conditional": 0})):
            with self.subTest(name=name), self.assertRaises(ingest.Rejected):
                ingest.check_summary(summary(**extra), name, parts)


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def write_arm_runs(tree: Path, skill, model, patterns, judges, *, tested, fdig,
                   start=0, model_tag="a", requested=True, without_judges=None,
                   fixture=None, checks=True):
    """Both arms of each run, laid out as routine-results; the without arm
    repeats `judges` unless `without_judges` gives its own. Without `checks`
    the trials have no objective checks (a judge-only fixture). Returns the
    run ids written."""
    run_ids = []
    for i, pattern in enumerate(patterns):
        r = start + i
        run_ids.append(f"{stamp(r)}-{model_tag}0000{r % 10}")
        rel = f"routine-results/{run_ids[-1]}/{skill}/{stamp(r)}"
        base = tree / rel
        base.mkdir(parents=True, exist_ok=True)
        (base / "report.md").write_text("# report\n", encoding="utf-8")
        for role in ("with", "without"):
            arm = base / (fixture or "") / f"{role}_skill"
            write_json(arm / "summary.json", {
                "skill": skill, "arm": f"{role}_skill", "role": role,
                "aggregate": {}, "harness": {"version": CLIS[r % 2]},
                "cross_model": {"model": model if requested else None},
                "context_subject": {"tested_digest": tested},
                "arm_context": {"skills_digest": role, "guidance_digest": "g",
                                "others_digest": "o"},
                "context": {"guidance": {"digest": "g"}},
                "fixture_digest": fdig, "judge_conditional": False,
                "n": len(pattern), "errors": 0,
                "run": {"id": stamp(r), "billing": "api"}})
            marks = figures((judges if role == "with" or without_judges is None
                             else without_judges)[i])
            for k, passed in enumerate(pattern):
                # As in real trials, no two arms' trial bytes are the same
                # (the arms differ in cost): identical bytes are a copy, and
                # a copy counts once.
                doc = trial(passed, T, 3 * r + k, marks[k],
                            cost=0.25 if role == "with" else 0.5)
                if not checks:
                    doc["objective_checks"] = []
                write_json(arm / f"trial-{k + 1}" / "summary.json",
                           {**doc, "skill": skill, "timestamp": stamp(r),
                            # A trial records its own requested model, as
                            # run_eval's `_write_summary` does.
                            **({"cross_model": {"model": model}} if requested else {})})
    return run_ids


def run_time(run_id: str):
    from datetime import datetime, timezone
    return datetime.strptime(run_id[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def iso(moment) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fire_title(fixture_path: str, model: str = "", mode: str = "eval", arms: str = "both",
               trials: int = 3) -> str:
    return (f"Fire eval routine: mode={mode} fixture={fixture_path} model={model} "
            f"arms={arms} trials={trials}")


#: A vouch.json MAC no key made: `seal` replaces it with the real one.
PLACEHOLDER_MAC = "0" * 64


def real_mac(root: Path, run_id: str, files) -> str:
    """The MAC the routine writes for `files` (paths under `root`) of run
    `run_id`, under the test VOUCH_KEY (scripts/write_vouch.py)."""
    return write_vouch.mac(write_vouch.derive_nonce(VOUCH_KEY.encode(), run_id),
                           {rel: (root / rel).read_bytes() for rel in files
                            if rel != "vouch.json"})


def git_blob(path: Path) -> str:
    import hashlib
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class ComputeGatesTests(unittest.TestCase):
    """The committed policy, on judge-carried fixtures (no objective checks
    in fixture.yaml): the cells are decided on the judge."""
    SKILLS = ("flat", "gain", "unasked", "one", "two", "guidancebot")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tree = self.tmp / "tree"
        self.roster = self.tmp / "roster.yml"
        self.roster.write_text("arms:\n  - id: model-a\n", encoding="utf-8")
        self.fires, self.ingest = [], {}
        # main: two commits; a fire runs the first, main is the second.
        self.main_repo = self.tmp / "main"
        self.main_repo.mkdir()
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(git + ["init", "-q"], cwd=self.main_repo, check=True)
        shas = []
        for n in ("fire", "main"):
            subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", n],
                           cwd=self.main_repo, check=True)
            shas.append(subprocess.run(git + ["rev-parse", "HEAD"], cwd=self.main_repo,
                                       check=True, capture_output=True,
                                       text=True).stdout.strip())
        self.fire_sha, self.main_sha = shas
        # The fixtures on main, tracked in Git, and a registry checkout.
        self.evals = self.tmp / "repo" / "evals"
        self.registry = self.tmp / "registry"
        for skill in self.SKILLS:
            self._fixture(self.evals / skill, skill)
            self._skill(skill, "body")
        for name in ("a", "b", "c", "d"):
            self._fixture(self.evals / "adrs" / name, "adrs")
        self._skill("adrs", "body")
        subprocess.run(["git", "init", "-q"], cwd=self.evals.parent, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.evals.parent, check=True)
        # An older-shape summary with no aggregate is not a validated run.
        write_json(self.tree / "results" / "flat" / "20260801T000000Z" / "with_skill"
                   / "summary.json", {"skill": "flat", "arm": "with_skill"})

    @staticmethod
    def _fixture(directory: Path, skill: str) -> None:
        directory.mkdir(parents=True)
        (directory / "fixture.yaml").write_text(f"skill: {skill}\nprompt: p\n",
                                                encoding="utf-8")

    def _skill(self, skill: str, body: str) -> None:
        path = self.registry / "plugins" / "bundle" / "skills" / skill / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {skill}\ndescription: d\n---\n{body}\n",
                        encoding="utf-8")

    def digest_of(self, skill):
        path = self.registry / "plugins" / "bundle" / "skills" / skill
        return context._file_digest(delivery._tree_files(path)[0])

    def write(self, skill, patterns, judges, *, fixture=None, tested=None,
              model="model-a", vouched=True, **kw):
        directory = self.evals / skill / (fixture or "")
        kw.setdefault("checks", False)
        run_ids = write_arm_runs(self.tree, skill, model, patterns, judges, fixture=fixture,
                                 tested=tested or self.digest_of(skill),
                                 fdig=run_eval.fixture_digest(directory), **kw)
        if vouched:
            for run_id, pattern in zip(run_ids, patterns):
                self.vouch(run_id, f"evals/{skill}" + (f"/{fixture}" if fixture else ""),
                           model, trials=len(pattern))
        return run_ids

    def ingested(self, run_id, after=3600, *, seal=True):
        """The run's first ingest: every file now under it, `after` seconds
        after its run id time, sealed (`seal`) unless `seal` is false."""
        from datetime import timedelta
        root = self.tree / "routine-results" / run_id
        self.ingest[run_id] = {
            "commit": "0" * 40, "time": iso(run_time(run_id) + timedelta(seconds=after)),
            "files": {p.relative_to(root).as_posix(): git_blob(p)
                      for p in sorted(root.rglob("*")) if p.is_file()}}
        if seal:
            self.seal(run_id)

    def seal(self, run_id):
        """A vouch.json of exactly {"mac": <64 hex>} becomes the canonical
        one the ingester stages, with the real MAC over the files its first
        ingest added, as the routine and ingester make it (round 6); any
        other vouch.json is left as a test wrote it."""
        root = self.tree / "routine-results" / run_id
        path = root / "vouch.json"
        if run_id not in self.ingest or path.is_symlink() or not path.is_file():
            return
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return
        if not (isinstance(doc, dict) and set(doc) == {"mac"} and isinstance(doc["mac"], str)
                and len(doc["mac"]) == 64):
            return
        path.write_bytes(compute_gates.canonical_vouch(
            real_mac(root, run_id, self.ingest[run_id]["files"])))
        if "vouch.json" in self.ingest[run_id]["files"]:
            self.ingest[run_id]["files"]["vouch.json"] = git_blob(path)

    def vouch(self, run, fixture_path, model, *, before=60, trials=3, arms="both",
              **fields):
        """The run's vouch.json, as the ingester stages it once its MAC
        verified, a successful fire naming it a minute before its run id,
        and its first ingest an hour after; `fields` overrides the fire's."""
        from datetime import timedelta
        write_json(self.tree / "routine-results" / run / "vouch.json",
                   {"mac": PLACEHOLDER_MAC})
        self.fires.append({"id": len(self.fires) + 1,
                           "created_at": iso(run_time(run) - timedelta(seconds=before)),
                           "conclusion": "success", "head_branch": "main",
                           "event": "workflow_dispatch",
                           "display_title": fire_title(fixture_path, model, arms=arms,
                                                       trials=trials),
                           "path": ".github/workflows/routine-eval-fire.yml",
                           "head_sha": self.fire_sha, "run_attempt": 1,
                           "run_number": len(self.fires) + 1, "run_id": run, **fields})
        self.ingested(run)

    def trust_args(self, as_of=AS_OF):
        """The trust flags. Unless `self.sentinel` is false, `--fires` also
        holds the sentinel part 2 dispatches before computing (round 8,
        R8-1): created at `as_of`, numbered after every fire this test has
        ever shown compute_gates, so a fire deleted since is a gap."""
        self.high_number = max([getattr(self, "high_number", 0)]
                               + [f["run_number"] for f in self.fires
                                  if f["path"] == compute_gates.FIRE_PATH])
        fires = list(self.fires)
        if getattr(self, "sentinel", True):
            fires.append(self.sentinel_fire(as_of, self.high_number + 1))
        write_json(self.tmp / "fires.json", fires)
        write_json(self.tmp / "ingest.json", self.ingest)
        return ["--fires", str(self.tmp / "fires.json"),
                "--ingest-times", str(self.tmp / "ingest.json"),
                "--main-sha", self.main_sha, "--main-repo", str(self.main_repo)]

    def sentinel_fire(self, as_of, number, **fields):
        """A trusted `mode=sentinel` fire created at `as_of`, numbered `number`."""
        moment = compute_gates._stamp_time(compute_gates.parse_as_of(as_of))
        return {"id": 900000 + number, "created_at": iso(moment), "conclusion": "success",
                "head_branch": "main", "event": "workflow_dispatch",
                "display_title": fire_title("", mode="sentinel", trials=1),
                "path": ".github/workflows/routine-eval-fire.yml",
                "head_sha": self.fire_sha, "run_attempt": 1, "run_number": number,
                "run_id": None, **fields}

    def run_gates(self, name, registry=True, as_of=AS_OF, trust=True):
        out = self.tmp / name
        args = ["--results-tree", str(self.tree), "--roster", str(self.roster),
                "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
                "--as-of", as_of, "--out", str(out)]
        if registry:
            args += ["--registry", f"adam-agentskills={self.registry}"]
        if trust:
            args += self.trust_args(as_of)
        with mock.patch.dict(os.environ, {"VOUCH_KEY": VOUCH_KEY}):
            self.assertEqual(compute_gates.main(args), 0)

        def refuse(value):
            raise ValueError(value)
        return out, json.loads(out.read_text(encoding="utf-8"), parse_constant=refuse)

    def edit(self, path, change, *, reingest=True):
        """Rewrite the JSON at `path`. Under a routine run with a first
        ingest, that ingest is taken to have held the new bytes (as if the
        run were written so), unless `reingest` is false: an edit in place
        after the ingest."""
        doc = json.loads(path.read_text(encoding="utf-8"))
        change(doc)
        path.write_text(json.dumps(doc), encoding="utf-8")
        parts = path.relative_to(self.tree).parts if path.is_relative_to(self.tree) else ()
        if reingest and parts[:1] == ("routine-results",) and parts[1] in self.ingest:
            root = self.tree / "routine-results" / parts[1]
            self.ingest[parts[1]]["files"][path.relative_to(root).as_posix()] = git_blob(path)
            self.seal(parts[1])

    def test_output_is_deterministic(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        first, _ = self.run_gates("a.json")
        second, _ = self.run_gates("b.json")
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_verdicts_links_and_skips(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        # One fixture per routine run id, as the fire workflow makes them.
        self.write("gain", FLAT[:5], [8.5, 8.7] * 3, without_judges=[6.0, 6.2] * 3,
                   model_tag="b")
        self.write("unasked", FLAT[:10], FLAT_JUDGE, requested=False, model_tag="c")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        self.assertEqual(doc["skills"]["gain"]["verdict"], "keep")
        self.assertEqual(doc["skills"]["unasked"]["verdict"], "insufficient")
        self.assertEqual(doc["skipped"], {"no aggregate block": 1,
                                          "no requested arm model": 20})
        self.assertEqual((doc["roster_models"], doc["as_of"]), (["model-a"], AS_OF))
        entry = doc["skills"]["flat"]["cells"][0]["runs"]["with"][0]
        self.assertEqual(entry["run"]["billing"], "api")
        self.assertTrue((self.tree / entry["report"]["path"]).is_file())
        self.assertEqual(doc["retirement_mode"], "proposal")
        self.assertNotIn("previous", doc)

    def test_five_runs_are_pending_and_ten_retire(self):
        self.write("flat", FLAT[:5], FLAT_JUDGE)
        _, doc = self.run_gates("1.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire-pending")
        self.write("flat", FLAT[5:10], FLAT_JUDGE[5:10], start=5)
        _, doc = self.run_gates("2.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def test_as_of_is_required(self):
        with self.assertRaises(SystemExit):
            compute_gates.main(["--results-tree", str(self.tree), "--roster",
                                str(self.roster), "--policy", str(POLICY_FILE),
                                "--out", str(self.tmp / "x.json")])
        for bad in ("yesterday", "2026-10-01"):
            with self.subTest(bad=bad):
                self.assertEqual(compute_gates.main([
                    "--results-tree", str(self.tree), "--roster", str(self.roster),
                    "--policy", str(POLICY_FILE), "--as-of", bad,
                    "--out", str(self.tmp / "x.json")]), 2)

    def test_a_run_first_ingested_after_as_of_has_not_landed(self):
        # Round 8, R8-2 (round 7 refused such an --as-of, so a squatted
        # future ingest time refused every evaluation; test_r8_probe's
        # test_future_ingest_time_crashes). Now a run first ingested after
        # --as-of is dropped and unlanded, so its fire blocks by the grace
        # rule; a stale --as-of can only stall, never retire early.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        newest = max(entry["time"] for entry in self.ingest.values())
        just_before = compute_gates._as_stamp(compute_gates._iso_time(newest)
                                              - __import__("datetime").timedelta(seconds=1))
        # Early, too few runs have landed to judge (and the rest are young
        # unlanded fires); a second before the last ingest, that one run's
        # fire holds the cell at pending.
        for as_of, verdict, count in ((stamp(4), "insufficient", 6),
                                      ("2026-10-01T04:00:00+00:00", "insufficient", 6),
                                      (just_before, "retire-pending", 1)):
            with self.subTest(as_of=as_of):
                _, doc = self.run_gates(f"{len(as_of)}.json", as_of=as_of)
                self.assertEqual(len(doc["unlanded"]), count)
                self.assertTrue(set(u["run_id"] for u in doc["unlanded"])
                                <= set(self.ingest))
                self.assertFalse(any(u["overdue"] for u in doc["unlanded"]))
                self.assertEqual(doc["skills"]["flat"]["verdict"], verdict)
        # At the newest ingest exactly, all ten are read.
        _, doc = self.run_gates("a.json", as_of=newest)
        self.assertEqual((doc["unlanded"], doc["skills"]["flat"]["verdict"]), ([], "retire"))
        # A squatted run id ingested in 2099 refuses nothing and counts for
        # nothing: no fire names it, and its MAC was never made. It names no
        # cell, so it blocks none, and waits for a waiver (round 9, R9-3).
        self.ingest["20991231T000000Z-abcdef"] = {
            "commit": "1" * 40, "time": "2099-12-31T00:00:00+00:00",
            "files": {"vouch.json": "2" * 40}}
        _, doc = self.run_gates("squat.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        self.assertEqual(doc["needs_waiver"], [{
            "skill": None, "fixture": None, "model": None,
            "run_id": "20991231T000000Z-abcdef", "overdue": True,
            "why": "its first ingest has no valid vouch.json"}])

    def test_deleting_the_newest_fires_is_a_gap_below_the_sentinel(self):
        # Round 8's reproducer (test_r8_probe's
        # test_tail_fire_deleted_and_ingest_blocked): blocking the ingest of
        # the three newest (gain) runs and deleting their fires left no gap,
        # so keep became retire. The sentinel part 2 dispatches after them
        # is numbered above them: they are a gap now.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        gain = self.write("flat", FLAT[:3], [9.6, 9.4, 9.6], without_judges=[5.0, 5.2, 5.0],
                          model_tag="b", start=10)
        _, base = self.run_gates("0.json")
        self.assertEqual((base["skills"]["flat"]["verdict"], base["sentinel_run_number"]),
                         ("keep", 14))
        numbers = [f["run_number"] for f in self.fires if f["run_id"] in gain]
        for run_id in gain:
            shutil.rmtree(self.tree / "routine-results" / run_id)
            del self.ingest[run_id]
        self.fires = [f for f in self.fires if f["run_id"] not in gain]
        _, doc = self.run_gates("1.json")
        self.assertEqual(doc["missing_fire_numbers"], numbers)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertIn("missing from the sequence",
                      doc["skills"]["flat"]["cells"][0]["reason"])
        # The sequence ends at the sentinel: a fire numbered after it (one
        # dispatched since, its predecessors not listed yet) is no gap.
        self.sentinel = False
        self.fires += [{**self.fires[0], "id": 500 + n, "run_number": n,
                        "conclusion": "cancelled", "run_id": None} for n in numbers]
        self.fires += [self.sentinel_fire(AS_OF, 14),
                       {**self.fires[0], "id": 518, "run_number": 18,
                        "conclusion": "failure", "run_id": None}]
        _, doc = self.run_gates("2.json")
        self.assertEqual((doc["sentinel_run_number"], doc["missing_fire_numbers"]), (14, []))

    def test_no_trusted_sentinel_at_or_after_as_of_blocks_no_benefit(self):
        # Round 8, R8-1: without a sentinel the sequence has no upper end.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, doc = self.run_gates("0.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        self.sentinel = False
        later = compute_gates._stamp_time(AS_OF)
        cases = {
            "none": [],
            "before as-of": [self.sentinel_fire("20261230T235959Z", 11)],
            "a failed one": [self.sentinel_fire(AS_OF, 11, conclusion="failure")],
            "a second attempt": [self.sentinel_fire(AS_OF, 11, run_attempt=2)],
            "another branch": [self.sentinel_fire(AS_OF, 11, head_branch="x")],
            "another workflow": [self.sentinel_fire(AS_OF, 11, path=".github/workflows/x.yml")],
            "not dispatched": [self.sentinel_fire(AS_OF, 11, event="push")],
            "not on main": [self.sentinel_fire(AS_OF, 11, head_sha="f" * 40)],
            "naming a run": [self.sentinel_fire(AS_OF, 11, run_id=f"{stamp(40)}-aaaaaa")],
            "with a fixture": [self.sentinel_fire(AS_OF, 11, display_title=fire_title(
                "evals/flat", mode="sentinel", trials=1))],
            "with a model": [self.sentinel_fire(AS_OF, 11, display_title=fire_title(
                "", "model-a", mode="sentinel", trials=1))],
            "an eval title": [self.sentinel_fire(AS_OF, 11, display_title=fire_title(
                "", mode="eval", trials=1))],
        }
        base = list(self.fires)
        for name, extra in cases.items():
            with self.subTest(case=name):
                self.fires = base + extra
                _, doc = self.run_gates(f"{name}.json")
                self.assertIsNone(doc["sentinel_run_number"])
                self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
                self.assertIn("sentinel", doc["skills"]["flat"]["cells"][0]["reason"])
        # A later one is fine; the lowest at or after as-of ends the
        # sequence, so a gap above it is not read.
        self.fires = base + [self.sentinel_fire(AS_OF, 12), self.sentinel_fire(AS_OF, 11)]
        self.fires[-2]["created_at"] = iso(later.replace(year=2027))
        _, doc = self.run_gates("ok.json")
        self.assertEqual((doc["sentinel_run_number"], doc["missing_fire_numbers"],
                          doc["skills"]["flat"]["verdict"]), (11, [], "retire"))
        # A keep cell is not blocked: only no-benefit is refused.
        self.fires = list(base)
        self.write("flat", FLAT[:3], [9.6, 9.4, 9.6], without_judges=[5.0, 5.2, 5.0],
                   model_tag="b", start=10)
        _, keep = self.run_gates("keep.json")
        self.assertEqual(keep["skills"]["flat"]["verdict"], "keep")

    def test_a_vouched_run_as_of_drops_is_unlanded_not_gone(self):
        # Round 7's reproducer (test_A): a vouched run whose fire came after
        # --as-of (or whose arms are stamped after it) was dropped as
        # "after as-of" yet counted as landed, so a gain run vanished with
        # nothing blocking. It is unlanded now: pending by the grace rule.
        from datetime import timedelta
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        run_id = f"{stamp(30)}-e00000"
        self.write("flat", FLAT[:1], [9.6], without_judges=[5.0], start=30, model_tag="e",
                   vouched=False)
        self.vouch(run_id, "evals/flat", "model-a", before=-60, trials=3)
        self.ingested(run_id, after=30)
        as_of = compute_gates._as_stamp(run_time(run_id) + timedelta(seconds=45))
        _, doc = self.run_gates("a.json", as_of=as_of)
        self.assertEqual(doc["skipped"]["after as-of"], 2)
        self.assertEqual([(u["run_id"], u["overdue"]) for u in doc["unlanded"]],
                         [(run_id, False)])
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire-pending")
        self.assertEqual(doc["needs_waiver"], [])

    def test_a_future_dated_run_does_not_choose_the_context(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        # Ingested ten minutes after its run id, its arms stamped 90 minutes
        # after it: at an --as-of between the two, its arms are in the future.
        future = "20261002T073000Z"
        run = self.tree / "routine-results" / f"{stamp(30)}-f00000" / "flat" / future
        shutil.copytree(self.tree / "routine-results" / f"{stamp(0)}-a00000" / "flat"
                        / stamp(0), run)
        self.vouch(f"{stamp(30)}-f00000", "evals/flat", "model-a")
        self.ingested(f"{stamp(30)}-f00000", after=600)
        for role in ("with", "without"):
            self.edit(run / f"{role}_skill" / "summary.json",
                      lambda d: d["arm_context"].update(skills_digest="future"))
            for k in (1, 2, 3):
                self.edit(run / f"{role}_skill" / f"trial-{k}" / "summary.json",
                          lambda d, c={"with": 0.75, "without": 0.85}[role]:
                          d["agent"].update(cost_usd=c))
        _, doc = self.run_gates("a.json", as_of="20261002T062000Z")
        # Not a duplicate (its bytes are its own), so only as-of keeps it out,
        # and its pool and context are the ten runs'. Dropped, it has not
        # landed (round 7, R7-2): pending by the grace rule, never retire.
        self.assertEqual((doc["skipped"].get("after as-of"),
                          doc["skipped"].get("duplicate arm run")), (2, None))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire-pending")
        # Read, it is one run against ten: the context with the most runs
        # is chosen, so the verdict stands (round 4, B2).
        _, doc = self.run_gates("b.json", as_of=future)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def copy_run(self, source_id, run_id, timestamp=None, *, reserialize=False):
        """`routine-results/<source_id>` again as `<run_id>`, its one
        skill's timestamp directory renamed to `timestamp` when given."""
        source = self.tree / "routine-results" / source_id
        target = self.tree / "routine-results" / run_id
        shutil.copytree(source, target)
        if timestamp is not None:
            (stamp_dir,) = (target / "flat").iterdir()
            stamp_dir.rename(stamp_dir.with_name(timestamp))
        if reserialize:
            for path in target.rglob("summary.json"):
                path.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8")),
                                           indent=1), encoding="utf-8")
        return target

    def test_a_copied_run_without_a_fire_counts_for_nothing(self):
        # Every routine run copied, re-serialized, under a new run id of
        # the same time: no fire vouches for it, so it adds no run.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, before = self.run_gates("a.json")
        for run in sorted((self.tree / "routine-results").iterdir()):
            copy = run.name.replace("-a0000", "-e0000")
            self.copy_run(run.name, copy, reserialize=True)
            self.ingested(copy)
        _, after = self.run_gates("b.json")
        self.assertEqual(after["skills"]["flat"]["runs_used"],
                         before["skills"]["flat"]["runs_used"])
        self.assertEqual(after["skipped"]["no trusted fire names the routine run"], 20)
        self.assertNotIn("duplicate arm run", after["skipped"])

    def test_a_vouched_copy_is_counted_once(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, before = self.run_gates("a.json")
        for run in sorted((self.tree / "routine-results").iterdir()):
            copy = run.name.replace("-a0000", "-e0000")
            self.copy_run(run.name, copy, reserialize=True)
            self.vouch(copy, "evals/flat", "model-a")
        _, after = self.run_gates("b.json")
        self.assertEqual(after["skills"]["flat"]["runs_used"],
                         before["skills"]["flat"]["runs_used"])
        self.assertEqual(after["skipped"]["duplicate arm run"], 20)

    def test_each_duplicate_key_alone_drops_a_copy(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        source_id = f"{stamp(0)}-a00000"

        def summaries(run):
            return [run / f"{role}_skill" / "summary.json" for role in ("with", "without")]

        def trials(run):
            return [run / f"{role}_skill" / f"trial-{k}" / "summary.json"
                    for role in ("with", "without") for k in (1, 2, 3)]

        for name, timestamp, edited in (
                ("same skill, fixture, model, role and timestamp", stamp(0),
                 lambda run: summaries(run) + trials(run)),
                ("same arm summary bytes", stamp(40), trials),
                ("same trial summary bytes", stamp(41), summaries)):
            with self.subTest(name=name):
                run_id = f"{timestamp}-e00000"
                copy = self.copy_run(source_id, run_id, timestamp)
                self.vouch(run_id, "evals/flat", "model-a")
                for path in edited(copy / "flat" / timestamp):
                    self.edit(path, lambda d: d.update(copied=True))
                _, doc = self.run_gates("a.json")
                self.assertEqual(doc["skipped"]["duplicate arm run"], 2)
                self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 20)
                shutil.rmtree(copy)
                self.fires.pop()
                del self.ingest[run_id]

    def test_a_skill_whose_name_starts_with_guidance_is_evaluated(self):
        self.write("guidancebot", FLAT[:10], FLAT_JUDGE)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["guidancebot"]["raw_verdict"], "retire")

    def test_without_a_registry_every_cell_is_insufficient(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, doc = self.run_gates("a.json", registry=False)
        verdict = doc["skills"]["flat"]
        self.assertEqual(verdict["verdict"], "insufficient")
        self.assertIn("tested_digest", verdict["cells"][0]["reason"])

    def test_runs_of_other_skill_content_do_not_count(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        self._skill("flat", "changed on main")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(doc["skills"]["flat"]["cells"][0]["runs"]["with"], [])

    def test_cells_come_from_the_fixtures_on_main(self):
        self.write("adrs", FLAT[:10], FLAT_JUDGE, fixture="a")
        _, doc = self.run_gates("a.json")
        verdict = doc["skills"]["adrs"]
        self.assertEqual(verdict["verdict"], "insufficient")
        self.assertEqual([(c["fixture"], c["class"]) for c in verdict["cells"]],
                         [("a", "no-benefit"), ("b", "missing"), ("c", "missing"),
                          ("d", "missing")])

    def test_crafted_summaries_are_skipped_never_a_crash(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        runs = sorted((self.tree / "routine-results").iterdir())
        trial_path = runs[0] / "flat" / stamp(0) / "with_skill" / "trial-1" / "summary.json"
        self.edit(trial_path, lambda d: d.update(objective_checks=5))
        nan_path = runs[1] / "flat" / stamp(1) / "with_skill" / "trial-1" / "summary.json"
        nan_path.write_text(nan_path.read_text(encoding="utf-8").replace(
            '"cost_usd": 0.25', '"cost_usd": NaN'), encoding="utf-8")
        self.ingested(runs[1].name)  # as if the run were written so
        for k in (1, 2, 3):
            self.edit(runs[2] / "flat" / stamp(2) / "without_skill" / f"trial-{k}"
                      / "summary.json", lambda d: d["agent"].update(cost_usd=1e308))
        self.edit(runs[3] / "flat" / stamp(3) / "with_skill" / "summary.json",
                  lambda d: d.update(fixture_digest=["not", "a", "digest"]))
        self.edit(runs[4] / "flat" / stamp(4) / "with_skill" / "summary.json",
                  lambda d: d.update(role=["with"]))
        _, doc = self.run_gates("a.json")
        # A run with one arm refused is not the both-arm run its fire asked
        # for, so its other arm goes too.
        self.assertEqual(doc["skipped"], {"malformed trial summary": 1,
                                          "unreadable trial summary": 1,
                                          "malformed arm summary": 2,
                                          "no aggregate block": 1,
                                          "no fire vouches for the routine run: its arms "
                                          "or trials are not its fire's": 4})
        self.assertIsNone(doc["skills"]["flat"]["cells"][0]["cost_usd"])
        # Round 6, R6-2: the four refused runs' trusted fires have no
        # verified run, so the cell may not show no benefit.
        cell = doc["skills"]["flat"]["cells"][0]
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(len(cell["unlanded_fires"]), 4)
        self.assertIn("no verified ingested run", cell["reason"])

    def test_the_verdict_reads_the_roster_it_is_given(self):
        # The roster follows current use (2026-10-25): a superseded model
        # leaves it at once. Its runs, a clear gain here, then count toward
        # nothing, and no evidence is asked of it.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        self.write("flat", FLAT[:5], [8.5, 8.7] * 3, without_judges=[6.0, 6.2] * 3,
                   model="model-old", model_tag="c", start=50)
        for arms, verdict in ((["model-a"], "retire"),
                              (["model-old", "model-a"], "keep"),
                              (["model-a", "model-new"], "insufficient")):
            with self.subTest(arms=arms):
                self.roster.write_text("arms:\n" + "".join(f"  - id: {m}\n" for m in arms),
                                       encoding="utf-8")
                _, doc = self.run_gates("a.json")
                flat = doc["skills"]["flat"]
                self.assertEqual((doc["roster_models"], flat["verdict"]),
                                 (sorted(arms), verdict))
                self.assertEqual(sorted(c["model"] for c in flat["cells"]), sorted(arms))
                if arms == ["model-a"]:
                    self.assertFalse([k for k in flat["runs_used"] if "-c0000" in k])

    def test_runs_of_two_models_at_one_timestamp_both_count(self):
        # One routine run may stamp every model's arms with one timestamp
        # (`--timestamp`): the same (skill, fixture, role, timestamp) on
        # another model is another run, not a copy.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        self.write("flat", FLAT[:10], FLAT_JUDGE, model="model-b", model_tag="b")
        self.roster.write_text("arms:\n  - id: model-a\n  - id: model-b\n",
                               encoding="utf-8")
        _, doc = self.run_gates("a.json")
        self.assertNotIn("duplicate arm run", doc["skipped"])
        self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 40)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    # -- round 3: an empty roster, and evidence that is vouched for --------

    def test_an_empty_or_malformed_roster_exits_2(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        for text in ("arms: []\n", "judge:\n  id: model-j\n",
                     "arms:\n  - model-a\n", "arms:\n  - id: model-a\n  - model-b\n"):
            with self.subTest(roster=text):
                self.roster.write_text(text, encoding="utf-8")
                out = self.tmp / "x.json"
                self.assertEqual(compute_gates.main([
                    "--results-tree", str(self.tree), "--roster", str(self.roster),
                    "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
                    "--as-of", AS_OF, "--out", str(out)]), 2)
                self.assertFalse(out.exists())

    def test_backdated_forged_runs_are_not_vouched_for(self):
        # Round 3's reproducer (p3.py): six honest runs per arm, then twenty
        # flat ones per arm stamped before them, under self-chosen run ids
        # and with no fire. They were the first looks and retired the cell.
        rng = random.Random(1)
        honest = {role: [base + rng.uniform(-0.6, 0.6) for _ in range(6)]
                  for role, base in (("with", 7.4), ("without", 7.1))}
        self.write("flat", FLAT[:6], honest["with"], without_judges=honest["without"],
                   start=200)
        _, alone = self.run_gates("a.json")
        self.write("flat", FLAT[:20], FLAT_JUDGE, model_tag="f", vouched=False)
        for run_id in [r.name for r in (self.tree / "routine-results").iterdir()
                       if "-f0000" in r.name]:
            # Even with a vouch.json of the ingester's shape: no fire.
            write_json(self.tree / "routine-results" / run_id / "vouch.json",
                       {"mac": PLACEHOLDER_MAC})
            self.ingested(run_id, after=0)
        _, forged = self.run_gates("b.json")
        self.assertEqual(forged["skipped"]["no trusted fire names the routine run"], 40)
        self.assertEqual(forged["skills"]["flat"]["cells"][0]["class"],
                         alone["skills"]["flat"]["cells"][0]["class"])
        self.assertEqual(forged["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(forged["skills"]["flat"]["runs_used"],
                         alone["skills"]["flat"]["runs_used"])

    def test_a_fire_vouches_for_one_run_only(self):
        first, second = (f"{stamp(0)}-a00000", f"{stamp(0)[:-5]}1000Z-a00001")
        self.write("flat", FLAT[:1], FLAT_JUDGE, vouched=False)
        self.copy_run(first, second, reserialize=True)
        self.vouch(first, "evals/flat", "model-a")
        # The copy carries the first run's vouch.json, and its fire too.
        shutil.copy(self.tree / "routine-results" / first / "vouch.json",
                    self.tree / "routine-results" / second / "vouch.json")
        self.ingested(second, after=0)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"]["no trusted fire names the routine run"], 2)
        used = doc["skills"]["flat"]["runs_used"]
        self.assertEqual({k.split("/")[1] for k in used}, {first})

    def test_what_a_fire_must_be_to_vouch(self):
        self.roster.write_text("arms:\n  - id: model-a\n  - id: model-b\n",
                               encoding="utf-8")
        vouch_file = lambda run_id: self.tree / "routine-results" / run_id / "vouch.json"

        def no_vouch(run_id):
            vouch_file(run_id).unlink()
            self.ingested(run_id)

        def late_vouch(run_id):
            # The first ingest held the results only; vouch.json came later.
            del self.ingest[run_id]["files"]["vouch.json"]

        def edited_vouch(run_id):
            # Edited in place since its first ingest.
            write_json(vouch_file(run_id), {"mac": "0" * 64})

        def old_vouch(run_id):
            # Round 4's nonce file, from before the keyed vouch.
            write_json(vouch_file(run_id), {"nonce": "0" * 64})
            self.ingested(run_id)

        def vouch_shape(run_id):
            write_json(vouch_file(run_id), {"mac": PLACEHOLDER_MAC, "x": 1})
            self.ingested(run_id)

        def symlinked_vouch(run_id):
            target = self.tmp / "elsewhere.json"
            write_json(target, {"mac": PLACEHOLDER_MAC})
            vouch_file(run_id).unlink()
            os.symlink(target, vouch_file(run_id))

        def without_arm_only(run_id):
            shutil.rmtree(next((self.tree / "routine-results" / run_id / "flat")
                               .iterdir()) / "with_skill")
            self.ingested(run_id)
        title = lambda **kw: {"display_title": fire_title("evals/flat", "model-a", **kw)}
        cases = {
            "as written": ({}, True, None),
            "a failed run": ({"conclusion": "failure"}, False, None),
            "an unfinished run": ({"conclusion": None}, False, None),
            "another branch": ({"head_branch": "feature"}, False, None),
            "another event": ({"event": "push"}, False, None),
            "another workflow": ({"path": ".github/workflows/ci.yml"}, False, None),
            "a commit not on main": ({"head_sha": "1" * 40}, False, None),
            "main itself": ({"head_sha": "MAIN"}, True, None),
            "scaffold mode": (title(mode="scaffold"), False, None),
            "another fixture": ({"display_title": fire_title("evals/gain", "model-a")},
                                False, None),
            "an uncommitted fixture": ({"display_title": fire_title("evals/nope",
                                                                     "model-a")}, False, None),
            "another model": ({"display_title": fire_title("evals/flat", "model-b")},
                              False, None),
            # Round 7, R7-3: a title must name its model, even the first arm.
            "no model, the roster's first arm": ({"display_title": fire_title(
                "evals/flat")}, False, None),
            "trailing text": ({"display_title": fire_title("evals/flat", "model-a") + " x"},
                              False, None),
            "the old title": ({"display_title": "Fire eval routine"}, False, None),
            "a title without arms and trials": (
                {"display_title": "Fire eval routine: mode=eval fixture=evals/flat "
                                  "model=model-a"}, False, None),
            "other trials": (title(trials=2), False, None),
            "one arm fired, both ran": (title(arms="with"), False, None),
            "both fired, one ran": ({}, False, without_arm_only),
            "one arm fired, one ran": (title(arms="without"), True, without_arm_only),
            "another run id": ({"run_id": "20261001T000000Z-ffffff"}, False, None),
            "no run id": ({"run_id": None}, False, None),
            "a second attempt": ({"run_attempt": 2}, False, None),
            "no vouch.json": ({}, False, no_vouch),
            "a vouch.json added after the first ingest": ({}, False, late_vouch),
            "a vouch.json edited since": ({}, False, edited_vouch),
            "round 4's nonce vouch.json": ({}, False, old_vouch),
            "a vouch.json of another shape": ({}, False, vouch_shape),
            "a symlinked vouch.json": ({}, False, symlinked_vouch),
            # The fire's own time no longer matters: the run id binds it.
            "created after the run id": ({"before": -60}, True, None),
            "created a day before": ({"before": 86400}, True, None),
        }
        for name, (fields, counts, hook) in cases.items():
            with self.subTest(case=name):
                shutil.rmtree(self.tree / "routine-results", ignore_errors=True)
                self.fires, self.ingest = [], {}
                (run_id,) = self.write("flat", FLAT[:1], FLAT_JUDGE, vouched=False)
                fields = dict(fields)
                if fields.get("head_sha") == "MAIN":
                    fields["head_sha"] = self.main_sha
                self.vouch(run_id, "evals/flat", "model-a",
                           before=fields.pop("before", 60), **fields)
                if hook:
                    hook(run_id)
                _, doc = self.run_gates("a.json")
                # Vouched: nothing skipped beyond setUp's old summary. A
                # lone arm is vouched but forms no pair (B6), so runs_used
                # is not the test.
                vouched = set(doc["skipped"]) <= {"no aggregate block"}
                self.assertEqual(vouched, counts, doc["skipped"])
        # No model is never accepted, whatever the roster's first arm is.
        shutil.rmtree(self.tree / "routine-results")
        self.fires, self.ingest = [], {}
        self.write("flat", FLAT[:1], FLAT_JUDGE)
        self.fires[0]["display_title"] = fire_title("evals/flat")
        self.roster.write_text("arms:\n  - id: model-b\n  - id: model-a\n",
                               encoding="utf-8")
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skills"]["flat"]["runs_used"], [])

    def test_what_a_routine_run_must_be_to_count(self):
        def setup(run_ids=None):
            shutil.rmtree(self.tree / "routine-results", ignore_errors=True)
            self.fires, self.ingest = [], {}
            (run_id,) = self.write("flat", FLAT[:1], FLAT_JUDGE)
            return run_id

        def skipped():
            _, doc = self.run_gates("a.json")
            self.assertEqual(doc["skills"]["flat"]["runs_used"], [])
            return doc["skipped"]

        run_id = setup()
        self.ingested(run_id, after=48 * 3600 + 1)
        self.assertEqual(skipped()["routine run id time is not within the 48 hours "
                                   "before its ingest"], 2)
        self.ingested(run_id, after=-1)
        self.assertIn("routine run id time is not within the 48 hours before its ingest",
                      skipped())
        del self.ingest[run_id]
        self.assertEqual(skipped()["routine run has no ingest time"], 2)
        # A run id that is digits but no time.
        run_id = setup()
        bad = "20261399T000000Z-a00000"
        (self.tree / "routine-results" / run_id).rename(self.tree / "routine-results" / bad)
        self.ingest[bad] = self.ingest.pop(run_id)
        self.assertEqual(skipped()["routine run id is not a real UTC time"], 2)
        # An arm timestamp over two hours from the run id.
        run_id = setup()
        far = f"{stamp(3)}"
        stamp_dir = self.tree / "routine-results" / run_id / "flat" / stamp(0)
        stamp_dir.rename(stamp_dir.with_name(far))
        self.ingested(run_id)
        self.assertEqual(skipped()["routine arm timestamp is not within 2 hours of its "
                                   "run id"], 2)
        # Two fixtures, or two runs of one arm, in one run id.
        run_id = setup()
        shutil.copytree(self.tree / "routine-results" / run_id / "flat",
                        self.tree / "routine-results" / run_id / "gain")
        for path in (self.tree / "routine-results" / run_id / "gain").rglob("summary.json"):
            self.edit(path, lambda d: d.update(skill="gain"))
        self.ingested(run_id)
        self.assertEqual(skipped()["routine run holds more than one fixture or model"], 4)
        run_id = setup()
        source = self.tree / "routine-results" / run_id / "flat" / stamp(0)
        shutil.copytree(source, source.with_name(stamp(0)[:-3] + "01Z"))
        self.ingested(run_id)
        self.assertEqual(skipped()["more than one arm run per run id, model and role"], 4)

    def test_without_every_trust_input_only_results_count(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        trust = dict(zip(*[iter(self.trust_args())] * 2))
        for given in itertools.chain.from_iterable(
                itertools.combinations(("--fires", "--ingest-times", "--main-sha"), n)
                for n in range(3)):
            with self.subTest(given=given):
                out = self.tmp / "x.json"
                self.assertEqual(compute_gates.main([
                    "--results-tree", str(self.tree), "--roster", str(self.roster),
                    "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
                    "--registry", f"adam-agentskills={self.registry}", "--as-of", AS_OF,
                    "--main-repo", str(self.main_repo), "--out", str(out),
                    *[a for flag in given for a in (flag, trust[flag])]]), 0)
                doc = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(doc["skipped"][compute_gates.NO_TRUST], 20)
                self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        # The same runs under results/ count without any of them, but no
        # fire vouches for them, so they can keep a skill and never retire
        # one (round 4, B4a).
        for run in sorted((self.tree / "routine-results").iterdir()):
            (stamp_dir,) = (run / "flat").iterdir()
            target = self.tree / "results" / "flat" / stamp_dir.name
            target.parent.mkdir(parents=True, exist_ok=True)
            stamp_dir.rename(target)
            run.rename(self.tmp / ("moved-" + run.name))
        _, doc = self.run_gates("b.json", trust=False)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 20)
        self.assertEqual(doc["skills"]["flat"]["cells"][0]["class"], "insufficient")
        self.assertIn("results/", doc["skills"]["flat"]["cells"][0]["reason"])
        self.write("gain", FLAT[:5], [8.5, 8.7] * 3, without_judges=[6.0, 6.2] * 3,
                   model_tag="b", vouched=False)
        for run in sorted((self.tree / "routine-results").iterdir()):
            (stamp_dir,) = (run / "gain").iterdir()
            target = self.tree / "results" / "gain" / stamp_dir.name
            target.parent.mkdir(parents=True, exist_ok=True)
            stamp_dir.rename(target)
        _, doc = self.run_gates("c.json", trust=False)
        self.assertEqual(doc["skills"]["gain"]["verdict"], "keep")

    def test_looks_follow_the_fire_not_the_run_stamp(self):
        # Run A is stamped after run B but its fire came first: A is first.
        a, b = f"{stamp(1)}-a00001", "20261001T005000Z-b00000"
        self.write("flat", FLAT[:1], FLAT_JUDGE, vouched=False, start=1)
        self.copy_run(a, b, reserialize=True)
        (stamp_dir,) = (self.tree / "routine-results" / b / "flat").iterdir()
        stamp_dir.rename(stamp_dir.with_name(b[:16]))
        self.vouch(a, "evals/flat", "model-a", before=3600)
        self.vouch(b, "evals/flat", "model-a", before=10)
        self.trust_args()
        tree_index = compute_gates.build_index(
            self.tree, self.evals, AS_OF,
            {"ingest": compute_gates.load_ingest_times(self.tmp / "ingest.json"),
             "fires": compute_gates.load_fires(self.tmp / "fires.json"),
             "first_arm": "model-a", "committed": compute_gates.committed_fixtures(self.evals),
             "main_sha": self.main_sha, "main_repo": self.main_repo,
             "vouch_key": VOUCH_KEY.encode()})
        runs = sorted(tree_index["runs"], key=gates._order)
        self.assertEqual([r["run_id"] for r in runs if r["role"] == "with"], [a, b])
        self.assertEqual(runs[0]["order_time"], "20261001T000000Z")
        self.assertLess(b[:16], a[:16])

    def test_the_trust_files_are_parsed_strictly(self):
        self.write("flat", FLAT[:1], FLAT_JUDGE)
        good = dict(self.fires[0])
        other = {**good, "id": 2, "run_id": "20261001T010000Z-ffffff"}
        bad_fires = [[{**good, "extra": 1}], [{k: v for k, v in good.items() if k != "event"}],
                     [{**good, "id": True}], [good, good],
                     [{**good, "created_at": "2026-10-01T00:00:00"}], {"id": 1},
                     [{**good, "display_title": 5}],
                     *[[{k: v for k, v in good.items() if k != key}]
                       for key in ("path", "head_sha", "run_id", "run_attempt",
                                   "run_number")],
                     # Round 7, R7-1: a run number is a positive integer.
                     [{**good, "run_number": 0}], [{**good, "run_number": True}],
                     [{**good, "run_number": "1"}],
                     [{**good, "nonce_sha256": "a" * 64}],
                     [{**good, "run_id": "not-a-run-id"}], [{**good, "run_id": 5}],
                     [{**good, "run_attempt": 0}], [{**good, "run_attempt": True}],
                     [{**good, "run_attempt": "1"}],
                     [{**good, "head_sha": "a" * 39}], [{**good, "head_sha": None}],
                     [{**good, "path": None}]]
        (run_id, entry), = self.ingest.items()
        bad_ingest = [{"not-a-run-id": entry}, {run_id: "2026-10-01T00:00:00Z"},
                      {run_id: {**entry, "time": "yesterday"}},
                      {run_id: {**entry, "commit": "x"}},
                      {run_id: {**entry, "files": "vouch.json"}},
                      {run_id: {**entry, "files": ["vouch.json"]}},
                      {run_id: {**entry, "files": {"vouch.json": "x" * 40}}},
                      {run_id: {**entry, "files": {"vouch.json": 5}}},
                      {run_id: {**entry, "files": {"": "a" * 40}}},
                      {run_id: {k: v for k, v in entry.items() if k != "files"}},
                      {run_id: {**entry, "extra": 1}}, ["x"]]
        # The good files parse: every refusal below is the bad case's own.
        write_json(self.tmp / "fires.json", [good, other])
        write_json(self.tmp / "ingest.json", self.ingest)
        self.assertEqual(compute_gates.main([
            "--results-tree", str(self.tree), "--roster", str(self.roster),
            "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
            "--as-of", AS_OF, "--out", str(self.tmp / "x.json"), "--main-sha", self.main_sha, "--main-repo", str(self.main_repo),
            "--fires", str(self.tmp / "fires.json"),
            "--ingest-times", str(self.tmp / "ingest.json")]), 0)
        for bad in ("abc", "A" * 40, "a" * 39):
            with self.subTest(main_sha=bad):
                self.assertEqual(compute_gates.main([
                    "--results-tree", str(self.tree), "--roster", str(self.roster),
                    "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
                    "--as-of", AS_OF, "--out", str(self.tmp / "x.json"),
                    "--main-sha", bad]), 2)
        for kind, cases in (("fires", bad_fires), ("ingest", bad_ingest)):
            for case in cases:
                with self.subTest(kind=kind, case=case):
                    write_json(self.tmp / "fires.json", case if kind == "fires" else self.fires)
                    write_json(self.tmp / "ingest.json",
                               case if kind == "ingest" else self.ingest)
                    self.assertEqual(compute_gates.main([
                        "--results-tree", str(self.tree), "--roster", str(self.roster),
                        "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
                        "--as-of", AS_OF, "--out", str(self.tmp / "x.json"),
                        "--fires", str(self.tmp / "fires.json"),
                        "--ingest-times", str(self.tmp / "ingest.json"),
                        "--main-sha", self.main_sha, "--main-repo", str(self.main_repo)]), 2)

    def test_trial_files_must_be_one_to_n_and_agree_with_the_arm_summary(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        runs = sorted((self.tree / "routine-results").iterdir())
        arm = runs[0] / "flat" / stamp(0) / "with_skill"
        (arm / "trial-3").rename(arm / "trial-4")
        self.edit(runs[1] / "flat" / stamp(1) / "with_skill" / "summary.json",
                  lambda d: d.update(n=2))
        self.edit(runs[2] / "flat" / stamp(2) / "with_skill" / "summary.json",
                  lambda d: d.update(errors=1))
        self.edit(runs[3] / "flat" / stamp(3) / "with_skill" / "summary.json",
                  lambda d: d.update(scored=1))
        self.edit(runs[4] / "flat" / stamp(4) / "with_skill" / "summary.json",
                  lambda d: d.pop("n"))
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"]["trial files are not numbered 1 to n"], 1)
        self.assertEqual(doc["skipped"]["arm summary's n or errors disagree with its "
                                        "trial files"], 4)

    def test_ingest_files_come_from_the_first_commit_adding_each_run(self):
        import routine_ingest_times
        repo = self.tmp / "results-checkout"
        repo.mkdir()

        def git(*args, date=None):
            env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
            if date:
                env.update(GIT_COMMITTER_DATE=date, GIT_AUTHOR_DATE=date)
            subprocess.run(["git", *INGEST_IDENTITY, *args], cwd=repo, check=True,
                           capture_output=True, env=env)
        git("init", "-q")
        one, two = "20261001T000000Z-aaaaaa", "20261002T000000Z-bbbbbb"
        for path, date in ((f"routine-results/{one}/x/a", "2026-10-01T01:00:00Z"),
                           (f"routine-results/{one}/x/b", "2026-10-03T00:00:00Z"),
                           (f"routine-results/{two}/c", "2026-10-02T03:00:00+02:00"),
                           ("routine-results/not-a-run/d", "2026-10-02T04:00:00Z"),
                           ("results/e", "2026-10-02T05:00:00Z")):
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(path, encoding="utf-8")
            git("add", "-A")
            git("commit", "-qm", path, date=date)
        log = subprocess.run(["git", "log", "--reverse", "--format=%H"], cwd=repo,
                             check=True, capture_output=True, text=True).stdout.split()
        # x/b came a commit later: it is not part of run one's first ingest.
        def blob(commit, path):
            return subprocess.run(["git", "rev-parse", f"{commit}:{path}"], cwd=repo,
                                  check=True, capture_output=True, text=True).stdout.strip()
        # Each file's blob id is the one its first ingest added (round 5, B2).
        self.assertEqual(routine_ingest_times.ingest_times(repo), {
            one: {"commit": log[0], "time": "2026-10-01T01:00:00+00:00",
                  "files": {"x/a": blob(log[0], f"routine-results/{one}/x/a")}},
            two: {"commit": log[2], "time": "2026-10-02T03:00:00+02:00",
                  "files": {"c": blob(log[2], f"routine-results/{two}/c")}}})
        # An edit in place afterwards does not change what was recorded.
        (repo / f"routine-results/{one}/x/a").write_text("edited", encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", "edit", date="2026-10-04T00:00:00Z")
        self.assertEqual(routine_ingest_times.ingest_times(repo)[one]["files"],
                         {"x/a": blob(log[0], f"routine-results/{one}/x/a")})
        self.assertIsNone(routine_ingest_times.ingest_times(self.tmp / "nowhere"))
        # A shallow clone may not reach a run's first ingest: refused, exit 2.
        shallow = self.tmp / "shallow"
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow)],
                       check=True, capture_output=True)
        self.assertIsNone(routine_ingest_times.ingest_times(shallow))
        self.assertEqual(routine_ingest_times.main([str(shallow)]), 2)
        self.assertEqual(routine_ingest_times.main([str(repo)]), 0)

    def set_context(self, run_ids, context, **arm_context):
        for run_id in run_ids:
            for path in (self.tree / "routine-results" / run_id).rglob("*_skill/summary.json"):
                self.edit(path, lambda d: d["arm_context"].update(
                    skills_digest=context + d["role"], **arm_context))

    def test_no_single_run_chooses_the_context(self):
        # Round 4's reproducer (test_p1): fifteen real runs that show a gain,
        # then ten later forged ones, each through a fire of its own, flat,
        # with a fresh arm context. The newest run's context once chose the
        # pool, leaving only the forged runs.
        self.write("gain", FLAT[:15], [8.5, 8.7] * 8, without_judges=[6.0, 6.2] * 8,
                   model_tag="b")
        _, real = self.run_gates("a.json")
        self.assertEqual(real["skills"]["gain"]["verdict"], "keep")
        forged = self.write("gain", FLAT[:10], FLAT_JUDGE, start=40, model_tag="f")
        self.set_context(forged, "forged-")
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skills"]["gain"]["verdict"], "keep")
        self.assertEqual(doc["skills"]["gain"]["cells"][0]["key"],
                         real["skills"]["gain"]["cells"][0]["key"])
        self.assertEqual(doc["skills"]["gain"]["runs_used"],
                         real["skills"]["gain"]["runs_used"])

    def test_a_context_tie_is_insufficient(self):
        self.write("flat", FLAT[:6], FLAT_JUDGE)
        other = self.write("flat", FLAT[:6], FLAT_JUDGE, start=40, model_tag="b")
        self.set_context(other, "other-")
        _, doc = self.run_gates("a.json")
        cell = doc["skills"]["flat"]["cells"][0]
        self.assertEqual((cell["key"]["with_context"], cell["key"]["without_context"]),
                         (None, None))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")

    def test_off_roster_runs_do_not_choose_the_context(self):
        self.write("flat", FLAT[:6], FLAT_JUDGE)
        _, alone = self.run_gates("a.json")
        off = self.write("flat", FLAT[:10], FLAT_JUDGE, start=40, model_tag="b",
                         model="model-z")
        self.set_context(off, "off-")
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skills"]["flat"]["cells"][0]["key"],
                         alone["skills"]["flat"]["cells"][0]["key"])
        self.assertEqual(doc["skills"]["flat"]["runs_used"],
                         alone["skills"]["flat"]["runs_used"])

    def git_results(self, repo, *, steps):
        """`repo`, a Git checkout of the results tree committed in `steps`:
        each (paths moved in, committer time); returns ingest_times of it."""
        import routine_ingest_times
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
        git = ["git", *INGEST_IDENTITY]
        repo.mkdir()
        subprocess.run(git + ["init", "-q"], cwd=repo, check=True)
        for paths, when in steps:
            for path in paths:
                target = repo / path.relative_to(self.tree)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(path, target) if path.is_dir() else shutil.copy(path, target)
            subprocess.run(git + ["add", "-A"], cwd=repo, check=True)
            subprocess.run(git + ["commit", "-qm", when], cwd=repo, check=True,
                           env={**env, "GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when})
        return routine_ingest_times.ingest_times(repo)

    def test_an_arm_added_after_the_first_ingest_is_not_read(self):
        # Round 4's reproducer (test_p3): the with arms ingested at once,
        # the without arms pushed into the same run ids thirty days later.
        # The run id's ingest time was its first commit, so the late arms
        # passed the 48-hour window and the cell retired on them.
        from datetime import timedelta
        run_ids = self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, honest = self.run_gates("a.json")
        self.assertEqual(honest["skills"]["flat"]["verdict"], "retire")
        routine = sorted((self.tree / "routine-results").iterdir())
        withouts = sorted((self.tree / "routine-results").rglob("without_skill"))
        first = [p for run in routine for p in run.rglob("*")
                 if p.is_file() and "without_skill" not in p.parts]
        # The routine's vouch.json covered what its first ingest held.
        for run in routine:
            (run / "vouch.json").write_bytes(compute_gates.canonical_vouch(real_mac(
                run, run.name, [p.relative_to(run).as_posix() for p in first
                                if p.is_relative_to(run)])))
        late = iso(run_time(run_ids[-1]) + timedelta(days=30))
        repo = self.tmp / "results-repo"
        self.ingest = self.git_results(repo, steps=[
            (first, iso(run_time(run_ids[-1]) + timedelta(hours=1))), (withouts, late)])
        self.tree = repo
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skipped"]["routine arm run added after its run's first "
                                        "ingest"], 10)
        self.assertEqual(doc["skipped"]["no fire vouches for the routine run: its arms or "
                                        "trials are not its fire's"], 10)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(doc["skills"]["flat"]["runs_used"], [])

    def test_a_file_pushed_into_an_ingested_run_does_not_disqualify_it(self):
        # Round 4's reproducer (test_p4b_dump): twenty real runs, half with a
        # judge gain, and twenty flat ones. A later push of one extra arm into
        # each gain run once refused the whole run, leaving only flat runs.
        with_judges = [8.6 if i % 4 >= 2 else (7.0, 7.2)[i % 2] for i in range(20)]
        without_judges = [6.0 if i % 4 >= 2 else (7.0, 7.2)[i % 2] for i in range(20)]
        run_ids = self.write("flat", FLAT[:20], with_judges, without_judges=without_judges)
        self.write("flat", FLAT[:20], FLAT_JUDGE, start=30, model_tag="b")
        _, before = self.run_gates("a.json")
        for i, run_id in enumerate(run_ids):
            if i % 4 >= 2:
                base = self.tree / "routine-results" / run_id / "flat"
                (stamp_dir,) = base.iterdir()
                extra = base / (stamp_dir.name[:-3] + "59Z")
                shutil.copytree(stamp_dir, extra)
                shutil.rmtree(extra / "without_skill")
                self.edit(extra / "with_skill" / "summary.json",
                          lambda d: d.update(errors=0, extra=True))
        _, after = self.run_gates("b.json")
        self.assertEqual(after["skipped"]["routine arm run added after its run's first "
                                         "ingest"], 10)
        self.assertEqual(after["skills"]["flat"]["verdict"],
                         before["skills"]["flat"]["verdict"])
        self.assertEqual(after["skills"]["flat"]["runs_used"],
                         before["skills"]["flat"]["runs_used"])
        self.assertEqual(after["skills"]["flat"]["cells"][0]["class"],
                         before["skills"]["flat"]["cells"][0]["class"])

    def test_judge_figures_whose_variance_underflows_do_not_crash(self):
        # Round 4's reproducer (test_p5): judge figures around 1e-100 square
        # to 0 in the Welch-Satterthwaite denominator: ZeroDivisionError.
        run_ids = self.write("flat", FLAT[:10], FLAT_JUDGE)
        for run_id in run_ids:
            for path in (self.tree / "routine-results" / run_id).rglob("trial-*/summary.json"):
                k = int(path.parent.name.split("-")[1])
                bump = 1e-100 if "with_skill" in path.parts and run_id[-1] in "13579" else 0
                self.edit(path, lambda d, v=(k - 1) * 1e-100 + bump:
                          d["judge"].update(overall=v))
        self.ingest = {}
        for run_id in run_ids:
            self.ingested(run_id)
        _, doc = self.run_gates("a.json")
        # Decided, not caught: a delta of 5e-101 is under every margin.
        self.assertEqual((doc["skills"]["flat"]["verdict"], doc["skills"]["flat"]["reason"]),
                         ("retire", "every cell shows no benefit"))

    def test_one_skills_failure_is_its_own(self):
        from unittest import mock
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        self.write("gain", FLAT[:5], [8.5, 8.7] * 3, without_judges=[6.0, 6.2] * 3,
                   model_tag="b")
        real = gates.retirement

        def failing(index, models, skill, policy, expected):
            if skill == "gain":
                raise ZeroDivisionError("a message that is not reported")
            return real(index, models, skill, policy, expected)
        with mock.patch.object(gates, "retirement", failing):
            _, doc = self.run_gates("a.json")
        gain = doc["skills"]["gain"]
        self.assertEqual((gain["verdict"], gain["cells"], gain["runs_used"], gain["reason"]),
                         ("insufficient", [], [], "the verdict raised ZeroDivisionError"))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def test_a_file_edited_in_place_after_its_ingest_is_not_read(self):
        # Round 5's reproducer (pers/): an ingested run's summary rewritten in
        # place on persistent/eval-results was read as vouched.
        gain = self.write("gain", FLAT[:10], [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5)
        _, before = self.run_gates("a.json")
        self.assertEqual(before["skills"]["gain"]["verdict"], "keep")
        for run_id in gain:
            for path in (self.tree / "routine-results" / run_id).rglob(
                    "with_skill/trial-*/summary.json"):
                self.edit(path, lambda d: d["judge"].update(overall=6.1), reingest=False)
        _, after = self.run_gates("b.json")
        # Round 6: an edit in place leaves the MAC unverifiable, so the
        # whole run (both arms) is not read.
        self.assertEqual(after["skipped"]["routine run's files are not the bytes its "
                                         "first ingest added, so its MAC cannot be "
                                         "verified"], 20)
        self.assertNotEqual(after["skills"]["gain"]["verdict"], "retire")
        self.assertEqual(after["skills"]["gain"]["runs_used"], [])

    def test_an_in_place_edit_on_the_results_branch_is_seen_end_to_end(self):
        from datetime import timedelta
        run_ids = self.write("flat", FLAT[:10], FLAT_JUDGE)
        everything = [p for p in sorted((self.tree / "routine-results").rglob("*"))
                      if p.is_file()]
        repo = self.tmp / "results-repo"
        self.ingest = self.git_results(repo, steps=[
            (everything, iso(run_time(run_ids[-1]) + timedelta(hours=1)))])
        self.tree = repo
        _, honest = self.run_gates("a.json")
        self.assertEqual(honest["skills"]["flat"]["verdict"], "retire")
        # A later commit edits one arm summary in place.
        target = next((repo / "routine-results" / run_ids[0]).rglob("with_skill/summary.json"))
        self.edit(target, lambda d: d.update(edited=True), reingest=False)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
                        "commit", "-qam", "edit"], cwd=repo, check=True)
        import routine_ingest_times
        self.ingest = routine_ingest_times.ingest_times(repo)
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skipped"]["routine run's files are not the bytes its first "
                                        "ingest added, so its MAC cannot be verified"], 2)

    def test_copies_elsewhere_never_displace_a_vouched_run(self):
        # Round 5's reproducer (test_suppress.py): byte copies of the gain
        # runs under results/, nested under a fixture not on main, were kept
        # (first by path) and the vouched runs dropped as duplicates: retire.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        gain = self.write("flat", FLAT[:10], [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5,
                          start=10, model_tag="b")
        _, before = self.run_gates("before.json")
        self.assertEqual(before["skills"]["flat"]["verdict"], "keep")
        for run_id in gain:
            for stamp_dir in (self.tree / "routine-results" / run_id / "flat").iterdir():
                dst = self.tree / "results" / "flat" / stamp_dir.name
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy(stamp_dir / "report.md", dst / "report.md")
                for arm in stamp_dir.iterdir():
                    if arm.is_dir():
                        shutil.copytree(arm, dst / "zzz" / arm.name)
        _, after = self.run_gates("after.json")
        self.assertNotEqual(after["skills"]["flat"]["verdict"], "retire")
        self.assertEqual(after["skipped"]["duplicate arm run from another cell or tree"], 20)
        self.assertNotIn("duplicate arm run", after["skipped"])
        self.assertEqual(after["polluted"], [["flat", "", "model-a"]])
        cell = after["skills"]["flat"]["cells"][0]
        self.assertEqual((cell["class"], len(after["skills"]["flat"]["runs_used"])),
                         ("insufficient", 40))
        self.assertIn("pollution", cell["reason"])

    def test_a_results_copy_of_a_vouched_run_pollutes_it_and_is_dropped(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        run_id = f"{stamp(0)}-a00000"
        source = self.tree / "routine-results" / run_id / "flat" / stamp(0)
        shutil.copytree(source, self.tree / "results" / "flat" / stamp(0))
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"]["duplicate arm run from another cell or tree"], 2)
        self.assertEqual(doc["polluted"], [["flat", "", "model-a"]])
        used = doc["skills"]["flat"]["runs_used"]
        self.assertTrue(all(k.startswith("routine-results/") for k in used))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")

    def test_fires_that_name_one_run_id_twice_never_stop_the_evaluation(self):
        # Round 5's reproducer (fires.json): a second fire from another
        # branch naming a real run id made load_fires raise, and the whole
        # evaluation exit 2.
        (run_id,) = self.write("flat", FLAT[:1], FLAT_JUDGE)
        good = dict(self.fires[0])
        attacker = {**good, "id": 2, "head_branch": "attacker", "display_title": "x"}
        for name, extra, vouched in (
                ("an untrusted second fire", [attacker], True),
                ("a second attempt", [{**good, "id": 2, "run_attempt": 2}], True),
                ("two trusted fires", [{**good, "id": 2}], False)):
            with self.subTest(name=name):
                self.fires = [good, *extra]
                _, doc = self.run_gates("a.json")
                self.assertEqual(set(doc["skipped"]) <= {"no aggregate block"}, vouched,
                                 doc["skipped"])
                if not vouched:
                    self.assertEqual(doc["skipped"]["more than one trusted fire names the "
                                                    "routine run"], 2)

    def test_reads_are_bounded_and_never_follow_a_symlink(self):
        # Round 5's reproducer (symtree/): a summary.json that is a symlink
        # to /dev/zero was read without bound.
        self.write("flat", FLAT[:1], FLAT_JUDGE)
        link = self.tree / "results" / "demo" / "20261001T000000Z" / "with_skill" / "summary.json"
        link.parent.mkdir(parents=True)
        os.symlink("/dev/zero", link)
        big = self.tree / "results" / "flat" / "20261002T000000Z" / "with_skill" / "summary.json"
        big.parent.mkdir(parents=True)
        big.write_text(json.dumps({"pad": "x" * (compute_gates.READ_CAPS["summary.json"])}),
                       encoding="utf-8")
        (big.parent.parent / "report.md").write_text("# r\n", encoding="utf-8")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"]["no readable arm summary"], 1)
        self.assertEqual(doc["skipped"]["arm summary over its size cap"], 1)
        # The reader itself: a symlink, a FIFO and an oversize file.
        target = self.tmp / "t.json"
        target.write_text("{}", encoding="utf-8")
        os.symlink(target, self.tmp / "l.json")
        os.mkfifo(self.tmp / "fifo")
        self.assertEqual(compute_gates._read_bytes(self.tmp / "l.json", 10), (None, "unreadable"))
        self.assertEqual(compute_gates._read_bytes(self.tmp / "fifo", 10), (None, "unreadable"))
        self.assertEqual(compute_gates._read_bytes(target, 1), (None, "oversize"))
        self.assertEqual(compute_gates._read_bytes(target, 2), (b"{}", None))

    def test_a_memory_error_is_one_skills_failure(self):
        from unittest import mock
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        self.write("gain", FLAT[:5], [8.5, 8.7] * 3, without_judges=[6.0, 6.2] * 3,
                   model_tag="b")
        real = gates.retirement

        def failing(index, models, skill, policy, expected):
            if skill == "gain":
                raise MemoryError
            return real(index, models, skill, policy, expected)
        with mock.patch.object(gates, "retirement", failing):
            _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["gain"]["reason"], "the verdict raised MemoryError")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def test_arms_of_other_skill_sets_are_not_paired(self):
        # compute_gates' pair key: arm_context.others_digest and the frozen
        # guidance, both arms alike.
        run_ids = self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        for run_id in run_ids:
            for path in (self.tree / "routine-results" / run_id).rglob(
                    "without_skill/summary.json"):
                self.edit(path, lambda d: d["arm_context"].update(others_digest="other"))
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        for run_id in run_ids:
            for path in (self.tree / "routine-results" / run_id).rglob(
                    "without_skill/summary.json"):
                self.edit(path, lambda d: (d["arm_context"].update(others_digest="o"),
                                           d["context"]["guidance"].update(digest="g2")))
        _, doc = self.run_gates("c.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")

    def test_only_one_skill_retires_per_evaluation(self):
        self.write("one", FLAT[:10], FLAT_JUDGE)
        self.write("two", FLAT[:11], FLAT_JUDGE, model_tag="b")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["two"]["verdict"], "retire")
        self.assertEqual(doc["skills"]["one"]["verdict"], "retire-pending")
        self.assertEqual(doc["skills"]["one"]["raw_verdict"], "retire")

    # --- Round 6 -----------------------------------------------------------

    def unlanded(self, n, *, start=50, fixture_path="evals/flat", **fields):
        """`n` trusted fires naming run ids whose results never landed."""
        run_ids = []
        for i in range(n):
            run_ids.append(f"{stamp(start + i)}-dead0{i}")
            self.fires.append({"id": len(self.fires) + 1,
                               "created_at": iso(run_time(run_ids[-1])),
                               "conclusion": "success", "head_branch": "main",
                               "event": "workflow_dispatch",
                               "display_title": fire_title(fixture_path, "model-a"),
                               "path": ".github/workflows/routine-eval-fire.yml",
                               "head_sha": self.fire_sha, "run_attempt": 1,
                               "run_number": len(self.fires) + 1,
                               "run_id": run_ids[-1], **fields})
        return run_ids

    def test_a_squatted_run_id_with_a_junk_mac_is_not_vouched(self):
        # Round 6's reproducer (test_r6_probe.py): a first ingest whose
        # vouch.json held an all-zero MAC no key made was counted, and the
        # cell retired on it.
        run_ids = self.write("flat", FLAT[:10], FLAT_JUDGE)
        for run_id in run_ids:
            (self.tree / "routine-results" / run_id / "vouch.json").write_bytes(
                compute_gates.canonical_vouch(PLACEHOLDER_MAC))
            self.ingested(run_id, seal=False)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"]["routine run's MAC does not verify under VOUCH_KEY"],
                         20)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(doc["skills"]["flat"]["runs_used"], [])

    def test_a_mac_under_another_key_or_run_id_is_not_vouched(self):
        run_ids = self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, honest = self.run_gates("a.json")
        self.assertEqual(honest["skills"]["flat"]["verdict"], "retire")
        root = self.tree / "routine-results"
        for case, mac in (
                ("another key", lambda run: write_vouch.mac(
                    write_vouch.derive_nonce(b"another-key", run.name),
                    {rel: (run / rel).read_bytes() for rel in self.ingest[run.name]["files"]
                     if rel != "vouch.json"})),
                ("another run id", lambda run: real_mac(run, run_ids[-1] if run.name !=
                                                        run_ids[-1] else run_ids[0],
                                                        self.ingest[run.name]["files"]))):
            with self.subTest(case=case):
                for run_id in run_ids:
                    (root / run_id / "vouch.json").write_bytes(
                        compute_gates.canonical_vouch(mac(root / run_id)))
                    self.ingested(run_id, seal=False)
                _, doc = self.run_gates(f"{case}.json")
                self.assertEqual(doc["skipped"]["routine run's MAC does not verify under "
                                                "VOUCH_KEY"], 20)
                self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")

    def test_only_the_canonical_vouch_line_is_read(self):
        # Round 6, R6-4: the ingester stages json.dumps({"mac": mac}) + "\n"
        # whatever the routine wrote, so any other bytes did not come
        # through it, even with the right MAC.
        (run_id,) = self.write("flat", FLAT[:1], FLAT_JUDGE)
        path = self.tree / "routine-results" / run_id / "vouch.json"
        mac = json.loads(path.read_text())["mac"]
        self.assertEqual(path.read_bytes(), (json.dumps({"mac": mac}) + "\n").encode())
        for case, data in (("no space", '{"mac":"%s"}\n' % mac),
                           ("no newline", '{"mac": "%s"}' % mac),
                           ("a CRLF", '{"mac": "%s"}\r\n' % mac)):
            with self.subTest(case=case):
                path.write_text(data, encoding="utf-8", newline="")
                self.ingested(run_id, seal=False)
                _, doc = self.run_gates(f"{case}.json")
                self.assertEqual(doc["skipped"].get("routine run's vouch.json is not a "
                                                    "verified MAC"), 2, doc["skipped"])

    def test_without_vouch_key_no_routine_run_counts(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        out = self.tmp / "nokey.json"
        args = ["--results-tree", str(self.tree), "--roster", str(self.roster),
                "--policy", str(POLICY_FILE), "--evals-dir", str(self.evals),
                "--as-of", AS_OF, "--out", str(out),
                "--registry", f"adam-agentskills={self.registry}", *self.trust_args()]
        for unset in (True, False):
            with self.subTest(unset=unset):
                with mock.patch.dict(os.environ, {"VOUCH_KEY": ""}):
                    if unset:
                        del os.environ["VOUCH_KEY"]
                    self.assertEqual(compute_gates.main(args), 0)
                doc = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(doc["skipped"][compute_gates.NO_KEY], 20)
                self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        # The key is never an argument.
        with mock.patch.dict(os.environ, {"VOUCH_KEY": ""}), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            compute_gates.main([*args, "--vouch-key", VOUCH_KEY])

    def test_unlanded_trusted_fires_refuse_no_benefit(self):
        # Round 6's reproducer (test_r6_probe.py): ten vouched flat runs and
        # five trusted fires whose results never landed retired the cell, so
        # blocking ingests cherry-picked the evidence toward retirement.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, honest = self.run_gates("honest.json")
        self.assertEqual(honest["skills"]["flat"]["verdict"], "retire")
        dead = self.unlanded(5)
        _, doc = self.run_gates("dead.json")
        cell = doc["skills"]["flat"]["cells"][0]
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(cell["class"], "insufficient")
        self.assertEqual(cell["unlanded_fires"], sorted(dead))
        for run_id in dead:
            self.assertIn(run_id, cell["reason"])
        self.assertEqual([u["run_id"] for u in doc["unlanded"]], sorted(dead))
        self.assertTrue(all(u["overdue"] for u in doc["unlanded"]))
        # Younger than the grace window: at most pending, never retire.
        _, young = self.run_gates("young.json", as_of=stamp(60))
        cell = young["skills"]["flat"]["cells"][0]
        self.assertEqual((cell["class"], young["skills"]["flat"]["verdict"]),
                         ("no-benefit-pending", "retire-pending"))
        self.assertFalse(any(u["overdue"] for u in young["unlanded"]))
        # A fire created after as-of is not read.
        _, before = self.run_gates("before.json", as_of=stamp(40))
        self.assertEqual(before["unlanded"], [])
        self.assertEqual(before["skills"]["flat"]["verdict"], "retire")

    def test_a_waived_unlanded_fire_blocks_nothing(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        dead = self.unlanded(2)
        policy = self.tmp / "policy.yml"
        text = POLICY_FILE.read_text(encoding="utf-8")
        for waived, verdict in ((dead[:1], "insufficient"), (dead, "retire")):
            with self.subTest(waived=len(waived)):
                entries = "".join(f"    - run_id: {r}\n      reason: the routine session "
                                  "died\n      date: 2026-10-05\n" for r in waived)
                policy.write_text(text.replace("  waived_fires: []\n",
                                               "  waived_fires:\n" + entries),
                                  encoding="utf-8")
                with mock.patch.object(sys.modules[__name__], "POLICY_FILE", policy):
                    _, doc = self.run_gates(f"w{len(waived)}.json")
                self.assertEqual(doc["skills"]["flat"]["verdict"], verdict)

    def with_policy(self, name, old, new):
        """`run_gates(name)` under the committed policy with `old` replaced."""
        policy = self.tmp / f"policy-{name}.yml"
        text = POLICY_FILE.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, old)
        policy.write_text(text.replace(old, new), encoding="utf-8")
        with mock.patch.object(sys.modules[__name__], "POLICY_FILE", policy):
            return self.run_gates(name)[1]

    def test_a_verified_run_with_no_trusted_fire_blocks_its_own_cell(self):
        # Round 7's reproducers (test_C, test_D): re-running a fire (the API
        # then reports attempt 2) or deleting it dropped its verified run
        # silently, so removing the runs that showed a gain flipped keep to
        # retire. The run's MAC verified, so the routine made it: it is an
        # orphan, and blocks its own cell until waived.
        self.write("flat", FLAT[:3], [9.6, 9.4, 9.6], without_judges=[5.0, 5.2, 5.0],
                   model_tag="b")
        self.write("flat", FLAT[:10], FLAT_JUDGE, start=3)
        _, base = self.run_gates("0.json")
        self.assertEqual(base["skills"]["flat"]["verdict"], "keep")
        gain = [f["run_id"] for f in self.fires[:3]]
        for name, change in (("re-run", lambda f: f.update(run_attempt=2)),
                             ("cancelled", lambda f: f.update(conclusion="cancelled")),
                             ("another branch", lambda f: f.update(head_branch="x"))):
            with self.subTest(case=name):
                saved = [dict(f) for f in self.fires]
                for fire in self.fires[:3]:
                    change(fire)
                _, doc = self.run_gates(f"{name}.json")
                self.fires = saved
                self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
                self.assertEqual(sorted(u["run_id"] for u in doc["unlanded"]), gain)
                self.assertTrue(all(u["overdue"] and u["model"] == "model-a"
                                    and u["skill"] == "flat" for u in doc["unlanded"]))
                self.assertEqual(doc["needs_waiver"], doc["unlanded"])
                reason = doc["skills"]["flat"]["cells"][0]["reason"]
                self.assertIn("verified runs no trusted fire names", reason)
                for run_id in gain:
                    self.assertIn(run_id, reason)
        # Two trusted fires naming one run: ambiguous, so an orphan too.
        saved = [dict(f) for f in self.fires]
        doubled = {**self.fires[0], "id": 99, "run_number": len(self.fires) + 1}
        self.fires.append(doubled)
        _, doc = self.run_gates("doubled.json")
        # Cancelled since, it is untrusted, and still fills its run number.
        self.fires = saved + [{**doubled, "conclusion": "cancelled"}]
        # Once, as an orphan, not again for each fire naming it.
        self.assertEqual([(u["run_id"], u["why"]) for u in doc["unlanded"]],
                         [(gain[0], "no trusted fire names its verified run")])
        # Two gain runs still read: an orphan refuses only no-benefit.
        self.assertEqual(doc["skills"]["flat"]["verdict"], "keep")
        # Waived, the orphans block nothing, and the cell is read without them.
        for fire in self.fires[:3]:
            fire["run_attempt"] = 2
        entries = "".join(f"    - run_id: {r}\n      reason: re-run by mistake\n"
                          "      date: 2026-10-05\n" for r in gain)
        doc = self.with_policy("waived", "  waived_fires: []\n", "  waived_fires:\n" + entries)
        self.assertEqual((doc["unlanded"], doc["needs_waiver"]), ([], []))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def test_a_deleted_fire_leaves_a_run_number_gap_that_blocks(self):
        # Round 7, R7-1c: a fire deleted with its results gone too leaves no
        # orphan; its run_number is the only trace. Any gap from
        # fire_sequence_from makes every no-benefit cell insufficient.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, base = self.run_gates("0.json")
        self.assertEqual((base["skills"]["flat"]["verdict"], base["missing_fire_numbers"]),
                         ("retire", []))
        # Two later fires (failed before their notice, so no run id and no
        # results), then the first deleted.
        for n in (11, 12):
            self.fires.append({**self.fires[0], "id": 50 + n, "run_number": n,
                               "conclusion": "failure", "run_id": None})
        gone = self.fires.pop(10)
        _, doc = self.run_gates("1.json")
        self.assertEqual(doc["missing_fire_numbers"], [gone["run_number"]])
        self.assertEqual(doc["unlanded"], [])
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        reason = doc["skills"]["flat"]["cells"][0]["reason"]
        self.assertIn("run numbers are missing from the sequence", reason)
        self.assertIn(str(gone["run_number"]), reason)
        # Waived, it blocks nothing.
        doc = self.with_policy("waived", "  waived_fire_numbers: []\n",
                               f"  waived_fire_numbers:\n    - number: {gone['run_number']}\n"
                               "      reason: deleted by mistake\n      date: 2026-10-05\n")
        self.assertEqual((doc["missing_fire_numbers"], doc["skills"]["flat"]["verdict"]),
                         ([], "retire"))
        # A gap before fire_sequence_from is not read.
        doc = self.with_policy("later", "  fire_sequence_from: 1\n",
                               f"  fire_sequence_from: {gone['run_number'] + 1}\n")
        self.assertEqual((doc["missing_fire_numbers"], doc["skills"]["flat"]["verdict"]),
                         ([], "retire"))
        # Any FIRE_PATH run fills the sequence, trusted or not; another
        # workflow's run numbers are not this sequence.
        self.fires.append({**gone, "id": 99, "head_branch": "attacker"})
        self.fires.append({**gone, "id": 98, "run_number": 20,
                           "path": ".github/workflows/other.yml"})
        _, doc = self.run_gates("2.json")
        self.assertEqual((doc["missing_fire_numbers"], doc["skills"]["flat"]["verdict"]),
                         ([], "retire"))

    def test_a_title_with_no_model_is_untrusted_and_its_run_an_orphan(self):
        # Round 7's reproducer (test_B): a title with no model was read as
        # the roster's first arm, so a roster change re-mapped every such
        # fire. It is untrusted now, whatever the roster: its verified run
        # is an orphan blocking its own cell (the run's own model).
        self.write("flat", FLAT[:10], FLAT_JUDGE, vouched=False)
        for run in sorted((self.tree / "routine-results").iterdir()):
            self.vouch(run.name, "evals/flat", "model-a", trials=3,
                       display_title=fire_title("evals/flat"))
        for roster in ("arms:\n  - id: model-a\n", "arms:\n  - id: model-b\n  - id: model-a\n"):
            with self.subTest(roster=roster):
                self.roster.write_text(roster, encoding="utf-8")
                _, doc = self.run_gates(f"{len(roster)}.json")
                self.assertEqual(doc["skills"]["flat"]["runs_used"], [])
                self.assertEqual(len(doc["unlanded"]), 10)
                self.assertEqual({(u["model"], u["overdue"]) for u in doc["unlanded"]},
                                 {("model-a", True)})

    def test_a_fire_that_carries_a_run_id_must_land_whatever_its_conclusion(self):
        # Round 9, R9-3: the routine-vouch notice comes just before the fire
        # API call, so a fire cancelled or failed after it may have started
        # the routine. It must land like a trusted fire, and never vouches.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        base = list(self.fires)
        for conclusion in ("cancelled", "failure", "timed_out", None):
            with self.subTest(conclusion=conclusion):
                self.fires = list(base)
                (dead,) = self.unlanded(1, conclusion=conclusion)
                _, doc = self.run_gates(f"{conclusion}.json")
                self.assertEqual([(u["run_id"], u["overdue"]) for u in doc["unlanded"]],
                                 [(dead, True)])
                self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        # Its run, when it lands, vouches for nothing: an orphan, still blocking.
        self.fires = list(base)
        self.fires[0]["conclusion"] = "cancelled"
        _, doc = self.run_gates("landed.json")
        self.assertEqual([(u["run_id"], u["why"]) for u in doc["unlanded"]],
                         [(base[0]["run_id"], "no trusted fire names its verified run")])
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")

    def test_a_run_id_with_no_valid_vouch_blocks_its_cell(self):
        # Round 9, R9-3: an ingested run id whose first ingest has no valid
        # vouch.json (a squat) blocks the cell its arm runs name; one that
        # names no cell is listed under needs_waiver.
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        (squat,) = self.write("flat", FLAT[:1], FLAT_JUDGE[:1], start=20, model_tag="c",
                              vouched=False)
        self.ingested(squat)
        _, doc = self.run_gates("0.json")
        self.assertEqual([(u["run_id"], u["skill"], u["model"], u["why"])
                          for u in doc["needs_waiver"]],
                         [(squat, "flat", "model-a",
                           "its first ingest has no valid vouch.json")])
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        # Waived, it blocks nothing.
        doc = self.with_policy("waived", "  waived_fires: []\n",
                               f"  waived_fires:\n    - run_id: {squat}\n"
                               "      reason: a squat\n      date: 2026-10-05\n")
        self.assertEqual((doc["needs_waiver"], doc["skills"]["flat"]["verdict"]),
                         ([], "retire"))

    def test_only_trusted_eval_fires_for_the_cell_block_it(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        cases = {
            "another branch": {"head_branch": "attacker"},
            "a second attempt": {"run_attempt": 2},
            # A failed fire with no run id never reached its notice.
            "a failed fire": {"conclusion": "failure", "run_id": None},
            "scaffold mode": {"display_title": fire_title("evals/flat", "model-a",
                                                         mode="scaffold")},
            "another fixture": {"display_title": fire_title("evals/gain", "model-a")},
            "another model": {"display_title": fire_title("evals/flat", "model-b")},
            "an uncommitted fixture": {"display_title": fire_title("evals/nope", "model-a")},
            # Round 7, R7-3: a title with no model is no trusted fire.
            "no model": {"display_title": fire_title("evals/flat")},
        }
        base = list(self.fires)
        for name, fields in cases.items():
            with self.subTest(case=name):
                self.fires = list(base)
                self.unlanded(1, **fields)
                _, doc = self.run_gates(f"{len(self.fires)}.json")
                self.assertEqual(doc["skills"]["flat"]["verdict"], "retire", doc["unlanded"])

    def test_a_side_branch_merged_in_is_never_a_first_ingest(self):
        # Round 6's reproducer (hist.sh): a side-branch commit adding a run
        # id, backdated before the genuine ingest and merged in afterwards,
        # was read as the run's first ingest. Only the first-parent chain,
        # in parent order, by the ingest identity, counts.
        repo = self.tmp / "hist"
        repo.mkdir()
        run = "routine-results/20261001T000000Z-abcdef"

        def git(*args, who=None, date=None):
            env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
            if date:
                env.update(GIT_COMMITTER_DATE=date, GIT_AUTHOR_DATE=date)
            ident = who or ["-c", "user.name=t", "-c", "user.email=t@example.com"]
            return subprocess.run(["git", *ident, *args], cwd=repo, check=True,
                                  capture_output=True, text=True, env=env).stdout.strip()

        def put(name, text):
            (repo / run).mkdir(parents=True, exist_ok=True)
            (repo / run / name).write_text(text, encoding="utf-8")
        git("init", "-q", "-b", "persistent/eval-results")
        (repo / "README").write_text("base\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-qm", "base", date="2026-09-01T00:00:00Z")
        git("checkout", "-q", "-b", "side")
        put("vouch.json", '{"mac": "%s"}\n' % ("0" * 64))
        put("x", "forged\n")
        put("y", "forged only\n")
        git("add", "-A")
        # Even committed as the ingest identity, and dated first.
        git("commit", "-qm", "forged", who=INGEST_IDENTITY, date="2026-10-01T00:30:00Z")
        git("checkout", "-q", "persistent/eval-results")
        put("vouch.json", '{"mac": "%s"}\n' % ("a" * 64))
        put("x", "genuine\n")
        git("add", "-A")
        git("commit", "-qm", "genuine", who=INGEST_IDENTITY, date="2026-10-01T01:00:00Z")
        genuine = git("rev-parse", "HEAD")
        git("merge", "-q", "-X", "theirs", "side", "-m", "merge", date="2026-10-01T02:00:00Z")
        times = routine_ingest_times.ingest_times(repo)
        first = times["20261001T000000Z-abcdef"]
        self.assertEqual((first["commit"], first["time"]),
                         (genuine, "2026-10-01T01:00:00+00:00"))
        self.assertEqual(sorted(first["files"]), ["vouch.json", "x"])
        self.assertEqual(first["files"]["x"], git("rev-parse", f"{genuine}:{run}/x"))

    def test_only_the_ingest_identity_can_first_ingest_a_run(self):
        repo = self.tmp / "who"
        repo.mkdir()
        env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}

        def commit(path, ident, date):
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(path, encoding="utf-8")
            subprocess.run(["git", *ident, "add", "-A"], cwd=repo, check=True, env=env)
            subprocess.run(["git", *ident, "commit", "-qm", path], cwd=repo, check=True,
                           env={**env, "GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date})
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
        other = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
        one = "20261001T000000Z-aaaaaa"
        commit(f"routine-results/{one}/squat", other, "2026-10-01T00:10:00Z")
        commit(f"routine-results/{one}/real", INGEST_IDENTITY, "2026-10-01T01:00:00Z")
        self.assertEqual(sorted(routine_ingest_times.ingest_times(repo)[one]["files"]),
                         ["real"])
        self.assertEqual(sorted(routine_ingest_times.ingest_times(repo, "t@example.com")
                                [one]["files"]), ["squat"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(routine_ingest_times.main(
                [str(repo), "--committer", "t@example.com"]), 0)
        self.assertEqual(sorted(json.loads(out.getvalue())[one]["files"]), ["squat"])

    def test_the_ingest_identity_is_what_the_ingest_workflow_commits_as(self):
        import yaml as _yaml
        workflow = _yaml.safe_load((ROOT / ".github" / "workflows" / "routine-eval-ingest.yml")
                                   .read_text(encoding="utf-8"))
        script = next(step["run"] for step in workflow["jobs"]["ingest"]["steps"]
                      if step.get("name") == "Commit to persistent/eval-results and push")
        import re as _re
        self.assertEqual(_re.findall(r'user\.email="([^"]*)"', script),
                         [routine_ingest_times.INGEST_COMMITTER])


if __name__ == "__main__":
    unittest.main()
