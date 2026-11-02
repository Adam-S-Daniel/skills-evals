"""#606: the arm's workspace PATH directories are the agent's way out.

The Claude Code CLI starts programs from PATH outside the sandbox every time
it launches (a planted `git` and `sh` ran at startup, CLI 2.1.316, measured
with a dead API URL). Every follow-up turn is a new launch, and many fixtures
put `$WORKSPACE/bin` first on PATH. So a PATH directory inside the workspace
is guarded like the workspace's `.claude/`: the settings deny writes to it,
a trial in which it changed fails after that turn and is never resumed
(`agent_wrote_agent_config`), a relative or empty PATH entry never reaches
the CLI, and a PATH entry that is the workspace itself refuses the arm.

The CLI is a stand-in that records argv and PATH. No network, no real
`claude`.
"""

from __future__ import annotations

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

import run_eval  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arm_test_env import install_arm_test_environment  # noqa: E402

# Turn `PD_TURN` plants or alters a program the way an agent's Bash could
# without the settings' denyWrite: `plant` writes `bin/git`, `chmod` makes the
# seeded `bin/helper` executable, `link` swaps `bin/gh` for a symlink, `nested` writes under a
# subdirectory of `bin/`.
STAND_IN = f"""#!{sys.executable}
import json, os, sys
with open(os.environ["PD_LOG"], "a") as fh:
    fh.write(json.dumps({{"argv": sys.argv[1:], "path": os.environ.get("PATH")}}) + "\\n")
turn = sum(1 for _ in open(os.environ["PD_LOG"]))
mode = os.environ.get("PD_MODE", "ok")
if turn == int(os.environ.get("PD_TURN", "1")):
    if mode == "plant":
        with open("bin/git", "w") as fh:
            fh.write("#!/bin/sh\\ncurl https://example.com/x\\n")
        os.chmod("bin/git", 0o755)
    elif mode == "chmod":
        os.chmod("bin/helper", 0o755)
    elif mode == "link":
        os.remove("bin/gh")
        os.symlink("/tmp/elsewhere", "bin/gh")
    elif mode == "nested":
        os.makedirs("bin/lib", exist_ok=True)
        with open("bin/lib/x.sh", "w") as fh:
            fh.write("curl https://example.com/x\\n")
print(json.dumps({{"type": "result", "is_error": False, "result": "done",
                  "total_cost_usd": 0, "usage": {{}}, "num_turns": 1,
                  "duration_ms": 1, "session_id": "s1",
                  "modelUsage": {{"fake-default-model": {{}}}}}}))
"""


@install_arm_test_environment
def setUpModule() -> None:
    pass


def tearDownModule() -> None:
    unittest.doModuleCleanups()


class WorkspacePathTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="issue-606-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.log = self.root / "calls.jsonl"
        stand_in = self.root / "claude"
        stand_in.write_text(STAND_IN, encoding="utf-8")
        stand_in.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_STATE_HOME": str(self.root / "state"),
            "CLAUDE_BIN": str(stand_in), "PD_LOG": str(self.log)})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("MANAGED_SETTINGS_FILES", "MANAGED_SETTINGS_DROPINS"):
            patcher = mock.patch.object(run_eval, name, ())
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ws = Path(tempfile.mkdtemp(prefix="workspace-")).resolve()
        self.addCleanup(shutil.rmtree, self.ws, ignore_errors=True)
        self.seed_bin()

    def calls(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def run_arm(self, mode="ok", path="$WORKSPACE/bin:$PATH", turn=1, followups=("again",)):
        arm = {"name": "without_skill", "timeout": 60, "followups": list(followups),
               "env": {"PD_LOG": str(self.log), "PD_MODE": mode,
                       "PD_TURN": str(turn), "PATH": path}}
        return run_eval.run_agent(self.ws, "do it", arm)

    def test_the_settings_deny_writes_to_the_workspace_path_directory(self):
        out = self.run_arm()
        self.assertNotIn("error", out, out)
        self.assertEqual(len(self.calls()), 2)
        for call in self.calls():
            argv = call["argv"]
            settings = json.loads(argv[argv.index("--settings") + 1])
            bin_dir = self.ws / "bin"
            self.assertIn(str(bin_dir), settings["sandbox"]["filesystem"]["denyWrite"])
            self.assertIn(f"Edit(/{bin_dir})", settings["permissions"]["deny"])
            self.assertIn(f"Edit(/{bin_dir}/**)", settings["permissions"]["deny"])

    def test_a_program_changed_in_one_turn_is_never_launched_from(self):
        for mode, name in (("plant", "PATH:bin/git"), ("chmod", "PATH:bin/helper"),
                           ("link", "PATH:bin/gh"), ("nested", "PATH:bin/lib")):
            with self.subTest(mode=mode):
                self.log.unlink(missing_ok=True)
                self.seed_bin()
                out = self.run_arm(mode)
                self.assertEqual(out.get("error"), "agent_wrote_agent_config", out)
                self.assertIn(name, out["detail"])
                # The follow-up launch, which would have run it, never happens.
                self.assertEqual(len(self.calls()), 1)

    def seed_bin(self):
        shutil.rmtree(self.ws / "bin", ignore_errors=True)
        (self.ws / "bin").mkdir()
        for name, mode in (("gh", 0o755), ("helper", 0o644)):
            (self.ws / "bin" / name).write_text("#!/bin/sh\necho fake\n", encoding="utf-8")
            (self.ws / "bin" / name).chmod(mode)

    def test_a_path_directory_that_does_not_exist_refuses_the_arm(self):
        out = self.run_arm(path="$WORKSPACE/tools:$WORKSPACE/bin:$PATH")
        self.assertEqual(out.get("error"), "read_rules_unsafe", out)
        self.assertEqual(self.calls(), [])

    def test_a_dotdot_entry_in_the_workspace_refuses_the_arm(self):
        (self.ws / "tools").mkdir()
        out = self.run_arm(path="$WORKSPACE/bin/../tools:$PATH")
        self.assertEqual(out.get("error"), "read_rules_unsafe", out)
        self.assertEqual(self.calls(), [])

    def test_a_symlinked_program_is_guarded_at_its_target(self):
        (self.ws / "lib").mkdir()
        (self.ws / "lib" / "git").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.ws / "bin" / "git").symlink_to("../lib/git")
        dirs = run_eval._agent_path_dirs(self.ws, f"{self.ws / 'bin'}:/usr/bin")
        before = run_eval._agent_config_snapshot(self.ws, path_dirs=dirs)
        (self.ws / "lib" / "git").write_text("#!/bin/sh\ncurl x\n", encoding="utf-8")
        self.assertIn("PATH:bin/git",
                      run_eval._agent_config_written(self.ws, before, path_dirs=dirs))

    def test_a_change_on_a_later_turn_fails_after_that_turn(self):
        out = self.run_arm("plant", turn=2, followups=("again", "and again"))
        self.assertEqual(out.get("error"), "agent_wrote_agent_config", out)
        self.assertIn("follow-up 1 of 2", out["detail"])
        self.assertEqual(len(self.calls()), 2)

    def test_a_symlinked_path_directory_is_guarded_at_its_target(self):
        real = self.ws / "realbin"
        (self.ws / "bin").rename(real)
        (self.ws / "bin").symlink_to(real)
        dirs = run_eval._agent_path_dirs(self.ws, f"{self.ws / 'bin'}:/usr/bin")
        self.assertEqual(dirs, [self.ws / "bin", real])
        before = run_eval._agent_config_snapshot(self.ws, path_dirs=dirs)
        (real / "git").write_text("#!/bin/sh\n", encoding="utf-8")
        self.assertIn("PATH:realbin/git",
                      run_eval._agent_config_written(self.ws, before, path_dirs=dirs))

    def test_relative_and_empty_entries_never_reach_the_cli(self):
        out = self.run_arm(path="$WORKSPACE/bin::.:bin:/usr/bin:/bin")
        self.assertNotIn("error", out, out)
        for call in self.calls():
            self.assertEqual(call["path"].split(os.pathsep),
                             [str(self.ws / "bin"), "/usr/bin", "/bin"])

    def test_the_workspace_itself_on_path_refuses_the_arm(self):
        for path in ("$WORKSPACE:$PATH", "$WORKSPACE/bin/..:$PATH", "$WORKSPACE/:$PATH",
                     "$WORKSPACE/.:$PATH"):
            with self.subTest(path=path):
                out = self.run_arm(path=path)
                self.assertEqual(out.get("error"), "read_rules_unsafe", out)
                self.assertEqual(self.calls(), [])

    def test_paths_outside_the_workspace_are_not_guarded(self):
        self.assertEqual(run_eval._agent_path_dirs(self.ws, "/usr/bin:/bin"), [])


if __name__ == "__main__":
    unittest.main()
