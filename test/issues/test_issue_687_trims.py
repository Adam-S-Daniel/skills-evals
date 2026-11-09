#!/usr/bin/env python3
"""skills-evals#687: queue the length-waived description trims through the
improve lane.

adam-agentskills caps a description at 400 characters; ten eval-protected
skills over it carry a `length-limit` waiver in its
`scripts/skills_waivers.yml`. A trim is a fixed chore, not a value bet: it
stays fire mode `improve` with a `trim_description` input, so the branch,
gate, outcomes, cooldown and allowance charge are improve's. What is pinned
here:

  * `propose_skill_edit.py --trim-description`: it refuses the flags it would
    ignore; an already-short description is rejected with no model call; the
    reply is parsed strictly (shape, line break, length after whitespace is
    collapsed, unchanged); the decision is aggregate non-inferiority with at
    most one lost check per fixture, and an errored fixture rejects; every
    model call goes through a fake runner;
  * `improve_gate.py`: a trim record passes `check_record` and a tampered one
    is rejected (counts, rule, lengths); its constants equal the loop's;
    `apply` refuses a body change and a description over the cap; `prepare`
    removes exactly the skill's waiver, comments kept, and refuses a file it
    cannot edit safely; `impact_entry` writes a RAN-form Eval line;
    `fire-check --trim` takes the ordinary fixture check with no holdout;
  * improve_outcomes reads `Fire eval routine: improve trim <skill>` as an
    improve attempt;
  * plan_week: trims go before the value-ranked improve fires, under the
    improve cap and rule C, and exclude an ordinary or trigger-only fire for
    the same skill; private skills and an unreadable waiver file plan none;
    `description-trim` work items are never issue-routed; validate-fire;
  * routine-eval-fire.yml and routine-eval-weekly.yml, parsed as YAML and
    their steps run for real; the routine prompt's trim command parses.

Deterministic: no network, no sleep, no wall clock. Discovered and run by
test/run_tests.py.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "routine-eval-fire.yml"
WEEKLY = REPO_ROOT / ".github" / "workflows" / "routine-eval-weekly.yml"
INSTRUCTIONS = REPO_ROOT / "docs" / "routine" / "eval-runner-instructions.md"
#: IMPROVE MODE's own file, which the instructions file points to.
IMPROVE_MODE = REPO_ROOT / "docs" / "routine" / "modes" / "improve.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(TEST_DIR / "issues"))
sys.path.insert(0, str(TEST_DIR))

import allowance_guard  # noqa: E402
import improve_gate as gate  # noqa: E402
import improve_outcomes as outcomes  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import plan_week  # noqa: E402
import propose_skill_edit as pse  # noqa: E402
import test_issue_71 as t71  # noqa: E402
import test_issue_closed_loop_planner as planner_tests  # noqa: E402
import test_issue_routine_eval_fire as fire_tests  # noqa: E402
import test_issue_routine_improve as tri  # noqa: E402

SKILL = t71.SKILL
#: A description over the cap: 4 x 110 characters.
LONG_DESCRIPTION = " ".join(
    ["Use this skill to record a non-obvious architecture decision in a short "
     f"Nygard-style ADR under docs/decisions part {i}."
     for i in range(4)])
SHORT_DESCRIPTION = ("Record a non-obvious architecture decision as a Nygard-style ADR "
                     "under docs/decisions. Not for code comments.")
LONG_SKILL_MD = t71.ORIGINAL_SKILL_MD.replace(
    "description: Write an Architecture Decision Record when a decision needs context.",
    f"description: {LONG_DESCRIPTION}")
assert len(LONG_DESCRIPTION) > pse.TRIM_MAX_CHARS
assert LONG_SKILL_MD != t71.ORIGINAL_SKILL_MD

#: The fixture numbers the fake runner answers with: {fixture: (passed,
#: total, judge)} per phase, summed over three trials by fixture_metrics.
EVEN = {"bootstrap": (2, 4, None), "existing-convention": (3, 4, None),
        "supersede": (4, 4, None)}


def reply(description=SHORT_DESCRIPTION) -> str:
    return json.dumps({"description": description})


class TrimRunner(t71.FakeRunner):
    """The fake runner, answering the one proposal call with `answer`; the
    description loop is never called in trim mode."""

    def __init__(self, baseline=EVEN, candidate=EVEN, answer=None):
        super().__init__(baseline, candidate, answer if answer is not None else reply())
        self.prompts = []

    def propose(self, prompt, model):
        self.prompts.append((prompt, model))
        return super().propose(prompt, model)

    def run_description_loop(self, argv, *, cwd, skill_creator):
        raise AssertionError("trim mode ran skill-creator's loop")


def counts(passed, total=12):
    return {"passed": passed, "total": total}


def trim_block(baseline=None, candidate=None, **changes) -> dict:
    block = {"max_chars": 400, "original_chars": len(LONG_DESCRIPTION),
             "candidate_chars": len(SHORT_DESCRIPTION), "rule": pse.TRIM_RULE,
             "tolerance_checks": 0, "fixture_drop_checks": 1,
             "baseline": baseline or {"a": counts(6), "b": counts(9), "c": counts(12)},
             "candidate": candidate or {"a": counts(6), "b": counts(9), "c": counts(12)}}
    block.update(changes)
    return block


def trim_record(**changes) -> dict:
    """An accepted trim record in improve_trim()'s shape."""
    doc = {
        "schema": 1, "skill": tri.SKILL, "timestamp": "20261103T101500Z", "mode": "trim",
        "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, not badge input",
        "registry": {"name": "adam-agentskills",
                     "url": "https://github.com/Adam-S-Daniel/adam-agentskills",
                     "sha": tri.REGISTRY_SHA, "skill_md": tri.SKILL_MD},
        "models": {"arm": "model-a", "proposal": "model-j"}, "trials": 3, "no_judge": True,
        "description": {"original": LONG_DESCRIPTION, "candidate": SHORT_DESCRIPTION},
        "trim": trim_block(),
        "runs": {"baseline": "/tmp/b", "candidate": "/tmp/c"},
        "status": "accepted", "decision": "accepted",
        "reasons": ["objective checks passed over all fixtures 27/36 -> 27/36"],
        "files": {"patch": "/tmp/x.patch", "pr_body": "/tmp/x.pr-body.md",
                  "record": "/tmp/x.json"},
    }
    doc.update(changes)
    return doc


# The gate's scratch registry for apply/prepare: tri.ORIGINAL with a long
# description, and its trimmed form.
GATE_ORIGINAL = tri.ORIGINAL.replace("description: Write an ADR.",
                                     f"description: {LONG_DESCRIPTION}")
GATE_TRIMMED = GATE_ORIGINAL.replace(f"description: {LONG_DESCRIPTION}",
                                     f"description: {SHORT_DESCRIPTION}")


# ---------------------------------------------------------------------------
# propose_skill_edit.py --trim-description


