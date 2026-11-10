"""A fixture's stand-in `claude` must never replace the CLI the harness runs (#950).

`two-setup-gaps/durable-machine-marketplace` puts `$WORKSPACE/bin` first on
the arm's PATH, holding an offline `claude` stand-in for the AGENT to call.
The harness launched the agent and its delivery guard as bare `claude` with
that same env, and `subprocess` searches the PATH of the env it is given, so
both ran the stand-in, read its empty stdout and reported every arm
INCONCLUSIVE (`invalid_json: ... character 0 of 0`) on every run.

Here the harness's own PATH holds a JSON-printing stand-in for the CLI and
the child env's PATH puts a silent decoy named `claude` in front of it, as
the fixture does. No network, no real `claude`.
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

import run_canary  # noqa: E402
import run_eval  # noqa: E402

CLI = f"""#!{sys.executable}
import json
print(json.dumps({{"type": "result", "is_error": False, "result": "ok",
                  "total_cost_usd": 0, "usage": {{}}, "num_turns": 1,
                  "duration_ms": 1, "session_id": "s",
                  "modelUsage": {{"fake-default-model": {{}}}}}}))
"""

# The fixture's stand-in, in shape: it logs the call and prints nothing for
# anything but the marketplace list.
DECOY = """#!/bin/sh
echo "$*" >> "$(dirname "$0")/../decoy-calls.log"
exit 0
"""

BASE_PATH = os.pathsep.join(dict.fromkeys(
    (str(Path(sys.executable).parent), "/usr/local/bin", "/usr/bin", "/bin")))


class FixtureStandInDoesNotShadowTheCli(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="issue950-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        cli_dir = self.root / "cli"
        cli_dir.mkdir()
        (cli_dir / "claude").write_text(CLI, encoding="utf-8")
        (cli_dir / "claude").chmod(0o755)
        self.ws = self.root / "workspace"
        (self.ws / "bin").mkdir(parents=True)
        (self.ws / "bin" / "claude").write_text(DECOY, encoding="utf-8")
        (self.ws / "bin" / "claude").chmod(0o755)
        self.log = self.ws / "decoy-calls.log"
        self.home = self.root / "home"
        self.home.mkdir()
        mountinfo = self.root / "mountinfo"
        mountinfo.write_text("", encoding="utf-8")
        self.harness_path = os.pathsep.join((str(cli_dir), BASE_PATH))
        # The fixture's `env: PATH: "$WORKSPACE/bin:$PATH"`, expanded.
        self.arm_path = os.pathsep.join((str(self.ws / "bin"), self.harness_path))
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home),
                                               "PATH": self.harness_path,
                                               run_eval.MOUNTINFO_ENV: str(mountinfo)})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("CLAUDE_BIN", None)

    def test_the_decoy_shadows_a_bare_name(self):
        # Proves the checks below can fail: a bare `claude` launched with the
        # arm's env runs the decoy, which prints nothing.
        out = subprocess.run(["claude", "-p", "x"], env={"PATH": self.arm_path},
                             capture_output=True, text=True, timeout=60,
                             stdin=subprocess.DEVNULL, check=True)
        self.assertEqual(out.stdout, "")
        self.assertTrue(self.log.exists())

    def test_cli_bin_resolves_on_the_harness_path(self):
        self.assertEqual(run_canary.cli_bin(), str(self.root / "cli" / "claude"))

    def test_cli_bin_keeps_an_explicit_path_and_an_unknown_name(self):
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": "/opt/x/claude"}):
            self.assertEqual(run_canary.cli_bin(), "/opt/x/claude")
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": "no-such-cli-950"}):
            self.assertEqual(run_canary.cli_bin(), "no-such-cli-950")

    def test_delivery_guard_leg(self):
        result = run_canary.run_leg(self.ws, "probe", "Read", model=None, timeout=60,
                                    env={"PATH": self.arm_path, "HOME": str(self.home)})
        self.assertNotIn("error", result, result)
        self.assertFalse(self.log.exists(), "the guard ran the fixture's stand-in")

    def test_agent_arm(self):
        result = run_eval.run_agent(self.ws, "do it", {
            "name": "without_guidance", "timeout": 60,
            "env": {"PATH": self.arm_path}})
        self.assertNotIn("error", result, result)
        self.assertFalse(self.log.exists(), "the arm ran the fixture's stand-in")


if __name__ == "__main__":
    unittest.main()
