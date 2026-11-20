#!/usr/bin/env python3
"""Summarize what one routine improve run measurably cost (#572 part 1).

An improve or guidance-improve run (scripts/propose_skill_edit.py,
scripts/propose_guidance_edit.py) spends model budget on its trials, its one
proposal call and, for a skill, skill-creator's trigger loop. Until
2026-11-02 none of that reached the results branch, so the allowance guard
could only reserve a constant per improve fire. The routine now runs

    python3 scripts/improve_cost.py summarize --results-dir "$RESULTS" \
      --run-id "$RUN_ID" --mode improve|guidance-improve --target <id> \
      --exit-code <0|1|2|none> --out "$COST/improve-cost/$RUN_ID/cost.json"

on EVERY exit and pushes that one file on `claude/eval-cost-<run id>`;
`scripts/ingest_routine_results.py` validates it with `check_record` (the
one schema, shared) and lands it at `improve-costs/<run id>.json` on
`persistent/eval-results`. Charging it in the guard is a follow-up (#572,
after at least 6 records); this module only measures.

What it reads, and nothing else (2026-11-02):

  * every regular, non-symlinked `summary.json` of at most 64 KiB under
    `<results>/runs/`, keeping only trial-scope ones
    (`usage.measured.scope == "trial"`): their `agent`/`judge`/`guard`
    dollars (only when every role that made a call says `cost_basis:
    "list"`; the rest are counted as `usd_unpriced_trials`), call counts,
    own run times, and weekly-window meter snapshots;
  * `<results>/proposal-<ts>.json`, the proposer's numbers-only record of its
    one `claude -p` call (`Runner.last_usage`), same cap and no-symlink rule
    (four keys before 2026-11-20, six since: the cache reads and writes);
  * the loop record `<results>/(guidance-)improvements/<target>/<ts>.json`
    (1 MiB cap): only `models.arm`, `models.proposal` and, for a skill, the
    trigger loop's `description_half.usage.total_calls`.

It never opens raw.json, a transcript, a patch, a report or a prompt, and
copies no string out of any file except a model id that fullmatches
MODEL_RE. Every other value it writes is a number, a bool, an enum, a
timestamp it re-formats, or the run id and target it was given and checked.
Precision is kept in full (no rounding); the meter span is the first and
last snapshot by PARSED time across all trials, because one trial's own
`meter_delta` spans only that trial and the proposal and trigger loop run
between trials, so they fall inside the bracket whenever a candidate is
measured (a run that stops before the candidate leaves them after the last
snapshot: uncovered).

Allowance points (schema 2, 2026-11-20): `points` prices what the record can
from token counts by type, with the weight table evals/usage-weights.lock pins
(harness/allowance_points.py): each trial whose every role has token counts,
and the proposal call when its counts and `models.proposal` are known.
`points.usd` is the dollars of those parts, so a reader charges the rest of
the record's dollars at `legacy_usd_per_point`; `complete` says nothing in
the trials or the proposal was left to dollars. The trigger loop's calls
report no tokens and are never in it. Null when nothing was priced from
tokens. Records written before (schema 1) carry no `points` and a four-key
`proposal`, and still validate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
import re
import stat
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import improve_outcomes  # noqa: E402  - stdlib-only: the shared name patterns

HARNESS = SCRIPTS.parent / "harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

import allowance_points  # noqa: E402  - the weight table evals/usage-weights.lock pins

SCHEMA_VERSION = 2
#: Schema 1 (2026-11-02 to 2026-11-20): no `points`, a four-key proposal.
SCHEMA_VERSIONS = (1, 2)
MODES = ("improve", "guidance-improve")
#: The target pattern per mode: the fire workflow's own (improve_outcomes.KINDS).
TARGET_RE = {mode: improve_outcomes.KINDS[mode]["name_re"] for mode in MODES}
RUN_ID_RE = re.compile(r"(?P<stamp>[0-9]{8}T[0-9]{6}Z)-[0-9a-f]{6}")
TIMESTAMP_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z")
#: A record time as written: seconds, optionally microseconds, always UTC.
AT_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,6})?Z")
#: A snapshot time as the harness writes it (ingest METER_FRACTION_RE allows
#: up to nanoseconds); parsed to microseconds, then re-formatted to AT_RE.
SNAPSHOT_AT_RE = re.compile(
    r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?Z")
USAGE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MODEL_RE = re.compile(r"claude-[a-z0-9][a-z0-9.-]{0,62}")
OUTCOMES = {0: "accepted", 1: "rejected", 2: "refused", None: "error"}
STAGES = ("none", "baseline", "proposal", "candidate")
DELTA_REASONS = ("measured", "window_reset", "fewer_than_two_snapshots")
SIDES = ("baseline", "candidate")
ROLES = ("agent", "judge", "guard")
PRICED_BASIS = "list"

#: Bounds (round-2 amendments, 2026-11-02): dollars 0..1000, tokens
#: 0..10^9, seconds 0..86400 (a day; the routine stops at 90 minutes),
#: counts 0..10^4, utilization 0..1.
MAX_USD = 1000
MAX_TOKENS = 10 ** 9
MAX_SECONDS = 86400
MAX_COUNT = 10 ** 4
#: Allowance points: 100 is the whole week; a record never charges more than
#: a hundred weeks, a sanity bound only.
MAX_POINTS = 10 ** 4
#: A sanity bound only (section 4, later, decides what gets charged): a
#: snapshot or the end time sits within [stamp - 5 min, stamp + 24 h] of the
#: run id's stamp, which the fire workflow mints before the routine starts.
BEFORE_STAMP = timedelta(minutes=5)
AFTER_STAMP = timedelta(hours=24)
#: resetsAt is epoch seconds of the weekly window's end: within a week after
#: the stamp, with a day's slack either side.
RESET_BEFORE = timedelta(days=1)
RESET_AFTER = timedelta(days=8)
TOLERANCE = 1e-9
SPAN_TOLERANCE = 1e-6

SUMMARY_CAP = 64 * 1024
PROPOSAL_CAP = 64 * 1024
LOOP_RECORD_CAP = 1024 * 1024
#: The ingest's cap on the pushed file; summarize refuses to write more.
RECORD_CAP = 4 * 1024

RECORD_KEYS = ("schema_version", "run_id", "mode", "target", "exit_code",
               "outcome", "stage_reached", "trial_summaries", "agent_calls",
               "judge_calls", "agent_usd", "judge_usd", "guard_usd",
               "usd_unpriced_trials", "sides", "proposal", "trigger_calls",
               "models", "busy_seconds", "span_seconds", "snapshots",
               "omitted", "first", "last", "delta", "delta_reason", "ended_at",
               "points")
SIDE_KEYS = ("trials", "usd")
PROPOSAL_TOKENS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
                   "cache_creation_input_tokens")
PROPOSAL_KEYS = ("calls", "usd") + PROPOSAL_TOKENS
POINTS_KEYS = ("points", "low", "high", "usd", "complete")
#: What schema 1 had, before `points` and the proposal's cache tokens.
RECORD_KEYS_V1 = RECORD_KEYS[:-1]
PROPOSAL_KEYS_V1 = PROPOSAL_KEYS[:4]
POINT_KEYS = ("at", "utilization", "resets_at")
MODEL_KEYS = ("arm", "proposal")


class Invalid(ValueError):
    """A record does not meet the schema. The message names a field and a
    reason, never a value."""


# ---------------------------------------------------------------------------
# Small typed checks.

def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _int(value, where, high, *, null=False):
    if value is None and null:
        return
    if not _is_int(value) or not 0 <= value <= high:
        raise Invalid(f"{where}: expected an integer in 0..{high}")


def _num(value, where, low, high, *, null=False):
    if value is None and null:
        return
    if not _is_number(value) or not low <= value <= high:
        raise Invalid(f"{where}: expected a number in {low}..{high}")


def _keys(value, where, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Invalid(f"{where}: expected exactly the keys {list(keys)}")


def parse_at(text: str) -> datetime | None:
    """A snapshot or record time, to the microsecond, or None."""
    if not isinstance(text, str):
        return None
    match = SNAPSHOT_AT_RE.fullmatch(text)
    if not match:
        return None
    try:
        moment = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    fraction = (match.group(2) or "")[:6].ljust(6, "0")
    return moment.replace(microsecond=int(fraction), tzinfo=timezone.utc)


def format_at(moment: datetime) -> str:
    base = moment.strftime("%Y-%m-%dT%H:%M:%S")
    return f"{base}.{moment.microsecond:06d}Z" if moment.microsecond else f"{base}Z"


def stamp_of(run_id: str) -> datetime:
    match = RUN_ID_RE.fullmatch(run_id) if isinstance(run_id, str) else None
    if not match:
        raise Invalid("run_id: not <YYYYMMDDTHHMMSSZ>-<6 hex>")
    return datetime.strptime(match.group("stamp"),
                             "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _in_window(moment: datetime, stamp: datetime) -> bool:
    return stamp - BEFORE_STAMP <= moment <= stamp + AFTER_STAMP


def _reset_ok(value, stamp: datetime) -> bool:
    if not _is_int(value):
        return False
    low = (stamp - RESET_BEFORE).timestamp()
    high = (stamp + RESET_AFTER).timestamp()
    return low <= value <= high


# ---------------------------------------------------------------------------
# The schema (shared by summarize, the ingest and, later, the guard).

def _check_point(point, where, stamp) -> datetime:
    _keys(point, where, POINT_KEYS)
    if not isinstance(point["at"], str) or not AT_RE.fullmatch(point["at"]):
        raise Invalid(f"{where}.at: not a UTC timestamp")
    moment = parse_at(point["at"])
    if moment is None or not _in_window(moment, stamp):
        raise Invalid(f"{where}.at: outside the run id's window")
    _num(point["utilization"], f"{where}.utilization", 0, 1)
    if not _reset_ok(point["resets_at"], stamp):
        raise Invalid(f"{where}.resets_at: not an epoch second within bounds")
    return moment


def check_record(doc) -> None:
    """Raise Invalid unless `doc` is a cost record exactly as `summarize`
    writes one: exact keys, every value typed and bounded, and the derived
    values (outcome, stage, sums, span, delta) consistent with their
    inputs. It never trusts a derived field it can recompute."""
    version = doc.get("schema_version") if isinstance(doc, dict) else None
    if not _is_int(version) or version not in SCHEMA_VERSIONS:
        _keys(doc, "record", RECORD_KEYS)
        raise Invalid("schema_version: unsupported")
    _keys(doc, "record", RECORD_KEYS if version == 2 else RECORD_KEYS_V1)
    stamp = stamp_of(doc["run_id"])
    if doc["mode"] not in MODES:
        raise Invalid("mode: not improve or guidance-improve")
    target = doc["target"]
    if not isinstance(target, str) or not TARGET_RE[doc["mode"]].fullmatch(target):
        raise Invalid("target: not a name of this mode")
    code = doc["exit_code"]
    if code is not None and (not _is_int(code) or code not in OUTCOMES):
        raise Invalid("exit_code: not 0, 1, 2 or null")
    if doc["outcome"] != OUTCOMES[code]:
        raise Invalid("outcome: disagrees with exit_code")
    if doc["stage_reached"] not in STAGES:
        raise Invalid("stage_reached: not a stage")
    for name in ("trial_summaries", "agent_calls", "judge_calls",
                 "usd_unpriced_trials", "snapshots", "omitted"):
        _int(doc[name], name, MAX_COUNT)
    _int(doc["trigger_calls"], "trigger_calls", MAX_COUNT, null=True)
    for role in ROLES:
        _num(doc[f"{role}_usd"], f"{role}_usd", 0, MAX_USD)
    _keys(doc["sides"], "sides", SIDES)
    for side in SIDES:
        _keys(doc["sides"][side], f"sides.{side}", SIDE_KEYS)
        _int(doc["sides"][side]["trials"], f"sides.{side}.trials", MAX_COUNT)
        _num(doc["sides"][side]["usd"], f"sides.{side}.usd", 0, MAX_USD)
    trials = {side: doc["sides"][side]["trials"] for side in SIDES}
    if sum(trials.values()) != doc["trial_summaries"]:
        raise Invalid("sides: trial counts do not add up to trial_summaries")
    if doc["usd_unpriced_trials"] > doc["trial_summaries"]:
        raise Invalid("usd_unpriced_trials: more than trial_summaries")
    side_usd = sum(doc["sides"][side]["usd"] for side in SIDES)
    role_usd = sum(doc[f"{role}_usd"] for role in ROLES)
    if abs(side_usd - role_usd) > TOLERANCE:
        raise Invalid("sides: dollars do not add up to agent+judge+guard")
    proposal = doc["proposal"]
    if proposal is not None:
        _keys(proposal, "proposal", PROPOSAL_KEYS if version == 2 else PROPOSAL_KEYS_V1)
        _int(proposal["calls"], "proposal.calls", MAX_COUNT)
        # A call that failed or timed out was still billed: usd and tokens
        # are null then (#577, the 2026-11-02 review).
        _num(proposal["usd"], "proposal.usd", 0, MAX_USD, null=True)
        for name in proposal:
            if name in PROPOSAL_TOKENS:
                _int(proposal[name], f"proposal.{name}", MAX_TOKENS, null=True)
    stage = doc["stage_reached"]
    expected = ("candidate" if trials["candidate"] else
                "none" if not trials["baseline"] else
                "proposal" if proposal is not None and proposal["calls"] else
                "baseline")
    if stage != expected:
        raise Invalid("stage_reached: disagrees with the trial counts")
    _keys(doc["models"], "models", MODEL_KEYS)
    for name in MODEL_KEYS:
        value = doc["models"][name]
        if value is not None and (not isinstance(value, str)
                                  or not MODEL_RE.fullmatch(value)):
            raise Invalid(f"models.{name}: not a model id")
    _num(doc["busy_seconds"], "busy_seconds", 0, MAX_SECONDS, null=True)
    _num(doc["span_seconds"], "span_seconds", 0, MAX_SECONDS, null=True)
    first, last = doc["first"], doc["last"]
    if (first is None) != (last is None):
        raise Invalid("first/last: both or neither")
    if first is None:
        if doc["span_seconds"] is not None or doc["delta"] is not None:
            raise Invalid("span_seconds/delta: set without two snapshots")
        if doc["delta_reason"] != "fewer_than_two_snapshots" or doc["snapshots"] >= 2:
            raise Invalid("delta_reason: disagrees with the snapshot count")
    else:
        if doc["snapshots"] < 2:
            raise Invalid("first/last: set with fewer than two snapshots")
        start = _check_point(first, "first", stamp)
        end = _check_point(last, "last", stamp)
        if start > end:
            raise Invalid("first/last: first is after last")
        span = (end - start).total_seconds()
        if doc["span_seconds"] is None or abs(doc["span_seconds"] - span) > SPAN_TOLERANCE:
            raise Invalid("span_seconds: disagrees with last.at - first.at")
        if first["resets_at"] == last["resets_at"]:
            if doc["delta_reason"] != "measured" or not _is_number(doc["delta"]) \
                    or abs(doc["delta"] - (last["utilization"] - first["utilization"])) > TOLERANCE:
                raise Invalid("delta: disagrees with last - first")
        elif doc["delta_reason"] != "window_reset" or doc["delta"] is not None:
            raise Invalid("delta: must be null across a window reset")
    ended = doc["ended_at"]
    if not isinstance(ended, str) or not AT_RE.fullmatch(ended) \
            or not _in_window(parse_at(ended), stamp):
        raise Invalid("ended_at: not a UTC timestamp in the run id's window")
    if version == 2:
        _check_points(doc)


def _check_points(doc: dict) -> None:
    """`points`: null, or its numbers bounded, `low <= points <= high`, and
    `usd` no more than the dollars the record holds."""
    points = doc["points"]
    if points is None:
        return
    _keys(points, "points", POINTS_KEYS)
    for name in ("points", "low", "high"):
        _num(points[name], f"points.{name}", 0, MAX_POINTS)
    if not points["low"] - TOLERANCE <= points["points"] <= points["high"] + TOLERANCE:
        raise Invalid("points: not within low..high")
    _num(points["usd"], "points.usd", 0, MAX_USD)
    proposal = doc["proposal"]
    held = sum(doc[f"{role}_usd"] for role in ROLES) + (
        proposal["usd"] if proposal is not None and proposal["usd"] is not None else 0)
    if points["usd"] > held + TOLERANCE:
        raise Invalid("points.usd: more than the record's dollars")
    if not isinstance(points["complete"], bool):
        raise Invalid("points.complete: not a bool")


# ---------------------------------------------------------------------------
# Reading the results tree.

def read_capped(path: Path, cap: int) -> bytes | None:
    """The bytes of a regular, non-symlinked file of at most `cap` bytes,
    else None."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > cap:
            return None
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(cap + 1)
    finally:
        os.close(fd)
    return data if len(data) <= cap else None


