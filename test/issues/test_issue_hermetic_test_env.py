"""The test environment's own guarantees (test/conftest.py, test/prereqs.py).

A test's Git reads no host config, so commit signing or hook wiring in a
developer's or cloud container's global config cannot change the commits a
test makes. A missing host prerequisite is a named skip outside CI and a
failure inside it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prereqs  # noqa: E402


class HermeticGitTests(unittest.TestCase):
    def test_git_reads_only_the_suites_global_config(self):
        self.assertEqual(os.environ.get("GIT_CONFIG_NOSYSTEM"), "1")
        config = os.environ.get("GIT_CONFIG_GLOBAL", "")
        self.assertTrue(Path(config).name == "gitconfig" and "skills-evals-gitconfig-" in config, config)
        listed = subprocess.run(["git", "config", "--global", "--list"], capture_output=True,
                                text=True, check=True).stdout.splitlines()
        self.assertEqual(sorted(listed), ["user.email=test@example.com",
                                          "user.name=skills-evals test"])

    def test_no_repository_steering_variable_is_inherited(self):
        # conftest's own env config (maintenance.auto, gc.auto) is the one
        # GIT_CONFIG_KEY/VALUE pair set allowed; nothing else may steer git.
        own = {"GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_COUNT"}
        count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
        pairs = {os.environ[f"GIT_CONFIG_KEY_{i}"]: os.environ[f"GIT_CONFIG_VALUE_{i}"]
                 for i in range(count)}
        self.assertEqual(pairs, {"maintenance.auto": "false", "gc.auto": "0"})
        own |= {f"GIT_CONFIG_{kind}_{i}" for kind in ("KEY", "VALUE") for i in range(count)}
        self.assertEqual([k for k in os.environ if k.startswith("GIT_") and k not in own], [])

    def test_a_commit_needs_no_host_identity_or_signing(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            Path(tmp, "f").write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "add", "f"], check=True)
            subprocess.run(["git", "-C", tmp, "commit", "-qm", "c"], check=True)
            author = subprocess.run(["git", "-C", tmp, "log", "-1", "--format=%ae"],
                                    capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(author, "test@example.com")


class PrerequisiteTests(unittest.TestCase):
    def test_present_does_nothing(self):
        prereqs.require_prerequisite(True, "anything")

    def test_missing_skips_outside_ci_naming_the_setup_command(self):
        with mock.patch.dict(os.environ, {"CI": ""}):
            with self.assertRaises(unittest.SkipTest) as caught:
                prereqs.require_prerequisite(False, "the widget", "make widget")
        self.assertIn("the widget", str(caught.exception))
        self.assertIn("`make widget`", str(caught.exception))

    def test_missing_fails_in_ci(self):
        with mock.patch.dict(os.environ, {"CI": "true"}):
            with self.assertRaises(AssertionError) as caught:
                prereqs.require_prerequisite(False, "the widget")
        self.assertIn(prereqs.DEV_SETUP, str(caught.exception))

    def test_require_executable_reads_path(self):
        with mock.patch.dict(os.environ, {"CI": "", "PATH": "/nonexistent"}):
            with self.assertRaises(unittest.SkipTest):
                prereqs.require_executable("git")


if __name__ == "__main__":
    unittest.main()
