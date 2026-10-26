#!/usr/bin/env python3
"""Issue #68 (first slice) / #372 U4: a `model` input on `routine-eval-fire.yml`.

The sweep runs each fixture on every roster arm, one dispatch per arm. What is
pinned here, on top of test_issue_routine_eval_fire.py:

  * `model` is an optional string input with no default;
  * it is valid in eval mode only, and when set it must be the `id` of an arm
    in the committed `evals/roster.yml` (`scripts/roster_arm.py`, which reads
    the roster with the harness's own reader and parses the YAML). The
    judge is not an arm. A refusal has a fixed message that never echoes the
    input;
  * the validation step reads it from `$GITHUB_EVENT_PATH` like the others,
    and no `run:` block interpolates `${{ inputs.* }}`;
  * the fire step's eval payload with `model` empty is byte for byte what it
    was before this input existed (so the weekly caller is unaffected), and
    with `model` set carries it as the last key; scaffold and improve
    payloads never carry it.

Discovered and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_68_model_input.py`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_issue_routine_eval_fire as base  # noqa: E402

REPO_ROOT = base.REPO_ROOT
SCRIPT = REPO_ROOT / "scripts" / "roster_arm.py"
ROSTER = REPO_ROOT / "evals" / "roster.yml"
FIXED_REFUSAL = "input 'model' is not an arm of the committed evals/roster.yml"


# Values an option parser would read as a flag, not as data.
OPTION_SHAPED = ("-h", "--help", "--he", "--roster=x", "--roster", "-x", "--",
                 "-", "-1", "--version")


def roster_doc() -> dict:
    return yaml.safe_load(ROSTER.read_text(encoding="utf-8"))


def arm_ids() -> list[str]:
    return [a["id"] for a in roster_doc()["arms"]]


class WorkflowInputTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = base.load(base.WORKFLOW)

    def test_model_is_an_optional_string_input_with_no_default(self):
        inputs = base.triggers(self.doc)["workflow_dispatch"]["inputs"]
        self.assertIn("model", inputs)
        self.assertEqual(inputs["model"]["type"], "string")
        self.assertIs(inputs["model"]["required"], False)
        self.assertNotIn("default", inputs["model"])

    def test_no_run_block_interpolates_an_input(self):
        runs = [(p, v) for p, v in base.scalars(self.doc) if p and p[-1] == "run"]
        self.assertTrue(runs)
        for path, value in runs:
            with self.subTest(path=path):
                self.assertNotIn("${{ inputs.", value)
                self.assertIsNone(base.FORBIDDEN_IN_RUN.search(value))

    def test_the_validation_step_checks_the_roster_with_the_script(self):
        script = base.step_script("Validate the dispatch inputs")
        self.assertIn("scripts/roster_arm.py", script)
        self.assertTrue(SCRIPT.is_file())

    def test_the_fire_step_gets_the_validated_model_from_step_outputs(self):
        steps = self.doc["jobs"]["fire"]["steps"]
        env = next(s for s in steps if s.get("name") == "Fire the eval routine")["env"]
        self.assertEqual(env["MODEL"], "${{ steps.validate.outputs.model }}")


class RosterArmScriptTests(unittest.TestCase):

    def run_script(self, *args, roster=None):
        cmd = [sys.executable, "-I", str(SCRIPT), *args]
        if roster is not None:
            cmd += ["--roster", str(roster)]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    def test_every_committed_arm_is_accepted(self):
        for arm in arm_ids():
            with self.subTest(arm=arm):
                proc = self.run_script(arm)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_the_judge_and_the_preflight_model_are_not_arms(self):
        doc = roster_doc()
        for name in ("judge", "preflight"):
            with self.subTest(name=name):
                proc = self.run_script(doc[name]["id"])
                self.assertEqual(proc.returncode, 1)

    def test_an_unknown_model_is_refused_without_echoing_it(self):
        for bad in ("claude-nonexistent-9", "", "claude-opus-5", " claude-opus-5-5",
                    "claude-opus-5-5\n", "CLAUDE-OPUS-5-5"):
            with self.subTest(bad=bad):
                proc = self.run_script(bad)
                self.assertEqual(proc.returncode, 1)
                self.assertIn(FIXED_REFUSAL, proc.stderr)
                if bad.strip():
                    self.assertNotIn(bad.strip(), proc.stdout + proc.stderr)

    def test_an_option_shaped_model_is_refused_not_parsed(self):
        # Review round 1, B1: argparse answered `-h` with its help and exit
        # 0, so the workflow took it for an arm. The first argument is the
        # model, read literally; nothing but the fixed refusal is printed.
        for bad in OPTION_SHAPED:
            with self.subTest(bad=bad):
                proc = self.run_script(bad)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(proc.stderr, FIXED_REFUSAL + "\n")

    def test_a_wrong_argument_count_or_option_is_refused_with_fixed_text(self):
        arm = arm_ids()[0]
        for argv in ((), (arm, arm), (arm, "--roster"), (arm, "--help"),
                     (arm, "-h"), ("--roster", str(ROSTER), arm),
                     (arm, "--rost", str(ROSTER)), (arm, "--roster", str(ROSTER), "x")):
            with self.subTest(argv=argv):
                proc = self.run_script(*argv)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(proc.stderr, FIXED_REFUSAL + "\n")

    def test_an_unreadable_or_wrong_shape_roster_refuses_every_model(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shapes = {
            "empty": "",
            "list": "- a\n- b\n",
            "arms_are_strings": "arms:\n  - claude-opus-5-5\n",
            "no_arms": "schema: 1\n",
            "truncated": "arms:\n  - id: [\n",
        }
        for label, text in shapes.items():
            with self.subTest(shape=label):
                path = tmp / f"{label}.yml"
                path.write_text(text, encoding="utf-8")
                proc = self.run_script("claude-opus-5-5", roster=path)
                self.assertEqual(proc.returncode, 1)
        proc = self.run_script("claude-opus-5-5", roster=tmp / "absent.yml")
        self.assertEqual(proc.returncode, 1)

    def test_resolve_is_the_fixture_pin_else_the_roster_first_arm(self):
        # #70, rounds 7 and 8: the model the weekly caller passes as the
        # fire's required `model`, and plan_scheduled_evals.py revalidates.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        roster = tmp / "roster.yml"
        roster.write_text('arms:\n  - id: "claude-first"\n  - id: "claude-second"\n',
                          encoding="utf-8")
        fixture_dir = REPO_ROOT / base.FIXTURE
        pin = yaml.safe_load((fixture_dir / "fixture.yaml").read_text(encoding="utf-8"))
        pin = pin.get("model") if isinstance(pin, dict) else None
        proc = self.run_script("--resolve", base.FIXTURE, roster=roster)
        self.assertEqual((proc.returncode, proc.stdout), (0, f"{pin or 'claude-first'}\n"))
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import roster_arm
        (tmp / "evals" / "pinned").mkdir(parents=True)
        (tmp / "evals" / "pinned" / "fixture.yaml").write_text(
            "skill: s\nprompt: p\nmodel: claude-pinned\n", encoding="utf-8")
        (tmp / "evals" / "plain").mkdir(parents=True)
        (tmp / "evals" / "plain" / "fixture.yaml").write_text(
            "skill: s\nprompt: p\n", encoding="utf-8")
        self.assertEqual(roster_arm.resolve("evals/pinned", roster, tmp), "claude-pinned")
        self.assertEqual(roster_arm.resolve("evals/plain", roster, tmp), "claude-first")
        empty = tmp / "empty.yml"
        empty.write_text("schema: 1\n", encoding="utf-8")
        self.assertIsNone(roster_arm.resolve("evals/plain", empty, tmp))
        proc = self.run_script("--resolve", base.FIXTURE, roster=tmp / "absent.yml")
        if not pin:
            self.assertEqual((proc.returncode, proc.stdout), (1, ""))
            self.assertEqual(proc.stderr, roster_arm.NO_MODEL + "\n")
        # `--resolve` takes exactly a fixture and an optional --roster.
        for argv in (("--resolve",), ("--resolve", base.FIXTURE, "x"),
                     ("--resolve", base.FIXTURE, "--rost", str(roster))):
            with self.subTest(argv=argv):
                proc = self.run_script(*argv)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(proc.stdout, "")

    def test_a_substring_or_a_comment_in_the_roster_is_not_an_arm(self):
        # The roster text mentions ids in comments and `reason:` prose; only
        # a parsed `arms[].id` counts.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        path = tmp / "roster.yml"
        path.write_text(
            "# - id: \"claude-in-a-comment\"\n"
            "arms:\n"
            "  - id: \"claude-real\"\n"
            "    reason: >-\n"
            "      id: \"claude-in-prose\"\n"
            "judge:\n  id: \"claude-the-judge\"\n", encoding="utf-8")
        self.assertEqual(self.run_script("claude-real", roster=path).returncode, 0)
        for bad in ("claude-in-a-comment", "claude-in-prose", "claude-the-judge",
                    "claude-rea"):
            with self.subTest(bad=bad):
                self.assertEqual(self.run_script(bad, roster=path).returncode, 1)


@unittest.skipUnless(shutil.which("jq") and shutil.which("git"),
                     "needs jq and git on PATH")
class ValidateStepModelTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.script = base.step_script("Validate the dispatch inputs")
        self.arm = arm_ids()[0]

    def run_step(self, inputs):
        event = self.tmp / "event.json"
        event.write_text(json.dumps({"inputs": inputs}), encoding="utf-8")
        output = self.tmp / "output"
        output.write_text("", encoding="utf-8")
        env = {"PATH": os.environ["PATH"], "HOME": str(self.tmp),
               "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
               "GITHUB_EVENT_PATH": str(event), "GITHUB_OUTPUT": str(output)}
        proc = subprocess.run(["bash", "-c", self.script], cwd=REPO_ROOT, env=env,
                              capture_output=True, text=True, timeout=60)
        values = dict(line.split("=", 1) for line in
                      output.read_text(encoding="utf-8").splitlines())
        return proc, values

    def eval_inputs(self, **extra):
        return {"mode": "eval", "fixture": base.FIXTURE, "arms": "both",
                "trials": "1", **extra}

    def test_a_roster_arm_passes_and_is_an_output(self):
        for arm in arm_ids():
            with self.subTest(arm=arm):
                proc, values = self.run_step(self.eval_inputs(model=arm))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(values["model"], arm)

    def test_an_empty_or_absent_model_is_refused_in_eval_mode(self):
        # #70, round 8 (R8-3): `run-name` is rendered from the inputs, so an
        # eval fire with no `model` input has a title naming no cell. It is
        # refused, never resolved behind its title's back.
        for extra in ({}, {"model": ""}):
            with self.subTest(extra=extra):
                proc, values = self.run_step(self.eval_inputs(**extra))
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(values, {})
                self.assertIn("::error::input 'model' is required in eval mode",
                              proc.stdout + proc.stderr)
                self.assertNotIn("::notice::", proc.stdout + proc.stderr)

    def test_an_unknown_model_fails_with_the_fixed_message_and_no_echo(self):
        for bad in ("claude-nonexistent-9", "claude-fable-5-1", self.arm + "x",
                    "$(id)", 'x", "evil": "1'):
            with self.subTest(bad=bad):
                proc, values = self.run_step(self.eval_inputs(model=bad))
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(FIXED_REFUSAL, proc.stdout + proc.stderr)
                self.assertNotIn(bad, proc.stdout + proc.stderr)
                self.assertNotIn("run_id", values)

    def test_an_option_shaped_model_fails_with_the_fixed_message_only(self):
        # Review round 1, B1: `-h` passed the step and was fired.
        for bad in OPTION_SHAPED:
            with self.subTest(bad=bad):
                proc, values = self.run_step(self.eval_inputs(model=bad))
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout.strip(), "::error::" + FIXED_REFUSAL)
                self.assertNotIn("usage", (proc.stdout + proc.stderr).lower())
                self.assertEqual(values, {})

    def test_the_step_refuses_an_option_shape_before_the_script_runs(self):
        # The step's own shape check, isolated from the script: a stand-in
        # `python3` that calls every model an arm, and fails the test if an
        # option-shaped one reaches its command line.
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        reached = self.tmp / "reached"
        stand_in = bin_dir / "python3"
        stand_in.write_text(
            f"#!{sys.executable}\nimport os, sys\n"
            "if sys.argv[1:2] == ['scripts/roster_arm.py']:\n"
            f"    open({str(reached)!r}, 'a').write('x')\n"
            "    sys.exit(0)\n"
            "os.execv(sys.executable, [sys.executable, *sys.argv[1:]])\n",
            encoding="utf-8")
        stand_in.chmod(0o755)
        path = f"{bin_dir}:{os.environ['PATH']}"
        with mock.patch.dict(os.environ, {"PATH": path}):
            proc, values = self.run_step(self.eval_inputs(model=self.arm))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(reached.exists(), "the stand-in was not used")
            reached.unlink()
            for bad in (*OPTION_SHAPED, ".hidden", "_x", "a" * 129, "a b", "a/b"):
                with self.subTest(bad=bad):
                    proc, values = self.run_step(self.eval_inputs(model=bad))
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertEqual(proc.stdout.strip(), "::error::" + FIXED_REFUSAL)
                    self.assertEqual(values, {})
                    self.assertFalse(reached.exists())

    def test_every_roster_arm_id_has_the_shape_the_step_admits(self):
        for arm in arm_ids():
            with self.subTest(arm=arm):
                self.assertRegex(arm, r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

    def test_a_model_of_the_wrong_type_is_refused_by_the_type_check(self):
        # Review round 1, N1: pins `model` in the type and NUL check, which
        # the control-character check would otherwise mask with a jq error.
        for label, bad in (("number", 5), ("list", [self.arm]), ("bool", True),
                           ("object", {"id": self.arm}), ("nul", self.arm + "\u0000")):
            with self.subTest(case=label):
                proc, values = self.run_step(self.eval_inputs(model=bad))
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("is missing, not a string, or contains a NUL byte",
                              proc.stdout)
                self.assertEqual(values, {})

    def test_a_malformed_model_value_is_refused(self):
        for label, bad in (("nul", self.arm + "\u0000"), ("newline", self.arm + "\n"),
                           ("number", 5), ("list", [self.arm])):
            with self.subTest(case=label):
                proc, values = self.run_step(self.eval_inputs(model=bad))
                self.assertNotEqual(proc.returncode, 0)
                self.assertNotIn("run_id", values)

    def test_a_model_is_refused_outside_eval_mode(self):
        modes = {
            "scaffold": {"mode": "scaffold", "candidate": base.CANDIDATE,
                         "arms": "both", "trials": "1"},
            "improve": {"mode": "improve", "skill": base.SKILL,
                        "holdout": base.HOLDOUT, "arms": "both", "trials": "1"},
        }
        for mode, inputs in modes.items():
            for model in (self.arm, "claude-nonexistent-9"):
                with self.subTest(mode=mode, model=model):
                    proc, values = self.run_step({**inputs, "model": model})
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn("'model' must be empty unless the mode is eval",
                                  proc.stdout + proc.stderr)
                    self.assertNotIn(model, proc.stdout + proc.stderr)
                    self.assertNotIn("run_id", values)
            with self.subTest(mode=mode, model="empty"):
                proc, values = self.run_step({**inputs, "model": ""})
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(values["model"], "")


# What the eval payload was before the `model` input existed, for the
# environment FireStepTests uses: a regression pin, not derived from the
# workflow under test.
LEGACY_DATA_BINARY = json.dumps({"text": json.dumps({
    "mode": "eval", "run_id": "20261006T120000Z-a1b2c3",
    "fixture": base.FIXTURE, "arms": "both", "trials": 2},
    separators=(",", ":"))}, separators=(",", ":"))


@unittest.skipUnless(shutil.which("jq"), "needs jq on PATH")
class FireStepModelTests(unittest.TestCase):
    SESSION = "session_01TestOnlyAbc"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        curl = bin_dir / "curl"
        curl.write_text(base.FAKE_CURL, encoding="utf-8")
        curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
        self.bin = bin_dir
        self.log = self.tmp / "log"
        self.log.mkdir()
        self.summary = self.tmp / "summary.md"
        self.snapshot = self.tmp / "issue-snapshot.json"
        self.snapshot.write_text("null\n", encoding="utf-8")
        self.script = base.step_script("Fire the eval routine")
        steps = base.load(base.WORKFLOW)["jobs"]["fire"]["steps"]
        self.url = next(s for s in steps
                        if s.get("name") == "Fire the eval routine")["env"]["FIRE_URL"]

    def fire(self, unset=(), **overrides):
        self.summary.write_text("", encoding="utf-8")
        (self.log / "argv.json").unlink(missing_ok=True)
        (self.log / "body").unlink(missing_ok=True)
        env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp), "FIRE_URL": self.url,
            "EVAL_ROUTINE_FIRE_BEARER": "sk-ant-oat01-FAKE-BEARER-FOR-TESTS",
            "RUN_ID": "20261006T120000Z-a1b2c3", "FIXTURE": base.FIXTURE,
            "ARMS": "both", "TRIALS": "2", "MODE": "eval", "CANDIDATE": "",
            "SKILL": "", "HOLDOUT": "", "MODEL": "", "VOUCH_KEY": "",
            "ISSUE_SNAPSHOT_FILE": str(self.snapshot),
            "GITHUB_STEP_SUMMARY": str(self.summary),
            "FAKE_CURL_LOG": str(self.log), "FAKE_CURL_STATUS": "200",
            "FAKE_CURL_BODY": json.dumps({
                "type": "routine_fire", "claude_code_session_id": self.SESSION,
                "claude_code_session_url": f"https://claude.ai/code/{self.SESSION}"}),
            **overrides,
        }
        for name in unset:
            env.pop(name)
        proc = subprocess.run(["bash", "-c", self.script], cwd=self.tmp, env=env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        # curl reads the body from `--data-binary @<file>` (#70, round 5).
        return (self.log / "body").read_text()

    @staticmethod
    def without_vouch(sent: str) -> str:
        """The data binary with #70's trailing `vouch_nonce` key removed,
        re-encoded as jq -c encodes it."""
        text = json.loads(json.loads(sent)["text"])
        assert list(text)[-1] == "vouch_nonce", list(text)
        text.pop("vouch_nonce")
        return json.dumps({"text": json.dumps(text, separators=(",", ":"))},
                          separators=(",", ":"))

    def test_an_empty_model_leaves_the_eval_payload_as_it_was(self):
        # Without VOUCH_KEY the payload is byte for byte the legacy one;
        # with it, the one difference is the trailing `vouch_nonce`.
        self.assertEqual(self.fire(MODEL=""), LEGACY_DATA_BINARY)
        self.assertEqual(self.without_vouch(self.fire(MODEL="", VOUCH_KEY=base.VOUCH_KEY)),
                         LEGACY_DATA_BINARY)

    def test_an_unset_model_variable_leaves_it_as_it_was_too(self):
        # A caller that predates the input never sets MODEL at all.
        self.assertEqual(self.fire(unset=("MODEL",)), LEGACY_DATA_BINARY)
        self.assertEqual(self.without_vouch(self.fire(unset=("MODEL",),
                                                      VOUCH_KEY=base.VOUCH_KEY)),
                         LEGACY_DATA_BINARY)

    def test_a_set_model_is_carried_as_the_last_key(self):
        arm = arm_ids()[1]
        text = json.loads(json.loads(self.fire(MODEL=arm))["text"])
        self.assertEqual(list(text), ["mode", "run_id", "fixture", "arms",
                                      "trials", "model"])
        self.assertEqual(text["model"], arm)
        # The vouch nonce, when there is one, follows it.
        text = json.loads(json.loads(self.fire(MODEL=arm, VOUCH_KEY=base.VOUCH_KEY))["text"])
        self.assertEqual(list(text), ["mode", "run_id", "fixture", "arms",
                                      "trials", "model", "vouch_nonce"])

    def test_the_model_is_json_encoded_by_jq(self):
        tricky = 'x", "evil": "1'
        text = json.loads(json.loads(self.fire(MODEL=tricky))["text"])
        self.assertEqual(text["model"], tricky)
        self.assertNotIn("evil", text)

    def test_scaffold_and_improve_payloads_never_carry_a_model(self):
        arm = arm_ids()[0]
        cases = {"scaffold": {"CANDIDATE": base.CANDIDATE},
                 "improve": {"SKILL": base.SKILL, "HOLDOUT": base.HOLDOUT}}
        for mode, extra in cases.items():
            with self.subTest(mode=mode):
                text = json.loads(json.loads(
                    self.fire(MODE=mode, MODEL=arm, **extra))["text"])
                self.assertNotIn("model", text)

    def test_the_summary_names_the_model_only_when_set(self):
        self.fire(MODEL="")
        self.assertNotIn("Model", self.summary.read_text())
        arm = arm_ids()[-1]
        self.fire(MODEL=arm)
        self.assertIn(f"- Model: `{arm}`", self.summary.read_text())


class DocsTests(unittest.TestCase):

    def test_the_workflow_header_names_the_input_and_the_roster(self):
        text = base.WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?s)`model`.*evals/roster\.yml")


if __name__ == "__main__":
    unittest.main()