def _load(path: Path, cap: int):
    data = read_capped(path, cap)
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None


def summary_paths(runs: Path) -> list[Path]:
    """Every `summary.json` under `runs`, never through a symlinked
    directory (os.walk does not follow links)."""
    out = []
    if runs.is_symlink() or not runs.is_dir():
        return out
    for root, dirs, files in os.walk(runs, followlinks=False):
        dirs.sort()
        if "summary.json" in files:
            out.append(Path(root) / "summary.json")
    return sorted(out)


def side_of(rel: Path, mode: str) -> str | None:
    """Which side a trial summary measured, from its path below runs/:
    skill `runs/<side>/<skill>/<ts>/...` (propose_skill_edit.run_paths),
    guidance `runs/<ts>/<side>/<fixture>/trial-<k>/...`
    (propose_guidance_edit.trial_dir)."""
    parts = rel.parts
    index = 0 if mode == "improve" else 1
    side = parts[index] if len(parts) > index else None
    return side if side in SIDES else None


def _trial_usd(measured: dict) -> dict | None:
    """{role: usd} when every role that made a call is priced at list,
    else None (the trial counts as unpriced)."""
    out = {}
    for role in ROLES:
        block = measured.get(role)
        if not isinstance(block, dict):
            return None
        calls = block.get("calls")
        if not _is_int(calls):
            return None
        if calls == 0:
            out[role] = 0
            continue
        cost = block.get("cost_usd")
        if block.get("cost_basis") != PRICED_BASIS or not _is_number(cost) \
                or not 0 <= cost <= MAX_USD:
            return None
        out[role] = cost
    return out


