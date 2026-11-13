"""#594: a late write into an in-place pair's profile.

Three parts: the CLI's `plugins/synced/<id>/.last-complete-round` stamp is a
profile marker; the agent CLI starts in its own session and its process group
is ended however the call ends; and a cleaned pair profile that a late writer
recreated holding only markers is removed instead of refused.

No real CLI, no real signal and no wall clock: every spawn is a stand-in,
`os.kill` and `os.killpg` are patched recorders in every test that could reach
them, and the group helper's wait runs on an injected clock. Run with the
repository runner, inside a PID namespace.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import delivery  # noqa: E402
import run_eval  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arm_test_env import install_arm_test_environment  # noqa: E402

SYNCED = "plugins/synced/0b7c2c1e-5d0f-4e8e-9a51-3f7b0c3f9d21/.last-complete-round"
# Never a real process: every test that hands it to code that could signal
# patches os.kill and os.killpg.
FAKE_PGID = 424242


@install_arm_test_environment
def setUpModule() -> None:
    pass


def tearDownModule() -> None:
    unittest.doModuleCleanups()


class _Scratch(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, base: Path, rel: str, data: str = "1761955200\n") -> Path:
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        return path


class SyncedPluginMarkerTests(_Scratch):
    """The stamp is exempt during a turn, as the skills one is, and only as
    a small regular file one directory below `plugins/synced/`."""

    def setUp(self):
        super().setUp()
        self.ws = self.root / "ws"
        self.config = self.root / "config"
        self.ws.mkdir()
        self.write(self.config, "CLAUDE.md", "guidance\n")
        self.before = run_eval._agent_config_snapshot(self.ws, self.config)

    def written(self):
        return run_eval._agent_config_written(self.ws, self.before, self.config)

    def test_a_stamp_written_during_a_turn_is_exempt(self):
        self.write(self.config, SYNCED)
        self.assertIsNone(self.written())
        self.write(self.config, SYNCED, "x" * 4096)
        self.assertIsNone(self.written())

    def test_an_oversize_stamp_is_a_change(self):
        self.write(self.config, SYNCED, "x" * 4097)
        self.assertIn(SYNCED, self.written())

    def test_a_directory_or_symlink_at_the_stamp_is_a_change(self):
        marker = self.config / SYNCED
        marker.mkdir(parents=True)
        self.write(marker, "hooks/hooks.json", "{}")
        self.assertIn(f"{SYNCED}/hooks/hooks.json", self.written())
        (marker / "hooks" / "hooks.json").unlink()
        (marker / "hooks").rmdir()
        marker.rmdir()
        marker.symlink_to(self.config / "CLAUDE.md")
        self.assertIn(SYNCED, self.written())

    def test_other_paths_under_plugins_synced_stay_watched(self):
        for rel in ("plugins/synced/u/p/.last-complete-round",
                    "plugins/synced/u/hooks/.last-complete-round",
                    "plugins/synced/.last-complete-round",
                    "plugins/synced/u/.last-complete-round.json",
                    "plugins/synced/u/hooks/hooks.json",
                    "plugins/cache/m/p/1/.last-complete-round"):
            with self.subTest(rel=rel):
                path = self.write(self.config, rel)
                self.assertIn(rel, self.written())
                path.unlink()

    def test_the_marker_table_carries_the_same_cap_as_the_skills_stamp(self):
        markers = run_eval._CLI_PROFILE_MARKERS
        self.assertEqual(markers["plugins/synced/*/.last-complete-round"],
                         markers["skills/synced/*/.last-complete-round"])
        self.assertEqual(markers["plugins/synced/*/.last-complete-round"], 4096)


class KillProcessGroupTests(unittest.TestCase):
    """The guard comes before any signal; the wait is bounded and injected."""

    def setUp(self):
        self.killpg = self.enterContext(mock.patch("os.killpg"))
        self.kill = self.enterContext(mock.patch("os.kill"))
        self.now = 0.0
        self.pauses = []

    def clock(self):
        return self.now

    def pause(self, seconds):
        self.pauses.append(seconds)
        self.now += seconds

    def reap(self, pgid, grace=1.0, states=lambda _pgid: ["S"]):
        run_eval._kill_process_group(pgid, grace=grace, poll=0.25,
                                     clock=self.clock, pause=self.pause,
                                     states=states)

    def test_an_unsafe_group_is_never_signaled(self):
        for pgid in (0, 1, -1, -42, True, False, None, "4242", 4242.0,
                     mock.MagicMock(), os.getpid(), os.getpgrp()):
            with self.subTest(pgid=pgid):
                self.reap(pgid)
                self.killpg.assert_not_called()
                self.kill.assert_not_called()
                self.assertEqual(self.pauses, [])

    def test_the_harness_group_is_refused_when_it_is_read(self):
        with mock.patch.object(run_eval.os, "getpgrp", return_value=FAKE_PGID), \
                mock.patch.object(run_eval.os, "getpid", return_value=FAKE_PGID + 1):
            self.reap(FAKE_PGID)
            self.reap(FAKE_PGID + 1)
        self.killpg.assert_not_called()
        self.kill.assert_not_called()

    def test_an_emptied_group_gets_sigterm_and_no_sigkill(self):
        self.killpg.side_effect = [None, ProcessLookupError()]
        self.reap(FAKE_PGID)
        self.assertEqual(self.killpg.call_args_list,
                         [mock.call(FAKE_PGID, signal.SIGTERM), mock.call(FAKE_PGID, 0)])
        self.assertEqual(self.pauses, [0.25])
        self.kill.assert_not_called()

    def test_a_group_left_after_the_grace_gets_sigkill(self):
        self.reap(FAKE_PGID, grace=1.0)
        calls = self.killpg.call_args_list
        self.assertEqual(calls[0], mock.call(FAKE_PGID, signal.SIGTERM))
        self.assertEqual(calls[-1], mock.call(FAKE_PGID, signal.SIGKILL))
        self.assertEqual(calls[1:-1], [mock.call(FAKE_PGID, 0)] * 4)
        self.assertEqual(self.pauses, [0.25] * 4)
        self.assertEqual(self.now, 1.0)
        self.kill.assert_not_called()

    def test_a_group_of_zombies_ends_the_wait_without_sigkill(self):
        seen = []
        answers = iter((["S", "Z"], ["Z", "Z"]))

        def states(pgid):
            seen.append(pgid)
            return next(answers)
        self.reap(FAKE_PGID, grace=5.0, states=states)
        self.assertEqual(seen, [FAKE_PGID, FAKE_PGID])
        self.assertEqual(self.killpg.call_args_list,
                         [mock.call(FAKE_PGID, signal.SIGTERM)]
                         + [mock.call(FAKE_PGID, 0)] * 2)
        self.assertEqual(self.pauses, [0.25, 0.25])
        self.kill.assert_not_called()

    def test_without_proc_the_wait_runs_its_course(self):
        self.reap(FAKE_PGID, grace=0.5, states=lambda _pgid: None)
        self.assertEqual(self.killpg.call_args_list[-1],
                         mock.call(FAKE_PGID, signal.SIGKILL))
        self.assertEqual(self.pauses, [0.25, 0.25])

    def test_no_member_found_in_proc_still_ends_with_sigkill(self):
        # A /proc from another PID namespace lists none of the group.
        self.reap(FAKE_PGID, grace=0.5, states=lambda _pgid: [])
        self.assertEqual(self.killpg.call_args_list[-1],
                         mock.call(FAKE_PGID, signal.SIGKILL))

    def test_an_already_empty_or_foreign_group_is_left_alone(self):
        for error in (ProcessLookupError(), PermissionError()):
            with self.subTest(error=type(error).__name__):
                self.killpg.reset_mock()
                self.killpg.side_effect = error
                self.reap(FAKE_PGID)
                self.assertEqual(self.killpg.call_args_list,
                                 [mock.call(FAKE_PGID, signal.SIGTERM)])
                self.assertEqual(self.pauses, [])


class GroupStatesTests(_Scratch):
    """`_group_states` reads a /proc-shaped tree; no real /proc is used."""

    def stat(self, pid, comm, state, pgrp):
        self.write(self.root, f"{pid}/stat",
                   f"{pid} ({comm}) {state} 1 {pgrp} {pgrp} 0 -1 4194304\n")

    def test_members_are_matched_by_pgrp_past_the_last_paren(self):
        self.stat(10, "claude", "S", 10)
        self.stat(11, "odd) name (x", "Z", 10)
        self.stat(12, "bash", "R", 99)
        self.write(self.root, "13/stat", "garbage")
        self.write(self.root, "self/stat", "1 (x) R 1 10 10")
        (self.root / "14").mkdir()  # vanished: no stat
        self.assertEqual(sorted(run_eval._group_states(10, str(self.root))), ["S", "Z"])
        self.assertEqual(run_eval._group_states(77, str(self.root)), [])

    def test_no_proc_is_unknown(self):
        self.assertIsNone(run_eval._group_states(10, str(self.root / "missing")))


class _FakeChild:
    """subprocess.Popen's stand-in: no process is started."""

    def __init__(self, cmd, outcome, **kwargs):
        self.args, self.kwargs, self.outcome = cmd, kwargs, outcome
        self.pid = FAKE_PGID
        self.returncode = None
        self.killed = self.waited = False

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.wait()

    def communicate(self, input=None, timeout=None):
        self.timeout = timeout
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        self.returncode = self.outcome[0]
        return self.outcome[1], self.outcome[2]

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.waited = True
        if self.returncode is None:
            self.returncode = -9 if self.killed else 0
        return self.returncode

    def poll(self):
        return self.returncode


