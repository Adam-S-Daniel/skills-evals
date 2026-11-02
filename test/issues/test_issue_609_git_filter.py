"""#609: the CLI's own startup `git` reads the workspace's git configuration.

CLI 2.1.316 runs `git status --short`, `git log` and `git config user.name`
in its cwd at every launch, outside the sandbox, with hooks and fsmonitor
off but filter drivers on. A follow-up turn is a new launch, so a multi-turn
arm whose git configuration changed during a turn fails after that turn and
is never resumed (`agent_wrote_agent_config`). Watched: `.git` itself (a
rename and re-create changes its inode), its config files, every include
they name (missing targets too), and the arm's global git config.

The CLI is a stand-in. No network, no real `claude`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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

# On turn `GF_TURN` the stand-in changes the workspace's git configuration the
# way `GF_MODE` names, standing in for an agent whose write got through.
STAND_IN = f"""#!{sys.executable}
import json, os, shutil, sys
with open(os.environ["GF_LOG"], "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
turn = sum(1 for _ in open(os.environ["GF_LOG"]))
mode = os.environ.get("GF_MODE", "ok")
driver = '[filter "x"]\\n\\tclean = cat\\n'
if turn == int(os.environ.get("GF_TURN", "1")):
    if mode == "config":
        with open(".git/config", "a") as fh:
            fh.write(driver)
    elif mode == "recreate":
        os.rename(".git", ".git_old")
        shutil.copytree(".git_old", ".git", symlinks=True)
    elif mode == "include":
        with open("inc.cfg", "w") as fh:
            fh.write(driver)
    elif mode == "global":
        with open(os.path.join(os.environ["HOME"], ".gitconfig"), "a") as fh:
            fh.write(driver)
    elif mode == "attributes":
        os.makedirs(".git/info", exist_ok=True)
        with open(".git/info/attributes", "w") as fh:
            fh.write("* filter=x\\n")
    elif mode == "commit":
        with open("work.txt", "w") as fh:
            fh.write("work\\n")
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


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd,
                   check=True, capture_output=True,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(cwd),
                        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})


class WorkspaceGitConfigTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="issue-609-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.log = self.root / "calls.jsonl"
        stand_in = self.root / "claude"
        stand_in.write_text(STAND_IN, encoding="utf-8")
        stand_in.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_STATE_HOME": str(self.root / "state"),
            "CLAUDE_BIN": str(stand_in), "GF_LOG": str(self.log)})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("MANAGED_SETTINGS_FILES", "MANAGED_SETTINGS_DROPINS"):
            patcher = mock.patch.object(run_eval, name, ())
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ws = Path(tempfile.mkdtemp(prefix="workspace-")).resolve()
        self.addCleanup(shutil.rmtree, self.ws, ignore_errors=True)
        git(self.ws, "init", "-q", ".")
        (self.ws / "a.txt").write_text("hello\n", encoding="utf-8")

    def calls(self) -> list:
        if not self.log.exists():
            return []
        return self.log.read_text().splitlines()

    def run_arm(self, mode="ok", turn=1, followups=("again",)):
        arm = {"name": "without_skill", "timeout": 60, "followups": list(followups),
               "env": {"GF_LOG": str(self.log), "GF_MODE": mode, "GF_TURN": str(turn)}}
        return run_eval.run_agent(self.ws, "do it", arm)

    def test_a_changed_git_configuration_is_never_launched_on(self):
        for mode, name in (("config", "git:.git/config"),
                           ("recreate", "git:.git"),
                           ("attributes", "git:.git/info/attributes")):
            with self.subTest(mode=mode):
                self.log.unlink(missing_ok=True)
                shutil.rmtree(self.ws / ".git_old", ignore_errors=True)
                shutil.rmtree(self.ws / ".git", ignore_errors=True)
                git(self.ws, "init", "-q", ".")
                out = self.run_arm(mode)
                self.assertEqual(out.get("error"), "agent_wrote_agent_config", out)
                self.assertIn(name, out["detail"])
                self.assertEqual(len(self.calls()), 1)

    def test_an_include_created_later_is_a_change(self):
        git(self.ws, "config", "include.path", "../inc.cfg")
        out = self.run_arm("include")
        self.assertEqual(out.get("error"), "agent_wrote_agent_config", out)
        self.assertIn("git:inc.cfg", out["detail"])
        self.assertEqual(len(self.calls()), 1)

    def test_the_arms_global_git_config_is_watched(self):
        out = self.run_arm("global")
        self.assertEqual(out.get("error"), "agent_wrote_agent_config", out)
        self.assertIn(".gitconfig", out["detail"])

    def test_a_change_on_a_later_turn_fails_before_the_next_launch(self):
        out = self.run_arm("config", turn=2, followups=("again", "and again"))
        self.assertEqual(out.get("error"), "agent_wrote_agent_config", out)
        self.assertIn("follow-up 1 of 2", out["detail"])
        self.assertEqual(len(self.calls()), 2)

    def test_ordinary_work_passes(self):
        out = self.run_arm("commit", followups=("again", "and again"))
        self.assertNotIn("error", out, out)
        self.assertEqual(len(self.calls()), 3)

    def test_the_last_turn_and_a_one_turn_arm_are_not_held_to_it(self):
        # No launch follows, so the CLI never reads what changed.
        self.assertNotIn("error", self.run_arm("config", turn=2))
        self.log.unlink()
        self.assertNotIn("error", self.run_arm("config", followups=()))

    def test_include_targets_resolve_as_git_resolves_them(self):
        git(self.ws, "config", "include.path", "rel.cfg")
        git(self.ws, "config", "includeIf.gitdir:/x/.path", "~/home.cfg")
        targets = run_eval._git_include_targets(self.ws / ".git" / "config", str(self.home))
        self.assertEqual(targets, [self.ws / ".git" / "rel.cfg", self.home / "home.cfg"])


if __name__ == "__main__":
    unittest.main()