def _seconds(measured: dict) -> float | None:
    times = []
    for name in ("started_at", "ended_at"):
        value = measured.get(name)
        try:
            times.append(datetime.strptime(value, USAGE_TIME_FORMAT))
        except (TypeError, ValueError):
            return None
    span = (times[1] - times[0]).total_seconds()
    return span if span >= 0 else None


def collect_trials(results: Path, mode: str, stamp: datetime) -> dict:
    tally = {"trials": {side: 0 for side in SIDES},
             "side_usd": {side: 0 for side in SIDES},
             "role_usd": {role: 0 for role in ROLES},
             "unpriced": 0, "agent_calls": 0, "judge_calls": 0,
             "busy": 0, "busy_known": False, "omitted": 0, "points": set(),
             "token_blocks": [], "token_usd": 0, "token_trials": 0}
    runs = results / "runs"
    for path in summary_paths(runs):
        side = side_of(path.parent.relative_to(runs), mode)
        doc = _load(path, SUMMARY_CAP)
        usage = doc.get("usage") if isinstance(doc, dict) else None
        measured = usage.get("measured") if isinstance(usage, dict) else None
        if side is None or not isinstance(measured, dict) \
                or measured.get("scope") != "trial":
            continue
        tally["trials"][side] += 1
        for role in ("agent", "judge"):
            block = measured.get(role)
            calls = block.get("calls") if isinstance(block, dict) else None
            if _is_int(calls) and 0 <= calls <= MAX_COUNT:
                tally[f"{role}_calls"] += calls
        usd = _trial_usd(measured)
        if usd is None:
            tally["unpriced"] += 1
        else:
            for role, cost in usd.items():
                tally["role_usd"][role] += cost
                tally["side_usd"][side] += cost
        if _from_tokens(measured):
            tally["token_blocks"].append(measured)
            tally["token_trials"] += 1
            tally["token_usd"] += sum(usd.values()) if usd is not None else 0
        seconds = _seconds(measured)
        if seconds is not None:
            tally["busy"] += seconds
            tally["busy_known"] = True
        meter = measured.get("meter")
        if not isinstance(meter, dict):
            continue
        omitted = meter.get("omitted")
        if _is_int(omitted) and 0 <= omitted <= MAX_COUNT:
            tally["omitted"] += omitted
        for shot in meter.get("snapshots") or []:
            point = _snapshot_point(shot, stamp)
            if point is not None:
                tally["points"].add(point)
    return tally