class OwnSessionLaunchTests(_Scratch):
    """The agent CLI's spawn: own session, and its group ended on a normal
    exit, a timeout and an exception, with run's result unchanged."""

    def setUp(self):
        super().setUp()
        self.killpg = self.enterContext(mock.patch("os.killpg"))
        self.kill = self.enterContext(mock.patch("os.kill"))
        self.reap = self.enterContext(mock.patch.object(run_eval, "_kill_process_group"))
        self.children = []

    def spawn(self, outcome):
        def popen(cmd, **kwargs):
            child = _FakeChild(cmd, outcome, **kwargs)
            self.children.append(child)
            return child
        return mock.patch.object(run_eval.subprocess, "Popen", popen)

    def launch(self):
        return run_eval._run_in_own_session(
            ["claude", "-p", "x"], cwd=self.root, capture_output=True, text=True,
            timeout=30, env={"PATH": "/usr/bin"})

    def assert_reaped_once(self):
        self.reap.assert_called_once_with(FAKE_PGID)
        self.killpg.assert_not_called()
        self.kill.assert_not_called()

    def test_a_normal_exit_returns_what_run_returned_and_ends_the_group(self):
        with self.spawn((3, "out", "err")):
            result = self.launch()
        self.assertEqual((result.args, result.returncode, result.stdout, result.stderr),
                         (["claude", "-p", "x"], 3, "out", "err"))
        (child,) = self.children
        self.assertEqual(child.kwargs, {
            "cwd": self.root, "env": {"PATH": "/usr/bin"},
            "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True,
            "start_new_session": True})
        self.assertEqual(child.timeout, 30)
        self.assertFalse(child.killed)
        self.assert_reaped_once()

    def test_a_timeout_kills_reaps_and_raises_as_run_does(self):
        with self.spawn(subprocess.TimeoutExpired(["claude"], 30)), \
                self.assertRaises(subprocess.TimeoutExpired):
            self.launch()
        (child,) = self.children
        self.assertTrue(child.killed and child.waited)
        self.assert_reaped_once()

    def test_an_exception_kills_and_raises(self):
        for error in (RuntimeError("boom"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.reap.reset_mock()
                self.children.clear()
                with self.spawn(error), self.assertRaises(type(error)):
                    self.launch()
                self.assertTrue(self.children[0].killed)
                self.assert_reaped_once()

    def test_a_signal_turned_exit_kills_the_cli_and_ends_its_group(self):
        with self.spawn(SystemExit(128 + signal.SIGTERM)), \
                self.assertRaises(SystemExit) as caught:
            self.launch()
        self.assertEqual(caught.exception.code, 128 + signal.SIGTERM)
        self.assertTrue(self.children[0].killed)
        self.assert_reaped_once()

    def test_a_cli_that_never_started_has_no_group_to_end(self):
        def popen(cmd, **kwargs):
            raise FileNotFoundError(2, "No such file")
        with mock.patch.object(run_eval.subprocess, "Popen", popen), \
                self.assertRaises(FileNotFoundError):
            self.launch()
        self.reap.assert_not_called()
        self.killpg.assert_not_called()
        self.kill.assert_not_called()

    def test_a_bad_timeout_is_refused_before_the_spawn(self):
        with mock.patch.object(run_eval.subprocess, "Popen") as popen, \
                self.assertRaises(run_eval.guidance.GuidanceError):
            run_eval._run_in_own_session(["claude"], cwd=self.root, capture_output=True,
                                         text=True, timeout=0, env={})
        popen.assert_not_called()
        self.reap.assert_not_called()


class RunAgentLaunchTests(OwnSessionLaunchTests):
    """run_agent starts the CLI through the helper, every way it can end."""

    CLI = "claude"
    REPLY = {"type": "result", "is_error": False, "result": "done",
             "total_cost_usd": 0.25, "usage": {"input_tokens": 2},
             "num_turns": 1, "duration_ms": 8, "session_id": "s-1",
             "modelUsage": {"fake-default-model": {"inputTokens": 2}}}

    def run_agent(self, **arm):
        # The CLI name is resolved on the host's PATH (`run_canary.cli_bin`),
        # so a real `claude` anywhere on it would change what is launched.
        # Pin the resolved name: these tests are about the session and group
        # handling, not about where the CLI lives.
        self.enterContext(mock.patch.object(run_eval.run_canary, "cli_bin",
                                            return_value=self.CLI))
        return run_eval.run_agent(self.root, "prompt",
                                  {"name": "without_skill", "timeout": 30, **arm})

    def test_a_normal_exit_is_scored_and_its_group_ended(self):
        with self.spawn((0, json.dumps(self.REPLY), "")):
            answer = self.run_agent()
        self.assertNotIn("error", answer, answer)
        self.assertEqual(answer["transcript"], "done")
        (child,) = self.children
        self.assertIs(child.kwargs["start_new_session"], True)
        self.assertEqual(child.args[0], self.CLI)
        self.assert_reaped_once()

    def test_each_followup_call_ends_its_own_group(self):
        with self.spawn((0, json.dumps(self.REPLY), "")):
            answer = self.run_agent(followups=["again"])
        self.assertNotIn("error", answer, answer)
        self.assertEqual(len(self.children), 2)
        self.assertTrue(all(c.kwargs["start_new_session"] for c in self.children))
        self.assertEqual(self.reap.call_args_list, [mock.call(FAKE_PGID)] * 2)
        self.killpg.assert_not_called()
        self.kill.assert_not_called()

    def test_a_timeout_is_the_arms_timeout_and_its_group_ended(self):
        with self.spawn(subprocess.TimeoutExpired(["claude"], 30)):
            answer = self.run_agent()
        self.assertEqual(answer["error"], "timeout")
        self.assertEqual(answer["detail"], "agent timed out after 30s")
        self.assertTrue(self.children[0].killed)
        self.assert_reaped_once()

    def test_an_exception_propagates_after_its_group_is_ended(self):
        with self.spawn(RuntimeError("boom")), self.assertRaises(RuntimeError):
            self.run_agent()
        self.assert_reaped_once()

    def test_a_spawn_failure_is_unchanged(self):
        def popen(cmd, **kwargs):
            raise FileNotFoundError(2, "No such file")
        with mock.patch.object(run_eval.subprocess, "Popen", popen):
            answer = self.run_agent()
        self.assertEqual(answer["error"], "spawn_failed")
        self.reap.assert_not_called()
        self.killpg.assert_not_called()


class SignalExitTests(unittest.TestCase):
    """main() turns SIGTERM and SIGHUP into SystemExit for its call only. No
    signal is delivered: the handler is called directly, and main's body is
    a stand-in."""

    def setUp(self):
        self.killpg = self.enterContext(mock.patch("os.killpg"))
        self.kill = self.enterContext(mock.patch("os.kill"))

    def test_the_handler_ignores_both_signals_then_exits_128_plus_the_signal(self):
        for signum in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signum=signum), \
                    mock.patch("signal.signal") as installed:
                with self.assertRaises(SystemExit) as caught:
                    run_eval._exit_on_signal(signum, None)
                self.assertEqual(caught.exception.code, 128 + signum)
                self.assertEqual(installed.call_args_list,
                                 [mock.call(signal.SIGTERM, signal.SIG_IGN),
                                  mock.call(signal.SIGHUP, signal.SIG_IGN)])
        self.killpg.assert_not_called()
        self.kill.assert_not_called()

    def test_main_installs_the_handlers_and_restores_the_previous_ones(self):
        before = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGHUP)}
        during = {}

        def body():
            during.update({s: signal.getsignal(s) for s in before})
            return 7
        self.assertEqual(run_eval._exiting_on_signals(body)(), 7)
        self.assertEqual(during, {s: run_eval._exit_on_signal for s in before})
        self.assertEqual({s: signal.getsignal(s) for s in before}, before)

        def failing():
            raise SystemExit(143)
        with self.assertRaises(SystemExit):
            run_eval._exiting_on_signals(failing)()
        self.assertEqual({s: signal.getsignal(s) for s in before}, before)

    def test_main_is_the_decorated_one_and_import_installs_nothing(self):
        self.assertEqual(run_eval.main.__name__, "main")
        self.assertIs(run_eval.main.__wrapped__.__wrapped__.__name__, "main")
        self.assertIsNot(signal.getsignal(signal.SIGTERM), run_eval._exit_on_signal)
        self.assertIsNot(signal.getsignal(signal.SIGHUP), run_eval._exit_on_signal)


