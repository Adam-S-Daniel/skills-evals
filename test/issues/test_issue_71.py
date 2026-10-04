#!/usr/bin/env python3
"""Issue #71 (smallest slice): scripts/propose_skill_edit.py.

Every model-spending step goes through the script's `Runner`, so these tests
drive the whole pipeline with a fake one: no `claude`, no network, no clock
(the timestamp is passed in). Two contract tests use the REAL subprocess
paths with stand-in CLIs instead of a fake runner: the harness's
`run_eval.py` under test/fake-claude, and Anthropic's skill-creator
`scripts/run_loop.py` under a stand-in `claude` on PATH. The second is skipped
when skill-creator is not installed (CI does not install it); point
SKILL_CREATOR_DIR at its skill directory to run it.

Discovered and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_71.py`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import propose_skill_edit as pse  # noqa: E402

SKILL = "writing-adrs"
FIXTURES = ["bootstrap", "existing-convention", "supersede"]
NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
TS = "20261004T120000Z"

ORIGINAL_SKILL_MD = textwrap.dedent("""\
    ---
    name: writing-adrs
    description: Write an Architecture Decision Record when a decision needs context.
    ---

    # Writing ADRs

    Step one: read the existing convention.
    Step two: write the record.
    """)

BODY_DIFF = textwrap.dedent("""\
    --- a/SKILL.md
    +++ b/SKILL.md
    @@ -6,4 +6,5 @@
     # Writing ADRs

     Step one: read the existing convention.
     Step two: write the record.
    +Step three: add the record to the index in the same change.
    """)

NEW_DESCRIPTION = "Use this skill to record a non-obvious decision as an ADR."


def make_registry(root: Path, text: str = ORIGINAL_SKILL_MD) -> Path:
    """A one-commit git repo laid out like adam-agentskills."""
    skill_dir = root / "plugins" / "demo" / "skills" / SKILL
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    (root / "README.md").write_text("fictional registry\n", encoding="utf-8")
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    for cmd in (["init", "-q", "-b", "main"], ["add", "-A"],
                ["-c", "user.name=t", "-c", "user.email=t@example.com",
                 "commit", "-q", "-m", "seed"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, env=env)
    return root


def make_skill_creator(root: Path) -> Path:
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "run_loop.py").write_text("# stand-in\n", encoding="utf-8")
    return root


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def write_arm(arm_dir: Path, passed: int, total: int, judge: float | None,
              trials: int = 3) -> None:
    """A with_skill arm in run_eval's --trials N > 1 layout."""
    for k in range(1, trials + 1):
        trial = arm_dir / f"trial-{k}"
        (trial / "transcripts").mkdir(parents=True)
        checks = [{"id": f"check-{i}", "passed": i < passed, "detail": f"detail {i}"}
                  for i in range(total)]
        (trial / "summary.json").write_text(json.dumps(
            {"error": None, "objective_checks": checks, "trial": k}), encoding="utf-8")
        (trial / "transcripts" / "raw.json").write_text(
            json.dumps({"result": f"reply of trial {k}"}), encoding="utf-8")
    judge_block = None
    if judge is not None:
        judge_block = {"n": trials, "errors": 0,
                       "overall": {"n": trials, "mean": judge, "min": judge,
                                   "max": judge, "sum": judge * trials},
                       "dimensions": []}
    (arm_dir / "summary.json").write_text(json.dumps({
        "error": None, "n": trials,
        "aggregate": {"objective": {"n": trials, "passed": passed * trials,
                                    "total": total * trials},
                      "judge": judge_block, "cost_usd": None}}), encoding="utf-8")


