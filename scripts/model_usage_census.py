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

AND THE KEYS ARE NOT TRUSTED EITHER. `message.model` is whatever the routing
layer wrote into the transcript, and it is not always a model id: a Bedrock
inference-profile ARN carries an AWS account number, a Vertex path carries a
GCP project id, a local proxy can put a filesystem path or free prose there.
Copying that verbatim into a top-level key published every one of them. Only
values matching `MODEL_ID_RE` become keys; everything else is counted under
the single key `other`, so the raw turn count this script publishes stays
honest — nothing is silently dropped — without any of those strings crossing
the boundary. The roster's own usage_share() then EXCLUDES `other`, and any
key it cannot rank, from what it divides by: this file's contract is a
truthful count of turns seen, not a truthful denominator for a model's
share, which is roster.py's decision to make. Nothing is ever passed
through `str()` — `str()` of a dict is `repr()`, which publishes its values.
`test/run_tests.py::TestIssue67::test_census_emits_only_model_week_counts_and
_leaks_nothing` and its review-round sibling in `TestIssue67Review` are the
guards on that, and they stay.

Runs on a durable machine (the transcripts are local, and a CI runner has
none). Weekly buckets, not daily: a daily series over one account is a
timeline of when a person was at their desk, and the roster policy only ever
asks about 4- and 8-week windows anyway.

Subagent transcripts are counted, on purpose: a subagent turn is a real API
turn against a real model, it is billed, and the roster's question is "what
does this account run", not "what did a human type at".

`generated_at` is when this script RAN, not when the usage happened — the
usage is in the week buckets. The roster's freshness check reads it as
"how long ago did someone last publish a census", which is the question it
should be asking of a publication timestamp.

Usage:
    python3 scripts/model_usage_census.py --out usage/latest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
from timeweeks import iso_week, parse_ts, window_start, window_weeks  # noqa: E402
# tier_words()/load_policy() ONLY — never the network or file-writing parts
# of roster.py. This is the one place model_usage_census.py stops being
# stdlib-only: roster.py imports PyYAML to read the tier ladder. The
# alternative — hand-rolling family words here — is exactly what NO MODEL
# IDS/FAMILY WORDS LIVE OUTSIDE roster-policy.yml exists to prevent.
import roster  # noqa: E402

DEFAULT_PROJECTS = Path.home() / ".claude" / "projects"
DEFAULT_WEEKS = 8
POLICY_PATH = Path(__file__).resolve().parent.parent / "evals" / "roster-policy.yml"


def _model_id_re() -> re.Pattern:
    """The shape of a model id, and the ONLY shape that becomes a published
    key. Being lowercase-and-dashes is necessary but not sufficient — a
    proxy alias or a path-shaped value can be shaped exactly like an id
    (measured: `claude-home-user-secret-client-northrop-merger`). It must
    also carry, as one of its dash-separated tokens, a family word from the
    tier ladder in evals/roster-policy.yml (read via `roster.tier_words`,
    never hardcoded here), and it is capped at the length a real id needs —
    about 40 — so a long adjacent string cannot ride in just because it
    happens to contain a family word somewhere in it.
    """
    words = "|".join(re.escape(w) for w in
                     roster.tier_words(roster.load_policy(POLICY_PATH)))
    return re.compile(
        rf"^(?=.{{1,40}}$)claude(?:-[a-z0-9.]{{1,20}})*-(?:{words})"
        rf"(?:-[a-z0-9.]{{1,20}})*$")


MODEL_ID_RE = _model_id_re()

#: Where everything else is counted. One key, no detail — the count is the
#: only part of a non-conforming value that is safe to publish.
OTHER_KEY = "other"


def published_key(model) -> str | None:
    """The key this `message.model` value may appear under, or None to skip.

    None means "this entry names no model" (absent or empty). Anything else
    that is not a model-id-shaped string — a dict, a list, an int, an ARN,
    a path, prose — is counted, but under `OTHER_KEY`.
    """
    if model is None or model == "":
        return None
    if isinstance(model, str) and MODEL_ID_RE.match(model):
        return model
    return OTHER_KEY


def _turn_key(entry: dict, message: dict):
    """What identifies one API turn across the several entries it writes.

    A single assistant turn is written as several JSONL entries — a thinking
    block, a text block, one per tool call — all sharing `message.id`. Counting
    entries measured tool density, not turns (2.5x inflation on an agentic
    transcript), and the roster's 10% and 2% bars were being decided on it.
    `requestId` is the fallback for older transcripts; an entry with neither is
    counted on its own, because there is nothing to fold it into.
    """
    for candidate in (message.get("id"), entry.get("requestId")):
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def census_counts(projects_dir: Path, now: datetime,
                  weeks: int = DEFAULT_WEEKS) -> dict:
    """{model_id: {iso_week: count}} over the trailing `weeks` ISO weeks.

    One count per assistant TURN that names a model, deduplicated per
    transcript on `message.id`. Entries outside the window, entries of any
    other type, entries without a model, and lines that are not JSON at all
    are all skipped — a transcript being written while this runs will have a
    torn last line, and that is not a reason to fail.
    """
    wanted = set(window_weeks(now, weeks))
    oldest = window_start(now, weeks)
    counts: dict[str, dict[str, int]] = {}
    projects_dir = Path(projects_dir)
    if not projects_dir.is_dir():
        return counts

    for transcript in sorted(projects_dir.rglob("*.jsonl")):
        try:
            # A transcript last written before the window cannot hold an entry
            # inside it; skipping it unread is the difference between reading
            # eight weeks of transcripts and reading every one ever made. The
            # bound carries a whole extra week of slack (window_start), so a
            # file being appended to across a week boundary is never dropped.
            if datetime.fromtimestamp(transcript.stat().st_mtime,
                                      timezone.utc) < oldest:
                continue
        except OSError:
            continue
        seen_turns: set[str] = set()
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
                    if not isinstance(message, dict):
                        continue
                    key = published_key(message.get("model"))
                    when = parse_ts(entry.get("timestamp"))
                    if key is None or when is None:
                        continue
                    week = iso_week(when)
                    if week not in wanted:
                        continue
                    turn = _turn_key(entry, message)
                    if turn is not None:
                        if turn in seen_turns:
                            continue
                        seen_turns.add(turn)
                    counts.setdefault(key, {})
                    counts[key][week] = counts[key].get(week, 0) + 1
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
        # cannot do the job. The message names no path: this line reaches a
        # public CI log and a Routine's status report.
        print("no Claude Code transcript directory on this surface; "
              "nothing published", file=sys.stderr)
        return 2

    document = build_document(args.projects, datetime.now(timezone.utc), args.weeks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, sort_keys=True)
        f.write("\n")

    # Non-identifying status line only: counts, and the OUTPUT path the caller
    # already knows — never a model id, never anything from under --projects.
    total = sum(sum(by_week.values()) for by_week in document["counts"].values())
    print(f"census: {len(document['counts'])} models, {total} assistant turns, "
          f"{args.weeks} weeks -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
