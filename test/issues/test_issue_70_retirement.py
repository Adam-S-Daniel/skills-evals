#!/usr/bin/env python3
"""Issue #70, part 1: the skill retirement verdict and `gates/latest.json`.

Adam's decisions: the thresholds (2026-10-10, #70) and pooled evidence
(2026-10-25), which replaced #70's four weekly sweeps, with the review rounds
of the same day: the arms are pooled by their own keys, cells come from the
fixtures on main and pool only runs of the content on main up to `--as-of`,
duplicate runs count once, an errored trial scores 0, `cannot-discriminate`,
and one retirement per evaluation. Since 2026-11-03 (the statistics review
and threshold sweep of that day) a cell is decided on PAIRED runs by a
betting confidence sequence with no variance prior: keep at 80% across the
subject's cells, no benefit at 90% under the 0.15 margin, `ceiling` cells
parked, `no-clear-effect` at the run cap. harness/gates.py classifies each
cell and takes the verdict; scripts/compute_gates.py writes the artifact.
test_issue_betting_gate.py covers the bound itself.

Hermetic: canned trial summaries, results trees, a fixture tree and a registry
checkout in a temporary directory, no network, no clock.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml
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
import ingest_routine_results as ingest  # noqa: E402
import run_eval  # noqa: E402

POLICY_FILE = ROOT / "evals" / "gate-policy.yml"
COMMITTED_POLICY = gates.parse_gate_policy(POLICY_FILE.read_text(encoding="utf-8"))["skills"]
#: The cell-rule tests feed up to 40 pairs a cell, so they run on the committed
#: policy with the cap it had before Adam's 2026-11-12 cut to 20; the committed
#: number itself is pinned by `test_committed_policy_loads_with_its_numbers`.
POLICY = {**COMMITTED_POLICY, "max_runs_per_cell": 40}
#: The cell rules are tested on the committed policy: identical arms (D = 0
#: every pair) are no-benefit at the 18th pair, and GAIN against LOSS (a
#: gain of about 0.4) keeps at the 7th.
TEST_POLICY = dict(POLICY)
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


def cell(with_runs, without_runs, *, carried=False, policy=TEST_POLICY, family=1,
         bet_prior=None):
    """`classify_cell` of one cell, a keep family of `family`."""
    return gates.classify_cell(with_runs, without_runs, policy, carried, family, bet_prior)


#: Pairs of identical arms the committed policy needs for no-benefit.
FLAT_DECIDES = 18


def flat_cell(n=FLAT_DECIDES, **kw):
    return (series("with", FLAT[:n], FLAT_JUDGE, **kw)
            + series("without", FLAT[:n], FLAT_JUDGE, **kw))


class PolicyTests(unittest.TestCase):

    def test_committed_policy_loads_with_its_numbers(self):
        # 2026-11-03 (the statistics review and the threshold sweep): keep
        # at 80% across the subject's cells, no benefit at 90% under 0.15, a
        # 40-pair cap, cut to 20 by Adam on 2026-11-12; removals automatic
        # again once withdrawal was hardened (PR #740, #645).
        self.assertEqual(COMMITTED_POLICY, {
            "objective_margin": 0.15, "judge_margin": 1.5, "benefit_confidence": 0.80,
            "retire_confidence": 0.90, "min_cli_versions": 2, "max_runs_per_cell": 20,
            "max_runs_high_cell": 20, "floor_fraction": 0.10, "floor_min_runs": 3,
            "high_stop_min_without": 0.90, "recheck_weeks": 8, "recheck_weeks_high": 4,
            "max_removal_pauses": 3, "retirement_mode": "auto"})

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
        for key, bad in (("retire_confidence", 1), ("benefit_confidence", 0.4),
                         ("min_cli_versions", 0), ("min_cli_versions", 2.5),
                         ("max_runs_per_cell", 0), ("max_runs_per_cell", 40.5),
                         ("max_runs_per_cell", "true"), ("objective_margin", -0.1),
                         # A margin of 1 leaves the removal test no stake.
                         ("objective_margin", 1), ("judge_margin", 11),
                         ("floor_fraction", 1), ("max_runs_high_cell", 0),
                         # Round 2's M2: the high-cell stop is inside the cap.
                         ("max_runs_high_cell", 41),
                         # Moved from code into the policy (docs/rules.md).
                         ("floor_min_runs", 0), ("high_stop_min_without", 1.1),
                         ("recheck_weeks", 0), ("recheck_weeks_high", 1.5),
                         ("max_removal_pauses", 0)):
            with self.assertRaises(gates.GatePolicyError, msg=f"{key}={bad}"):
                gates.parse_gate_policy(self._text(**{key: bad}))

    def test_missing_and_unknown_keys_are_refused(self):
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(self._text(judge_margin=None))
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(self._text(max_runs_per_cell=None))
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy(self._text() + "  sweeps: 4\n")
        # The keys of the fixed-look design (before 2026-10-31) and of the
        # normal-mixture bound (before 2026-11-03) are unknown.
        for retired in ("  min_runs: 5\n", "  retire_looks: [5, 10, 20]\n",
                        "  bootstrap_resamples: 2000\n", "  prior_strength: 4\n",
                        "  check_confidence: 0.85\n", "  ceiling_fraction: 0.9\n",
                        "  judge_ceiling: 9.0\n"):
            with self.subTest(retired=retired), self.assertRaises(gates.GatePolicyError):
                gates.parse_gate_policy(self._text() + retired)
        with self.assertRaises(gates.GatePolicyError):
            gates.parse_gate_policy("- not a mapping\n")


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

    def test_the_judge_counts_only_when_every_trial_was_judged(self):
        judged = [gates.trial_record(trial(overall=f)) for f in (7.0, 7.1, 7.2)]
        self.assertAlmostEqual(gates.run_numbers(judged, True)["judge_mean"], 7.1)
        self.assertTrue(gates.run_numbers(judged, True)["judge_spread"])
        self.assertFalse(gates.run_numbers(judged, True)["judge_conditional"])
        # A conditional run keeps its figure and says it was conditional;
        # _classify decides whether the cell may use it.
        self.assertAlmostEqual(gates.run_numbers(judged, False)["judge_mean"], 7.1)
        self.assertTrue(gates.run_numbers(judged, False)["judge_conditional"])
        one_skipped = judged[:2] + [gates.trial_record(trial(skipped=True))]
        self.assertIsNone(gates.run_numbers(one_skipped * 2, True)["judge_mean"])
        same = [gates.trial_record(trial(overall=7.0))] * 3
        self.assertFalse(gates.run_numbers(same, True)["judge_spread"])


class CellTests(unittest.TestCase):

    def test_a_clear_gain_is_benefit(self):
        self.assertEqual(cell(series("with", GAIN[:6]), series("without", LOSS[:6]))["class"],
                         "insufficient")
        result = cell(series("with", GAIN[:7]), series("without", LOSS[:7]))
        self.assertEqual(result["class"], "benefit")
        self.assertEqual(result["objective"]["keep_at"], 7)

    def test_flat_pairs_are_no_benefit_once_the_remove_test_rejects(self):
        runs = flat_cell(FLAT_DECIDES - 1)
        result = cell(runs[:FLAT_DECIDES - 1], runs[FLAT_DECIDES - 1:])
        self.assertEqual((result["class"], result["reason"]),
                         ("insufficient", "neither test has rejected yet"))
        runs = flat_cell()
        result = cell(runs[:FLAT_DECIDES], runs[FLAT_DECIDES:])
        self.assertEqual(result["class"], "no-benefit", result["reason"])
        self.assertEqual(result["objective"]["remove_at"], FLAT_DECIDES)
        self.assertGreaterEqual(result["objective"]["no_help_confidence"],
                                POLICY["retire_confidence"])
        self.assertLess(result["objective"]["retire_upper"], POLICY["objective_margin"])
        self.assertNotIn("priors", result)

    def test_the_review_repro_four_identical_runs_are_not_no_benefit(self):
        # The 2026-11-03 statistics review: four identical runs per arm at a
        # pass rate of 1.0, two CLI versions and identical judge figures
        # were no-benefit under the old bound.
        same = [(100, 100, 100)] * 4
        result = cell(series("with", same, [9.0] * 4), series("without", same, [9.0] * 4))
        self.assertNotEqual(result["class"], "no-benefit")
        self.assertEqual(result["cli_versions"], CLIS)

    def test_one_cli_version_is_insufficient(self):
        runs = flat_cell(cli=CLIS[0])
        result = cell(runs[:FLAT_DECIDES], runs[FLAT_DECIDES:])
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("not been at its level on pairs spanning 2 CLI versions (1 so far)",
                      result["reason"])
        self.assertEqual(cell(runs[:FLAT_DECIDES], runs[FLAT_DECIDES:],
                              policy={**TEST_POLICY, "min_cli_versions": 1})["class"],
                         "no-benefit")
        # Keeping needs no second version.
        self.assertEqual(cell(series("with", GAIN[:7], cli=CLIS[0]),
                              series("without", LOSS[:7], cli=CLIS[0]))["class"], "benefit")

    def test_pairs_are_one_fire_each_and_a_lone_run_is_unpaired(self):
        runs = flat_cell(5)
        with_runs, without_runs = runs[:5], runs[5:]
        # Another fire's lone with arm, and a second without run of fire 0
        # under another path (the first by path pairs).
        lone = series("with", FLAT[:1], start=40)
        copy = dict(without_runs[0], path=without_runs[0]["path"] + "-b")
        result = cell(with_runs + lone, without_runs + [copy])
        self.assertEqual((result["pairs"], result["unpaired"]), (5, 2))
        self.assertEqual((result["with"]["runs"], result["without"]["runs"]), (5, 5))
        pairs, unpaired = gates.pair_runs(with_runs + lone, [copy] + without_runs)
        self.assertEqual([w["timestamp"] for w, _ in pairs],
                         [r["timestamp"] for r in with_runs])
        self.assertIs(pairs[0][1], without_runs[0])
        self.assertEqual({id(r) for r in unpaired}, {id(lone[0]), id(copy)})

    def test_an_arm_with_no_counted_run_has_no_pair(self):
        result = cell(series("with", FLAT[:4]), [])
        self.assertEqual((result["class"], result["pairs"]), ("insufficient", 0))
        self.assertIn("no pair", result["reason"])

    def test_a_run_needs_one_scored_trial(self):
        runs = flat_cell(5)
        runs[0]["trials"] = [gates.trial_record(trial(infra=True))] * 3
        result = cell(runs[:5], runs[5:])
        self.assertEqual((result["with"]["runs"], result["unpaired"]), (4, 1))
        self.assertEqual(result["skipped"], {"fewer than 1 scored or errored trials": 1})
        # The skipped run, and so its fire, is as if it were not there.
        without = cell(runs[1:5], runs[6:])
        self.assertEqual((result["class"], result["objective"]),
                         (without["class"], without["objective"]))
        # One infrastructure error among three leaves two trials: it counts.
        runs = flat_cell(5)
        runs[0]["trials"][0] = gates.trial_record(trial(infra=True))
        self.assertEqual(cell(runs[:5], runs[5:])["with"]["runs"], 5)

    def test_errored_trials_are_never_scored_around(self):
        # Round 2's reproducer: the without arm errors in 2 of 5 trials per
        # run. Scored around, only the trials that went well would compare.
        with_runs = series("with", [(80,) * 5] * 20, FLAT_JUDGE)
        without_runs = series("without", [(80,) * 5] * 20, FLAT_JUDGE)
        for run in without_runs:
            run["trials"][:2] = [gates.trial_record(trial(error="agent_failed"))] * 2
        result = cell(with_runs, without_runs)
        self.assertNotEqual(result["class"], "no-benefit")
        self.assertEqual((result["without"]["runs"], result["skipped"]), (20, {}))
        self.assertAlmostEqual(result["objective"]["delta"], 0.32, places=12)

    def test_without_arm_timeouts_censoring_its_failures_cannot_retire(self):
        # Round 3's reproducer (p2.py), paired: twenty-four clean with runs;
        # half the without runs have a timed-out trial. Dropping those runs
        # would leave only the without arm's good runs, level with the skill.
        with_runs = series("with", [(80, 80, 80)] * 24, [7.0, 7.2] * 12, carried=True)
        without_runs = []
        for r in range(24):
            if r % 2:
                trials = [trial(80, T, 3 * r + k, 7.0 + (k - 1) / 10) for k in range(2)] \
                    + [trial(0, T, 0, None, error="timeout")]
                without_runs.append(arm_run("without", trials, r, carried=True))
            else:
                without_runs += series("without", [(80, 80, 80)], [7.0 if r % 4 else 7.2],
                                       start=r, carried=True)
        result = cell(with_runs, without_runs, carried=True)
        self.assertNotEqual(result["class"], "no-benefit")
        self.assertEqual(result["without"]["runs"], 24)

    def test_without_arm_timeouts_can_show_benefit(self):
        def runs(role):
            out = []
            for r in range(12):
                marks = figures(FLAT_JUDGE[r])
                trials = [trial(p, T, 3 * r + k, marks[k]) for k, p in enumerate(FLAT[r])]
                if role == "without":
                    trials[2] = trial(0, T, 0, None, error="timeout")
                out.append(arm_run(role, trials, r))
            return out
        self.assertEqual(cell(runs("with"), runs("without"))["class"], "benefit")

    def test_an_errored_trial_blocks_no_benefit(self):
        # One budget stop in one with run: it scores 0 on every check, and
        # the numbers are still no-benefit.
        runs = flat_cell(FLAT_DECIDES + 2)
        runs[0]["trials"].append(gates.trial_record(trial(error="budget_exceeded")))
        result = cell(runs[:FLAT_DECIDES + 2], runs[FLAT_DECIDES + 2:])
        self.assertTrue(result["reason"].startswith("no-benefit on the numbers"),
                        result["reason"])
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("agent-errored", result["reason"])
        # In-situ guidance cells do not block on an errored trial.
        result = gates.classify_cell(runs[:FLAT_DECIDES + 2], runs[FLAT_DECIDES + 2:],
                                     TEST_POLICY, errored_blocks=False)
        self.assertEqual(result["class"], "no-benefit")

    def test_a_run_without_check_results_keeps_the_cell_from_retiring(self):
        runs = flat_cell(FLAT_DECIDES + 2)
        runs[3]["trials"][0] = gates.trial_record({**trial(), "objective_checks": []})
        result = cell(runs[:FLAT_DECIDES + 2], runs[FLAT_DECIDES + 2:])
        self.assertEqual(result["skipped"], {gates.NO_CHECKS_REASON: 1})
        self.assertEqual(result["class"], "insufficient")

    def test_noisy_runs_are_insufficient(self):
        result = cell(series("with", NOISY, FLAT_JUDGE),
                      series("without", NOISY_BACK, FLAT_JUDGE))
        self.assertEqual(result["class"], "insufficient")

    def test_constant_arms_are_decided(self):
        same = [(80, 80, 80)] * FLAT_DECIDES
        self.assertEqual(cell(series("with", same, FLAT_JUDGE),
                              series("without", same, FLAT_JUDGE))["class"], "no-benefit")
        # Constant and apart: benefit.
        self.assertEqual(cell(series("with", [(90, 90, 90)] * 8),
                              series("without", [(40, 40, 40)] * 8))["class"], "benefit")

    def test_a_without_arm_above_one_minus_the_margin_is_ceiling(self):
        # The review's C2: a without arm above 0.85 cannot show a 0.15 gain,
        # so the cell parks as `ceiling`, but only once the ceiling test (a
        # betting bound on the without arm's mean, at the retire level) says
        # so; round 1's C1: a sample mean over three pairs parked helpful
        # cells for good. A perfect without arm takes 18 pairs.
        same = [(100, 100, 100)] * 30
        result = cell(series("with", same[:17]), series("without", same[:17]))
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("decide whether the cell has headroom", result["reason"])
        result = cell(series("with", same), series("without", same))
        self.assertEqual((result["class"], result["ceiling_at"]), ("ceiling", 18))
        self.assertIs(result["headroom"], False)
        self.assertAlmostEqual(result["without_mean"], 1.0, places=12)
        # The removal test rejected by then; the ceiling still parks it.
        self.assertIsNotNone(result["objective"]["remove_at"])
        self.assertEqual(result["noharm_at"], 18)
        # A without arm at 0.90 is above the floor but too near it for the
        # bound: it never votes, and at `max_runs_high_cell` (20) pairs it
        # stops as `ceiling-unconfirmed` (round 2's M2).
        near = [(90, 90, 90)] * 40
        result = cell(series("with", near[:19]), series("without", near[:19]))
        self.assertEqual(result["class"], "insufficient")
        self.assertIsNotNone(result["objective"]["remove_at"])
        for n in (20, 40):
            self.assertEqual(cell(series("with", near[:n]),
                                  series("without", near[:n]))["class"],
                             "ceiling-unconfirmed")
        # Exactly 1 - margin has headroom.
        edge = [(85, 85, 85)] * 30
        self.assertEqual(cell(series("with", edge), series("without", edge))["class"],
                         "no-benefit")

    def test_a_ceiling_cell_can_still_keep(self):
        # Keep is tested first: a gain shown at the ceiling is a gain.
        result = cell(series("with", [(100, 100, 100)] * 21),
                      series("without", [(90, 90, 90)] * 21))
        self.assertEqual(result["class"], "benefit")

    def test_a_check_failing_everywhere_no_longer_parks_the_cell(self):
        # It adds the same 0 to both arms; the deltas decide (2026-11-03).
        def runs(role):
            return [arm_run(role, [trial(8, 10, fail={9, (3 * r + k) % 9}) for k in range(3)], r)
                    for r in range(5)]
        self.assertNotEqual(cell(runs("with"), runs("without"))["class"], "cannot-discriminate")

    def test_the_floor_needs_floor_min_runs_pairs(self):
        low = [(1, 1, 1), (1, 1, 0)] * 3
        n = POLICY["floor_min_runs"]
        result = cell(series("with", low[:n - 1], total=10),
                      series("without", low[:n - 1], total=10))
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("decide whether the fixture is broken", result["reason"])
        self.assertEqual(cell(series("with", low[:n], total=10),
                              series("without", low[:n], total=10))["class"],
                         "cannot-discriminate")

    def test_both_arms_near_the_floor_cannot_discriminate(self):
        low = [(1, 1, 1), (1, 1, 0)] * 3
        self.assertEqual(cell(series("with", low[:5], total=10),
                              series("without", low[:5], total=10))["class"],
                         "cannot-discriminate")

    def test_insufficient_runs_come_before_cannot_discriminate(self):
        # An arm with no counted run has no pair, even beside an arm at the
        # floor.
        low = [(1, 1, 1), (1, 1, 0)] * 3
        without = series("without", low[:4], total=10)
        for run in without:
            run["trials"] = [gates.trial_record(trial(infra=True))]
        result = cell(series("with", low[:4], total=10), without)
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("no pair", result["reason"])
        self.assertEqual(cell(series("with", low[:4], total=10),
                              series("without", low[:4], total=10))["class"],
                         "cannot-discriminate")

    def test_the_keep_family_raises_the_keep_bar(self):
        # Seven pairs keep a one-cell subject; across a family of 4 cells
        # each test runs at 0.20 / 4 and needs more.
        runs = (series("with", GAIN[:7]), series("without", LOSS[:7]))
        self.assertEqual(cell(*runs)["class"], "benefit")
        result = cell(*runs, family=4)
        self.assertEqual((result["class"], result["keep_family"]), ("insufficient", 4))
        self.assertLess(result["objective"]["keep_p"], 0.2)
        self.assertGreater(result["objective"]["keep_p"], 0.05)
        self.assertEqual(result["keep_tests"],
                         [{"route": "objective", "p": result["objective"]["keep_p"],
                           "log_wealth": result["objective"]["keep_log_wealth"]}])
        self.assertEqual(cell(series("with", GAIN * 2), series("without", LOSS * 2),
                              family=4)["objective"]["keep_at"], 11)

    def test_the_first_test_to_reject_decides(self):
        # Flat pairs reject removal at 18; a later run of gains does not undo
        # it (the decision stands at the first crossing, as Ville's bound is
        # for the stopped sequence).
        with_runs = series("with", FLAT, FLAT_JUDGE) + series("with", [(100,) * 3] * 10,
                                                              start=20)
        without_runs = series("without", FLAT, FLAT_JUDGE) + series(
            "without", [(40,) * 3] * 10, start=20)
        result = cell(with_runs, without_runs)
        self.assertEqual((result["class"], result["objective"]["remove_at"]),
                         ("no-benefit", FLAT_DECIDES))
        self.assertIsNotNone(result["objective"]["keep_at"])

    def test_single_checks_do_not_keep_on_their_own(self):
        # Overall the arms are level; check A is better with the skill and B
        # worse, by the same amount (the review's M1: no per-check route).
        def runs(role):
            out = []
            for r in range(10):
                even = r % 2 == 0
                a, b = ((3, 0) if even else (2, 1)) if role == "with" else \
                    ((0, 3) if even else (1, 2))
                c = 3 if even else 2
                trials = [trial(fail={i for i, n in enumerate((a, b, c)) if k >= n},
                                total=3, overall=7.0) for k in range(3)]
                out.append(arm_run(role, trials, r))
            return out
        result = cell(runs("with"), runs("without"))
        self.assertEqual(result["class"], "insufficient")
        self.assertNotIn("confident_checks", result)
        self.assertEqual([t["route"] for t in result["keep_tests"]], ["objective"])


class JudgeReportTests(unittest.TestCase):
    """The judge is reported and never votes (2026-11-03): no keep and no
    removal reads it."""

    def test_a_judge_gain_alone_does_not_keep(self):
        result = cell(series("with", FLAT, [9.6, 9.4] * 10),
                      series("without", FLAT, [5.0, 5.2] * 10))
        self.assertEqual(result["class"], "no-benefit")
        self.assertIs(result["judge"]["votes"], False)
        self.assertGreaterEqual(result["judge"]["helps_confidence"],
                                POLICY["benefit_confidence"])
        self.assertAlmostEqual(result["judge"]["delta"], 4.4, places=9)

    def test_a_judge_loss_does_not_block_a_keep(self):
        result = cell(series("with", GAIN[:7], [2.0] * 7),
                      series("without", LOSS[:7], [9.0] * 7))
        self.assertEqual(result["class"], "benefit")

    def test_no_judge_figure_does_not_hold_a_removal(self):
        # Before 2026-11-03 a cell that was not judge-carried needed a usable
        # judge to remove (the review's M2).
        runs = flat_cell()
        for run in runs:
            run["trials"] = [{**t, "judge": None} for t in run["trials"]]
        result = cell(runs[:FLAT_DECIDES], runs[FLAT_DECIDES:])
        self.assertEqual((result["class"], result["judge"]), ("no-benefit", None))

    def test_a_conditional_judge_with_a_skipped_call_is_not_reported(self):
        with_runs, without_runs = [series(role, FLAT, FLAT_JUDGE, conditional=True)
                                   for role in ("with", "without")]
        self.assertIsNotNone(cell(with_runs, without_runs)["judge"])
        for runs in (with_runs, without_runs):
            runs[0]["trials"] = [gates.trial_record(trial(skipped=True, offset=k))
                                 for k in range(3)]
        result = cell(with_runs, without_runs)
        self.assertEqual((result["class"], result["judge"]), ("no-benefit", None))

    def test_judge_carried_cells_are_decided_on_their_objective(self):
        # Class C: the objective decides; its judge is reported only.
        result = cell(series("with", [(95, 95, 95), (95, 95, 94)] * 5, [7.0, 7.2] * 5,
                             pairwise=True, carried=True),
                      series("without", [(40, 40, 40), (40, 40, 39)] * 5, [7.0, 7.2] * 5,
                             pairwise=True, carried=True), carried=True)
        self.assertEqual((result["class"], result["judge_carried"]), ("benefit", True))
        result = cell(series("with", FLAT, [8.0, 8.2] * 10, pairwise=True),
                      series("without", FLAT, [6.0, 6.2] * 10, pairwise=True), carried=True)
        self.assertEqual(result["class"], "no-benefit")
        self.assertAlmostEqual(result["judge"]["delta"], 2.0, places=9)


class CapTests(unittest.TestCase):
    """`max_runs_per_cell`: a cell undecided at the cap has no clear effect."""

    def swing(self, n):
        # Pairs alternating +0.1 and -0.1 around a true gain of 0: too noisy
        # to decide fast, then capped.
        up, down = [(90, 90, 90), (70, 70, 70)] * n, [(80, 80, 80)] * (2 * n)
        return series("with", up[:n], cli=None), series("without", down[:n])

    def test_a_cell_at_the_cap_has_no_clear_effect(self):
        policy = {**TEST_POLICY, "max_runs_per_cell": 6}
        result = cell(*self.swing(5), policy=policy)
        self.assertEqual(result["class"], "insufficient")
        result = cell(*self.swing(6), policy=policy)
        self.assertEqual(result["class"], "no-clear-effect")
        self.assertIn("6 pairs and neither test rejected", result["reason"])

    def test_pairs_past_the_cap_do_not_decide(self):
        policy = {**TEST_POLICY, "max_runs_per_cell": 6}
        w, o = self.swing(6)
        late_w = series("with", [(100,) * 3] * 10, start=30)
        late_o = series("without", [(10,) * 3] * 10, start=30)
        result = cell(w + late_w, o + late_o, policy=policy)
        self.assertEqual((result["class"], result["pairs"], result["pairs_used"]),
                         ("no-clear-effect", 16, 6))

    def test_the_cap_needs_min_cli_versions_too(self):
        policy = {**TEST_POLICY, "max_runs_per_cell": 6}
        w = series("with", [(90, 90, 90), (70, 70, 70)] * 3, cli=CLIS[0])
        o = series("without", [(80, 80, 80)] * 6, cli=CLIS[0])
        result = cell(w, o, policy=policy)
        self.assertEqual(result["class"], "insufficient")
        self.assertIn("no clear effect on the numbers, but 1 CLI version(s)",
                      result["reason"])


class VerdictTests(unittest.TestCase):
    MODELS = ["model-a", "model-b", "model-c"]

    def verdict(self, runs, models=None, expected=None):
        return gates.retirement({"runs": runs}, models or self.MODELS, "demo", TEST_POLICY,
                                expected if expected is not None else EXPECT)

    @staticmethod
    def expect(*fixtures, tested="t1", fdig="f1"):
        return {f: {"fixture_digest": fdig, "tested_digest": tested} for f in fixtures}

    def flat(self, model, n=FLAT_DECIDES, **kw):
        return flat_cell(n, model=model, **kw)

    def gain(self, model, **kw):
        # Twenty pairs of about +0.4: a keep across a family of 9 cells.
        return series("with", GAIN * 2, model=model, **kw) + series(
            "without", LOSS * 2, model=model, **kw)

    def ceiling(self, model, **kw):
        same = [(100, 100, 100)] * 18
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

    def test_a_cell_with_too_few_runs_holds_the_verdict(self):
        # One pair short on model-a: insufficient, and so is the verdict.
        others = [r for m in self.MODELS[1:] for r in self.flat(m)]
        result = self.verdict(others + self.flat("model-a", FLAT_DECIDES - 1))
        self.assertEqual(result["verdict"], "insufficient")
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["insufficient", "no-benefit", "no-benefit"])
        self.assertEqual(self.verdict(others + self.flat("model-a"))["verdict"], "retire")

    def test_one_benefit_cell_keeps(self):
        runs = [r for m in self.MODELS[1:] for r in self.flat(m)] + self.gain("model-a")
        self.assertEqual(self.verdict(runs)["verdict"], "keep")

    def test_ceiling_cells_do_not_vote_and_all_ceiling_is_ceiling(self):
        # The review's C2 (2026-11-03): a ceiling cell is parked, never a
        # vote for removal; the other cells decide. Adam, 2026-11-13: every
        # retire is automatic, so the parked cell only shows in the reason.
        runs = [r for m in self.MODELS[1:] for r in self.flat(m)] + self.ceiling("model-a")
        result = self.verdict(runs)
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["ceiling", "no-benefit", "no-benefit"])
        self.assertEqual((result["verdict"], result["removal"]), ("retire", "auto"))
        self.assertIn("parked cell(s) (at the ceiling", result["removal_reason"])
        # Every cell at the ceiling: the subject needs a fixture, and is never
        # removed for it.
        fixtures = ("one", "two")
        runs = [r for m in self.MODELS for f in fixtures for r in self.ceiling(m, fixture=f)]
        result = self.verdict(runs, expected=self.expect(*fixtures))
        self.assertEqual(result["verdict"], "ceiling")
        self.assertNotIn("removal", result)

    def test_a_broken_fixture_cell_is_left_out_of_the_verdict(self):
        runs = self.low("model-a") + self.flat("model-b") + self.flat("model-c")
        result = self.verdict(runs)
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["cannot-discriminate", "no-benefit", "no-benefit"])
        self.assertEqual((result["verdict"], result["reason"], result["removal"]),
                         ("retire", "every cell with headroom shows no benefit (cells "
                                    "parked or with a broken fixture do not vote)",
                          "auto"))

    def test_every_cell_broken_is_cannot_discriminate(self):
        runs = [r for m in self.MODELS for r in self.low(m)]
        self.assertEqual(self.verdict(runs)["verdict"], "cannot-discriminate")

    def test_insufficient_outranks_cannot_discriminate(self):
        runs = self.low("model-a") + self.flat("model-b") + self.flat("model-c", 1)
        result = self.verdict(runs)
        self.assertEqual([c["class"] for c in result["cells"]],
                         ["cannot-discriminate", "no-benefit", "insufficient"])
        self.assertEqual(result["verdict"], "insufficient")

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
        self.assertEqual(len(result["runs_used"]), 2 * FLAT_DECIDES)

    def test_a_skill_with_no_fixture_on_main_is_insufficient(self):
        result = self.verdict(self.flat("model-a"), ["model-a"], {})
        self.assertEqual((result["verdict"], result["cells"]), ("insufficient", []))
        self.assertIn("no fixture", result["reason"])

    def test_the_without_arm_pools_across_skill_content(self):
        runs = (series("with", FLAT, FLAT_JUDGE, tested="new")
                + series("without", FLAT, FLAT_JUDGE, tested="old"))
        self.assertEqual(self.verdict(runs, ["model-a"], self.expect("", tested="new"))
                         ["verdict"], "retire")

    def test_new_skill_content_starts_the_with_arm_over(self):
        old = series("with", FLAT[:10], FLAT_JUDGE, tested="old")
        new = series("with", FLAT[10:11], FLAT_JUDGE[10:11], start=10, tested="new")
        without = series("without", FLAT[:15], FLAT_JUDGE)
        expected = self.expect("", tested="new")
        result = self.verdict(old + without, ["model-a"], expected)
        # No with run of the content on main: nothing to pair the arms on.
        self.assertEqual((result["verdict"], result["cells"][0]["reason"]),
                         ("insufficient",
                          "pooling key incomplete: with_context, without_context"))
        result = self.verdict(old + new + without, ["model-a"], expected)
        self.assertEqual(result["cells"][0]["with"]["runs"], 1)
        self.assertEqual([e["timestamp"] for e in result["cells"][0]["runs"]["with"]],
                         [stamp(10)])

    def test_a_stale_run_of_old_content_does_not_choose_the_pool(self):
        # Ten flat runs of content A, twenty of B (on main), then one late
        # run of A stamped newest. The newest run is not what is current.
        a = series("with", FLAT[:10], FLAT_JUDGE, tested="A")
        b = series("with", FLAT, FLAT_JUDGE, start=10, tested="B")
        stale = series("with", FLAT[:1], FLAT_JUDGE, start=30, tested="A")
        without = series("without", (FLAT * 2)[:31], (FLAT_JUDGE * 2)[:31])
        result = self.verdict(a + b + stale + without, ["model-a"],
                              self.expect("", tested="B"))
        self.assertEqual(result["cells"][0]["with"]["runs"], 20)
        self.assertEqual([e["timestamp"] for e in result["cells"][0]["runs"]["with"]],
                         [stamp(r) for r in range(10, 30)])
        self.assertEqual(result["verdict"], "retire")

    def test_runs_of_another_fixture_or_arm_context_are_not_pooled(self):
        for field in ("fdig", "ctx"):
            with self.subTest(field=field):
                old = series("with", FLAT[:2], FLAT_JUDGE, **{field: "older"})
                new = series("with", FLAT[2:5], FLAT_JUDGE, start=2)
                without = series("without", FLAT[:5], FLAT_JUDGE)
                result = self.verdict(old + new + without, ["model-a"])
                self.assertEqual(result["cells"][0]["with"]["runs"], 3)
                self.assertEqual([e["timestamp"] for e in result["cells"][0]["runs"]["with"]],
                                 [stamp(r) for r in (2, 3, 4)])

    def test_a_moved_fixture_pools_its_flat_runs_only_with_the_same_digest(self):
        # #422/#427: a flat fixture nested as `nested`, content unchanged.
        # Its old runs (fixture None) pool with the new name; a run of other
        # content under the old name does not.
        old = (series("with", FLAT[:10], FLAT_JUDGE)
               + series("without", FLAT[:10], FLAT_JUDGE))
        new = (series("with", FLAT[10:], FLAT_JUDGE, start=10, fixture="nested")
               + series("without", FLAT[10:], FLAT_JUDGE, start=10, fixture="nested"))
        stale = series("with", FLAT[:3], FLAT_JUDGE, start=30, fdig="older")
        with mock.patch.dict(gates.FIXTURE_ALIASES, {("demo", ""): "nested"}):
            result = self.verdict(old + new + stale, ["model-a"], self.expect("nested"))
            mismatched = self.verdict(old, ["model-a"], self.expect("nested", fdig="changed"))
        self.assertEqual(result["verdict"], "retire")
        self.assertEqual((result["cells"][0]["fixture"], result["cells"][0]["with"]["runs"],
                          result["cells"][0]["without"]["runs"]), ("nested", 20, 20))
        self.assertEqual(len(result["runs_used"]), 40)
        # Old content is a fixture no longer on main: the cell has no run.
        self.assertEqual((mismatched["cells"][0]["class"], mismatched["cells"][0]["runs"]),
                         ("missing", {"with": [], "without": []}))
        # Without the alias the old runs belong to a fixture no longer on main.
        plain = self.verdict(old + new, ["model-a"], self.expect("nested"))
        self.assertEqual(len(plain["cells"][0]["runs"]["with"]), 10)

    def test_the_declared_fixture_aliases_point_at_nested_fixtures_on_main(self):
        self.assertTrue(gates.FIXTURE_ALIASES)
        for (skill, old), new in gates.FIXTURE_ALIASES.items():
            with self.subTest(skill=skill):
                self.assertFalse((ROOT / "evals" / skill / old / "fixture.yaml").exists())
                self.assertTrue((ROOT / "evals" / skill / new / "fixture.yaml").is_file())
                # A target taken off the schedule (unscheduled.yml) is not expected.
                unscheduled = {row["path"] for row in yaml.safe_load(
                    (ROOT / "evals/unscheduled.yml").read_text(encoding="utf-8"))["fixtures"]}
                if f"evals/{skill}/{new}" not in unscheduled:
                    self.assertIn(new, compute_gates.expected_content(ROOT / "evals", skill, {}))

    def test_the_arms_are_paired_on_one_guidance_and_skill_set(self):
        # Round 5's reproducer (test_ctx.py): twenty without runs from old
        # guidance G1, then fifteen of each arm from new guidance G2, which
        # lowers both arms; the skill still adds 0.1. Pooled independently,
        # the without arm took G1's runs (it had the most), and the cell
        # compared G2 with against G1 without: retire. Chosen jointly, only
        # G2 with G2 counts, and only G2's fires pair.
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
                          mixed["cells"][0]["without"]["runs"],
                          mixed["cells"][0]["unpaired"]), (15, 15, 5))

    def test_no_shared_pair_or_a_tie_is_insufficient(self):
        unpaired = (series("with", FLAT[:10], FLAT_JUDGE, pair="others:G2")
                    + series("without", FLAT[:10], FLAT_JUDGE, pair="others:G1"))
        result = self.verdict(unpaired, ["model-a"])
        self.assertEqual(result["verdict"], "insufficient")
        self.assertIn("pooling key incomplete", result["cells"][0]["reason"])
        # No pair key at all (a summary from before others_digest).
        result = self.verdict(flat_cell(pair=None), ["model-a"])
        self.assertEqual(result["verdict"], "insufficient")
        # Two pairs with as many runs in their smaller arms: the one with the
        # newer runs (Adam, 2026-11-01), and neither only when that ties too.
        tie = (flat_cell(6, pair="others:G1")
               + series("with", FLAT[:6], FLAT_JUDGE, start=40, ctx="w2", pair="others:G2")
               + series("without", FLAT[:6], FLAT_JUDGE, start=40, ctx="o2",
                        pair="others:G2"))
        self.assertEqual(self.verdict(tie, ["model-a"])["cells"][0]["key"]["with_context"],
                         "w2")
        full_tie = (series("with", FLAT[:6], FLAT_JUDGE, start=40, ctx="w1", pair="others:G1")
                    + series("without", FLAT[:6], FLAT_JUDGE, start=40, ctx="o1",
                             pair="others:G1")
                    + series("with", FLAT[:6], FLAT_JUDGE, start=40, ctx="w2",
                             pair="others:G2")
                    + series("without", FLAT[:6], FLAT_JUDGE, start=40, ctx="o2",
                             pair="others:G2"))
        self.assertEqual(self.verdict(full_tie, ["model-a"])["cells"][0]["key"]["with_context"],
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

    def test_one_trial_runs_count_and_are_decided_like_any_other(self):
        # Round 5, N1: the weekly sweep fires one trial per run. Such a run
        # counts, and is decided on its run figures at any count.
        one = [(80,), (79,)] * 10
        judges = [7.0, 7.2] * 10

        def runs(n, with_judges=judges):
            return (series("with", one[:n], with_judges[:n], spread=False)
                    + series("without", one[:n], judges[:n], spread=False))
        for n, want in ((FLAT_DECIDES - 1, "insufficient"), (FLAT_DECIDES, "no-benefit"),
                        (20, "no-benefit")):
            with self.subTest(n=n):
                result = cell(*(lambda r: (r[:n], r[n:]))(runs(n)), carried=True)
                self.assertEqual(result["class"], want, result["reason"])
                self.assertEqual(result["with"]["runs"], n)
        # Its pairs are the run-level differences, every one 0.
        result = cell(*(lambda r: (r[:20], r[20:]))(runs(20)), carried=True)
        self.assertEqual(result["objective"]["delta"], 0.0)
        self.assertLess(result["objective"]["retire_upper"], TEST_POLICY["objective_margin"])
        # Equal judge figures in every one-trial run of an arm are decided:
        # no spread is required (2026-10-31).
        flat = runs(20, [7.0] * 20)
        result = cell(flat[:20], flat[20:], carried=True)
        self.assertEqual(result["class"], "no-benefit", result["reason"])

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
        self.assertEqual(len(c["runs"]["with"]), FLAT_DECIDES)
        entry = c["runs"]["with"][0]
        self.assertEqual(entry["run"], {"id": stamp(0)})
        self.assertEqual(entry["report"]["url"],
                         "https://github.com/Adam-S-Daniel/skills-evals/blob/"
                         "persistent/eval-results/" + entry["report"]["path"])
        self.assertAlmostEqual(c["cost_usd"], 2 * FLAT_DECIDES * 3 * 0.25, places=12)
        self.assertEqual(len(result["runs_used"]), 2 * FLAT_DECIDES)
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
                   fixture=None, checks=True, without_patterns=None):
    """Both arms of each run, laid out as routine-results; the without arm
    repeats `patterns` and `judges` unless `without_patterns` and
    `without_judges` give its own. Without `checks`
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
            own = pattern if role == "with" or without_patterns is None \
                else without_patterns[i]
            for k, passed in enumerate(own):
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