class ArgTests(unittest.TestCase):

    def parse(self, *extra):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                return pse.parse_args([SKILL, "--trim-description", *extra]), ""
            except SystemExit:
                return None, err.getvalue()

    def test_flags_it_would_ignore_are_refused(self):
        for flags in (["--holdout", "bootstrap"], ["--rotation", "1"], ["--min-gain", ".2"],
                      ["--no-judge"], ["--trigger-eval-set", "x.json"],
                      ["--skill-creator", "/sc"], ["--trigger-only"]):
            with self.subTest(flags=flags):
                args, err = self.parse(*flags)
                self.assertIsNone(args)
                self.assertIn("--trim-description does not take", err)

    def test_trials_are_taken(self):
        args, _ = self.parse("--trials", "2")
        self.assertEqual((args.trim_description, args.trials), (True, 2))
        args, _ = self.parse()
        self.assertEqual(args.trials, pse.DEFAULT_TRIALS)


class ParseReplyTests(unittest.TestCase):

    def assert_invalid(self, text, message):
        with self.assertRaises(pse.InvalidProposal) as caught:
            pse.parse_trim_reply(text, LONG_DESCRIPTION)
        self.assertEqual(str(caught.exception), message)
        self.assertNotIn("zz-marker", str(caught.exception))

    def test_accepts_the_shape_fenced_or_not(self):
        self.assertEqual(pse.parse_trim_reply(reply(), LONG_DESCRIPTION), SHORT_DESCRIPTION)
        fenced = "```json\n" + reply() + "\n```"
        self.assertEqual(pse.parse_trim_reply(fenced, LONG_DESCRIPTION), SHORT_DESCRIPTION)
        spaced = reply("  Record   an ADR.\t")
        self.assertEqual(pse.parse_trim_reply(spaced, LONG_DESCRIPTION), "Record an ADR.")

    def test_the_cap_is_counted_after_whitespace_is_collapsed(self):
        exact = "x" * 400
        self.assertEqual(pse.parse_trim_reply(reply(exact), LONG_DESCRIPTION), exact)
        self.assertEqual(pse.parse_trim_reply(reply("x" * 399 + "   "), LONG_DESCRIPTION),
                         "x" * 399)
        self.assert_invalid(reply("x" * 401), pse.TRIM_REPLY_LENGTH)
        self.assert_invalid(reply("   "), pse.TRIM_REPLY_LENGTH)

    def test_refusals(self):
        self.assert_invalid(reply("first line\nzz-marker"), pse.TRIM_REPLY_NEWLINE)
        self.assert_invalid(reply("first line\rzz-marker"), pse.TRIM_REPLY_NEWLINE)
        # Unchanged is judged after whitespace is collapsed (and after the
        # length check, so an over-cap original fails on length first).
        with self.assertRaises(pse.InvalidProposal) as caught:
            pse.parse_trim_reply(reply("  " + SHORT_DESCRIPTION.replace(" ", "  ")),
                                 SHORT_DESCRIPTION)
        self.assertEqual(str(caught.exception), pse.TRIM_REPLY_UNCHANGED)
        self.assert_invalid(reply(LONG_DESCRIPTION), pse.TRIM_REPLY_LENGTH)
        for bad in ("zz-marker", "", json.dumps({"description": "x", "why": "zz-marker"}),
                    json.dumps({"text": "zz-marker"}), json.dumps(["zz-marker"]),
                    json.dumps({"description": 3}),
                    "Sure! " + reply(), reply() + " zz-marker"):
            with self.subTest(bad=bad):
                self.assert_invalid(bad, pse.TRIM_REPLY_MALFORMED)


def m(passed, total=12, error=None):
    return {"passed": passed, "total": total, "error": error}


class DecideTests(unittest.TestCase):
    NAMES = ["a", "b", "c"]

    def decide(self, baseline, candidate):
        return pse.decide_trim(dict(zip(self.NAMES, baseline)),
                               dict(zip(self.NAMES, candidate)), self.NAMES)

    def test_equal_is_accepted(self):
        accepted, reasons = self.decide([m(6), m(9), m(12)], [m(6), m(9), m(12)])
        self.assertTrue(accepted, reasons)
        self.assertIn("objective checks passed over all fixtures 27/36 -> 27/36", reasons)

    def test_aggregate_non_inferiority(self):
        # One lost check, bought back elsewhere: accepted.
        self.assertTrue(self.decide([m(6), m(9), m(11)], [m(5), m(10), m(11)])[0])
        # One lost check, not bought back: rejected.
        accepted, reasons = self.decide([m(6), m(9), m(12)], [m(5), m(9), m(12)])
        self.assertFalse(accepted)
        self.assertIn("the trimmed description passed fewer checks in aggregate", reasons)

    def test_no_fixture_may_lose_more_than_one(self):
        accepted, reasons = self.decide([m(6), m(9), m(10)], [m(4), m(12), m(12)])
        self.assertFalse(accepted)
        self.assertIn("fixture 'a' lost 2 checks, more than 1", reasons)

    def test_an_errored_or_mismatched_fixture_is_inconclusive(self):
        accepted, reasons = self.decide([m(6), m(9), m(12)],
                                        [m(6), m(None, None, "timeout"), m(12)])
        self.assertFalse(accepted)
        self.assertEqual(reasons, ["inconclusive: fixture 'b' errored on the candidate "
                                   "(timeout)"])
        self.assertFalse(self.decide([m(6), m(9), m(12)], [m(6), m(9, 11), m(12)])[0])
        self.assertFalse(self.decide([m(0, 0), m(9), m(12)], [m(0, 0), m(9), m(12)])[0])
        self.assertFalse(pse.decide_trim({"a": m(1)}, {}, ["a"])[0])


class TrimPipelineCase(t71.PipelineCase):

    def setUp(self):
        super().setUp()
        shutil.rmtree(self.registry)
        self.registry = t71.make_registry(self.tmp / "registry", LONG_SKILL_MD)

    def argv(self, *extra):
        return [SKILL, "--trim-description", "--registry",
                f"adam-agentskills={self.registry}", "--results-dir", str(self.results),
                *extra]

    def stem(self) -> Path:
        return self.results / "improvements" / SKILL / t71.TS


