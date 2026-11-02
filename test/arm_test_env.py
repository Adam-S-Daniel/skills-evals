"""Host-independent PATH and mount metadata for arm-running tests, and the
agent CLI spawn routed through a faked `subprocess.run`."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import unittest
from collections.abc import Callable
from functools import wraps
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


def install_arm_test_environment(setup: Callable[[], None]) -> Callable[[], None]:
    """Wrap module setup, restoring its environment if setup raises or skips.

    Tests measuring particular aliases or toolchains install their own
    mount metadata or PATH inside this scope. Callers must expose
    ``tearDownModule`` calling ``unittest.doModuleCleanups()``: pytest runs
    module teardown hooks but does not run unittest's module-cleanup queue.
    Neither runner calls module teardown after failed setup; roll back
    immediately in that case, including ``SkipTest`` and other BaseExceptions.
    """
    @wraps(setup)
    def wrapped_setup() -> None:
        patcher = mock.patch.dict(os.environ, arm_test_environment())
        patcher.start()
        unittest.addModuleCleanup(patcher.stop)
        try:
            setup()
        except BaseException:
            # stop() is idempotent when unittest later drains module cleanups.
            patcher.stop()
            raise

    return wrapped_setup


def route_cli_through_subprocess_run(case: unittest.TestCase, run_eval) -> None:
    """For `case`'s tests, which fake `subprocess.run` as the agent CLI.

    `run_eval.run_agent` starts the CLI through `_run_in_own_session` (its own
    session, its process group ended afterwards, #594), which takes the same
    arguments as `subprocess.run`. Each call is handed to whatever
    `subprocess.run` is when it is made, so no process is started in a
    session and no group is signaled. The session and group handling has
    its own tests in test/issues/test_issue_594_late_writer.py.
    """
    def forward(cmd, **kwargs):
        return run_eval.subprocess.run(cmd, **kwargs)

    patcher = mock.patch.object(run_eval, "_run_in_own_session", forward)
    patcher.start()
    case.addCleanup(patcher.stop)
