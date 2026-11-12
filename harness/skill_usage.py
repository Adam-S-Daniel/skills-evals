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
`full`, `stub-only`, `neither` or `unknown`; `invocations` is null). A
`listing` row counts local sessions by how their first skill listing read
(`name` is `full`, `truncated` or `unknown`; `invocations` is null):
`truncated` means Claude Code's listing budget cut descriptions, so some
skills were listed by name only and could rarely trigger (#668). A second source, `scope: "hooks"` with `runs_scanned`, is present only
when a hook log was read, so an absent one means unknown, not zero.

CLOUD HOOK rows (cloud sessions' agent-checks runs) have the shape of the local
`hook` rows above, with `surface: "cloud"`: one row per (week, check id,
repo, runner) and an `all` row per week, `invocations` the runs in which the
check ran and `blocked` the runs in which it failed. They come from the
`events/<YYYY-MM>/cloud-hooks/<16 hex>.jsonl` records a cloud session's Stop
hook uploads to the private `persistent/usage-events` branch, never from a
log read here. Their source, `scope: "hook-records"` with `surface: "cloud"`
and `records_scanned` (the distinct runs counted), is present only when at
least one such record exists; its `from` is the later of the census window's
start and the Monday of the earliest record's week, so coverage before the
first record is unknown, not zero. A reader that finds no such source must
read cloud hook runs as not counted, never as zero.

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

LOADED SKILL COPIES (#562, 2026-11-02): a `skill-digest` row counts the
local uses of one allowlisted skill, in one week, by which copy the session
loaded: `digest` is the first 12 hex of the lock digest
(`harness/skill_digest.py`) or `unknown:<reason>` (`UNKNOWN_REASONS`, a fixed
list: a new reason is a schema change), `repo` the canonical `owner/repo` of
a `private: false` registry or null, `invocations` the uses and `sessions` the
distinct sessions; `digest` exists on this kind only. A prefix is published
only when the content once existed on a public branch of that registry (see
`scripts/model_usage_census.py`). For every published name and every week on
or after its source's `from`, the `skill-digest` invocations sum to the
`skill` row's. Their source is `scope: "skill-records"` with
`events_scanned` (the uses counted); absent means unknown, not zero.
`check_public` is the last gate before the file is published.

CLOUD `skill-digest` rows (#562 PR B) have `surface: "cloud"` and their own
`skill-records` source with `surface: "cloud"`. They count the uses cloud
sessions uploaded (one per distinct id, a use also recorded locally counted
only as local), so for each name and week their invocations equal the
distinct cloud ids counted. Coverage is records seen, never complete: uses
after a session's last successful upload are lost with the container. There
are no cloud `skill` rows, so no sum rule ties them to one.

`week` is the Monday (UTC) of the ISO week. Rows are sorted by week, kind,
name, repo. `sessions` is the number of distinct transcript files that invoked the
name that week; `sessions_scanned` is how many transcript files were read
inside the window. Neither carries an id.

UNKNOWN IS NOT ZERO. `weight()` returns None when there is no census or it is
stale, and 0 only when a fresh census saw no invocation of the skill. A skill
name is matched by its BASENAME (`skill_basename`): a census row may carry a
plugin prefix (`adam-coding-anywhere:debug-github-workflows`) and the registry
lists the bare name. A
planner that read a missing census as "nobody uses anything" would rank every
skill last on the strength of a machine that did not run.

Stdlib only, no network; the caller supplies `now`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from timeweeks import parse_ts, week_monday, window_weeks

SCHEMA = 1
SURFACE_LOCAL = "local"
SURFACE_CLOUD = "cloud"
#: Kinds that count sessions: their invocations are always null.
SESSION_KINDS = ("guidance", "guidance-check", "listing")
CLOUD_SCOPE = "guidance-records"
#: The source of the cloud `hook` rows: present only when hook records exist.
CLOUD_HOOK_SCOPE = "hook-records"
#: The cloud source's flag: its records say which sessions had the registry
#: installed and a full listing. Absent means cloud exposure is unknown.
LISTING_RECORDED = "listing_recorded"
#: The local transcripts source's list of the skill names the census counts
#: by name; any other skill is counted under `other` and so reads as 0 uses.
TRACKED_FIELD = "skill_keys"
#: #562: the source of the `skill-digest` rows, one per surface.
DIGEST_SCOPE = "skill-records"
DIGEST_KIND = "skill-digest"
#: Why a `skill-digest` row names no prefix. The first eight are the private
#: records' `DIGEST_NULL_REASONS` (scripts/model_usage_census.py; a test keeps
#: them equal); the last three are decided when the rows are built. Fixed: a
#: new reason is a schema change, never a free string from a record.
UNKNOWN_REASONS = ("no-base-dir", "builtin", "outside-known-roots", "gone",
                   "changed-since-load", "refused-by-registry-rules", "too-large",
                   "bad-name", "conflict", "unlisted-registry", "unverified-commit")
_PREFIX_RE = re.compile(r"[0-9a-f]{12}")
#: Any hex run longer than a published prefix: a full digest, a commit, a
#: session id's hex. Nothing in the file may carry one (#562).
_LONG_HEX_RE = re.compile(r"[0-9a-fA-F]{13,}")
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
             blocked: int, runner: str | None = None,
             surface: str = SURFACE_LOCAL) -> dict:
    """One hook row: runs in which check `name` ran, and failed, by the runner
    build `runner` (12 hex of its digest, None when unknown), on `surface`
    (local, or cloud for the records a cloud session uploaded)."""
    return {**row(iso_week_label, "hook", name, runs, None), "repo": repo,
            "blocked": blocked, "runner": runner, "surface": surface}


def guidance_row(iso_week_label: str, state: str, sessions: int,
                 surface: str = SURFACE_LOCAL) -> dict:
    """One guidance row: `sessions` sessions that week whose loaded memory
    was in `state` (full, stub-only, neither or unknown; a cloud row may also
    be `invalid`), on `surface`."""
    return {**row(iso_week_label, "guidance", state, None, sessions),
            "surface": surface}


def listing_row(iso_week_label: str, state: str, sessions: int,
                surface: str = SURFACE_LOCAL) -> dict:
    """One listing row: `sessions` sessions that week whose first skill
    listing was `state` (full, truncated or unknown), on `surface`. A cloud
    row is written only for the state `full`, and counts the sessions whose
    record shows the adam-agentskills registry installed AND a full listing
    (see `exposure_by_surface`)."""
    return {**row(iso_week_label, "listing", state, None, sessions), "surface": surface}


def truncated_listings(doc, now: datetime, weeks: int = 4) -> int:
    """Local sessions over the `weeks` ISO weeks ending with `now`'s whose
    skill listing had descriptions cut (#668); 0 when no row says so."""
    window = {week_monday(label) for label in window_weeks(now, weeks)}
    return sum(r.get("sessions") or 0 for r in (doc or {}).get("rows", [])
               if r.get("kind") == "listing" and r.get("name") == "truncated"
               and r.get("surface") == SURFACE_LOCAL and r.get("week") in window)


def guidance_check_row(iso_week_label: str, result: str, sessions: int) -> dict:
    """One cloud guidance-check row: `sessions` sessions that week whose
    check value report was `result` (match, mismatch, none, absent or unknown)."""
    return {**guidance_row(iso_week_label, result, sessions, SURFACE_CLOUD),
            "kind": "guidance-check"}


def digest_row(week_monday_text: str, name: str, repo: str | None, digest: str,
               invocations: int, sessions: int, surface: str = SURFACE_LOCAL) -> dict:
    """One `skill-digest` row (#562): `invocations` uses of `name` in the week
    starting `week_monday_text` whose session loaded the copy `digest` (12
    hex, or `unknown:<reason>`), in `sessions` distinct sessions."""
    return {"week": week_monday_text, "kind": DIGEST_KIND, "name": name, "repo": repo,
            "surface": surface, "invocations": invocations, "sessions": sessions,
            "digest": digest, "blocked": None, "overridden": None, "outcome": None,
            "runner": None}


def digest_source(floor: datetime, now: datetime, events_scanned: int,
                  surface: str = SURFACE_LOCAL) -> dict:
    """The source of the `skill-digest` rows: `from` is the floor (no week
    before it has rows), `events_scanned` the uses counted on or after it."""
    return {"surface": surface, "scope": DIGEST_SCOPE, "from": floor.strftime(STAMP),
            "to": now.strftime(STAMP), "events_scanned": events_scanned}


def add_rows(doc: dict, rows: list[dict], source: dict) -> None:
    """Add `rows` and their `source` to a built document, keeping the order."""
    doc["sources"].append(source)
    doc["rows"] = sorted(doc["rows"] + rows, key=_sort_key)


def cloud_source(window_from: datetime, now: datetime, records_scanned: int,
                 listing_recorded: bool = False) -> dict:
    """The source of the cloud guidance rows. `to` is when they were read; the
    carry-forward below ages a source by it. `listing_recorded` (published only
    when true) says the records carried the install and listing fields, so the
    cloud `listing` rows are a count and not an absence."""
    out = {"surface": SURFACE_CLOUD, "scope": CLOUD_SCOPE,
           "from": window_from.strftime(STAMP), "to": now.strftime(STAMP),
           "records_scanned": records_scanned}
    if listing_recorded:
        out[LISTING_RECORDED] = True
    return out


def cloud_hook_source(window_from: datetime, now: datetime, records_scanned: int) -> dict:
    """The source of the cloud `hook` rows (see CLOUD_HOOK_SCOPE)."""
    return {"surface": SURFACE_CLOUD, "scope": CLOUD_HOOK_SCOPE,
            "from": window_from.strftime(STAMP), "to": now.strftime(STAMP),
            "records_scanned": records_scanned}


def document(rows: list[dict], now: datetime, window_from: datetime,
             sessions_scanned: int, hook_runs_scanned: int | None = None,
             cloud_guidance: dict | None = None,
             skill_keys: list | None = None,
             cloud_hooks: dict | None = None) -> dict:
    """The whole file: exactly `generated_at`, `schema`, `sources`, `rows`.

    `cloud_guidance` is {"from": datetime, "records_scanned": n, optionally
    "listing_recorded": bool}, passed only when the private records were read.
    `skill_keys` is the skill names the census counts by name (TRACKED_FIELD
    on the transcripts source); None leaves it out, and a reader then cannot
    tell a skill with no use from one the census never counted.
    `cloud_hooks` is {"from": datetime, "records_scanned": n}, passed only when
    cloud hook records exist."""
    window = {"surface": SURFACE_LOCAL, "from": window_from.strftime(STAMP),
              "to": now.strftime(STAMP)}
    sources = [{**window, "scope": "transcripts", "sessions_scanned": sessions_scanned}]
    if skill_keys is not None:
        sources[0][TRACKED_FIELD] = sorted(set(skill_keys))
    if hook_runs_scanned is not None:
        sources.append({**window, "scope": "hooks", "runs_scanned": hook_runs_scanned})
    if cloud_guidance is not None:
        sources.append(cloud_source(cloud_guidance["from"], now,
                                    cloud_guidance["records_scanned"],
                                    bool(cloud_guidance.get("listing_recorded"))))
    if cloud_hooks is not None:
        sources.append(cloud_hook_source(cloud_hooks["from"], now,
                                         cloud_hooks["records_scanned"]))
    return {
        "generated_at": now.strftime(STAMP),
        "schema": SCHEMA,
        "sources": sources,
        "rows": sorted(rows, key=_sort_key),
    }


def _sort_key(entry: dict) -> tuple:
    return (entry["week"], entry["kind"], entry["name"], entry["repo"] or "",
            entry["surface"], entry.get("digest") or "", entry["runner"] or "")


#: What a publish whose private store could not be read carries forward from
#: the document last published (#562 generalized #536's cloud-only carry):
#: (summary label, source scope, row kinds, surface). Each entry is matched by
#: scope AND surface and aged by its own source's `to`, so a local guidance
#: row is never carried.
CARRIED = (("cloud", CLOUD_SCOPE, SESSION_KINDS, SURFACE_CLOUD),
           ("skill copies", DIGEST_SCOPE, (DIGEST_KIND,), SURFACE_LOCAL),
           ("cloud skill copies", DIGEST_SCOPE, (DIGEST_KIND,), SURFACE_CLOUD),
           ("cloud hooks", CLOUD_HOOK_SCOPE, ("hook",), SURFACE_CLOUD))


def carry(previous, new: dict, max_age_days: int = 14) -> dict:
    """Copy each CARRIED part of `previous` (the document last published)
    into `new`, verbatim, and return {label: rows carried, or None when that
    part was not carried}. For when the private records could not be read
    this run: the rows are already public, and a census older than 14 days
    counts as missing, so a failed fetch must not drop them from a publish
    that goes ahead. A part is not carried when `previous` has no such
    source, `new` already has one, or the source was read more than
    `max_age_days` before `new` was generated: an old count must not look
    current. The carried source keeps its old `to`, so a reader sees it is
    stale; the sum invariant is not re-checked on carried rows."""
    now = parse_ts(new.get("generated_at"))
    out = {}
    for label, scope, kinds, surface in CARRIED:
        out[label] = None
        if not isinstance(previous, dict) or now is None:
            continue
        if any(s.get("scope") == scope and s.get("surface") == surface
               for s in new["sources"]):
            continue
        source = next((s for s in previous.get("sources", [])
                       if isinstance(s, dict) and s.get("surface") == surface
                       and s.get("scope") == scope), None)
        read = parse_ts(source.get("to")) if source else None
        if read is None or read > now or now - read > timedelta(days=max_age_days):
            continue
        carried = [r for r in previous.get("rows", []) if isinstance(r, dict)
                   and r.get("surface") == surface and r.get("kind") in kinds]
        new["sources"].append(source)
        new["rows"] = sorted(new["rows"] + carried, key=_sort_key)
        out[label] = len(carried)
    return out


def check_public(doc, allowlist, public_repos) -> list[str]:
    """Why `doc` must not be published, as fixed phrases (never a value from
    the document); empty when it may. `public_repos` holds the canonical
    `owner/repo` of every `private: false` registry, `allowlist` the skill
    names that may be keys. The publisher calls it last, before `git add`
    (#562): a full digest, a commit, a fork's name or a private skill's name
    must fail here even if every builder above it has a bug."""
    problems = []
    if not isinstance(doc, dict) or not isinstance(doc.get("rows"), list):
        return ["not a usage document"]
    if _LONG_HEX_RE.search(json.dumps(doc, sort_keys=True)):
        problems.append("a hex run longer than 12")
    unknown = {f"unknown:{reason}" for reason in UNKNOWN_REASONS}
    listed = tracked_skills(doc)
    if listed is not None and not listed <= set(allowlist):
        problems.append("a tracked skill name outside the allowlist")
    for row in doc["rows"]:
        if not isinstance(row, dict):
            problems.append("a row that is not an object")
            continue
        kind = row.get("kind")
        if kind != DIGEST_KIND:
            if "digest" in row:
                problems.append("a digest on a row that is not skill-digest")
            if kind == "skill" and not (row.get("name") == "other"
                                        or row.get("name") in allowlist):
                problems.append("a skill name outside the allowlist")
            continue
        name, repo, digest = row.get("name"), row.get("repo"), row.get("digest")
        if name not in allowlist:
            problems.append("a skill-digest name outside the allowlist")
        if repo is not None and repo not in public_repos:
            problems.append("a skill-digest repo outside the public registries")
        if isinstance(digest, str) and _PREFIX_RE.fullmatch(digest):
            if repo is None:
                problems.append("a prefix with no public repo")
        elif digest not in unknown:
            problems.append("a digest that is neither a prefix nor a known reason")
    return problems


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


#: The census's catch-all skill name: never a real skill.
OTHER_NAME = "other"


def skill_basename(name: str) -> str:
    """`name` without any plugin prefix: everything up to the last `:` goes,
    so `adam-coding-anywhere:debug-github-workflows` is
    `debug-github-workflows` and a bare name is unchanged."""
    return name.rsplit(":", 1)[-1]


def weight(doc, skill: str, now: datetime, weeks: int = 4) -> int | None:
    """Invocations of `skill` over the `weeks` ISO weeks ending with `now`'s,
    summed across every surface and repo.

    Local uses come from the `skill` rows. Cloud uses come from the cloud
    `skill-digest` rows, because no cloud `skill` rows are written. There is no
    double count: the census counts a use whose id was also seen locally once,
    as local, so a cloud digest row never repeats a local use, and local
    `skill-digest` rows (which would repeat the `skill` rows) are never added.

    None when `doc` is None or stale (unknown); 0 when a fresh census has no
    row for it.
    """
    if doc is None or not is_fresh(doc, now) or not isinstance(doc.get("rows"), list):
        return None
    mondays = {week_monday(label) for label in window_weeks(now, weeks)}
    wanted = skill_basename(skill)
    if wanted == OTHER_NAME:
        return 0
    return sum(entry["invocations"] for entry in doc["rows"]
               if isinstance(entry, dict)
               and (entry.get("kind") == "skill"
                    or (entry.get("kind") == DIGEST_KIND
                        and entry.get("surface") == SURFACE_CLOUD))
               and isinstance(entry.get("name"), str)
               and skill_basename(entry["name"]) == wanted
               and entry.get("week") in mondays
               and _count(entry.get("invocations")))


def counted_from(doc, surface: str) -> datetime | None:
    """The first moment from which `doc` counts skill uses on `surface`.

    Local: the `from` of the local `transcripts` source, the start of the
    census window. Cloud: the `from` of the cloud `skill-records` source plus
    7 days. That `from` is the Monday of the week of the earliest cloud record,
    and the records started mid-week (the hook was new), so that first week is
    only partly covered; counting from the next week is the conservative
    reading.

    None when the source is missing, its `from` is unparseable, or `surface`
    is neither.
    """
    if not isinstance(doc, dict):
        return None
    if surface == SURFACE_LOCAL:
        scope, extra = "transcripts", timedelta(0)
    elif surface == SURFACE_CLOUD:
        scope, extra = DIGEST_SCOPE, timedelta(days=7)
    else:
        return None
    for source in doc.get("sources") or []:
        if (isinstance(source, dict) and source.get("scope") == scope
                and source.get("surface") == surface):
            start = parse_ts(source.get("from"))
            return None if start is None else start + extra
    return None


def tracked_skills(doc) -> frozenset | None:
    """The skill names `doc` says the census counts by name, or None when it
    does not say (a document published before the list existed)."""
    if not isinstance(doc, dict):
        return None
    for source in doc.get("sources") or []:
        if (isinstance(source, dict) and source.get("scope") == "transcripts"
                and source.get("surface") == SURFACE_LOCAL):
            keys = source.get(TRACKED_FIELD)
            if isinstance(keys, list) and all(isinstance(k, str) for k in keys):
                return frozenset(keys)
            return None
    return None


def is_tracked(doc, skill: str) -> bool:
    """True only when `doc` lists `skill` (by basename) among the names the
    census counts. A skill it does not list is counted under `other`, so its
    zero uses prove nothing; a document with no list cannot say."""
    keys = tracked_skills(doc)
    return keys is not None and skill_basename(skill) in keys


#: Sources a surface's counts come from, by scope.
_SURFACE_SCOPES = {SURFACE_LOCAL: ("transcripts",), SURFACE_CLOUD: (CLOUD_SCOPE,)}


def census_current(doc, surfaces: tuple, now: datetime,
                   max_age: timedelta = timedelta(days=1)) -> bool:
    """True when `doc`'s `generated_at` and the `to` of every source on each
    of `surfaces` lie within `max_age` before `now` (never after it), and each
    surface has the source its counts come from. `is_fresh` allows 14 days and
    `carry` keeps a cloud source with an old `to`; an irreversible action
    reads this instead, so the census stops where the floor window stops."""
    if not isinstance(doc, dict):
        return False

    def recent(value) -> bool:
        moment = parse_ts(value)
        return moment is not None and timedelta(0) <= now - moment <= max_age

    if not recent(doc.get("generated_at")):
        return False
    for surface in surfaces:
        sources = [s for s in doc.get("sources") or []
                   if isinstance(s, dict) and s.get("surface") == surface]
        if not any(s.get("scope") in _SURFACE_SCOPES.get(surface, ()) for s in sources):
            return False
        if not all(recent(s.get("to")) for s in sources):
            return False
    return True


#: Sessions on the surfaces a skill reaches in which it was listed, with no
#: use, before a zero reads as evidence rather than a quiet fortnight. The
#: single source: scripts/eval_scope.py and the removal policy import it.
ZERO_USE_MIN_SESSIONS = 500
#: The census's window, in ISO weeks.
CENSUS_WEEKS = 8


def exposure_by_surface(doc, now: datetime, surfaces: tuple = (SURFACE_LOCAL, SURFACE_CLOUD),
                        weeks: int = CENSUS_WEEKS) -> dict | None:
    """{surface: sessions, or None when unknown} in which a skill reaching
    that surface was listed in full, over the `weeks` ISO weeks ending with
    `now`'s week. A surface counts only the weeks whose Monday is on or after
    its `counted_from`; a surface with no `counted_from` contributes 0.

    Local: the `listing` rows named `full`. A `truncated` listing cut some
    descriptions and an `unknown` one has no record, so neither counts (they
    are left out, not a veto). Cloud: the `listing` rows named `full` with
    surface cloud, which count only sessions whose record shows the
    adam-agentskills registry installed AND a full, untruncated listing. A
    cloud listing can be truncated, and a guidance record is written whether
    or not the skills bundle was installed, so the `guidance` rows prove
    neither and are never counted. When the cloud source does not say its
    records carried those fields (`LISTING_RECORDED`), cloud exposure is None:
    unknown, never 0. `guidance-check` rows are a second view of the same
    sessions and are never counted.

    None when `doc` is None or stale (unknown, never 0).
    """
    if doc is None or not is_fresh(doc, now) or not isinstance(doc.get("rows"), list):
        return None
    mondays = {week_monday(label) for label in window_weeks(now, weeks)}
    out = {}
    for surface in surfaces:
        if surface == SURFACE_CLOUD and not any(
                isinstance(s, dict) and s.get("scope") == CLOUD_SCOPE
                and s.get("surface") == SURFACE_CLOUD and s.get(LISTING_RECORDED) is True
                for s in doc.get("sources") or []):
            out[surface] = None
            continue
        counted = counted_from(doc, surface)
        total = 0
        if counted is not None:
            usable = {m for m in mondays
                      if datetime.fromisoformat(m).replace(tzinfo=timezone.utc) >= counted}
            for entry in doc["rows"]:
                if (not isinstance(entry, dict) or entry.get("surface") != surface
                        or entry.get("week") not in usable
                        or not _count(entry.get("sessions"))):
                    continue
                if entry.get("kind") == "listing" and entry.get("name") == "full":
                    total += entry["sessions"]
        out[surface] = total
    return out


def exposure(doc, now: datetime, surfaces: tuple = (SURFACE_LOCAL, SURFACE_CLOUD),
             weeks: int = CENSUS_WEEKS) -> int | None:
    """The sum of `exposure_by_surface` over the surfaces whose exposure is
    known (a pause may rest on those); None when `doc` is stale."""
    by_surface = exposure_by_surface(doc, now, surfaces, weeks)
    return None if by_surface is None else sum(n for n in by_surface.values() if n is not None)


def zero_use(doc, skill: str, now: datetime, weeks: int = CENSUS_WEEKS,
             surfaces: tuple = (SURFACE_LOCAL, SURFACE_CLOUD),
             min_sessions: int = ZERO_USE_MIN_SESSIONS) -> bool | None:
    """True when `skill` had no use over the `weeks` ISO weeks ending with
    `now`'s AND the surfaces it reaches listed it in full in at least
    `min_sessions` sessions (`exposure`); False when it had any use (any use
    wins, whatever the exposure); None when that cannot be known.

    This is the contract the eval-scope automation uses to stop evals on
    skills nobody uses. UNKNOWN IS NOT ZERO: None when `doc` is None or stale,
    and None when there was no use but too few sessions to say so (a skill
    nobody could have used has no zero). Exposure replaces the older
    truncated-listing and per-surface coverage vetoes: a truncated listing is
    not counted, and a surface counted for fewer weeks has fewer sessions.
    Pass only the surfaces the skill actually reaches, for example
    `(SURFACE_LOCAL,)` for a plugin delivered only to the owner's machines.
    """
    if doc is None or not is_fresh(doc, now):
        return None
    used = weight(doc, skill, now, weeks)
    if used is None:
        return None
    if used > 0:
        return False
    if not is_tracked(doc, skill):
        return None
    seen = exposure(doc, now, surfaces, weeks)
    return True if seen is not None and seen >= min_sessions else None


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
