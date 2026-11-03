#!/usr/bin/env python3
"""skills-evals#662, part A: the trigger-only improve fire.

Adam's decision (2026-11-03, the #662 decision card): "New fire mode runs only
skill-creator's description loop; accept when held-out trigger accuracy rises
0.15+ with no drop on should-not-trigger queries; PR auto-merges like other
loop PRs." It stays fire mode `improve` with a `trigger_only` input, so the
branch, gate, outcomes, cooldown and allowance charge are improve's. What is
pinned here:

  * `propose_skill_edit.py --trigger-only`: it needs `--trigger-eval-set` and
    refuses the flags it would ignore; a set with fewer than
    TRIGGER_ONLY_MIN_CLASS distinct queries of a class is refused; the
    decision reads skill-creator's loop output (history[0] the original, the
    best by `best_description`), accepts a held-out gain of exactly 0.15 and
    rejects 0.125, a should-not-trigger drop or an unchanged description,
    and refuses a malformed output; it runs with zero fixtures; every model
    call goes through a fake runner;
  * `improve_gate.py`: a trigger-only record passes `check_record` and a whole
    branch passes `validate`, while a tampered `trigger_only` block (gain
    under 0.15, a drop, bool counts, unequal totals) is rejected; `apply`
    refuses a body change for it; `impact_entry` writes the trigger counts in
    a form adam-agentskills' gate reads as a run; `fire-check --trigger-only`
    accepts writing-adrs' committed set and refuses a holdout, a missing,
    uncommitted or small set and a foreign registry, never echoing input;
  * improve_outcomes reads `Fire eval routine: improve trigger <skill>` as an
    improve attempt of that skill and nothing else as a trigger fire;
  * routine-eval-fire.yml, parsed as YAML and its steps run for real: the
    input, the title, the validation and the payload's sixth key only when
    true; the routine prompt's trigger-only command is one the script parses.

Deterministic: no network, no sleep, no wall clock. Discovered and run by
test/run_tests.py.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "routine-eval-fire.yml"
INSTRUCTIONS = REPO_ROOT / "docs" / "routine" / "eval-runner-instructions.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(TEST_DIR / "issues"))
sys.path.insert(0, str(TEST_DIR))

import allowance_guard  # noqa: E402
import improve_gate as gate  # noqa: E402
import improve_outcomes as outcomes  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import propose_skill_edit as pse  # noqa: E402
import test_issue_71 as t71  # noqa: E402
import test_issue_closed_loop_planner as planner_tests  # noqa: E402
import test_issue_routine_eval_fire as fire_tests  # noqa: E402
import test_issue_routine_improve as tri  # noqa: E402

SKILL = t71.SKILL
ORIGINAL_DESCRIPTION = pse.frontmatter_data(t71.ORIGINAL_SKILL_MD)["description"]
NEW_DESCRIPTION = "Use this skill to record a non-obvious decision as an ADR."
TRIGGER_EXPRESSION = planner_tests.TRIGGER_EXPRESSION

#: A reviewed set at the per-class minimum: eight of each class.
REVIEWED_8 = (
    [{"query": f"record the {topic} decision", "should_trigger": True}
     for topic in ("queue", "cache", "schema", "auth", "deploy", "billing",
                   "search", "logging")]
    + [{"query": f"fix the flaky {thing} test", "should_trigger": False}
       for thing in ("login", "upload", "search", "export", "import", "email",
                     "cron", "webhook")])


def entry(description: str, passed: int, total: int, snt_passed: int,
          snt_total: int) -> dict:
    """One skill-creator history entry: `total` held-out should-trigger
    results (the first `passed` pass) and `snt_total` should-not-trigger
    train results (the first `snt_passed` pass)."""
    return {"description": description, "test_passed": passed, "test_total": total,
            "train_passed": snt_passed, "train_total": snt_total,
            "train_results": [{"query": f"n{i}", "should_trigger": False,
                               "pass": i < snt_passed, "runs": 3, "triggers": 0}
                              for i in range(snt_total)],
            "test_results": [{"query": f"p{i}", "should_trigger": True,
                              "pass": i < passed, "runs": 3, "triggers": 3}
                             for i in range(total)]}


def loop_output(original=(10, 20, 5, 5), best=(13, 20, 5, 5),
                best_description=NEW_DESCRIPTION) -> dict:
    history = [entry(ORIGINAL_DESCRIPTION, *original),
               entry(best_description, *best)]
    return {"original_description": ORIGINAL_DESCRIPTION,
            "best_description": best_description, "best_score": "x",
            "best_test_score": f"{best[0]}/{best[1]}", "best_train_score": "5/5",
            "iterations_run": 2, "history": history}


class LoopRunner:
    """Answers the description loop with canned output; any other call is a
    failure (trigger-only mode measures no fixture and proposes no body)."""

    def __init__(self, loop):
        self.loop = loop
        self.calls = []

    def run_description_loop(self, argv, *, cwd, skill_creator):
        self.calls.append(list(argv))
        self.eval_set = json.loads(Path(t71.flag(argv, "--eval-set")).read_text())
        self.settings = json.loads((Path(cwd) / ".claude" / "settings.json").read_text())
        return self.loop

    def run_eval(self, argv):
        raise AssertionError("trigger-only mode ran a fixture")

    def propose(self, prompt, model):
        raise AssertionError("trigger-only mode made a proposal call")


def trigger_record(**changes) -> dict:
    """An accepted trigger-only record in improve_trigger_only()'s shape."""
    doc = {
        "schema": 1, "skill": tri.SKILL, "timestamp": "20261103T101500Z",
        "mode": "trigger-only",
        "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, not badge input",
        "registry": {"name": "adam-agentskills",
                     "url": "https://github.com/Adam-S-Daniel/adam-agentskills",
                     "sha": tri.REGISTRY_SHA, "skill_md": tri.SKILL_MD},
        "models": {"arm": "model-a"},
        "trigger_set": {"source": "file:trigger-eval-set.json", "size": 20,
                        "split": {"train": {"should_trigger": 6, "should_not_trigger": 6},
                                  "held_out": {"should_trigger": 4,
                                               "should_not_trigger": 4}},
                        "problems": []},
        "description_half": {"changed": True, "original": "Write an ADR.",
                             "best": "Write an ADR when a decision needs a record."},
        "trigger_only": {"min_gain": 0.15,
                         "original": {"test_passed": 4, "test_total": 8,
                                      "should_not_passed": 10, "should_not_total": 12},
                         "best": {"test_passed": 6, "test_total": 8,
                                  "should_not_passed": 11, "should_not_total": 12},
                         "gain": 0.25},
        "status": "accepted", "decision": "accepted",
        "reasons": ["held-out trigger queries passed 4/8 -> 6/8"],
        "files": {"patch": "/tmp/x.patch", "pr_body": "/tmp/x.pr-body.md",
                  "record": "/tmp/x.json"},
    }
    doc.update(changes)
    return doc


