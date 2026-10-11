#!/usr/bin/env python3
"""Conditional judging (#371 items 1 and 2): the judge is not called for a
with/without pair whose objective result already decides it.

For a pair (`--arm both`, or a guidance run of exactly one `with` and one
`without` arm) no judge call is made while trials run. Once every trial of
both arms is scored, the arms' objective pass rates (checks passed over
checks scored, over the trials whose `error` is null) are compared exactly:
`with` strictly ahead skips the judge for every scored trial of the pair and
records `{"status": "skipped", "reason": "objective-decided"}`; a tie, a loss
or an undefined rate judges every scored trial of both arms. A single-arm
run, `--judge always` and a fixture whose judge mode is not absolute judge
each trial in place, as before. `--no-judge` judges nothing and records null.

Hermetic: the CLI is test/fake-claude, directly or through test_issue_66's
scripted stand-in, which counts the judge calls a run makes. No test sleeps,
reads the clock or touches the network.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE = TEST_DIR / "fake-claude"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_issue_66 import (TS, _HarnessCase, _child_env,  # noqa: E402
                           _write_fixture)
from test_issue_97 import make_guidance_checkout  # noqa: E402

sys.path.insert(0, str(HARNESS_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import ingest_routine_results as ingest  # noqa: E402
import make_badge  # noqa: E402
import run_eval  # noqa: E402

SKILL = "conditional-skill"
SKIPPED = {"status": "skipped", "reason": "objective-decided"}
SKIPPED_AGGREGATE = {**SKIPPED, "n": 0, "errors": 0, "overall": None,
                     "dimensions": []}
CELL = "skipped (objective-decided)"
#: An agent step that writes the file the fixture's second check wants: the
#: arm passes 2 of 2 checks. A bare step passes 1 of 2.
GAIN = {"write": "marker.txt"}
BARE = {}


def judge_steps(count: int) -> list:
    return [{"overall": 7.0}] * count


class PairCase(_HarnessCase):
    """`--arm both` runs of one flat fixture against the scripted CLI."""

    def setUp(self):
        super().setUp()
        self.fixture_dir = _write_fixture(self.evals / SKILL, SKILL)
        self.registry = self._registry(SKILL)

    def both(self, agents: list, judges: list | None = None, *flags: str,
             arm: str = "both"):
        self._script(agents=agents, judges=judges or [])
        return self._run(self.fixture_dir, "--arm", arm,
                         "--registry", f"adam-agentskills={self.registry}",
                         "--timestamp", TS, *flags)

    def trial_summaries(self, trials: int) -> dict:
        """Every trial summary of the run, by arm."""
        out = {}
        for arm in ("with_skill", "without_skill"):
            base = self.results / SKILL / TS / arm
            paths = ([base / "summary.json"] if trials == 1 else
                     [base / f"trial-{k}" / "summary.json"
                      for k in range(1, trials + 1)])
            out[arm] = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
        return out

    def arm_summary(self, arm: str) -> dict:
        return self._json(SKILL, TS, arm, "summary.json")

    def report(self) -> str:
        return (self.results / SKILL / TS / "report.md").read_text(encoding="utf-8")

    def kinds(self) -> list[str]:
        return [c["kind"] for c in self._calls()]

    def results_files(self) -> dict:
        return {p.relative_to(self.results).as_posix():
                json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(self.results.rglob("summary.json"))}


class GainSkipsTests(PairCase):

    def gain(self, trials: int):
        proc = self.both([GAIN] * trials + [BARE] * trials, [],
                         "--trials", str(trials))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self._calls("judges"), [])
        return self.trial_summaries(trials)

    def test_one_trial_gain_skips_both_arms(self):
        found = self.gain(1)
        for arm, summaries in found.items():
            with self.subTest(arm=arm):
                (summary,) = summaries
                self.assertEqual(summary["judge"], SKIPPED)
                self.assertEqual(summary["judge_models_used"], [])
                self.assertEqual(
                    summary["usage"]["measured"]["judge"]["calls"], 0)
        self.assertIn(CELL, self.report())
        self.assertEqual(self.report().count(CELL), 2)

    def test_three_trial_gain_skips_every_trial_and_the_aggregate_says_so(self):
        found = self.gain(3)
        for arm, summaries in found.items():
            with self.subTest(arm=arm):
                self.assertEqual(len(summaries), 3)
                for summary in summaries:
                    self.assertEqual(summary["judge"], SKIPPED)
                aggregate = self.arm_summary(arm)
                self.assertEqual(aggregate["judge"], SKIPPED)
                self.assertEqual(aggregate["aggregate"]["judge"],
                                 SKIPPED_AGGREGATE)
                self.assertEqual(aggregate["judge_models_used"], [])
                self.assertEqual(
                    aggregate["usage"]["measured"]["judge"]["calls"], 0)
        # Never `-`, `error` or a number in the judge column.
        row = [line for line in self.report().splitlines()
               if line.startswith("| with_skill |")][0]
        self.assertIn(f"| {CELL} |", row)

    def test_the_ingester_accepts_every_summary_of_a_skipped_run(self):
        self.gain(3)
        count = 0
        for rel, doc in self.results_files().items():
            with self.subTest(summary=rel):
                ingest.check_summary(doc, rel, ingest.parse_result_path(rel))
                count += 1
        self.assertEqual(count, 8)

    def test_the_ingester_rejects_a_malformed_status_block(self):
        self.gain(1)
        rel = f"{SKILL}/{TS}/with_skill/summary.json"
        doc = self.results_files()[rel]
        parts = ingest.parse_result_path(rel)
        for bad in ({"status": "skipped"},
                    {"status": "skipped", "reason": "other"},
                    {"status": "judged", "reason": "objective-decided"},
                    {**SKIPPED, "extra": 1},
                    {"status": "skipped", "reason": ["objective-decided"]}):
            with self.subTest(judge=bad):
                with self.assertRaises(ingest.Rejected):
                    ingest.check_summary({**doc, "judge": bad}, rel, parts)

    def test_the_badge_reads_the_pair_by_its_objective_result(self):
        for trials in (1, 3):
            with self.subTest(trials=trials):
                shutil.rmtree(self.results, ignore_errors=True)
                self.gain_again(trials)
                badge = make_badge.build_badge(self.results, SKILL)
                self.assertEqual(badge["color"], "green")
                self.assertTrue(
                    badge["message"].startswith("with 2/2 vs without 1/2"),
                    badge["message"])

    def gain_again(self, trials: int) -> None:
        (self.cli_dir / "state.json").unlink(missing_ok=True)
        self.gain(trials)

    def test_a_skipped_judge_is_no_judge_figure_in_the_badge(self):
        self.gain(1)
        for arm in ("with_skill", "without_skill"):
            stats = make_badge.arm_stats(self.results / SKILL / TS, arm)
            self.assertEqual((stats["judge_n"], stats["judge_sum"]), (0, None))


class TieAndLossJudgeTests(PairCase):

    def test_a_tie_judges_every_trial_of_both_arms_after_all_the_agents(self):
        proc = self.both([BARE] * 4, judge_steps(4), "--trials", "2")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.kinds(), ["agents"] * 4 + ["judges"] * 4)
        for arm, summaries in self.trial_summaries(2).items():
            for summary in summaries:
                self.assertEqual(summary["judge"]["overall"], 7.0)
                self.assertEqual(summary["judge_models_used"],
                                 ["fake-judge-model"])
        aggregate = self.arm_summary("with_skill")["aggregate"]["judge"]
        self.assertEqual((aggregate["n"], aggregate["errors"]), (2, 0))
        self.assertNotIn(CELL, self.report())

    def test_a_loss_judges_every_trial_of_both_arms(self):
        proc = self.both([BARE, GAIN], judge_steps(2))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.kinds(), ["agents", "agents", "judges", "judges"])
        for summaries in self.trial_summaries(1).values():
            self.assertEqual(summaries[0]["judge"]["overall"], 7.0)

    def test_an_errored_trial_cannot_flip_the_decision_and_is_not_judged(self):
        # with: trial 1 passes 2 of 2, trial 2 errors. without: 1 of 2 twice.
        # Counting the errored trial as a failure would tie them (2/4 each).
        proc = self.both([GAIN, {"mode": "error"}, BARE, BARE], [],
                         "--trials", "2")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self._calls("judges"), [])
        found = self.trial_summaries(2)
        self.assertEqual(found["with_skill"][0]["judge"], SKIPPED)
        self.assertIsNone(found["with_skill"][1]["judge"])
        self.assertEqual(found["with_skill"][1]["error"]["type"], "nonzero_exit")
        for summary in found["without_skill"]:
            self.assertEqual(summary["judge"], SKIPPED)
        self.assertEqual(self.arm_summary("with_skill")["aggregate"]["judge"],
                         SKIPPED_AGGREGATE)

    def test_an_arm_with_nothing_scored_leaves_the_rate_undefined_and_judges(self):
        proc = self.both([{"mode": "error"}, BARE], judge_steps(1))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self.kinds(), ["agents", "agents", "judges"])
        found = self.trial_summaries(1)
        self.assertIsNone(found["with_skill"][0]["judge"])
        self.assertEqual(found["without_skill"][0]["judge"]["overall"], 7.0)


class InPlaceJudgingTests(PairCase):

    def test_a_single_arm_run_judges_the_trial_inside_the_trial(self):
        proc = self.both([GAIN], judge_steps(1), arm="with_skill")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.kinds(), ["agents", "judges"])
        (summary,) = self.trial_summaries_one("with_skill")
        self.assertEqual(summary["judge"]["overall"], 7.0)

    def trial_summaries_one(self, arm: str) -> list:
        return [self.arm_summary(arm)]

    def test_judge_always_judges_despite_a_gain_trial_by_trial(self):
        proc = self.both([GAIN, BARE], judge_steps(2), "--judge", "always")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.kinds(), ["agents", "judges", "agents", "judges"])
        for summaries in self.trial_summaries(1).values():
            self.assertEqual(summaries[0]["judge"]["overall"], 7.0)
        self.assertNotIn(CELL, self.report())

    def test_no_judge_wins_and_records_null_not_skipped(self):
        for flags in (("--no-judge",), ("--no-judge", "--judge", "always")):
            with self.subTest(flags=flags):
                shutil.rmtree(self.results, ignore_errors=True)
                (self.cli_dir / "state.json").unlink(missing_ok=True)
                (self.cli_dir / "calls.jsonl").unlink(missing_ok=True)
                proc = self.both([GAIN, BARE], [], *flags)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(self._calls("judges"), [])
                for summaries in self.trial_summaries(1).values():
                    self.assertIsNone(summaries[0]["judge"])
                self.assertNotIn(CELL, self.report())

    def test_judge_flag_rejects_an_unknown_value(self):
        proc = self.both([GAIN, BARE], [], "--judge", "never")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self._calls(), [])


class PairwiseTests(PairCase):

    def args(self, **given) -> argparse.Namespace:
        return argparse.Namespace(**{"no_judge": False, "judge": "auto",
                                     **given})

    def test_the_decision_helper_holds_only_a_pair_under_auto(self):
        absolute = {"judge": {"mode": " Absolute "}}
        for fixture in ({}, {"judge": {}}, {"judge": {"mode": ""}}, absolute):
            with self.subTest(fixture=fixture):
                self.assertEqual(run_eval._judge_hold(
                    self.args(), fixture, ["with_skill", "without_skill"]), [])
        self.assertIsNone(run_eval._judge_hold(
            self.args(), {}, ["with_skill"]))
        self.assertIsNone(run_eval._judge_hold(
            self.args(), {}, ["with_skill", "with_guidance"]))
        self.assertIsNone(run_eval._judge_hold(
            self.args(judge="always"), {}, ["with_skill", "without_skill"]))
        self.assertIsNone(run_eval._judge_hold(
            self.args(no_judge=True), {}, ["with_skill", "without_skill"]))

    def test_a_judge_mode_that_is_not_absolute_is_never_held(self):
        for mode in ("pairwise", " Pairwise ", "ranking"):
            with self.subTest(mode=mode):
                self.assertIsNone(run_eval._judge_hold(
                    self.args(), {"judge": {"mode": mode}},
                    ["with_skill", "without_skill"]))

    def test_a_judged_pairwise_run_is_still_refused_before_any_arm(self):
        fixture = _write_fixture(self.evals / "pairwise-skill", "pairwise-skill",
                                 judge={"model": "m", "mode": "pairwise"})
        self._script(agents=[GAIN, BARE])
        proc = self._run(fixture, "--arm", "both", "--timestamp", TS,
                         "--registry",
                         f"adam-agentskills={self._registry('pairwise-skill')}")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("judge_mode_unsupported", proc.stdout)
        self.assertEqual(self._calls(), [])


class StatisticsAndReportTests(unittest.TestCase):

    @staticmethod
    def trial(judge, error=None) -> dict:
        return {"error": error, "agent": None, "judge": judge,
                "objective_checks": [{"id": "a", "passed": True}]}

    def test_a_skipped_block_is_not_counted_as_a_judge_error(self):
        stats = run_eval.aggregate_trials(
            [self.trial(dict(SKIPPED)), self.trial(dict(SKIPPED))])
        self.assertEqual(stats["aggregate"]["judge"], SKIPPED_AGGREGATE)

    def test_a_skipped_block_beside_a_judged_one_changes_no_judge_figure(self):
        stats = run_eval.aggregate_trials(
            [self.trial({"overall": 6.0, "dimensions": []}),
             self.trial(dict(SKIPPED))])
        self.assertEqual((stats["aggregate"]["judge"]["n"],
                          stats["aggregate"]["judge"]["errors"]), (1, 0))

    def test_an_errored_skipped_trial_stays_out_of_the_judge_figures(self):
        stats = run_eval.aggregate_trials(
            [self.trial(dict(SKIPPED)),
             self.trial(None, error={"type": "x", "detail": "d"})])
        self.assertEqual(stats["aggregate"]["judge"], SKIPPED_AGGREGATE)

    def test_the_single_trial_report_prints_the_skip(self):
        report = run_eval._render_report("s", "p", "T", [
            {"arm": "with_skill", "judge": dict(SKIPPED),
             "objective_checks": [{"id": "a", "passed": True}]},
            {"arm": "without_skill", "judge": None, "objective_checks": []}])
        lines = report.splitlines()
        self.assertIn(f"| with_skill | 1/1 | {CELL} |", lines[-2])
        self.assertIn("| without_skill | - | - |", lines[-1])

    def test_the_trials_report_prints_the_skip(self):
        stats = run_eval.aggregate_trials([self.trial(dict(SKIPPED))])
        report = run_eval._render_trials_report("s", "T", 1, [
            {"label": "s", "prompt": "p",
             "arms": [{"arm": "with_skill", "models_used": [],
                       "stats": stats}]}])
        row = [l for l in report.splitlines() if l.startswith("| with_skill |")]
        self.assertIn(f"| {CELL} |", row[0])
        self.assertNotIn("error", row[0])

    def test_the_guidance_report_prints_the_skip(self):
        report = run_eval._render_guidance_report(
            "alpha", "p", "T", "user", {"with_guidance": 3}, [
                {"arm": "with_guidance", "mode": "section", "guard": {},
                 "judge": dict(SKIPPED),
                 "objective_checks": [{"id": "a", "passed": True}]}])
        row = report.splitlines()[-1]
        self.assertIn(f"| 1/1 | {CELL} |", row)


FIGURES = ("num_turns", "cost_usd", "models", "cache_creation")


class SinkTests(unittest.TestCase):
    """What a judge call and a canary leg hand to a collecting block."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def env(self, **extra):
        return mock.patch.dict(os.environ, {
            "CLAUDE_BIN": str(FAKE_CLAUDE), "FAKE_CLAUDE_MODE": "judge",
            "HOME": str(self.tmp), **extra})

    def test_a_judge_sink_entry_carries_the_figures_the_result_has(self):
        from scorers import judge
        with self.env(FAKE_CLAUDE_FULL_USAGE="1"):
            with judge.collecting_models() as sink:
                judge._run_judge_cli("p", model="m-1", timeout=60)
        (entry,) = sink
        self.assertEqual(set(entry), {"modelUsage", "num_turns", "usage",
                                      "total_cost_usd"})
        self.assertEqual((entry["num_turns"], entry["total_cost_usd"]),
                         (2, 0.07))
        self.assertEqual(entry["usage"]["cache_creation"],
                         {"ephemeral_5m_input_tokens": 3,
                          "ephemeral_1h_input_tokens": 4})
        self.assertEqual(entry["modelUsage"]["m-1"]["costUSD"], 0.07)

    def test_a_judge_sink_entry_leaves_out_what_the_result_lacks(self):
        from scorers import judge
        done = subprocess.CompletedProcess(
            [], 0, stdout=json.dumps({"result": "x", "total_cost_usd": 0.5}),
            stderr="")
        with mock.patch.object(judge.subprocess, "run", return_value=done):
            with judge.collecting_models() as sink:
                judge._run_judge_cli("p", model=None, timeout=60)
        self.assertEqual(sink, [{"modelUsage": None, "total_cost_usd": 0.5}])

    def test_a_canary_leg_collects_every_parsed_result_and_returns_as_before(self):
        import run_canary
        for mode, shape in (("agent", {"reply"}),
                            ("agent_error", {"error", "detail", "raw"})):
            with self.subTest(mode=mode), self.env(
                    FAKE_CLAUDE_MODE=mode, FAKE_CLAUDE_FULL_USAGE="1"):
                with run_canary.collecting_results() as sink:
                    result = run_canary.run_leg(
                        self.tmp, "p", "Read", model="m-1", timeout=60)
                self.assertEqual(set(result), shape)
                (entry,) = sink
                self.assertEqual(set(entry), {"modelUsage", "num_turns",
                                              "usage", "total_cost_usd"})

    def test_a_leg_that_fails_before_a_result_collects_nothing(self):
        import run_canary
        with self.env(FAKE_CLAUDE_MODE="error"):
            with run_canary.collecting_results() as sink:
                result = run_canary.run_leg(self.tmp, "p", "Read", model=None,
                                            timeout=60)
        self.assertEqual(result["error"], "nonzero_exit")
        self.assertEqual(sink, [])


