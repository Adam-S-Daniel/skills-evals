#!/usr/bin/env python3
"""Ingest cloud usage records dropped in the private S3 bucket into the
private usage store.

A cloud session in a project that has no write access to the private
repository cannot append its usage records with git. _agent-guidance ADR 0037
gives it a second route: the Stop hook (`guidance-load-record.sh`) PUTs one
JSON object per send to a private S3 bucket under
`drop/<YYYY-MM-DD>/<32 hex>.json`, and adam-agentskills-private's
`.github/workflows/usage-sink-ingest.yml` lists the bucket, downloads the
planned objects, and runs this script against its checkout of the private
`persistent/usage-events` branch. This script writes the records into exactly
the files the census already reads (`model_usage_census.py`):

  * a guidance record -> events/<YYYY-MM of its ts>/cloud-guidance.jsonl
    (read by `cloud_guidance_tally`), unless its `session` already appears in
    any events/*/cloud-guidance.jsonl;
  * a skill line -> events/<YYYY-MM of its ts>/cloud-skills/<session>.jsonl
    (read by `cloud_skill_records`), unless its `id` is already in that shard.

Each line is re-serialized compactly (`separators=(",", ":")`), which gives
back the hook's own bytes: the git route writes the same `json.dumps` of the
same dict, in the same key order.

THE OBJECTS ARE UNTRUSTED. The writer key that uploads them sits in every
cloud environment that sends records, so anyone holding it can upload
anything under `drop/`, with any key, date part and content. So:

  * Every pattern applied to a key, date or hex value is ASCII only
    (`[0-9]`, `re.ASCII`): Python's `\\d` also matches other scripts' digits,
    and such a key would pass here and fail the workflow's bash check. The
    census patterns used here are written with explicit ASCII classes, and
    every string checked against them must also be `str.isascii()`.
  * `plan` keeps a key only when its date part is the UTC date of the
    object's `LastModified` (set by S3, not by the writer) or the day
    before, and orders by `LastModified`, so a backdated or junk key cannot
    sort ahead of real ones. It plans at most `--max` keys per run.
  * A record whose `ts` is more than MAX_BEFORE before or MAX_AFTER after its
    object's `LastModified` is invalid, so a forged record cannot be
    backdated into past weeks' tallies.
  * THE ENVELOPE is checked whole: at most SIZE_CAP bytes, UTF-8, JSON with
    no duplicated key and no NaN/Infinity, exactly the keys {v, kind, sent,
    guidance, skills}, `v` 1, `kind` `usage-drop`, `sent` a UTC second stamp,
    `guidance` a list of at most one item and `skills` a list. An object
    whose envelope fails is rejected whole (`bad-envelope`) and nothing from
    it is written.
  * EACH RECORD is checked on its own. A skill line must pass the census's
    own reader (`_cloud_line_ok`, the ADR 0036 shape); a guidance record
    must pass `guidance_record_ok`: exactly the keys the hook's phase 1
    uploads (GUIDANCE_KEYS), each value in the shape the hook builds it. The
    hook's local copy of a record carries one more key, `uploaded`; the line
    it uploads does not. A record with `uploaded` (true, false or null) is
    accepted and stored without it. Records in the hook's older shapes (no
    `check_*`, no `sources`) are invalid. Invalid records are dropped and
    counted; the object's valid records are kept, and the object is recorded
    as ingested with `partial=<number dropped>`. A record lost to a
    validator that drifted from the hook is then one record, not a whole
    object's worth.

Rejections carry one of the fixed REASONS and the VALIDATOR_VERSION, never
anything taken from the object. A key rejected under an older version is
planned again, except for `unreadable` and `bad-envelope`, which no
validator change can turn into an accepted object.

THE STORE LAYOUT (relative to `--store`):

  events/<YYYY-MM>/cloud-guidance.jsonl         guidance records (append only)
  events/<YYYY-MM>/cloud-skills/<16 hex>.jsonl  skill lines (append only)
  sink/ingested/<YYYY-MM>.txt                   `<key> <sha256 of body>[ partial=<k>]`
  sink/rejected/<YYYY-MM>.txt                   `<key> <reason> v<version>`

The two index files take the month of the key's own date. A rejected line
without a version (written before versions existed) reads as version 1. A key
ingested, or rejected for good, is never planned or applied again, so a
re-run is IDEMPOTENT: the second `apply` over the same objects changes no
byte. Data lines are written before the index line, so an interrupted run is
finished by the next one, whose dedupe (session, id) keeps the data from
doubling.

WRITES ARE APPEND ONLY: an existing line is never rewritten or deleted (a
file that does not end in a newline gets one before the first appended
line, as the hook's git route does). Every path written is refused, before
anything is written for that object, when it or any directory between it
and the store is a symbolic link: the store is a clone of a branch, and a
committed link could point a write at another file or out of the clone.

NOTHING FROM AN OBJECT IS PRINTED. `plan` prints keys (which the listing
already holds and which pass KEY_RE) and S3's `LastModified`; `apply` prints
counts and fixed reason names only. Errors are fixed strings on stderr.

Subcommands (stdlib only):

  plan  --listing FILE --store DIR [--max N]
        FILE is `aws s3api list-objects-v2` JSON output. Prints at most N
        (default 300) lines `<key>\\t<LastModified as YYYY-MM-DDTHH:MM:SSZ>`,
        oldest LastModified first (then by key), for every key that matches
        KEY_RE, has an int `Size` no larger than SIZE_CAP, has a date part
        equal to LastModified's UTC date or the day before, and is not
        already recorded (see above). The last stderr line is always
        `planned=<n> backlog=<eligible> skipped_bad_date=<n> skipped_size=<n>`.
  apply --incoming DIR --store DIR --manifest FILE [--unreadable FILE]
        DIR holds the downloaded objects at their keys
        (DIR/drop/<date>/<hex>.json). FILE is the plan's output; an object
        not in it, any other name, and any link are ignored. The
        `--unreadable` file lists keys, one per line, that the workflow could
        not GET (SSE-C, an archive storage class, a vanished object): each is
        recorded as rejected `unreadable`.

Exit 0 on success, rejections included; 2 when an input cannot be read
(the listing, manifest, unreadable list, or the incoming or store
directory); 1 when a write fails or would go through a link.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_usage_census as census  # noqa: E402

#: Bumped whenever validation accepts more than before, so that keys rejected
#: by an older version (except for good: PERMANENT_REASONS) are planned again.
VALIDATOR_VERSION = 2

#: The hook's object key: `drop/<UTC day of send>/<32 hex from os.urandom>.json`.
KEY_RE = re.compile(r"drop/([0-9]{4}-[0-9]{2})-[0-9]{2}/[0-9a-f]{32}\.json", re.ASCII)
_DATE_DIR_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_KEY_FILE_RE = re.compile(r"[0-9a-f]{32}\.json", re.ASCII)
_MONTH_RE = re.compile(r"[0-9]{4}-[0-9]{2}", re.ASCII)
#: S3's LastModified as the AWS CLI prints it (`+00:00` or `Z`, fraction optional).
_LISTED_TIME_RE = re.compile(
    r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.[0-9]{1,9})?"
    r"(Z|[+-][0-9]{2}:?[0-9]{2})", re.ASCII)
#: Whole seconds, UTC, as the hook's strftime("%Y-%m-%dT%H:%M:%SZ") writes;
#: also the plan's LastModified column.
SECOND_TS_RE = re.compile(
    r"(20[0-9]{2}|2100)-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", re.ASCII)
ISO = "%Y-%m-%dT%H:%M:%SZ"
#: The largest object the hook sends; a larger one is split.
SIZE_CAP = 262144
DEFAULT_MAX = 300
#: A record's `ts` must lie within this window around its object's LastModified.
MAX_BEFORE = timedelta(hours=48)
MAX_AFTER = timedelta(minutes=10)

DROP_KEYS = frozenset({"v", "kind", "sent", "guidance", "skills"})

#: Phase 1's uploaded line: `phase1()` in guidance-load-record.sh.
GUIDANCE_KEYS = frozenset({
    "v", "ts", "kind", "session", "surface", "remote", "cli", "state", "repos",
    "guidance_version", "check_expected", "check_reported", "registry_sha",
    "sources", "sources_dropped"})
#: The hook's local copy adds this one; it is dropped before storing.
UPLOADED_KEY = "uploaded"
#: The transcript's `entrypoint` (remote_projects, remote_trigger, cli, ...).
SURFACE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", re.ASCII)
GUIDANCE_VERSION_RE = re.compile(r"[0-9a-f]{8}", re.ASCII)
#: `registry_sources()`: `<owner>/<repo>` from a github.com URL.
SOURCE_REGISTRY_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}/[A-Za-z0-9][A-Za-z0-9._-]{0,99}", re.ASCII)
SOURCE_REF_RE = re.compile(r"[0-9a-f]{40}", re.ASCII)
_VERSION_TOKEN_RE = re.compile(r"v([0-9]{1,6})", re.ASCII)
MAX_SOURCES = 16
MAX_COUNT = 1_000_000

UNREADABLE, BAD_ENVELOPE = "unreadable", "bad-envelope"
REASONS = (UNREADABLE, BAD_ENVELOPE)
#: Reasons no validator change can undo: never planned again.
PERMANENT_REASONS = frozenset(REASONS)

SINK_DIR = "sink"
INGESTED, REJECTED = "ingested", "rejected"


class Rejected(Exception):
    """An object's envelope fails validation."""


