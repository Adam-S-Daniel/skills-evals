"""Host-independent PATH and mount metadata for arm-running tests."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_PATH = os.pathsep.join([str(Path.home() / ".local" / "bin"),
                             "/usr/local/bin", "/usr/bin", "/bin"])
MOUNTINFO_ENV = "SKILLS_EVALS_MOUNTINFO"
_mountinfo: Path | None = None


def arm_test_environment() -> dict[str, str]:
    """Explicit Linux tools and an empty, process-owned mountinfo fixture.

    Used locally by install helpers too, so a deliberately poisoned parent
    environment cannot override a fixture installed at the module boundary.
    """
    global _mountinfo
    if _mountinfo is None:
        directory = Path(tempfile.mkdtemp(prefix="arm-test-env-"))
        atexit.register(shutil.rmtree, directory, ignore_errors=True)
        _mountinfo = directory / "mountinfo"
        _mountinfo.write_bytes(b"")
    return {"PATH": TEST_PATH, MOUNTINFO_ENV: str(_mountinfo)}


def install_arm_test_environment() -> None:
    """A unittest module fixture; restore the caller's environment afterward.

    Tests measuring particular aliases or toolchains install their own
    mount metadata or PATH inside this scope.
    """
    patcher = mock.patch.dict(os.environ, arm_test_environment())
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)