class FakeRunner:
    """Records every call; answers from canned numbers."""

    def __init__(self, baseline: dict, candidate: dict, proposal: str | None,
                 best_description: str | None = None):
        self.numbers = {"baseline": baseline, "candidate": candidate}
        self.proposal = proposal
        self.best_description = best_description
        self.calls: list[tuple] = []
        self.seen_skill_md: dict[str, str] = {}

    def run_eval(self, argv):
        label = Path(flag(argv, "--results-dir")).name
        registry = Path(flag(argv, "--registry").split("=", 1)[1])
        self.calls.append(("run_eval", label, registry, list(argv)))
        assert not (registry / ".git").exists(), "scratch registry carries .git"
        self.seen_skill_md[label] = (registry / "plugins" / "demo" / "skills"
                                     / SKILL / "SKILL.md").read_text(encoding="utf-8")
        base = Path(flag(argv, "--results-dir")) / SKILL / flag(argv, "--timestamp")
        for fixture, (passed, total, judge) in self.numbers[label].items():
            write_arm(base / fixture / "with_skill", passed, total, judge,
                      int(flag(argv, "--trials")))
        return 1

    def run_description_loop(self, argv, *, cwd, skill_creator):
        self.calls.append(("loop", list(argv), cwd, skill_creator))
        self.eval_set = json.loads(Path(flag(argv, "--eval-set")).read_text())
        self.loop_cwd_had_claude_dir = (Path(cwd) / ".claude").is_dir()
        original = pse.frontmatter_data(
            (Path(flag(argv, "--skill-path")) / "SKILL.md").read_text())["description"]
        best = self.best_description or original
        return {"best_description": best, "original_description": original,
                "best_test_score": "2/2", "best_train_score": "3/4",
                "iterations_run": 2}

    def propose(self, prompt, model):
        self.calls.append(("propose", prompt, model))
        if self.proposal is None:
            raise AssertionError("no proposal call expected")
        return self.proposal


class NoCallRunner:
    def __getattr__(self, name):
        raise AssertionError(f"dry run made a {name} call")


GOOD = {"bootstrap": (2, 4, 6.0), "existing-convention": (2, 4, 6.0),
        "supersede": (3, 4, 7.0)}


def proposal(diff: str = BODY_DIFF, rationale: str = "index step was missing") -> str:
    return "```json\n" + json.dumps({"rationale": rationale, "unified_diff": diff}) + "\n```"


class PipelineCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-issue-71-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.registry = make_registry(self.tmp / "registry")
        self.skill_creator = make_skill_creator(self.tmp / "skill-creator")
        self.results = self.tmp / "results"

    def argv(self, *extra):
        return [SKILL, "--registry", f"adam-agentskills={self.registry}",
                "--skill-creator", str(self.skill_creator),
                "--results-dir", str(self.results), *extra]

    def run_main(self, runner, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = pse.main(self.argv(*extra), runner=runner, now=NOW)
        return rc, out.getvalue(), err.getvalue()

    def record(self):
        return json.loads((self.results / "improvements" / SKILL / f"{TS}.json").read_text())


class SplitTests(unittest.TestCase):

    def test_split_is_deterministic_and_order_independent(self):
        self.assertEqual(pse.split_fixtures(["c", "a", "b"], 0), (["b", "c"], "a"))
        self.assertEqual(pse.split_fixtures(["a", "b", "c"], 0), (["b", "c"], "a"))

    def test_split_rotates(self):
        held = [pse.split_fixtures(FIXTURES, r)[1] for r in range(4)]
        self.assertEqual(held, FIXTURES + [FIXTURES[0]])

    def test_default_rotation_counts_existing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp)
            self.assertEqual(pse.default_rotation(records / "absent"), 0)
            for name in ("a.json", "b.json", "a.patch"):
                (records / name).write_text("{}")
            self.assertEqual(pse.default_rotation(records), 2)

    def test_fewer_than_three_fixtures_is_refused(self):
        with self.assertRaisesRegex(pse.Refusal, "needs more fixtures"):
            pse.split_fixtures(["a", "b"], 0)


class RefusalTests(PipelineCase):

    def test_a_flat_single_fixture_skill_exits_2(self):
        rc, _, err = self.run_main(NoCallRunner(), "--dry-run")
        self.assertEqual(rc, 0)  # sanity: writing-adrs itself plans fine
        argv = self.argv()
        argv[0] = "workflow-path-audit"
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(io.StringIO()):
            rc = pse.main(argv, runner=NoCallRunner(), now=NOW)
        self.assertEqual(rc, 2)
        self.assertIn("needs more fixtures", buf.getvalue())

    def test_two_nested_fixtures_exit_2(self):
        evals = self.tmp / "evals"
        for name in FIXTURES[:2]:
            shutil.copytree(REPO_ROOT / "evals" / SKILL / name, evals / SKILL / name)
        with mock.patch.object(pse, "EVALS_DIR", evals):
            rc, _, err = self.run_main(NoCallRunner())
        self.assertEqual(rc, 2)
        self.assertIn("needs more fixtures", err)
        self.assertFalse(self.results.exists())

    def test_missing_skill_creator_is_named(self):
        argv = self.argv()
        argv[argv.index("--skill-creator") + 1] = str(self.tmp / "nowhere")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = pse.main(argv, runner=NoCallRunner(), now=NOW)
        self.assertEqual(rc, 2)
        self.assertIn("--skill-creator", err.getvalue())


