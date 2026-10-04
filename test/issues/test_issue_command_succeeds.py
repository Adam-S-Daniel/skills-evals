"""Offline command-check regressions; subprocess timeouts are mocked."""

from __future__ import annotations

import json
import io
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "harness"))
sys.path.insert(0, str(REPO / "scripts"))
from scorers import commands, objective
import local_eval


class CommandSucceedsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="command-check-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ws = self.root / "final"
        self.ws.mkdir()
        self.network = mock.patch.object(commands, "_network_prefix", return_value=[])
        self.probe = self.network.start()
        self.addCleanup(self.network.stop)

    def check(self, argv=None, **kwargs):
        return commands.command_succeeds(str(self.ws), [], argv=argv, **kwargs)

    def python(self, code, *args, **kwargs):
        return self.check(["python3", "-c", code, *args], **kwargs)

    def test_exit_zero_passes(self):
        passed, detail = self.python("raise SystemExit(0)")
        self.assertTrue(passed)
        self.assertIn("command_success exit=0", detail)

    def test_nonzero_fails(self):
        passed, detail = self.python("raise SystemExit(7)")
        self.assertFalse(passed)
        self.assertIn("command_nonzero exit=7", detail)

    def test_pass_text_does_not_pass(self):
        passed, detail = self.python("print('PASS'); raise SystemExit(1)")
        self.assertFalse(passed)
        self.assertIn("command_nonzero exit=1", detail)
        self.assertNotIn("PASS", detail)

    def test_spawn_failure_is_named_and_sanitized(self):
        with mock.patch.object(commands.subprocess, "Popen",
                               side_effect=OSError("/home/private/credential-value")):
            passed, detail = self.python("pass")
        self.assertFalse(passed)
        self.assertIn("command_spawn_failed", detail)
        self.assertNotIn("private", detail)
        passed, detail = self.check(["./missing-program"])
        self.assertFalse(passed)
        self.assertIn("command_spawn_failed", detail)

    def test_timeout_is_named_and_terminates_own_group(self):
        proc = mock.Mock(pid=123456)
        proc.wait.side_effect = [subprocess.TimeoutExpired("private", 3), -9]
        with mock.patch.object(commands.subprocess, "Popen", return_value=proc), \
                mock.patch.object(commands.os, "killpg") as kill:
            passed, detail = self.python("pass", timeout_s=3)
        self.assertFalse(passed)
        self.assertIn("command_timeout", detail)
        self.assertNotIn("private", detail)
        kill.assert_called_once_with(proc.pid, commands.signal.SIGKILL)
        self.assertEqual(proc.wait.call_args_list,
                         [mock.call(timeout=3), mock.call(timeout=commands.CLEANUP_TIMEOUT_S)])

    def test_cleanup_wait_is_bounded(self):
        proc = mock.Mock(pid=123456)
        proc.wait.side_effect = [0, subprocess.TimeoutExpired("private", 2)]
        with mock.patch.object(commands.subprocess, "Popen", return_value=proc), \
                mock.patch.object(commands.os, "killpg"):
            passed, detail = self.python("pass")
        self.assertFalse(passed)
        self.assertIn("command_timeout", detail)
        self.assertEqual(proc.wait.call_args.kwargs,
                         {"timeout": commands.CLEANUP_TIMEOUT_S})

    def test_argv_validation(self):
        for argv in (None, [], "python3", ("python3",), [1], [" "],
                     ["python3", None], ["python3", "\x00"]):
            with self.subTest(argv=argv), mock.patch.object(commands, "_run_command") as run:
                self.assertEqual(self.check(argv), (False, "command_invalid_argv"))
                run.assert_not_called()

    def test_timeout_validation(self):
        for timeout in (None, True, False, "1", 0, -1, 60.01,
                        float("nan"), float("inf"), -float("inf"), 10**1000):
            with self.subTest(timeout=timeout), mock.patch.object(commands, "_run_command") as run:
                self.assertEqual(self.python("pass", timeout_s=timeout),
                                 (False, "command_invalid_timeout"))
                run.assert_not_called()
        for timeout in (0.5, 60):
            with mock.patch.object(commands, "_run_command", return_value=0) as run:
                self.assertTrue(self.python("pass", timeout_s=timeout)[0])
                self.assertEqual(run.call_args.args[-1], timeout)

    def test_final_workspace_literal_args_and_closed_stdin(self):
        (self.ws / "state.txt").write_text("final", encoding="utf-8")
        code = ("import pathlib,sys; assert pathlib.Path('state.txt').read_text() == 'final'; "
                "assert sys.argv[1:] == ['$HOME', '$(exit 1)', '; exit 1']; "
                "assert sys.stdin.read() == ''")
        self.assertTrue(self.python(code, "$HOME", "$(exit 1)", "; exit 1")[0])
        proc = mock.Mock(pid=123456)
        proc.wait.return_value = 0
        with mock.patch.object(commands.subprocess, "Popen", return_value=proc) as spawn, \
                mock.patch.object(commands.os, "killpg"):
            self.assertTrue(self.python("pass", "$HOME", "$(exit 1)")[0])
        self.assertEqual(spawn.call_args.args[0][1:], ["-c", "pass", "$HOME", "$(exit 1)"])
        self.assertEqual(spawn.call_args.kwargs["cwd"], self.ws.resolve())
        self.assertIs(spawn.call_args.kwargs["shell"], False)
        self.assertEqual(spawn.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(spawn.call_args.kwargs["start_new_session"], os.name == "posix")

    def test_workspace_executable_runs_without_path_lookup(self):
        program = self.ws / "run-check"
        program.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        program.chmod(0o700)
        self.assertTrue(self.check(["./run-check"])[0])
        self.assertEqual(self.check(["git", "--version"])[0], False)
        self.assertEqual(self.check(["/usr/bin/true"]), (False, "command_invalid_executable"))

    def test_fixed_interpreter_beats_agent_planted_name(self):
        planted = self.ws / "python3"
        planted.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
        planted.chmod(0o700)
        with mock.patch.dict(os.environ, {"PATH": str(self.ws)}):
            self.assertTrue(self.python("pass")[0])
        self.assertIn(commands._executable(self.ws, "python3"), commands.INTERPRETERS["python3"])

    def test_symlink_escape_and_cli_alias_rejected(self):
        (self.ws / "escape").symlink_to("/usr/bin/true")
        (self.ws / "claude").write_text("NEVER EXECUTE", encoding="utf-8")
        (self.ws / "alias").symlink_to("claude")
        for name in ("./escape", "claude", "claude.exe", "./claude", "./alias"):
            with self.subTest(name=name), mock.patch.object(commands, "_run_command") as run:
                self.assertEqual(self.check([name]), (False, "command_invalid_executable"))
                run.assert_not_called()

    def test_child_environment_has_no_credentials_or_parent_config(self):
        hostile = {"ANTHROPIC_API_KEY": "fixture-value", "GH_TOKEN": "fixture-value",
                   "GITHUB_TOKEN": "fixture-value", "AWS_ACCESS_KEY_ID": "fixture-value",
                   "CLAUDE_BIN": "fixture-value", "PYTHONPATH": "fixture-value",
                   "BASH_ENV": "fixture-value"}
        code = "import os; assert not set(" + repr(list(hostile)) + ").intersection(os.environ)"
        with mock.patch.dict(os.environ, hostile):
            self.assertTrue(self.python(code)[0])
        with mock.patch.object(commands, "_run_command", return_value=0) as run:
            self.assertTrue(self.python("pass")[0])
            env = run.call_args.args[2]
            self.assertEqual(set(env), {"HOME", "PATH", "LANG", "LC_ALL",
                "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
                "XDG_RUNTIME_DIR", "GH_CONFIG_DIR", "TMPDIR", "TMP", "TEMP"})

    def test_home_config_isolated_and_removed(self):
        parent_home = self.root / "parent-home"
        parent_home.mkdir()
        (parent_home / ".claude.json").write_text("fixture-value", encoding="utf-8")
        code = ("import os,pathlib,json; home=pathlib.Path.home(); "
                "assert not (home / '.claude.json').exists(); "
                "assert home != pathlib.Path(" + repr(str(parent_home)) + "); "
                "paths={k:v for k,v in os.environ.items() if k.endswith('_HOME') "
                "or k in ('HOME','GH_CONFIG_DIR','TMPDIR')}; "
                "assert all(pathlib.Path(v).is_dir() for v in paths.values()); "
                "pathlib.Path('isolation.json').write_text(json.dumps(paths))")
        with mock.patch.dict(os.environ, {"HOME": str(parent_home), "GH_CONFIG_DIR": str(parent_home)}):
            self.assertTrue(self.python(code)[0])
        paths = json.loads((self.ws / "isolation.json").read_text())
        self.assertTrue(paths)
        self.assertTrue(all(not Path(path).exists() for path in paths.values()))
        self.assertTrue((parent_home / ".claude.json").exists())

    def test_output_is_suppressed_sanitized_and_truncated(self):
        passed, detail = self.python("import os,sys; print(os.environ['HOME']); "
                                    "print('fixture-env-value'); print('x'*5000); "
                                    "sys.stderr.write('/home/runner/private')")
        self.assertTrue(passed)
        self.assertNotIn("/home/", detail)
        self.assertNotIn("objective-command-", detail)
        self.assertNotIn("fixture-env-value", detail)
        self.assertIn("stdout_bytes=4096", detail)
        self.assertIn("output=truncated", detail)
        self.assertLess(len(detail), 200)

    def test_registry_constraint_routing(self):
        fixture = {"objective_checks": [{"id": "command", "type": "command_succeeds",
                                        "argv": ["python3", "-c", "pass"], "timeout_s": 5}]}
        self.assertIs(objective.CHECKS["command_succeeds"], commands.command_succeeds)
        result = objective.run_checks(fixture, str(self.ws), str(self.root))[0]
        self.assertTrue(result["passed"])
        fixture["objective_checks"][0]["environment"] = {}
        with self.assertRaises(ValueError):
            objective.run_checks(fixture, str(self.ws), str(self.root))

    def test_network_probe_supported_and_unavailable(self):
        self.network.stop()
        with mock.patch.object(commands.sys, "platform", "linux"), \
                mock.patch.object(commands.Path, "is_file", return_value=True), \
                mock.patch.object(commands.subprocess, "run") as run:
            run.return_value.returncode = 0
            prefix = commands._network_prefix({"HOME": "isolated"})
            self.assertEqual(prefix, ["/usr/bin/unshare", "--net", "--"])
            self.assertEqual(run.call_args.args[0], prefix + ["/usr/bin/true"])
            self.assertEqual(run.call_args.kwargs["timeout"], commands.PROBE_TIMEOUT_S)
            self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
            run.return_value.returncode = 1
            self.assertEqual(commands._network_prefix({}), [])
            run.side_effect = subprocess.TimeoutExpired("private", 2)
            self.assertEqual(commands._network_prefix({}), [])
        with mock.patch.object(commands.sys, "platform", "other"):
            self.assertEqual(commands._network_prefix({}), [])
        self.probe = self.network.start()
        self.probe.return_value = ["/usr/bin/unshare", "--net", "--"]
        with mock.patch.object(commands, "_run_command", return_value=0) as run:
            self.assertIn("network=isolated", self.python("pass")[1])
            self.assertEqual(run.call_args.args[0][:3], self.probe.return_value)

    def test_local_guard_environment_is_not_a_cli_launch_path(self):
        # A mock guard names a program that must never run. The command child
        # receives neither that launcher nor any inherited CLI configuration.
        env = local_eval.child_environment({"CLAUDE_BIN": "must-not-run",
                                           "PATH": os.environ["PATH"],
                                           "HOME": os.environ["HOME"]})
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(commands, "_run_command", return_value=0) as run:
            self.assertTrue(self.python("pass")[0])
            child = run.call_args.args[2]
            self.assertNotIn("CLAUDE_BIN", child)
            stub = Path(child["PATH"].split(":")[0]) / "claude"
            # Temporary paths are removed by this point; inspect the stub
            # while the process sink is called in a separate invocation.
        def inspect(argv, workspace, child, stdout, stderr, timeout):
            refusal = Path(child["PATH"].split(":")[0]) / "claude"
            self.assertEqual(refusal.read_text(), "#!/bin/sh\nexit 97\n")
            self.assertEqual(refusal.stat().st_mode & 0o777, 0o700)
            self.assertNotIn("must-not-run", child.values())
            return 0
        with mock.patch.object(commands, "_run_command", side_effect=inspect):
            self.assertTrue(self.python("pass")[0])
        self.assertFalse(stub.exists())
        guard = self.ws / "claude"
        guard.write_text("NEVER EXECUTE", encoding="utf-8")
        with mock.patch.object(commands.subprocess, "Popen") as spawn:
            self.assertEqual(self.check([str(guard)]), (False, "command_invalid_executable"))
            spawn.assert_not_called()
        # Exercise the launch-time guard itself without executing any CLI.
        import local_eval_guard
        settings = self.ws / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text('{"apiKeyHelper": "fixture-value"}', encoding="utf-8")
        source = local_eval_guard.launcher_source(sys.executable, str(REPO / "scripts"),
            str(self.root / "never-cli"), str(self.root / "empty-checkout"),
            str(self.root / "guard-refusals"))
        with mock.patch.object(sys, "argv", ["guard", "-p", "never"]), \
                mock.patch.object(sys, "path", list(sys.path)), \
                mock.patch.object(sys, "dont_write_bytecode", sys.dont_write_bytecode), \
                mock.patch.object(os, "getcwd", return_value=str(self.ws)), \
                mock.patch.object(os, "execv") as execute, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as refusal:
                exec(compile(source, "offline-guard", "exec"), {})
            self.assertEqual(refusal.exception.code, local_eval_guard.GUARD_EXIT)
            execute.assert_not_called()

    def test_ci_objective_only_entrypoint_uses_final_workspace(self):
        eval_dir = self.root / "fixture"
        eval_dir.mkdir()
        (eval_dir / "seed").mkdir()
        (self.ws / "final-marker").write_text("final", encoding="utf-8")
        fixture = {"name": "offline-command", "skill": "writing-adrs", "objective_checks": [{"id": "command",
            "type": "command_succeeds", "argv": ["python3", "-c",
                "from pathlib import Path; assert Path('final-marker').read_text() == 'final'"]}]}
        import yaml
        (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")
        import run_eval
        output = io.StringIO()
        with mock.patch.object(sys, "argv", [str(REPO / "harness/run_eval.py"),
            str(eval_dir), "--arm", "objective-only", "--workspace", str(self.ws),
            "--results-dir", str(self.root / "results")]), contextlib.redirect_stdout(output):
            exit_code = run_eval.main()
        self.assertEqual(exit_code, 0, output.getvalue())
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["checks"][0]["passed"])
        self.assertIn("command_success", payload["checks"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