class UsageOfADeferredJudgeTests(PairCase):

    def figures_run(self, *flags: str, full: bool = True, mode="agent_and_judge"):
        """A both-arms run against test/fake-claude itself, every call
        logged. With `full`, the judge's results (and the guard's, below)
        carry every usage figure; the agent's never do, so its figures differ
        from the judge's."""
        self.log = self.tmp / "argv.log"
        fixture = _write_fixture(
            self.evals / "figures-skill", "figures-skill",
            env={"FAKE_CLAUDE_MODE": mode,
                 "FAKE_CLAUDE_ARGV_LOG": str(self.log)})
        self.registry = self._registry("figures-skill")
        extra = {"CLAUDE_BIN": str(FAKE_CLAUDE), "FAKE_CLAUDE_MODE": mode,
                 "FAKE_CLAUDE_ARGV_LOG": str(self.log)}
        if full:
            extra["FAKE_CLAUDE_FULL_USAGE"] = "1"
        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(fixture),
               "--arm", "both", "--registry", f"adam-agentskills={self.registry}",
               "--results-dir", str(self.results), "--timeout", "60",
               "--timestamp", TS, *flags]
        return subprocess.run(cmd, capture_output=True, text=True,
                              env=_child_env(self.tmp, **extra),
                              cwd=str(REPO_ROOT), timeout=600)

    def argvs(self) -> list[list[str]]:
        lines = self.log.read_text(encoding="utf-8").splitlines()
        return [argv for argv in (json.loads(l)["argv"] for l in lines)
                if "--version" not in argv]

    def summaries_of(self, arm: str) -> dict:
        return json.loads((self.results / "figures-skill" / TS / arm
                           / "summary.json").read_text(encoding="utf-8"))

    def test_a_judge_call_records_its_own_figures_apart_from_the_agents(self):
        proc = self.figures_run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        measured = self.summaries_of("with_skill")["usage"]["measured"]
        judge, agent = measured["judge"], measured["agent"]
        self.assertEqual(judge["calls"], 1)
        self.assertEqual((judge["num_turns"], judge["cost_usd"]), (2, 0.07))
        self.assertEqual(judge["cache_creation"], {
            "ephemeral_5m_input_tokens": 3, "ephemeral_1h_input_tokens": 4})
        self.assertEqual(list(judge["models"]), ["fake-judge-model"])
        self.assertEqual(judge["models"]["fake-judge-model"]["cost_usd"], 0.07)
        self.assertEqual(judge["reasons"], {})
        # The agent's own result carries no such figures: its block says so.
        self.assertEqual((agent["cost_usd"], agent["num_turns"]), (0.05, 2))
        self.assertIsNone(agent["cache_creation"])
        self.assertIn("agent", agent["reasons"]["cache_creation"])
        for rel, doc in self.results_files_of("figures-skill").items():
            with self.subTest(summary=rel):
                ingest.check_summary(doc, rel, ingest.parse_result_path(rel))

    def results_files_of(self, skill: str) -> dict:
        return {k: v for k, v in self.results_files().items()
                if k.startswith(skill)}

    def test_a_judge_result_without_a_figure_is_null_with_its_reason(self):
        proc = self.figures_run(full=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        judge = self.summaries_of("with_skill")["usage"]["measured"]["judge"]
        self.assertEqual(judge["calls"], 1)
        self.assertIsNone(judge["cache_creation"])
        self.assertEqual(set(judge["reasons"]), {"cache_creation", "cost_basis"})
        self.assertEqual(set(judge["reasons"].values()),
                         {"the judge's CLI result does not carry it"})
        for rel, doc in self.results_files_of("figures-skill").items():
            with self.subTest(summary=rel):
                ingest.check_summary(doc, rel, ingest.parse_result_path(rel))

    def test_the_ingester_requires_a_reason_exactly_for_a_null_figure(self):
        proc = self.figures_run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rel = "figures-skill/%s/with_skill/summary.json" % TS
        doc = self.results_files()[rel]
        parts = ingest.parse_result_path(rel)
        for role in ("judge", "agent"):
            for name in FIGURES:
                nulled = json.loads(json.dumps(doc))
                block = nulled["usage"]["measured"][role]
                has_reason = name in block["reasons"]
                with self.subTest(role=role, name=name):
                    if has_reason:
                        # A reason for a value that is there.
                        block["reasons"].pop(name)
                        block[name] = block[name] if block[name] is not None else 1
                    else:
                        # A null without its reason.
                        block[name] = None
                    with self.assertRaises(ingest.Rejected):
                        ingest.check_summary(nulled, rel, parts)

    def test_judging_adds_no_call_and_samples_no_meter(self):
        proc = self.figures_run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        argvs = self.argvs()
        judges = [a for a in argvs if "fake-judge-model" in a]
        self.assertEqual((len(argvs), len(judges)), (4, 2))
        for argv in judges:
            self.assertNotIn("--verbose", argv)

    def test_a_judge_that_fails_is_a_judge_error_with_its_outcome_listed(self):
        proc = self.both([BARE, BARE], [{"fail": True}, {"overall": 5.0}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        first = self.trial_summaries(1)["with_skill"][0]
        self.assertIn("error", first["judge"])
        self.assertEqual(first["usage"]["measured"]["calls"][1]["outcome"],
                         "error")


class GuidancePairTests(unittest.TestCase):
    """The guidance path: one `with` and one `without` arm, one trial each."""

    SECTION = "alpha"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="conditional-guidance-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = make_guidance_checkout(self.tmp / "checkout")
        if not (self.root / ".claude" / "hooks" / "fleet-memory.sh").is_file():
            self.skipTest("no fleet-memory.sh to deliver guidance with")
        self.log = self.tmp / "argv.log"
        self.results = self.tmp / "results"

    def run_guidance(self, check: str, *flags: str, arms=None, full=False):
        eval_dir = self.tmp / "eval"
        eval_dir.mkdir()
        fixture = {
            "subject": "guidance", "section": self.SECTION,
            "prompt": "Do the ordinary task.", "model": "fake-agent-model",
            "judge_rubric": "Score it.", "judge": {"model": "fake-judge"},
            "env": {"FAKE_CLAUDE_MODE": "guidance_probe",
                    "FAKE_CLAUDE_ARGV_LOG": str(self.log)},
            "objective_checks": [{"id": "c", "type": "transcript_matches",
                                  "must_match": [check]}]}
        if arms:
            fixture["arms"] = arms
        (eval_dir / "fixture.yaml").write_text(
            yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8")
        if full:
            fixture["env"]["FAKE_CLAUDE_FULL_USAGE"] = "1"
            (eval_dir / "fixture.yaml").write_text(
                yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8")
        env = _child_env(self.tmp, CLAUDE_BIN=str(FAKE_CLAUDE),
                         FAKE_CLAUDE_ARGV_LOG=str(self.log),
                         **({"FAKE_CLAUDE_FULL_USAGE": "1"} if full else {}))
        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
               "--arm", "both", "--guidance", str(self.root),
               "--results-dir", str(self.results), "--timeout", "60", *flags]
        return subprocess.run(cmd, capture_output=True, text=True, env=env,
                              cwd=str(REPO_ROOT), timeout=600)

    def judge_calls(self) -> int:
        if not self.log.exists():
            return 0
        lines = self.log.read_text(encoding="utf-8").splitlines()
        return sum("fake-judge" in json.loads(line)["argv"] for line in lines)

    def summary(self, arm: str) -> dict:
        (run_dir,) = (self.results / f"guidance/{self.SECTION}").iterdir()
        return json.loads((run_dir / arm / "summary.json")
                          .read_text(encoding="utf-8"))

    def test_a_gain_skips_the_judge_for_both_arms(self):
        # Only the arm that was delivered the token can match it.
        proc = self.run_guidance("$MAGIC_TOKEN")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.judge_calls(), 0)
        for arm in ("with_guidance", "without_guidance"):
            self.assertEqual(self.summary(arm)["judge"], SKIPPED)
            self.assertEqual(
                self.summary(arm)["usage"]["measured"]["judge"]["calls"], 0)
        (run_dir,) = (self.results / f"guidance/{self.SECTION}").iterdir()
        self.assertIn(CELL, (run_dir / "report.md").read_text(encoding="utf-8"))

    def test_a_tie_judges_both_arms(self):
        proc = self.run_guidance(".")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.judge_calls(), 2)
        for arm in ("with_guidance", "without_guidance"):
            summary = self.summary(arm)
            self.assertNotEqual(summary["judge"], SKIPPED)
            self.assertEqual(summary["usage"]["measured"]["judge"]["calls"], 1)

    def test_a_guard_call_records_its_figures_and_adds_no_call(self):
        proc = self.run_guidance(".", full=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for arm in ("with_guidance", "without_guidance"):
            guard = self.summary(arm)["usage"]["measured"]["guard"]
            with self.subTest(arm=arm):
                self.assertEqual(guard["calls"], 1)
                self.assertEqual((guard["num_turns"], guard["cost_usd"]),
                                 (2, 0.07))
                self.assertEqual(guard["cache_creation"], {
                    "ephemeral_5m_input_tokens": 3,
                    "ephemeral_1h_input_tokens": 4})
                self.assertTrue(guard["models"])
                self.assertEqual(guard["reasons"], {})
        lines = self.log.read_text(encoding="utf-8").splitlines()
        argvs = [a for a in (json.loads(l)["argv"] for l in lines)
                 if "--version" not in a]
        guards = [a for a in argvs if "--disallowedTools" in a
                  and "--setting-sources" in a and "-p" in a
                  and "fake-agent-model" in a and "--verbose" not in a]
        # Two guards, two agents, two judges (a tie): nothing added.
        self.assertEqual(len(argvs), 6)
        self.assertEqual(sum("fake-judge" in a for a in argvs), 2)
        self.assertGreaterEqual(len(guards), 2)
        for argv in argvs:
            if "fake-judge" in argv:
                self.assertNotIn("--verbose", argv)

    def test_a_guard_result_without_a_figure_is_null_with_its_reason(self):
        proc = self.run_guidance(".")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        guard = self.summary("with_guidance")["usage"]["measured"]["guard"]
        self.assertEqual(guard["calls"], 1)
        self.assertIsNone(guard["cache_creation"])
        self.assertEqual(guard["reasons"]["cache_creation"],
                         "the guard's CLI result does not carry it")
        for arm in ("with_guidance", "without_guidance"):
            summary = self.summary(arm)
            ingest.check_usage(summary["usage"], arm, summary["run"])

    def test_judge_always_judges_despite_a_gain(self):
        proc = self.run_guidance("$MAGIC_TOKEN", "--judge", "always")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.judge_calls(), 2)

    def test_arms_that_are_not_a_with_without_pair_judge_in_place(self):
        proc = self.run_guidance("$MAGIC_TOKEN", arms={
            "treatment": {"mode": "section"}, "control": {"mode": "none"}})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.judge_calls(), 2)
        self.assertNotEqual(self.summary("treatment")["judge"], SKIPPED)


if __name__ == "__main__":
    unittest.main()