TRIGGER_CANDIDATE = tri.ORIGINAL.replace(
    "description: Write an ADR.", "description: Write an ADR when a decision needs a record.")


# ---------------------------------------------------------------------------
# propose_skill_edit.py --trigger-only


class ArgTests(unittest.TestCase):

    def parse(self, *argv):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            try:
                return pse.parse_args([SKILL, *argv]), ""
            except SystemExit as exc:
                self.assertEqual(exc.code, 2)
                return None, err.getvalue()

    def test_trigger_only_needs_a_set(self):
        args, err = self.parse("--trigger-only")
        self.assertIsNone(args)
        self.assertIn("--trigger-only needs --trigger-eval-set", err)
        args, _ = self.parse("--trigger-only", "--trigger-eval-set", "x.json")
        self.assertTrue(args.trigger_only)

    def test_flags_it_would_ignore_are_refused(self):
        for extra in (["--holdout", "bootstrap"], ["--rotation", "1"], ["--no-judge"],
                      ["--trials", "3"], ["--min-gain", "0.2"]):
            with self.subTest(extra=extra):
                args, err = self.parse("--trigger-only", "--trigger-eval-set", "x.json",
                                       *extra)
                self.assertIsNone(args)
                self.assertIn(f"--trigger-only does not take {extra[0]}", err)

    def test_the_normal_mode_keeps_its_defaults(self):
        args, _ = self.parse()
        self.assertEqual((args.trials, args.min_gain, args.trigger_only),
                         (pse.DEFAULT_TRIALS, pse.DEFAULT_MIN_GAIN, False))
        args, _ = self.parse("--trials", "2", "--min-gain", "0.2", "--holdout", "x")
        self.assertEqual((args.trials, args.min_gain), (2, 0.2))


class SetTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def write(self, items) -> Path:
        path = self.tmp / "set.json"
        path.write_text(json.dumps(items), encoding="utf-8")
        return path

    def test_eight_of_each_class_is_enough(self):
        items, counts = pse.trigger_only_set(self.write(REVIEWED_8))
        self.assertEqual(len(items), 16)
        self.assertEqual(counts["held_out"], {"should_trigger": 3, "should_not_trigger": 3})

    def test_a_small_or_lopsided_set_is_refused_with_fixed_text(self):
        positives, negatives = REVIEWED_8[:8], REVIEWED_8[8:]
        # A whitespace variant is the same query, so it does not count twice.
        twin = dict(positives[0], query="  record  the queue   decision ")
        cases = {"seven positives": positives[:7] + negatives,
                 "seven negatives": positives + negatives[:7],
                 "one class": positives + [dict(p, query=p["query"] + " again")
                                           for p in positives],
                 "a duplicate": positives[:7] + [twin] + negatives}
        for name, items in cases.items():
            with self.subTest(name):
                with self.assertRaises(pse.Refusal) as caught:
                    pse.trigger_only_set(self.write(items))
                self.assertEqual(str(caught.exception), pse.TRIGGER_ONLY_SET_REFUSAL)

    def test_normalization_is_the_one_trigger_eval_set_uses(self):
        items = [{"query": " a  b ", "should_trigger": True},
                 {"query": "a b", "should_trigger": False},
                 {"query": "c", "should_trigger": False}]
        self.assertEqual(pse.normalize_trigger_items(items),
                         [{"query": "a b", "should_trigger": True},
                          {"query": "c", "should_trigger": False}])
        self.assertEqual(pse.normalize_trigger_items(items, {"c"}),
                         [{"query": "a b", "should_trigger": True}])


