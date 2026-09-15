#!/usr/bin/env python3
"""ISO-week arithmetic and RFC 3339 parsing, shared by the roster and the census.

`harness/roster.py` decides on 4- and 8-week windows; `scripts/model_usage
_census.py` buckets transcripts into the same weeks. They ran two copies of
this arithmetic and had to agree byte-for-byte on the week LABEL — a
disagreement would not raise, it would silently zero every usage share, which
is the failure mode with no symptom. One implementation, imported by both.

Stdlib only: the census runs on a durable machine from a plain checkout, with
no pip install between it and the transcripts.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_ts(value) -> datetime | None:
    """Parse an RFC 3339 timestamp, `Z` included. None on anything unparseable.

    Naive timestamps are read as UTC: every producer in this feature writes
    UTC, and guessing a local zone here would shift a week boundary.
    """
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


def iso_week(moment: datetime) -> str:
    """`2026-W36`. ISO year, NOT calendar year — they differ in early January,
    and mixing them puts one week of usage in a bucket nobody queries."""
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"


def window_weeks(now: datetime, count: int) -> list[str]:
    """The `count` ISO week labels ending with the one `now` falls in."""
    return [iso_week(now - timedelta(weeks=offset)) for offset in range(count)]


def window_start(now: datetime, count: int) -> datetime:
    """Midnight-ish lower bound of the `count`-week window.

    Deliberately generous — a whole extra week — because it is used to SKIP
    work (see the census's mtime prefilter), and a bound that is too tight
    drops real data while one that is too loose only costs a file read.
    """
    return now - timedelta(weeks=count + 1)