class LinkRefused(Exception):
    """A path to be written goes through a symbolic link."""


class BadInput(Exception):
    """An input file (listing, manifest, unreadable list) cannot be read."""


# --- validation -----------------------------------------------------------------

def _ascii_match(pattern: re.Pattern, value) -> bool:
    return isinstance(value, str) and value.isascii() and bool(pattern.fullmatch(value))


def _count(value) -> bool:
    return type(value) is int and 0 <= value <= MAX_COUNT


def _ts_near(ts: str, modified: datetime | None) -> bool:
    """Whether the record time `ts` (already shape-checked) lies in
    [modified - MAX_BEFORE, modified + MAX_AFTER]; True with no `modified`."""
    when = census.parse_ts(ts)
    if when is None:
        return False
    if modified is None:
        return True
    when = when.astimezone(timezone.utc)
    return modified - MAX_BEFORE <= when <= modified + MAX_AFTER


def guidance_record_ok(record, modified: datetime | None = None) -> bool:
    """Whether `record` has exactly the shape phase 1 of the hook uploads
    (with or without `uploaded`), stamped near `modified` when given."""
    if not isinstance(record, dict):
        return False
    keys = set(record)
    if keys != GUIDANCE_KEYS and keys != GUIDANCE_KEYS | {UPLOADED_KEY}:
        return False
    ts, state, expected = record["ts"], record["state"], record["check_expected"]
    sources, dropped = record["sources"], record["sources_dropped"]
    cli, surface, version = record["cli"], record["surface"], record["guidance_version"]
    if not (type(record["v"]) is int and record["v"] == 1
            and record["kind"] == "guidance-load"
            and _ascii_match(census.CLOUD_SESSION_RE, record["session"])
            and _ascii_match(SECOND_TS_RE, ts) and _ts_near(ts, modified)
            and (surface is None or _ascii_match(SURFACE_RE, surface))
            and record["remote"] is True
            and (cli is None or _ascii_match(census.CLOUD_CLI_RE, cli))
            and isinstance(state, str) and state in census.GUIDANCE_STATES
            and _count(record["repos"])
            and (version is None or _ascii_match(GUIDANCE_VERSION_RE, version))
            and isinstance(record["check_reported"], str)
            and record["check_reported"] in census.CHECK_RESULTS
            and record["registry_sha"] is None
            and record.get(UPLOADED_KEY, None) in (None, True, False)):
        return False
    # `unknown` means no instructions entry: no repos, no expected value.
    if state == census.GUIDANCE_UNKNOWN:
        if expected is not None or record["repos"] != 0:
            return False
    elif expected is not True and expected is not False:
        return False
    if record["check_reported"] == "match" and expected is not True:
        return False
    if sources is None:
        return dropped is None
    if not (isinstance(sources, list) and len(sources) <= MAX_SOURCES and _count(dropped)):
        return False
    pairs = []
    for item in sources:
        if not (isinstance(item, dict) and set(item) == {"registry", "ref"}
                and _ascii_match(SOURCE_REGISTRY_RE, item["registry"])
                and _ascii_match(SOURCE_REF_RE, item["ref"])):
            return False
        pairs.append((item["registry"], item["ref"]))
    return pairs == sorted(set(pairs))