class ComputeGatesTests(unittest.TestCase):
    """The committed policy on fixtures whose trials report objective checks:
    the cells are decided on the objective, and the judge is reported only
    (2026-11-03). `checks=False` writes judge-only trials."""
    SKILLS = ("flat", "gain", "unasked", "one", "two", "guidancebot")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tree = self.tmp / "tree"
        self.roster = self.tmp / "roster.yml"
        self.roster.write_text("arms:\n  - id: model-a\n", encoding="utf-8")
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
              model="model-a", **kw):
        directory = self.evals / skill / (fixture or "")
        run_ids = write_arm_runs(self.tree, skill, model, patterns, judges, fixture=fixture,
                                 tested=tested or self.digest_of(skill),
                                 fdig=run_eval.fixture_digest(directory), **kw)
        return run_ids


    def run_gates(self, name, registry=True, as_of=AS_OF, policy_file=None):
        out = self.tmp / name
        args = ["--results-tree", str(self.tree), "--roster", str(self.roster),
                "--policy", str(policy_file or POLICY_FILE), "--evals-dir", str(self.evals),
                "--as-of", as_of, "--out", str(out)]
        if registry:
            args += ["--registry", f"adam-agentskills={self.registry}"]
        self.assertEqual(compute_gates.main(args), 0)

        def refuse(value):
            raise ValueError(value)
        return out, json.loads(out.read_text(encoding="utf-8"), parse_constant=refuse)

    def edit(self, path, change):
        """Rewrite the JSON at `path`."""
        doc = json.loads(path.read_text(encoding="utf-8"))
        change(doc)
        path.write_text(json.dumps(doc), encoding="utf-8")

    def test_output_is_deterministic(self):
        self.write("flat", FLAT, FLAT_JUDGE)
        first, _ = self.run_gates("a.json")
        second, _ = self.run_gates("b.json")
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_one_trial_runs_count(self):
        """A one-trial run's arm summary IS its trial, with `n: 1`, no
        aggregate and no trial files (harness/run_eval.py, "Fixture
        layout"). Every routine run fired with trials 1 was once skipped as
        "no aggregate block", so no gate saw it (2026-10-31)."""
        self.write("one", [[80]] * 3, [8.0] * 3)
        for arm in sorted(self.tree.glob("routine-results/*/one/*/*_skill")):
            outer = json.loads((arm / "summary.json").read_text(encoding="utf-8"))
            inner = json.loads((arm / "trial-1" / "summary.json").read_text(
                encoding="utf-8"))
            shutil.rmtree(arm / "trial-1")
            for field in ("aggregate", "errors"):
                outer.pop(field)
            write_json(arm / "summary.json", {**outer, **inner, "n": 1})
        index = compute_gates.build_index(self.tree, self.evals, AS_OF)
        mine = [r for r in index["runs"] if r["skill"] == "one"]
        self.assertEqual(sorted(r["role"] for r in mine), ["with"] * 3 + ["without"] * 3)
        self.assertTrue(all(len(r["trials"]) == 1 and r["trials"][0]["scored"]
                            for r in mine))
        self.assertEqual(index["skipped"], {"no aggregate block": 1})
        # Only `n` 1 with no trial files is a trial; `n` 2 still needs its
        # aggregate, and so does a summary beside trial files.
        arms = sorted(self.tree.glob("routine-results/*/one/*/*_skill"))
        self.edit(arms[0] / "summary.json", lambda d: d.update(n=2))
        self.edit(arms[1] / "summary.json", lambda d: d.update(n=True))
        write_json(arms[2] / "trial-1" / "summary.json",
                   json.loads((arms[2] / "summary.json").read_text(encoding="utf-8")))
        index = compute_gates.build_index(self.tree, self.evals, AS_OF)
        self.assertEqual(len([r for r in index["runs"] if r["skill"] == "one"]), 3)
        self.assertEqual(index["skipped"], {"no aggregate block": 4})

    def test_verdicts_links_and_skips(self):
        self.write("flat", FLAT, FLAT_JUDGE)
        # One fixture per routine run id, as the fire workflow makes them.
        self.write("gain", GAIN, [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5,
                   model_tag="b", without_patterns=LOSS)
        self.write("unasked", FLAT, FLAT_JUDGE, requested=False, model_tag="c")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        self.assertEqual(doc["skills"]["gain"]["verdict"], "keep")
        self.assertEqual(doc["skills"]["unasked"]["verdict"], "insufficient")
        self.assertEqual(doc["skipped"], {"no aggregate block": 1,
                                          "no requested arm model": 40})
        self.assertEqual((doc["roster_models"], doc["as_of"]), (["model-a"], AS_OF))
        entry = doc["skills"]["flat"]["cells"][0]["runs"]["with"][0]
        self.assertEqual(entry["run"]["billing"], "api")
        self.assertTrue((self.tree / entry["report"]["path"]).is_file())
        self.assertEqual(doc["retirement_mode"], "auto")
        self.assertNotIn("previous", doc)

    def in_place_fixture(self, skill):
        """A fixture on main that runs in place (a top-level `context`
        mapping, ADR 0012), tracked in Git, with its registry copy."""
        directory = self.evals / skill
        directory.mkdir(parents=True)
        (directory / "fixture.yaml").write_text(
            f"skill: {skill}\nprompt: p\ncontext:\n  repository: example/repo\n",
            encoding="utf-8")
        self._skill(skill, "body")
        subprocess.run(["git", "add", "-A"], cwd=self.evals.parent, check=True)

    def bare(self, skill, r, *, model_tag="z", pairing=None):
        """A one-arm run: only `without_skill`. With no `pairing` it is an
        isolation arm, with no context blocks, as a bare fire (`arms: bare`,
        ADR 0012's 2026-10-27 addendum) leaves it."""
        (run_id,) = self.write(skill, FLAT[:1], FLAT_JUDGE, start=r, model_tag=model_tag)
        base = self.tree / "routine-results" / run_id / skill / stamp(r)
        shutil.rmtree(base / "with_skill")

        def change(doc):
            if pairing is None:
                for key in ("arm_context", "context", "context_subject"):
                    doc.pop(key)
            else:
                doc["pairing"] = pairing
        self.edit(base / "without_skill" / "summary.json", change)
        return run_id, base

    def test_a_bare_run_is_reported_apart_and_never_pooled(self):
        self.in_place_fixture("ctxbot")
        run_id, base = self.bare("ctxbot", 40)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["bare_runs"], [{
            "skill": "ctxbot", "fixture": None, "model": "model-a", "timestamp": stamp(40),
            "path": f"routine-results/{run_id}/ctxbot/{stamp(40)}",
            "report": gates._link(f"routine-results/{run_id}/ctxbot/{stamp(40)}/report.md")}])
        cell = doc["skills"]["ctxbot"]["cells"][0]
        # Pooled, it would be the cell's `without` arm and put the cell on
        # its model; set apart, the cell still has no run at all.
        self.assertEqual((cell["class"], cell["runs"]), ("missing", {"with": [], "without": []}))
        self.assertEqual(doc["skills"]["ctxbot"]["runs_used"], [])
        self.assertIsNone(doc["newest_run"])
        # Its in-place pairs are decided as before, the bare run beside them.
        self.write("ctxbot", FLAT[:10], FLAT_JUDGE)
        _, with_bare = self.run_gates("b.json")
        shutil.rmtree(base.parent.parent)
        _, without_bare = self.run_gates("c.json")
        # The verdict is the same; only the discarded-runs report and the
        # run-utility ledger name it.
        bare_discards = with_bare["skills"]["ctxbot"].pop("discarded_runs")
        without_bare["skills"]["ctxbot"].pop("discarded_runs")
        bare_ledger = with_bare["skills"]["ctxbot"].pop("run_utility")
        without_bare["skills"]["ctxbot"].pop("run_utility")
        self.assertEqual([r["reason"] for r in bare_ledger if r["reason"]], ["bare_run"])
        self.assertEqual(with_bare["skills"], without_bare["skills"])
        self.assertEqual(bare_discards["by_reason"]["bare_run"]["runs"], 1)
        self.assertEqual(len(with_bare["bare_runs"]), 1)
        self.assertEqual(without_bare["bare_runs"], [])

    def test_only_a_lone_isolation_without_arm_on_an_in_place_fixture_is_bare(self):
        self.in_place_fixture("ctxbot")
        # An in-place summary is in-place evidence, alone or not.
        self.bare("ctxbot", 41, model_tag="y", pairing="in_place")
        # A fixture with no `context` mapping: its isolation `without` arm
        # is an ordinary run, as before.
        self.bare("one", 42, model_tag="x")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["bare_runs"], [])
        for skill in ("ctxbot", "one"):
            with self.subTest(skill=skill):
                cell = doc["skills"][skill]["cells"][0]
                self.assertEqual(cell["class"], "insufficient")
        self.assertEqual(len(doc["skills"]["one"]["cells"][0]["runs"]["without"]), 1)
        # A `with` arm beside it makes it a pair, even an unreadable one.
        run_id, base = self.bare("ctxbot", 43, model_tag="w")
        write_json(base / "with_skill" / "summary.json", {"skill": "ctxbot"})
        index = compute_gates.build_index(self.tree, self.evals, AS_OF)
        self.assertEqual(index["bare_runs"], [])
        self.assertIn(f"routine-results/{run_id}/ctxbot/{stamp(43)}",
                      {r["path"] for r in index["runs"]})
        # After as-of, a bare run is not read either.
        self.bare("ctxbot", 44, model_tag="v")
        index = compute_gates.build_index(self.tree, self.evals, stamp(43))
        self.assertEqual((index["bare_runs"], index["skipped"].get("after as-of")), ([], 1))
        self.assertEqual(len(compute_gates.build_index(self.tree, self.evals,
                                                       AS_OF)["bare_runs"]), 1)

    def test_the_verdict_is_retaken_on_every_pair(self):
        # No fixed looks (2026-10-31): the verdict is retaken on every run,
        # since the betting bound holds at every pair count. On the committed
        # policy, seventeen flat pairs leave the remove test short of its
        # level and the eighteenth crosses it.
        self.write("flat", FLAT[:FLAT_DECIDES - 1], FLAT_JUDGE)
        _, doc = self.run_gates("1.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        cell_ = doc["skills"]["flat"]["cells"][0]
        self.assertGreaterEqual(cell_["objective"]["retire_upper"],
                                POLICY["objective_margin"])
        self.write("flat", FLAT[FLAT_DECIDES - 1:FLAT_DECIDES],
                   FLAT_JUDGE[FLAT_DECIDES - 1:FLAT_DECIDES], start=FLAT_DECIDES - 1)
        _, doc = self.run_gates("2.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        self.assertEqual(doc["skills"]["flat"]["cells"][0]["with"]["runs"], FLAT_DECIDES)

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


    def test_a_run_stamped_after_as_of_is_not_read(self):
        self.write("flat", FLAT, FLAT_JUDGE)
        later = "20261002T073000Z"
        run = self.tree / "routine-results" / f"{stamp(30)}-f00000" / "flat" / later
        shutil.copytree(self.tree / "routine-results" / f"{stamp(0)}-a00000" / "flat"
                        / stamp(0), run)
        for role in ("with", "without"):
            self.edit(run / f"{role}_skill" / "summary.json",
                      lambda d: d["arm_context"].update(skills_digest="later"))
            for k in (1, 2, 3):
                self.edit(run / f"{role}_skill" / f"trial-{k}" / "summary.json",
                          lambda d, c={"with": 0.75, "without": 0.85}[role]:
                          d["agent"].update(cost_usd=c))
        _, doc = self.run_gates("a.json", as_of="20261002T062000Z")
        # Not a duplicate (its bytes are its own), so only as-of keeps it out.
        self.assertEqual((doc["skipped"].get("after as-of"),
                          doc["skipped"].get("duplicate arm run")), (2, None))
        self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 40)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")
        # Read, it is one run against twenty: the context with the most runs
        # is chosen, so the verdict stands.
        _, doc = self.run_gates("b.json", as_of=later)
        self.assertNotIn("after as-of", doc["skipped"])
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


    def test_a_copy_is_counted_once(self):
        self.write("flat", FLAT[:10], FLAT_JUDGE)
        _, before = self.run_gates("a.json")
        for run in sorted((self.tree / "routine-results").iterdir()):
            copy = run.name.replace("-a0000", "-e0000")
            self.copy_run(run.name, copy, reserialize=True)
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
                for path in edited(copy / "flat" / timestamp):
                    self.edit(path, lambda d: d.update(copied=True))
                _, doc = self.run_gates("a.json")
                self.assertEqual(doc["skipped"]["duplicate arm run"], 2)
                self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 20)
                shutil.rmtree(copy)

    def test_a_skill_whose_name_starts_with_guidance_is_evaluated(self):
        self.write("guidancebot", FLAT, FLAT_JUDGE)
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["guidancebot"]["raw_verdict"], "retire")

    def test_without_a_registry_every_cell_is_insufficient(self):
        self.write("flat", FLAT, FLAT_JUDGE)
        _, doc = self.run_gates("a.json", registry=False)
        verdict = doc["skills"]["flat"]
        self.assertEqual(verdict["verdict"], "insufficient")
        self.assertIn("tested_digest", verdict["cells"][0]["reason"])

    def test_runs_of_other_skill_content_do_not_count(self):
        self.write("flat", FLAT, FLAT_JUDGE)
        self._skill("flat", "changed on main")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "insufficient")
        self.assertEqual(doc["skills"]["flat"]["cells"][0]["runs"]["with"], [])

    def test_cells_come_from_the_fixtures_on_main(self):
        self.write("adrs", FLAT, FLAT_JUDGE, fixture="a")
        _, doc = self.run_gates("a.json")
        verdict = doc["skills"]["adrs"]
        self.assertEqual(verdict["verdict"], "insufficient")
        self.assertEqual([(c["fixture"], c["class"]) for c in verdict["cells"]],
                         [("a", "no-benefit"), ("b", "missing"), ("c", "missing"),
                          ("d", "missing")])

    def test_crafted_summaries_are_skipped_never_a_crash(self):
        self.write("flat", (FLAT * 2)[:22], FLAT_JUDGE * 2)
        runs = sorted((self.tree / "routine-results").iterdir())
        trial_path = runs[0] / "flat" / stamp(0) / "with_skill" / "trial-1" / "summary.json"
        self.edit(trial_path, lambda d: d.update(objective_checks=5))
        nan_path = runs[1] / "flat" / stamp(1) / "with_skill" / "trial-1" / "summary.json"
        nan_path.write_text(nan_path.read_text(encoding="utf-8").replace(
            '"cost_usd": 0.25', '"cost_usd": NaN'), encoding="utf-8")
        for k in (1, 2, 3):
            self.edit(runs[2] / "flat" / stamp(2) / "without_skill" / f"trial-{k}"
                      / "summary.json", lambda d: d["agent"].update(cost_usd=1e308))
        self.edit(runs[3] / "flat" / stamp(3) / "with_skill" / "summary.json",
                  lambda d: d.update(fixture_digest=["not", "a", "digest"]))
        self.edit(runs[4] / "flat" / stamp(4) / "with_skill" / "summary.json",
                  lambda d: d.update(role=["with"]))
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"], {"malformed trial summary": 1,
                                          "unreadable trial summary": 1,
                                          "malformed arm summary": 2,
                                          "no aggregate block": 1})
        self.assertIsNone(doc["skills"]["flat"]["cells"][0]["cost_usd"])
        # A pair is the unit: the four refused with arms leave their without
        # arms counted but unpaired, and eighteen pairs decide.
        self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 40)
        self.assertEqual((doc["skills"]["flat"]["cells"][0]["with"]["runs"],
                          doc["skills"]["flat"]["cells"][0]["without"]["runs"],
                          doc["skills"]["flat"]["cells"][0]["unpaired"]), (18, 18, 4))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def test_the_verdict_reads_the_roster_it_is_given(self):
        # The roster follows current use (2026-10-25): a superseded model
        # leaves it at once. Its runs, a clear gain here, then count toward
        # nothing, and no evidence is asked of it.
        self.write("flat", FLAT, FLAT_JUDGE)
        self.write("flat", GAIN, [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5,
                   model="model-old", model_tag="c", start=50, without_patterns=LOSS)
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
        self.write("flat", FLAT, FLAT_JUDGE)
        self.write("flat", FLAT, FLAT_JUDGE, model="model-b", model_tag="b")
        self.roster.write_text("arms:\n  - id: model-a\n  - id: model-b\n",
                               encoding="utf-8")
        _, doc = self.run_gates("a.json")
        self.assertNotIn("duplicate arm run", doc["skipped"])
        self.assertEqual(len(doc["skills"]["flat"]["runs_used"]), 80)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    # -- round 3: an empty roster ---------------------------------------------

    def test_an_empty_or_malformed_roster_exits_2(self):
        self.write("flat", FLAT, FLAT_JUDGE)
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


    def test_trial_files_must_be_one_to_n_and_agree_with_the_arm_summary(self):
        self.write("flat", FLAT, FLAT_JUDGE)
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


    def set_context(self, run_ids, context, **arm_context):
        for run_id in run_ids:
            for path in (self.tree / "routine-results" / run_id).rglob("*_skill/summary.json"):
                self.edit(path, lambda d: d["arm_context"].update(
                    skills_digest=context + d["role"], **arm_context))

    def test_no_single_run_chooses_the_context(self):
        # Round 4's reproducer (test_p1): ten runs that show a gain, then
        # five later flat ones with another arm context. The newest run's
        # context once chose the pool, leaving only the later runs.
        self.write("gain", GAIN, [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5,
                   model_tag="b", without_patterns=LOSS)
        _, real = self.run_gates("a.json")
        self.assertEqual(real["skills"]["gain"]["verdict"], "keep")
        later = self.write("gain", FLAT[:5], FLAT_JUDGE, start=40, model_tag="f")
        self.set_context(later, "later-")
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
        off = self.write("flat", FLAT, FLAT_JUDGE, start=40, model_tag="b",
                         model="model-z")
        self.set_context(off, "off-")
        _, doc = self.run_gates("b.json")
        self.assertEqual(doc["skills"]["flat"]["cells"][0]["key"],
                         alone["skills"]["flat"]["cells"][0]["key"])
        self.assertEqual(doc["skills"]["flat"]["runs_used"],
                         alone["skills"]["flat"]["runs_used"])


    def test_judge_figures_whose_variance_underflows_do_not_crash(self):
        # Round 4's reproducer (test_p5): judge figures around 1e-100 squared
        # to 0 in the old Welch-Satterthwaite denominator (ZeroDivisionError);
        # the moderated variance's prior keeps every bound finite.
        run_ids = self.write("flat", FLAT, FLAT_JUDGE)
        for run_id in run_ids:
            for path in (self.tree / "routine-results" / run_id).rglob("trial-*/summary.json"):
                k = int(path.parent.name.split("-")[1])
                bump = 1e-100 if "with_skill" in path.parts and run_id[-1] in "13579" else 0
                self.edit(path, lambda d, v=(k - 1) * 1e-100 + bump:
                          d["judge"].update(overall=v))
        _, doc = self.run_gates("a.json")
        # Decided, not caught: the judge figures are reported only, and the
        # objective is flat. One cell with headroom still retires, automatically.
        flat = doc["skills"]["flat"]
        self.assertEqual((flat["verdict"], flat["reason"], flat["removal"]),
                         ("retire", "the one cell with headroom shows no benefit",
                          "auto"))
        self.assertTrue(all(math.isfinite(v) for v in
                            (flat["cells"][0]["judge"]["benefit_lower"],
                             flat["cells"][0]["judge"]["retire_upper"])))

    def test_one_skills_failure_is_its_own(self):
        from unittest import mock
        self.write("flat", FLAT, FLAT_JUDGE)
        self.write("gain", GAIN, [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5,
                   model_tag="b", without_patterns=LOSS)
        real = gates.retirement

        def failing(index, models, skill, policy, expected, *args, **kw):
            if skill == "gain":
                raise ZeroDivisionError("a message that is not reported")
            return real(index, models, skill, policy, expected, *args, **kw)
        with mock.patch.object(gates, "retirement", failing):
            _, doc = self.run_gates("a.json")
        gain = doc["skills"]["gain"]
        self.assertEqual((gain["verdict"], gain["cells"], gain["runs_used"], gain["reason"]),
                         ("insufficient", [], [], "the verdict raised ZeroDivisionError"))
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")


    def test_a_results_copy_of_a_routine_run_counts_once(self):
        # The same run ingested under both trees is one run of its cell.
        self.write("flat", FLAT, FLAT_JUDGE)
        run_id = f"{stamp(0)}-a00000"
        source = self.tree / "routine-results" / run_id / "flat" / stamp(0)
        shutil.copytree(source, self.tree / "results" / "flat" / stamp(0))
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skipped"]["duplicate arm run"], 2)
        used = doc["skills"]["flat"]["runs_used"]
        self.assertEqual(len(used), 40)
        self.assertEqual(sum(k.startswith("results/") for k in used), 2)
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

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
        self.write("flat", FLAT, FLAT_JUDGE)
        self.write("gain", GAIN, [8.5, 8.7] * 5, without_judges=[6.0, 6.2] * 5,
                   model_tag="b", without_patterns=LOSS)
        real = gates.retirement

        def failing(index, models, skill, policy, expected, *args, **kw):
            if skill == "gain":
                raise MemoryError
            return real(index, models, skill, policy, expected, *args, **kw)
        with mock.patch.object(gates, "retirement", failing):
            _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["gain"]["reason"], "the verdict raised MemoryError")
        self.assertEqual(doc["skills"]["flat"]["verdict"], "retire")

    def test_arms_of_other_skill_sets_are_not_paired(self):
        # compute_gates' pair key: arm_context.others_digest and the frozen
        # guidance, both arms alike.
        run_ids = self.write("flat", FLAT, FLAT_JUDGE)
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
        self.write("one", FLAT, FLAT_JUDGE)
        self.write("two", (FLAT * 2)[:21], FLAT_JUDGE * 2, model_tag="b")
        _, doc = self.run_gates("a.json")
        self.assertEqual(doc["skills"]["two"]["verdict"], "retire")
        self.assertEqual(doc["skills"]["one"]["verdict"], "retire-pending")
        self.assertEqual(doc["skills"]["one"]["raw_verdict"], "retire")

    # --- Round 6 -----------------------------------------------------------


class ExpectedContentSkipTests(unittest.TestCase):
    """expected_content leaves out a fixture listed in evals/unscheduled.yml
    and a `draft: true` one (Adam, 2026-11-02); everything else is expected."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.evals = self.tmp / "evals"
        for name, extra in (("kept", ""), ("listed", ""), ("drafty", "draft: true\n")):
            directory = self.evals / "demo" / name
            directory.mkdir(parents=True)
            (directory / "fixture.yaml").write_text(
                f"skill: demo\nprompt: p\n{extra}", encoding="utf-8")

    def write(self, text):
        (self.evals / "unscheduled.yml").write_text(text, encoding="utf-8")

    def test_a_listed_fixture_and_a_draft_are_skipped_and_the_rest_kept(self):
        self.write("fixtures:\n  - path: evals/demo/listed\n    reason: Example reason.\n")
        self.assertEqual(sorted(compute_gates.expected_content(self.evals, "demo", {})), ["kept"])

    def test_no_unscheduled_file_expects_every_non_draft_fixture(self):
        self.assertEqual(sorted(compute_gates.expected_content(self.evals, "demo", {})),
                         ["kept", "listed"])

    def test_a_malformed_unscheduled_file_fails_closed(self):
        for text in ("fixtures: [", "- just\n- a list\n", "fixtures: nope\n",
                     "fixtures:\n  - reason: no path\n"):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaises(ValueError):
                    compute_gates.expected_content(self.evals, "demo", {})


class ConfidenceReachedTests(unittest.TestCase):
    """The display level the explorer page shows: 1 - 1 / the largest wealth
    a test has reached, which is exactly the level at which it would have
    rejected (Ville)."""

    def test_the_test_rejects_at_the_level_reached(self):
        ds = [0.4, 0.3, 0.5, 0.4, 0.4]
        wealth = gates.keep_wealth(ds)
        level = gates.reached(wealth)
        self.assertTrue(0 < level < 1)
        # A hair under the level reached rejects; a hair over does not.
        self.assertIsNotNone(gates.first_crossing(wealth, (1 - level) * (1 + 1e-9)))
        self.assertIsNone(gates.first_crossing(wealth, (1 - level) * (1 - 1e-6)))
        self.assertAlmostEqual(gates.ville_p(wealth), 1 - level, places=12)

    def test_the_wrong_side_reaches_no_confidence(self):
        self.assertEqual(gates.reached(gates.keep_wealth([-0.4] * 5)), 0.0)
        self.assertEqual(gates.reached(gates.keep_wealth([0.0] * 5)), 0.0)
        self.assertEqual(gates.reached(gates.remove_wealth([0.5] * 5, 0.15)), 0.0)
        self.assertEqual(gates.ville_p(gates.keep_wealth([])), 1.0)

    def test_more_runs_raise_it(self):
        one = gates.reached(gates.keep_wealth([0.4] * 2))
        four = gates.reached(gates.keep_wealth([0.4] * 6))
        self.assertLess(one, four)


if __name__ == "__main__":
    unittest.main()
