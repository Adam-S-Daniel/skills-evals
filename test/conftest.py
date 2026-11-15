"""pytest hooks for `run_tests.py --jobs N --shard K/N` (ci.yml's matrix).

Loaded by every pytest-xdist worker, which is where collection happens, so
the shard filter has to live here: a plugin object passed to `pytest.main`
in the controller never reaches the workers. Without the option this file
does nothing, so `python3 -m pytest test/issues/<file>.py` is unchanged.
"""

from __future__ import annotations

import os

from shard import assign, nodeid_key, parse_shard


# `run_eval.main()` proves the sandbox with a canary CLI call before its first
# arm (#1024). A test's scripted fake CLI counts its calls, so every test
# skips the canary through this TEST-ONLY variable, which child processes the
# tests start inherit when they inherit the environment.
# test_issue_1024_sandbox_probe.py turns it back on where it tests the canary.
os.environ["SKILLS_EVALS_TEST_SKIP_SANDBOX_PROBE"] = "1"


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
