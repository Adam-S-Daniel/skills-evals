"""scripts/dev_setup.sh installs exactly what ci.yml's `test` job installs.

A fresh cloud session could not run the tests because nothing said which pip
packages and fixture npm directories CI installs. scripts/dev_setup.sh lists
them; this module parses .github/workflows/ci.yml with yaml and fails when the
script's pip pins or npm directories drift from the workflow's, so the script
cannot silently go stale. No test runs the script's install path (it needs
the network); only its --print flags and argument handling are exercised.
"""

from __future__ import annotations

import os
import re
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dev_setup.sh"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
CI_PREFIX = "skills-evals/"


def _test_steps() -> list[dict]:
    doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    return doc["jobs"]["test"]["steps"]


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT,
                          capture_output=True, text=True, check=False)


def _strip_prefix(path: str) -> str:
    return path[len(CI_PREFIX):] if path.startswith(CI_PREFIX) else path


class DevSetupMatchesCiTests(unittest.TestCase):
    def test_pip_pins_equal_ci(self):
        runs = [s["run"].strip() for s in _test_steps()
                if isinstance(s.get("run"), str)
                and s["run"].strip().startswith("pip install ")]
        self.assertEqual(len(runs), 1, runs)
        ci_pins = runs[0].split()[2:]
        result = _run_script("--print-pins")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split("\n")[:-1], ci_pins)

    def test_npm_dirs_equal_ci(self):
        ci_dirs: list[str] = []
        for step in _test_steps():
            run = step.get("run")
            if not isinstance(run, str) or "npm ci" not in run:
                continue
            base = step["working-directory"]
            loop = re.search(r"for dir in ([^;]+);\s*do", run)
            if loop:
                ci_dirs += [f"{base}/{d}" for d in loop.group(1).split()]
            else:
                ci_dirs.append(base)
        ci_dirs = [_strip_prefix(d) for d in ci_dirs]
        self.assertTrue(ci_dirs)
        result = _run_script("--print-npm-dirs")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = result.stdout.split("\n")[:-1]
        self.assertEqual(listed, ci_dirs)
        for d in listed:
            self.assertTrue((ROOT / d).is_dir(), d)
            self.assertTrue((ROOT / d / "package-lock.json").is_file(), d)


class DevSetupScriptTests(unittest.TestCase):
    def test_print_flags_install_nothing(self):
        # Both flags must leave through the print branch: stdout is only the
        # list, stderr is empty (an install would print pip or npm output).
        for flag in ("--print-pins", "--print-npm-dirs"):
            with self.subTest(flag=flag):
                result = _run_script(flag)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                lines = result.stdout.split("\n")[:-1]
                self.assertTrue(lines)
                self.assertNotIn("dev_setup: done.", lines)
                self.assertTrue(all(l and " " not in l for l in lines), lines)

    def test_unknown_argument_exits_2(self):
        result = _run_script("--nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_script_is_executable_and_strict(self):
        self.assertTrue(os.stat(SCRIPT).st_mode & 0o100)
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(text.splitlines()[0], "#!/usr/bin/env bash")
        self.assertIn("set -euo pipefail", text)


if __name__ == "__main__":
    unittest.main()