def skill_line_ok(record, modified: datetime | None = None) -> bool:
    """Whether `record` is a well-formed ADR 0036 shard line, by the census's
    own reader, for the shard its `ts` and `session` file it under, with
    every string ASCII and its `ts` near `modified` when given."""
    if not (isinstance(record, dict) and isinstance(record.get("ts"), str)
            and _ascii_match(census.CLOUD_SESSION_RE, record.get("session"))
            and all(v.isascii() for v in record.values() if isinstance(v, str))):
        return False
    return (census._cloud_line_ok(record, record["ts"][:7], record["session"])
            and _ts_near(record["ts"], modified))


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise Rejected(BAD_ENVELOPE)
    return dict(pairs)


def _no_constant(_name):
    raise Rejected(BAD_ENVELOPE)


def parse_drop(body: bytes) -> dict:
    """The object, with a valid envelope, or Rejected(BAD_ENVELOPE). The
    records inside are not checked here (see `split_records`)."""
    if len(body) > SIZE_CAP:
        raise Rejected(BAD_ENVELOPE)
    try:
        doc = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates,
                         parse_constant=_no_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise Rejected(BAD_ENVELOPE) from None
    if not (isinstance(doc, dict) and set(doc) == DROP_KEYS
            and type(doc["v"]) is int and doc["v"] == 1
            and doc["kind"] == "usage-drop"
            and _ascii_match(SECOND_TS_RE, doc["sent"])
            and census.parse_ts(doc["sent"]) is not None
            and isinstance(doc["guidance"], list) and len(doc["guidance"]) <= 1
            and isinstance(doc["skills"], list)):
        raise Rejected(BAD_ENVELOPE)
    return doc