class PipelineTests(TrimPipelineCase):

    def test_accepts_and_writes_record_patch_and_pr_body(self):
        runner = TrimRunner()
        rc, out, err = self.run_main(runner)
        self.assertEqual(rc, pse.EXIT_ACCEPTED, out + err)
        self.assertEqual(len(runner.prompts), 1)
        prompt, model = runner.prompts[0]
        self.assertIn(LONG_DESCRIPTION, prompt)
        self.assertIn('{"description":', prompt)
        self.assertEqual(model, pse.proposal_model())
        # Both sides on every fixture, one whole-skill call each, no judge.
        calls = [c for c in runner.calls if c[0] == "run_eval"]
        self.assertEqual([c[1] for c in calls], ["baseline", "candidate"])
        for call in calls:
            self.assertIn("--no-judge", call[3])
            self.assertNotIn("--fixture", call[3])
        self.assertIn(f"description: {LONG_DESCRIPTION}", runner.seen_skill_md["baseline"])
        self.assertIn(f"description: {SHORT_DESCRIPTION}", runner.seen_skill_md["candidate"])
        record = self.record()
        self.assertEqual((record["status"], record["decision"], record["mode"]),
                         ("accepted", "accepted", "trim"))
        self.assertEqual(record["description"],
                         {"original": LONG_DESCRIPTION, "candidate": SHORT_DESCRIPTION})
        self.assertEqual(record["trim"]["baseline"]["bootstrap"], counts(6))
        self.assertEqual(record["trim"]["candidate"]["supersede"], counts(12))
        self.assertEqual(record["trim"]["candidate_chars"], len(SHORT_DESCRIPTION))
        patch = self.stem().with_suffix(".patch").read_text()
        self.assertEqual(sum(1 for line in patch.splitlines()
                             if line.startswith(("+", "-"))
                             and not line.startswith(("+++", "---"))), 2,
                         "only the description line moves")
        body = self.stem().with_name(t71.TS + ".pr-body.md").read_text()
        self.assertEqual(body.split("\n", 1)[0], gate.REPORT_TITLE.format(skill=SKILL))
        self.assertIn("| `bootstrap` | 6/12 | 6/12 |", body)
        gate.check_report(body, "report.md", SKILL)

    def test_the_accepted_record_passes_the_gate(self):
        rc, out, err = self.run_main(TrimRunner())
        self.assertEqual(rc, 0, out + err)
        found = gate.check_record(json.loads(json.dumps(self.record())), "summary.json",
                                  str(REPO_ROOT))
        self.assertEqual(found["skill"], SKILL)
        gate.check_patch(self.stem().with_suffix(".patch").read_text(), "skill.patch",
                         found["skill_md"])

    def test_an_already_short_description_makes_no_call(self):
        shutil.rmtree(self.registry)
        self.registry = t71.make_registry(self.tmp / "registry")
        rc, out, err = self.run_main(t71.NoCallRunner())
        self.assertEqual(rc, pse.EXIT_REJECTED, out + err)
        record = self.record()
        self.assertEqual((record["status"], record["reasons"]),
                         ("rejected", [pse.TRIM_ALREADY_SHORT]))
        self.assertFalse(self.stem().with_suffix(".patch").exists())

    def test_an_invalid_proposal_is_never_measured(self):
        cases = {"too long": reply("y" * 401), "newline": reply("a\nb"),
                 "unchanged": reply(LONG_DESCRIPTION), "shape": "no json here"}
        for name, answer in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.results, ignore_errors=True)
                runner = TrimRunner(answer=answer)
                rc, out, err = self.run_main(runner)
                self.assertEqual(rc, pse.EXIT_REJECTED, out + err)
                record = self.record()
                self.assertEqual((record["status"], record["decision"]),
                                 ("invalid-proposal", "rejected"))
                self.assertEqual([c for c in runner.calls if c[0] == "run_eval"], [])
                self.assertIsNone(record["description"]["candidate"])

    def test_a_worse_candidate_is_rejected(self):
        worse = dict(EVEN, bootstrap=(1, 4, None))
        rc, out, err = self.run_main(TrimRunner(candidate=worse))
        self.assertEqual(rc, pse.EXIT_REJECTED, out + err)
        record = self.record()
        self.assertEqual(record["status"], "rejected")
        self.assertIn("fixture 'bootstrap' lost 3 checks, more than 1", record["reasons"])
        self.assertFalse(self.stem().with_name(t71.TS + ".pr-body.md").exists())
        self.assertTrue(self.stem().with_suffix(".patch").exists())

    def test_a_fixture_missing_on_one_side_rejects(self):
        missing = {k: v for k, v in EVEN.items() if k != "supersede"}
        rc, out, err = self.run_main(TrimRunner(candidate=missing))
        self.assertEqual(rc, pse.EXIT_REJECTED, out + err)
        self.assertEqual(self.record()["reasons"],
                         ["inconclusive: fixture 'supersede' errored on the candidate "
                          "(missing_summary)"])

    def test_a_refused_measurement_is_a_refused_record(self):
        runner = t71.RefusingRunner("candidate")
        runner.proposal = reply()
        rc, out, err = self.run_main(runner)
        self.assertEqual(rc, pse.EXIT_REFUSED, out + err)
        record = self.record()
        self.assertEqual((record["status"], record["phase"]), ("refused", "candidate"))

    def test_dry_run_plans_without_calls_or_writes(self):
        rc, out, err = self.run_main(t71.NoCallRunner(), "--dry-run")
        self.assertEqual(rc, 0, err)
        planned = json.loads(out)
        self.assertEqual((planned["mode"], planned["max_chars"], planned["rule"]),
                         ("trim", 400, pse.TRIM_RULE))
        self.assertEqual(planned["fixtures"], t71.FIXTURES)
        self.assertFalse(self.results.exists())

    def test_fewer_than_the_minimum_fixtures_is_refused(self):
        with mock.patch.object(pse, "MIN_FIXTURES", 4):
            rc, _, err = self.run_main(t71.NoCallRunner())
        self.assertEqual(rc, pse.EXIT_REFUSED)
        self.assertIn("needs more fixtures", err)
        self.assertFalse(self.results.exists())


class RecordKeyTests(unittest.TestCase):

    def test_keys_the_trim_writer_writes_are_allowed(self):
        tree = ast.parse((REPO_ROOT / "scripts" / "propose_skill_edit.py").read_text())
        keys = set()
        for func in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                     and node.name in {"improve_trim", "write_record", "record_refusal"}):
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
        self.assertIn("trim", keys)
        self.assertLessEqual(keys, set(gate.TRIM_RECORD_ALLOWED))
        self.assertLessEqual(set(gate.TRIM_RECORD_REQUIRED), keys)

    def test_the_loop_gate_and_planner_share_their_constants(self):
        for name in ("TRIM_MAX_CHARS", "TRIM_TOLERANCE_CHECKS", "TRIM_FIXTURE_DROP_CHECKS",
                     "TRIM_RULE"):
            with self.subTest(name):
                self.assertEqual(getattr(gate, name), getattr(pse, name))
        self.assertEqual(plan_week.TRIM_MAX_CHARS, pse.TRIM_MAX_CHARS)
        self.assertEqual(plan_week.TRIM_MIN_FIXTURES, pse.MIN_FIXTURES)
        self.assertEqual((plan_week.WAIVERS_FILE, plan_week.LENGTH_WAIVER_CLASS),
                         (gate.WAIVERS_FILE, gate.LENGTH_WAIVER_CLASS))
        self.assertEqual(set(gate.TRIM_BLOCK_KEYS), set(trim_block()))


# ---------------------------------------------------------------------------
# improve_gate.py


class GateRecordTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        (self.repo / "evals" / tri.SKILL).mkdir(parents=True)

    def check(self, doc):
        return gate.check_record(doc, "summary.json", str(self.repo))

    def assert_rejected(self, doc, pattern):
        with self.assertRaises(ingest.Rejected) as caught:
            self.check(doc)
        self.assertRegex(str(caught.exception), pattern)

    def test_accepts_a_trim_record(self):
        self.assertEqual(self.check(trim_record())["skill_md"], tri.SKILL_MD)
        # One lost check bought back elsewhere is the rule's edge.
        self.check(trim_record(trim=trim_block(
            candidate={"a": counts(5), "b": counts(10), "c": counts(12)})))

    def test_the_acceptance_is_re_derived_from_the_counts(self):
        cases = {
            "aggregate drop": (trim_block(candidate={"a": counts(5), "b": counts(9),
                                                     "c": counts(12)}),
                               "fewer checks in aggregate"),
            "fixture drop": (trim_block(baseline={"a": counts(6), "b": counts(9),
                                                  "c": counts(10)},
                                        candidate={"a": counts(4), "b": counts(12),
                                                   "c": counts(12)}),
                             "lost more checks"),
            "unequal totals": (trim_block(candidate={"a": counts(6, 11), "b": counts(9),
                                                     "c": counts(12)}),
                               "different checks"),
            "fixture sets": (trim_block(candidate={"a": counts(6), "b": counts(9)}),
                             "same fixtures"),
            "bool count": (trim_block(candidate={"a": counts(True), "b": counts(9),
                                                 "c": counts(12)}),
                           "checks passed of run"),
            "over total": (trim_block(candidate={"a": counts(13), "b": counts(9),
                                                 "c": counts(12)}),
                           "checks passed of run"),
            "zero total": (trim_block(baseline={"a": counts(0, 0)},
                                      candidate={"a": counts(0, 0)}),
                           "checks passed of run"),
            "rule": (trim_block(rule="per-fixture-strict"), "not this gate's trim rule"),
            "tolerance": (trim_block(fixture_drop_checks=5), "not this gate's trim rule"),
            "cap": (trim_block(max_chars=1024), "not this gate's trim rule"),
            "chars lie": (trim_block(candidate_chars=10), "not within the cap"),
            "missing key": ({"rule": pse.TRIM_RULE}, "missing keys"),
        }
        for name, (block, pattern) in cases.items():
            with self.subTest(name):
                self.assert_rejected(trim_record(trim=block), pattern)

    def test_the_descriptions_are_checked(self):
        long = "x" * 401
        self.assert_rejected(trim_record(
            description={"original": LONG_DESCRIPTION, "candidate": long},
            trim=trim_block(candidate_chars=401)), "not within the cap")
        self.assert_rejected(trim_record(
            description={"original": LONG_DESCRIPTION, "candidate": "a\nb"},
            trim=trim_block(candidate_chars=3)), "not within the cap")
        self.assert_rejected(trim_record(
            description={"original": "short", "candidate": SHORT_DESCRIPTION},
            trim=trim_block(original_chars=5)), "was not over the cap")

    def test_mode_and_keys_must_agree(self):
        doc = trim_record()
        doc.pop("trim")
        self.assert_rejected(doc, "missing keys")
        self.assert_rejected(trim_record(split={"rotation": 0}), "unexpected keys")
        self.assert_rejected(trim_record(status="rejected"), "not accepted")
        self.assert_rejected(trim_record(mode="trimmed"), "unknown mode")
        self.assert_rejected(trim_record(trigger_only={}), "needs mode trigger-only")
        shutil.rmtree(self.repo / "evals" / tri.SKILL)
        self.assert_rejected(trim_record(), "no evals/ directory")


class GateValidateTests(tri.GitCase):
    """A whole trim branch through `validate`."""

    def files(self, record=None):
        return tri.good_files(
            summary_json=json.dumps(record or trim_record(), indent=2).encode(),
            skill_patch=tri.patch_text(old=GATE_ORIGINAL, new=GATE_TRIMMED).encode())

    def test_a_trim_branch_validates(self):
        self.commit(self.files())
        self.assertEqual(self.validate()["target_branch"], f"eval-improve/{tri.SKILL}")

    def test_a_tampered_trim_branch_is_rejected(self):
        bad = trim_record()
        bad["trim"]["candidate"]["a"]["passed"] = 3
        self.commit(self.files(bad))
        self.assertRejected("fewer checks in aggregate")


class GateApplyTests(unittest.TestCase):
    """`apply` refuses a body change or a long description for a trim record,
    on a scratch registry like test_issue_routine_improve's."""
    run_git = tri.ApplyTests.run_git
    stage = tri.ApplyTests.stage

    def setUp(self):
        tri.ApplyTests.setUp(self)
        (self.tree / tri.SKILL_MD).write_text(GATE_ORIGINAL, encoding="utf-8")
        self.run_git("commit", "-q", "-am", "long description")
        (self.staged / "summary.json").write_text(json.dumps(trim_record()), encoding="utf-8")

    def assert_rejected(self, pattern):
        with self.assertRaises(ingest.Rejected) as caught:
            gate.apply(self.staged, self.tree, tri.SKILL_MD)
        self.assertRegex(str(caught.exception), pattern)

    def test_a_trim_may_shorten_the_description(self):
        self.stage(tri.patch_text(old=GATE_ORIGINAL, new=GATE_TRIMMED))
        self.assertEqual(gate.apply(self.staged, self.tree, tri.SKILL_MD),
                         {"changed": tri.SKILL_MD})

    def test_a_trim_may_not_move_the_body(self):
        self.stage(tri.patch_text(old=GATE_ORIGINAL,
                                  new=GATE_TRIMMED + "One more line.\n"))
        self.assert_rejected("a trim patch changes the body")

    def test_a_trim_may_not_leave_the_description_over_the_cap(self):
        longer = GATE_ORIGINAL.replace(LONG_DESCRIPTION, "y" * 401)
        self.stage(tri.patch_text(old=GATE_ORIGINAL, new=longer))
        self.assert_rejected("not within the 400-character cap")


WAIVERS = textwrap.dedent("""\
    # Declared exemptions (header comment).
    #
    # More header.

    waivers:
      - klass: length-limit
        registry: adam-agentskills
        path: plugins/adam-coding-anywhere/skills/ci-job-performance/SKILL.md
        reason: >-
          Eval-protected: over the cap, trimmed through the improve lane.
        issue: https://github.com/Adam-S-Daniel/skills-evals/issues/668
      # A comment that belongs to the next entry.
      - klass: length-limit
        registry: adam-agentskills
        path: {skill_md}
        reason: >-
          Eval-protected: over the cap, trimmed through the improve lane,
          on two folded lines.
        issue: https://github.com/Adam-S-Daniel/skills-evals/issues/668

      - klass: length-limit
        registry: adam-agentskills
        path: plugins/adam-anything-anywhere/skills/fan-out-triage/SKILL.md
        reason: >-
          Eval-protected.
        issue: https://github.com/Adam-S-Daniel/skills-evals/issues/668
    # Trailing comment.
    """).format(skill_md=tri.SKILL_MD)


