#!/usr/bin/env python3
"""Count which Claude models this account actually used, per ISO week.

*** THE OUTPUT OF THIS SCRIPT IS PUBLISHED PUBLICLY. ***

It is committed to the `eval-results` branch of a PUBLIC repository as
`usage/latest.json`, exactly the way the Tier-3 account-store Routine
publishes its audit (see `evals/propagation/ROUTINE.md`). Treat every byte it
emits as world-readable, forever.

That is why the output is `{model_id: {iso_week: count}}` and NOTHING else. It
carries no project names, no directory names, no filesystem paths, no prompt
or reply text, no session ids, no timestamps finer than an ISO week. The
transcripts it reads are full of all of those — `~/.claude/projects/` encodes
the project path in the directory name alone — so the narrowness here is the
whole safety property, not tidiness.
`test/run_tests.py::TestIssue67::test_census_emits_only_model_week_counts_and_leaks_nothing`
is the guard on that, and it stays.

Runs on a durable machine (the transcripts are local, and a CI runner has
none). Weekly buckets, not daily: a daily series over one account is a
timeline of when a person was at their desk, and the roster policy only ever
asks about 4- and 8-week windows anyway.

Usage:
    python3 scripts/model_usage_census.py --out usage/latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_PROJECTS = Path.home() / ".claude" / "projects"
DEFAULT_WEEKS = 8


def iso_week(moment: datetime) -> str:
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"


def window_weeks(now: datetime, weeks: int) -> list[str]:
    return [iso_week(now - timedelta(weeks=offset)) for offset in range(weeks)]


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def census_counts(projects_dir: Path, now: datetime,
                  weeks: int = DEFAULT_WEEKS) -> dict:
    """{model_id: {iso_week: count}} over the trailing `weeks` ISO weeks.

    One count per assistant entry that names a model. Entries outside the
    window, entries of any other type, entries without a model, and lines that
    are not JSON at all are all skipped — a transcript being written while this
    runs will have a torn last line, and that is not a reason to fail.
    """
    wanted = set(window_weeks(now, weeks))
    counts: dict[str, dict[str, int]] = {}
    projects_dir = Path(projects_dir)
    if not projects_dir.is_dir():
        return counts

    for transcript in sorted(projects_dir.rglob("*.jsonl")):
        try:
            with open(transcript, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(entry, dict) or entry.get("type") != "assistant":
                        continue
                    message = entry.get("message")
                    model = message.get("model") if isinstance(message, dict) else None
                    when = _parse_ts(entry.get("timestamp"))
                    if not model or when is None:
                        continue
                    week = iso_week(when)
                    if week not in wanted:
                        continue
                    counts.setdefault(str(model), {})
                    counts[str(model)][week] = counts[str(model)].get(week, 0) + 1
        except OSError:
            continue
    return counts


def build_document(projects_dir: Path, now: datetime,
                   weeks: int = DEFAULT_WEEKS) -> dict:
    """The published artifact. Exactly three keys — see the module docstring."""
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weeks": window_weeks(now, weeks),
        "counts": census_counts(projects_dir, now, weeks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS,
                        help="Claude Code transcript root (default ~/.claude/projects)")
    parser.add_argument("--weeks", type=int, default=DEFAULT_WEEKS)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if not Path(args.projects).is_dir():
        # Say so and stop, rather than publishing a clean census of nothing —
        # the same rule the account-store Routine follows on a surface that
        # cannot do the job.
        print("no Claude Code transcript directory on this surface; "
              "nothing published", file=sys.stderr)
        return 2

    document = build_document(args.projects, datetime.now(timezone.utc), args.weeks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, sort_keys=True)
        f.write("\n")

    # Non-identifying status line only: counts, never names of anything local.
    total = sum(sum(by_week.values()) for by_week in document["counts"].values())
    print(f"census: {len(document['counts'])} models, {total} assistant turns, "
          f"{args.weeks} weeks -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
