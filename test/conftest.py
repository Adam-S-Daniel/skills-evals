"""pytest hooks for `run_tests.py --jobs N --shard K/N` (ci.yml's matrix).

Loaded by every pytest-xdist worker, which is where collection happens, so
the shard filter has to live here: a plugin object passed to `pytest.main`
in the controller never reaches the workers. Without the option the shard
filter does nothing, so `python3 -m pytest test/issues/<file>.py` is unchanged.
It also makes every test's Git hermetic (`_hermetic_git` below).
"""

from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

from shard import assign, nodeid_key, parse_shard


# `run_eval.main()` proves the sandbox with a canary CLI call before its first
# arm (#1024). A test's scripted fake CLI counts its calls, so every test
# skips the canary through this TEST-ONLY variable, which child processes the
# tests start inherit when they inherit the environment.
# test_issue_1024_sandbox_probe.py turns it back on where it tests the canary.
os.environ["SKILLS_EVALS_TEST_SKIP_SANDBOX_PROBE"] = "1"


def _hermetic_git() -> None:
    """Every `git` a test runs, or a child process of it, reads only the
    config the test writes, never this host's: no system or global file and
    no inherited `GIT_*` variable. A developer's or cloud container's global
    config (commit signing, `init.templateDir`, `includeIf` hook wiring, a
    `GIT_DIR` from a hook the suite runs under) otherwise changed what the
    tests' own commits did, so the same commit failed only on some hosts.
    The global file carries an identity alone, which CI's runner derives from
    its hostname and a bare container cannot."""
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        del os.environ[key]
    home = tempfile.mkdtemp(prefix="skills-evals-gitconfig-")
    atexit.register(shutil.rmtree, home, ignore_errors=True)
    config = os.path.join(home, "gitconfig")
    with open(config, "w", encoding="utf-8") as handle:
        handle.write("[user]\n\tname = skills-evals test\n\temail = test@example.com\n")
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    os.environ["GIT_CONFIG_GLOBAL"] = config
    # `git commit` spawns a detached `git maintenance run --auto`, which can
    # still be touching .git/objects when a test's rmtree walks its throwaway
    # repo (FileNotFoundError in teardown). Env config reaches every git, even
    # one a test starts with GIT_CONFIG_GLOBAL=/dev/null.
    count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    for key, value in (("maintenance.auto", "false"), ("gc.auto", "0")):
        os.environ[f"GIT_CONFIG_KEY_{count}"] = key
        os.environ[f"GIT_CONFIG_VALUE_{count}"] = value
        count += 1
    os.environ["GIT_CONFIG_COUNT"] = str(count)


_hermetic_git()


def pytest_addoption(parser):
    parser.addoption("--skills-evals-shard", default=None, metavar="K/N",
                     help="run only the tests test/shard.py assigns to "
                          "shard K of N (set by run_tests.py --shard)")


def pytest_collection_modifyitems(config, items):
    value = config.getoption("--skills-evals-shard")
    if not value:
        return
    k, n = parse_shard(value)
    shards = assign([nodeid_key(item.nodeid) for item in items], n)
    keep, drop = [], []
    for item in items:
        (keep if shards[nodeid_key(item.nodeid)] == k else drop).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


# The allowance guard reserves the loop's own automatic jobs out of the cap and
# refuses without a fresh `loop_jobs` in spend/weekly.json (allowance_guard.py,
# 2026-11-15). The older tests build a bare results tree, so by default this
# reads the reserve as 0; a test that exercises the reserve itself (marked
# `real_loop_reserve`) gets the real reader.
def pytest_configure(config):
    config.addinivalue_line("markers", "real_loop_reserve: use the guard's real loop reserve reader")


@pytest.fixture(autouse=True)
def _no_loop_reserve_by_default(request, monkeypatch):
    if request.node.get_closest_marker("real_loop_reserve"):
        return
    guard = sys.modules.get("allowance_guard")
    if guard is not None:
        monkeypatch.setattr(guard, "loop_reserve_fraction", lambda tree, now: 0.0)


# The suite needs Git 2.54 or later (scripts/dev_setup.sh's GIT_MIN): tests
# that run real fixtures opting into the fleet hooks get the harness's
# `git_too_old_for_fleet_hooks` refusal on an older Git. Said once at the end
# of a run, beside the failures it explains, so they are not mistaken for
# regressions; CI's suite job checks the same thing up front.
def pytest_terminal_summary(terminalreporter):
    setup = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "scripts", "dev_setup.sh")
    try:
        result = subprocess.run(["bash", setup, "--check-git"], capture_output=True,
                                text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        terminalreporter.write_line(f"skills-evals: could not check the Git version ({type(exc).__name__})")
        return
    if result.returncode != 0:
        terminalreporter.write_sep("=", "host prerequisite missing", yellow=True)
        terminalreporter.write_line(result.stderr.strip())
        terminalreporter.write_line("Tests that fail with `git_too_old_for_fleet_hooks` "
                                    "are this, not a regression.")
