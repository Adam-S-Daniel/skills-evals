#!/usr/bin/env python3
"""Generate a shields.io endpoint-format JSON badge from a window of run summaries.

Reads the `--window` newest runs under `<results-dir>/<skill>/` (run dirs are
UTC timestamps, so lexicographic order == chronological), averages the
with_skill and without_skill arms over them on objective-check pass counts and
judge overall scores, and writes `badges/<skill>.json` for shields.io's
endpoint badge:

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

A single run is scheduling luck, not a measurement: the arms have been
observed several checks apart from one run to the next, so a badge built from
one run reports noise. The window averages that out. Runs where either arm is
missing or errored are dropped from the window rather than blanking the badge,
so one bad night does not erase a week of signal; a window with no usable run
at all still goes lightgrey.

The message carries the sample size (`n=N`) whenever more than one run was
averaged — at n=1 there is no average and the marker is omitted, which is
exactly the pre-window message. Means print as integers when integral (`7/7`,
never `7.0/7`) and to one decimal otherwise.

The message always carries a run's date (from the run directory's timestamp,
NOT the wall clock) so a stale badge is self-evident: the newest run that
contributed to the aggregate, or — when nothing was usable — the newest run
directory found. Output is deterministic for the same inputs. Stdlib only.

Usage:
    python3 scripts/make_badge.py workflow-path-audit
    python3 scripts/make_badge.py <skill> [--results-dir results] [--out PATH]
                                          [--window N]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Runs are weekly-ish, so five is roughly a month of signal: long enough to
# average out the run-to-run spread, short enough that a real regression shows
# up within a couple of runs instead of being buried by history.
DEFAULT_WINDOW = 5


def runs_newest_first(results_dir: Path, skill: str) -> list[Path]:
    """Run dirs under results/<skill>/, newest first.

    Run dirs are UTC timestamps (%Y%m%dT%H%M%SZ), so reverse-lexicographic
    order is reverse-chronological order — no stat() calls, no wall clock.
    """
    skill_dir = results_dir / skill
    if not skill_dir.is_dir():
        return []
    return sorted((d for d in skill_dir.iterdir() if d.is_dir()), reverse=True)


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


def usable_runs(results_dir: Path, skill: str,
                window: int) -> list[tuple[Path, dict, dict]]:
    """(run_dir, with_stats, without_stats) for the usable runs in the window.

    The window is the `window` NEWEST run dirs; runs where either arm is
    missing or errored are then dropped. Deliberately not "scan back until you
    find `window` good runs": the window names a time span, so a bad night
    shrinks the sample rather than silently pulling in an older run. Newest
    first.
    """
    out = []
    for run_dir in runs_newest_first(results_dir, skill)[:max(1, window)]:
        with_stats = arm_stats(run_dir, "with_skill")
        without_stats = arm_stats(run_dir, "without_skill")
        if with_stats is None or without_stats is None:
            continue
        out.append((run_dir, with_stats, without_stats))
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def aggregate(stats: list[dict]) -> dict:
    """Mean {"passed", "total", "judge"} over one arm's per-run stats.

    `total` is averaged too rather than assumed constant: a fixture that gains
    a check mid-window would otherwise print a pass count against a
    denominator no run actually had. `judge` averages only the runs that
    carried a numeric judge overall, and is None when none did.
    """
    judges = [s["judge"] for s in stats if s["judge"] is not None]
    return {
        "passed": _mean([s["passed"] for s in stats]),
        "total": _mean([s["total"] for s in stats]),
        "judge": _mean(judges) if judges else None,
    }


def _fmt_mean(value: float) -> str:
    """One decimal, but an integral mean prints as an integer (`7`, not `7.0`)."""
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"


def build_badge(results_dir: Path, skill: str,
                window: int = DEFAULT_WINDOW) -> dict:
    label = f"skill eval: {skill}"
    runs = runs_newest_first(results_dir, skill)
    if not runs:
        return {"schemaVersion": 1, "label": label,
                "message": "no runs yet", "color": "lightgrey"}

    usable = usable_runs(results_dir, skill, window)
    if not usable:
        # Nothing in the window was scorable; date the badge from the newest
        # run dir so the reader still sees how stale the attempt is.
        return {"schemaVersion": 1, "label": label,
                "message": f"no data · {run_date(runs[0])}", "color": "lightgrey"}

    with_agg = aggregate([w for _, w, _ in usable])
    without_agg = aggregate([wo for _, _, wo in usable])
    # Newest CONTRIBUTING run, not newest run dir: the date must belong to the
    # data being reported.
    date = run_date(usable[0][0])
    # n=1 is not an average, and omitting the marker there keeps the
    # single-run message byte-identical to the pre-window badge.
    sample = f"n={len(usable)} · " if len(usable) > 1 else ""

    message = (f"with {_fmt_mean(with_agg['passed'])}/{_fmt_mean(with_agg['total'])} vs "
               f"without {_fmt_mean(without_agg['passed'])}/{_fmt_mean(without_agg['total'])} "
               f"· {sample}{date}")
    return {"schemaVersion": 1, "label": label, "message": message,
            "color": compare_arms(with_agg, without_agg)}


def _positive_int(value: str) -> int:
    """argparse type: reject `--window 0` loudly instead of silently clamping."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {value}")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", help="skill name, e.g. workflow-path-audit")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root of committed run summaries (default: results)")
    parser.add_argument("--out", type=Path, default=None,
                        help="output path (default: badges/<skill>.json)")
    parser.add_argument("--window", type=_positive_int, default=DEFAULT_WINDOW,
                        help=f"average over the N newest runs "
                             f"(default: {DEFAULT_WINDOW}; 1 = newest run only)")
    args = parser.parse_args()

    badge = build_badge(args.results_dir, args.skill, args.window)
    out = args.out or Path("badges") / f"{args.skill}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(badge, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"{out}: {badge['message']} ({badge['color']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