class DecideTests(unittest.TestCase):

    def test_gain_at_the_boundary(self):
        accepted, reasons, block, raw = pse.decide_trigger_only(
            loop_output((0, 20, 5, 5), (3, 20, 5, 5)))
        self.assertTrue(accepted, reasons)
        self.assertEqual(raw, NEW_DESCRIPTION)
        self.assertAlmostEqual(block["gain"], 0.15, places=12)
        accepted, reasons, block, _ = pse.decide_trigger_only(
            loop_output((4, 8, 5, 5), (5, 8, 5, 5)))
        self.assertFalse(accepted)
        self.assertEqual(block["gain"], 0.125)
        self.assertIn("held-out trigger accuracy did not rise by the minimum gain", reasons)

    def test_a_should_not_trigger_drop_rejects(self):
        accepted, reasons, _, _ = pse.decide_trigger_only(
            loop_output((2, 8, 5, 6), (7, 8, 4, 6)))
        self.assertFalse(accepted)
        self.assertIn("fewer should-not-trigger queries passed", reasons)

    def test_an_unchanged_description_rejects(self):
        spaced = ORIGINAL_DESCRIPTION.replace(" ", "  ", 1)
        accepted, reasons, _, _ = pse.decide_trigger_only(
            loop_output((2, 8, 5, 5), (7, 8, 5, 5), best_description=spaced))
        self.assertFalse(accepted)
        self.assertIn("the best description is the original", reasons)

    def test_the_best_is_found_by_its_description(self):
        loop = loop_output((2, 8, 5, 5), (7, 8, 5, 5))
        loop["history"].append(entry("a later, worse one", 1, 8, 5, 5))
        accepted, _, block, _ = pse.decide_trigger_only(loop)
        self.assertTrue(accepted)
        self.assertEqual(block["best"]["test_passed"], 7)

    def test_malformed_output_is_refused(self):
        def mutate(change):
            loop = loop_output((2, 8, 5, 5), (7, 8, 5, 5))
            change(loop)
            return loop
        cases = {
            "not an object": [],
            "no history": mutate(lambda d: d.pop("history")),
            "empty history": mutate(lambda d: d.update(history=[])),
            "no best": mutate(lambda d: d.pop("best_description")),
            "best not in history": mutate(lambda d: d.update(best_description="other")),
            "bool count": mutate(lambda d: d["history"][1].update(test_passed=True)),
            "passed over total": mutate(lambda d: d["history"][1].update(test_passed=9)),
            "totals differ": mutate(lambda d: d["history"][1].update(
                test_total=9, test_results=d["history"][1]["test_results"] + [
                    {"query": "x", "should_trigger": True, "pass": False}])),
            "no held-out": mutate(lambda d: [e.update(test_passed=0, test_total=0)
                                             for e in d["history"]]),
            "bad result": mutate(lambda d: d["history"][0]["train_results"].append(
                {"query": "x", "should_trigger": "false", "pass": True})),
            "snt totals differ": mutate(lambda d: d["history"][1]["train_results"].append(
                {"query": "x", "should_trigger": False, "pass": True})),
        }
        for name, loop in cases.items():
            with self.subTest(name):
                with self.assertRaises(pse.Refusal) as caught:
                    pse.decide_trigger_only(loop)
                self.assertEqual(str(caught.exception), pse.TRIGGER_LOOP_MALFORMED)


class TriggerPipelineCase(t71.PipelineCase):

    def setUp(self):
        super().setUp()
        self.reviewed_set.write_text(json.dumps(REVIEWED_8))

    def run_trigger(self, loop, *extra):
        runner = LoopRunner(loop)
        rc, out, err = self.run_main(runner, "--trigger-only", *extra)
        return rc, out, err, runner

    def stem(self) -> Path:
        return self.results / "improvements" / SKILL / t71.TS