class WaiverRemovalTests(unittest.TestCase):

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree)
        (self.tree / "scripts").mkdir()
        self.path = self.tree / gate.WAIVERS_FILE

    def remove(self, text, skill_md=tri.SKILL_MD):
        self.path.write_text(text, encoding="utf-8")
        return gate.remove_length_waiver(self.tree, skill_md)

    def test_removes_exactly_the_one_entry_and_keeps_every_comment(self):
        self.assertTrue(self.remove(WAIVERS))
        after = self.path.read_text(encoding="utf-8")
        for comment in ("# Declared exemptions (header comment).",
                        "# A comment that belongs to the next entry.", "# Trailing comment."):
            self.assertIn(comment, after)
        self.assertNotIn(tri.SKILL_MD, after)
        self.assertNotIn("on two folded lines", after)
        before = yaml.safe_load(WAIVERS)["waivers"]
        self.assertEqual(yaml.safe_load(after)["waivers"], [before[0], before[2]])
        # Every other line is byte for byte what it was.
        removed = [line for line in WAIVERS.splitlines() if line not in after.splitlines()]
        # (klass, registry, reason and issue lines repeat in the other
        # entries, so only the three unique lines show here.)
        self.assertEqual(len(removed), 3, removed)
        self.assertEqual(len(after.splitlines()), len(WAIVERS.splitlines()) - 7)

    def test_the_first_and_the_last_entries(self):
        first = "plugins/adam-coding-anywhere/skills/ci-job-performance/SKILL.md"
        self.assertTrue(self.remove(WAIVERS, first))
        self.assertEqual([w["path"] for w in yaml.safe_load(self.path.read_text())["waivers"]],
                         [tri.SKILL_MD,
                          "plugins/adam-anything-anywhere/skills/fan-out-triage/SKILL.md"])
        last = "plugins/adam-anything-anywhere/skills/fan-out-triage/SKILL.md"
        self.assertTrue(self.remove(WAIVERS, last))
        self.assertIn("# Trailing comment.", self.path.read_text())
        self.assertEqual(len(yaml.safe_load(self.path.read_text())["waivers"]), 2)

    def test_the_only_entry_leaves_an_empty_list(self):
        only = "waivers:\n  - klass: length-limit\n    registry: adam-agentskills\n" \
               f"    path: {tri.SKILL_MD}\n    reason: r\n    issue: i\n"
        self.assertTrue(self.remove(only))
        self.assertEqual(self.path.read_text(), "waivers: []\n")
        self.assertEqual(yaml.safe_load(self.path.read_text()), {"waivers": []})

    def test_no_entry_or_no_file_leaves_everything_alone(self):
        self.assertFalse(gate.remove_length_waiver(self.tree, tri.SKILL_MD))
        other = WAIVERS.replace(tri.SKILL_MD, "plugins/x/skills/other/SKILL.md")
        self.assertFalse(self.remove(other))
        self.assertEqual(self.path.read_text(), other)
        # A waiver of another class for the skill is not this one.
        klass = WAIVERS.replace(f"  - klass: length-limit\n    registry: adam-agentskills\n"
                                f"    path: {tri.SKILL_MD}",
                                f"  - klass: yaml-parse\n    registry: adam-agentskills\n"
                                f"    path: {tri.SKILL_MD}")
        self.assertFalse(self.remove(klass))

    def test_a_file_it_cannot_edit_safely_is_rejected(self):
        twice = WAIVERS + textwrap.indent(
            "- klass: length-limit\n  registry: adam-agentskills\n"
            f"  path: {tri.SKILL_MD}\n  reason: r\n  issue: i\n", "  ")
        flow = ("waivers: [{klass: length-limit, registry: adam-agentskills, "
                f"path: {tri.SKILL_MD}, reason: r, issue: i}}]\n")
        for name, text in {"two entries": twice, "flow style": flow,
                           "not yaml": "waivers: [\n", "no list": "waivers: {}\n"}.items():
            with self.subTest(name):
                with self.assertRaises(ingest.Rejected):
                    self.remove(text)
                self.assertEqual(self.path.read_text(), text, "left untouched")


class PrepareTests(unittest.TestCase):
    """`prepare` for a trim record, on test_issue_routine_improve's scratch
    registry with a waiver file beside it (its helpers borrowed, not its
    tests)."""
    git = tri.PrepareTests.git
    write = tri.PrepareTests.write
    prepare = tri.PrepareTests.prepare
    changed = tri.PrepareTests.changed
    show = tri.PrepareTests.show

    def setUp(self):
        tri.PrepareTests.setUp(self)
        self.write({tri.SKILL_MD: GATE_ORIGINAL, gate.WAIVERS_FILE: WAIVERS})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "long description and waivers")
        self.measured = self.git("rev-parse", "HEAD")

    def stage(self, new=None, doc=None):
        tri.PrepareTests.stage(self, new=GATE_TRIMMED if new is None else new,
                      doc=doc or trim_record(registry={**trim_record()["registry"],
                                                       "skill_md": tri.SKILL_MD}))
        (self.staged / "skill.patch").write_text(
            tri.patch_text(old=GATE_ORIGINAL, new=GATE_TRIMMED if new is None else new),
            encoding="utf-8")

    def test_a_trim_removes_its_waiver_in_the_content_commit(self):
        self.stage()
        out = self.prepare()
        skill_dir = f"plugins/{tri.PLUGIN}/skills/{tri.SKILL}"
        self.assertIn(gate.WAIVERS_FILE, self.changed())
        self.assertIn(gate.WAIVERS_FILE,
                      self.git("show", "--name-only", "--format=", out["content_sha"]))
        self.assertNotIn(tri.SKILL_MD, self.show(gate.WAIVERS_FILE))
        self.assertIn("# A comment that belongs to the next entry.",
                      self.show(gate.WAIVERS_FILE))
        self.assertEqual(self.show(f"{skill_dir}/SKILL.md"), GATE_TRIMMED)
        entry = self.show("docs/skill-impact.md")
        self.assertIn("skills-evals#687", entry)
        self.assertIn(f"its `length-limit` waiver removed from `{gate.WAIVERS_FILE}`", entry)

    def test_a_trim_with_no_waiver_leaves_the_file_alone(self):
        self.write({gate.WAIVERS_FILE: WAIVERS.replace(tri.SKILL_MD, "plugins/x/skills/y/SKILL.md")})
        self.git("commit", "-q", "-am", "no waiver for the skill")
        self.measured = self.git("rev-parse", "HEAD")
        self.stage()
        self.prepare()
        self.assertNotIn(gate.WAIVERS_FILE, self.changed())
        self.assertNotIn("waiver removed", self.show("docs/skill-impact.md"))

    def test_an_ordinary_record_never_touches_the_waivers(self):
        new = GATE_ORIGINAL.replace("Step one.", "Step one, carefully.") \
            if "Step one." in GATE_ORIGINAL else GATE_ORIGINAL + "Extra.\n"
        tri.PrepareTests.stage(self, new=new)
        (self.staged / "skill.patch").write_text(
            tri.patch_text(old=GATE_ORIGINAL, new=new), encoding="utf-8")
        self.prepare()
        self.assertNotIn(gate.WAIVERS_FILE, self.changed())