def split_records(doc: dict, modified: datetime | None) -> tuple[list, list, int]:
    """(valid guidance records, valid skill lines, number of invalid records)."""
    guidance = [r for r in doc["guidance"] if guidance_record_ok(r, modified)]
    skills = [r for r in doc["skills"] if skill_line_ok(r, modified)]
    dropped = len(doc["guidance"]) + len(doc["skills"]) - len(guidance) - len(skills)
    return guidance, skills, dropped


# --- the store ------------------------------------------------------------------

def _index_lines(store: Path, sub: str):
    """The lines of sink/<sub>/<YYYY-MM>.txt, READ-ONLY; linked directories
    and files, and names of another shape, are skipped."""
    sink = store / SINK_DIR
    folder = sink / sub
    if sink.is_symlink() or folder.is_symlink() or not folder.is_dir():
        return
    for path in sorted(folder.glob("*.txt")):
        if path.is_symlink() or not path.is_file() or not _MONTH_RE.fullmatch(path.stem):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        yield from (line for line in text.splitlines() if line)


def _done_keys(store: Path) -> set:
    """Keys that are never planned or applied again: every ingested key, and
    every key rejected under the current validator or for a permanent reason.
    A rejected line `<key> <reason>` with no version token is version 1."""
    done = {line.split(" ", 1)[0] for line in _index_lines(store, INGESTED)}
    for line in _index_lines(store, REJECTED):
        parts = line.split(" ")
        reason = parts[1] if len(parts) > 1 else ""
        found = _VERSION_TOKEN_RE.fullmatch(parts[2]) if len(parts) > 2 else None
        version = int(found.group(1)) if found else 1
        if reason in PERMANENT_REASONS or version >= VALIDATOR_VERSION:
            done.add(parts[0])
    return done


