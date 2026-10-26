#!/usr/bin/env python3
"""Write `gates/latest.json`: the retirement verdict of every skill (#70).

  compute_gates.py --results-tree DIR --roster evals/roster.yml
                   --policy evals/gate-policy.yml --as-of TIME --out FILE
                   [--ingest-times FILE --fires FILE --main-sha SHA
                    [--main-repo DIR]]          (VOUCH_KEY in the environment)
                   [--evals-dir DIR] [--registry NAME=PATH ...]

The results tree is laid out like `persistent/eval-results`:

  results/<skill>/<timestamp>/[<fixture>/]<arm>[/trial-<k>]/summary.json
  routine-results/<run id>/<skill>/<timestamp>/[<fixture>/]<arm>[/trial-<k>]/summary.json

with `report.md` beside each `<timestamp>`'s arms. Paths below the prefix are
parsed by `ingest_routine_results.parse_result_path`, the parser the ingester
validates routine branches with. `guidance/` subjects are left out (a later
part of #70/#124).

THE CONTENT ON MAIN. Each skill's fixtures are enumerated from `--evals-dir`
(`run_eval.resolve_fixture_dirs`: `<skill>/fixture.yaml`, or every
`<skill>/<fixture>/fixture.yaml`), and each fixture's expected digest is
`run_eval.fixture_digest`, the function run_eval records it with. The
expected `tested_digest` is the skill's copy in a `--registry` checkout (the
fixture's `registry:` names which; else the one copy across them), digested
as harness/delivery.py digests a registry skill. Only `--registry` flags
count, never an environment or sibling default, so the expected content is
what the caller checked out. No registry, or no unique copy, leaves it
unknown, and every cell of the skill is then insufficient.

A VALIDATED ARM RUN is one arm of one `<timestamp>[/<fixture>]` whose summary
parses as a JSON object naming the skill and carrying an `aggregate` and a
`run` block, whose role is `with` or `without` (the summary's `role`, else
`run_eval._ROLES` of the arm name), whose requested model is recorded
(`run_eval._arm_model`), whose trial summaries parse and have the shape
run_eval writes (`gates.trial_record`), are numbered 1 to n and agree with
the arm summary's `n` and `errors` (one trial and no trial files is `n` 1),
and whose `report.md` exists.
Everything else is counted under `skipped` by reason. The arms are
independent samples (harness/gates.py), so an arm run needs no partner. The
tree is untrusted data: it is read, never executed; NaN and Infinity are
refused on read and on write.

AS OF. `--as-of` is required: the time the evaluation stands at (the
workflow passes the results commit's committer time), as
`YYYYMMDDTHHMMSSZ` or an ISO 8601 time with its offset. A run stamped later
is not read (`skipped`: "after as-of"), so a future-dated run cannot choose a
cell's pool, its context key or its order.

READS ARE BOUNDED (round 5, B5). Every file is read with lstat and
O_NOFOLLOW, only when it is a regular file, and at most the ingester's
SIZE_CAPS (VOUCH_CAP for vouch.json) plus one byte; a symlink is
unreadable and a larger file is skipped with a size reason. An arm run's
JSON, content digest and Git blob ids all come from one read of its files;
the MAC check reads a routine run's first-ingest files again, and each arm
run's bytes must be the same blobs, so what is judged is what verified.

DUPLICATES (round 5, B3). Copies are matched by their arm summary bytes,
their set of trial summary bytes, and their (skill, fixture, requested
model, role, timestamp). Vouched runs are taken first, then by path, so an
unvouched copy never displaces a vouched run. A copy within the same cell
key (skill, fixture, model, role) and the same tree (`results/` or
`routine-results/`) is a plain duplicate (`skipped`: "duplicate arm run").
The same bytes in another cell or the other tree are POLLUTION: the copy is
dropped ("duplicate arm run from another cell or tree") and the cell the
bytes came from is listed in `polluted`, which harness/gates.py makes at
most `insufficient`. Copying a run's bytes can then only stall its cell,
never move its verdict. The model is in the key because one routine run may
stamp every model's arms with one `--timestamp`.

ROUTINE EVIDENCE IS VOUCHED FOR, failing closed (rounds 3 to 5). A routine
run's run id is self-chosen, so a `routine-results/<run id>` counts only
when:

  * `--ingest-times` (scripts/routine_ingest_times.py: each run id's FIRST
    ingest commit, its time and the Git blob id of every file it added),
    `--fires` (routine-eval-fire.yml's Actions runs, `FIRE_KEYS`, with the
    run id from each run's `routine-vouch` annotation; part 2's workflow
    fetches them) and `--main-sha` (main's commit, in `--main-repo`, which
    must be a full clone: part 2 checks it out with `fetch-depth: 0`, or the
    ancestry check cannot see a fire's commit) are all given; without them
    routine results are skipped;
  * its MAC verifies HERE (round 6, R6-1): its first ingest added a
    `vouch.json` that is still those bytes and is exactly the ingester's
    canonical `{"mac": <64 hex>}` line, every other file that ingest added
    is still the blob it added (round 5, B2), and the MAC equals
    `write_vouch.mac(write_vouch.derive_nonce(VOUCH_KEY, run id), those
    files)`, compared with `hmac.compare_digest`. VOUCH_KEY comes from the
    environment only, never argv, so the job that runs this needs the
    VOUCH_KEY secret in its env; without it no routine run counts
    (`NO_KEY`). Anyone able to write persistent/eval-results can squat a
    public run id, but not with a MAC this check accepts. A file edited in
    place since its first ingest makes the MAC unverifiable, so the whole
    run is skipped;
  * only files its first ingest added are read: an arm run with a file
    added later is skipped and the rest are judged without it, so a later
    push can neither rewrite nor disqualify what the first ingest held, and
    a fired arm added later is missing, not read (ingest_routine_results.py's
    `place` is write-once per run id anyway);
  * its run id is a real UTC time within the 48 hours before that first
    ingest, and every arm timestamp in it a real time within 2 hours of it;
  * it holds one fixture and one requested model, at most one arm run per
    role;
  * exactly ONE TRUSTED fire names its run id (round 5, B4): a first
    attempt (`run_attempt` 1) that concluded `success`, on `main`, by
    `workflow_dispatch`, from `FIRE_PATH`, at a commit that is an ancestor
    of `--main-sha`. Untrusted fires are set aside first, so they can
    neither vouch nor make a run id ambiguous; two trusted fires naming one
    run id vouch for neither, a skip, never a refusal of the evaluation.
    That fire's display title (`FIRE_TITLE_RE`, the workflow's `run-name`)
    names mode `eval`, this fixture's committed path, this model, and the
    arms and trials the run holds (`both` means both roles; every arm has
    `trials` trials). An eval title with no model is not trusted (round 7,
    R7-3): it cannot say which cell it was for, and the roster's first arm
    today need not be the one it ran.

A vouched run is ordered, and judged against `--as-of`, by its fire's
creation time, which no run can choose. Fires dispatched before the
workflow gained its `run-name`, annotation and keyed vouch vouch for
nothing, so routine evidence from before that change counts toward
nothing; it restarts from the first fire after it.

MISSING EVIDENCE BLOCKS NO-BENEFIT (rounds 6 and 7). Listed in `unlanded`,
unless gate-policy.yml's `waived_fires` names the run id:

  * every trusted fire (the filter above; ambiguous ones included) created
    by `--as-of` whose run id has no vouched run that `--as-of` kept (a
    vouched run stamped, ordered or first ingested after `--as-of` did not
    land, rounds 7 and 8),
    mapped from its title to its cell (skill and fixture from its fixture
    path, its model); a fire whose fixture is not on main gates no cell and
    is left out;
  * every run whose MAC verified but that no one trusted fire names (its
    fire re-run, deleted, cancelled or doubled since; R7-1), in its own cell;
  * a fire that would be trusted but for its conclusion, once it carries a
    run id (its `routine-vouch` notice came just before the fire API call,
    so a fire cancelled or failed after it may have started the routine;
    round 9, R9-3): it must land like a trusted one, and still vouches for
    nothing;
  * every ingested run id whose first ingest has no valid vouch.json (a
    squat, R9-3): in its cell when its arm runs name one, else under
    `needs_waiver` only.

harness/gates.py refuses `no-benefit` for that cell: `insufficient` once
overdue (a fire older than `unlanded_fire_grace_hours`; an orphaned run
always), at most `no-benefit-pending` before. Overdue entries are repeated
under `needs_waiver`.

THE SENTINEL (round 8, R8-1). Deleting the newest fires leaves no gap below
them, so the sequence needs an upper end no one can delete in time: a
trusted `mode=sentinel` fire of routine-eval-fire.yml (validates, publishes
nothing to the routine, succeeds; `sentinel_number`) created at or after
`--as-of`. Any gap in the workflow's `run_number`s from gate-policy.yml's
`fire_sequence_from` up to the lowest such sentinel's (less
`waived_fire_numbers`) is listed in `missing_fire_numbers` and makes every
no-benefit cell `insufficient`; with no such sentinel every no-benefit cell
is `insufficient` too (`sentinel_run_number` null). Part 2 dispatches the
sentinel, waits for it to succeed, then computes with `--as-of` = the
scheduled run's own `created_at` (never a commit date, and before the
sentinel's), giving `--fires` every run of the workflow, each record read
from `/actions/runs/{id}/attempts/1`, so a re-run never changes a record;
`run_attempt` 1 stays required. Blocking an ingest, squatting a run id, or
re-running or deleting a fire can then only stall a cell, never steer it
toward retirement.

AS OF, AGAIN (round 8, R8-2): a vouched run counts only once its first
ingest (`--ingest-times`) is at or before `--as-of`; one ingested later was
not landed then (`dropped_by_as_of`), so its fire blocks by the grace rule.
A stale or backdated `--as-of` can only hide runs whose fires then block,
and a squatted future ingest time refuses nothing.

`results/` IS NOT VOUCHED FOR: persistent/eval-results is guarded against
deletion only, so a direct push could add to it. Its runs count, but a cell
holding one can show `benefit` and never `no-benefit` (harness/gates.py).

ONE SKILL'S FAILURE IS ITS OWN: an exception while classifying a skill
(MemoryError included) makes that skill `insufficient`, naming the
exception's type (never its message), and the others are still decided.

AFTER harness/gates.py's verdict, ONE RETIREMENT PER EVALUATION: of several
skills whose verdict is `retire`, only the one with the most arm runs (then
the first by name) keeps it; the rest are `retire-pending`. Nothing is read
from an earlier gates file: confirmation is harness/gates.py's, at two looks,
and a standing retirement belongs to part 2, which reads the open pull
requests from GitHub.

Deterministic: sorted keys, sorted
walks, no clock.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import context  # noqa: E402
import delivery  # noqa: E402
import gates  # noqa: E402
import harness_repo  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import run_eval  # noqa: E402
import write_vouch  # noqa: E402

PREFIXES = ("results", "routine-results")
ROUTINE = "routine-results"
#: A routine run id as routine-eval-fire.yml makes it.
RUN_ID_RE = re.compile(r"([0-9]{8}T[0-9]{6}Z)-[0-9a-f]{6}")
#: The keys of one `--fires` entry: the Actions run's own fields, and the
#: run id its `routine-vouch` annotation published (null when it has none).
FIRE_KEYS = frozenset(("id", "created_at", "conclusion", "head_branch", "event",
                       "display_title", "path", "head_sha", "run_attempt", "run_number",
                       "run_id"))
FIRE_PATH = ".github/workflows/routine-eval-fire.yml"
#: routine-eval-fire.yml's `run-name`, whole.
FIRE_TITLE_RE = re.compile(r"Fire eval routine: mode=(eval|scaffold|improve|sentinel) "
                           r"fixture=(\S*) model=(\S*) arms=(both|with|without) "
                           r"trials=([1-9][0-9]?)")
#: An arm id as routine-eval-fire.yml accepts its `model` input.
FIRE_MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
#: A Git object id, SHA-1 or SHA-256.
OID_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
ARMS = {"both": {"with", "without"}, "with": {"with"}, "without": {"without"}}
VOUCH_FILE = "vouch.json"
#: What the ingester stages as a run's vouch.json once its MAC verified.
VOUCH_RE = re.compile(r'\{"mac": ?"[0-9a-f]{64}"\}\n?')
#: The most bytes read of each file kind: the ingester's own caps.
READ_CAPS = {**ingest.SIZE_CAPS, VOUCH_FILE: ingest.VOUCH_CAP}
INGEST_WINDOW = timedelta(hours=48)
ARM_WINDOW = timedelta(hours=2)
NO_TRUST = "routine results without --ingest-times, --fires and --main-sha"
NO_KEY = "VOUCH_KEY is not set, so no routine run's MAC can be verified"


def canonical_vouch(mac: str) -> bytes:
    """The vouch.json bytes the ingester stages for `mac` (round 6, R6-4)."""
    return (json.dumps({"mac": mac}) + "\n").encode("ascii")


def _refuse_constant(name):
    raise ValueError(f"{name} is not JSON")


def _read_bytes(path: Path, cap: int) -> tuple:
    """(bytes, None) of `path`, a regular file read without following a
    symlink and of at most `cap` bytes; else (None, "unreadable" or
    "oversize"). At most `cap` + 1 bytes are ever read (round 5, B5)."""
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return None, "unreadable"
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return None, "unreadable"
            chunks, left = [], cap + 1
            while left > 0:
                chunk = os.read(fd, min(left, 1 << 16))
                if not chunk:
                    break
                chunks.append(chunk)
                left -= len(chunk)
        finally:
            os.close(fd)
    except OSError:
        return None, "unreadable"
    data = b"".join(chunks)
    return (None, "oversize") if len(data) > cap else (data, None)


def _parse(data):
    """A JSON object from `data`, or None."""
    if data is None:
        return None
    try:
        doc = json.loads(data.decode("utf-8"), parse_constant=_refuse_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    return doc if isinstance(doc, dict) else None


def _read(path: Path, cap: int = READ_CAPS["summary.json"]):
    """The JSON object in `path` (`_read_bytes`), or None."""
    return _parse(_read_bytes(path, cap)[0])


def blob_ids(data: bytes) -> dict:
    """{40: SHA-1, 64: SHA-256} Git blob ids of `data`."""
    header = b"blob %d\0" % len(data)
    return {40: hashlib.sha1(header + data).hexdigest(),
            64: hashlib.sha256(header + data).hexdigest()}


def _summaries(tree: Path) -> dict:
    """{(run dir, skill, timestamp, fixture, arm): {"summary", "trials"}}."""
    arms: dict = {}
    for prefix in PREFIXES:
        root = tree / prefix
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("summary.json")):
            parts = path.relative_to(root).parts
            head, parts = (parts[:1], parts[1:]) if prefix == "routine-results" else ((), parts)
            try:
                found = ingest.parse_result_path("/".join(parts))
            except ingest.Rejected:
                continue
            if found["key"].split("/")[0] == "guidance":
                continue
            run_dir = "/".join((prefix, *head, found["key"], found["timestamp"]))
            entry = arms.setdefault((run_dir, found["key"], found["timestamp"],
                                     found["fixture"], found["arm"]),
                                    {"summary": None, "trials": []})
            if found["trial"] is None:
                entry["summary"] = path
            else:
                entry["trials"].append((found["trial"], path))
    return arms


def _fixture_class(evals_dir: Path, skill: str, fixture, trials: list) -> tuple:
    """(judge-carried, has objective checks or None when unknown)."""
    path = evals_dir / skill / (fixture or "") / run_eval.FIXTURE_FILE
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        doc = None
    if isinstance(doc, dict):
        return (bool(run_eval._judge_is_pairwise(doc) or not doc.get("objective_checks")),
                bool(doc.get("objective_checks")))
    return any(t.get("pairwise") for t in trials), None


def _count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _string(value):
    return value if isinstance(value, str) and value else None


def _validate(tree: Path, key: tuple, entry: dict, evals_dir: Path):
    """(arm run record, None) or (None, the reason it is skipped)."""
    run_dir, skill, timestamp, fixture, arm = key
    cap = READ_CAPS["summary.json"]
    raw, problem = _read_bytes(entry["summary"], cap) if entry["summary"] else (None, None)
    if problem == "oversize":
        return None, "arm summary over its size cap"
    summary = _parse(raw)
    if summary is None:
        return None, "no readable arm summary"
    if not isinstance(summary.get("aggregate"), dict):
        return None, "no aggregate block"
    if not isinstance(summary.get("run"), dict):
        return None, "no run block"
    if summary.get("skill") != skill:
        return None, "summary names another skill"
    subject, context_block = summary.get("context_subject"), summary.get("arm_context")
    if any(field in summary and not isinstance(summary[field], str)
           for field in ("role", "fixture_digest")) \
            or ("fixture_digest" in summary
                and not ingest.DIGEST_RE.fullmatch(summary["fixture_digest"])) \
            or any(block is not None and not isinstance(block, dict)
                   for block in (subject, context_block, summary.get("harness"))):
        return None, "malformed arm summary"
    role = summary.get("role") or run_eval._ROLES.get(arm)
    if role not in ("with", "without"):
        return None, "not a with or without arm"
    numbers = sorted(k for k, _ in entry["trials"])
    if numbers != list(range(1, len(numbers) + 1)):
        return None, "trial files are not numbered 1 to n"
    trial_paths = [p for _, p in sorted(entry["trials"])]
    trial_reads = [_read_bytes(p, cap) for p in trial_paths]
    if any(problem == "oversize" for _, problem in trial_reads):
        return None, "trial summary over its size cap"
    trials = [_parse(data) for data, _ in trial_reads] or [summary]
    if any(t is None for t in trials):
        return None, "unreadable trial summary"
    errors = sum(1 for t in trials if t.get("error"))
    if summary.get("n") != len(trials) or not _count(summary.get("n")) or (
            trial_paths and (not _count(summary.get("errors")) or summary["errors"] != errors
                             or ("scored" in summary
                                 and summary["scored"] != len(trials) - errors))):
        return None, "arm summary's n or errors disagree with its trial files"
    model = run_eval._arm_model([summary, *trials])
    if not isinstance(model, str) or not model:
        return None, "no requested arm model"
    report = f"{run_dir}/report.md"
    report_bytes, problem = _read_bytes(tree / report, READ_CAPS["report.md"])
    if problem == "oversize":
        return None, "report over its size cap"
    if report_bytes is None:
        return None, "no report"
    try:
        records = [gates.trial_record(t) for t in trials]
    except gates.MalformedSummary:
        return None, "malformed trial summary"
    context_digest = None
    if isinstance(context_block, dict) and _string(context_block.get("skills_digest")) \
            and _string(context_block.get("guidance_digest")):
        context_digest = (f"{context_block['skills_digest']}:"
                          f"{context_block['guidance_digest']}")
    # Round 5, B6: what both arms of one comparison share, the non-subject
    # skills and the frozen guidance.
    frozen = summary.get("context")
    guidance_base = (frozen.get("guidance") or {}).get("digest") \
        if isinstance(frozen, dict) and isinstance(frozen.get("guidance"), dict) else None
    others = context_block.get("others_digest") if isinstance(context_block, dict) else None
    pair_key = (f"{others}:{guidance_base}"
                if _string(others) and _string(guidance_base) else None)
    carried, has_checks = _fixture_class(evals_dir, skill, fixture, records)
    clis = sorted({doc["harness"]["version"] for doc in (summary, *trials)
                   if isinstance(doc.get("harness"), dict)
                   and _string(doc["harness"].get("version"))})
    read = {report: report_bytes, entry["summary"].relative_to(tree).as_posix(): raw,
            **{p.relative_to(tree).as_posix(): data
               for p, (data, _) in zip(trial_paths, trial_reads)}}
    files = sorted(read)
    return {"skill": skill, "fixture": fixture, "model": model, "role": role,
            "timestamp": timestamp, "path": run_dir, "report": report, "files": files,
            "trial_count": len(trials),
            "run_id": run_dir.split("/")[1] if run_dir.startswith(ROUTINE + "/") else None,
            "tested_digest": (_string(subject.get("tested_digest"))
                              if isinstance(subject, dict) else None),
            "fixture_digest": summary.get("fixture_digest"),
            "arm_context_digest": context_digest, "pair_key": pair_key, "cli_versions": clis,
            "run": summary["run"],
            # Judged unconditionally only when every trial says so (#70).
            "judge_conditional": not all(t.get("judge_conditional") is False
                                         for t in trials),
            "judge_carried": carried, "fixture_checks": has_checks,
            "trials": records, "blobs": {rel: blob_ids(data) for rel, data in read.items()},
            "content": _content(raw, [data for data, _ in trial_reads])}, None


def _content(summary: bytes, trials: list) -> tuple:
    """(sha256 of the arm summary's bytes, sha256 over the sorted sha256s of
    its trial summaries' bytes, or None without trial files), from the bytes
    `_validate` read."""
    def digest(data):
        return hashlib.sha256(data).hexdigest()
    trial_set = (hashlib.sha256("\n".join(sorted(map(digest, trials))).encode()).hexdigest()
                 if trials else None)
    return digest(summary), trial_set


def _stamp_time(value: str):
    """A results timestamp as an aware UTC datetime, or None."""
    if not isinstance(value, str) or not ingest.TIMESTAMP_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _iso_time(value):
    """An ISO 8601 time with its offset as an aware UTC datetime, or
    ValueError."""
    if not isinstance(value, str):
        raise ValueError("a time is not a string")
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError("a time has no time zone offset")
    return moment.astimezone(timezone.utc)


def _as_stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_ingest_times(path: Path) -> dict:
    """{run id: {"commit", "time", "files": {path: blob id}}} from
    `--ingest-times` (scripts/routine_ingest_times.py), or ValueError."""
    doc = json.loads(path.read_text(encoding="utf-8"), parse_constant=_refuse_constant)
    if not isinstance(doc, dict):
        raise ValueError("--ingest-times must be a JSON object")
    out = {}
    for run_id, value in doc.items():
        if not RUN_ID_RE.fullmatch(run_id):
            raise ValueError("--ingest-times has a key that is not a run id")
        if not isinstance(value, dict) or set(value) != {"commit", "time", "files"} \
                or not isinstance(value["commit"], str) \
                or not (COMMIT_RE.fullmatch(value["commit"])
                        or HEX64_RE.fullmatch(value["commit"])) \
                or not isinstance(value["files"], dict) \
                or not all(isinstance(f, str) and f and isinstance(o, str)
                           and OID_RE.fullmatch(o) for f, o in value["files"].items()):
            raise ValueError("--ingest-times entries must be {commit, time, "
                             "files: {path: blob id}}")
        out[run_id] = {"commit": value["commit"], "time": _iso_time(value["time"]),
                       "files": dict(value["files"])}
    return out


def load_fires(path: Path) -> list:
    """The `--fires` list, each entry exactly `FIRE_KEYS` of the right
    types, or ValueError. Whether a fire is trusted, and what two fires
    naming one run id mean, is `trusted_fires`'s: never a refusal here
    (round 5, B4)."""
    doc = json.loads(path.read_text(encoding="utf-8"), parse_constant=_refuse_constant)
    if not isinstance(doc, list):
        raise ValueError("--fires must be a JSON list")
    out, ids = [], set()
    for fire in doc:
        if not isinstance(fire, dict) or set(fire) != FIRE_KEYS:
            raise ValueError(f"--fires entries must have exactly the keys {sorted(FIRE_KEYS)}")
        if not _count(fire["id"]) or fire["id"] < 1 or fire["id"] in ids:
            raise ValueError("--fires needs a unique positive integer id per entry")
        ids.add(fire["id"])
        if not all(isinstance(fire[k], str) for k in ("event", "display_title", "path")) \
                or any(fire[k] is not None and not isinstance(fire[k], str)
                       for k in ("conclusion", "head_branch")) \
                or not isinstance(fire["head_sha"], str) \
                or not COMMIT_RE.fullmatch(fire["head_sha"]) \
                or not _count(fire["run_attempt"]) or fire["run_attempt"] < 1 \
                or not _count(fire["run_number"]) or fire["run_number"] < 1 \
                or not (fire["run_id"] is None or (isinstance(fire["run_id"], str)
                                                   and RUN_ID_RE.fullmatch(fire["run_id"]))):
            raise ValueError("--fires has a field of the wrong type or shape")
        out.append({**fire, "created_at": _iso_time(fire["created_at"])})
    return out


def trusted_fire_list(trust: dict, must_land: bool = False) -> list:
    """Every trusted fire (`trusted_fires`), in `--fires` order. With
    `must_land`, whatever its conclusion (round 9, R9-3): a fire carries a
    run id only once its `routine-vouch` notice was emitted, just before the
    fire API call, so a fire cancelled or failed after it may have started
    the routine; it must land, but it never vouches."""
    cache = trust.setdefault("ancestors", {})
    out = []
    for fire in trust["fires"]:
        if fire["run_id"] is None \
                or (not must_land and fire["conclusion"] != "success") \
                or fire["head_branch"] != "main" or fire["event"] != "workflow_dispatch" \
                or fire["path"] != FIRE_PATH or fire["run_attempt"] != 1:
            continue
        # Round 7, R7-3: an eval fire's title names the model it resolved;
        # one that names none cannot say which cell it was for.
        found = FIRE_TITLE_RE.fullmatch(fire["display_title"])
        if found and found[1] == "eval" and not found[3]:
            continue
        if fire["head_sha"] not in cache:
            cache[fire["head_sha"]] = harness_repo.is_ancestor(
                fire["head_sha"], trust["main_sha"], trust["main_repo"])
        if cache[fire["head_sha"]] is True:
            out.append(fire)
    return out


def trusted_fires(trust: dict) -> tuple[dict, set]:
    """({run id: the one trusted fire naming it}, {run ids two or more
    trusted fires name}). A fire is trusted when it is a first attempt that
    concluded `success`, of `FIRE_PATH`, dispatched on `main`, at a commit
    that is an ancestor of `--main-sha`. The filter comes FIRST, so a fire
    from any other branch, workflow or attempt can neither vouch nor make a
    run id ambiguous; two trusted fires naming one run id vouch for neither."""
    named: dict = {}
    for fire in trusted_fire_list(trust):
        named.setdefault(fire["run_id"], []).append(fire)
    return ({run_id: fires[0] for run_id, fires in named.items() if len(fires) == 1},
            {run_id for run_id, fires in named.items() if len(fires) > 1})


def fire_problem(fire: dict, run: dict, trust: dict) -> str | None:
    """Why `fire`, the one trusted fire naming a routine run, does not vouch
    for it (module docstring), or None. `run` is {"fixture_path", "model",
    "roles", "trials"}."""
    found = FIRE_TITLE_RE.fullmatch(fire["display_title"])
    if not found or found[1] != "eval":
        return "its fire's title is not an eval fire's"
    title_fixture, title_model, arms, trials = found[2], found[3], found[4], int(found[5])
    if title_fixture != run["fixture_path"] or title_fixture not in trust["committed"]:
        return "its fire names another fixture"
    if not (FIRE_MODEL_RE.fullmatch(title_model) and title_model == run["model"]):
        return "its fire names another model"
    if run["roles"] != ARMS[arms] or set(run["trials"]) != {trials}:
        return "its arms or trials are not its fire's"
    return None


def vouch_problem(tree: Path, run_id: str, first: dict, key: bytes) -> str | None:
    """Why `routine-results/<run id>` does not verify as the routine's
    (module docstring; round 6, R6-1), or None. Its first ingest must have
    added vouch.json, still those bytes, in the ingester's canonical shape;
    every other file that ingest added must still be its blob; and the MAC
    over those files, under the nonce VOUCH_KEY (`key`) derives for the run
    id, must be the one vouch.json holds."""
    if VOUCH_FILE not in first["files"]:
        return "routine run has no vouch.json from its first ingest"
    root = tree / ROUTINE / run_id
    data, _ = _read_bytes(root / VOUCH_FILE, READ_CAPS[VOUCH_FILE])
    if data is None or blob_ids(data).get(len(first["files"][VOUCH_FILE])) \
            != first["files"][VOUCH_FILE]:
        return "routine run's vouch.json is not the bytes its first ingest added"
    found = VOUCH_RE.fullmatch(data.decode("utf-8", "replace"))
    mac = found and json.loads(data)["mac"]
    if not found or data != canonical_vouch(mac):
        return "routine run's vouch.json is not a verified MAC"
    files = {}
    for rel, oid in sorted(first["files"].items()):
        if rel == VOUCH_FILE:
            continue
        try:
            cap = READ_CAPS[ingest.parse_result_path(rel)["kind"]]
        except ingest.Rejected:
            return "routine run's first ingest added a file that is not a result"
        content, _ = _read_bytes(root / rel, cap)
        if content is None or blob_ids(content).get(len(oid)) != oid:
            return ("routine run's files are not the bytes its first ingest added, "
                    "so its MAC cannot be verified")
        files[rel] = content
    if not hmac.compare_digest(write_vouch.mac(write_vouch.derive_nonce(key, run_id), files),
                               mac):
        return "routine run's MAC does not verify under VOUCH_KEY"
    return None


def committed_fixtures(evals_dir: Path) -> set:
    """`evals/<path>` of every fixture directory under `evals_dir`."""
    out = set()
    if not evals_dir.is_dir():
        return out
    for skill in sorted(evals_dir.iterdir()):
        if not skill.is_dir() or not run_eval._SKILL_NAME_RE.fullmatch(skill.name):
            continue
        try:
            directories = run_eval.resolve_fixture_dirs(skill, None)
        except (run_eval.FixtureLayoutError, OSError):
            continue
        out.update("evals/" + d.relative_to(evals_dir).as_posix() for d in directories)
    return out


def vouch(records: list, trust: dict | None, tree: Path) -> tuple[list, dict, list]:
    """(routine arm runs a fire vouches for, each with `order_time`;
    {reason: count} of the rest; the orphans: [{"skill", "fixture", "model",
    "run_id"}] of each run whose MAC verified but that no one trusted fire
    names, round 7, R7-1), by the module docstring's rules."""
    skipped: dict = {}
    orphans: list = []

    def skip(group, reason):
        if group:
            skipped[reason] = skipped.get(reason, 0) + len(group)

    if trust is None:
        skip(records, NO_TRUST)
        return [], skipped, orphans
    if not trust.get("vouch_key"):
        skip(records, NO_KEY)
        return [], skipped, orphans
    groups: dict = {}
    for record in records:
        groups.setdefault(record["run_id"], []).append(record)
    # An ingested run id with no arm run read, and no valid vouch.json: a
    # squat no cell can be named for (round 9, R9-3).
    for run_id in sorted(set(trust["ingest"]) - set(groups)):
        if vouch_problem(tree, run_id, trust["ingest"][run_id], trust["vouch_key"]):
            orphans.append({"skill": None, "fixture": None, "model": None,
                            "run_id": run_id, "why": "its first ingest has no valid vouch.json"})
    fires, ambiguous = trusted_fires(trust)
    kept = []
    for run_id in sorted(groups):
        group = groups[run_id]
        found = RUN_ID_RE.fullmatch(run_id)
        moment = _stamp_time(found[1]) if found else None
        first = trust["ingest"].get(run_id)
        if moment is None:
            skip(group, "routine run id is not a real UTC time")
            continue
        if first is None:
            skip(group, "routine run has no ingest time")
            continue
        if not first["time"] - INGEST_WINDOW <= moment <= first["time"]:
            skip(group, "routine run id time is not within the 48 hours before its ingest")
            continue
        problem = vouch_problem(tree, run_id, first, trust["vouch_key"])
        if problem:
            # Round 9, R9-3: a run id whose first ingest holds no valid
            # vouch.json is a squat, or a run the routine made that cannot
            # be checked; it blocks its cell when one is named, else it
            # needs a waiver.
            named = {(r["skill"], r["fixture"] or "", r["model"]) for r in group}
            (skill, fixture, model), = named if len(named) == 1 else ((None, None, None),)
            orphans.append({"skill": skill, "fixture": fixture, "model": model,
                            "run_id": run_id, "why": "its first ingest has no valid vouch.json"})
            skip(group, problem)
            continue
        prefix = f"{ROUTINE}/{run_id}/"
        late = [r for r in group
                if not all(f.startswith(prefix) and f[len(prefix):] in first["files"]
                           for f in r["files"])]
        skip(late, "routine arm run added after its run's first ingest")
        dropped = {id(r) for r in late}
        # The bytes each arm run was validated from must be the blobs the
        # MAC was verified over (round 5, B2), or a file swapped between the
        # two reads would be judged unverified.
        changed = [r for r in group if id(r) not in dropped and not all(
            r["blobs"][f].get(len(first["files"][f[len(prefix):]]))
            == first["files"][f[len(prefix):]] for f in r["files"])]
        skip(changed, "routine arm file is not the bytes its first ingest added")
        dropped |= {id(r) for r in changed}
        group = [r for r in group if id(r) not in dropped]
        if not group:
            continue
        stamps = [_stamp_time(r["timestamp"]) for r in group]
        if any(t is None or abs(t - moment) > ARM_WINDOW for t in stamps):
            skip(group, "routine arm timestamp is not within 2 hours of its run id")
            continue
        subjects = {(r["skill"], r["fixture"], r["model"]) for r in group}
        roles = [r["role"] for r in group]
        if len(subjects) != 1:
            skip(group, "routine run holds more than one fixture or model")
            continue
        if len(roles) != len(set(roles)):
            skip(group, "more than one arm run per run id, model and role")
            continue
        skill, fixture, model = next(iter(subjects))
        if run_id in ambiguous or run_id not in fires:
            # The routine made it (its MAC verified), so its fire existed:
            # re-run, deleted, cancelled or doubled since. It blocks its own
            # cell's no-benefit, or removing a fire would choose the
            # evidence (round 7, R7-1).
            orphans.append({"skill": skill, "fixture": fixture or "", "model": model,
                            "run_id": run_id})
            skip(group, "more than one trusted fire names the routine run"
                 if run_id in ambiguous else "no trusted fire names the routine run")
            continue
        fire = fires[run_id]
        problem = fire_problem(fire, {
            "fixture_path": f"evals/{skill}" + (f"/{fixture}" if fixture else ""),
            "model": model, "roles": set(roles),
            "trials": [r["trial_count"] for r in group]}, trust)
        if problem:
            skip(group, f"no fire vouches for the routine run: {problem}")
            continue
        # Round 8, R8-2: ordered by its fire, and not landed before its
        # first ingest, so an --as-of before that ingest drops it.
        kept += [{**r, "order_time": _as_stamp(fire["created_at"]),
                  "ingest_time": _as_stamp(first["time"]), "fire": fire["id"],
                  "vouched": True} for r in group]
    return kept, skipped, orphans


def unlanded_fires(trust: dict | None, index: dict, as_of: str, grace_hours,
                   waived: set) -> list:
    """[{"skill", "fixture", "model", "run_id", "overdue", "why"}]: every
    trusted eval fire created by `as_of` whose run id is not among
    `index["landed"]` (run ids with a vouched run that `as_of` kept; round 7,
    R7-2), the same for a fire trusted but for its conclusion (round 9,
    R9-3), and every orphan (`index["orphans"]`: a run whose MAC verified
    but that no one trusted fire names, R7-1, or an ingested run id with no
    valid vouch.json, R9-3, whose skill is None when no cell is named),
    less the `waived` run ids (module docstring). A fire is `overdue` past `grace_hours` at `as_of`; an
    orphan always is. A fire created after `as_of` is read only when its
    run is one `as_of` dropped."""
    if trust is None:
        return []
    now = _stamp_time(as_of)
    landed, dropped = set(index["landed"]), set(index["dropped_by_as_of"])
    out = [{**o, "overdue": True, "why": o.get("why", "no trusted fire names its verified run")}
           for o in index["orphans"] if o["run_id"] not in waived]
    seen = {o["run_id"] for o in index["orphans"]}
    for fire in trusted_fire_list(trust, must_land=True):
        if fire["run_id"] in landed or fire["run_id"] in waived or now is None \
                or fire["run_id"] in seen \
                or (fire["created_at"] > now and fire["run_id"] not in dropped):
            continue
        found = FIRE_TITLE_RE.fullmatch(fire["display_title"])
        if not found or found[1] != "eval" or found[2] not in trust["committed"]:
            continue
        _evals, skill, *fixture = found[2].split("/")
        seen.add(fire["run_id"])
        out.append({"skill": skill, "fixture": "/".join(fixture),
                    "model": found[3], "run_id": fire["run_id"],
                    "overdue": now - fire["created_at"] > timedelta(hours=grace_hours),
                    "why": "its fire has no verified ingested run"})
    return sorted(out, key=lambda u: (u["skill"] or "", u["fixture"] or "", u["model"] or "",
                                      u["run_id"]))


def build_index(tree: Path, evals_dir: Path, as_of: str, trust: dict | None = None) -> dict:
    """{"runs": [validated arm runs], "skipped": {reason: count},
    "skills": [every skill key seen], "polluted": [[skill, fixture, model]]}:
    routine runs only as `vouch` keeps them (`trust` None keeps none), none
    stamped or ordered after `as-of`, and each arm run once, by the module
    docstring's DUPLICATES rules."""
    runs, skipped, skills = [], {}, set()
    validated, routine = [], []
    for key, entry in sorted(_summaries(tree).items(),
                             key=lambda item: tuple(p or "" for p in item[0])):
        skills.add(key[1])
        record, reason = _validate(tree, key, entry, evals_dir)
        if record is None:
            skipped[reason] = skipped.get(reason, 0) + 1
        elif record["run_id"] is not None:
            routine.append(record)
        else:
            validated.append({**record, "vouched": False})
    vouched, refused, orphans = vouch(routine, trust, tree)
    for reason, count in refused.items():
        skipped[reason] = skipped.get(reason, 0) + count

    def count(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    def cell_of(record):
        return (record["skill"], record["fixture"] or "", record["model"])

    # Vouched copies first, so an unvouched copy never displaces one.
    seen: dict = {}
    polluted, dropped = set(), set()
    for record in sorted(validated + vouched,
                         key=lambda r: (not r["vouched"], r["path"], r["fixture"] or "",
                                        r["role"])):
        if record["timestamp"] > as_of or (record.get("order_time") or "") > as_of \
                or (record.get("ingest_time") or "") > as_of:
            count("after as-of")
            if record["vouched"]:
                dropped.add(record["run_id"])
            continue
        here = (*cell_of(record), record["role"])
        tree_of = record["path"].split("/", 1)[0]
        marks = {("summary", record["content"][0])}
        if record["content"][1] is not None:
            marks.add(("trials", record["content"][1]))
        stamp_mark = ("run", *here, record["timestamp"])
        owners = [seen[m] for m in sorted(marks) if m in seen]
        if owners:
            # The same bytes again. Within one cell key and tree it is a
            # plain duplicate; from another cell or tree it is pollution:
            # the cell the bytes came from is at most insufficient.
            for owner_here, owner_tree in owners:
                if owner_here != here or owner_tree != tree_of:
                    polluted.add(owner_here[:3])
            count("duplicate arm run" if all(o == (here, tree_of) for o in owners)
                  else "duplicate arm run from another cell or tree")
            continue
        if stamp_mark in seen:
            count("duplicate arm run")
            continue
        for mark in (*marks, stamp_mark):
            seen[mark] = (here, tree_of)
        runs.append(record)
    return {"runs": runs, "skipped": skipped, "skills": sorted(skills),
            "polluted": sorted(list(c) for c in polluted),
            # Round 7, R7-2: a vouched run `as_of` dropped did not land.
            "landed": sorted({r["run_id"] for r in vouched} - dropped),
            "dropped_by_as_of": sorted(dropped), "orphans": orphans}


def sentinel_number(trust: dict | None, as_of: str):
    """The lowest `run_number` of a trusted sentinel fire created at or
    after `as_of` (round 8, R8-1), or None: a first attempt that concluded
    `success`, of `FIRE_PATH`, dispatched on `main` at an ancestor of
    `--main-sha`, titled `mode=sentinel` with no fixture and no model, and
    naming no routine run. Run numbers rise with creation, so every fire
    created by `as_of` has a lower one, and a deleted one is a gap below it."""
    now = _stamp_time(as_of)
    if trust is None or now is None:
        return None
    cache = trust.setdefault("ancestors", {})
    numbers = []
    for fire in trust["fires"]:
        found = FIRE_TITLE_RE.fullmatch(fire["display_title"])
        if not found or found[1] != "sentinel" or found[2] or found[3] \
                or fire["run_id"] is not None or fire["conclusion"] != "success" \
                or fire["head_branch"] != "main" or fire["event"] != "workflow_dispatch" \
                or fire["path"] != FIRE_PATH or fire["run_attempt"] != 1 \
                or fire["created_at"] < now:
            continue
        if fire["head_sha"] not in cache:
            cache[fire["head_sha"]] = harness_repo.is_ancestor(
                fire["head_sha"], trust["main_sha"], trust["main_repo"])
        if cache[fire["head_sha"]] is True:
            numbers.append(fire["run_number"])
    return min(numbers, default=None)


def missing_fire_numbers(trust: dict | None, start: int, waived: set, upto) -> list:
    """The `run_number`s of FIRE_PATH from `start` up to `upto` (the
    sentinel's, `sentinel_number`) that `--fires` lacks, less `waived`
    (rounds 7 and 8): a fire deleted after its results were public, the
    newest ones included, since the sentinel was dispatched after them.
    Part 2 reads every run of the workflow, so a gap is a run that no longer
    exists. [] with no sentinel (`upto` None), which blocks on its own."""
    if trust is None or upto is None:
        return []
    numbers = {f["run_number"] for f in trust["fires"] if f["path"] == FIRE_PATH}
    return sorted(set(range(start, upto + 1)) - numbers - waived)


def parse_as_of(value: str) -> str:
    """`value` as a results timestamp (`YYYYMMDDTHHMMSSZ`, UTC), or
    ValueError. An ISO 8601 time must carry its offset."""
    if ingest.TIMESTAMP_RE.fullmatch(value):
        return value
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError("--as-of needs a time zone offset")
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main_sha(value: str | None) -> str | None:
    """`--main-sha` as a full commit id, or ValueError."""
    if value is not None and not COMMIT_RE.fullmatch(value):
        raise ValueError("--main-sha must be a full 40-hex commit id")
    return value


def flag_registries(values: list[str] | None) -> dict:
    """The registries the caller checked out (`--registry NAME=PATH`), by
    run_eval's own resolution; no environment or sibling default."""
    resolved = run_eval.resolve_registries(values or [], None, REPO_ROOT, None)
    return {name: entry for name, entry in resolved.items()
            if entry["source"] == "--registry flag" and entry["path"].is_dir()}


def tested_digest(registries: dict, skill, url) -> str | None:
    """The skill's `tested_digest` as on main: its one copy in `registries`
    (the fixture's `registry:` one, when it names one), digested as
    harness/delivery.py digests a registry skill; None when it is not
    unique or not readable."""
    if not isinstance(skill, str) or not run_eval._SKILL_NAME_RE.fullmatch(skill):
        return None
    try:
        if url is not None:
            entry = run_eval.registry_for_url(registries, str(url))
            registries = {entry["name"]: entry}
        matches = delivery._registry_matches(registries, None, skill)
        if len(matches) != 1:
            return None
        files, _modes = delivery._tree_files(matches[0][2])
    except (ValueError, OSError, delivery.DeliveryError, context.ContextError):
        return None
    return context._file_digest(files)


def expected_content(evals_dir: Path, skill: str, registries: dict) -> dict:
    """{fixture name, "" for a flat one: {"fixture_digest", "tested_digest"}}
    for every fixture of `skill` on main; {} when it has none."""
    eval_dir = evals_dir / skill
    try:
        directories = run_eval.resolve_fixture_dirs(eval_dir, None) if eval_dir.is_dir() else []
    except (run_eval.FixtureLayoutError, OSError):
        return {}
    out = {}
    for directory in directories:
        try:
            doc = yaml.safe_load((directory / run_eval.FIXTURE_FILE).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            doc = None
        doc = doc if isinstance(doc, dict) else {}
        out["" if directory == eval_dir else directory.name] = {
            "fixture_digest": run_eval.fixture_digest(directory),
            "tested_digest": tested_digest(registries, doc.get("skill"), doc.get("registry"))}
    return out


def finalize(skills: dict) -> None:
    """One retirement per evaluation, in place: of the skills whose verdict
    is `retire`, the one with the most arm runs (then the first by name)
    keeps it."""
    for verdict in skills.values():
        verdict["raw_verdict"] = verdict["verdict"]
    retiring = [name for name, v in sorted(skills.items()) if v["verdict"] == "retire"]
    if not retiring:
        return
    chosen = min(retiring, key=lambda n: (-len(skills[n]["runs_used"]), n))
    for name in retiring:
        if name != chosen:
            skills[name]["verdict"] = "retire-pending"
            skills[name]["reason"] = (f"no benefit is confirmed, but only one skill "
                                      f"retires per evaluation and {chosen} has more runs")


def compute(tree: Path, roster_path: Path, policy_path: Path, evals_dir: Path,
            as_of: str, registries: dict | None = None, ingest_times: dict | None = None,
            fires: list | None = None, main_sha: str | None = None,
            main_repo: Path = REPO_ROOT, vouch_key: bytes | None = None) -> dict:
    """The gates document. ValueError for a roster with no arm or a
    malformed one: an empty roster must never mean no cell to fail."""
    policy = gates.load_gate_policy(policy_path)["skills"]
    roster, problem = run_eval.read_roster(roster_path)
    if problem:
        raise ValueError(problem)
    arm_ids, _judge, _is_arm, malformed = run_eval.roster_models(roster)
    if not arm_ids or malformed:
        raise ValueError("the roster has no arm, or an arm that is not an id")
    models = sorted(arm_ids)
    trust = (None if ingest_times is None or fires is None or main_sha is None else
             {"ingest": ingest_times, "fires": fires, "first_arm": arm_ids[0],
              "committed": committed_fixtures(evals_dir), "main_sha": main_sha,
              "main_repo": main_repo, "vouch_key": vouch_key})
    index = build_index(tree, evals_dir, as_of, trust)
    index["unlanded"] = unlanded_fires(trust, index, as_of,
                                       policy["unlanded_fire_grace_hours"],
                                       {w["run_id"] for w in policy["waived_fires"]})
    # Round 8, R8-1: no trusted sentinel at or after --as-of, no upper end
    # for the sequence, so no-benefit is refused everywhere.
    sentinel = sentinel_number(trust, as_of)
    index["no_sentinel"] = trust is not None and sentinel is None
    index["missing_fire_numbers"] = missing_fire_numbers(
        trust, policy["fire_sequence_from"],
        {w["number"] for w in policy["waived_fire_numbers"]}, sentinel)
    skills = {}
    for skill in index["skills"]:
        try:
            skills[skill] = gates.retirement(index, models, skill, policy,
                                             expected_content(evals_dir, skill,
                                                              registries or {}))
        except Exception as exc:  # noqa: BLE001 - one skill's failure is its own
            skills[skill] = {"verdict": "insufficient", "cells": [], "runs_used": [],
                             "reason": f"the verdict raised {type(exc).__name__}"}
    finalize(skills)
    return {"schema_version": 1, "as_of": as_of,
            "newest_run": max((r["timestamp"] for r in index["runs"]), default=None),
            "policy": policy, "retirement_mode": policy["retirement_mode"],
            "roster_models": models, "registries": sorted((registries or {}).keys()),
            "skipped": index["skipped"], "polluted": index["polluted"],
            "unlanded": index["unlanded"],
            # Round 7, R7-4: what blocks a cell until the owner waives it.
            "needs_waiver": [u for u in index["unlanded"] if u["overdue"]],
            "missing_fire_numbers": index["missing_fire_numbers"],
            "sentinel_run_number": sentinel, "skills": skills}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--ingest-times", type=Path)
    parser.add_argument("--fires", type=Path)
    parser.add_argument("--main-sha")
    parser.add_argument("--main-repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        doc = compute(args.results_tree, args.roster, args.policy, args.evals_dir,
                      parse_as_of(args.as_of), flag_registries(args.registry),
                      load_ingest_times(args.ingest_times) if args.ingest_times else None,
                      load_fires(args.fires) if args.fires else None,
                      main_sha(args.main_sha), args.main_repo,
                      # From the environment only, never argv (round 6, R6-1).
                      os.environ.get("VOUCH_KEY", "").encode("utf-8") or None)
        text = json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (gates.GatePolicyError, ValueError, OSError, RecursionError) as exc:
        print(f"compute_gates: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
