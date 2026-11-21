"""Declared host prerequisites for tests that cannot run without one.

A test that needs something this repository does not carry (a fixture's
installed npm or gem directory, a tool on PATH) declares it with
`require_prerequisite`, naming the command that provides it. Where the thing
is missing the test is skipped with that command as the reason, so a fresh or
cloud session shows one named skip instead of a pile of failures it then has
to tell apart from real ones by diffing against `main`.

In CI (`CI=true`, which GitHub Actions sets) a missing prerequisite FAILS
instead: ci.yml's `test` job installs everything (scripts/dev_setup.sh mirrors
it), so a skip there would hide a broken install step rather than a host gap.
"""

from __future__ import annotations

import os
import shutil
import unittest

DEV_SETUP = "bash scripts/dev_setup.sh"


def in_ci() -> bool:
    return os.environ.get("CI", "").lower() == "true"


def require_prerequisite(present: bool, missing: str, setup: str = DEV_SETUP) -> None:
    """Skip the calling test (fail it in CI) unless `present`.

    `missing` says what is absent; `setup` is the command that provides it."""
    if present:
        return
    message = f"prerequisite missing: {missing}. Provide it with `{setup}`"
    if in_ci():
        raise AssertionError(f"{message} (CI installs it, so this is a broken install step)")
    raise unittest.SkipTest(message)


def require_executable(name: str, setup: str = DEV_SETUP) -> None:
    require_prerequisite(shutil.which(name) is not None, f"`{name}` is not on PATH", setup)
