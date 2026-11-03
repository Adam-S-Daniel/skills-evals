"""scripts/install_claude_code.sh retries a bad Claude Code install.

Run 41670633700 installed Claude Code and `claude --version` printed "Error:
claude native binary not installed." These tests run the real script with a
fake `npm`, a fake `claude`, a fake `sleep` and a fake clock first on PATH:
no network, no real sleep, no wall clock. The fake sleep records its argument
and advances the fake clock by it; the fake npm advances the clock by
FAKE_INSTALL_SECONDS per call.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "install_claude_code.sh"
BAD = "Error: claude native binary not installed."


@unittest.skipUnless(shutil.which("bash") and shutil.which("timeout")
                     and shutil.which("cat") and shutil.which("chmod")
                     and shutil.which("mktemp") and shutil.which("rm"),
                     "needs bash and coreutils")
class InstallClaudeCodeTests(unittest.TestCase):

    def run_script(self, latest="2.1.290", *, bad_attempts=0, bad_version=None,
                   install_seconds=0, arg=None, noisy=False):
        """Run the script. The first `bad_attempts` npm installs leave a broken
        `claude` (BAD, exit 1) or, when `bad_version` is set, one that reports
        that version; later installs leave a good one."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        fakes, tools = tmp / "fakes", tmp / "tools"
        fakes.mkdir()
        tools.mkdir()
        for tool in ("timeout", "cat", "chmod", "mktemp", "rm"):
            (tools / tool).symlink_to(shutil.which(tool))
        clock, count = tmp / "clock", tmp / "count"
        npm_log, sleep_log = tmp / "npm.log", tmp / "sleep.log"
        clock.write_text("1000\n")
        count.write_text("0\n")

        def tool(path, body):
            path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
            path.chmod(0o755)

        q = lambda p: shlex.quote(str(p))  # noqa: E731
        bad_body = (f"echo {shlex.quote(bad_version + ' (Claude Code)')}\n"
                    if bad_version else f"echo {shlex.quote(BAD)}\nexit 1\n")
        tool(tmp / "claude.bad", bad_body)
        tool(tmp / "claude.good", ("echo 'update available' >&2\n" if noisy else "")
             + f"echo '{latest} (Claude Code)'\n")
        tool(fakes / "npm", (
            f'echo "$*" >> {q(npm_log)}\n'
            f'n=$(( $(<{q(count)}) + 1 )); echo $n > {q(count)}\n'
            f'echo $(( $(<{q(clock)}) + {install_seconds} )) > {q(clock)}\n'
            f'if [ $n -le {bad_attempts} ]; then src={q(tmp / "claude.bad")}; '
            f'else src={q(tmp / "claude.good")}; fi\n'
            f'while IFS= read -r l; do printf "%s\\n" "$l"; done < "$src" '
            f'> {q(fakes / "claude")}\n'
            f'chmod 755 {q(fakes / "claude")}\n'))
        tool(fakes / "fake-sleep", (
            f'echo "$1" >> {q(sleep_log)}\n'
            f'echo $(( $(<{q(clock)}) + $1 )) > {q(clock)}\n'))
        env = {"PATH": os.pathsep.join(str(d) for d in (fakes, tools)),
               "SLEEP_CMD": str(fakes / "fake-sleep"),
               "NOW_CMD": f"cat {clock}"}
        done = subprocess.run(
            [shutil.which("bash"), str(SCRIPT)] + ([latest] if arg is None else arg),
            capture_output=True, text=True, timeout=60, env=env)
        read = lambda p: p.read_text().splitlines() if p.is_file() else []  # noqa: E731
        return done, read(npm_log), read(sleep_log)

    def test_success_on_the_first_try(self):
        done, npm, sleeps = self.run_script()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(npm, ["install -g @anthropic-ai/claude-code@2.1.290"])
        self.assertEqual(sleeps, [])
        self.assertEqual(done.stdout.strip().splitlines(),
                         ["Claude Code 2.1.290 installed and verified on "
                          "attempt 1 (0s)"])

    def test_stderr_noise_does_not_hide_the_version(self):
        done, npm, _ = self.run_script(noisy=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(len(npm), 1)

    def test_success_on_the_third_try_records_the_sleeps(self):
        done, npm, sleeps = self.run_script(bad_attempts=2)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(sleeps, ["5", "10"])
        pkg = "@anthropic-ai/claude-code@2.1.290"
        # The first attempt is a plain install; every later one adds --force.
        self.assertEqual(npm, [f"install -g {pkg}", f"install -g --force {pkg}",
                               f"install -g --force {pkg}"])
        self.assertIn("installed and verified on attempt 3 (15s)", done.stdout)
        self.assertIn(f"attempt 1 failed ({BAD}); retrying in 5s", done.stdout)

    def test_gives_up_before_an_attempt_that_would_cross_the_limit(self):
        # Each install takes 30 s: attempts end at 30, 65, 105, 155 s. After
        # the 4th, a 40 s delay would start the 5th at 195 s, past the 180 s
        # limit, so the script stops there.
        done, npm, sleeps = self.run_script(bad_attempts=99, install_seconds=30)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(sleeps, ["5", "10", "20"])
        self.assertEqual(len(npm), 4)
        self.assertEqual(
            [ln for ln in done.stdout.splitlines() if ln.startswith("::error::")],
            ["::error::Claude Code 2.1.290 did not install a working claude "
             f"after 4 attempts in 155 seconds (last error: {BAD})"])

    def test_every_planned_delay_is_used_when_there_is_time(self):
        done, npm, sleeps = self.run_script(bad_attempts=99)
        self.assertEqual(done.returncode, 1)
        self.assertEqual(sleeps, ["5", "10", "20", "40", "80"])
        self.assertEqual(len(npm), 6)
        self.assertIn("after 6 attempts in 155 seconds", done.stdout)

    def test_a_version_mismatch_is_a_failure_and_is_retried(self):
        done, npm, sleeps = self.run_script(bad_attempts=99,
                                            bad_version="2.1.289")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(len(npm), 6)
        self.assertEqual(sleeps, ["5", "10", "20", "40", "80"])
        self.assertIn("(last error: claude --version reported "
                      "'2.1.289 (Claude Code)', expected 2.1.290)", done.stdout)
        self.assertNotIn("installed and verified", done.stdout)

    def test_a_failing_npm_install_is_retried_with_its_first_error_line(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "npm").write_text("#!/bin/bash\nprintf 'E503 busy\\nextra line\\n' >&2\n"
                                 "exit 1\n")
        (tmp / "npm").chmod(0o755)
        for t in ("timeout", "mktemp", "rm"):
            (tmp / t).symlink_to(shutil.which(t))
        env = {"PATH": str(tmp), "SLEEP_CMD": "true", "NOW_CMD": "echo 0"}
        done = subprocess.run([shutil.which("bash"), str(SCRIPT), "2.1.290"],
                              capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(done.returncode, 1)
        self.assertIn("(last error: E503 busy)", done.stdout)
        self.assertNotIn("extra line", done.stdout)

    def test_a_version_that_is_not_plain_is_refused_without_installing(self):
        for bad in ("2.2.0-beta.1", "latest", ""):
            done, npm, _ = self.run_script(arg=[bad])
            self.assertEqual(done.returncode, 2, bad)
            self.assertEqual(npm, [])


class CallersTests(unittest.TestCase):
    """Each workflow step calls the script, from its own checkout."""

    def steps(self):
        for name, job in (("eval.yml", "eval"), ("eval.yml", "roster"),
                          ("propagation.yml", "arms")):
            doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / name)
                                 .read_text(encoding="utf-8"))
            yield name, doc["jobs"][job]["steps"]

    def test_every_install_step_runs_the_script_after_a_skills_evals_checkout(self):
        call = ('bash "$GITHUB_WORKSPACE/skills-evals/scripts/'
                'install_claude_code.sh" "$latest"')
        for name, steps in self.steps():
            at = next(i for i, s in enumerate(steps)
                      if s.get("name") == "Install Claude Code CLI")
            self.assertIn(call, steps[at]["run"].splitlines(), name)
            self.assertTrue(any(s.get("uses", "").startswith("actions/checkout")
                                and (s.get("with") or {}).get("path") == "skills-evals"
                                for s in steps[:at]), name)