class DryRunTests(PipelineCase):

    def test_dry_run_makes_no_call_and_writes_nothing(self):
        rc, out, _ = self.run_main(NoCallRunner(), "--dry-run", "--rotation", "1")
        self.assertEqual(rc, 0)
        plan = json.loads(out)
        self.assertEqual(plan["validation"], "existing-convention")
        self.assertEqual(plan["train"], ["bootstrap", "supersede"])
        self.assertEqual(plan["models"]["arm"], "claude-sonnet-5")
        self.assertFalse(self.results.exists())


class AcceptTests(PipelineCase):

    def setUp(self):
        super().setUp()
        self.runner = FakeRunner(
            GOOD, {"bootstrap": (4, 4, 7.0), "existing-convention": (3, 4, 6.5),
                   "supersede": (3, 4, 7.0)}, proposal(), NEW_DESCRIPTION)
        self.rc, self.out, _ = self.run_main(self.runner, "--rotation", "2")

    def test_accepts_and_writes_record_patch_and_pr_body(self):
        self.assertEqual(self.rc, 0, self.out)
        record = self.record()
        self.assertEqual(record["status"], "accepted")
        self.assertEqual(record["split"], {"rotation": 2, "validation": "supersede",
                                           "train": ["bootstrap", "existing-convention"]})
        stem = self.results / "improvements" / SKILL / TS
        self.assertTrue(stem.with_suffix(".patch").is_file())
        body = (stem.parent / f"{TS}.pr-body.md").read_text()
        self.assertIn("| bootstrap | train | 6/12 | 12/12 | 6.00 | 7.00 |", body)
        self.assertIn("| supersede | validation | 9/12 | 9/12 | 7.00 | 7.00 |", body)
        self.assertIn(NEW_DESCRIPTION, body)
        self.assertIn("index step was missing", body)
        self.assertIn("ADR 0002", body)

    def test_both_halves_reach_the_measured_candidate(self):
        measured = self.runner.seen_skill_md["candidate"]
        self.assertIn("Step three: add the record to the index", measured)
        self.assertEqual(pse.frontmatter_data(measured)["description"], NEW_DESCRIPTION)
        self.assertEqual(pse.frontmatter_data(measured)["name"], SKILL)
        self.assertEqual(self.runner.seen_skill_md["baseline"], ORIGINAL_SKILL_MD)

    def test_patch_applies_to_the_registry_and_reproduces_the_candidate(self):
        patch = (self.results / "improvements" / SKILL / f"{TS}.patch").read_text()
        subprocess.run(["git", "-C", str(self.registry), "apply", "-"],
                       input=patch, text=True, check=True)
        applied = (self.registry / "plugins" / "demo" / "skills" / SKILL
                   / "SKILL.md").read_text()
        self.assertEqual(applied, self.runner.seen_skill_md["candidate"])

    def test_measurement_uses_the_harness_with_n_trials_on_with_skill(self):
        evals = [c for c in self.runner.calls if c[0] == "run_eval"]
        self.assertEqual([c[1] for c in evals], ["baseline", "candidate"])
        for _, _, _, argv in evals:
            self.assertEqual(flag(argv, "--arm"), "with_skill")
            self.assertEqual(flag(argv, "--trials"), "3")
            self.assertEqual(flag(argv, "--timestamp"), TS)
            self.assertEqual(Path(argv[0]), REPO_ROOT / "evals" / SKILL)

    def test_trigger_half_never_sees_the_validation_prompt(self):
        validation_prompt = " ".join(pse.run_eval.load_fixture(
            REPO_ROOT / "evals" / SKILL / "supersede")["prompt"].split())
        queries = [i["query"] for i in self.runner.eval_set]
        self.assertNotIn(validation_prompt, queries)
        positives = [i for i in self.runner.eval_set if i["should_trigger"]]
        self.assertEqual(len(positives), 2)
        self.assertTrue(any(not i["should_trigger"] for i in self.runner.eval_set))

    def test_skill_creator_loop_runs_in_a_scratch_project(self):
        _, argv, cwd, skill_creator = next(c for c in self.runner.calls if c[0] == "loop")
        self.assertTrue(self.runner.loop_cwd_had_claude_dir)
        self.assertFalse(Path(cwd).resolve().is_relative_to(REPO_ROOT))
        self.assertEqual(skill_creator, self.skill_creator.resolve())
        self.assertEqual(flag(argv, "--holdout"), "0.4")
        self.assertEqual(flag(argv, "--report"), "none")

    def test_proposal_prompt_carries_train_failures_only(self):
        _, prompt, model = next(c for c in self.runner.calls if c[0] == "propose")
        self.assertEqual(model, pse.proposal_model())
        self.assertIn('<fixture name="bootstrap">', prompt)
        self.assertNotIn('<fixture name="supersede">', prompt)
        self.assertIn("reply of trial 1", prompt)