class PipelineTests(TriggerPipelineCase):

    def test_accepts_and_writes_record_patch_and_pr_body(self):
        rc, out, err, runner = self.run_trigger(loop_output((0, 20, 5, 5), (3, 20, 5, 5)))
        self.assertEqual(rc, pse.EXIT_ACCEPTED, out + err)
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(len(runner.eval_set), 16, "the whole set, nothing held out")
        self.assertEqual(runner.settings, {"enabledPlugins": {"demo@test-market": False}})
        record = self.record()
        self.assertEqual((record["status"], record["decision"], record["mode"]),
                         ("accepted", "accepted", "trigger-only"))
        self.assertEqual(record["trigger_set"]["source"], "file:reviewed-queries.json")
        self.assertEqual(record["trigger_only"]["original"],
                         {"test_passed": 0, "test_total": 20,
                          "should_not_passed": 5, "should_not_total": 5})
        self.assertNotIn("split", record)
        patch = self.stem().with_suffix(".patch").read_text()
        self.assertIn(f"+description: {NEW_DESCRIPTION}", patch)
        self.assertEqual(sum(1 for line in patch.splitlines()
                             if line.startswith(("+", "-"))
                             and not line.startswith(("+++", "---"))), 2,
                         "only the description line moves")
        body = self.stem().with_name(t71.TS + ".pr-body.md").read_text()
        self.assertEqual(body.split("\n", 1)[0],
                         gate.REPORT_TITLE.format(skill=SKILL))
        self.assertIn("trigger-only", body)
        self.assertIn("0/20 -> 3/20", body)
        self.assertIn("5/5 -> 5/5", body)
        gate.check_report(body, "report.md", SKILL)

    def test_the_accepted_record_passes_the_gate(self):
        rc, out, err, _ = self.run_trigger(loop_output((0, 20, 5, 5), (3, 20, 5, 5)))
        self.assertEqual(rc, 0, out + err)
        record = self.record()
        found = gate.check_record(json.loads(json.dumps(record)), "summary.json",
                                  str(REPO_ROOT))
        self.assertEqual(found["skill"], SKILL)
        gate.check_patch(self.stem().with_suffix(".patch").read_text(), "skill.patch",
                         found["skill_md"])

    def test_rejections_write_a_record_and_no_pr_body(self):
        cases = {"gain 0.125": loop_output((4, 8, 5, 5), (5, 8, 5, 5)),
                 "snt drop": loop_output((2, 8, 5, 6), (7, 8, 4, 6)),
                 "unchanged": loop_output((2, 8, 5, 5), (7, 8, 5, 5),
                                          best_description=ORIGINAL_DESCRIPTION)}
        for name, loop in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.results, ignore_errors=True)
                rc, out, err, _ = self.run_trigger(loop)
                self.assertEqual(rc, pse.EXIT_REJECTED, out + err)
                self.assertEqual(self.record()["status"], "rejected")
                self.assertFalse(self.stem().with_name(t71.TS + ".pr-body.md").exists())

    def test_malformed_loop_output_is_a_refused_record(self):
        rc, out, err, _ = self.run_trigger({"history": "nope", "best_description": "x"})
        self.assertEqual(rc, pse.EXIT_REFUSED, out + err)
        record = self.record()
        self.assertEqual((record["status"], record["phase"]), ("refused", "decision"))
        self.assertEqual(record["reasons"], [pse.TRIGGER_LOOP_MALFORMED])

    def test_a_small_set_is_refused_before_any_call_or_write(self):
        self.reviewed_set.write_text(json.dumps(REVIEWED_8[1:]))
        rc, _, err, runner = self.run_trigger(loop_output())
        self.assertEqual(rc, pse.EXIT_REFUSED)
        self.assertIn(pse.TRIGGER_ONLY_SET_REFUSAL, err)
        self.assertEqual(runner.calls, [])
        self.assertFalse(self.results.exists())

    def test_dry_run_plans_without_calls_or_writes(self):
        rc, out, err = self.run_main(t71.NoCallRunner(), "--trigger-only", "--dry-run")
        self.assertEqual(rc, 0, err)
        planned = json.loads(out)
        self.assertEqual(planned["mode"], "trigger-only")
        self.assertEqual(planned["trigger_eval_set"]["size"], 16)
        self.assertEqual(planned["min_gain"], pse.TRIGGER_ONLY_MIN_GAIN)
        self.assertFalse(self.results.exists())

    def test_a_skill_with_no_fixture_runs_against_adam_agentskills(self):
        empty = self.tmp / "no-fixtures"
        empty.mkdir()
        with mock.patch.object(pse, "EVALS_DIR", empty):
            rc, out, err = self.run_main(t71.NoCallRunner(), "--trigger-only", "--dry-run")
            self.assertEqual(rc, 0, err)
            planned = json.loads(out)
            self.assertEqual(planned["fixtures"], 0)
            self.assertEqual(planned["registry"]["name"], "adam-agentskills")
            self.assertEqual(planned["models"]["arm"], pse.arm_model({}))
            rc, out, err, _ = self.run_trigger(loop_output((0, 20, 5, 5), (3, 20, 5, 5)))
        self.assertEqual(rc, 0, out + err)


