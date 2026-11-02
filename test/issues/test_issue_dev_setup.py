"""scripts/dev_setup.sh installs exactly what ci.yml's `test` job installs.

A fresh cloud session could not run the tests because nothing said which pip
packages and fixture npm directories CI installs. scripts/dev_setup.sh lists
them; this module parses .github/workflows/ci.yml with yaml and fails when the
script's pip pins or npm directories drift from the workflow's, so the script
cannot silently go stale. No test runs the script's install path (it needs
the network); only its --print flags and argument handling are exercised.

Git (#535): ci.yml's suite checks Git with the script's own `--check-git`,
so the minimum lives in the script alone, and that minimum must equal the
harness's (run_eval.FLEET_HOOKS_MIN_GIT). `--check-git` and `--build-git`
run against stub `git`, `curl` and `make` first on PATH.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

# Spelled with `.parent`, not `.parents[2]`: run_tests.py's suite-fork scan
# reads `.parent` statically, so `_loop_dirs`' python3 target stays provably
# scripts/scaffold_real_work.py rather than an unknown, possibly the runner.
ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "dev_setup.sh"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
CI_PREFIX = "skills-evals/"


def _test_steps() -> list[dict]:
    doc = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))
    return doc["jobs"]["suite"]["steps"]


def _run_script(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, check=False)


def _stub_path(tmp: Path, **scripts: str) -> dict:
    """The environment with `tmp` first on PATH, holding one executable shell
    script per keyword (`git`, `curl`, `make`): stubs for the host's tools."""
    for name, body in scripts.items():
        stub = tmp / name
        stub.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        stub.chmod(0o755)
    return {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}"}


def _strip_prefix(path: str) -> str:
    return path[len(CI_PREFIX):] if path.startswith(CI_PREFIX) else path


#: How ci.yml's real-work steps read their list: the fixtures' own `deps:`.
DERIVED = re.compile(r'dirs="\$\(python3 \.\./\.\./scripts/scaffold_real_work\.py deps-dirs '
                     r'--manager (npm|bundler)\)"')