def _from_tokens(measured: dict) -> bool:
    """Whether every role of one trial that made a call has token counts the
    pinned table prices (no legacy rate is given, so any other role reads
    as unpriced)."""
    estimate = allowance_points.estimate_blocks([measured])
    return not estimate["unpriced_roles"] and not estimate["legacy_roles"]


def _proposal_records(proposal: dict | None, model: str | None) -> list | None:
    """The package records of the proposal call, [] when there was none, or
    None when it cannot be priced from tokens (a schema 1 file, a failed
    call, no model id, or a model the table does not price)."""
    if proposal is None or not proposal["calls"]:
        return []
    if model is None or any(proposal.get(name) is None for name in PROPOSAL_TOKENS):
        return None
    block = {"calls": proposal["calls"], "models": {model: {
        name: proposal[name] for name in PROPOSAL_TOKENS}}}
    estimate = allowance_points.estimate_blocks([{"agent": block}])
    return None if estimate["unpriced_roles"] or estimate["legacy_roles"] else [block]


def allowance(tally: dict, proposal: dict | None, model: str | None) -> dict | None:
    """The record's `points` (module docstring, schema 2), or None when
    nothing was priced from tokens."""
    blocks = list(tally["token_blocks"])
    usd = tally["token_usd"]
    proposal_blocks = _proposal_records(proposal, model)
    if proposal_blocks:
        blocks.append({"agent": proposal_blocks[0]})
        usd += proposal["usd"] or 0
    if not blocks:
        return None
    estimate = allowance_points.estimate_blocks(blocks)
    trials = sum(tally["trials"].values())
    return {"points": estimate["points"], "low": estimate["low"],
            "high": estimate["high"], "usd": usd,
            "complete": tally["token_trials"] == trials and proposal_blocks is not None}