class ImpactEntryTests(unittest.TestCase):

    def test_trim_entry(self):
        text = gate.impact_entry(trim_record(), "adam-anything-anywhere", tri.RUN_ID,
                                 ("1.2.3", "1.2.4"), False, "auto", True)
        self.assertTrue(text.startswith(
            f"## 2026-11-03 — adam-anything-anywhere/{tri.SKILL} — edit\n"))
        self.assertIn("skills-evals#687", text)
        self.assertIn(f"from {len(LONG_DESCRIPTION)} to {len(SHORT_DESCRIPTION)} characters",
                      text)
        self.assertIn("body unchanged", text)
        eval_line = next(line for line in text.splitlines() if line.startswith("- Eval:"))
        self.assertIn("a 6/12 -> 6/12; b 9/12 -> 9/12; c 12/12 -> 12/12; "
                      "all fixtures 27/36 -> 27/36", eval_line)
        # adam-agentskills' check_skill_gates.py RAN form: a pass count or a
        # run id, on a line that does not start with `none` or `not run`.
        body = eval_line[len("- Eval:"):].strip()
        self.assertRegex(body, r"\b\d+/\d+\b")
        self.assertIn(tri.RUN_ID, body)
        self.assertFalse(body.lower().startswith(("none", "not run")))
        gate.check_body_text(text, "entry")
        self.assertNotIn("waiver removed",
                         gate.impact_entry(trim_record(), "p", tri.RUN_ID, ("1", "2"),
                                           False, "auto"))