class RecordKeyTests(unittest.TestCase):

    def test_keys_the_trigger_only_writer_writes_are_allowed(self):
        tree = ast.parse((REPO_ROOT / "scripts" / "propose_skill_edit.py").read_text())
        keys = set()
        for func in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                     and node.name in {"improve_trigger_only", "write_record"}):
            for node in ast.walk(func):
                if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "record"
                        for t in node.targets) and isinstance(node.value, ast.Dict):
                    keys |= {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
                if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                        and node.value.id == "record" and isinstance(node.ctx, ast.Store) \
                        and isinstance(node.slice, ast.Constant):
                    keys.add(node.slice.value)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and node.func.attr == "update" \
                        and isinstance(node.func.value, ast.Name) \
                        and node.func.value.id == "record":
                    keys |= {kw.arg for kw in node.keywords if kw.arg}
        self.assertIn("trigger_only", keys)
        self.assertLessEqual(keys, set(gate.RECORD_ALLOWED))
        self.assertLessEqual(keys, set(gate.TRIGGER_RECORD_ALLOWED))
        self.assertLessEqual(set(gate.TRIGGER_RECORD_REQUIRED), keys)

    def test_the_gate_and_the_loop_share_their_constants(self):
        self.assertEqual(gate.TRIGGER_ONLY_MIN_GAIN, pse.TRIGGER_ONLY_MIN_GAIN)
        self.assertEqual(gate.TRIGGER_SET_FILE, pse.TRIGGER_SET_FILE)
        self.assertEqual(gate.TRIGGER_COUNT_KEYS, pse.TRIGGER_COUNT_KEYS)
        self.assertEqual(pse.TRIGGER_ONLY_DEFAULT_REGISTRY, gate.REGISTRY_URL)


# ---------------------------------------------------------------------------
# improve_gate.py


class GateRecordTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        (self.repo / "evals" / tri.SKILL).mkdir(parents=True)
        (self.repo / "evals" / tri.SKILL / "trigger-eval-set.json").write_text("[]\n")

    def check(self, doc):
        return gate.check_record(doc, "summary.json", str(self.repo))

    def assert_rejected(self, doc, pattern):
        with self.assertRaises(ingest.Rejected) as caught:
            self.check(doc)
        self.assertRegex(str(caught.exception), pattern)

    def test_accepts_a_trigger_record(self):
        self.assertEqual(self.check(trigger_record())["skill_md"], tri.SKILL_MD)

    def test_a_trigger_record_needs_the_reviewed_set_on_the_default_branch(self):
        (self.repo / "evals" / tri.SKILL / "trigger-eval-set.json").unlink()
        self.assert_rejected(trigger_record(), "no reviewed trigger eval set")
        (self.repo / "evals" / tri.SKILL / "trigger-eval-set.json").symlink_to(self.tmp)
        self.assert_rejected(trigger_record(), "no reviewed trigger eval set")

    def test_tampered_counts_are_rejected(self):
        def block(original=(4, 8, 10, 12), best=(6, 8, 11, 12), gain=None):
            keys = pse.TRIGGER_COUNT_KEYS
            if gain is None and all(type(v) is int for v in original + best) \
                    and original[1] == best[1] and original[1]:
                gain = (best[0] - original[0]) / original[1]
            return {"min_gain": 0.15, "original": dict(zip(keys, original)),
                    "best": dict(zip(keys, best)), "gain": gain if gain is not None else 0.25}
        cases = {
            "gain 0.125": (block((4, 8, 10, 12), (5, 8, 10, 12)), "less than the minimum"),
            "snt drop": (block((4, 8, 10, 12), (7, 8, 9, 12)), "fewer should-not-trigger"),
            "bool count": (block((4, 8, 10, 12), (True, 8, 11, 12), gain=-0.375),
                           "expected an integer"),
            "passed over total": (block((4, 8, 10, 12), (9, 8, 11, 12)), "more queries passed"),
            "unequal totals": (block((4, 8, 10, 12), (6, 9, 11, 12), gain=0.25),
                               "not measured on the same queries"),
            "zero total": (block((0, 0, 10, 12), (0, 0, 11, 12), gain=0.25),
                           "not measured on the same queries"),
            "gain lies": (block((4, 8, 10, 12), (5, 8, 10, 12), gain=0.5),
                          "gain disagrees"),
            "missing key": ({"min_gain": 0.15, "original": {}, "best": {}}, "missing keys"),
        }
        for name, (value, pattern) in cases.items():
            with self.subTest(name):
                self.assert_rejected(trigger_record(trigger_only=value), pattern)

    def test_the_gain_boundary_is_the_loops(self):
        keys = pse.TRIGGER_COUNT_KEYS
        value = {"min_gain": 0.15, "original": dict(zip(keys, (0, 20, 5, 5))),
                 "best": dict(zip(keys, (3, 20, 5, 5))), "gain": 3 / 20}
        self.check(trigger_record(trigger_only=value))

    def test_mode_and_block_must_agree(self):
        self.assert_rejected(trigger_record(mode="bare"), "unknown mode")
        self.assert_rejected(trigger_record(mode=None), "unknown mode")
        doc = trigger_record()
        doc.pop("trigger_only")
        self.assert_rejected(doc, "missing keys")
        self.assert_rejected(tri.record(trigger_only=trigger_record()["trigger_only"]),
                             "needs mode trigger-only")
        self.assert_rejected(trigger_record(split={"rotation": 0}), "unexpected keys")
        self.assert_rejected(trigger_record(status="rejected"), "not accepted")


class GateValidateTests(tri.GitCase):
    """A whole trigger-only branch through `validate`."""

    def setUp(self):
        super().setUp()
        self.git("checkout", "-q", "main")
        self.write({f"evals/{tri.SKILL}/trigger-eval-set.json": b"[]\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "set")
        self.git("checkout", "-q", "-B", tri.BRANCH)

    def files(self, record=None):
        return tri.good_files(
            summary_json=json.dumps(record or trigger_record(), indent=2).encode(),
            skill_patch=tri.patch_text(new=TRIGGER_CANDIDATE).encode())

    def test_a_trigger_only_branch_validates(self):
        self.commit(self.files())
        self.assertEqual(self.validate()["target_branch"], f"eval-improve/{tri.SKILL}")

    def test_a_tampered_trigger_only_branch_is_rejected(self):
        bad = trigger_record()
        bad["trigger_only"]["best"]["should_not_passed"] = 9
        self.commit(self.files(bad))
        self.assertRejected("fewer should-not-trigger")


class GateApplyTests(unittest.TestCase):
    """`apply` refuses a body change for a trigger-only record, on
    test_issue_routine_improve's scratch registry."""
    setUp = tri.ApplyTests.setUp
    run_git = tri.ApplyTests.run_git
    stage = tri.ApplyTests.stage

    def stage_record(self, doc):
        (self.staged / "summary.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_a_trigger_record_may_move_the_description(self):
        self.stage_record(trigger_record())
        self.stage(tri.patch_text(new=TRIGGER_CANDIDATE))
        self.assertEqual(gate.apply(self.staged, self.tree, tri.SKILL_MD),
                         {"changed": tri.SKILL_MD})

    def test_a_trigger_record_may_not_move_the_body(self):
        self.stage_record(trigger_record())
        self.stage(tri.patch_text())
        with self.assertRaises(ingest.Rejected) as caught:
            gate.apply(self.staged, self.tree, tri.SKILL_MD)
        self.assertIn("only the description may change", str(caught.exception))

    def test_a_normal_record_may_move_the_body(self):
        self.stage_record(tri.record())
        self.stage(tri.patch_text())
        gate.apply(self.staged, self.tree, tri.SKILL_MD)

    def test_an_unreadable_staged_record_is_refused(self):
        (self.staged / "summary.json").write_text("{", encoding="utf-8")
        self.stage(tri.patch_text(new=TRIGGER_CANDIDATE))
        with self.assertRaises(ingest.Rejected):
            gate.apply(self.staged, self.tree, tri.SKILL_MD)


class ImpactEntryTests(unittest.TestCase):

    def test_trigger_only_entry(self):
        text = gate.impact_entry(trigger_record(), "adam-anything-anywhere", tri.RUN_ID,
                                 ("1.2.3", "1.2.4"), False, "auto")
        self.assertTrue(text.startswith(
            f"## 2026-11-03 — adam-anything-anywhere/{tri.SKILL} — edit\n"))
        self.assertIn("trigger-only improvement run", text)
        self.assertIn("skills-evals#662", text)
        self.assertIn("body unchanged", text)
        eval_line = next(line for line in text.splitlines() if line.startswith("- Eval:"))
        self.assertIn("held-out trigger queries passed, original -> candidate: "
                      "4/8 -> 6/8; should-not-trigger passed: 10/12 -> 11/12", eval_line)
        # adam-agentskills' check_skill_gates.py RAN form: a pass count or a
        # run id, on a line that does not start with `none` or `not run`.
        body = eval_line[len("- Eval:"):].strip()
        self.assertRegex(body, r"\b\d+/\d+\b")
        self.assertIn(tri.RUN_ID, body)
        self.assertFalse(body.lower().startswith(("none", "not run")))
        gate.check_body_text(text, "entry")

    def test_the_normal_entry_is_unchanged(self):
        text = gate.impact_entry(tri.record(), "adam-anything-anywhere", tri.RUN_ID,
                                 ("1.2.3", "1.2.4"), False, "auto")
        self.assertIn("train checks failed", text)
        self.assertNotIn("trigger-only", text)


class FireCheckTriggerTests(unittest.TestCase):

    def check(self, skill, holdout=""):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = gate.main(["fire-check", skill, f"--holdout={holdout}", "--trigger-only"])
        return code, err.getvalue()

    def assert_rejected(self, skill, message, holdout=""):
        code, err = self.check(skill, holdout)
        self.assertEqual((code, err), (1, f"rejected: {message}\n"))
        for value in (skill, holdout):
            if value and value not in message:
                self.assertNotIn(value, err)

    def test_accepts_writing_adrs_committed_set(self):
        self.assertEqual(self.check("writing-adrs"), (0, ""))

    def test_refuses_a_holdout(self):
        self.assert_rejected("writing-adrs", gate.FIRE_TRIGGER_HOLDOUT, "bootstrap")

    def test_refuses_a_skill_with_no_set(self):
        self.assert_rejected("no-such-skill-xyz", gate.FIRE_NO_TRIGGER_SET)
        self.assert_rejected("../evals", gate.FIRE_NOT_A_SKILL_NAME)

    def evals(self, sets: dict, fixtures: dict = (), commit=True):
        """A committed scratch evals/ tree: {skill: set items}, {rel: fixture}."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        evals = root / "evals"
        for skill, items in sets.items():
            (evals / skill).mkdir(parents=True, exist_ok=True)
            (evals / skill / "trigger-eval-set.json").write_text(json.dumps(items))
        for rel, doc in dict(fixtures).items():
            (evals / rel).mkdir(parents=True)
            (evals / rel / "fixture.yaml").write_text(yaml.safe_dump(doc))
        env = dict(os.environ, **tri.GIT_ENV)
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True, env=env)
        if commit:
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, env=env)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "x"],
                           check=True, env=env)
        return mock.patch.object(pse, "EVALS_DIR", evals)

    def test_synthetic_layouts(self):
        sk, url = "zqx-synthetic", gate.REGISTRY_URL
        with self.evals({sk: REVIEWED_8}):
            self.assertEqual(self.check(sk), (0, ""), "zero fixtures is fine")
        with self.evals({sk: REVIEWED_8}, {f"{sk}/a": {"skill": sk, "registry": url}}):
            self.assertEqual(self.check(sk), (0, ""), "one fixture is fine")
        with self.evals({sk: REVIEWED_8[1:]}):
            self.assert_rejected(sk, gate.FIRE_TRIGGER_SET_UNUSABLE)
        with self.evals({sk: [{"query": "q", "should_trigger": "yes"}]}):
            self.assert_rejected(sk, gate.FIRE_TRIGGER_SET_UNUSABLE)
        with self.evals({sk: REVIEWED_8}, commit=False):
            self.assert_rejected(sk, gate.FIRE_NO_TRIGGER_SET)
        with self.evals({sk: REVIEWED_8}, {f"{sk}/a": {
                "skill": sk, "registry": "https://github.com/Adam-S-Daniel/cms-platform"}}):
            self.assert_rejected(sk, gate.FIRE_NOT_ROUTINE_REGISTRY)
        with self.evals({sk: REVIEWED_8}, {f"{sk}/a": {
                "skill": sk, "registry": "https://example.com/r"}}):
            self.assert_rejected(sk, gate.FIRE_NOT_ROUTINE_REGISTRY)

    def test_a_symlinked_set_is_refused(self):
        sk = "zqx-synthetic"
        with self.evals({"other": REVIEWED_8}) as evals:
            (evals / sk).mkdir()
            (evals / sk / "trigger-eval-set.json").symlink_to(
                evals / "other" / "trigger-eval-set.json")
            self.assert_rejected(sk, gate.FIRE_NO_TRIGGER_SET)

    def test_messages_are_distinct(self):
        messages = (gate.FIRE_TRIGGER_HOLDOUT, gate.FIRE_NOT_A_SKILL_NAME,
                    gate.FIRE_NO_TRIGGER_SET, gate.FIRE_TRIGGER_SET_UNUSABLE,
                    gate.FIRE_NOT_ROUTINE_REGISTRY, gate.FIRE_NOT_A_SKILL)
        self.assertEqual(len(set(messages)), len(messages))


# ---------------------------------------------------------------------------
# improve_outcomes / allowance guard

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def fire(run_id, title, started, conclusion="success", status="completed"):
    stamp = started.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": run_id, "display_title": title, "run_started_at": stamp,
            "created_at": stamp, "updated_at": (started + timedelta(minutes=30)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"), "conclusion": conclusion, "status": status}


class TitleTests(unittest.TestCase):

    def test_trigger_titles(self):
        self.assertEqual(outcomes.parse_title("Fire eval routine: improve trigger writing-adrs "),
                         {"mode": "improve", "target": "writing-adrs", "model": None,
                          "bare": False, "trigger": True})
        # A skill named `trigger` is a target, not a flag.
        self.assertEqual(outcomes.parse_title("Fire eval routine: improve trigger "),
                         {"mode": "improve", "target": "trigger", "model": None,
                          "bare": False, "trigger": False})
        for bad in ("Fire eval routine: eval trigger x ",
                    "Fire eval routine: eval trigger evals/x claude-opus-5-5",
                    "Fire eval routine: scaffold trigger a__b__1 ",
                    "Fire eval routine: guidance-improve trigger some-section ",
                    "Fire eval routine: improve bare trigger x ",
                    "Fire eval routine: improvetrigger x "):
            with self.subTest(bad=bad):
                self.assertIsNone(outcomes.parse_title(bad))

    def test_the_workflow_renders_the_trigger_title(self):
        template = yaml.safe_load(WORKFLOW.read_text())["run-name"]
        self.assertIn(TRIGGER_EXPRESSION, template)
        render = planner_tests.render_title
        title = render(template, mode="improve", skill="writing-adrs", trigger_only="true",
                       arms="both")
        self.assertNotIn("${{", title)
        self.assertTrue(outcomes.parse_title(title)["trigger"])
        for inputs in ({"mode": "improve", "trigger_only": "false"}, {"mode": "improve"},
                       {"mode": "eval", "trigger_only": "true", "fixture": "evals/x"}):
            with self.subTest(**inputs):
                parsed = outcomes.parse_title(render(template, skill="writing-adrs"
                                                     if inputs["mode"] == "improve" else "",
                                                     arms="both", **inputs))
                self.assertFalse(parsed["trigger"])

    def test_trigger_fires_are_improve_attempts_of_their_skill(self):
        t = NOW - timedelta(days=2)
        runs = [fire(1, "Fire eval routine: improve writing-adrs ", t),
                fire(2, "Fire eval routine: improve trigger writing-adrs ",
                     t + timedelta(hours=1)),
                fire(3, "Fire eval routine: eval trigger evals/x m", t)]
        fires = outcomes.improve_fires(runs)
        self.assertEqual([(f["id"], f["skill"], f["trigger"]) for f in fires],
                         [(1, "writing-adrs", False), (2, "writing-adrs", True)])
        self.assertEqual([f["id"] for f in outcomes.charged_fires(runs)], [1, 2])
        branch = (t + timedelta(hours=1, minutes=1)).strftime("%Y%m%dT%H%M%SZ") + "-abcdef"
        records = outcomes.outcomes(runs, [{"run_id": branch, "skill": "writing-adrs"}], NOW)
        self.assertEqual([r["outcome"] for r in records], ["rejected", "accepted"])
        # Charged exactly as the same fire without the flag.
        plain = [dict(r, display_title=r["display_title"].replace(" trigger", ""))
                 if r["id"] == 2 else r for r in runs]
        self.assertEqual(allowance_guard.improve_counts(runs, NOW),
                         allowance_guard.improve_counts(plain, NOW))
        self.assertEqual(allowance_guard.improve_counts(runs, NOW)[0], 2)
        self.assertEqual(allowance_guard.improve_kind_counts(runs, NOW),
                         allowance_guard.improve_kind_counts(plain, NOW))


# ---------------------------------------------------------------------------
# routine-eval-fire.yml and the routine prompt


class WorkflowShapeTests(unittest.TestCase):

    def setUp(self):
        self.doc = yaml.safe_load(WORKFLOW.read_text())

    def test_the_input(self):
        inputs = self.doc[True]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["trigger_only"],
                         {"description": inputs["trigger_only"]["description"],
                          "required": False, "type": "choice",
                          "options": ["false", "true"], "default": "false"})
        self.assertIn("skills-evals#662", inputs["trigger_only"]["description"])

    def test_the_fire_step_reads_the_validated_value(self):
        step = next(s for s in self.doc["jobs"]["fire"]["steps"]
                    if s.get("name") == "Fire the eval routine")
        self.assertEqual(step["env"]["TRIGGER_ONLY"],
                         "${{ steps.validate.outputs.trigger_only }}")


@unittest.skipUnless(shutil.which("jq") and shutil.which("git"), "needs jq and git on PATH")
class ValidateStepTests(unittest.TestCase):
    setUp = fire_tests.ValidateStepTests.setUp
    run_step = fire_tests.ValidateStepTests.run_step

    def improve(self, **extra):
        return {"mode": "improve", "candidate": "", "fixture": "", "skill": "writing-adrs",
                "holdout": "", "arms": "both", "trials": "1", **extra}

    def test_accepts_a_trigger_only_improve_fire(self):
        proc, values = self.run_step(self.improve(trigger_only="true"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(values["trigger_only"], "true")
        self.assertIn("trigger_only: true", proc.stdout)

    def test_the_default_is_false(self):
        proc, values = self.run_step(self.improve())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(values["trigger_only"], "false")

    def test_refusals(self):
        cases = {
            "word": (self.improve(trigger_only="yes"), "must be false or true"),
            "case": (self.improve(trigger_only="True"), "must be false or true"),
            "bool": (self.improve(trigger_only=True), "not a string"),
            "holdout": (self.improve(trigger_only="true", holdout="bootstrap"),
                        "'holdout' must be empty when 'trigger_only' is true"),
            "no set": (self.improve(trigger_only="true", skill="skills-doctor"),
                       "refused by the trigger-only loop's check"),
            "eval mode": ({"mode": "eval", "fixture": fire_tests.FIXTURE, "arms": "both",
                           "trials": "1", "trigger_only": "true"},
                          "may be true in improve mode only"),
        }
        for name, (inputs, expect) in cases.items():
            with self.subTest(name):
                proc, values = self.run_step(inputs)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(expect, proc.stdout + proc.stderr)
                self.assertNotIn("run_id", values)


@unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
class FireStepTests(unittest.TestCase):
    BEARER = fire_tests.FireStepTests.BEARER
    SESSION = fire_tests.FireStepTests.SESSION
    setUp = fire_tests.FireStepTests.setUp
    run_step = fire_tests.FireStepTests.run_step
    ok_body = fire_tests.FireStepTests.ok_body

    def payload(self, **env):
        proc = self.run_step("200", self.ok_body(), MODE="improve", SKILL="writing-adrs",
                             TRIALS="1", HOLDOUT="", **env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        argv = json.loads((self.log / "argv.json").read_text())
        return json.loads(argv[argv.index("--data-binary") + 1])["text"]

    def test_the_sixth_key_only_when_true(self):
        default = self.payload()
        self.assertEqual(self.payload(TRIGGER_ONLY="false"), default)
        self.assertEqual(list(json.loads(default)),
                         ["run_id", "mode", "skill", "trials", "holdout"])
        sent = json.loads(self.payload(TRIGGER_ONLY="true"))
        self.assertEqual(list(sent), ["run_id", "mode", "skill", "trials", "holdout",
                                      "trigger_only"])
        self.assertIs(sent["trigger_only"], True)
        self.assertIn("trigger-only: `true`", self.summary.read_text())


class InstructionsTests(unittest.TestCase):

    def test_the_trigger_only_command_is_one_the_script_parses(self):
        text = INSTRUCTIONS.read_text()
        line = next(line for line in text.splitlines() if "--trigger-only --trigger-eval-set"
                    in line)
        words = shlex.split(line.split("scripts/propose_skill_edit.py", 1)[1])
        argv = [w.replace("$SKILL", SKILL).replace("$REG_SHA", "HEAD")
                .replace("$REG", "/r").replace("$SC", "/sc").replace("$RESULTS", "/out")
                for w in words]
        self.assertEqual(argv[0], SKILL)
        self.assertNotIn("--trials", argv)
        self.assertNotIn("--holdout", argv)
        args = pse.parse_args(argv)
        self.assertTrue(args.trigger_only)
        self.assertEqual(args.trigger_eval_set, Path(f"evals/{SKILL}/{pse.TRIGGER_SET_FILE}"))

    def test_the_payload_rule_and_the_fire_check(self):
        text = INSTRUCTIONS.read_text()
        self.assertIn('"trigger_only": true (only the JSON boolean true', text)
        self.assertIn('fire-check "$SKILL" --holdout= --trigger-only', text)


if __name__ == "__main__":
    unittest.main()
