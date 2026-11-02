#!/usr/bin/env python3
"""The weekly usage file `usage/weekly-local.json`: its schema, and the reader
the improvement planner calls.

`scripts/model_usage_census.py --weekly-out` writes it and
`scripts/publish_usage_census.sh` publishes it on the `persistent/eval-results`
branch (see `evals/usage/CENSUS.md`). The planner reads it through `load`,
`is_fresh` and `weight`, so a skill used often is improved first.

THE SCHEMA LIVES HERE, and only here: the census builds every row with
`row()` (or `hook_row()`) and every document with `document()`. The file
holds rows of more than one kind, so the reader ignores any kind it is not
asked about.

    {"generated_at": "2026-09-04T12:00:00Z", "schema": 1,
     "sources": [{"surface": "local", "scope": "transcripts",
                  "from": "<window start>Z", "to": "<now>Z",
                  "sessions_scanned": n}],
     "rows": [{"week": "2026-08-31", "kind": "skill", "name": "<name|other>",
               "repo": null, "surface": "local", "invocations": n,
               "sessions": n, "blocked": null, "overridden": null,
               "outcome": null, "runner": null}]}

A `hook` row counts local git-hook runs from the agent-checks log: `name`
is a check id (or `other`, or `all` for every run that week), `repo` an
allowlisted public `owner/name`, `other` or null, `invocations` the runs in
which the check ran and `blocked` the runs in which it failed; `sessions` is
null; `runner` is the first 12 hex of the runner's digest, or null when the
log line had none (an absent `runner` reads as unknown, since rows written
elsewhere omit it). Non-hook rows carry `runner: null`. A `guidance` row
counts sessions per loaded-guidance state (`name` is
`full`, `stub-only`, `neither` or `unknown`; `invocations` is null). A second source, `scope: "hooks"` with `runs_scanned`, is present only
when a hook log was read, so an absent one means unknown, not zero.

CLOUD GUIDANCE rows come from the records cloud sessions write to the private
`persistent/usage-events` branch, never from a transcript: a `guidance` row
with `surface: "cloud"` (`name` is the state, or `invalid`) and a
`guidance-check` row with `surface: "cloud"` (`name` is `match`, `mismatch`,
`none`, `absent` or `unknown`), each counting sessions, `invocations` null. A
`guidance-check` row is a second view of the SAME sessions, so a sum of
sessions over week and surface leaves it out. Their source,
`scope: "guidance-records"` with `surface: "cloud"`, `records_scanned` (the
distinct sessions counted) and a `from` that is a week boundary, is present
only when the branch was read; its `from` is the later of the census window's
start and the Monday of the earliest record's week, because the records carry
no promise of coverage before the first one: coverage is unknown, not zero.
The registry commit a session installed is not recorded (`registry_sha` is
always null); a per-source install record is a follow-up.

`week` is the Monday (UTC) of the ISO week. Rows are sorted by week, kind,
name, repo. `sessions` is the number of distinct transcript files that invoked the
name that week; `sessions_scanned` is how many transcript files were read
inside the window. Neither carries an id.

UNKNOWN IS NOT ZERO. `weight()` returns None when there is no census or it is
stale, and 0 only when a fresh census saw no invocation of the skill. A
planner that read a missing census as "nobody uses anything" would rank every
skill last on the strength of a machine that did not run.

Stdlib only, no network; the caller supplies `now`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from timeweeks import parse_ts, week_monday, window_weeks

SCHEMA = 1
SURFACE_LOCAL = "local"
SURFACE_CLOUD = "cloud"
#: Kinds that count sessions: their invocations are always null.
SESSION_KINDS = ("guidance", "guidance-check")
CLOUD_SCOPE = "guidance-records"
ROW_FIELDS = ("week", "kind", "name", "repo", "surface", "invocations",
              "sessions", "blocked", "overridden", "outcome", "runner")
STAMP = "%Y-%m-%dT%H:%M:%SZ"


def row(iso_week_label: str, kind: str, name: str, invocations: int,
        sessions: int) -> dict:
    """One local row; the fields this census does not know are null."""
    return {"week": week_monday(iso_week_label), "kind": kind, "name": name,
            "repo": None, "surface": SURFACE_LOCAL, "invocations": invocations,
            "sessions": sessions, "blocked": None, "overridden": None,
            "outcome": None, "runner": None}


def hook_row(iso_week_label: str, name: str, repo: str | None, runs: int,
             blocked: int, runner: str | None = None) -> dict:
    """One local hook row: runs in which check `name` ran, and failed, by
    the runner build `runner` (12 hex of its digest, None when unknown)."""
    return {**row(iso_week_label, "hook", name, runs, None), "repo": repo,
            "blocked": blocked, "runner": runner}


def guidance_row(iso_week_label: str, state: str, sessions: int,
                 surface: str = SURFACE_LOCAL) -> dict:
    """One guidance row: `sessions` sessions that week whose loaded memory
    was in `state` (full, stub-only, neither or unknown; a cloud row may also
    be `invalid`), on `surface`."""
    return {**row(iso_week_label, "guidance", state, None, sessions),
            "surface": surface}


def guidance_check_row(iso_week_label: str, result: str, sessions: int) -> dict:
    """One cloud guidance-check row: `sessions` sessions that week whose
    check value report was `result` (match, mismatch, none, absent or unknown)."""
    return {**guidance_row(iso_week_label, result, sessions, SURFACE_CLOUD),
            "kind": "guidance-check"}


def cloud_source(window_from: datetime, now: datetime, records_scanned: int) -> dict:
    """The source of the cloud guidance rows. `to` is when they were read; the
    carry-forward below ages a source by it."""
    return {"surface": SURFACE_CLOUD, "scope": CLOUD_SCOPE,
            "from": window_from.strftime(STAMP), "to": now.strftime(STAMP),
            "records_scanned": records_scanned}


def document(rows: list[dict], now: datetime, window_from: datetime,
             sessions_scanned: int, hook_runs_scanned: int | None = None,
             cloud_guidance: dict | None = None) -> dict:
    """The whole file: exactly `generated_at`, `schema`, `sources`, `rows`.

    `cloud_guidance` is {"from": datetime, "records_scanned": n}, passed only
    when the private records were read."""
    window = {"surface": SURFACE_LOCAL, "from": window_from.strftime(STAMP),
              "to": now.strftime(STAMP)}
    sources = [{**window, "scope": "transcripts", "sessions_scanned": sessions_scanned}]
    if hook_runs_scanned is not None:
        sources.append({**window, "scope": "hooks", "runs_scanned": hook_runs_scanned})
    if cloud_guidance is not None:
        sources.append(cloud_source(cloud_guidance["from"], now,
                                    cloud_guidance["records_scanned"]))
    return {
        "generated_at": now.strftime(STAMP),
        "schema": SCHEMA,
        "sources": sources,
        "rows": sorted(rows, key=_sort_key),
    }


def _sort_key(entry: dict) -> tuple:
    return (entry["week"], entry["kind"], entry["name"], entry["repo"] or "",
            entry["surface"], entry["runner"] or "")


def _is_cloud_row(entry) -> bool:
    return (isinstance(entry, dict) and entry.get("surface") == SURFACE_CLOUD
            and entry.get("kind") in SESSION_KINDS)


def carry_cloud(previous, new: dict, max_age_days: int = 14) -> int:
    """Copy the cloud guidance rows and source of `previous` (the document
    last published) into `new`, verbatim, and return how many rows were
    carried. For when the private records could not be read this run: the
    rows are already public, and a census older than 14 days counts as
    missing, so a failed fetch must not drop them from a publish that goes
    ahead. Nothing is carried when `previous` has no cloud source, or its
    source was read more than `max_age_days` before `new` was generated: an
    old count must not look current."""
    now = parse_ts(new.get("generated_at"))
    if not isinstance(previous, dict) or now is None:
        return 0
    source = next((s for s in previous.get("sources", [])
                   if isinstance(s, dict) and s.get("surface") == SURFACE_CLOUD
                   and s.get("scope") == CLOUD_SCOPE), None)
    read = parse_ts(source.get("to")) if source else None
    if read is None or read > now or now - read > timedelta(days=max_age_days):
        return 0
    carried = [r for r in previous.get("rows", []) if _is_cloud_row(r)]
    new["sources"].append(source)
    new["rows"] = sorted(new["rows"] + carried, key=_sort_key)
    return len(carried)


def _count(value) -> bool:
    return type(value) is int and value >= 0


def load(path) -> dict | None:
    """The document at `path`, or None when it is missing, is not JSON, or
    does not have the published shape."""
    try:
        with open(Path(path), encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        return None
    if not isinstance(doc.get("generated_at"), str) or parse_ts(doc["generated_at"]) is None:
        return None
    sources, rows = doc.get("sources"), doc.get("rows")
    if not isinstance(sources, list) or not all(isinstance(s, dict) for s in sources):
        return None
    if not isinstance(rows, list):
        return None
    for entry in rows:
        if not isinstance(entry, dict):
            return None
        if not all(isinstance(entry.get(field), str) for field in ("week", "kind", "name")):
            return None
        # A guidance row counts sessions, so its invocations are null.
        if entry["kind"] in SESSION_KINDS:
            if entry.get("invocations") is not None:
                return None
        elif not _count(entry.get("invocations")):
            return None
    return doc


def is_fresh(doc, now: datetime, max_age_days: int = 14) -> bool:
    """True when `doc` was generated no more than `max_age_days` before `now`.

    A `generated_at` in the future is not fresh: every week of usage would
    fall outside the window (the roster's census check reads it the same way).
    """
    if not isinstance(doc, dict):
        return False
    generated = parse_ts(doc.get("generated_at"))
    if generated is None or generated > now:
        return False
    return now - generated <= timedelta(days=max_age_days)


def weight(doc, skill: str, now: datetime, weeks: int = 4) -> int | None:
    """Invocations of `skill` over the `weeks` ISO weeks ending with `now`'s,
    summed across every surface and repo.

    None when `doc` is None or stale (unknown); 0 when a fresh census has no
    row for it.
    """
    if doc is None or not is_fresh(doc, now) or not isinstance(doc.get("rows"), list):
        return None
    mondays = {week_monday(label) for label in window_weeks(now, weeks)}
    return sum(entry["invocations"] for entry in doc["rows"]
               if isinstance(entry, dict) and entry.get("kind") == "skill"
               and entry.get("name") == skill and entry.get("week") in mondays
               and _count(entry.get("invocations")))


def session_rate(doc, now: datetime, days: int = 28) -> float | None:
    """Transcript sessions scanned, scaled to `days` by the source window
    (`from` to `to`): the expected number of sessions in `days`, and so the
    expected uses of anything every session loads, such as the guidance.

    None when `doc` is None or stale, has no local transcripts source, or its
    window or count is unreadable (unknown, never 0).
    """
    if doc is None or not is_fresh(doc, now):
        return None
    for source in doc.get("sources", []):
        if source.get("scope") != "transcripts" or source.get("surface") != SURFACE_LOCAL:
            continue
        start, end = parse_ts(source.get("from")), parse_ts(source.get("to"))
        scanned = source.get("sessions_scanned")
        if start is None or end is None or end <= start or not _count(scanned):
            return None
        return scanned * (timedelta(days=days) / (end - start))
    return None