def _guidance_sessions(store: Path) -> set:
    """Every string `session` in the store's events/*/cloud-guidance.jsonl,
    READ-ONLY; linked months and files are skipped, as the census skips them."""
    sessions = set()
    for path in sorted(store.glob(f"{census.EVENTS_DIR}/*/{census.CLOUD_GUIDANCE_FILE}")):
        if path.parent.is_symlink() or path.is_symlink() or not path.is_file():
            continue
        for record in census._jsonl_dicts(path):
            if isinstance(record.get("session"), str):
                sessions.add(record["session"])
    return sessions


def _shard_ids(path: Path) -> set:
    if not path.exists():
        return set()
    return {r["id"] for r in census._jsonl_dicts(path) if isinstance(r.get("id"), str)}


def _check_target(store: Path, rel: tuple) -> Path:
    """`store`/rel..., after checking that no existing component below the
    store is a link and that an existing target is a regular file."""
    path = store
    for part in rel:
        path = path / part
        if path.is_symlink():
            raise LinkRefused()
    if path.exists() and not path.is_file():
        raise LinkRefused()
    return path


def _append(path: Path, lines: list) -> None:
    """Append `lines` (str, no newline) to `path`, creating it and its
    directories; never through a link (O_NOFOLLOW on the file itself)."""
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o644)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise LinkRefused()
        prefix = b""
        if info.st_size and os.pread(fd, 1, info.st_size - 1) != b"\n":
            prefix = b"\n"
        data = prefix + "".join(line + "\n" for line in lines).encode("utf-8")
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
    finally:
        os.close(fd)


def _line(record: dict) -> str:
    return json.dumps(record, separators=(",", ":"))


def _reject_line(key: str, reason: str) -> str:
    return f"{key} {reason} v{VALIDATOR_VERSION}"


# --- plan -----------------------------------------------------------------------

def _listed_time(value) -> datetime | None:
    """S3's LastModified, in UTC, truncated to the second; None if malformed."""
    found = _LISTED_TIME_RE.fullmatch(value) if isinstance(value, str) else None
    if not found or not value.isascii():
        return None
    offset = "+00:00" if found.group(2) == "Z" else found.group(2)
    try:
        when = datetime.fromisoformat(found.group(1) + offset)
    except ValueError:
        return None
    return when.astimezone(timezone.utc)


def _key_date(key: str) -> date | None:
    try:
        return date.fromisoformat(key[5:15])
    except ValueError:
        return None


def plan(listing_path, store, limit: int = DEFAULT_MAX) -> tuple[list, dict]:
    """([(key, LastModified text)] to fetch, oldest first, at most `limit`;
    counts). BadInput on an unreadable listing."""
    try:
        text = Path(listing_path).read_text(encoding="utf-8")
        doc = json.loads(text) if text.strip() else {}
    except (OSError, UnicodeDecodeError, ValueError):
        raise BadInput() from None
    contents = doc.get("Contents") if isinstance(doc, dict) else None
    if not isinstance(doc, dict) or not isinstance(contents or [], list):
        raise BadInput()
    done = _done_keys(Path(store))
    counts = {"skipped_bad_date": 0, "skipped_size": 0}
    eligible = {}
    for item in contents or []:
        key = item.get("Key") if isinstance(item, dict) else None
        if not _ascii_match(KEY_RE, key) or key in done or key in eligible:
            continue
        size = item.get("Size")
        if not (type(size) is int and 0 <= size <= SIZE_CAP):
            counts["skipped_size"] += 1
            continue
        when, day = _listed_time(item.get("LastModified")), _key_date(key)
        if when is None or day is None or day not in (when.date(),
                                                      when.date() - timedelta(days=1)):
            counts["skipped_bad_date"] += 1
            continue
        eligible[key] = when
    ordered = sorted(eligible.items(), key=lambda kv: (kv[1], kv[0]))
    counts["backlog"] = len(ordered)
    planned = [(key, when.strftime(ISO)) for key, when in ordered[:limit]]
    counts["planned"] = len(planned)
    return planned, counts


# --- apply ----------------------------------------------------------------------

