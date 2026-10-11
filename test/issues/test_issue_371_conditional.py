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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


#: test/fake-claude, except that the judge's result carries a per-model cost
#: of its own (a judge result reaches the harness as `modelUsage` alone), so
#: the judge's figure can be told from the agent's $0.04.
COSTING_CLI = '''\
import json
import subprocess
import sys

FAKE = {fake!r}
if "--version" in sys.argv:
    sys.exit(subprocess.run([FAKE] + sys.argv[1:]).returncode)
done = subprocess.run([FAKE] + sys.argv[1:], input=sys.stdin.read(),
                      capture_output=True, text=True, check=True)
payload = json.loads(done.stdout)
if "fake-judge-model" in sys.argv:
    for usage in payload["modelUsage"].values():
        usage["costUSD"] = 0.03
print(json.dumps(payload))
'''


class UsageOfADeferredJudgeTests(PairCase):

    def costing_cli(self) -> Path:
        self.cli_dir.mkdir(exist_ok=True)
        cli = self.cli_dir / "costing-claude"
        cli.write_text("#!/usr/bin/env python3\n"
                       + COSTING_CLI.format(fake=str(FAKE_CLAUDE)),
                       encoding="utf-8")
        cli.chmod(0o755)
        return cli

    def test_a_deferred_judge_call_is_recorded_on_its_own_trial(self):
        cli = self.costing_cli()
        proc = self._run(self.fixture_dir, "--arm", "both", "--trials", "2",
                         "--registry", f"adam-agentskills={self.registry}",
                         "--timestamp", TS, cli=cli, mode="agent_and_judge")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for rel, doc in self.results_files().items():
            with self.subTest(summary=rel):
                ingest.check_summary(doc, rel, ingest.parse_result_path(rel))
        for arm, summaries in self.trial_summaries(2).items():
            for summary in summaries:
                measured = summary["usage"]["measured"]
                self.assertEqual(measured["judge"]["calls"], 1)
                self.assertEqual(measured["agent"]["calls"], 1)
                self.assertEqual(measured["judge"]["cost_usd"], 0.03)
                self.assertEqual(measured["agent"]["cost_usd"], 0.04)
                self.assertEqual([(c["role"], c["index"])
                                  for c in measured["calls"]],
                                 [("agent", 0), ("judge", 0)])
                self.assertLessEqual(measured["calls"][0]["ended_at"],
                                     measured["calls"][1]["started_at"])
                self.assertEqual(measured["ended_at"],
                                 measured["calls"][1]["ended_at"])
            total = self.arm_summary(arm)["usage"]["measured"]
            self.assertEqual(total["judge"]["calls"], 2)
            self.assertEqual(total["agent"]["calls"], 2)
            self.assertAlmostEqual(total["judge"]["cost_usd"], 0.06)
            self.assertAlmostEqual(total["agent"]["cost_usd"], 0.08)

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

    def run_guidance(self, check: str, *flags: str, arms=None):
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
        env = _child_env(self.tmp, CLAUDE_BIN=str(FAKE_CLAUDE),
                         FAKE_CLAUDE_ARGV_LOG=str(self.log))
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
