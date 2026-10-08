"""Mandatory scorer filesystem boundaries, with offline unit seams and live probes."""
from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "harness"))
import run_eval
from scorers import commands, objective, repo_tests


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="scorer-sandbox-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ws = self.root / "workspace"
        self.ws.mkdir()
        self.env_root = self.root / "environment"
        self.env_root.mkdir()
        self.env = commands._environment(self.env_root, self.ws)

    def test_missing_bubblewrap_never_executes_workspace_code(self):
        with mock.patch.object(commands, "_bubblewrap", return_value=None, create=True), \
                mock.patch.object(commands, "_run_command", return_value=0) as run:
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertEqual((passed, detail), (False, "scorer_sandbox_unavailable exit=-1"))
        run.assert_not_called()

    def test_failed_probes_never_execute_workspace_code(self):
        with mock.patch.object(commands, "_bubblewrap", return_value="/usr/bin/bwrap", create=True), \
                mock.patch.object(commands.subprocess, "run", return_value=SimpleNamespace(returncode=17)), \
                mock.patch.object(commands, "_run_command", return_value=0) as run:
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertFalse(passed)
        self.assertIn("scorer_sandbox_unavailable exit=17", detail)
        run.assert_not_called()

    def test_network_fallback_preserves_every_mandatory_mount(self):
        denied = self.root / "private"
        denied.mkdir()
        with mock.patch.object(commands, "_bubblewrap", return_value="/usr/bin/bwrap"), \
                mock.patch.object(commands.subprocess, "run", side_effect=[
                    SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)]) as probe:
            prefix, network = commands._sandbox_prefix(self.ws, self.env_root, self.env, [denied])
        self.assertEqual(network, "unavailable")
        first, second = [call.args[0] for call in probe.call_args_list]
        self.assertIn("--unshare-net", first)
        self.assertNotIn("--unshare-net", second)
        first.remove("--unshare-net")
        self.assertEqual(first, second)
        self.assertEqual(second, prefix + ["/usr/bin/true"])
        for flag in ("--unshare-pid", "--die-with-parent", "--proc", "--dev", "--ro-bind", "--tmpfs"):
            self.assertIn(flag, prefix)
        self.assertEqual(probe.call_args.kwargs["timeout"], commands.PROBE_TIMEOUT_S)

    def test_ancestor_denials_collapse_before_workspace_carve_out(self):
        prefix = commands._sandbox_mounts(self.ws, self.env_root, [self.ws.parent, self.ws.parent / "private"])
        self.assertEqual(prefix.count("--tmpfs"), 1)
        hide = prefix.index("--tmpfs")
        self.assertEqual(prefix[hide + 1], str(self.root))
        self.assertLess(hide, prefix.index("--bind"))
        self.assertIn(["--bind", str(self.ws), str(self.ws)], [prefix[i:i+3] for i in range(len(prefix))])

    def test_conflicting_denials_and_broad_workspace_fail_closed(self):
        for workspace, environment, denied in (
                (self.ws, self.env_root, [self.ws]),
                (self.ws, self.env_root, [self.ws / "private"]),
                (self.ws, self.env_root, [self.env_root]),
                (self.ws, self.env_root, [self.env_root / "private"]),
                (Path("/"), self.env_root, [])):
            with self.subTest(workspace=workspace, denied=denied):
                with self.assertRaises(commands.ScorerSandboxUnavailable):
                    commands._sandbox_mounts(workspace, environment, denied)

    def test_default_denials_include_harness_and_real_home(self):
        denied = commands._read_denied(None)
        self.assertIn(REPO, denied)
        self.assertIn(Path.home().resolve(), denied)

    def test_trusted_bubblewrap_cannot_resolve_into_workspace(self):
        planted = self.ws / "bwrap"
        planted.write_text("#!/bin/sh\nexit 0\n")
        planted.chmod(0o700)
        with mock.patch.object(commands.shutil, "which", return_value=str(planted)), \
                mock.patch.object(commands, "BWRAP_PATHS", ()):
            self.assertIsNone(commands._bubblewrap(self.ws))

    def test_original_workspace_path_cannot_supply_bubblewrap(self):
        final = self.root / "original-final"
        final.mkdir()
        planted = final / "bwrap"
        planted.write_text("#!/bin/sh\nexit 0\n")
        planted.chmod(0o700)
        with mock.patch.dict(os.environ, {"PATH": str(final)}), \
                mock.patch.object(commands, "BWRAP_PATHS", ()):
            self.assertIsNone(commands._bubblewrap(self.ws, [final]))
        with mock.patch.object(commands, "BWRAP_PATHS", (str(planted),)):
            self.assertIsNone(commands._bubblewrap(self.ws, [final]))

    def test_later_sandbox_start_failure_is_named_without_output(self):
        with mock.patch.object(commands, "_sandbox_prefix", return_value=(["/usr/bin/bwrap", "--"], "isolated")), \
                mock.patch.object(commands, "_run_command", return_value=1):
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertFalse(passed)
        self.assertIn("scorer_sandbox_unavailable exit=1", detail)
        self.assertNotIn(str(self.root), detail)

    def test_child_pid_json_does_not_prove_sandbox_setup(self):
        def failed_after_fork(argv, workspace, env, stdout, stderr, timeout_s, *, pass_fds):
            os.write(pass_fds[0], b'{"child-pid": 123}')
            return 1
        with mock.patch.object(commands, "_sandbox_prefix", return_value=(["/usr/bin/bwrap", "--"], "isolated")), \
                mock.patch.object(commands, "_run_command", side_effect=failed_after_fork):
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertEqual((passed, detail), (False, "scorer_sandbox_unavailable exit=1"))

    def test_timeout_before_sandbox_marker_is_unavailable(self):
        def stalled_setup(argv, workspace, env, stdout, stderr, timeout_s, *, pass_fds):
            os.write(pass_fds[0], b'{"child-pid": 123}')
            raise subprocess.TimeoutExpired("private sentinel", timeout_s)
        with mock.patch.object(commands, "_sandbox_prefix", return_value=(["/usr/bin/bwrap", "--"], "isolated")), \
                mock.patch.object(commands, "_run_command", side_effect=stalled_setup):
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertEqual((passed, detail), (False, "scorer_sandbox_unavailable exit=-1"))

    def test_timeout_after_sandbox_marker_remains_command_timeout(self):
        def stalled_command(argv, workspace, env, stdout, stderr, timeout_s, *, pass_fds):
            os.write(pass_fds[0], b'scorer-sandbox-started\n')
            raise subprocess.TimeoutExpired("private sentinel", timeout_s)
        with mock.patch.object(commands, "_sandbox_prefix", return_value=(["/usr/bin/bwrap", "--"], "isolated")), \
                mock.patch.object(commands, "_run_command", side_effect=stalled_command):
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertFalse(passed)
        self.assertIn("command_timeout network=isolated", detail)
        self.assertNotIn("private sentinel", detail)

    def test_nonexecuting_fixtures_do_not_probe_git_clone(self):
        fixture = {"objective_checks": [{"type": "files_exist", "id": "files", "paths": ["x"]}]}
        with mock.patch.object(run_eval, "_git", side_effect=AssertionError("no scoring process")) as git:
            self.assertEqual(run_eval.scorer_read_denied(SimpleNamespace(), fixture=fixture), [])
        git.assert_not_called()

    def test_probe_exception_text_is_suppressed(self):
        with mock.patch.object(commands, "_bubblewrap", return_value="/usr/bin/bwrap"), \
                mock.patch.object(commands.subprocess, "run", side_effect=OSError("private sentinel")):
            passed, detail = commands.command_succeeds(str(self.ws), [], ["python3", "-c", "pass"])
        self.assertFalse(passed)
        self.assertIn("scorer_sandbox_unavailable", detail)
        self.assertNotIn("private sentinel", detail)

    def test_read_denials_route_only_to_executing_checks(self):
        checks = [{"id": "cmd", "type": "command_succeeds", "argv": ["python3", "-c", "pass"]},
                  {"id": "files", "type": "files_exist", "paths": ["x"]}]
        denied = [self.root / "private"]
        with mock.patch.dict(objective.CHECKS, {"command_succeeds": mock.Mock(return_value=(True, "ok")),
                                              "files_exist": mock.Mock(return_value=(True, "ok"))}):
            objective.run_checks({"objective_checks": checks}, str(self.ws), str(self.ws), read_denied=denied)
            self.assertEqual(objective.CHECKS["command_succeeds"].call_args.kwargs["read_denied"],
                             [*denied, self.ws.parent])
            self.assertNotIn("read_denied", objective.CHECKS["files_exist"].call_args.kwargs)
        checks[0]["read_denied"] = []
        with self.assertRaises(ValueError):
            objective.run_checks({"objective_checks": checks}, str(self.ws), str(self.ws))

    def test_all_run_eval_scoring_calls_receive_the_seam(self):
        calls = [node for node in ast.walk(ast.parse((REPO / "harness/run_eval.py").read_text()))
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and isinstance(node.func.value, ast.Name) and node.func.value.id == "objective"
                 and node.func.attr == "run_checks"]
        self.assertEqual(len(calls), 5)
        for call in calls:
            keyword = next((k for k in call.keywords if k.arg == "read_denied"), None)
            self.assertIsNotNone(keyword)
            self.assertIsInstance(keyword.value, ast.Call)
            self.assertEqual(keyword.value.func.id, "scorer_read_denied")

    def test_seam_uses_common_git_directory_for_worktree_clone_parent(self):
        checkout = self.root / "repos" / "harness"
        checkout.mkdir(parents=True)
        (checkout / ".git").mkdir()
        worktree = self.root / "elsewhere" / "worktree"
        worktree.mkdir(parents=True)
        args = SimpleNamespace(results_dir=self.root / "outputs")
        for kind in (None, "command_succeeds", "repo_tests"):
            fixture = None if kind is None else {"objective_checks": [{"type": kind}]}
            with self.subTest(kind=kind), mock.patch.object(
                    run_eval, "_git", return_value=SimpleNamespace(stdout=str(checkout / ".git") + "\n")) as git:
                denied = run_eval.scorer_read_denied(args, harness_root=worktree, fixture=fixture)
            git.assert_called_once()
            self.assertIn(checkout.parent, denied)
            self.assertIn(worktree, denied)
            self.assertIn(args.results_dir.resolve(), denied)
            self.assertIn(run_eval.session_archive_dir().parent.resolve(), denied)


class LiveSandboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bwrap = shutil.which("bwrap") or str(Path.home() / ".local/bin/bwrap")
        try:
            probe = subprocess.run([bwrap, "--ro-bind", "/", "/", "--unshare-pid", "--proc", "/proc",
                                    "--dev", "/dev", "--die-with-parent", "--", "/usr/bin/true"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            raise unittest.SkipTest("live bubblewrap filesystem/PID namespaces unavailable")
        if probe.returncode:
            raise unittest.SkipTest("live bubblewrap filesystem/PID namespaces unavailable")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="scorer-live-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = self.root / "ws"
        self.ws.mkdir()
        self.denied = self.root / "private"
        self.denied.mkdir()
        (self.denied / "sentinel").write_text("private sentinel")

    def command(self, code, *args, denied=None):
        return commands.command_succeeds(str(self.ws), [], ["python3", "-c", code, *map(str, args)],
                                         read_denied=[self.denied] if denied is None else denied)

    def test_denied_read_and_proc_root_bypass_fail_while_workspace_is_writable(self):
        code = ("import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                "assert not p.exists(); assert not pathlib.Path('/proc/1/root'+str(p)).exists(); "
                "pathlib.Path('local-result').write_text('ok')")
        passed, detail = self.command(code, self.denied / "sentinel")
        self.assertTrue(passed, detail)
        self.assertEqual((self.ws / "local-result").read_text(), "ok")
        self.assertNotIn("private sentinel", detail)

    def test_absolute_outside_write_fails(self):
        outside = self.root / "outside"
        passed, detail = self.command("import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('bad')", outside)
        self.assertFalse(passed)
        self.assertIn("command_nonzero", detail)
        self.assertFalse(outside.exists())

    def test_workspace_carve_out_under_denied_ancestor_keeps_dependencies(self):
        for directory in ("node_modules", ".fixture-python"):
            (self.ws / directory).mkdir()
            (self.ws / directory / "installed").write_text("ok")
        passed, detail = self.command("import pathlib; assert pathlib.Path('node_modules/installed').read_text()=='ok'; "
                                     "assert pathlib.Path('.fixture-python/installed').read_text()=='ok'; "
                                     "pathlib.Path('result').write_text('ok')", denied=[self.root])
        self.assertTrue(passed, detail)

    def test_hidden_checker_copied_but_original_fixture_and_workspace_denied(self):
        fixture = self.root / "fixture"
        seed = fixture / "seed"
        seed.mkdir(parents=True)
        (fixture / "solution.patch").write_text("private sentinel")
        checker = fixture / "checker"
        checker.mkdir()
        code = ("from pathlib import Path\n"
                f"assert not Path({str(fixture / 'solution.patch')!r}).exists()\n"
                f"assert not Path({str(checker / 'hidden.py')!r}).exists()\n"
                f"assert not Path({str(self.ws / 'original')!r}).exists()\n"
                "assert Path('hidden.py').is_file()\nPath('scoring-write').write_text('ok')\n")
        (checker / "hidden.py").write_text(code)
        (self.ws / "original").write_text("agent final")
        passed, detail = repo_tests.repo_tests(str(self.ws), [], overlay="checker", argv=["python3", "hidden.py"],
                                              fail_to_pass=["selected"], seed=str(seed), read_denied=[self.denied])
        self.assertTrue(passed, detail)
        self.assertFalse((self.ws / "scoring-write").exists())

    def test_actual_setup_failure_after_successful_probe_is_unavailable(self):
        prepare = commands._sandbox_prefix
        def failed_mount(*args, **kwargs):
            prefix, network = prepare(*args, **kwargs)
            return [*prefix[:-1], "--ro-bind", str(self.root / "missing-source"),
                    "/sandbox-missing-source", "--"], network
        with mock.patch.object(commands, "_sandbox_prefix", side_effect=failed_mount):
            passed, detail = self.command("pass")
        self.assertEqual((passed, detail), (False, "scorer_sandbox_unavailable exit=1"))
        self.assertNotIn(str(self.root), detail)

    def test_real_command_exit_one_remains_command_nonzero(self):
        passed, detail = self.command("raise SystemExit(1)")
        self.assertFalse(passed)
        self.assertIn("command_nonzero exit=1", detail)

    def test_bootstrap_does_not_import_workspace_sitecustomize(self):
        (self.ws / "sitecustomize.py").write_text(
            "from pathlib import Path\nPath('premature-startup-import').write_text('bad')\n")
        passed, detail = commands.command_succeeds(str(self.ws), [], ["sh", "-c", "exit 0"],
                                                  read_denied=[self.denied])
        self.assertTrue(passed, detail)
        self.assertFalse((self.ws / "premature-startup-import").exists())

    def test_real_node_modules_import_survives_sandbox(self):
        if commands._fixed_interpreter("node") is None:
            self.skipTest("system node unavailable for live module import")
        package = self.ws / "node_modules" / "fixture-package"
        package.mkdir(parents=True)
        (package / "index.js").write_text("module.exports = 42;\n")
        passed, detail = commands.command_succeeds(
            str(self.ws), [], ["node", "-e", "if (require('fixture-package') !== 42) process.exit(1)"],
            read_denied=[self.root])
        self.assertTrue(passed, detail)

    def test_real_fixture_python_import_survives_original_workspace_denial(self):
        fixture = self.root / "fixture"
        seed = fixture / "seed"
        seed.mkdir(parents=True)
        checker = fixture / "checker"
        checker.mkdir()
        (checker / "hidden.py").write_text("import fixture_package\nassert fixture_package.answer == 42\n")
        venv = self.ws / ".fixture-python"
        (venv / "bin").mkdir(parents=True)
        python = Path(commands._fixed_interpreter("python3"))
        # The selected interpreter's version decides its deterministic venv path.
        version = subprocess.run([str(python), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                                 capture_output=True, text=True, timeout=2, check=True).stdout.strip()
        site = venv / "lib" / f"python{version}" / "site-packages"
        site.mkdir(parents=True)
        (site / "fixture_package.py").write_text("answer = 42\n")
        (venv / "bin" / "python3").symlink_to(python)
        (venv / "pyvenv.cfg").write_text(f"home = {python.parent}\ninclude-system-site-packages = false\n")
        passed, detail = repo_tests.repo_tests(
            str(self.ws), [], overlay="checker", argv=["python3", "hidden.py"],
            fail_to_pass=["selected"], seed=str(seed), _python_deps=True)
        self.assertTrue(passed, detail)

    def test_agent_helper_cannot_read_fixture_solution_from_hidden_test(self):
        fixture = self.root / "fixture"
        seed = fixture / "seed"
        seed.mkdir(parents=True)
        (fixture / "solution.patch").write_text("private sentinel")
        checker = fixture / "checker"
        checker.mkdir()
        (checker / "hidden.py").write_text("import helper\nassert helper.answer() == 'private sentinel'\n")
        (self.ws / "helper.py").write_text("from pathlib import Path\ndef answer():\n"
                                          f"    return Path({str(fixture / 'solution.patch')!r}).read_text()\n")
        passed, detail = repo_tests.repo_tests(str(self.ws), [], overlay="checker", argv=["python3", "hidden.py"],
                                              fail_to_pass=["selected"], seed=str(seed))
        self.assertFalse(passed)
        self.assertIn("exit=1", detail)
        self.assertNotIn("private sentinel", detail)
        self.assertNotIn(str(self.root), detail)


if __name__ == "__main__":
    unittest.main()
