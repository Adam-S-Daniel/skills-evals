#!/usr/bin/env python3
"""#572 part 1 (2026-11-02): record every improve run's measured cost.

`scripts/improve_cost.py summarize` reads an improve or guidance-improve
run's results tree and writes one small record; `check_record` is its one
schema, shared with the ingest (test_issue_routine_eval_ingest.py covers the
branch). What is pinned here:

  * the summarizer on the skill layout (`runs/<side>/<skill>/<ts>/...`) and
    the guidance layout (`runs/<ts>/<side>/<fixture>/trial-<k>/...`): trial
    summaries only, dollars only from list-priced trials (the rest counted),
    each side's trials and dollars, the meter's first and last snapshot by
    PARSED time across all trials, the delta (null across a window reset or
    with fewer than two snapshots), and an empty tree;
  * it never opens raw.json or anything but summaries, the proposal file
    and the loop record, and never copies a string out of them except a
    model id that fits the pattern;
  * the proposal file is numbers only: a CLI reply carrying `result` and
    `session_id` leaves neither in the file or the record;
  * `check_record` rejects extra keys, wrong types, out-of-range numbers and
    every derived field that disagrees with its inputs;
  * the CLI writes the record (at most 4 KiB) and exits 0, or writes
    nothing and exits 1;
  * the routine prompt's improve sections, mirrored in docs/how-it-works.md,
    pass `--results-dir "$RESULTS"` to both proposers, run a summarize
    command these scripts' own parser accepts, and stage exactly one path.

Fixtures are built in-test in temporary directories. Discovered and run by
test/run_tests.py.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "harness"))

import improve_cost  # noqa: E402
import propose_guidance_edit as pge  # noqa: E402
import propose_skill_edit as pse  # noqa: E402

RUN_ID = "20261102T120000Z-abc123"
STAMP = datetime(2026, 11, 2, 12, 0, 0, tzinfo=timezone.utc)
TS = "20261102T120005Z"
RESET = int((STAMP + timedelta(days=3)).timestamp())
#: A window that resets during the run: due 10 minutes in, then a week on.
EARLY = int((STAMP + timedelta(minutes=10)).timestamp())
NOW = STAMP + timedelta(minutes=50)
MARKER = "do-not-copy-this-marker"
DOCS = REPO_ROOT / "docs" / "how-it-works.md"


def snap(at: str, utilization: float, reset: int = RESET) -> dict:
    return {"at": at, "at_source": "cli_message", "call": {"role": "agent", "index": 0},
            "info": {"unifiedWindows": {"seven_day": {"utilization": utilization,
                                                      "resetsAt": reset}},
                     "note": MARKER}}


def role(calls: int, usd: float, basis: str | None = "list") -> dict:
    return {"calls": calls, "duration_ms": 1000 * calls, "cost_usd": usd if calls else 0,
            "cost_basis": basis if calls else None, "num_turns": calls,
            "models": {}, "cache_creation": None, "reasons": {"x": MARKER}}


def summary(snaps=(), agent=(1, 0.5), judge=(0, 0), guard=(0, 0), basis="list",
            started="2026-11-02T12:01:00Z", ended="2026-11-02T12:03:00Z",
            scope="trial", omitted=0) -> dict:
    return {"arm": "with_skill", "error": MARKER,
            "usage": {"measured": {
                "scope": scope, "started_at": started, "ended_at": ended,
                "calls": None,
                "meter": {"snapshots": list(snaps), "omitted": omitted},
                "agent": role(*agent, basis), "judge": role(*judge, basis),
                "guard": role(*guard, basis), "reasons": {}}}}


class TreeCase(unittest.TestCase):

    def setUp(self):
        self.results = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.results)

    def put(self, rel: str, doc) -> Path:
        path = self.results / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
        return path

    def skill_trial(self, side: str, k: int, doc: dict) -> Path:
        return self.put(f"runs/{side}/demo/{TS}/fx/t{k}/demo/{TS}/fx/with_skill/summary.json",
                        doc)

    def guidance_trial(self, side: str, k: int, doc: dict) -> Path:
        return self.put(f"runs/{TS}/{side}/fx/trial-{k}/guidance/sec/{TS}/full/summary.json",
                        doc)

    def summarize(self, mode="improve", target="demo", code=1):
        return improve_cost.summarize(self.results, RUN_ID, mode, target, code, NOW)


class SummarizeTests(TreeCase):

    def test_skill_layout_measures_both_sides_and_the_cross_trial_span(self):
        # Times deliberately sort differently as strings and as times: the
        # 9-digit fraction sorts after "12:10:00Z" as text.
        self.skill_trial("baseline", 1, summary([snap("2026-11-02T12:10:00.000000001Z", 0.40),
                                                 snap("2026-11-02T12:12:00Z", 0.41)],
                                                agent=(1, 0.25), judge=(1, 0.125)))
        self.skill_trial("baseline", 2, summary([snap("2026-11-02T12:10:00Z", 0.395)],
                                                agent=(1, 0.5)))
        self.skill_trial("candidate", 1, summary([snap("2026-11-02T12:30:30.5Z", 0.43)],
                                                 agent=(2, 1.0), guard=(1, 0.0625)))
        # An arm aggregate is not a trial.
        self.put(f"runs/candidate/demo/{TS}/summary.json",
                 summary([snap("2026-11-02T13:00:00Z", 0.9)], scope="arm"))
        doc = self.summarize()
        self.assertEqual(doc["trial_summaries"], 3)
        self.assertEqual(doc["sides"], {"baseline": {"trials": 2, "usd": 0.875},
                                        "candidate": {"trials": 1, "usd": 1.0625}})
        self.assertEqual((doc["agent_usd"], doc["judge_usd"], doc["guard_usd"]),
                         (1.75, 0.125, 0.0625))
        self.assertEqual((doc["agent_calls"], doc["judge_calls"]), (4, 1))
        self.assertEqual(doc["first"], {"at": "2026-11-02T12:10:00Z", "utilization": 0.395,
                                        "resets_at": RESET})
        self.assertEqual(doc["last"], {"at": "2026-11-02T12:30:30.500000Z",
                                       "utilization": 0.43, "resets_at": RESET})
        self.assertEqual(doc["snapshots"], 4)
        self.assertEqual(doc["span_seconds"], 20 * 60 + 30.5)
        self.assertEqual(doc["delta"], 0.43 - 0.395)  # full precision, unrounded
        self.assertEqual(doc["delta_reason"], "measured")
        self.assertEqual(doc["stage_reached"], "candidate")
        self.assertEqual(doc["busy_seconds"], 3 * 120)
        self.assertEqual((doc["outcome"], doc["exit_code"]), ("rejected", 1))

    def test_guidance_layout(self):
        self.guidance_trial("baseline", 1, summary([snap("2026-11-02T12:05:00Z", 0.1)]))
        self.guidance_trial("candidate", 1, summary([snap("2026-11-02T12:06:00Z", 0.2)]))
        doc = self.summarize("guidance-improve", "sec", 0)
        self.assertEqual(doc["sides"]["baseline"]["trials"], 1)
        self.assertEqual(doc["sides"]["candidate"]["trials"], 1)
        self.assertEqual(doc["outcome"], "accepted")
        self.assertEqual(doc["span_seconds"], 60)

    def test_unpriced_trials_are_counted_not_summed(self):
        self.skill_trial("baseline", 1, summary(agent=(1, 0.5), basis="list"))
        self.skill_trial("baseline", 2, summary(agent=(1, 9.0), basis=None))
        self.skill_trial("baseline", 3, summary(agent=(1, 9.0), basis="estimate"))
        doc = self.summarize()
        self.assertEqual(doc["usd_unpriced_trials"], 2)
        self.assertEqual(doc["agent_usd"], 0.5)
        self.assertEqual(doc["sides"]["baseline"], {"trials": 3, "usd": 0.5})
        self.assertEqual(doc["stage_reached"], "baseline")

    def test_window_reset_has_no_delta(self):
        self.skill_trial("baseline", 1, summary([snap("2026-11-02T12:05:00Z", 0.9, EARLY),
                                                 snap("2026-11-02T12:20:00Z", 0.01,
                                                      EARLY + 604800)]))
        doc = self.summarize()
        self.assertIsNone(doc["delta"])
        self.assertEqual(doc["delta_reason"], "window_reset")
        self.assertEqual(doc["span_seconds"], 900)

    def test_one_snapshot_and_an_empty_tree(self):
        self.skill_trial("baseline", 1, summary([snap("2026-11-02T12:05:00Z", 0.9)]))
        doc = self.summarize()
        self.assertEqual((doc["first"], doc["last"], doc["delta"], doc["span_seconds"]),
                         (None, None, None, None))
        self.assertEqual(doc["delta_reason"], "fewer_than_two_snapshots")
        empty = improve_cost.summarize(self.results / "absent", RUN_ID, "improve",
                                       "demo", None, NOW)
        self.assertEqual((empty["trial_summaries"], empty["stage_reached"],
                          empty["outcome"], empty["snapshots"]), (0, "none", "error", 0))

    def test_out_of_bounds_snapshots_and_files_are_skipped(self):
        self.skill_trial("baseline", 1, summary([
            snap("2026-11-01T11:00:00Z", 0.1),             # before the stamp window
            snap("2026-11-02T12:05:00Z", 1.5),             # utilization over 1
            snap("2026-11-02T12:06:00Z", 0.2, reset=True),  # bool reset
            snap("not-a-time", 0.2),
            snap("2026-11-02T12:07:00Z", 0.3)]))
        big = self.skill_trial("baseline", 2, summary())
        big.write_text(json.dumps(summary()) + " " * improve_cost.SUMMARY_CAP)
        doc = self.summarize()
        self.assertEqual(doc["snapshots"], 1)
        self.assertEqual(doc["trial_summaries"], 1)

    def test_symlinks_are_never_followed(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "summary.json").write_text(json.dumps(summary()))
        link_dir = self.results / "runs" / "baseline" / "demo"
        link_dir.mkdir(parents=True)
        os.symlink(outside, link_dir / "linked")
        os.symlink(outside / "summary.json", link_dir / "summary.json")
        self.assertEqual(self.summarize()["trial_summaries"], 0)

    def test_reads_only_summaries_the_proposal_and_the_record(self):
        self.skill_trial("baseline", 1, summary([snap("2026-11-02T12:05:00Z", 0.1)]))
        raw = self.results / f"runs/baseline/demo/{TS}/fx/t1/demo/{TS}/fx/with_skill/raw.json"
        raw.write_text(json.dumps({"secret": MARKER}))
        self.put(f"improvements/demo/{TS}.patch", MARKER)
        self.put(f"improvements/demo/{TS}.pr-body.md", MARKER)
        opened = []
        real_open = os.open

        def spy(path, *args, **kwargs):
            opened.append(Path(path).name)
            return real_open(path, *args, **kwargs)

        with mock.patch.object(improve_cost.os, "open", spy):
            doc = self.summarize()
        self.assertEqual(sorted(set(opened)), ["summary.json"])
        self.assertNotIn(MARKER, json.dumps(doc))

    def test_record_shape_and_size(self):
        for k in range(1, 4):
            for side in ("baseline", "candidate"):
                self.skill_trial(side, k, summary([snap(f"2026-11-02T12:0{k}:00Z", 0.1 * k),
                                                   snap(f"2026-11-02T12:1{k}:00Z", 0.1 * k + 0.01)],
                                                  agent=(3, 1.2345678901234567),
                                                  judge=(1, 0.3333333333333333)))
        doc = self.summarize()
        self.assertEqual(list(doc), list(improve_cost.RECORD_KEYS))
        self.assertLessEqual(len(improve_cost.encode(doc)), improve_cost.RECORD_CAP)
        improve_cost.check_record(json.loads(improve_cost.encode(doc)))


class ProposalAndRecordTests(TreeCase):

    REPLY = {"type": "result", "result": f"the reply text {MARKER}",
             "session_id": "session-" + MARKER, "total_cost_usd": 0.0421,
             "usage": {"input_tokens": 1234, "output_tokens": 567,
                       "cache_read_input_tokens": 9}}

    def test_runner_keeps_numbers_only_and_the_caller_writes_them(self):
        proc = subprocess.CompletedProcess([], 0, json.dumps(self.REPLY), "")

        @contextlib.contextmanager
        def env():
            yield {"CLAUDE_BIN": "claude"}

        runner = pse.Runner()
        with mock.patch.object(pse, "guarded_environment", env), \
                mock.patch.object(pse.subprocess, "run", return_value=proc):
            self.assertEqual(runner.propose("prompt", "claude-x"), self.REPLY["result"])
        self.assertEqual(runner.last_usage, {"calls": 1, "usd": 0.0421,
                                             "input_tokens": 1234, "output_tokens": 567})
        pse.write_proposal_usage(self.results, TS, runner)
        text = (self.results / f"proposal-{TS}.json").read_text()
        for word in (MARKER, "session", "result"):
            self.assertNotIn(word, text)
        self.skill_trial("baseline", 1, summary())
        doc = self.summarize()
        self.assertEqual(doc["proposal"], runner.last_usage)
        self.assertEqual(doc["stage_reached"], "proposal")
        self.assertNotIn(MARKER, json.dumps(doc))

    def test_guidance_runner_carries_the_inner_usage(self):
        inner = mock.Mock()
        inner.propose.return_value = "reply"
        inner.last_usage = {"calls": 1, "usd": 0.5, "input_tokens": 1, "output_tokens": 2}
        with mock.patch.object(pge.pse, "Runner", return_value=inner):
            runner = pge.Runner()
            self.assertEqual(runner.propose("p", "m"), "reply")
        self.assertEqual(runner.last_usage, inner.last_usage)

    def test_unusable_usage_writes_nothing(self):
        for reply in ({**self.REPLY, "total_cost_usd": True},
                      {**self.REPLY, "total_cost_usd": 5000},
                      {**self.REPLY, "usage": {"input_tokens": 1.5, "output_tokens": 1}},
                      {"result": "x"}):
            self.assertIsNone(pse.proposal_usage(reply))
        pse.write_proposal_usage(self.results, TS, object())  # a fake with no attribute
        self.assertEqual(list(self.results.iterdir()), [])

    def test_proposal_file_is_type_checked(self):
        self.skill_trial("baseline", 1, summary())
        for bad in ({"calls": 1, "usd": 0.1, "input_tokens": 1},
                    {"calls": 1, "usd": "0.1", "input_tokens": 1, "output_tokens": 1},
                    {"calls": True, "usd": 0.1, "input_tokens": 1, "output_tokens": 1},
                    {"calls": 1, "usd": 0.1, "input_tokens": 1, "output_tokens": 1,
                     "note": MARKER}):
            with self.subTest(bad=bad):
                self.put(f"proposal-{TS}.json", bad)
                self.assertIsNone(self.summarize()["proposal"])
        self.put(f"proposal-{TS}.json", {"calls": 1, "usd": 0.1, "input_tokens": 1,
                                         "output_tokens": 1})
        self.put("proposal-20261102T120006Z.json", {"calls": 1, "usd": 0.1,
                                                    "input_tokens": 1, "output_tokens": 1})
        self.assertIsNone(self.summarize()["proposal"], "two files are ambiguous")

    def test_models_and_trigger_calls_come_from_the_loop_record(self):
        self.put(f"improvements/demo/{TS}.json", {
            "models": {"arm": "claude-sonnet-4-6", "proposal": "claude-opus-4-1"},
            "description_half": {"usage": {"total_calls": 42, "cost_usd": None}},
            "body_half": {"rationale": MARKER}})
        doc = self.summarize()
        self.assertEqual(doc["models"], {"arm": "claude-sonnet-4-6",
                                         "proposal": "claude-opus-4-1"})
        self.assertEqual(doc["trigger_calls"], 42)
        self.put(f"guidance-improvements/sec/{TS}.json", {
            "models": {"arm": ["claude-a", "claude-b"], "proposal": MARKER}})
        doc = self.summarize("guidance-improve", "sec")
        self.assertEqual(doc["models"], {"arm": None, "proposal": None})
        self.assertIsNone(doc["trigger_calls"])
        self.put(f"guidance-improvements/sec/{TS}.json", {"models": {"arm": ["claude-a"]}})
        self.assertEqual(self.summarize("guidance-improve", "sec")["models"]["arm"],
                         "claude-a")


class CheckRecordTests(TreeCase):

    def good(self) -> dict:
        self.skill_trial("baseline", 1, summary([snap("2026-11-02T12:05:00Z", 0.1),
                                                 snap("2026-11-02T12:06:00Z", 0.2)],
                                                agent=(1, 0.5)))
        self.skill_trial("candidate", 1, summary(agent=(1, 0.25)))
        doc = self.summarize()
        improve_cost.check_record(doc)
        return doc

    def assertInvalid(self, doc, pattern):
        with self.assertRaisesRegex(improve_cost.Invalid, pattern):
            improve_cost.check_record(doc)

    def test_rejections(self):
        good = self.good()
        cases = [
            ({"extra": 1}, "exactly the keys"),
            ({"schema_version": 2}, "schema_version"),
            ({"run_id": "x"}, "run_id"),
            ({"mode": "eval"}, "mode"),
            ({"target": "Bad Name"}, "target"),
            ({"exit_code": True}, "exit_code"),
            ({"exit_code": 0}, "outcome"),
            ({"stage_reached": "baseline"}, "stage_reached"),
            ({"agent_calls": -1}, "agent_calls"),
            ({"agent_calls": 1.0}, "agent_calls"),
            ({"agent_usd": 1001}, "agent_usd"),
            ({"agent_usd": 0.7}, "dollars do not add up"),
            ({"guard_usd": float("nan")}, "guard_usd"),
            ({"usd_unpriced_trials": 3}, "usd_unpriced_trials"),
            ({"sides": {"baseline": good["sides"]["baseline"]}}, "sides"),
            ({"trial_summaries": 3}, "trial counts"),
            ({"proposal": {"calls": 1, "usd": 0.1, "input_tokens": 1}}, "proposal"),
            ({"proposal": {"calls": 1, "usd": 0.1, "input_tokens": 10 ** 9 + 1,
                           "output_tokens": 0}}, "input_tokens"),
            ({"models": {"arm": "gpt-4", "proposal": None}}, "models.arm"),
            ({"busy_seconds": 86401}, "busy_seconds"),
            ({"span_seconds": 61}, "span_seconds"),
            ({"delta": 0.2}, "delta"),
            ({"first": {**good["first"], "at": "2026-11-01T12:00:00Z"}}, "window"),
            ({"first": {**good["first"], "at": "2026-11-02 12:05:00"}}, "first.at"),
            ({"first": {**good["first"], "resets_at": True}}, "resets_at"),
            ({"first": {**good["first"], "resets_at": RESET * 1000}}, "resets_at"),
            ({"first": good["last"], "last": good["first"]}, "after last|span"),
            ({"first": None}, "both or neither"),
            ({"ended_at": "2026-11-04T12:00:00Z"}, "ended_at"),
            ({"trigger_calls": "3"}, "trigger_calls"),
        ]
        for change, pattern in cases:
            with self.subTest(change=str(change)[:60]):
                self.assertInvalid({**good, **change}, pattern)

    def test_window_reset_requires_a_null_delta(self):
        good = self.good()
        reset = {**good, "first": {**good["first"], "resets_at": EARLY},
                 "last": {**good["last"], "resets_at": EARLY + 604800}}
        self.assertInvalid(reset, "window reset")
        improve_cost.check_record({**reset, "delta": None, "delta_reason": "window_reset"})


class CliTests(TreeCase):

    def run_main(self, *extra) -> tuple[int, Path]:
        out = self.results / "out" / "improve-cost" / RUN_ID / "cost.json"
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            code = improve_cost.main(["summarize", "--results-dir", str(self.results),
                                      "--run-id", RUN_ID, "--mode", "improve",
                                      "--target", "demo", "--out", str(out), *extra],
                                     now=NOW)
        return code, out

    def test_writes_a_valid_record_and_exits_zero(self):
        for code_text, expected in (("0", 0), ("1", 1), ("2", 2), ("none", None), ("9", None)):
            with self.subTest(code=code_text):
                code, out = self.run_main("--exit-code", code_text)
                self.assertEqual(code, 0)
                doc = json.loads(out.read_bytes())
                self.assertEqual(doc["exit_code"], expected)
                improve_cost.check_record(doc)

    def test_an_invalid_target_writes_nothing_and_exits_one(self):
        out = self.results / "x" / "cost.json"
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = improve_cost.main(["summarize", "--results-dir", str(self.results),
                                      "--run-id", RUN_ID, "--mode", "improve",
                                      "--target", "../" + MARKER, "--exit-code", "1",
                                      "--out", str(out)], now=NOW)
        self.assertEqual(code, 1)
        self.assertFalse(out.exists())
        self.assertNotIn(MARKER, err.getvalue())


class PromptMirrorTests(unittest.TestCase):
    """docs/how-it-works.md mirrors the routine's saved prompt (which is not
    in this repository); its commands are held to these scripts' own flags
    by parsing them (shlex, then argparse), never by matching text."""

    @classmethod
    def setUpClass(cls):
        text = DOCS.read_text(encoding="utf-8")
        head = "### Routine improve mode: what each run costs (#572)"
        section = text[text.index(head):]
        section = section[:section.index("\n### ", 1)]
        block = re.search(r"```text\n(.*?)\n```", section, re.S)
        cls.block = block.group(1)
        cls.modes = {
            "improve": cls.block[cls.block.index("IMPROVE MODE (payload"):
                                 cls.block.index("GUIDANCE-IMPROVE MODE (payload")],
            "guidance-improve": cls.block[cls.block.index("GUIDANCE-IMPROVE MODE (payload"):]}

    @staticmethod
    def command_lines(text: str, script: str) -> list[list[str]]:
        out = []
        for line in text.splitlines():
            if f"scripts/{script}" in line and line.lstrip().startswith(
                    ("python3", "env ")):
                # The prompt's `<...>` placeholder is prose; one word here.
                argv = shlex.split(re.sub(r"<[^>]*>", "none", line.strip()))
                out.append(argv[argv.index(f"scripts/{script}") + 1:])
        return out

    def test_both_proposers_get_the_results_dir(self):
        for mode, script in (("improve", "propose_skill_edit.py"),
                             ("guidance-improve", "propose_guidance_edit.py")):
            with self.subTest(mode=mode):
                [argv] = self.command_lines(self.modes[mode], script)
                self.assertEqual(argv[argv.index("--results-dir") + 1], "$RESULTS")

    def test_summarize_command_parses_with_the_scripts_own_parser(self):
        for mode, target in (("improve", "$SKILL"), ("guidance-improve", "$SECTION")):
            with self.subTest(mode=mode):
                [argv] = self.command_lines(self.modes[mode], "improve_cost.py")
                with mock.patch.object(improve_cost, "summarize",
                                       side_effect=improve_cost.Invalid("x")) as called, \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(improve_cost.main(argv), 1)
                args = called.call_args.args
                self.assertEqual((args[0], args[1], args[2], args[3]),
                                 (Path("$RESULTS"), "$RUN_ID", mode, target))
                self.assertEqual(argv[argv.index("--out") + 1],
                                 "$COST/improve-cost/$RUN_ID/cost.json")

    def test_the_cost_step_stages_exactly_one_path(self):
        for mode, text in self.modes.items():
            with self.subTest(mode=mode):
                fragments = [f.strip() for f in re.split(r";\s|\.\s", text)]
                adds = [shlex.split(f) for f in fragments
                        if f.startswith('git -C "$W" ') and " add " in f]
                self.assertEqual([argv[argv.index("add") + 1:] for argv in adds],
                                 [["--", "improve-cost/$RUN_ID/cost.json"]])
                self.assertIn("Never use git add -A or git add . here", text)
                self.assertIn("claude/eval-cost-$RUN_ID", text)
        self.assertIn("claude/eval-cost-<run_id>", self.block.split("\n\n")[0])

if __name__ == "__main__":
    unittest.main()
