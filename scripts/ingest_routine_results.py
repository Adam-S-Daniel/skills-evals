#!/usr/bin/env python3
"""Validate a routine's `claude/eval-<run id>` branch and stage its results.

ADR 0010 decision 2: the eval routine pushes its results to
`claude/eval-<run id>`, and that branch is UNTRUSTED input to Actions (an AI
run wrote it). `.github/workflows/routine-eval-ingest.yml` runs this script
from the default branch's checkout, never from the pushed branch, and only
ever reads the branch's objects through git plumbing (`git diff --raw`,
`git cat-file`). Nothing from the branch is executed, imported or checked out.

What a branch must look like to be ingested:

  * its name is `claude/eval-<YYYYMMDDTHHMMSSZ>-<6 hex>` (BRANCH_RE);
  * its tip, diffed against its merge-base with the default branch, ADDS
    files and nothing else, every one a regular non-executable file (mode
    100644: no symlink, no submodule, no executable bit), all under ONE
    `eval-results/<run id>/` directory (SOURCE_ROOT), where `<run id>` is
    the branch's own;
  * every added path has one of the shapes the harness writes
    (`parse_result_path`): `<key>/<timestamp>/report.md`,
    `<key>/<timestamp>/[<fixture>/]<arm>[/trial-<k>]/summary.json` and the
    same arm directory's `transcripts/tool_trace.json`. Anything else,
    `raw.json` included, rejects the whole branch;
  * every file is under its size cap, valid UTF-8 with no control
    characters, and passes its schema (`check_summary`, `check_tool_trace`,
    `check_report`).

A rejected branch stages nothing. An accepted one is written to
`<out>/routine-results/<run id>/<path below the run id>`, a deterministic
path the `place` subcommand then copies onto a `persistent/eval-results`
checkout, refusing to overwrite a file that differs.

Subcommands (all output is `key=value` lines of already-validated values,
for $GITHUB_OUTPUT):

  resolve  --event-name NAME --event-path PATH
  validate --repo DIR --base REF --source REF --branch NAME
           [--expect-sha SHA] --out DIR
  place    --staged DIR --tree DIR
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Names and shapes.

RUN_ID = r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}"
BRANCH_RE = re.compile(rf"claude/eval-(?P<run_id>{RUN_ID})")
SHA_RE = re.compile(r"[0-9a-f]{40}")
TIMESTAMP_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z")
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
TRIAL_RE = re.compile(r"trial-(?P<k>[1-9][0-9]?)")
#: The trial cap the harness itself enforces (run_eval.MAX_TRIALS).
MAX_TRIALS = 20
#: Names a fixture or arm segment may not take: each is a file or directory
#: name the harness writes inside a run, so it would make a path ambiguous.
RESERVED_NAMES = frozenset({"report.md", "summary.json", "transcripts",
                            "tool_trace.json", "raw.json"})

#: The one top-level directory the routine pushes results under: its saved
#: prompt (edited 2026-10-06, owner's answer "Pin eval-results/") writes
#: `eval-results/<run id>/` at the repo root and commits nothing else.
SOURCE_ROOT = "eval-results"
#: Branches pushed before the root was pinned, by run id, with the root each
#: used. Only claude/eval-20261006T192432Z-93755e needs an entry
#: (`results/<run id>/`); claude/eval-20261006T194256Z-f944ea already used
#: `eval-results/`. claude/eval-20261006T195724Z-a3f2d3 wrote
#: `results/<key>/` with no run id directory and stays rejected.
LEGACY_ROOTS = {"20261006T192432Z-93755e": "results"}
#: Where accepted results land on persistent/eval-results. Not `results/`:
#: that tree is eval.yml's main-pinned WIF output and the badge input, and
#: routine results are a local exhibit only (ADR 0010, decision 3), not
#: comparable to it until a paired run shows they agree.
DEST_ROOT = "routine-results"

#: Which validated result files are kept long-term on persistent/eval-results
#: (owner's answer, 2026-10-06: "summary + report only"). Every file is
#: validated either way; a file left out of this set is checked and then not
#: copied. `tool_trace.json` is dropped: harness/cli_json.py's tool-trace
#: notes say traces are never committed to persistent/eval-results.
KEEP_LONG_TERM = frozenset({"summary.json", "report.md"})

#: Byte caps, per file kind. The real files are 1.8 to 7.6 KB; the trace cap
#: leaves room for the harness's own 64 KiB event cap (TRACE_MAX_BYTES,
#: measured compact) once pretty-printed.
SIZE_CAPS = {"summary.json": 64 * 1024, "tool_trace.json": 192 * 1024,
             "report.md": 64 * 1024}
MAX_FILES = 256
MAX_TOTAL_BYTES = 4 * 1024 * 1024

#: Bounds for a free-form JSON value (agent usage, aggregates, guidance
#: extras): it may hold any JSON, but only so much of it.
MAX_DEPTH = 8
MAX_STRING = 4096
MAX_ITEMS = 512


class Rejected(Exception):
    """The branch, or one of its files, is not ingestible. The message never
    quotes file content: it names a path and a reason."""


# ---------------------------------------------------------------------------
# Paths.

def parse_result_path(rel: str) -> dict:
    """The parts of one path below `eval-results/<run id>/`, or Rejected.

    Returns {"kind", "key", "timestamp", "fixture", "arm", "trial"}; kind is
    the file's basename, which is also its schema.
    """
    parts = rel.split("/")
    if any(not p for p in parts) or len(parts) > 8:
        raise Rejected(f"{rel!r}: not a result path")
    stamps = [i for i, p in enumerate(parts) if TIMESTAMP_RE.fullmatch(p)]
    if len(stamps) != 1:
        raise Rejected(f"{rel!r}: needs exactly one timestamp segment")
    at = stamps[0]
    key_parts, below = parts[:at], parts[at + 1:]
    if key_parts and key_parts[0] == "guidance" and len(key_parts) == 2:
        if not NAME_RE.fullmatch(key_parts[1]):
            raise Rejected(f"{rel!r}: bad guidance section name")
    elif len(key_parts) != 1 or not NAME_RE.fullmatch(key_parts[0]) \
            or key_parts[0] == "guidance":
        raise Rejected(f"{rel!r}: bad subject key")
    found = {"key": "/".join(key_parts), "timestamp": parts[at],
             "fixture": None, "arm": None, "trial": None}
    if below == ["report.md"]:
        return {"kind": "report.md", **found}
    if below[-1:] == ["summary.json"]:
        kind, arm_path = "summary.json", below[:-1]
    elif below[-2:] == ["transcripts", "tool_trace.json"]:
        kind, arm_path = "tool_trace.json", below[:-2]
    else:
        raise Rejected(f"{rel!r}: not a file the harness publishes")
    if arm_path and TRIAL_RE.fullmatch(arm_path[-1]):
        trial = int(TRIAL_RE.fullmatch(arm_path[-1]).group("k"))
        if trial > MAX_TRIALS:
            raise Rejected(f"{rel!r}: trial number out of range")
        found["trial"] = trial
        arm_path = arm_path[:-1]
    if len(arm_path) not in (1, 2):
        raise Rejected(f"{rel!r}: expected [<fixture>/]<arm>")
    for name in arm_path:
        if not NAME_RE.fullmatch(name) or name in RESERVED_NAMES \
                or TRIAL_RE.fullmatch(name) or TIMESTAMP_RE.fullmatch(name):
            raise Rejected(f"{rel!r}: bad fixture or arm name")
    if len(arm_path) == 2:
        found["fixture"] = arm_path[0]
    found["arm"] = arm_path[-1]
    return {"kind": kind, **found}


# ---------------------------------------------------------------------------
# Content.

def decode_text(data: bytes, where: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Rejected(f"{where}: not UTF-8") from None
    if any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127 for c in text):
        raise Rejected(f"{where}: has a control character")
    return text


def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Rejected("duplicate JSON key")
        out[key] = value
    return out


def _no_constant(name):
    raise Rejected(f"non-finite JSON number {name}")


def load_json(text: str, where: str):
    try:
        return json.loads(text, object_pairs_hook=_no_duplicates,
                          parse_constant=_no_constant)
    except Rejected as exc:
        raise Rejected(f"{where}: {exc}") from None
    except (ValueError, RecursionError):
        raise Rejected(f"{where}: not valid JSON") from None


def is_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def bounded(value, where: str, depth: int = 0) -> None:
    """Any JSON value, within MAX_DEPTH / MAX_STRING / MAX_ITEMS."""
    if depth > MAX_DEPTH:
        raise Rejected(f"{where}: nested too deep")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if not is_number(value):
            raise Rejected(f"{where}: not a finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise Rejected(f"{where}: string too long")
        return
    if isinstance(value, list):
        if len(value) > MAX_ITEMS:
            raise Rejected(f"{where}: list too long")
        for item in value:
            bounded(item, where, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_ITEMS:
            raise Rejected(f"{where}: object too large")
        for key, item in value.items():
            if len(key) > 128:
                raise Rejected(f"{where}: key too long")
            bounded(item, where, depth + 1)
        return
    raise Rejected(f"{where}: unexpected JSON type")


def _string(value, where, limit, *, null=False):
    if value is None and null:
        return
    if not isinstance(value, str) or len(value) > limit:
        raise Rejected(f"{where}: expected a string of at most {limit} chars")


def _integer(value, where, low, high, *, null=False):
    if value is None and null:
        return
    if isinstance(value, bool) or not isinstance(value, int) \
            or not low <= value <= high:
        raise Rejected(f"{where}: expected an integer in {low}..{high}")


def _number(value, where, low, high, *, null=False):
    if value is None and null:
        return
    if not is_number(value) or not low <= value <= high:
        raise Rejected(f"{where}: expected a number in {low}..{high}")


def _object(value, where, allowed, required=()):
    if not isinstance(value, dict):
        raise Rejected(f"{where}: expected an object")
    extra = set(value) - set(allowed)
    if extra:
        raise Rejected(f"{where}: unexpected keys {sorted(extra)}")
    missing = set(required) - set(value)
    if missing:
        raise Rejected(f"{where}: missing keys {sorted(missing)}")


MODEL_ID_RE = re.compile(r"[^\s`|]{1,128}")

SUMMARY_REQUIRED = ("arm", "timestamp", "error", "agent", "objective_checks",
                    "judge", "harness", "models_used", "judge_models_used")
#: `_write_summary`'s own keys, its `extra` keys for a skill fixture (fixture,
#: n, trial, and the trial aggregate's) and a guidance subject's.
SUMMARY_ALLOWED = SUMMARY_REQUIRED + (
    "skill", "fixture", "n", "trial",
    "errors", "scored", "trial_errors", "aggregate",
    "subject", "section", "mode", "bytes", "delivery", "hook_verdict",
    "installed", "decoy", "hook_returncode", "guard")
AGENT_KEYS = ("usage", "cost_usd", "num_turns", "duration_ms")
HARNESS_KEYS = ("name", "version", "permission_mode")


def check_summary(doc, where: str, parts: dict) -> None:
    _object(doc, where, SUMMARY_ALLOWED, SUMMARY_REQUIRED)
    if doc["arm"] != parts["arm"]:
        raise Rejected(f"{where}: arm does not match its directory")
    if doc["timestamp"] != parts["timestamp"]:
        raise Rejected(f"{where}: timestamp does not match its directory")
    if doc.get("fixture") != parts["fixture"]:
        raise Rejected(f"{where}: fixture does not match its directory")
    if parts["key"].startswith("guidance/"):
        if doc.get("subject") != "guidance" \
                or doc.get("section") != parts["key"].split("/", 1)[1] \
                or "skill" in doc:
            raise Rejected(f"{where}: guidance subject does not match its key")
    elif doc.get("skill") != parts["key"] or "subject" in doc:
        raise Rejected(f"{where}: skill does not match its key")
    if parts["trial"] is not None:
        if doc.get("trial") != parts["trial"] or "n" in doc:
            raise Rejected(f"{where}: trial does not match its directory")
    else:
        _integer(doc.get("n"), f"{where}: n", 1, MAX_TRIALS)
        if "trial" in doc:
            raise Rejected(f"{where}: trial outside a trial directory")

    error = doc["error"]
    if error is not None:
        _object(error, f"{where}: error", ("type", "detail"), ("type",))
        _string(error["type"], f"{where}: error.type", 64)
        _string(error.get("detail", ""), f"{where}: error.detail", MAX_STRING)

    agent = doc["agent"]
    if agent is not None:
        _object(agent, f"{where}: agent", AGENT_KEYS)
        _number(agent.get("cost_usd"), f"{where}: agent.cost_usd", 0, 1000,
                null=True)
        _integer(agent.get("num_turns"), f"{where}: agent.num_turns", 0,
                 100_000, null=True)
        _integer(agent.get("duration_ms"), f"{where}: agent.duration_ms", 0,
                 7 * 24 * 3600 * 1000, null=True)
        bounded(agent.get("usage"), f"{where}: agent.usage")

    checks = doc["objective_checks"]
    if checks is not None:
        if not isinstance(checks, list) or len(checks) > 200:
            raise Rejected(f"{where}: objective_checks must be a short list")
        for check in checks:
            _object(check, f"{where}: objective check", ("id", "passed",
                                                         "detail"),
                    ("id", "passed"))
            bounded(check["id"], f"{where}: objective check id")
            if not isinstance(check["passed"], bool):
                raise Rejected(f"{where}: objective check passed not a bool")
            _string(check.get("detail", ""), f"{where}: objective detail",
                    MAX_STRING)

    judge = doc["judge"]
    if judge is not None:
        if not isinstance(judge, dict):
            raise Rejected(f"{where}: judge must be an object")
        bounded(judge, f"{where}: judge")
        if "overall" in judge:
            _number(judge["overall"], f"{where}: judge.overall", 0, 10)
        if isinstance(judge.get("dimensions"), list):
            for dim in judge["dimensions"]:
                if not isinstance(dim, dict):
                    raise Rejected(f"{where}: judge dimension not an object")
                if "score" in dim:
                    _number(dim["score"], f"{where}: judge score", 0, 10)

    harness = doc["harness"]
    _object(harness, f"{where}: harness", HARNESS_KEYS, HARNESS_KEYS)
    _string(harness["name"], f"{where}: harness.name", 64)
    _string(harness["version"], f"{where}: harness.version", 64, null=True)
    _string(harness["permission_mode"], f"{where}: harness.permission_mode",
            32, null=True)

    for field in ("models_used", "judge_models_used"):
        models = doc[field]
        if not isinstance(models, list) or len(models) > 16 or not all(
                isinstance(m, str) and MODEL_ID_RE.fullmatch(m)
                for m in models):
            raise Rejected(f"{where}: {field} must be a short list of model ids")

    for field in ("errors", "scored"):
        if field in doc:
            _integer(doc[field], f"{where}: {field}", 0, MAX_TRIALS)
    for field in ("trial_errors", "aggregate", "section", "mode", "bytes",
                  "delivery", "hook_verdict", "installed", "decoy",
                  "hook_returncode", "guard", "subject"):
        if field in doc:
            bounded(doc[field], f"{where}: {field}")


TRACE_KEYS = ("schema_version", "limits", "calls", "events", "omitted_events")
LIMIT_KEYS = ("input_chars", "output_chars", "max_bytes")
EVENT_KEYS = {
    "tool_use": ("call", "kind", "id", "name", "input", "input_chars",
                 "subagent"),
    "tool_result": ("call", "kind", "id", "is_error", "output",
                    "output_chars", "subagent"),
}
#: `_clip` appends "..." to a cut string, and a string too large to redact
#: becomes "<N chars, too large to redact>"; both fit within this slack.
CLIP_SLACK = 48


def check_tool_trace(doc, where: str) -> None:
    _object(doc, where, TRACE_KEYS, TRACE_KEYS)
    if doc["schema_version"] != 1 or isinstance(doc["schema_version"], bool):
        raise Rejected(f"{where}: unknown schema_version")
    _object(doc["limits"], f"{where}: limits", LIMIT_KEYS, LIMIT_KEYS)
    input_cap = doc["limits"]["input_chars"]
    output_cap = doc["limits"]["output_chars"]
    _integer(input_cap, f"{where}: limits.input_chars", 1, 1000)
    _integer(output_cap, f"{where}: limits.output_chars", 1, 1000)
    _integer(doc["limits"]["max_bytes"], f"{where}: limits.max_bytes", 1,
             SIZE_CAPS["tool_trace.json"])
    _integer(doc["calls"], f"{where}: calls", 0, 100)
    _integer(doc["omitted_events"], f"{where}: omitted_events", 0, 1_000_000)
    events = doc["events"]
    if not isinstance(events, list) or len(events) > 5000:
        raise Rejected(f"{where}: events must be a bounded list")
    for event in events:
        if not isinstance(event, dict) or event.get("kind") not in EVENT_KEYS:
            raise Rejected(f"{where}: event of unknown kind")
        keys = EVENT_KEYS[event["kind"]]
        _object(event, f"{where}: event", keys, keys)
        _integer(event["call"], f"{where}: event.call", 0, 100)
        _string(event["id"], f"{where}: event.id", 128)
        if not isinstance(event["subagent"], bool):
            raise Rejected(f"{where}: event.subagent not a bool")
        if event["kind"] == "tool_use":
            _string(event["name"], f"{where}: event.name", 100 + CLIP_SLACK)
            _string(event["input"], f"{where}: event.input",
                    input_cap + CLIP_SLACK)
            _integer(event["input_chars"], f"{where}: event.input_chars", 0,
                     10**9)
        else:
            if not isinstance(event["is_error"], bool):
                raise Rejected(f"{where}: event.is_error not a bool")
            _string(event["output"], f"{where}: event.output",
                    output_cap + CLIP_SLACK)
            _integer(event["output_chars"], f"{where}: event.output_chars", 0,
                     10**9)


def check_report(text: str, where: str, parts: dict) -> None:
    first = text.split("\n", 1)[0]
    skill = parts["key"].split("/")[-1]
    if not first.startswith("# Eval report: ") or skill not in first:
        raise Rejected(f"{where}: report does not open with its eval title")


# ---------------------------------------------------------------------------
# Git, read-only.

def git(repo: str, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                            check=False)
    if result.returncode != 0:
        # Never echo git's stderr: it can quote a ref or a path from the
        # untrusted branch.
        raise Rejected(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout


def resolve_commit(repo: str, ref: str) -> str:
    sha = git(repo, "rev-parse", "--verify", "--quiet",
              f"{ref}^{{commit}}").decode().strip()
    if not SHA_RE.fullmatch(sha):
        raise Rejected("could not resolve a commit")
    return sha


def added_files(repo: str, base: str, tip: str) -> list[tuple[str, str, str]]:
    """(path, mode, blob id) of every file `tip` changes against `base`,
    rejecting any change that is not the addition of a regular file."""
    raw = git(repo, "diff", "--raw", "-z", "--no-abbrev", "--no-renames",
              "--no-ext-diff", "--no-textconv", base, tip)
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        raise Rejected("unexpected git diff output")
    out = []
    for meta, path in zip(fields[0::2], fields[1::2]):
        try:
            _, new_mode, _, new_oid, status = meta.decode("ascii").split(" ")
            name = path.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            raise Rejected("a changed path is not plain UTF-8") from None
        if status != "A":
            raise Rejected(f"{name!r}: modified or deleted (status {status}); "
                           "only additions are ingestible")
        if new_mode != "100644":
            raise Rejected(f"{name!r}: mode {new_mode} is not a regular file")
        if not SHA_RE.fullmatch(new_oid):
            raise Rejected(f"{name!r}: unexpected blob id")
        out.append((name, new_mode, new_oid))
    return out


# ---------------------------------------------------------------------------
# Subcommands.

def validate(repo: str, base: str, source: str, branch: str,
             expect_sha: str | None, out: Path) -> dict:
    match = BRANCH_RE.fullmatch(branch)
    if not match:
        raise Rejected("branch name is not claude/eval-<run id>")
    run_id = match.group("run_id")
    tip = resolve_commit(repo, source)
    if expect_sha is not None:
        if not SHA_RE.fullmatch(expect_sha):
            raise Rejected("expected sha is not a 40-hex commit id")
        if tip != expect_sha:
            raise Rejected("the branch moved since the push that triggered "
                           "this run; that newer push triggers its own ingest")
    base_sha = resolve_commit(repo, base)
    merge_base = git(repo, "merge-base", base_sha, tip).decode().strip()
    if not SHA_RE.fullmatch(merge_base):
        raise Rejected("the branch shares no history with the default branch")

    files = added_files(repo, merge_base, tip)
    if not files:
        raise Rejected("the branch adds no files")
    if len(files) > MAX_FILES:
        raise Rejected(f"the branch adds more than {MAX_FILES} files")
    prefix = f"{LEGACY_ROOTS.get(run_id, SOURCE_ROOT)}/{run_id}/"

    staged, total = [], 0
    for name, _, oid in files:
        if not name.startswith(prefix):
            raise Rejected(f"{name!r}: not under {prefix!r}")
        rel = name[len(prefix):]
        where = repr(name)
        parts = parse_result_path(rel)
        kind = parts["kind"]
        size = int(git(repo, "cat-file", "-s", oid).decode().strip())
        if size > SIZE_CAPS[kind]:
            raise Rejected(f"{name!r}: {size} bytes is over the {kind} cap")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise Rejected("the branch's results are over the total size cap")
        data = git(repo, "cat-file", "blob", oid)
        if len(data) != size:
            raise Rejected(f"{name!r}: size changed while reading")
        text = decode_text(data, where)
        if kind == "summary.json":
            check_summary(load_json(text, where), where, parts)
        elif kind == "tool_trace.json":
            check_tool_trace(load_json(text, where), where)
        else:
            check_report(text, where, parts)
        if kind in KEEP_LONG_TERM:
            staged.append((rel, data))
    if not any(rel.endswith("summary.json") for rel, _ in staged) \
            and "summary.json" in KEEP_LONG_TERM:
        raise Rejected("the branch carries no summary.json")

    dest = out / DEST_ROOT / run_id
    if out.exists() and any(out.iterdir()):
        raise Rejected("the staging directory is not empty")
    for rel, data in staged:
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return {"run_id": run_id, "sha": tip, "files": str(len(staged))}


def place(staged: Path, tree: Path) -> dict:
    """Copy every staged file onto `tree`. A file already there with the
    same bytes is left alone; one with different bytes is a conflict and
    nothing is written. No path component in `tree` may be a symlink."""
    plan = []
    tree_root = tree.resolve()
    for path in sorted(p for p in staged.rglob("*") if p.is_file()):
        if path.is_symlink():
            raise Rejected("staged file is a symlink")
        rel = path.relative_to(staged)
        target = tree / rel
        cursor = tree
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise Rejected(f"{str(rel)!r}: the destination path has a symlink")
        if not target.resolve().is_relative_to(tree_root):
            raise Rejected(f"{str(rel)!r}: escapes the destination tree")
        data = path.read_bytes()
        if target.exists():
            if not target.is_file() or target.read_bytes() != data:
                raise Rejected(f"{str(rel)!r}: already ingested with different content")
            continue
        plan.append((target, data))
    for target, data in plan:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return {"changed": "true" if plan else "false", "added": str(len(plan))}


def resolve(event_name: str, event_path: str) -> dict:
    """The branch (and, for a push, the sha) to ingest, from the event file
    the runner wrote, as validated values only."""
    try:
        with open(event_path, encoding="utf-8") as handle:
            event = json.load(handle)
    except (OSError, ValueError):
        raise Rejected("could not read the event file") from None
    if not isinstance(event, dict):
        raise Rejected("event is not an object")
    if event_name == "workflow_run":
        run = event.get("workflow_run")
        repo = (event.get("repository") or {}).get("full_name")
        if not isinstance(run, dict) or run.get("event") != "push":
            raise Rejected("the triggering run was not a push")
        if (run.get("head_repository") or {}).get("full_name") != repo \
                or not isinstance(repo, str):
            raise Rejected("the triggering push is not from this repository")
        branch, sha = run.get("head_branch"), run.get("head_sha")
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise Rejected("the triggering push has no valid head sha")
    elif event_name == "workflow_dispatch":
        branch, sha = (event.get("inputs") or {}).get("branch"), ""
    else:
        raise Rejected("unsupported event")
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        raise Rejected("branch is not claude/eval-<run id>")
    return {"branch": branch, "sha": sha,
            "run_id": BRANCH_RE.fullmatch(branch).group("run_id")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("resolve")
    p.add_argument("--event-name", required=True)
    p.add_argument("--event-path", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--repo", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--expect-sha", default="")
    p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("place")
    p.add_argument("--staged", required=True, type=Path)
    p.add_argument("--tree", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            result = resolve(args.event_name, args.event_path)
        elif args.command == "validate":
            result = validate(args.repo, args.base, args.source, args.branch,
                              args.expect_sha or None, args.out)
        else:
            result = place(args.staged, args.tree)
    except Rejected as exc:
        # Paths are already repr()-escaped; this is the backstop, so no
        # message can start a new log line (a `::workflow-command::`).
        message = "".join(c if c.isprintable() else repr(c)[1:-1]
                          for c in str(exc))
        print(f"rejected: {message}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