class RejectTests(PipelineCase):

    def test_validation_drop_is_rejected_and_recorded_with_numbers(self):
        runner = FakeRunner(GOOD, {"bootstrap": (4, 4, 7.0),
                                   "existing-convention": (4, 4, 7.0),
                                   "supersede": (2, 4, 7.0)}, proposal())
        rc, _, _ = self.run_main(runner, "--rotation", "2")
        self.assertEqual(rc, 1)
        record = self.record()
        self.assertEqual(record["status"], "rejected")
        self.assertEqual(record["candidate"]["supersede"]["passed"], 6)
        self.assertEqual(record["baseline"]["supersede"]["passed"], 9)
        self.assertIn("validation objective fell", " ".join(record["reasons"]))
        self.assertFalse((self.results / "improvements" / SKILL / f"{TS}.pr-body.md").exists())
        self.assertTrue((self.results / "improvements" / SKILL / f"{TS}.patch").exists())

    def test_diff_touching_another_file_is_rejected_before_measurement(self):
        bad = BODY_DIFF.replace("a/SKILL.md", "a/README.md").replace("b/SKILL.md", "b/README.md")
        runner = FakeRunner(GOOD, {}, proposal(bad))
        rc, out, _ = self.run_main(runner)
        self.assertEqual(rc, 1)
        self.assertEqual([c[1] for c in runner.calls if c[0] == "run_eval"], ["baseline"])
        self.assertEqual(self.record()["status"], "invalid-proposal")
        self.assertIn("README.md", self.record()["reasons"][0])

    def test_diff_touching_the_frontmatter_is_rejected_before_measurement(self):
        bad = textwrap.dedent("""\
            --- a/SKILL.md
            +++ b/SKILL.md
            @@ -1,3 +1,3 @@
             ---
            -name: writing-adrs
            +name: writing-adrs-2
             description: Write an Architecture Decision Record when a decision needs context.
            """)
        runner = FakeRunner(GOOD, {}, proposal(bad))
        rc, _, _ = self.run_main(runner)
        self.assertEqual(rc, 1)
        self.assertEqual([c[1] for c in runner.calls if c[0] == "run_eval"], ["baseline"])
        self.assertIn("frontmatter", self.record()["reasons"][0])

    def test_no_change_from_either_half_measures_nothing(self):
        runner = FakeRunner(GOOD, {}, proposal(""))
        rc, _, _ = self.run_main(runner)
        self.assertEqual(rc, 1)
        self.assertEqual(self.record()["status"], "no-candidate")
        self.assertEqual(len([c for c in runner.calls if c[0] == "run_eval"]), 1)


class DiffTargetTests(unittest.TestCase):

    def test_other_targets_are_refused(self):
        for header in ("--- a/SKILL.md\n+++ b/references/x.md\n",
                       "--- /dev/null\n+++ b/SKILL.md\n",
                       "diff --git a/SKILL.md b/NEW.md\n--- a/SKILL.md\n+++ b/SKILL.md\n",
                       "--- a/SKILL.md\n+++ b/SKILL.md\nnew file mode 100644\n",
                       "@@ -1 +1 @@\n-a\n+b\n"):
            with self.subTest(header=header), self.assertRaises(pse.InvalidProposal):
                pse.check_diff_targets(header)
        pse.check_diff_targets(BODY_DIFF)