def read_manifest(path) -> dict:
    """{key: LastModified} from the plan's lines. BadInput when the file
    cannot be read or a line is not `<key>\\t<YYYY-MM-DDTHH:MM:SSZ>`."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise BadInput() from None
    manifest = {}
    for line in text.splitlines():
        if not line:
            continue
        key, sep, stamp = line.partition("\t")
        if not (sep and _ascii_match(KEY_RE, key) and _ascii_match(SECOND_TS_RE, stamp)):
            raise BadInput()
        try:
            manifest[key] = datetime.strptime(stamp, ISO).replace(tzinfo=timezone.utc)
        except ValueError:
            raise BadInput() from None
    return manifest


def read_unreadable(path) -> list:
    """The keys of the `--unreadable` file, one per line. BadInput when the
    file cannot be read or a line is not a key."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise BadInput() from None
    keys = [line for line in text.splitlines() if line]
    if not all(_ascii_match(KEY_RE, key) for key in keys):
        raise BadInput()
    return sorted(set(keys))


def _incoming_keys(incoming: Path):
    """({key: path} of the key-named regular files under `incoming`, never
    through a link; how many other entries were passed over)."""
    keys, ignored = {}, 0
    for top in sorted(incoming.iterdir()):
        if top.name != "drop" or top.is_symlink() or not top.is_dir():
            ignored += 1
            continue
        for day in sorted(top.iterdir()):
            if day.is_symlink() or not day.is_dir() or not _ascii_match(_DATE_DIR_RE, day.name):
                ignored += 1
                continue
            for obj in sorted(day.iterdir()):
                key = f"drop/{day.name}/{obj.name}"
                if (obj.is_symlink() or not obj.is_file()
                        or not _ascii_match(_KEY_FILE_RE, obj.name)
                        or not _ascii_match(KEY_RE, key)):
                    ignored += 1
                    continue
                keys[key] = obj
    return keys, ignored


