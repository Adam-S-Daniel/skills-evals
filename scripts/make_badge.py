#!/usr/bin/env python3
"""Generate a shields.io endpoint-format JSON badge from the newest run summary.

Reads the newest run under `<results-dir>/<skill>/` (run dirs are UTC
timestamps, so lexicographic max == newest), compares the with_skill and
without_skill arms on their objective-check pass counts and judge overall
scores, and writes `badges/<skill>.json` for shields.io's endpoint badge:

    https://img.shields.io/endpoint?url=<raw URL of badges/<skill>.json>

Color semantics (objective checks are the primary signal; the judge can
only demote, never promote):
  green      — with_skill strictly better on objective checks, and not
               worse on judge overall
  yellow     — objective tied (regardless of judge advantage — a judge
               delta never produces green), or mixed signals (objective
               better but judge worse)
  red        — with_skill worse on objective checks, or objective tied
               with a worse judge overall
  lightgrey  — data missing (no runs yet, an arm errored, or a summary is
               absent/unreadable/malformed)

The message always carries the run's date (from the run directory's
timestamp, NOT the wall clock) so a stale badge is self-evident. Output is
deterministic for the same inputs. Stdlib only.

Usage:
    python3 scripts/make_badge.py pin-actions-to-sha
    python3 scripts/make_badge.py <skill> [--results-dir results] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def newest_run(results_dir: Path, skill: str) -> Path | None:
    """The lexicographically-last run dir under results/<skill>/, or None."""
    skill_dir = results_dir / skill
    if not skill_dir.is_dir():
        return None
    runs = sorted(d for d in skill_dir.iterdir() if d.is_dir())
    return runs[-1] if runs else None


def run_date(run_dir: Path) -> str:
    """YYYY-MM-DD from a %Y%m%dT%H%M%SZ run-dir name; the raw name otherwise."""
    name = run_dir.name
    if len(name) >= 8 and name[:8].isdigit():
        return f"{name[:4]}-{name[4:6]}-{name[6:8]}"
    return name


def arm_stats(run_dir: Path, arm: str) -> dict | None:
    """{"passed", "total", "judge"} for an arm, or None if missing/errored.

    Defensive against malformed summaries (non-dict payloads, non-list
    objective_checks, non-dict check entries or judge): anything that isn't
    the expected shape reads as missing data — the badge goes lightgrey
    rather than the job crashing.
    """
    summary_path = run_dir / arm / "summary.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(summary, dict) or summary.get("error"):
        return None
    checks = summary.get("objective_checks")
    if not isinstance(checks, list) or not checks:
        return None
    judge = summary.get("judge")
    overall = judge.get("overall") if isinstance(judge, dict) else None
    return {
        "passed": sum(1 for c in checks
                      if isinstance(c, dict) and c.get("passed")),
        "total": len(checks),
        "judge": overall if isinstance(overall, (int, float)) else None,
    }


def _cmp(a: float, b: float) -> int:
    return (a > b) - (a < b)


def compare_arms(with_stats: dict, without_stats: dict) -> str:
    """green/yellow/red per the with-vs-without comparison.

    Objective checks are primary; the judge can only demote. Green requires
    with_skill strictly better on objective checks — on an objective tie a
    judge advantage never promotes to green (it caps at yellow), while a
    judge disadvantage demotes (tie -> red, objective-better -> yellow).
    """
    objective = _cmp(with_stats["passed"] / with_stats["total"],
                     without_stats["passed"] / without_stats["total"])
    judge = None
    if with_stats["judge"] is not None and without_stats["judge"] is not None:
        judge = _cmp(with_stats["judge"], without_stats["judge"])

    if objective < 0:
        return "red"
    if objective == 0:
        return "red" if judge == -1 else "yellow"
    return "yellow" if judge == -1 else "green"  # objective strictly better


def build_badge(results_dir: Path, skill: str) -> dict:
    label = f"skill eval: {skill}"
    run_dir = newest_run(results_dir, skill)
    if run_dir is None:
        return {"schemaVersion": 1, "label": label,
                "message": "no runs yet", "color": "lightgrey"}

    date = run_date(run_dir)
    with_stats = arm_stats(run_dir, "with_skill")
    without_stats = arm_stats(run_dir, "without_skill")
    if with_stats is None or without_stats is None:
        return {"schemaVersion": 1, "label": label,
                "message": f"no data · {date}", "color": "lightgrey"}

    message = (f"with {with_stats['passed']}/{with_stats['total']} vs "
               f"without {without_stats['passed']}/{without_stats['total']} "
               f"· {date}")
    return {"schemaVersion": 1, "label": label, "message": message,
            "color": compare_arms(with_stats, without_stats)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", help="skill name, e.g. pin-actions-to-sha")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root of committed run summaries (default: results)")
    parser.add_argument("--out", type=Path, default=None,
                        help="output path (default: badges/<skill>.json)")
    args = parser.parse_args()

    badge = build_badge(args.results_dir, args.skill)
    out = args.out or Path("badges") / f"{args.skill}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(badge, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"{out}: {badge['message']} ({badge['color']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
