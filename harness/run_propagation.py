#!/usr/bin/env python3
"""Tier-2 propagation probes: does each delivery channel still deliver?

One arm per channel, each spawning the real Claude Code CLI twice (control leg,
then arm leg) and asserting on the difference against `skills.lock`. Unlike
`run_eval.py` and `run_canary.py` this runner reaches NO API and needs NO
credential: it reads the `system/init` event, which the CLI computes locally
before its first request, then kills the child. A full five-arm run costs
$0.00, so this belongs on `pull_request` rather than behind `eval.yml`'s OIDC —
where a branch dispatch would die at token exchange and tell you nothing.

The same run also carries the FRESHNESS GATE: it reads the Tier-3 account
audit's last published result and fails when that result is missing, stale or
unreadable. That is how a scheduled probe that quietly stops firing reaches a
human — the next pull request goes red.

What the gate does NOT do on a pull request is relay the audit's own verdict.
A red Tier-3 result means the ACCOUNT store has drifted; no commit in this repo
caused it and no commit here can clear it, so blocking every pull request on it
only teaches people to ignore the gate while the drift outlives their patience.
It is reported as WARN on a pull request and stays fatal on the schedule, where
`report` files the tracking issue. Liveness is this gate's job; the verdict is
the schedule's. See --account-verdict-advisory.

Usage:
    python3 harness/run_propagation.py evals/propagation
    python3 harness/run_propagation.py evals/propagation --arm bootstrap-hook
    python3 harness/run_propagation.py evals/propagation --gate-only \\
        --account-latest eval-results/propagation/account/latest.json

Exit codes: 0 everything asserted holds; 1 an assertion failed; 2 a probe
fault — the CLI would not start, the stream changed shape, or a guard did not
hold, so neither a pass nor a fail would have meant anything.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from propagation import account_store, arms  # noqa: E402

EXIT_OK, EXIT_FAILED, EXIT_FAULT = 0, 1, 2


def load_fixture(eval_dir: Path) -> dict:
    with open(eval_dir / "fixture.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_registry(cli_value: Path | None) -> Path:
    """Same convention as run_eval.py: --registry, $AGENTSKILLS_DIR, ~/repos.

    ABSOLUTE on every branch, and that is load-bearing rather than tidiness:
    the arms hand registry-derived paths to children they spawn with `cwd` set
    to a scratch workspace — `arms._run_hook` runs `bash <hook>` there — so a
    relative registry is read against a directory that does not contain it.
    Measured in CI, where propagation.yml passes `--registry ../agentskills`:
    both hook-running arms died with rc=127, `bash:
    ../agentskills/.claude/hooks/skills-bootstrap.sh: No such file or
    directory`. It never reproduced locally because every local invocation had
    passed an absolute path — which is exactly how it reached CI.
    """
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env = os.environ.get("AGENTSKILLS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "repos" / "agentskills").resolve()


# The one status that says "the audit ran, on time, and did not like what it
# saw". Every other unhappy status says the audit itself is not reaching us,
# which is the thing this gate exists to detect and is never advisory.
ADVISORY_STATUSES = frozenset({"reported-failure"})


def run_gate(fixture: dict, latest: Path | None, marker: Path | None,
             now: datetime, advisory: frozenset = frozenset()) -> tuple:
    """(ok, rendered) for the freshness gate. Pure: no network, no wall clock
    unless the caller passes one.

    `advisory` names statuses to REPORT without failing. The verdict itself is
    computed identically either way -- `freshness_verdict` states what is true
    and this decides what blocks -- so a downgraded status still prints its full
    message, including which skills drifted. A caller that silently dropped the
    line instead would leave a pull request with no trace of the drift at all.
    """
    summary = None
    if latest and latest.is_file():
        try:
            summary = json.loads(latest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"FAIL freshness-gate: {latest} is unreadable: {exc}"
        if not isinstance(summary, dict):
            return False, (f"FAIL freshness-gate: {latest} is not an object "
                           "(the account audit publishes a JSON object)")
    ok, status, message = account_store.freshness_verdict(
        summary, now=now, max_age_days=int(fixture["account_audit_max_age_days"]),
        bootstrapped=bool(marker and marker.exists()))
    if not ok and status in advisory:
        # WARN, not PASS: the run is green, and the log still says plainly that
        # something is wrong somewhere this pull request cannot reach.
        return True, (f"WARN freshness-gate [{status}]: {message} — advisory "
                      "here because no change in this repo can cause or clear "
                      "it; the scheduled run treats it as a failure and files "
                      "the tracking issue")
    label = "PASS" if ok else "FAIL"
    return ok, f"{label} freshness-gate [{status}]: {message}"


def self_test(ctx: arms.ArmContext) -> tuple:
    """Prove the assertion layer can still fail — against the REAL binary.

    The hermetic mutation suite proves the probe's logic; it cannot prove the
    CLI still emits `init` where this harness looks for it, or that a
    plugin install still produces namespaced names. So one live run of the
    plugin arm goes against a lock carrying a skill the registry does not ship,
    and is REQUIRED to come back FAIL. A green self-test on a real CLI whose
    event shape has moved would otherwise be the whole suite's blind spot: an
    arm that can no longer detect anything reports INCONCLUSIVE at worst and
    PASS at best, and this is what tells them apart.
    """
    mutated = dict(ctx.lock, skills=dict(ctx.lock["skills"],
                                         **{f"{ctx.bundle}/phantom-skill": "0" * 64}))
    # Its OWN scratch root. Sharing the arms' root would let the real run's
    # marketplace install sit in the HOME this leg treats as clean, firing the
    # negative control and returning FAIL for a reason that has nothing to do
    # with the phantom skill — a green self-test that proves nothing.
    root = Path(tempfile.mkdtemp(prefix="propagation-selftest-"))
    try:
        result = arms.run_arm("plugin-marketplace",
                              arms.ArmContext(**dict(vars(ctx), root=root,
                                                     lock=mutated)))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if result.status == arms.FAIL:
        return True, ("PASS self-test: the live plugin arm still fails on a lock "
                      "naming a skill the registry does not ship")
    return False, (f"FAIL self-test: injecting a phantom skill into the lock "
                   f"produced {result.status}, not FAIL — the assertion layer "
                   f"has stopped detecting anything against this CLI\n"
                   + result.render())


def build_context(fixture: dict, registry: Path, root: Path,
                  timeout: int) -> arms.ArmContext:
    lock_path = registry / fixture["lock_path"]
    hook = registry / fixture["hook_path"]
    for path, what in ((registry, "registry checkout"), (lock_path, "skills.lock"),
                       (hook, "bootstrap hook")):
        if not path.exists():
            raise arms.ArmError(
                f"{what} not found at {path} — pass --registry PATH (or set "
                "$AGENTSKILLS_DIR) pointing at an agentskills checkout")
    return arms.ArmContext(
        root=root, registry=registry, lock_path=lock_path,
        lock=arms.load_lock(lock_path), hook=hook,
        bundle=fixture["bundle"], collision_skill=fixture["collision_skill"],
        timeout=timeout)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eval_dir", type=Path)
    parser.add_argument("--arm", action="append", default=None,
                        help="run only this arm (repeatable); default: all")
    parser.add_argument("--registry", type=Path, default=None,
                        help="agentskills checkout: this, else $AGENTSKILLS_DIR, "
                             "else ~/repos/agentskills")
    parser.add_argument("--account-latest", type=Path, default=None,
                        help="the Tier-3 audit's published latest.json, fetched "
                             "from the eval-results branch by the caller")
    parser.add_argument("--account-marker", type=Path, default=None,
                        help="propagation/.bootstrapped from eval-results; its "
                             "absence means the audit has never run yet")
    parser.add_argument("--gate-only", action="store_true",
                        help="run the freshness gate and nothing else (no CLI)")
    parser.add_argument("--no-gate", action="store_true",
                        help="skip the freshness gate (arms only)")
    parser.add_argument("--account-verdict-advisory", action="store_true",
                        help="report a RED account audit without failing — for "
                             "pull requests, which can neither cause nor clear "
                             "it. Liveness failures (missing, stale, "
                             "unreadable) still fail: those mean the audit is "
                             "not reaching us, which is what this gate is for")
    parser.add_argument("--self-test", action="store_true",
                        help="also prove, against the real binary, that the "
                             "plugin arm still FAILS on a deliberately wrong lock")
    parser.add_argument("--now", default=None,
                        help="ISO-8601 instant the freshness gate treats as now; "
                             "tests pass it so they never depend on the clock")
    parser.add_argument("--timeout", type=int, default=120,
                        help="per-CLI-invocation timeout in seconds")
    parser.add_argument("--json", type=Path, default=None,
                        help="also write the machine-readable run record here")
    args = parser.parse_args(argv)

    fixture = load_fixture(args.eval_dir)
    now = (account_store.parse_iso8601(args.now) if args.now
           else datetime.now(timezone.utc))

    gate_ok, gate_line = True, None
    if not args.no_gate:
        gate_ok, gate_line = run_gate(
            fixture, args.account_latest, args.account_marker, now,
            advisory=(ADVISORY_STATUSES if args.account_verdict_advisory
                      else frozenset()))

    results = []
    self_test_line = None
    self_test_ok = True
    fault = False
    if not args.gate_only:
        names = args.arm or list(fixture["arms"])
        unknown = [name for name in names if name not in arms.ARMS]
        if unknown:
            print(f"unknown arm(s): {unknown}; known: {sorted(arms.ARMS)}")
            return EXIT_FAULT
        root = Path(tempfile.mkdtemp(prefix="propagation-"))
        try:
            ctx = build_context(fixture, resolve_registry(args.registry), root,
                                args.timeout)
            for name in names:
                results.append(arms.run_arm(name, ctx))
            if args.self_test:
                self_test_ok, self_test_line = self_test(ctx)
        except arms.ArmError as exc:
            print(f"{arms.INCONCLUSIVE} setup: {exc}")
            fault = True
        finally:
            shutil.rmtree(root, ignore_errors=True)

    for result in results:
        print(result.render())
    if self_test_line:
        print(self_test_line)
    if gate_line:
        print(gate_line)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "schema": 1,
            "probe": "propagation/tier2",
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "arms": [r.to_dict() for r in results],
            "freshness_gate": {"ok": gate_ok, "detail": gate_line},
            "self_test": {"ok": self_test_ok, "detail": self_test_line},
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if fault or any(r.status == arms.INCONCLUSIVE for r in results):
        return EXIT_FAULT
    if not gate_ok or not self_test_ok or any(r.status == arms.FAIL for r in results):
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