class DescriptionRewriteTests(unittest.TestCase):

    def test_only_the_description_changes(self):
        text = ("---\nname: x\ndescription: >\n  old words\n  more old\n"
                "license: MIT\n---\nbody\n")
        new = pse.set_description(text, 'Use it: when "quoted" things # matter')
        data = pse.frontmatter_data(new)
        self.assertEqual(data, {"name": "x", "license": "MIT",
                                "description": 'Use it: when "quoted" things # matter'})
        self.assertTrue(new.endswith("---\nbody\n"))

    def test_over_long_description_is_refused(self):
        with self.assertRaises(pse.InvalidProposal):
            pse.set_description(ORIGINAL_SKILL_MD, "x" * 1025)


def m(passed, total, judge=None, error=None):
    return {"passed": passed, "total": total, "judge_mean": judge, "error": error}


class DecisionTableTests(unittest.TestCase):
    """Accept only if validation held AND train improved (#71 step 3)."""

    TRAIN, VAL = ["t1", "t2"], "v"
    BASE = {"t1": m(2, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(3, 4, 7.0)}

    def check(self, candidate, expected):
        accepted, reasons = pse.decide(self.BASE, candidate, self.TRAIN, self.VAL)
        self.assertEqual(accepted, expected, reasons)

    def test_table(self):
        cases = [
            ("train up, validation equal", {"t1": m(3, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(3, 4, 7.0)}, True),
            ("train up, validation up", {"t1": m(3, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(4, 4, 7.0)}, True),
            ("train up, validation objective down", {"t1": m(4, 4, 6.0), "t2": m(4, 4, 6.0), "v": m(2, 4, 7.0)}, False),
            ("train up, validation judge down 0.6", {"t1": m(3, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(3, 4, 6.4)}, False),
            ("train up, validation judge down 0.5", {"t1": m(3, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(3, 4, 6.5)}, True),
            ("train flat", {"t1": m(2, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(4, 4, 9.0)}, False),
            ("train objective flat, train judge up", {"t1": m(2, 4, 7.0), "t2": m(2, 4, 7.0), "v": m(3, 4, 7.0)}, True),
            ("train down", {"t1": m(1, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(3, 4, 7.0)}, False),
            ("errored fixture", {"t1": m(4, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(3, 4, 7.0, "trial_errors")}, False),
            ("unscored fixture", {"t1": m(4, 4, 6.0), "t2": m(2, 4, 6.0), "v": m(0, 0)}, False),
        ]
        for name, candidate, expected in cases:
            with self.subTest(name):
                self.check(candidate, expected)

    def test_no_judge_compares_objective_only(self):
        base = {k: m(v["passed"], v["total"]) for k, v in self.BASE.items()}
        cand = {"t1": m(3, 4), "t2": m(2, 4), "v": m(3, 4)}
        self.assertTrue(pse.decide(base, cand, self.TRAIN, self.VAL)[0])


class ProposalParsingTests(unittest.TestCase):

    def test_fenced_and_bare_json_parse(self):
        self.assertEqual(pse.parse_proposal(proposal())["rationale"], "index step was missing")
        self.assertEqual(pse.parse_proposal('noise {"a": 1} {"rationale": "r", '
                                            '"unified_diff": ""}')["rationale"], "r")

    def test_wrong_shape_is_invalid(self):
        for reply in ("", "no json", '{"rationale": "r"}', '{"rationale": 1, "unified_diff": ""}'):
            with self.subTest(reply=reply), self.assertRaises(pse.InvalidProposal):
                pse.parse_proposal(reply)


class SubprocessRunnerContractTests(unittest.TestCase):
    """The real Runner's subprocess paths, with stand-in CLIs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="test-issue-71-runner-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_propose_sends_the_prompt_on_stdin_with_no_tools(self):
        fake = self.tmp / "claude"
        log = self.tmp / "log.json"
        fake.write_text(textwrap.dedent(f"""\
            #!{sys.executable}
            import json, sys
            json.dump({{"argv": sys.argv[1:], "stdin": sys.stdin.read()}},
                      open({str(log)!r}, "w"))
            print(json.dumps({{"result": "the reply"}}))
            """))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(fake)}):
            reply = pse.Runner().propose("the prompt", "model-x")
        self.assertEqual(reply, "the reply")
        seen = json.loads(log.read_text())
        self.assertEqual(seen["stdin"], "the prompt")
        argv = seen["argv"]
        self.assertEqual(flag(argv, "--tools"), "")
        self.assertEqual(flag(argv, "--permission-mode"), "default")
        self.assertEqual(flag(argv, "--model"), "model-x")
        self.assertNotIn("the prompt", argv)

    def test_run_eval_argv_is_accepted_and_its_tree_is_read(self):
        registry = make_registry(self.tmp / "registry")
        scratch = pse.archive_registry(registry, pse.resolve_ref(registry, "HEAD"),
                                       self.tmp / "scratch")
        self.assertFalse((scratch / ".git").exists())
        results = self.tmp / "results" / "runs" / "baseline"
        env = {"CLAUDE_BIN": str(TEST_DIR / "fake-claude"), "FAKE_CLAUDE_MODE": "agent"}
        with mock.patch.dict(os.environ, env), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = pse.Runner().run_eval(pse.run_eval_argv(
                SKILL, "adam-agentskills", scratch, results, TS, 2, True))
        self.assertIn(rc, (0, 1))
        for name in FIXTURES:
            arm = pse.run_paths(self.tmp / "results", "baseline", SKILL, TS, name)
            metrics = pse.fixture_metrics(arm)
            self.assertIsNone(metrics["error"], name)
            self.assertEqual(metrics["n"], 2)
            self.assertGreater(metrics["total"], 0)
            self.assertTrue(pse.failure_evidence(arm), name)


def _skill_creator_dir() -> Path | None:
    try:
        return pse.find_skill_creator(None)[0]
    except pse.Refusal:
        return None


@unittest.skipUnless(_skill_creator_dir(), "skill-creator not installed; set SKILL_CREATOR_DIR")
class SkillCreatorContractTests(unittest.TestCase):
    """Anthropic's own run_loop.py, unmodified, driven by our argv, with a
    stand-in `claude` on PATH: it triggers (names the command file skill-creator
    planted) only for a should-trigger query once the description carries
    IMPROVED, and answers the improvement call with such a description."""

    FAKE = textwrap.dedent("""\
        #!{python}
        import json, pathlib, sys
        argv = sys.argv[1:]
        if "text" in argv:
            sys.stdin.read()
            print("<new_description>IMPROVED: use this for ADRs</new_description>")
            sys.exit(0)
        query = argv[argv.index("-p") + 1]
        commands = sorted(pathlib.Path(".claude/commands").glob("*.md"))
        names = [p.stem for p in commands if "IMPROVED" in p.read_text()]
        content = []
        if names and "POSITIVE" in query:
            content = [{{"type": "tool_use", "name": "Skill",
                         "input": {{"skill": " ".join(names)}}}}]
        print(json.dumps({{"type": "assistant", "message": {{"content": content}}}}))
        print(json.dumps({{"type": "result"}}))
        """)

    def test_run_loop_picks_the_held_out_winner(self):
        tmp = Path(tempfile.mkdtemp(prefix="test-issue-71-sc-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "claude"
        fake.write_text(self.FAKE.format(python=sys.executable))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        skill_dir = tmp / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(ORIGINAL_SKILL_MD)
        eval_set = [{"query": f"POSITIVE query {i}", "should_trigger": True} for i in range(3)]
        eval_set += [{"query": f"negative query {i}", "should_trigger": False} for i in range(3)]
        eval_path = tmp / "eval-set.json"
        eval_path.write_text(json.dumps(eval_set))
        project = tmp / "project"
        (project / ".claude").mkdir(parents=True)
        argv = pse.description_loop_argv(eval_path, skill_dir, "model-x", tmp / "out")
        argv[argv.index("--max-iterations") + 1] = "2"
        argv[argv.index("--runs-per-query") + 1] = "1"
        env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        with mock.patch.dict(os.environ, env):
            out = pse.Runner().run_description_loop(
                argv, cwd=project, skill_creator=_skill_creator_dir())
        self.assertEqual(out["iterations_run"], 2)
        self.assertTrue(out["best_description"].startswith("IMPROVED"))
        self.assertEqual(out["best_test_score"], "2/2")
        self.assertEqual(list((project / ".claude" / "commands").glob("*.md")), [])


if __name__ == "__main__":
    unittest.main()
