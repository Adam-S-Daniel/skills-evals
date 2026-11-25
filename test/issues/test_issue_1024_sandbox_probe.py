"""A hosted session starts with no command sandbox and says nothing (#1024).

Claude Code 2.1.325 starts Claude Code on the web, cloud scheduled tasks and
Cowork cloud sessions despite `sandbox.failIfUnavailable`, so a routine's arm
no longer fails on the CLI's stderr lines. The harness proves the read fence
instead: before the first agent arm it has the CLI `cat` a sentinel under a
`denyRead` path. These tests drive that canary with `test/fake-claude`'s
probe answers (no network, no model, no clock).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

sys.path.insert(0, str(ROOT / "scripts"))
import ingest_routine_results  # noqa: E402
import local_eval_guard  # noqa: E402
import routine_eval  # noqa: E402
import run_eval  # noqa: E402
from arm_test_env import install_arm_test_environment  # noqa: E402

FAKE_CLAUDE = ROOT / "test" / "fake-claude"

# The fake CLI reads its mode from its own environment, which the harness's
# allowlist does not forward, so a wrapper sets it and hands over.
WRAPPER = f"""#!{sys.executable}
import os, sys
os.environ["FAKE_CLAUDE_PROBE"] = {{how!r}}
os.environ["FAKE_CLAUDE_PROBE_STATE"] = {{state!r}}
os.environ["FAKE_CLAUDE_ARGV_LOG"] = {{log!r}}
os.execv({sys.executable!r}, [{sys.executable!r}, {str(FAKE_CLAUDE)!r}, *sys.argv[1:]])
"""


@install_arm_test_environment
def setUpModule() -> None:
    pass


def tearDownModule() -> None:
    unittest.doModuleCleanups()


class SandboxProbeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="sandbox-probe-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.log = self.root / "argv.jsonl"
        seed = self.root / "seed"
        seed.mkdir()
        (seed / "calc.py").write_text("x = 1\n", encoding="utf-8")
        self.ws = run_eval.materialize_workspace(seed, {})
        self.addCleanup(shutil.rmtree, self.ws, ignore_errors=True)
        for patch in (
                mock.patch.object(run_eval, "_SANDBOX_PROBE_REQUIRED", True),
                mock.patch.object(run_eval, "_SANDBOX_PROBE_VERDICT", None)):
            patch.start()
            self.addCleanup(patch.stop)

    def use_cli(self, how: str) -> None:
        stand_in = self.root / "claude"
        stand_in.write_text(WRAPPER.format(how=how, log=str(self.log),
                                       state=str(self.root / "probe-state")),
                            encoding="utf-8")
        stand_in.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_STATE_HOME": str(self.root / "state"),
            "CLAUDE_BIN": str(stand_in)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def arm(self) -> dict:
        return {"name": "without_skill", "timeout": 60}

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line)["argv"] for line in self.log.read_text().splitlines()]

    def probes(self) -> list[list[str]]:
        return [argv for argv in self.calls() if "--max-turns" in argv]

    def test_a_leaked_sentinel_fails_every_arm_sandbox_unavailable(self):
        self.use_cli("leak")
        for _ in range(2):
            out = run_eval.run_agent(self.ws, "do it", self.arm())
            self.assertEqual(out["error"], "sandbox_unavailable", out)
            self.assertIn("sandbox not enforcing", out["detail"])
        # Once per run and never retried: the second arm reuses the verdict,
        # and no arm started.
        self.assertEqual(len(self.calls()), 1)

    def test_a_denied_sentinel_lets_the_arms_proceed(self):
        self.use_cli("deny")
        for _ in range(2):
            out = run_eval.run_agent(self.ws, "do it", self.arm())
            self.assertNotIn("error", out, out)
        calls = self.calls()
        self.assertEqual(len(calls), 3)  # one probe, two arms
        self.assertEqual(len(self.probes()), 1)

    def test_the_probe_runs_under_the_arms_own_settings_with_a_cheap_model(self):
        self.use_cli("deny")
        run_eval.run_agent(self.ws, "do it", self.arm())
        (argv,) = self.probes()
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertIs(settings["sandbox"]["failIfUnavailable"], True)
        self.assertIn(str(self.home.resolve()),
                      settings["sandbox"]["filesystem"]["denyRead"])
        self.assertEqual(argv[argv.index("--model") + 1], "haiku")
        # The sentinel lived under the denied HOME and is gone again.
        self.assertEqual(list(self.home.iterdir()), [])

    def test_a_probe_that_errors_fails_closed(self):
        self.use_cli("error")
        out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertEqual(out["error"], "sandbox_unavailable", out)
        self.assertIn("inconclusive", out["detail"])
        self.assertNotIn("not enforcing", out["detail"])
        # Tried, retried twice, no arm; the detail says how often.
        self.assertEqual(len(self.calls()), run_eval._SANDBOX_PROBE_ATTEMPTS)
        self.assertEqual(run_eval._SANDBOX_PROBE_ATTEMPTS, 3)
        self.assertIn("(all 3 tries)", out["detail"])

    def test_a_probe_whose_command_never_ran_fails_closed(self):
        self.use_cli("skip")
        out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertEqual(out["error"], "sandbox_unavailable", out)
        self.assertIn("inconclusive", out["detail"])
        self.assertIn("the model made no Bash call", out["detail"])

    def test_an_inconclusive_probe_says_why_in_the_clis_terms(self):
        # A routine run lost a model's arms to two inconclusive probes with no
        # word on why (skills-evals routine run 20261125T020222Z-59af29).
        cmd = "cat /x 2>&1; echo probe-ran-3"
        def run(*events, result=None):
            tail = [result or {"type": "result", "is_error": False,
                               "subtype": "success"}]
            return run_eval._probe_unproven_reason(
                [*events, *tail], cmd, *run_eval._probe_outcomes([*events, *tail], cmd))
        def bash(command, id_="t1"):
            return {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": id_, "name": "Bash",
                 "input": {"command": command}}]}}
        self.assertIn("not a JSON event list",
                      run_eval._probe_unproven_reason(None, cmd, [], []))
        self.assertIn("no result event",
                      run_eval._probe_unproven_reason([], cmd, [], []))
        self.assertIn("error (subtype error_max_turns)", run(result={
            "type": "result", "is_error": True, "subtype": "error_max_turns"}))
        self.assertIn("1 tool call(s) were denied permission", run(bash(cmd), result={
            "type": "result", "is_error": False, "subtype": "success",
            "permission_denials": [{"tool_name": "Bash"}]}))
        self.assertEqual(run(), "the model made no Bash call")
        self.assertIn("none with the exact probe command", run(bash("cat /x")))
        self.assertIn("lacked the marker", run(bash(cmd), {
            "type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "hi"}]}}))

    def test_tries_that_fail_differently_are_each_reported(self):
        answers = iter([("unproven", "a"), ("unproven", "b"), ("unproven", "b")])
        with mock.patch.object(run_eval, "_probe_once",
                               side_effect=lambda *a, **k: next(answers)):
            self.assertEqual(run_eval.probe_arm_sandbox(),
                             "try 1: a | try 2: b | try 3: b")

    def test_a_probe_timeout_fails_closed(self):
        self.use_cli("deny")
        with mock.patch.object(run_eval, "_run_in_own_session",
                               side_effect=run_eval.subprocess.TimeoutExpired("c", 1)):
            out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertEqual(out["error"], "sandbox_unavailable", out)
        self.assertIn("timed out", out["detail"])

    def test_a_direct_run_agent_call_launches_no_probe(self):
        self.use_cli("leak")
        with mock.patch.object(run_eval, "_SANDBOX_PROBE_REQUIRED", False):
            out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertNotIn("error", out, out)
        self.assertEqual(self.probes(), [])

    def test_an_echo_that_never_attempted_the_read_fails_closed(self):
        # The marker alone proves nothing: a model can echo it without cat.
        for how in ("echo", "nodenial", "typo", "forged"):
            with self.subTest(how=how):
                run_eval._SANDBOX_PROBE_VERDICT = None
                self.use_cli(how)
                out = run_eval.run_agent(self.ws, "do it", self.arm())
                self.assertEqual(out["error"], "sandbox_unavailable", out)
                self.assertIn("inconclusive", out["detail"])

    def test_an_inconclusive_probe_is_retried(self):
        self.use_cli("once_skip")
        out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertNotIn("error", out, out)
        self.assertEqual(len(self.probes()), 2)

    def test_a_leak_is_never_retried(self):
        self.use_cli("once_leak")  # a retry would be answered "deny"
        out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertEqual(out["error"], "sandbox_unavailable", out)
        self.assertTrue(out["detail"].startswith("sandbox not enforcing"))
        self.assertEqual(len(self.probes()), 1)

    def test_a_guidance_arm_goes_through_the_probe(self):
        self.use_cli("leak")
        env = {"PATH": os.environ["PATH"], "HOME": str(self.home)}
        out = run_eval.run_agent(self.ws, "do it", {
            "name": "with_guidance", "timeout": 60,
            "setting_sources": "user,project", "env_override": env})
        self.assertEqual(out["error"], "sandbox_unavailable", out)
        self.assertEqual(len(self.probes()), 1)

    def test_main_requires_the_probe_with_no_hosted_variable(self):
        import argparse
        for skip, expected in ((None, True), ("1", False)):
            env = {k: v for k, v in os.environ.items()
                   if k not in ("CLAUDE_CODE_REMOTE", run_eval.SANDBOX_PROBE_SKIP_ENV)}
            if skip:
                env[run_eval.SANDBOX_PROBE_SKIP_ENV] = skip
            with mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch.object(sys, "argv", ["run_eval.py"]), \
                    mock.patch.object(argparse.ArgumentParser, "parse_args",
                                      side_effect=SystemExit(2)):
                with self.assertRaises(SystemExit):
                    run_eval.main()
                self.assertIs(run_eval._SANDBOX_PROBE_REQUIRED, expected)

    def run_main_until_parse(self, skip: str | None) -> str:
        """`main()` up to its argument parsing; what it printed to stderr."""
        import argparse
        env = {k: v for k, v in os.environ.items()
               if k != run_eval.SANDBOX_PROBE_SKIP_ENV}
        if skip:
            env[run_eval.SANDBOX_PROBE_SKIP_ENV] = skip
        err = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(sys, "argv", ["run_eval.py"]), \
                mock.patch.object(argparse.ArgumentParser, "parse_args",
                                  side_effect=SystemExit(2)), \
                contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                run_eval.main()
        return err.getvalue()

    def recorded(self) -> str:
        out = self.root / "results"
        run_eval._write_summary(out, "s", "without_skill", "t", None, None,
                                None, None, None)
        return json.loads((out / "s" / "t" / "without_skill" / "summary.json")
                          .read_text())["sandbox_probe"]

    def test_a_skipped_probe_warns_and_is_recorded(self):
        with mock.patch.object(run_eval, "_SANDBOX_PROBE_SKIPPED", False):
            warning = self.run_main_until_parse("1")
            self.assertIn("NOT proven", warning)
            self.assertIn(run_eval.SANDBOX_PROBE_SKIP_ENV, warning)
            self.assertEqual(self.recorded(), "skipped")

    def test_a_run_that_probes_does_not_warn_and_records_the_verdict(self):
        with mock.patch.object(run_eval, "_SANDBOX_PROBE_SKIPPED", False):
            self.assertEqual(self.run_main_until_parse(None), "")
            self.assertEqual(self.recorded(), "not_run")
            run_eval._SANDBOX_PROBE_VERDICT = ""
            self.assertEqual(self.recorded(), "passed")
            run_eval._SANDBOX_PROBE_VERDICT = "sandbox not enforcing: x"
            self.assertEqual(self.recorded(), "failed")

    def test_exhibit_and_improve_runs_refuse_the_skip_variable(self):
        self.assertEqual(local_eval_guard.refused_env_names(
            {run_eval.SANDBOX_PROBE_SKIP_ENV: "1", "PATH": "/usr/bin"}),
            [run_eval.SANDBOX_PROBE_SKIP_ENV])

    def test_a_routine_refuses_to_start_run_eval_with_the_skip_variable(self):
        self.assertEqual(routine_eval.SANDBOX_PROBE_SKIP_ENV,
                         run_eval.SANDBOX_PROBE_SKIP_ENV)
        log = self.root / "routine.log"
        with mock.patch.dict(os.environ, {run_eval.SANDBOX_PROBE_SKIP_ENV: "1"}), \
                mock.patch.object(routine_eval.subprocess, "Popen") as popen:
            code = routine_eval.Runner().run_eval(
                ["true"], cwd=self.root, timeout=1, log=log)
        self.assertEqual(code, 127)
        popen.assert_not_called()
        self.assertIn("refusing to run", log.read_text())

    def test_the_ingester_knows_every_status_run_eval_records(self):
        self.assertIn("sandbox_probe", ingest_routine_results.SUMMARY_ALLOWED)
        for state in ((True, None), (True, ""), (True, "x"), (False, None)):
            with mock.patch.object(run_eval, "_SANDBOX_PROBE_REQUIRED", state[0]), \
                    mock.patch.object(run_eval, "_SANDBOX_PROBE_VERDICT", state[1]), \
                    mock.patch.object(run_eval, "_SANDBOX_PROBE_SKIPPED", not state[0]):
                self.assertIn(run_eval.sandbox_probe_status(),
                              ingest_routine_results.SANDBOX_PROBE_STATUSES)

    def test_the_cli_sandbox_stderr_detection_still_applies(self):
        self.assertIsNotNone(run_eval._sandbox_unavailable_detail(
            "Error: sandbox required but unavailable: no bwrap\n"))


if __name__ == "__main__":
    unittest.main()