class FireCheckTrimTests(unittest.TestCase):

    def check(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                code = gate.main(["fire-check", *argv])
            except SystemExit as exc:
                code = exc.code
        return code, err.getvalue()

    def test_accepts_writing_adrs(self):
        self.assertEqual(self.check("writing-adrs", "--holdout=", "--trim"), (0, ""))

    def test_refusals_never_echo_input(self):
        self.assertEqual(self.check("writing-adrs", "--holdout=bootstrap", "--trim"),
                         (1, f"rejected: {gate.FIRE_TRIM_HOLDOUT}\n"))
        code, err = self.check("zz-no-such-skill", "--holdout=", "--trim")
        self.assertEqual((code, err), (1, f"rejected: {gate.FIRE_NOT_A_SKILL}\n"))
        with self.assertRaises(gate.Rejected) as caught:
            gate.fire_check("writing-adrs", "", trigger_only=True, trim=True)
        self.assertEqual(str(caught.exception), gate.FIRE_TRIM_AND_TRIGGER)
        code, _ = self.check("writing-adrs", "--trim", "--trigger-only")
        self.assertEqual(code, 2, "argparse refuses both flags")


# ---------------------------------------------------------------------------
# improve_outcomes / allowance guard

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def fire(run_id, title, started, conclusion="success", status="completed"):
    stamp = started.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": run_id, "display_title": title, "run_started_at": stamp,
            "created_at": stamp, "updated_at": (started + timedelta(minutes=30)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"), "conclusion": conclusion, "status": status}


class TitleTests(unittest.TestCase):

    def test_trim_titles(self):
        self.assertEqual(outcomes.parse_title("Fire eval routine: improve trim writing-adrs "),
                         {"mode": "improve", "target": "writing-adrs", "model": None,
                          "bare": False, "trigger": False, "trim": True})
        # A skill named `trim` is a target, not a flag.
        self.assertEqual(outcomes.parse_title("Fire eval routine: improve trim ")["target"],
                         "trim")
        for bad in ("Fire eval routine: eval trim evals/x ",
                    "Fire eval routine: guidance-improve trim some-section ",
                    "Fire eval routine: improve trigger trim x "):
            with self.subTest(bad=bad):
                self.assertIsNone(outcomes.parse_title(bad))

    def test_the_workflow_renders_the_trim_title(self):
        template = yaml.safe_load(WORKFLOW.read_text())["run-name"]
        self.assertIn(planner_tests.TRIM_EXPRESSION, template)
        render = planner_tests.render_title
        title = render(template, mode="improve", skill="writing-adrs", trim_description="true",
                       arms="both")
        self.assertNotIn("${{", title)
        self.assertEqual(title, "Fire eval routine: improve trim writing-adrs ")
        self.assertTrue(outcomes.parse_title(title)["trim"])
        title = render(template, mode="eval", fixture="evals/x", trim_description="true",
                       arms="both")
        self.assertFalse(outcomes.parse_title(title)["trim"])

    def test_trim_fires_are_improve_attempts_of_their_skill(self):
        t = NOW - timedelta(days=2)
        runs = [fire(1, "Fire eval routine: improve writing-adrs ", t),
                fire(2, "Fire eval routine: improve trim writing-adrs ",
                     t + timedelta(hours=1))]
        fires = outcomes.improve_fires(runs)
        self.assertEqual([(f["id"], f["skill"], f["trim"]) for f in fires],
                         [(1, "writing-adrs", False), (2, "writing-adrs", True)])
        plain = [dict(r, display_title=r["display_title"].replace(" trim", ""))
                 if r["id"] == 2 else r for r in runs]
        self.assertEqual(allowance_guard.improve_counts(runs, NOW),
                         allowance_guard.improve_counts(plain, NOW))
        self.assertEqual(allowance_guard.improve_counts(runs, NOW)[0], 2)


# ---------------------------------------------------------------------------
# plan_week.py

skill = planner_tests.skill
ctx = planner_tests.ctx


class PlannerTests(unittest.TestCase):

    def plan(self, **over):
        base = {"room": 1.0, "improve_charge": 0.10}
        base.update(over)
        return plan_week.build_plan(ctx(**base), planner_tests.NOW)

    def test_trims_go_before_the_value_ranked_improve_fires(self):
        plan = self.plan(skills={"a": skill(), "w": skill(fixtures=3, headroom=0.0)},
                         trims={"w": {"chars": 900}})
        improve = [(f["skill"], f["trim_description"]) for f in plan["fires"]
                   if f["mode"] == "improve"]
        self.assertEqual(improve, [("w", "true"), ("a", "false")])
        trim = next(f for f in plan["fires"] if f["skill"] == "w")
        self.assertEqual((trim["holdout"], trim["change_type"], trim["value"], trim["cost"]),
                         ("", "skill-edit", None, 0.10))
        leg = next(r for r in plan["matrix"]["include"] if r["skill"] == "w")
        self.assertEqual((leg["trim_description"], leg["trigger_only"], leg["holdout"]),
                         ("true", "false", ""))
        self.assertTrue(all(r["trim_description"] == "false"
                            for r in plan["matrix"]["include"] if r["skill"] != "w"))
        self.assertEqual(plan["trims"], {"w": {"eligible": True, "reasons": [], "chars": 900,
                                               "planned": True}})
        self.assertIsNone(plan["trims_unread"])
        self.assertEqual(plan["work"][0], {"kind": "description-trim",
                                           "change_type": "skill-edit", "skill": "w",
                                           "chars": 900, "route": "fire"})
        self.assertIn("Description trims: w (planned)", plan_week.summary_lines(plan))
        self.assertIn(f"- improve: improve w (description trim), 10.00 points",
                      plan_week.summary_lines(plan))

    def test_the_improve_cap_takes_trims_first(self):
        state = {"cap": 0.30, "improve_charge": 0.06, "improve_by_kind": {},
                 "improve_in_flight": {}}
        plan = self.plan(skills={"a": skill(), "w": skill()}, trims={"w": {"chars": 900}},
                         improve_charge=0.06, improve_state=state)
        self.assertEqual([(f["skill"], f["trim_description"]) for f in plan["fires"]],
                         [("w", "true")])
        plan = self.plan(skills={"w": skill(), "v": skill()},
                         trims={"w": {"chars": 900}, "v": {"chars": 800}},
                         improve_charge=0.06, improve_state=state)
        self.assertEqual([f["skill"] for f in plan["fires"]], ["v"])
        routes = {w["skill"]: w["route"] for w in plan["work"]
                  if w["kind"] == "description-trim"}
        self.assertEqual(routes, {"v": "fire", "w": "the improve cap is reached"})
        self.assertFalse(plan["trims"]["w"]["planned"])

    def test_a_trim_excludes_another_improve_fire_for_its_skill(self):
        plan = self.plan(skills={"w": skill()}, trims={"w": {"chars": 900}},
                         triggers={"w": {"trigger_set": True, "hook_candidate": False}},
                         skill_weights={"w": 0})
        self.assertEqual([(f["skill"], f["trim_description"], f["trigger_only"])
                          for f in plan["fires"]], [("w", "true", "false")])
        self.assertEqual(plan["skills"]["w"]["deferred"], "a description trim is planned for it")
        self.assertEqual(plan["triggers"]["w"]["reasons"],
                         ["a description trim is planned for it"])

    def test_ineligible_trims_say_why(self):
        plan = self.plan(
            skills={"few": skill(fixtures=2), "paused": skill(paused="cooling down after a "
                                                                    "rejection"),
                    "foreign": skill(registry_ok=False), "retiring": skill(verdict="retire"),
                    "short": skill()},
            trims={"few": {"chars": 500}, "paused": {"chars": 500}, "foreign": {"chars": 500},
                   "retiring": {"chars": 500}, "short": {"chars": 400},
                   "nofixtures": {"chars": None}, "secret": {"chars": 900}},
            private_skills=frozenset({"secret"}))
        self.assertFalse(any(f.get("trim_description") == "true" for f in plan["fires"]))
        reasons = {name: v["reasons"][0] for name, v in plan["trims"].items()}
        self.assertEqual(reasons, {
            "few": "2 fixture(s), under 3",
            "paused": "cooling down after a rejection",
            "foreign": "its fixtures do not all name adam-agentskills",
            "retiring": "owned by retirement (retire)",
            "short": "already within the cap",
            "nofixtures": "no public fixtures under evals/ to measure a trim on"})
        self.assertNotIn("secret", json.dumps(plan))
        self.assertNotIn("secret", "\n".join(plan_week.summary_lines(plan)))
        routes = {w["skill"]: w["route"] for w in plan["work"]
                  if w["kind"] == "description-trim"}
        self.assertEqual(routes, reasons)

    def test_one_trim_per_plugin_at_a_time(self):
        plan = self.plan(skills={"v": skill(), "w": skill(), "x": skill()},
                         trims={"v": {"chars": 900, "plugin": "p"},
                                "w": {"chars": 900, "plugin": "p"},
                                "x": {"chars": 900, "plugin": "q"}})
        self.assertEqual([f["skill"] for f in plan["fires"] if f["trim_description"] == "true"],
                         ["v", "x"])
        self.assertEqual(plan["trims"]["w"]["reasons"],
                         ["another trim or improve attempt in plugin p is open or planned"])
        # A busy waived skill (paused itself) holds every other trim of its plugin.
        plan = self.plan(skills={"v": skill(paused="an attempt is in flight"), "w": skill()},
                         trims={"v": {"chars": 900, "plugin": "p", "busy": True},
                                "w": {"chars": 900, "plugin": "p"}})
        self.assertFalse(any(f["trim_description"] == "true" for f in plan["fires"]))
        self.assertEqual(plan["trims"]["w"]["reasons"],
                         ["another trim or improve attempt in plugin p is open or planned"])

    def test_an_unreadable_waiver_file_plans_no_trim_and_says_so(self):
        for trims in ({}, {"trims": None}):
            with self.subTest(trims=trims):
                plan = self.plan(skills={"w": skill()}, **trims)
                self.assertEqual(plan["trims"], {})
                self.assertEqual(plan["trims_unread"], plan_week.TRIMS_UNREAD)
                self.assertIn("Description trims: " + plan_week.TRIMS_UNREAD,
                              plan_week.summary_lines(plan))
                self.assertEqual([f["trim_description"] for f in plan["fires"]], ["false"])
        plan = self.plan(skills={"w": skill()}, trims={})
        self.assertIn("Description trims: none waived", plan_week.summary_lines(plan))

    def test_held_while_the_routine_is_down(self):
        plan = self.plan(skills={"w": skill()}, trims={"w": {"chars": 900}},
                         routine_down=planner_tests.NOW - timedelta(hours=1),
                         cells=[planner_tests.cell("evals/w/a", "heavy", "missing")])
        self.assertFalse(any(f["trim_description"] == "true" for f in plan["fires"]))
        self.assertEqual(plan["work"][0]["route"],
                         "not planned this sweep (no room, or the routine is down)")

    def test_trim_work_items_are_never_issue_routed(self):
        jq = shutil.which("jq")
        if jq is None:
            self.skipTest("jq is not installed")
        step = next(s for s in yaml.safe_load(WEEKLY.read_text())["jobs"]["plan"]["steps"]
                    if s.get("name") == "Extract the issue-routed work items")
        program = step["run"].split("jq '", 1)[1].split("' \\", 1)[0]
        plan = self.plan(skills={"w": skill()}, trims={"w": {"chars": 900}})
        out = json.loads(subprocess.run([jq, program], input=json.dumps(plan), text=True,
                                        capture_output=True, check=True).stdout)
        self.assertEqual(out["work"], [])


class TrimContextTests(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.registries = {"adam-agentskills": {"path": str(self.root)}}

    def write(self, rel, text):
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(text, encoding="utf-8")

    def test_reads_length_waivers_and_description_lengths(self):
        self.write(gate.WAIVERS_FILE, WAIVERS + textwrap.dedent("""\
            other: x
            """).replace("other: x\n", ""))
        self.write(tri.SKILL_MD, GATE_ORIGINAL)
        doc = yaml.safe_load(WAIVERS)
        doc["waivers"].append({"klass": "yaml-parse", "registry": "adam-agentskills",
                               "path": "plugins/p/skills/parse/SKILL.md"})
        doc["waivers"].append({"klass": "length-limit", "registry": "cms-platform",
                               "path": "plugins/p/skills/elsewhere/SKILL.md"})
        doc["waivers"].append({"klass": "length-limit", "registry": "adam-agentskills",
                               "path": "../escape/SKILL.md"})
        self.write(gate.WAIVERS_FILE, yaml.safe_dump(doc))
        self.assertEqual(plan_week.trim_contexts(self.registries), {
            "ci-job-performance": {"chars": None, "plugin": "adam-coding-anywhere"},
            tri.SKILL: {"chars": len(LONG_DESCRIPTION), "plugin": tri.SKILL_MD.split("/")[1]},
            "fan-out-triage": {"chars": None, "plugin": "adam-anything-anywhere"}})

    def test_busy_marks_an_in_flight_attempt_or_an_open_pull_request(self):
        trims = {"a": {"chars": 900, "plugin": "p"}, "b": {"chars": 900, "plugin": "p"},
                 "c": {"chars": 900, "plugin": "q"}, "d": {"chars": 900, "plugin": "q"}}
        records = [{"skill": "a", "outcome": "pending"}, {"skill": "c", "outcome": "rejected"}]
        prs = [{"skill": "d", "state": "open"}, {"skill": "b", "state": "merged"}]
        plan_week.trim_busy(trims, records, prs)
        self.assertEqual({n: i["busy"] for n, i in trims.items()},
                         {"a": True, "b": False, "c": False, "d": True})
        self.assertIsNone(plan_week.trim_busy(None, records, prs))

    def test_missing_or_unreadable_is_none(self):
        self.assertIsNone(plan_week.trim_contexts({}))
        self.assertIsNone(plan_week.trim_contexts(self.registries))
        for text in ("waivers: [\n", "waivers: {}\n", "- a\n"):
            with self.subTest(text=text):
                self.write(gate.WAIVERS_FILE, text)
                self.assertIsNone(plan_week.trim_contexts(self.registries))
        self.write(gate.WAIVERS_FILE, "waivers: []\n")
        self.assertEqual(plan_week.trim_contexts(self.registries), {})


class ValidateFireTests(unittest.TestCase):

    def leg(self, **env):
        base = {"MODE": "improve", "SKILL": "writing-adrs", "HOLDOUT": "",
                "TRIGGER_ONLY": "false", "TRIM_DESCRIPTION": "true"}
        base.update(env)
        return base

    def test_accepts_a_trim_leg(self):
        plan_week.validate_fire(self.leg())

    def test_refusals(self):
        cases = {
            "holdout": (self.leg(HOLDOUT="bootstrap"), "malformed"),
            "both": (self.leg(TRIGGER_ONLY="true"), "never both"),
            "word": (self.leg(TRIM_DESCRIPTION="yes"), "not true or false"),
            "eval": ({"MODE": "eval", "TRIM_DESCRIPTION": "true"},
                     "only an improve leg may be a description trim"),
            "fire check": (self.leg(SKILL="zz-no-such-skill"), "refused by the fire check"),
        }
        for name, (env, pattern) in cases.items():
            with self.subTest(name):
                with self.assertRaises(plan_week.PlanError) as caught:
                    plan_week.validate_fire(env)
                self.assertIn(pattern, str(caught.exception))


# ---------------------------------------------------------------------------
# The workflows and the routine prompt


class WorkflowShapeTests(unittest.TestCase):

    def test_the_input(self):
        doc = yaml.safe_load(WORKFLOW.read_text())
        inputs = doc[True]["workflow_dispatch"]["inputs"]
        self.assertEqual(inputs["trim_description"],
                         {"description": inputs["trim_description"]["description"],
                          "required": False, "type": "choice",
                          "options": ["false", "true"], "default": "false"})
        self.assertIn("skills-evals#687", inputs["trim_description"]["description"])
        step = next(s for s in doc["jobs"]["fire"]["steps"]
                    if s.get("name") == "Fire the eval routine")
        self.assertEqual(step["env"]["TRIM_DESCRIPTION"],
                         "${{ steps.validate.outputs.trim_description }}")

    def test_the_weekly_legs_carry_the_flag(self):
        doc = yaml.safe_load(WEEKLY.read_text())
        steps = [s for job in doc["jobs"].values() for s in job.get("steps", [])
                 if "TRIGGER_ONLY" in (s.get("env") or {})]
        self.assertEqual(len(steps), 2)
        for step in steps:
            self.assertEqual(step["env"]["TRIM_DESCRIPTION"], "${{ matrix.trim_description }}")


@unittest.skipUnless(shutil.which("jq") and shutil.which("git"), "needs jq and git on PATH")
class ValidateStepTests(unittest.TestCase):
    setUp = fire_tests.ValidateStepTests.setUp
    run_step = fire_tests.ValidateStepTests.run_step

    def improve(self, **extra):
        return {"mode": "improve", "candidate": "", "fixture": "", "skill": "writing-adrs",
                "holdout": "", "arms": "both", "trials": "3", **extra}

    def test_accepts_a_trim_and_defaults_to_false(self):
        proc, values = self.run_step(self.improve(trim_description="true"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(values["trim_description"], "true")
        self.assertIn("trim_description: true", proc.stdout)
        proc, values = self.run_step(self.improve())
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(values["trim_description"], "false")

    def test_refusals(self):
        cases = {
            "word": (self.improve(trim_description="yes"), "must be false or true"),
            "bool": (self.improve(trim_description=True), "not a string"),
            "holdout": (self.improve(trim_description="true", holdout="bootstrap"),
                        "'holdout' must be empty when 'trim_description' is true"),
            "both": (self.improve(trim_description="true", trigger_only="true"),
                     "may not both be true"),
            "no fixtures": (self.improve(trim_description="true", skill="zz-no-such-skill"),
                            "refused by the description trim's fixture check"),
            "eval mode": ({"mode": "eval", "fixture": fire_tests.FIXTURE, "arms": "both",
                           "trials": "1", "trim_description": "true"},
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
                             TRIALS="3", HOLDOUT="", **env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        argv = json.loads((self.log / "argv.json").read_text())
        return json.loads(argv[argv.index("--data-binary") + 1])["text"]

    def test_the_last_key_only_when_true(self):
        default = self.payload()
        self.assertEqual(self.payload(TRIM_DESCRIPTION="false"), default)
        self.assertEqual(list(json.loads(default)),
                         ["run_id", "mode", "skill", "trials", "holdout"])
        sent = json.loads(self.payload(TRIM_DESCRIPTION="true"))
        self.assertEqual(list(sent), ["run_id", "mode", "skill", "trials", "holdout",
                                      "trim_description"])
        self.assertIs(sent["trim_description"], True)
        self.assertIn("description trim: `true`", self.summary.read_text())


class InstructionsTests(unittest.TestCase):

    def test_the_trim_command_is_one_the_script_parses(self):
        text = IMPROVE_MODE.read_text()
        line = next(line for line in text.splitlines() if "--trim-description" in line
                    and "propose_skill_edit.py" in line)
        words = shlex.split(line.split("scripts/propose_skill_edit.py", 1)[1])
        argv = [w.replace("$SKILL", SKILL).replace("$REG_SHA", "HEAD")
                .replace("$REG", "/r").replace("$TRIALS", "3").replace("$RESULTS", "/out")
                for w in words]
        self.assertEqual(argv[0], SKILL)
        self.assertNotIn("--holdout", argv)
        args = pse.parse_args(argv)
        self.assertTrue(args.trim_description)
        self.assertEqual(args.trials, 3)

    def test_the_payload_rule_and_the_fire_check(self):
        self.assertIn('"trim_description": true (the same rule for that key; never both keys)',
                      INSTRUCTIONS.read_text())
        self.assertIn('fire-check "$SKILL" --holdout= --trim', IMPROVE_MODE.read_text())


if __name__ == "__main__":
    unittest.main()