def _snapshot_point(shot, stamp: datetime) -> tuple | None:
    """(time, utilization, resets_at) of one snapshot's weekly window, or
    None when any part is unreadable or out of bounds."""
    if not isinstance(shot, dict):
        return None
    moment = parse_at(shot.get("at"))
    info = shot.get("info")
    windows = info.get("unifiedWindows") if isinstance(info, dict) else None
    week = windows.get("seven_day") if isinstance(windows, dict) else None
    if moment is None or not _in_window(moment, stamp) or not isinstance(week, dict):
        return None
    utilization, reset = week.get("utilization"), week.get("resetsAt")
    if not _is_number(utilization) or not 0 <= utilization <= 1 \
            or not _reset_ok(reset, stamp):
        return None
    return moment, utilization, reset


def _one(paths: list[Path]) -> Path | None:
    """The one file, or None when there is none or the choice is ambiguous."""
    return paths[0] if len(paths) == 1 else None


def _timestamped(directory: Path, prefix: str) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir()
                  if p.name.startswith(prefix) and p.name.endswith(".json")
                  and TIMESTAMP_RE.fullmatch(p.name[len(prefix):-len(".json")]))


def read_proposal(results: Path) -> dict | None:
    """`proposal-<ts>.json` (the proposer's `last_usage`), every field
    type-checked and copied by name, or None."""
    path = _one(_timestamped(results, "proposal-"))
    doc = _load(path, PROPOSAL_CAP) if path else None
    if not isinstance(doc, dict) or set(doc) not in (set(PROPOSAL_KEYS),
                                                      set(PROPOSAL_KEYS_V1)):
        return None
    # A file from before the cache tokens were kept reads them as unknown.
    out = {"calls": doc["calls"], "usd": doc["usd"],
           **{name: doc.get(name) for name in PROPOSAL_TOKENS}}
    try:
        _int(out["calls"], "calls", MAX_COUNT)
        _num(out["usd"], "usd", 0, MAX_USD, null=True)
        for name in PROPOSAL_TOKENS:
            _int(out[name], name, MAX_TOKENS, null=True)
    except Invalid:
        return None
    return out


