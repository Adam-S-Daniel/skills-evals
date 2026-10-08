"""Regression coverage for arm test environment cleanup under pytest.

pytest does not run unittest's module-cleanup queue, so every caller of
``install_arm_test_environment`` must expose cleanup through its module hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "test"
CALLERS = (
    TEST_DIR / "run_tests.py",
    *(TEST_DIR / "issues" / name for name in (
        "test_issue_202_harness.py",
        "test_issue_97.py",
        "test_issue_arm_hardening.py",
        "test_issue_arm_network_sandbox.py",
        "test_issue_cli_json.py",
        "test_issue_guidance_violations.py",
        "test_issue_local_eval.py",
        "test_issue_model_tokens_effort.py",
        "test_issue_permission_mode.py",
        "test_issue_tool_trace.py",
    )),
)
ORIGINAL_PATH = "/opt/hostedtoolcache:/usr/local/sbin:/usr/bin:/bin"


def _exercise_caller(caller: Path) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="arm-env-pytest-") as temp:
        probe = Path(temp)
        caller_source = json.dumps(str(caller))
        (probe / "test_first.py").write_text(
            "import importlib.util\n"
            "import os\n"
            "from pathlib import Path\n"
            f"spec = importlib.util.spec_from_file_location('_arm_env_caller', {caller_source})\n"
            "caller = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(caller)\n"
            "from arm_test_env import TEST_PATH\n"
            "setUpModule = caller.setUpModule\n"
            "tearDownModule = getattr(caller, 'tearDownModule', lambda: None)\n"
            "def test_caller_installed_arm_environment():\n"
            "    assert os.environ['PATH'] == TEST_PATH\n"
            "    mountinfo = Path(os.environ['SKILLS_EVALS_MOUNTINFO'])\n"
            "    assert mountinfo.read_bytes() == b''\n",
            encoding="utf-8",
        )
        (probe / "test_observer.py").write_text(
            "import os\n"
            "def test_original_path_is_restored():\n"
            "    assert os.environ['PATH'] == '/opt/hostedtoolcache:/usr/local/sbin:/usr/bin:/bin'\n"
            "def test_mountinfo_is_removed():\n"
            "    assert 'SKILLS_EVALS_MOUNTINFO' not in os.environ\n",
            encoding="utf-8",
        )
        # Keep the subprocess target a readable script for the suite recursion audit.
        (probe / "pytest_probe.py").write_text(
            "import sys\n"
            "import pytest\n"
            "raise SystemExit(pytest.main(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        child_env = os.environ.copy()
        child_env["PATH"] = ORIGINAL_PATH
        child_env.pop("SKILLS_EVALS_MOUNTINFO", None)
        child_env.pop("PYTEST_ADDOPTS", None)
        child_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        child_env["SKILLS_EVALS_USER_MEMORY"] = str(probe / "scratch-user-memory")
        child_env["PYTHONPATH"] = os.pathsep.join(
            [str(TEST_DIR), child_env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        return subprocess.run(
            [sys.executable, "pytest_probe.py", "-q",
             "test_first.py", "test_observer.py"],
            cwd=probe,
            env=child_env,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )


class ArmTestEnvironmentCleanupTests(unittest.TestCase):
    pass


def _caller_test(caller: Path):
    def test(self: ArmTestEnvironmentCleanupTests) -> None:
        result = _exercise_caller(caller)
        self.assertEqual(
            result.returncode,
            0,
            f"pytest subprocess for {caller.name} failed:\n"
            f"{result.stdout}\n{result.stderr}",
        )

    return test


for _index, _caller in enumerate(CALLERS):
    setattr(
        ArmTestEnvironmentCleanupTests,
        f"test_{_index:02}_{_caller.stem}_restores_environment",
        _caller_test(_caller),
    )