def _loop_dirs(run: str) -> list[str] | None:
    """The directories one ci.yml step's `for dir in ...; do` loop installs,
    with a derived `$dirs` list expanded the way the step expands it."""
    loop = re.search(r"for dir in ([^;]+);\s*do", run)
    if not loop:
        return None
    words = loop.group(1).split()
    if words == ["$dirs"]:
        derived = DERIVED.search(run)
        assert derived, "a $dirs loop must read scaffold_real_work.py deps-dirs"
        listed = subprocess.run(["python3", str(ROOT / "scripts" / "scaffold_real_work.py"),
                                 "deps-dirs", "--manager", derived.group(1)],
                                capture_output=True, text=True, check=True).stdout
        return listed.split()
    return words


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
            loop = _loop_dirs(run)
            if loop is not None:
                ci_dirs += [f"{base}/{d}" for d in loop]
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


    def test_bundler_dirs_equal_ci(self):
        ci_dirs: list[str] = []
        for step in _test_steps():
            run = step.get("run")
            if not isinstance(run, str) or "bundle install" not in run:
                continue
            loop = _loop_dirs(run)
            self.assertIsNotNone(loop, run)
            ci_dirs += [f"{step['working-directory']}/{d}" for d in loop]
        ci_dirs = [_strip_prefix(d) for d in ci_dirs]
        self.assertTrue(ci_dirs)
        result = _run_script("--print-bundler-dirs")
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = result.stdout.split("\n")[:-1]
        self.assertEqual(listed, ci_dirs)
        for d in listed:
            self.assertTrue((ROOT / d / "Gemfile.lock").is_file(), d)


    def test_ci_checks_git_with_dev_setup(self):
        # #535: one Git check, scripts/dev_setup.sh's, in the suite job before
        # the tests, gated like every other suite step; the minimum lives in
        # the script alone, so the two cannot drift.
        steps = _test_steps()
        checks = [i for i, s in enumerate(steps)
                  if isinstance(s.get("run"), str) and "--check-git" in s["run"]]
        self.assertEqual(len(checks), 1, checks)
        step = steps[checks[0]]
        self.assertEqual(step["run"].strip(), "bash scripts/dev_setup.sh --check-git")
        self.assertEqual(step["working-directory"], CI_PREFIX.rstrip("/"))
        self.assertEqual(step["if"], "steps.salient.outputs.run == 'true'")
        tests = next(i for i, s in enumerate(steps) if s.get("name") == "Run tests")
        self.assertLess(checks[0], tests)
        self.assertFalse([s for s in steps if isinstance(s.get("run"), str)
                          and re.search(r"\bgit\b.*--version|apt-get[^\n]*\bgit\b",
                                        s["run"])])

    def test_git_minimum_equals_the_harness_minimum(self):
        sys.path.insert(0, str(ROOT / "harness"))
        import run_eval  # noqa: PLC0415
        result = _run_script("--print-git-pin")
        self.assertEqual(result.returncode, 0, result.stderr)
        minimum, pin, sha256 = result.stdout.split("\n")[:-1]
        self.assertEqual(minimum, ".".join(map(str, run_eval.FLEET_HOOKS_MIN_GIT)))
        self.assertTrue(run_eval.git_supports_fleet_hooks(f"git version {pin}"), pin)
        self.assertRegex(pin, r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
        self.assertRegex(sha256, r"\A[0-9a-f]{64}\Z")


class DevSetupGitTests(unittest.TestCase):
    """--check-git and --build-git against stubbed `git`, `curl` and `make`
    on PATH: the host's Git is never changed and nothing is downloaded."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="dev-setup-git-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def check(self, version_line: str, status: int = 0) -> subprocess.CompletedProcess:
        env = _stub_path(self.tmp, git=f"echo '{version_line}'; exit {status}")
        return _run_script("--check-git", env=env)

    def test_check_git_passes_at_or_above_the_minimum(self):
        for line in ("git version 2.54.0", "git version 2.56.0",
                     "git version 2.55.0.windows.1", "git version 3.0.0",
                     "git version 2.540.1"):
            with self.subTest(line=line):
                result = self.check(line)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(line, result.stdout)

    def test_check_git_fails_below_it_with_the_way_out(self):
        for line, status in (("git version 2.43.0", 0), ("git version 2.53.9", 0),
                             ("git version 2.5.0", 0), ("git version 1.99.0", 0),
                             ("not git at all", 0), ("git version 2.56.0", 1)):
            with self.subTest(line=line, status=status):
                result = self.check(line, status)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn("Git 2.54 or later not found", result.stderr)
                self.assertIn("--build-git", result.stderr)

    def test_build_git_refuses_a_tarball_whose_sha256_differs(self):
        marker = self.tmp / "make-ran"
        env = _stub_path(
            self.tmp,
            # Writes a tarball that is not the pinned one wherever -o says.
            curl='while [ "$#" -gt 0 ]; do [ "$1" = -o ] && out="$2"; shift; done; '
                 'printf "not the release" > "$out"',
            make=f"touch '{marker}'")
        result = _run_script("--build-git", str(self.tmp / "prefix"), env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists(), "make ran on an unverified tarball")
        self.assertFalse((self.tmp / "prefix").exists())

    def test_build_git_needs_an_absolute_prefix(self):
        result = _run_script("--build-git", "relative/prefix")
        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute PREFIX", result.stderr)

    def test_build_git_fetches_the_pinned_release_over_https(self):
        text = SCRIPT.read_text(encoding="utf-8")
        pin = _run_script("--print-git-pin").stdout.split("\n")[1]
        self.assertIn('GIT_PIN_URL="https://mirrors.edge.kernel.org/pub/software/scm/git/'
                      'git-${GIT_PIN}.tar.xz"', text)
        self.assertIn(f"GIT_PIN={pin}\n", text)
        self.assertIn("--proto '=https'", text)


class DevSetupScriptTests(unittest.TestCase):
    def test_print_flags_install_nothing(self):
        # Both flags must leave through the print branch: stdout is only the
        # list, stderr is empty (an install would print pip or npm output).
        for flag in ("--print-pins", "--print-npm-dirs", "--print-bundler-dirs",
                     "--print-git-pin"):
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
