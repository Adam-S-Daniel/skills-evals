#!/usr/bin/env python3
"""Tier-3 account-store audit: what claude.ai actually serves, vs the registry.

Runs on a surface with a signed-in account (a scheduled cloud session — see
`evals/propagation/ROUTINE.md`), reads `~/.claude/skills/synced/` and a
registry checkout, and publishes a JSON result. It spawns no CLI, calls no API
and spends nothing; the only thing it needs that CI has not got is the account
store itself.

The result is not for this run's reader — it is for the NEXT pull request. The
credential-free Tier-2 gate (`run_propagation.py`) reads it and reds the pull
request when it is missing, stale or failing, which is what makes a scheduled
probe that silently stops firing impossible to ignore.

Usage:
    python3 harness/run_account_audit.py --registry ~/repos/agentskills
    python3 harness/run_account_audit.py --registry ../agentskills \\
        --out results/propagation/account --badge badges/account-store.json

Exit codes: 0 in sync; 1 drift found; 2 the audit could not run (no account
store on this surface, or no registry checkout) — never reported as in-sync.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from propagation import account_store  # noqa: E402

EXIT_OK, EXIT_DRIFT, EXIT_FAULT = 0, 1, 2


def registry_ref(registry: Path) -> str:
    try:
        proc = subprocess.run(  # noqa: S603 — argv list, no shell
            ["git", "-C", str(registry), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def resolve_registry(cli_value: Path | None) -> Path:
    """--registry, $AGENTSKILLS_DIR, ~/repos — ABSOLUTE on every branch.

    Same class as run_propagation's copy, different mechanism: `git_tracked`
    runs `git -C <registry> ls-files -- <skill dir>`, so the child reads that
    pathspec inside the REGISTRY. A relative one lands outside it (measured:
    rc=128, `is outside repository`), git_tracked returns None, and the audit
    silently falls back to a raw filesystem walk — which counts git-ignored
    working-tree files as payload the account copy is missing. Measured on one
    fixture: the same tree audits PASS absolute and FAIL relative. A relative
    `--registry` is a legitimate thing for a caller to pass, so resolving it
    here is what keeps it safe; ROUTINE.md passes absolute on top of that, so a
    regression in this function cannot silently fabricate a finding there.
    """
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env = os.environ.get("AGENTSKILLS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "repos" / "agentskills").resolve()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=None,
                        help="agentskills checkout: this, else $AGENTSKILLS_DIR, "
                             "else ~/repos/agentskills")
    parser.add_argument("--home", type=Path, default=None,
                        help="surface whose account store to read (default $HOME)")
    parser.add_argument("--out", type=Path, default=None,
                        help="directory to write summary.json + latest.json into")
    parser.add_argument("--badge", type=Path, default=None,
                        help="also write a shields.io endpoint badge here")
    parser.add_argument("--now", default=None,
                        help="ISO-8601 instant to stamp the result with; tests "
                             "pass it so the output is deterministic")
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser() if args.home else Path.home()
    registry = resolve_registry(args.registry)
    now = (account_store.parse_iso8601(args.now) if args.now
           else datetime.now(timezone.utc))

    try:
        result = account_store.audit(home, registry)
    except account_store.AuditError as exc:
        # Never a clean exit 0: "could not look" and "looked and found nothing
        # wrong" are different claims, and only one of them should let a
        # freshness gate go green downstream.
        print(f"INCONCLUSIVE account-audit: {exc}")
        return EXIT_FAULT

    summary = account_store.summarise(
        result, generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        registry_ref=registry_ref(registry))

    for finding in summary["findings"]:
        print(f"FAIL {finding['skill']} [{finding['kind']}]: {finding['detail']}")
    print(f"{summary['status'].upper()} account-audit: "
          f"{len(summary['checked'])} registry-owned skill(s) checked, "
          f"{len(summary['skipped'])} not owned here, "
          f"{len(summary['findings'])} finding(s)")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        (args.out / f"{stamp}.json").write_text(payload, encoding="utf-8")
        (args.out / "latest.json").write_text(payload, encoding="utf-8")
    if args.badge:
        args.badge.parent.mkdir(parents=True, exist_ok=True)
        args.badge.write_text(
            json.dumps(account_store.badge(summary), indent=2, sort_keys=True) + "\n",
            encoding="utf-8")

    return EXIT_OK if summary["status"] == "pass" else EXIT_DRIFT


if __name__ == "__main__":
    raise SystemExit(main())