def _read_object(path: Path) -> bytes:
    """At most SIZE_CAP + 1 bytes of a regular file, never through a link."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise OSError("not a regular file")
        return f.read(SIZE_CAP + 1)


def apply(incoming, store, manifest: dict, unreadable=()) -> dict:
    """Ingest the manifest's objects under `incoming` into `store`, and
    record each `unreadable` key as rejected. Returns counts. LinkRefused or
    OSError when a write cannot be made safely."""
    incoming, store = Path(incoming), Path(store).resolve()
    if not incoming.is_dir() or not store.is_dir():
        raise FileNotFoundError("incoming or store is not a directory")
    found, ignored = _incoming_keys(incoming)
    done = _done_keys(store)
    sessions = _guidance_sessions(store)
    stats = {"objects": 0, "ingested": 0, "partial": 0, "rejected": 0, "already": 0,
             "ignored": ignored + len(set(found) - set(manifest) - set(unreadable)),
             "missing": 0, "records_dropped": 0, "guidance_added": 0,
             "skills_added": 0, "reasons": {}}

    def reject(key, reason):
        month = KEY_RE.fullmatch(key).group(1)
        target = _check_target(store, (SINK_DIR, REJECTED, f"{month}.txt"))
        _append(target, [_reject_line(key, reason)])
        done.add(key)
        stats["rejected"] += 1
        stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1

    for key in unreadable:
        if key in done:
            stats["already"] += 1
        else:
            reject(key, UNREADABLE)
    for key in sorted(manifest, key=lambda k: (manifest[k], k)):
        if key in done:
            stats["already"] += 1
            continue
        path = found.get(key)
        if path is None:
            stats["missing"] += 1      # planned, not downloaded, not listed unreadable
            continue
        stats["objects"] += 1
        try:
            body = _read_object(path)
        except OSError:
            reject(key, UNREADABLE)
            continue
        try:
            doc = parse_drop(body)
        except Rejected as exc:
            reject(key, exc.args[0])
            continue
        guidance, skills, dropped = split_records(doc, manifest[key])
        writes: dict = {}
        for record in guidance:
            record = {k: v for k, v in record.items() if k != UPLOADED_KEY}
            rel = (census.EVENTS_DIR, record["ts"][:7], census.CLOUD_GUIDANCE_FILE)
            writes.setdefault(rel, []).append(record)
        for record in skills:
            rel = (census.EVENTS_DIR, record["ts"][:7], census.CLOUD_SKILLS_DIR,
                   f"{record['session']}.jsonl")
            writes.setdefault(rel, []).append(record)
        index = (SINK_DIR, INGESTED, f"{KEY_RE.fullmatch(key).group(1)}.txt")
        targets = {rel: _check_target(store, rel) for rel in [*writes, index]}
        for rel, records in sorted(writes.items()):
            if rel[-1] == census.CLOUD_GUIDANCE_FILE:
                lines = []
                for record in records:
                    if record["session"] not in sessions:
                        sessions.add(record["session"])
                        lines.append(_line(record))
                stats["guidance_added"] += len(lines)
            else:
                have, lines = _shard_ids(targets[rel]), []
                for record in records:
                    if record["id"] not in have:
                        have.add(record["id"])
                        lines.append(_line(record))
                stats["skills_added"] += len(lines)
            _append(targets[rel], lines)
        note = f" partial={dropped}" if dropped else ""
        _append(targets[index], [f"{key} {hashlib.sha256(body).hexdigest()}{note}"])
        done.add(key)
        stats["ingested"] += 1
        stats["partial"] += bool(dropped)
        stats["records_dropped"] += dropped
    return stats


def _summary(stats: dict) -> str:
    reasons = ", ".join(f"{r} {stats['reasons'][r]}" for r in REASONS if r in stats["reasons"])
    return (f"usage-sink apply: {stats['objects']} objects read: {stats['ingested']} ingested "
            f"({stats['partial']} partial, {stats['records_dropped']} invalid records dropped), "
            f"{stats['rejected']} rejected, {stats['already']} already recorded, "
            f"{stats['missing']} planned but missing, {stats['ignored']} other entries ignored; "
            f"{stats['guidance_added']} guidance lines and {stats['skills_added']} skill "
            f"lines added" + (f"; rejected by reason: {reasons}" if reasons else ""))


def _max_arg(value: str) -> int:
    if not _ascii_match(re.compile(r"[0-9]{1,7}", re.ASCII), value):
        raise argparse.ArgumentTypeError("--max takes a whole number")
    return int(value)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="print the keys to fetch")
    p.add_argument("--listing", required=True)
    p.add_argument("--store", required=True)
    p.add_argument("--max", type=_max_arg, default=DEFAULT_MAX)
    a = sub.add_parser("apply", help="ingest downloaded objects into the store")
    a.add_argument("--incoming", required=True)
    a.add_argument("--store", required=True)
    a.add_argument("--manifest", required=True)
    a.add_argument("--unreadable")
    args = parser.parse_args(argv)
    if args.command == "plan":
        try:
            planned, counts = plan(args.listing, args.store, args.max)
        except BadInput:
            print("usage-sink plan: the listing cannot be read", file=sys.stderr)
            return 2
        for key, stamp in planned:
            print(f"{key}\t{stamp}")
        print(f"planned={counts['planned']} backlog={counts['backlog']} "
              f"skipped_bad_date={counts['skipped_bad_date']} "
              f"skipped_size={counts['skipped_size']}", file=sys.stderr)
        return 0
    try:
        manifest = read_manifest(args.manifest)
        unreadable = read_unreadable(args.unreadable) if args.unreadable else []
    except BadInput:
        print("usage-sink apply: the manifest or unreadable list cannot be read",
              file=sys.stderr)
        return 2
    try:
        stats = apply(args.incoming, args.store, manifest, unreadable)
    except FileNotFoundError:
        print("usage-sink apply: the incoming or store directory cannot be read",
              file=sys.stderr)
        return 2
    except LinkRefused:
        print("usage-sink apply: refused to write through a link or onto a non-file",
              file=sys.stderr)
        return 1
    except OSError:
        print("usage-sink apply: a write failed", file=sys.stderr)
        return 1
    print(_summary(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