class LeftoverPairProfileTests(_Scratch):
    """`_in_place_scratch` removes a leftover holding only late markers, and
    refuses anything else with install_collision, as before."""

    def setUp(self):
        super().setUp()
        self.config = self.root / "pair" / "config"
        self.config.parent.mkdir()
        self.plan = {"_pair_config": self.config}

    def scratch(self) -> Path:
        scratch = run_eval._in_place_scratch(self.plan)
        self.addCleanup(lambda: scratch.rmdir() if scratch.is_dir() else None)
        return scratch

    def assert_refused(self):
        with self.assertRaises(delivery.DeliveryError) as caught:
            self.scratch()
        self.assertEqual(caught.exception.code, "install_collision")
        self.assertTrue(os.path.lexists(self.config))

    def test_a_markers_only_leftover_is_removed(self):
        for rels in ((SYNCED,),
                     (SYNCED, "skills/synced/u/.last-complete-round",
                      "plugins/cache/m/p/1/.orphaned_at")):
            with self.subTest(rels=rels):
                for rel in rels:
                    self.write(self.config, rel)
                scratch = self.scratch()
                self.assertTrue(scratch.is_dir())
                self.assertFalse(os.path.lexists(self.config))

    def test_a_leftover_with_anything_else_still_refuses(self):
        for extra in ("settings.json", "CLAUDE.md", ".claude.json",
                      "plugins/installed_plugins.json",
                      "projects/-tmp-ws/s.jsonl",
                      "plugins/synced/u/hooks/.last-complete-round"):
            with self.subTest(extra=extra):
                self.write(self.config, SYNCED)
                self.write(self.config, extra)
                self.assert_refused()
                run_eval.shutil.rmtree(self.config)

    def test_an_oversize_or_linked_marker_still_refuses(self):
        self.write(self.config, SYNCED, "x" * 4097)
        self.assert_refused()
        run_eval.shutil.rmtree(self.config)
        target = self.write(self.root, "elsewhere")
        (self.config / SYNCED).parent.mkdir(parents=True)
        (self.config / SYNCED).symlink_to(target)
        self.assert_refused()

    def test_a_linked_directory_still_refuses(self):
        real = self.root / "real"
        self.write(real, ".last-complete-round")
        (self.config / "plugins" / "synced").mkdir(parents=True)
        (self.config / "plugins" / "synced" / "u").symlink_to(real)
        self.assert_refused()

    def test_a_linked_profile_still_refuses(self):
        real = self.root / "real"
        self.write(real, SYNCED)
        self.config.symlink_to(real)
        self.assert_refused()

    def test_an_empty_leftover_still_refuses(self):
        self.config.mkdir()
        self.assert_refused()


if __name__ == "__main__":
    unittest.main()