def _model(value) -> str | None:
    """A model id, or a list holding exactly one (guidance records every
    arm model the fixtures use); anything else is null."""
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value if isinstance(value, str) and MODEL_RE.fullmatch(value) else None


def read_loop_record(results: Path, mode: str, target: str) -> dict:
    """models.arm / models.proposal and, for a skill, the trigger loop's
    call count, from the loop's own record; nulls when it is absent."""
    folder = "improvements" if mode == "improve" else "guidance-improvements"
    path = _one(_timestamped(results / folder / target, ""))
    doc = _load(path, LOOP_RECORD_CAP) if path else None
    doc = doc if isinstance(doc, dict) else {}
    models = doc.get("models") if isinstance(doc.get("models"), dict) else {}
    half = doc.get("description_half")
    usage = half.get("usage") if isinstance(half, dict) else None
    calls = usage.get("total_calls") if isinstance(usage, dict) else None
    return {"models": {"arm": _model(models.get("arm")),
                       "proposal": _model(models.get("proposal"))},
            "trigger_calls": calls if _is_int(calls) and 0 <= calls <= MAX_COUNT else None}


# ---------------------------------------------------------------------------
# summarize

def summarize(results: Path, run_id: str, mode: str, target: str,
              exit_code: int | None, now: datetime) -> dict:
    stamp = stamp_of(run_id)
    if mode not in MODES or not isinstance(target, str) \
            or not TARGET_RE[mode].fullmatch(target):
        raise Invalid("mode/target: not a valid pair")
    tally = collect_trials(results, mode, stamp)
    proposal = read_proposal(results)
    loop = read_loop_record(results, mode, target)
    points = sorted(tally["points"], key=lambda p: (p[0], p[1], p[2]))
    trials = tally["trials"]
    record = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "mode": mode,
        "target": target, "exit_code": exit_code, "outcome": OUTCOMES[exit_code],
        "stage_reached": ("candidate" if trials["candidate"] else
                          "none" if not trials["baseline"] else
                          "proposal" if proposal is not None and proposal["calls"] else
                          "baseline"),
        "trial_summaries": sum(trials.values()),
        "agent_calls": tally["agent_calls"], "judge_calls": tally["judge_calls"],
        **{f"{role}_usd": tally["role_usd"][role] for role in ROLES},
        "usd_unpriced_trials": tally["unpriced"],
        "sides": {side: {"trials": trials[side], "usd": tally["side_usd"][side]}
                  for side in SIDES},
        "proposal": proposal, "trigger_calls": loop["trigger_calls"],
        "models": loop["models"],
        "busy_seconds": (tally["busy"] if tally["busy_known"]
                         and tally["busy"] <= MAX_SECONDS else None),
        "span_seconds": None, "snapshots": len(points),
        "omitted": min(tally["omitted"], MAX_COUNT),
        "first": None, "last": None, "delta": None,
        "delta_reason": "fewer_than_two_snapshots",
        "ended_at": format_at(now.astimezone(timezone.utc)),
        "points": allowance(tally, proposal, loop["models"]["proposal"]),
    }
    if len(points) >= 2:
        (start, u0, r0), (end, u1, r1) = points[0], points[-1]
        record["first"] = {"at": format_at(start), "utilization": u0, "resets_at": r0}
        record["last"] = {"at": format_at(end), "utilization": u1, "resets_at": r1}
        record["span_seconds"] = (end - start).total_seconds()
        if r0 == r1:
            record["delta"], record["delta_reason"] = u1 - u0, "measured"
        else:
            record["delta_reason"] = "window_reset"
    check_record(record)
    return record


def encode(record: dict) -> bytes:
    return (json.dumps(record, indent=1, sort_keys=False) + "\n").encode("utf-8")


def parse_exit_code(text: str) -> int | None:
    """0, 1 or 2; `none` or anything else is an error outcome (null)."""
    return int(text) if text in ("0", "1", "2") else None


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("summarize")
    p.add_argument("--results-dir", required=True, type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--mode", required=True, choices=MODES)
    p.add_argument("--target", required=True)
    p.add_argument("--exit-code", required=True)
    p.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        record = summarize(args.results_dir, args.run_id, args.mode, args.target,
                           parse_exit_code(args.exit_code),
                           now or datetime.now(timezone.utc))
        data = encode(record)
        if len(data) > RECORD_CAP:
            raise Invalid(f"record: over {RECORD_CAP} bytes")
    except Invalid as exc:
        # Fixed field names only: no value from the tree reaches the log.
        print(f"improve_cost: not written: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    print(f"improve_cost: wrote {args.out} ({record['outcome']}, "
          f"{record['trial_summaries']} trials, {record['snapshots']} snapshots)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
