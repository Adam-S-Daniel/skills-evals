"""#612: what is left of the CLI's unsandboxed launch-time reads (#606, #609).

* The CLI's own startup `git` gets `GIT_CEILING_DIRECTORIES` set to the
  workspace's parent, so a `.git` it cannot use in the workspace never sends
  it up to a parent directory's configuration.
* A fixture's `env:` may not move where git finds a repository or its
  configuration (`GIT_DIR`, `GIT_CONFIG_*`, ...).
* The file tools are denied every PATH directory outside the workspace and
  the real HOME's global git configuration; the sandbox already keeps Bash out.
* A PATH entry that holds the workspace (an ancestor) refuses the arm.

The CLI is a stand-in that records argv and environment. No network, no real
`claude`.
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

import guidance  # noqa: E402
import run_eval  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arm_test_env import install_arm_test_environment  # noqa: E402

STAND_IN = f"""#!{sys.executable}
import json, os, sys
with open(os.environ["LG_LOG"], "a") as fh:
    fh.write(json.dumps({{"argv": sys.argv[1:], "ceiling": os.environ.get("GIT_CEILING_DIRECTORIES")}}) + "\\n")
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


class LaunchGuardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="issue-612-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.log = self.root / "calls.jsonl"
        stand_in = self.root / "claude"
        stand_in.write_text(STAND_IN, encoding="utf-8")
        stand_in.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_STATE_HOME": str(self.root / "state"),
            "CLAUDE_BIN": str(stand_in), "LG_LOG": str(self.log)})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("MANAGED_SETTINGS_FILES", "MANAGED_SETTINGS_DROPINS"):
            patcher = mock.patch.object(run_eval, name, ())
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ws = Path(tempfile.mkdtemp(prefix="workspace-")).resolve()
        self.addCleanup(shutil.rmtree, self.ws, ignore_errors=True)

    def calls(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def run_arm(self, env=None, followups=("again",)):
        arm = {"name": "without_skill", "timeout": 60, "followups": list(followups),
               "env": {"LG_LOG": str(self.log), **(env or {})}}
        return run_eval.run_agent(self.ws, "do it", arm)

    def test_every_launch_stops_git_at_the_workspace(self):
        self.assertNotIn("error", self.run_arm())
        self.assertEqual([c["ceiling"] for c in self.calls()], [str(self.ws.parent)] * 2)

    def test_with_the_ceiling_git_never_reads_a_parents_configuration(self):
        # The move the ceiling closes: the workspace's `.git` is unusable,
        # and a parent directory holds one of its own.
        parent = self.root / "parent"
        ws = parent / "ws"
        ws.mkdir(parents=True)
        env = {"PATH": "/usr/bin:/bin", "HOME": str(self.home),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
        subprocess.run(["git", "init", "-q", str(parent)], check=True, env=env)
        subprocess.run(["git", "-C", str(parent), "config", "marker.x", "parent"],
                       check=True, env=env)
        (ws / ".git").mkdir()  # no HEAD: git skips it
        read = lambda extra: subprocess.run(  # noqa: E731
            ["git", "config", "marker.x"], cwd=ws, capture_output=True,
            text=True, env={**env, **extra}).stdout.strip()
        self.assertEqual(read({}), "parent")
        self.assertEqual(read({"GIT_CEILING_DIRECTORIES": str(parent)}), "")

    def test_a_fixture_may_not_redirect_git(self):
        for name in ("GIT_DIR", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_COUNT",
                     "GIT_CONFIG_KEY_0", "GIT_CONFIG_PARAMETERS",
                     "GIT_CEILING_DIRECTORIES", "XDG_CONFIG_HOME"):
            with self.subTest(name=name):
                with self.assertRaises(guidance.GuidanceError) as caught:
                    guidance.check_env_block({name: "x"}, "f")
                self.assertIn("#612", str(caught.exception))
        guidance.check_env_block({"GIT_TRACE": "1", "GH_REPO": "o/r"}, "f")

    def test_the_file_tools_are_denied_what_the_cli_runs_at_launch(self):
        tools = self.root / "tools"
        tools.mkdir()
        self.assertNotIn("error", self.run_arm(env={"PATH": f"{tools}:/usr/bin:/bin"},
                                               followups=()))
        argv = self.calls()[0]["argv"]
        deny = json.loads(argv[argv.index("--settings") + 1])["permissions"]["deny"]
        for path in (tools, Path("/usr/bin"), self.home / ".gitconfig",
                     self.home / ".config" / "git"):
            self.assertIn(f"Edit(/{path})", deny)
            self.assertIn(f"Edit(/{path}/**)", deny)

    def test_a_symlinked_gitconfig_denies_its_target_too(self):
        # A dotfiles setup links ~/.gitconfig elsewhere; git reads the target.
        dotfiles = self.root / "dotfiles"
        dotfiles.mkdir()
        (dotfiles / "gitconfig").write_text("[user]\n\tname = x\n", encoding="utf-8")
        (self.home / ".gitconfig").symlink_to(dotfiles / "gitconfig")
        self.assertNotIn("error", self.run_arm(followups=()))
        argv = self.calls()[0]["argv"]
        deny = json.loads(argv[argv.index("--settings") + 1])["permissions"]["deny"]
        self.assertIn(f"Edit(/{(dotfiles / 'gitconfig').resolve()})", deny)

    def test_a_path_entry_that_holds_the_workspace_refuses_the_arm(self):
        out = self.run_arm(env={"PATH": f"{self.ws.parent}:/usr/bin:/bin"})
        self.assertEqual(out.get("error"), "read_rules_unsafe", out)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
