#!/usr/bin/env python3
"""Count which Claude models this account actually used, per ISO week.

*** THE OUTPUT OF THIS SCRIPT IS PUBLISHED PUBLICLY. ***

It is committed to the `persistent/eval-results` branch of a PUBLIC repository as
`usage/latest.json` by `scripts/publish_usage_census.sh` (see
`evals/usage/CENSUS.md`). Treat every byte it emits as world-readable,
forever.

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

NOT stdlib-only: classifying a `message.model` value against the tier ladder
needs `harness/roster.py`'s `tier_words()`/`load_policy()`, and roster.py
itself needs PyYAML. That import is LAZY (see `_require_model_id_re()`), so
importing this module and running `--help` work with no PyYAML installed —
only building an actual census does, and a machine that lacks it gets one
named line on stderr and exit 2, never an ImportError traceback. See
`evals/usage/CENSUS.md` for installing it on the durable machine that runs
this script.

SKILL USAGE rides the same walk when `--weekly-out` is given: how often each
skill was invoked, per ISO week, published beside the model census as
`usage/weekly-local.json` (schema: `harness/skill_usage.py`, the one place it
is defined). The same contract holds, and the keys are just as
untrusted: a `Skill` tool call's `input.skill` and a typed
`<command-name>` are free strings, so a name becomes a key ONLY when it is
in `skill_allowlist()` — skills that already appear by name in this public
repo, as a fixture or a non-coverage row whose registry is not private — and
matches `SKILL_KEY_RE`. Every other Skill tool call counts under `other`; a
typed slash command that is not an allowlisted skill (`/clear`, `/model`)
is not a skill invocation and is not counted at all.

HOOK RUNS from the fleet's git hook runner (agent-checks writes one JSON line
per local run, `--hook-logs`) become `hook` rows in the same weekly file:
per check id, per allowlisted public repository, runs and failures. A check
id is published only when shaped like one, a repository only when it is
public (`public_repos()`); everything else is `other`, and an `all` row per
week counts every run, so the totals do not depend on either allowlist.

CLOUD GUIDANCE records are read only when `--cloud-guidance DIR` names a
checkout of the private `persistent/usage-events` branch: every
`events/*/cloud-guidance.jsonl` under it, read-only, one record per cloud
session. Their coverage is unknown: nothing says how
many cloud sessions ran without writing one. The records are as untrusted as
transcripts and `state` and `check_reported` cross a private-to-public
boundary, so each is mapped through a fixed enum (anything else is `invalid`
for `state`, `unknown` for `check_reported`); no session id, CLI version,
repository count or guidance version is copied.

PRIVATE EVENTS are the exception, and the only one: `--events-out` writes
one JSON line per skill invocation, with its timestamp, session id and title,
repository and branch. That file is NEVER published publicly:
`scripts/publish_usage_census.sh` commits it only to the private
`persistent/usage-events` branch of adam-agentskills-private (see
`evals/usage/CENSUS.md`, "Private usage events"). Nothing from it reaches
the two public files.

Each private skill record also says which copy of the skill the session
loaded (`LoadedCopies`): `digest` (the lock digest of `harness/skill_digest.py`,
bare hex, or null), `digest_null_reason` (null, or one of
`DIGEST_NULL_REASONS`), `base_kind` (one of `BASE_KINDS`) and `registry`
(`owner/repo` or null). They come from the `isMeta` entry that links to the
call (`sourceToolUseID` for a Skill call, `parentUuid` for a typed command)
and whose first line is `Base directory for this skill: <path>`; the path
itself is never recorded. None of the four reaches a public file.

Usage:
    python3 scripts/model_usage_census.py --out usage/latest.json \
        [--weekly-out usage/weekly-local.json] [--events-out events.jsonl] \
        [--hook-logs PATH[:PATH...]] [--cloud-guidance DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
# Appended, not inserted: eval_coverage (for the skill allowlist) is the only
# module wanted from scripts/, and nothing there may shadow anything else.
sys.path.append(str(REPO_ROOT / "scripts"))
from timeweeks import iso_week, parse_ts, window_start, window_weeks  # noqa: E402
import skill_digest  # noqa: E402
import skill_usage  # noqa: E402

DEFAULT_PROJECTS = Path.home() / ".claude" / "projects"
DEFAULT_WEEKS = 8
POLICY_PATH = REPO_ROOT / "evals" / "roster-policy.yml"

#: The one message this script prints for a missing PyYAML, everywhere it can
#: be hit — main()'s guard and the test that shims the import away both key
#: off this exact string, so it can never drift out of step with itself.
PYYAML_MISSING_MESSAGE = ("model_usage_census needs PyYAML: "
                          "python3 -m pip install --user pyyaml")


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

    `import roster` is LOCAL to this function, not at module level: it is
    the one place this script needs PyYAML (roster.py's own `import yaml`,
    to read the tier ladder) — the alternative, hand-rolling family words
    here, is exactly what NO MODEL IDS/FAMILY WORDS LIVE OUTSIDE
    roster-policy.yml exists to prevent. Deferring the import means a
    machine with no PyYAML installed can still import this module and reach
    `--help`/argument errors; only actually building a census needs it, and
    `main()` turns that ImportError into one named line, never a traceback.
    """
    import roster
    words = "|".join(re.escape(w) for w in
                     roster.tier_words(roster.load_policy(POLICY_PATH)))
    # `\Z`, not `$`: `$` matches just before a trailing newline too, so an
    # otherwise honest id with one appended would satisfy this pattern and
    # be published as its own (distinct, newline-carrying) key rather than
    # falling to `other` (see test/run_tests.py's HOSTILE_MODELS).
    return re.compile(
        rf"^(?=.{{1,40}}\Z)claude(?:-[a-z0-9.]{{1,20}})*-(?:{words})"
        rf"(?:-[a-z0-9.]{{1,20}})*\Z")


#: Populated by `_require_model_id_re()` on first use — never at import time.
MODEL_ID_RE: re.Pattern | None = None


def _require_model_id_re() -> re.Pattern:
    """The module-level MODEL_ID_RE, computed on first call. Raises
    ImportError, uncaught, if PyYAML (via roster.py) is not installed —
    callers that can reach a user (main()) must catch it themselves and
    print PYYAML_MISSING_MESSAGE; callers in a test that already has PyYAML
    installed never see it raise at all.
    """
    global MODEL_ID_RE
    if MODEL_ID_RE is None:
        MODEL_ID_RE = _model_id_re()
    return MODEL_ID_RE


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
    if isinstance(model, str) and _require_model_id_re().match(model):
        return model
    return OTHER_KEY


#: Effort levels Claude Code records; any other non-empty value is `other`.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def _effort(entry: dict) -> str | None:
    """The turn's effort level from the entry's top level, allowlisted."""
    value = entry.get("perTurnEffort")
    if value is None:
        value = entry.get("effort")
    if value is None or value == "":
        return None
    if isinstance(value, str) and value in EFFORT_LEVELS:
        return value
    return OTHER_KEY


def _context_tokens(message: dict) -> int | None:
    """Input plus cached input tokens on the turn: how full the context was.
    Only non-negative ints count; None when none of the three is valid."""
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return None
    total = None
    for field in ("input_tokens", "cache_read_input_tokens",
                  "cache_creation_input_tokens"):
        value = usage.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            total = (total or 0) + value
    return total


def _turn_facts(entry: dict, message: dict) -> dict:
    """What one assistant entry says about its turn, for a skill record."""
    return {"model": published_key(message.get("model")),
            "effort": _effort(entry),
            "context_tokens": _context_tokens(message)}


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


#: The shape of a published skill key: a skill directory basename, lowercase.
#: Necessary even for an allowlisted name — the allowlist is read from files a
#: pull request can change, and this is the last check before a public key.
SKILL_KEY_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")

#: A typed slash command, as Claude Code records it in the user entry.
_COMMAND_NAME_RE = re.compile(r"<command-name>([^<]{0,200})</command-name>")


def skill_allowlist(root: Path = REPO_ROOT) -> frozenset[str]:
    """The skill names that may become published keys.

    A name qualifies when this public repo already carries it: a skill
    fixture `scripts/eval_coverage.py` counts under `root/evals`, or a row
    of `root/evals/non-coverage.yml`, in either case only when its registry
    is not private (a private skill's name must not become a public key; its
    calls count under `other`).
    Both are read by eval_coverage's own `count_fixtures`/`load_skips`, so
    "is a fixture" means the same here as in the coverage census. Raises
    `eval_coverage.CensusRefusal` or ValueError when either cannot be read;
    the caller fails closed. Needs PyYAML, so the import is lazy.
    """
    import eval_coverage
    import run_eval
    registries = {entry["name"]: entry
                  for entry in run_eval._load_registries_config()}
    fixtures = eval_coverage.count_fixtures(Path(root) / "evals", registries)
    skips: dict = {}
    eval_coverage.load_skips(Path(root) / "evals" / "non-coverage.yml",
                             registries, private=False, into=skips)
    names = {skill for registry, skill in fixtures
             if registry not in eval_coverage.PRIVATE_REGISTRIES}
    names |= {skill for registry, skill in skips
              if registry not in eval_coverage.PRIVATE_REGISTRIES}
    return frozenset(name for name in names if SKILL_KEY_RE.fullmatch(name))


def private_plugins() -> frozenset[str]:
    """The plugin names harness/registries.yml lists for a private registry.
    Needs PyYAML, so the import is lazy."""
    import eval_coverage
    import run_eval
    return frozenset(plugin for entry in run_eval._load_registries_config()
                     if entry["name"] in eval_coverage.PRIVATE_REGISTRIES
                     for plugin in entry.get("plugins", ()))


def _private_prefix(raw, private: frozenset[str]) -> bool:
    """True when `raw` is prefixed (`plugin:skill`) by a private plugin. This
    guards prefixed invocations only: a bare name resolves by the allowlist."""
    if not isinstance(raw, str) or ":" not in raw:
        return False
    plugin = raw[1:] if raw.startswith("/") else raw
    return plugin.rsplit(":", 1)[0] in private


def _skill_name(raw) -> str | None:
    """`/adam-coding-anywhere:workflow-path-audit` -> `workflow-path-audit`."""
    if not isinstance(raw, str):
        return None
    name = raw[1:] if raw.startswith("/") else raw
    return name.rsplit(":", 1)[-1]


def skill_key(raw, allowlist: frozenset[str],
              private: frozenset[str] = frozenset()) -> str:
    """The key a Skill tool call's `input.skill` is counted under. A name
    prefixed by a `private` registry's plugin counts under `other`."""
    name = _skill_name(raw)
    if _private_prefix(raw, private):
        return OTHER_KEY
    if name in allowlist and SKILL_KEY_RE.fullmatch(name):
        return name
    return OTHER_KEY


def _typed_command(message: dict) -> str | None:
    """The slash command a user entry typed, as written, or None.

    Only the message's own text counts (a string, or `text` items): a
    `tool_result` can quote a transcript, and its tags were not typed here.
    The first text that carries a command decides.
    """
    content = message.get("content")
    if isinstance(content, str):
        texts = [content]
    elif isinstance(content, list):
        texts = [item["text"] for item in content
                 if isinstance(item, dict) and item.get("type") == "text"
                 and isinstance(item.get("text"), str)]
    else:
        return None
    for text in texts:
        match = _COMMAND_NAME_RE.search(text)
        if match:
            return match.group(1)
    return None


def _typed_skill(message: dict, allowlist: frozenset[str],
                 private: frozenset[str] = frozenset()) -> str | None:
    """The allowlisted skill a user entry's slash command names, or None
    (also None for a command prefixed by a `private` plugin)."""
    command = _typed_command(message)
    name = _skill_name(command)
    if _private_prefix(command, private):
        return None
    if name in allowlist and SKILL_KEY_RE.fullmatch(name):
        return name
    return None


# --- Private per-invocation records (`--events-out`) -----------------------
# These go ONLY to the private repository. They still get bounds: every free
# string is capped, and a repository is published as `owner/name` only when it
# has that shape, so a remote URL carrying a token never reaches the record.

#: Longest kept value of a free string in a private record.
EVENT_TEXT_CAP = 200
#: A host name that may name a file in the private store.
MACHINE_RE = re.compile(r"(?!cloud-)[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_GITHUB_REMOTE_RE = re.compile(
    r"(?:https://(?:[^@/\s]+@)?github\.com/|ssh://git@github\.com/|git@github\.com:)"
    r"([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?")


def machine_name() -> str:
    """This host's name, or `unknown` when it is not shaped like one."""
    name = socket.gethostname()
    return name if isinstance(name, str) and MACHINE_RE.fullmatch(name) else "unknown"


def _text(value) -> str | None:
    """A non-empty string, capped; anything else is None."""
    return value[:EVENT_TEXT_CAP] if isinstance(value, str) and value else None


def github_repo(url) -> str | None:
    """`owner/name` of a github.com remote URL, or None for any other URL."""
    match = _GITHUB_REMOTE_RE.fullmatch(url) if isinstance(url, str) else None
    if not match or match.group(2) in (".", ".."):
        return None
    return f"{match.group(1)}/{match.group(2)}"


def cwd_repo(cwd, cache: dict) -> str | None:
    """`owner/name` of `cwd`'s `origin` when `cwd` still exists and that
    remote is on github.com; None otherwise. One `git` call per directory."""
    if not isinstance(cwd, str) or not cwd:
        return None
    if cwd not in cache:
        repo = None
        if os.path.isabs(cwd) and os.path.isdir(cwd):
            try:
                proc = subprocess.run(
                    ["git", "-C", cwd, "-c", "core.fsmonitor=false",
                     "remote", "get-url", "origin"],
                    capture_output=True, text=True, timeout=10,
                    stdin=subprocess.DEVNULL)
                if proc.returncode == 0:
                    repo = github_repo(proc.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                repo = None
        cache[cwd] = repo
    return cache[cwd]


def _event_ts(when: datetime) -> str:
    """UTC, milliseconds, `Z`: one shape, so records sort as strings."""
    return when.astimezone(timezone.utc).isoformat(timespec="milliseconds") \
        .replace("+00:00", "Z")


def _skill_event(entry: dict, when: datetime, event_id, name: str,
                 cache: dict, machine: str, root: str,
                 model: str | None = None, effort: str | None = None,
                 context_tokens: int | None = None) -> dict:
    """One private record of a skill invocation. `session_title` is filled
    in when the whole transcript has been read. `model` is the sanitized
    key of the model running at the call, or None when unknown; `effort`
    and `context_tokens` come from the same assistant turn, None when
    unknown. `cli` is the Claude Code version the transcript line recorded
    (its use-time value), None when the line has none."""
    ts = _event_ts(when)
    session = _text(entry.get("sessionId"))
    if not _text(event_id):
        # No tool-use id or entry uuid: an id that is still stable across runs.
        event_id = hashlib.sha256(f"{session}\n{ts}\n{name}".encode("utf-8")).hexdigest()
    return {"v": 1, "id": _text(event_id), "ts": ts, "kind": "skill",
            "name": name[:EVENT_TEXT_CAP], "model": model,
            "effort": effort, "context_tokens": context_tokens, "surface": "local", "root": root,
            "cli": _text(entry.get("version")),
            "machine": machine,
            "session_id": session, "session_title": None,
            "cwd_repo": cwd_repo(entry.get("cwd"), cache),
            "branch": _text(entry.get("gitBranch")),
            **_NOT_LOADED}


# --- Which skill copy a local session loaded (private records only) --------
# Claude Code answers a Skill call, or a typed skill command, with a user entry
# marked `isMeta` whose text starts `Base directory for this skill: <path>`.
# That path names the copy the session loaded; the census hashes it with the
# lock digest (harness/skill_digest.py) and says where it lives. Only the
# digest, a reason, a kind and an `owner/repo` are recorded, never the path,
# and only in the private events: nothing here reaches a public file.

#: Why a skill record's `digest` is null (null when it has one).
DIGEST_NULL_REASONS = ("no-base-dir", "builtin", "outside-known-roots", "gone",
                       "changed-since-load", "refused-by-registry-rules",
                       "too-large", "bad-name")
#: Where the loaded copy lives.
BASE_KINDS = ("plugin-cache", "user-skills", "repo", "builtin", "account-plugin",
              "account-sync", "unknown")
#: Claude Code's built-in prompt skills, measured to write no base-directory
#: message.
BUILTIN_SKILLS = frozenset({"schedule", "update-config", "loop", "simplify",
                            "artifact-design", "workflow-authoring"})
#: A skill directory name; also what the base directory's basename must be.
SKILL_DIR_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_BASE_DIR_LINE = "Base directory for this skill: "
_OWNER_REPO_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100})")
_HTTPS_GITHUB_RE = re.compile(
    r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}?)(?:\.git)?")
_DRIVE_PATH_RE = re.compile(r"([A-Za-z]):\\(.*)", re.DOTALL)
_WSL_UNC_RE = re.compile(r"\\\\wsl(?:\.localhost|\$)\\[^\\]+(\\.*)?",
                         re.DOTALL | re.IGNORECASE)
_NOT_LOADED = {"digest": None, "digest_null_reason": "no-base-dir",
               "base_kind": "unknown", "registry": None}


def _owner_repo(value) -> str | None:
    """`value` when it is an `owner/repo` string, else None."""
    match = _OWNER_REPO_RE.fullmatch(value) if isinstance(value, str) else None
    return value if match and match.group(2) not in (".", "..") else None


def base_dir_line(message: dict) -> str | None:
    """The path after `Base directory for this skill: ` when that is the
    FIRST line of the entry's text (a string, or a first `text` item), else
    None. A line quoted further down in prose does not count."""
    content = message.get("content")
    if isinstance(content, list):
        first = content[0] if content else None
        content = (first.get("text") if isinstance(first, dict)
                   and first.get("type") == "text" else None)
    if not isinstance(content, str):
        return None
    line = content.split("\n", 1)[0]
    if not line.startswith(_BASE_DIR_LINE):
        return None
    return line[len(_BASE_DIR_LINE):] or None


def native_path(raw: str) -> str:
    """`C:\\x\\y` -> `/mnt/c/x/y`, `\\\\wsl.localhost\\<distro>\\x` (or
    `\\\\wsl$\\...`) -> `/x`; anything else unchanged."""
    match = _DRIVE_PATH_RE.fullmatch(raw)
    if match:
        return f"/mnt/{match.group(1).lower()}/" + match.group(2).replace("\\", "/")
    match = _WSL_UNC_RE.fullmatch(raw)
    if match:
        return (match.group(1) or "\\").replace("\\", "/")
    return raw


def _path_shape(real: str) -> tuple[str, str | None, str | None]:
    """(kind by path alone, the `.claude` directory, the marketplace)."""
    parts = PurePosixPath(real).parts
    if "local-agent-mode-sessions" in parts:
        return "account-plugin", None, None
    for index, part in enumerate(parts):
        if part != ".claude":
            continue
        claude, rest = str(PurePosixPath(*parts[:index + 1])), parts[index + 1:]
        if len(rest) == 7 and rest[:2] == ("plugins", "cache") and rest[5] == "skills":
            return "plugin-cache", claude, rest[2]
        if len(rest) > 2 and rest[:2] == ("skills", "synced"):
            return "account-sync", claude, None
        if len(rest) == 2 and rest[0] == "skills":
            return "user-skills", claude, None
    return "unknown", None, None


def _latest_change(root: str, skip: frozenset) -> float:
    """The latest max(st_mtime, st_ctime) of `root` and every entry under it
    (links not followed, `skip` left out). DigestTooLarge past the digest's
    file cap; OSError when the tree cannot be read."""
    def fail(error):
        raise error
    info = os.lstat(root)
    latest, count = max(info.st_mtime, info.st_ctime), 0
    for directory, subdirs, names in os.walk(root, followlinks=False, onerror=fail):
        for name in subdirs + names:
            path = os.path.join(directory, name)
            if path in skip:
                continue
            count += 1
            if count > 2 * skill_digest.MAX_FILES:
                raise skill_digest.DigestTooLarge("too many entries")
            info = os.lstat(path)
            latest = max(latest, info.st_mtime, info.st_ctime)
    return latest


class LoadedCopies:
    """Resolves which skill copy each private record's session loaded.

    One instance per census run: each base directory is walked and hashed
    at most once, each checkout asked for its ignored files and remote once;
    the change guard is then compared per record. Every lookup root (the
    `.claude` directory, the checkout) comes from the base directory itself.
    """

    def __init__(self):
        self._trees: dict = {}
        self._toplevels: dict = {}
        self._json: dict = {}

    def resolve(self, name: str, base: str | None, when: datetime) -> dict:
        """The four loaded-copy keys of a record invoking `name` at `when`
        whose base-directory message named `base` (None: no such message)."""
        out = dict(_NOT_LOADED, digest_null_reason=None)
        bare = name.split(":", 1)[1] if ":" in name else name
        if not SKILL_DIR_NAME_RE.fullmatch(bare):
            return dict(out, digest_null_reason="bad-name")
        if base is None:
            if bare in BUILTIN_SKILLS:
                return dict(out, base_kind="builtin", digest_null_reason="builtin")
            return dict(out, digest_null_reason="no-base-dir")
        path = native_path(base)
        if not os.path.isabs(path):
            return dict(out, digest_null_reason="outside-known-roots")
        if "bundled-skills" in PurePosixPath(path).parts:
            return dict(out, base_kind="builtin", digest_null_reason="builtin")
        real = os.path.realpath(path)
        if os.path.basename(os.path.normpath(path)) != bare \
                or os.path.basename(real) != bare:
            return dict(out, digest_null_reason="no-base-dir")
        kind, claude, marketplace = _path_shape(real)
        if not os.path.isdir(real):
            return dict(out, base_kind=kind, digest_null_reason="gone")
        checkout = None
        if kind in ("user-skills", "unknown"):
            checkout = self._toplevel(real)
            if checkout is not None:
                kind = "repo"
        if kind == "unknown":
            return dict(out, digest_null_reason="outside-known-roots")
        out["base_kind"] = kind
        if kind == "plugin-cache":
            out["registry"] = self._marketplace_repo(claude, marketplace)
        elif kind == "repo":
            out["registry"] = self._origin_repo(checkout)
        tree = self._tree(real, checkout)
        reason = tree.get("reason")
        if reason is None and tree["latest"] > when.timestamp():
            reason = "changed-since-load"
        if reason is None:
            reason = self._digest(tree)
        if reason is not None:
            return dict(out, digest_null_reason=reason)
        out["digest"] = tree["digest"]
        if kind == "user-skills":
            out["registry"] = self._bootstrap_repo(claude, bare, tree["digest"])
        return out

    def _tree(self, real: str, checkout: str | None) -> dict:
        """{"latest", "skip"} or {"reason"} for one base directory, cached."""
        if real not in self._trees:
            try:
                skip = (skill_digest.git_ignored(checkout) if checkout is not None
                        else frozenset())
                self._trees[real] = {"path": real, "skip": skip,
                                     "latest": _latest_change(real, skip)}
            except skill_digest.DigestTooLarge:
                self._trees[real] = {"reason": "too-large"}
            except OSError:
                self._trees[real] = {"reason": "gone"}
        return self._trees[real]

    @staticmethod
    def _digest(tree: dict) -> str | None:
        """Hash the tree once; None, or the null reason."""
        if "digest" not in tree:
            try:
                tree["digest"] = skill_digest.lock_digest(tree["path"], tree["skip"])
            except skill_digest.DigestRefused:
                tree["reason"] = "refused-by-registry-rules"
            except skill_digest.DigestTooLarge:
                tree["reason"] = "too-large"
            except (OSError, UnicodeError):
                tree["reason"] = "gone"
            if "reason" in tree:
                tree["digest"] = None
        return tree.get("reason")

    def _toplevel(self, real: str) -> str | None:
        """The work tree `real` is inside, or None."""
        if real not in self._toplevels:
            top = None
            try:
                proc = subprocess.run(
                    ["git", "-C", real, "-c", "core.fsmonitor=false",
                     "rev-parse", "--show-toplevel"],
                    capture_output=True, text=True, timeout=10,
                    stdin=subprocess.DEVNULL)
                if proc.returncode == 0 and proc.stdout.strip():
                    top = os.path.realpath(proc.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                top = None
            self._toplevels[real] = top
        return self._toplevels[real]

    def _origin_repo(self, checkout: str) -> str | None:
        """`owner/repo` of the checkout's github.com `origin`, else None."""
        key = ("origin", checkout)
        if key not in self._json:
            url = None
            try:
                proc = subprocess.run(
                    ["git", "-C", checkout, "config", "--get", "remote.origin.url"],
                    capture_output=True, text=True, timeout=10,
                    stdin=subprocess.DEVNULL)
                if proc.returncode == 0:
                    url = proc.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                url = None
            self._json[key] = github_repo(url)
        return self._json[key]

    def _load(self, path: str):
        """A JSON file's content, or None when it cannot be read."""
        if path not in self._json:
            try:
                with open(path, encoding="utf-8") as handle:
                    self._json[path] = json.load(handle)
            except (OSError, ValueError):
                self._json[path] = None
        return self._json[path]

    def _marketplace_repo(self, claude: str, marketplace: str) -> str | None:
        """The github `owner/repo` that `<claude>/plugins/known_marketplaces.json`
        names for `marketplace`, else None."""
        known = self._load(os.path.join(claude, "plugins", "known_marketplaces.json"))
        entry = known.get(marketplace) if isinstance(known, dict) else None
        source = entry.get("source") if isinstance(entry, dict) else None
        if isinstance(source, dict) and source.get("source") == "github":
            return _owner_repo(source.get("repo"))
        return None

    def _bootstrap_repo(self, claude: str, name: str, digest: str) -> str | None:
        """The registry the skills-bootstrap hook's install record names for
        `name`, only when its digest is this copy's and its URL is a plain
        `https://github.com/<owner>/<repo>`; else None."""
        record = self._load(os.path.join(claude, "skills",
                                         ".skills-bootstrap-installed.json"))
        installed = record.get("installed") if isinstance(record, dict) else None
        for entry in installed if isinstance(installed, list) else ():
            if not (isinstance(entry, dict) and entry.get("name") == name):
                continue
            recorded, url = entry.get("digest"), entry.get("registry")
            if not (isinstance(recorded, str) and isinstance(url, str)
                    and skill_digest.normalize(recorded) == digest):
                return None
            match = _HTTPS_GITHUB_RE.fullmatch(url)
            return _owner_repo(match.group(1)) if match else None
        return None


#: Signature strings that tell a session's loaded memory files apart. They
#: mirror the marker lines in _agent-guidance's agents-md/base.md (the full
#: fleet guidance) and agents-md/stub.md (the repo stub), plus the two
#: headings older versions carried before the markers existed.
GUIDANCE_FULL_MARKERS = ("guidance-marker: fleet-full", "## Working in these repos")
GUIDANCE_STUB_MARKERS = ("guidance-marker: fleet-stub",
                         "Fleet guidance is delivered once per session")
GUIDANCE_FULL, GUIDANCE_STUB, GUIDANCE_NEITHER, GUIDANCE_UNKNOWN = (
    "full", "stub-only", "neither", "unknown")


def _instruction_texts(entry: dict) -> list[str] | None:
    """The memory-file texts of an `attachment` entry of type `instructions`,
    or None when the entry is not one."""
    attachment = entry.get("attachment")
    if not isinstance(attachment, dict) or attachment.get("type") != "instructions":
        return None
    files = attachment.get("files")
    return [f["content"] for f in files if isinstance(f, dict)
            and isinstance(f.get("content"), str)] if isinstance(files, list) else []


def guidance_state(texts: list[str] | None) -> str:
    """Classify a session by the memory texts it loaded; None means no
    instructions entry was found (an older CLI may not write one)."""
    if texts is None:
        return GUIDANCE_UNKNOWN
    if any(m in t for t in texts for m in GUIDANCE_FULL_MARKERS):
        return GUIDANCE_FULL
    if any(m in t for t in texts for m in GUIDANCE_STUB_MARKERS):
        return GUIDANCE_STUB
    return GUIDANCE_NEITHER


def _bump(counts: dict, key: str, week: str) -> None:
    counts.setdefault(key, {})
    counts[key][week] = counts[key].get(week, 0) + 1


# --- Cloud guidance records (`--cloud-guidance`) ----------------------------
# One line per cloud session, appended by _agent-guidance's guidance-load hook
# to events/<YYYY-MM>/cloud-guidance.jsonl on the private branch: {"v","ts",
# "kind":"guidance-load","session","state","check_expected","check_reported",
# "cli","repos","guidance_version","registry_sha",...}. Only `session`, `ts`,
# `state` and `check_reported` are read.

CLOUD_GUIDANCE_FILE = "cloud-guidance.jsonl"
GUIDANCE_INVALID = "invalid"
GUIDANCE_STATES = (GUIDANCE_FULL, GUIDANCE_STUB, GUIDANCE_NEITHER, GUIDANCE_UNKNOWN)
CHECK_UNKNOWN = "unknown"
CHECK_RESULTS = ("match", "mismatch", "none", "absent")


def _enum(value, allowed: tuple, otherwise: str) -> str:
    """`value` when it is one of the fixed strings in `allowed`, else
    `otherwise`; never anything else, whatever the record held."""
    return value if isinstance(value, str) and value in allowed else otherwise


def cloud_guidance_tally(root, now: datetime, weeks: int = DEFAULT_WEEKS) -> dict:
    """Weekly counts from `root`/events/*/cloud-guidance.jsonl, READ-ONLY.

    Returns {"guidance": {state: {iso_week: n}}, "checks": {result:
    {iso_week: n}}, "records_scanned": n, "earliest": datetime | None}.
    A record counts only with a string `session` and a parseable `ts` inside
    the census window (not before the Monday of its oldest week, not in a
    later week than `now`'s); a session counts once across every file, at the
    earliest `ts`, the first line winning a tie (files in sorted order).
    Malformed lines, unreadable files and linked files are skipped without a
    trace. `records_scanned` is the number of distinct sessions counted.
    """
    wanted = set(window_weeks(now, weeks))
    start = datetime.fromisoformat(skill_usage.week_monday(window_weeks(now, weeks)[-1])
                                   ).replace(tzinfo=timezone.utc)
    first: dict[str, tuple[datetime, dict]] = {}
    for path in sorted(Path(root).glob(f"{EVENTS_DIR}/*/{CLOUD_GUIDANCE_FILE}")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or not isinstance(record.get("session"), str) \
                    or not record["session"] or not isinstance(record.get("ts"), str):
                continue
            when = parse_ts(record["ts"])
            when = None if when is None else when.astimezone(timezone.utc)
            if when is None or when < start or iso_week(when) not in wanted:
                continue
            kept = first.get(record["session"])
            if kept is None or when < kept[0]:
                first[record["session"]] = (when, record)
    tally = {"guidance": {}, "checks": {}, "records_scanned": len(first),
             "earliest": min((when for when, _ in first.values()), default=None)}
    for when, record in first.values():
        week = iso_week(when)
        _bump(tally["guidance"], _enum(record.get("state"), GUIDANCE_STATES,
                                       GUIDANCE_INVALID), week)
        _bump(tally["checks"], _enum(record.get("check_reported"), CHECK_RESULTS,
                                     CHECK_UNKNOWN), week)
    return tally


def census_counts(projects_dir: Path, now: datetime,
                  weeks: int = DEFAULT_WEEKS) -> dict:
    """{model_id: {iso_week: count}} over the trailing `weeks` ISO weeks.

    One count per assistant TURN that names a model, deduplicated per
    transcript on `message.id`. Entries outside the window, entries of any
    other type, entries without a model, and lines that are not JSON at all
    are all skipped — a transcript being written while this runs will have a
    torn last line, and that is not a reason to fail.
    """
    return census_all(projects_dir, now, weeks)[0]


# --- Local git-hook runs (`--hook-logs`) -----------------------------------
# agent-checks (managed in _agent-guidance) appends one line per local hook
# run: {"v":1,"ts":"...Z","event":"pre-commit|pre-push","repo":"owner/name"|null,
# "checks":[ids],"failed":[ids]}. The lines are as untrusted as transcripts.

#: The shape of a check id that may be a published key.
HOOK_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
HOOK_EVENTS = ("pre-commit", "pre-push")
#: The runner digest a log line may carry: 12 lowercase hex, nothing else.
RUNNER_RE = re.compile(r"[0-9a-f]{12}")
#: The per-week row that counts every run, whatever its checks.
HOOK_ALL = "all"
#: Public repositories that are not skill registries but run the hooks.
ALWAYS_PUBLIC_REPOS = frozenset({"Adam-S-Daniel/skills-evals",
                                 "Adam-S-Daniel/_agent-guidance"})
_HOOK_LIST_CAP = 200


def default_hook_log() -> str:
    """Where agent-checks writes, by the same rule it uses."""
    explicit = os.environ.get("AGENT_CHECKS_LOG")
    if explicit:
        return explicit
    state = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state")
    return os.path.join(state, "agent-checks", "runs.jsonl")


def public_repos() -> frozenset[str]:
    """`owner/name` of every registry in harness/registries.yml that is not
    private, plus ALWAYS_PUBLIC_REPOS. Needs PyYAML, so the import is lazy."""
    import eval_coverage
    import run_eval
    repos = set(ALWAYS_PUBLIC_REPOS)
    for entry in run_eval._load_registries_config():
        if entry["name"] not in eval_coverage.PRIVATE_REGISTRIES:
            repo = github_repo(entry["url"])
            if repo:
                repos.add(repo)
    return frozenset(repos)


def _id_list(value) -> list | None:
    if not isinstance(value, list) or len(value) > _HOOK_LIST_CAP:
        return None
    if not all(isinstance(item, str) and 0 < len(item) <= 100 for item in value):
        return None
    return value


def _hook_run(line: str) -> dict | None:
    """One well-formed agent-checks line, or None."""
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    if not isinstance(entry, dict) or type(entry.get("v")) is not int or entry["v"] != 1:
        return None
    when = parse_ts(entry["ts"]) if isinstance(entry.get("ts"), str) else None
    repo = entry.get("repo")
    checks, failed = _id_list(entry.get("checks")), _id_list(entry.get("failed"))
    if (when is None or entry.get("event") not in HOOK_EVENTS or checks is None
            or failed is None
            or not (repo is None or (isinstance(repo, str) and 0 < len(repo) <= 200))):
        return None
    runner = entry.get("runner")
    if not (isinstance(runner, str) and RUNNER_RE.fullmatch(runner)):
        runner = None
    return {"when": when, "event": entry["event"], "repo": repo,
            "checks": checks, "failed": failed, "runner": runner}


def _hook_key(check: str) -> str:
    return check if HOOK_ID_RE.fullmatch(check) and check != HOOK_ALL else OTHER_KEY


def hook_tally(paths, now: datetime, weeks: int, repos: frozenset[str],
               events: list | None = None, machine: str = "") -> dict | None:
    """{"rows": {(iso_week, name, repo, runner): [runs, blocked]},
    "runs_scanned": n}
    over the census window, or None when no file in `paths` could be read.

    A malformed line is skipped. A line seen twice (the same bytes in two
    logs) counts once: its id is the hash of the machine and the line. When
    `events` is a list, each counted run is appended to it as a private
    record.
    """
    wanted = set(window_weeks(now, weeks))
    rows: dict = {}
    seen: set[str] = set()
    read = False
    for path in paths:
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        read = True
        with handle:
            for raw in handle:
                raw = raw.strip()
                run = _hook_run(raw) if raw else None
                if run is None or iso_week(run["when"]) not in wanted:
                    continue
                digest = hashlib.sha256(f"{machine}\n{raw}".encode("utf-8")).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                week = iso_week(run["when"])
                repo = run["repo"]
                if repo is not None and repo not in repos:
                    repo = OTHER_KEY
                failed = {_hook_key(check) for check in run["failed"]}
                ran = {_hook_key(check) for check in run["checks"]} | failed
                for name, hit in [((HOOK_ALL, None), bool(failed))] + \
                        [((key, repo), key in failed) for key in ran]:
                    counts = rows.setdefault((week, *name, run["runner"]), [0, 0])
                    counts[0] += 1
                    counts[1] += int(hit)
                if events is not None:
                    events.append({"v": 1, "id": digest, "ts": _event_ts(run["when"]),
                                   "kind": "hook", "event": run["event"],
                                   "repo": run["repo"], "checks": run["checks"],
                                   "failed": run["failed"], "runner": run["runner"],
                                   "surface": "local",
                                   "root": root_kind(path), "machine": machine})
    return {"rows": rows, "runs_scanned": len(seen)} if read else None


def root_kind(path) -> str:
    """Which transcript root `path` is, for the private records: `cowork`
    (the desktop app's Cowork sandbox), `windows` (a Windows drive seen from
    WSL, `/mnt/<letter>/...`) or `wsl` (this side's own home)."""
    parts = Path(path).parts
    if "local-agent-mode-sessions" in parts:
        return "cowork"
    if len(parts) > 2 and parts[:2] == ("/", "mnt") and len(parts[2]) == 1:
        return "windows"
    return "wsl"


def census_all(projects_dir, now: datetime, weeks: int = DEFAULT_WEEKS,
               allowlist: frozenset[str] | None = None,
               events: list | None = None,
               private: frozenset[str] = frozenset()) -> tuple[dict, dict]:
    """(model counts, skill tally) from ONE walk of the transcripts.

    `projects_dir` is one transcript root or a list of them (WSL, Windows,
    Cowork). A turn, Skill call or typed command whose id an EARLIER root
    already counted is skipped, so a session stored under two roots counts
    once. Inside one Cowork root the ids are deduplicated across files too:
    the desktop app stores each Cowork session twice.

    Model counts are `census_counts`'s. The skill tally is
    {"invocations": {skill: {iso_week: n}}, "sessions": {skill: {iso_week: n}},
    "sessions_scanned": n}. Invocations stay empty when `allowlist` is None;
    otherwise one per `Skill` tool call (deduplicated per transcript on the
    tool_use `id`) and one per user entry whose typed slash command names an
    allowlisted skill. `sessions` counts the distinct transcript files that
    invoked a skill in a week; `sessions_scanned` the transcript files read
    (those the mtime prefilter kept). Same window as the models.

    When `events` is a list (and `allowlist` is given), one private record
    per counted invocation is appended to it, the name as invoked; its
    `session_title` is the transcript's last `summary` or `custom-title`.
    """
    wanted = set(window_weeks(now, weeks))
    oldest = window_start(now, weeks)
    counts: dict[str, dict[str, int]] = {}
    skills: dict[str, dict[str, int]] = {}
    sessions: dict[str, dict[str, int]] = {}
    tally = {"invocations": skills, "sessions": sessions, "sessions_scanned": 0,
             "guidance": {}}
    #: (st_dev, st_ino) of every transcript already processed. A symlink or a
    #: hard-linked copy is the SAME underlying file reachable via a second
    #: path in the walk — reading it twice double-counts every turn in it.
    #: This is deliberately NOT the same thing as deduping turns globally:
    #: inside one non-Cowork root `seen` below still resets per (unique)
    #: file, because two genuinely different transcripts can legitimately
    #: share a message id (a resumed session) and both must still count.
    seen_files: set[tuple[int, int]] = set()
    roots = ([Path(projects_dir)] if isinstance(projects_dir, (str, Path))
             else [Path(root) for root in projects_dir])
    record = events is not None and allowlist is not None
    machine = machine_name() if record else ""
    repos: dict = {}
    copies = LoadedCopies() if record else None
    #: ("t"|"c"|"u", id) of every turn, Skill call and typed entry counted
    #: under an earlier root.
    claimed: set[tuple[str, str]] = set()
    for root in roots:
        if root.is_dir():
            claimed |= _census_root(root, wanted, oldest, counts, tally, seen_files,
                                    claimed, allowlist, events if record else None,
                                    repos, machine, private, copies)
    return counts, tally


def _census_root(root: Path, wanted: set, oldest: datetime, counts: dict,
                 tally: dict, seen_files: set, claimed: set, allowlist,
                 events: list | None, repos: dict, machine: str,
                 private: frozenset[str] = frozenset(),
                 copies: LoadedCopies | None = None) -> set:
    """Walk one transcript root into `counts` and `tally`; return the ids it
    counted. See census_all."""
    skills, sessions = tally["invocations"], tally["sessions"]
    record = events is not None
    kind_of_root = root_kind(root)
    this_root: set[tuple[str, str]] = set()

    def fresh(key) -> bool:
        if key in claimed or key in seen:
            return False
        seen.add(key)
        return True

    for transcript in sorted(root.rglob("*.jsonl")):
        try:
            stat = transcript.stat()
        except OSError:
            continue
        file_id = (stat.st_dev, stat.st_ino)
        if file_id in seen_files:
            continue
        seen_files.add(file_id)
        # A transcript last written before the window cannot hold an entry
        # inside it; skipping it unread is the difference between reading
        # eight weeks of transcripts and reading every one ever made. The
        # bound carries a whole extra week of slack (window_start), so a
        # file being appended to across a week boundary is never dropped.
        if datetime.fromtimestamp(stat.st_mtime, timezone.utc) < oldest:
            continue
        seen = this_root if kind_of_root == "cowork" else set()
        invoked: set[tuple[str, str]] = set()   # (skill, week) in this file
        file_events: list[dict] = []
        pending_model: list[dict] = []  # typed-command events awaiting a model
        # Each record's base-directory message: a Skill call links only by
        # `sourceToolUseID`, a typed command only by `parentUuid`.
        loads: list[dict] = []
        by_call: dict[str, dict] = {}
        by_parent: dict[str, dict] = {}
        title = None
        first_when = first_uuid = None
        texts: list[str] | None = None
        tally["sessions_scanned"] += 1
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
                    if not isinstance(entry, dict):
                        continue
                    kind = entry.get("type")
                    if first_when is None:
                        first_when = parse_ts(entry.get("timestamp"))
                        first_uuid = entry.get("uuid")
                    if kind == "attachment":
                        found = _instruction_texts(entry)
                        if found is not None:
                            texts = (texts or []) + found
                        continue
                    if record and kind in ("summary", "custom-title"):
                        text = entry.get("summary" if kind == "summary" else "customTitle")
                        title = _text(text) or title
                        continue
                    if kind not in ("assistant", "user"):
                        continue
                    message = entry.get("message")
                    if not isinstance(message, dict):
                        continue
                    if record and kind == "user" and entry.get("isMeta") is True:
                        for table, key in ((by_call, entry.get("sourceToolUseID")),
                                           (by_parent, entry.get("parentUuid"))):
                            load = table.get(key) if isinstance(key, str) else None
                            if load is not None and load["base"] is None:
                                load["base"] = base_dir_line(message)
                    # "<synthetic>" marks a message Claude Code wrote itself
                    # (an interrupt or an API error), not a model's turn.
                    if kind == "assistant" and pending_model \
                            and message.get("model") != "<synthetic>":
                        facts = _turn_facts(entry, message)
                        if facts["model"] is not None:
                            for pending in pending_model:
                                pending.update(facts)
                            pending_model.clear()
                    when = parse_ts(entry.get("timestamp"))
                    if when is None:
                        continue
                    week = iso_week(when)
                    if week not in wanted:
                        continue
                    if kind == "user":
                        if allowlist is not None:
                            typed = _typed_skill(message, allowlist, private)
                            uuid = entry.get("uuid")
                            if typed is not None and isinstance(uuid, str) and uuid \
                                    and not fresh(("u", uuid)):
                                typed = None
                            if typed is not None:
                                _bump(skills, typed, week)
                                invoked.add((typed, week))
                                if record:
                                    raw = _typed_command(message)
                                    event = _skill_event(
                                        entry, when, entry.get("uuid"),
                                        raw[1:] if raw.startswith("/") else raw,
                                        repos, machine, kind_of_root)
                                    file_events.append(event)
                                    pending_model.append(event)
                                    load = {"event": event, "when": when,
                                            "base": None}
                                    loads.append(load)
                                    if isinstance(uuid, str) and uuid:
                                        by_parent.setdefault(uuid, load)
                        continue
                    if allowlist is not None and isinstance(message.get("content"), list):
                        for item in message["content"]:
                            if not (isinstance(item, dict)
                                    and item.get("type") == "tool_use"
                                    and item.get("name") == "Skill"):
                                continue
                            call = item.get("id")
                            if isinstance(call, str) and call \
                                    and not fresh(("c", call)):
                                continue
                            given = item.get("input")
                            raw = given.get("skill") if isinstance(given, dict) else None
                            name = skill_key(raw, allowlist, private)
                            _bump(skills, name, week)
                            invoked.add((name, week))
                            if record and _text(raw):
                                event = _skill_event(
                                    entry, when, call, raw, repos, machine,
                                    kind_of_root,
                                    **_turn_facts(entry, message))
                                file_events.append(event)
                                load = {"event": event, "when": when, "base": None}
                                loads.append(load)
                                if isinstance(call, str) and call:
                                    by_call.setdefault(call, load)
                    key = published_key(message.get("model"))
                    if key is None:
                        continue
                    turn = _turn_key(entry, message)
                    if turn is not None and not fresh(("t", turn)):
                        continue
                    _bump(counts, key, week)
        except OSError:
            continue
        for name, week in invoked:
            _bump(sessions, name, week)
        # One guidance state per session, in the week of its first timestamped
        # entry; a session stored twice (Cowork, or under two roots) counts once.
        # A subagent transcript loads no memory of its own, so it would only
        # inflate `unknown`.
        if first_when is not None and iso_week(first_when) in wanted \
                and "subagents" not in transcript.parts \
                and not (isinstance(first_uuid, str) and first_uuid
                         and not fresh(("g", first_uuid))):
            _bump(tally["guidance"], guidance_state(texts), iso_week(first_when))
        for event in file_events:
            event["session_title"] = title
        for load in loads:
            load["event"].update(copies.resolve(
                load["event"]["name"], load["base"], load["when"]))
        if record:
            events.extend(file_events)
        if seen is not this_root:
            this_root |= seen
    return this_root


def build_document(projects_dir: Path, now: datetime,
                   weeks: int = DEFAULT_WEEKS) -> dict:
    """The published artifact. Exactly three keys — see the module docstring."""
    return _document(census_counts(projects_dir, now, weeks), now, weeks)


def _document(counts: dict, now: datetime, weeks: int) -> dict:
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weeks": window_weeks(now, weeks),
        "counts": counts,
    }


def build_weekly_document(tally: dict, now: datetime,
                          weeks: int = DEFAULT_WEEKS, hooks: dict | None = None,
                          cloud: dict | None = None) -> dict:
    """`usage/weekly-local.json`, built by `harness/skill_usage.py`, which
    owns its schema. The window starts at the Monday of its oldest week.
    `hooks` is `hook_tally()`'s result; None adds no hook rows or source.
    `cloud` is `cloud_guidance_tally()`'s; None adds no cloud rows or source."""
    rows = [skill_usage.row(week, "skill", name, n,
                            tally["sessions"].get(name, {}).get(week, 0))
            for name, by_week in tally["invocations"].items()
            for week, n in by_week.items()]
    rows += [skill_usage.guidance_row(week, state, n)
             for state, by_week in tally.get("guidance", {}).items()
             for week, n in by_week.items()]
    if hooks is not None:
        rows += [skill_usage.hook_row(week, name, repo, runs, blocked, runner)
                 for (week, name, repo, runner), (runs, blocked) in hooks["rows"].items()]
    oldest = skill_usage.week_monday(window_weeks(now, weeks)[-1])
    window_from = datetime.fromisoformat(oldest).replace(tzinfo=timezone.utc)
    cloud_source = None
    if cloud is not None:
        rows += [skill_usage.guidance_row(week, state, n, skill_usage.SURFACE_CLOUD)
                 for state, by_week in cloud["guidance"].items()
                 for week, n in by_week.items()]
        rows += [skill_usage.guidance_check_row(week, result, n)
                 for result, by_week in cloud["checks"].items()
                 for week, n in by_week.items()]
        # The Monday of the earliest record's week: no coverage is claimed
        # before the first record.
        earliest = cloud["earliest"]
        record_week = (None if earliest is None else datetime.fromisoformat(
            skill_usage.week_monday(iso_week(earliest))).replace(tzinfo=timezone.utc))
        cloud_source = {"from": max(window_from, record_week or window_from),
                        "records_scanned": cloud["records_scanned"]}
    return skill_usage.document(rows, now, window_from, tally["sessions_scanned"],
                                None if hooks is None else hooks["runs_scanned"],
                                cloud_source)


#: Where the private store keeps records: events/<YYYY-MM>/<machine>.jsonl.
EVENTS_DIR = "events"
_MONTH_RE = re.compile(r"[0-9]{4}-[0-9]{2}")


def merge_events(events_path, store) -> int:
    """Add each record of `events_path` (this script's `--events-out`) to
    `store`/events/<YYYY-MM>/<machine>.jsonl unless its id is already there.

    Existing lines are kept byte for byte, whatever they hold; a file that
    gains a record is rewritten sorted by `ts` (stable, so equal stamps keep
    their order). Returns how many records were added. ValueError for a
    malformed record or a target path that goes through a symbolic link
    (the store is a clone of a branch, and a committed link could point the
    write at `lessons/` or outside the clone). PRIVATE:
    `scripts/publish_usage_census.sh` calls this only on its clone of the
    private `persistent/usage-events` branch, and prints only the count.
    """
    store = Path(store).resolve()
    groups: dict = {}
    with open(events_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            event = json.loads(line)
            if not (isinstance(event, dict) and isinstance(event.get("id"), str)
                    and isinstance(event.get("ts"), str)
                    and isinstance(event.get("machine"), str)
                    and _MONTH_RE.fullmatch(event["ts"][:7])
                    and MACHINE_RE.fullmatch(event["machine"])):
                raise ValueError("an event record is malformed")
            groups.setdefault((event["ts"][:7], event["machine"]), []).append(event)
    added = 0
    for (month, machine), batch in sorted(groups.items()):
        path = store / EVENTS_DIR / month / f"{machine}.jsonl"
        if path.resolve() != path:
            raise ValueError("an event file's path goes through a link")
        kept, ids = [], set()
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                try:
                    old = json.loads(raw)
                except ValueError:
                    old = None
                old = old if isinstance(old, dict) else {}
                if isinstance(old.get("id"), str):
                    ids.add(old["id"])
                kept.append((old["ts"] if isinstance(old.get("ts"), str) else "", raw))
        new = []
        for event in batch:
            if event["id"] not in ids:
                ids.add(event["id"])
                new.append((event["ts"], json.dumps(event, sort_keys=True)))
        if not new:
            continue
        added += len(new)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = sorted(kept + new, key=lambda pair: pair[0])
        path.write_text("".join(raw + "\n" for _, raw in lines), encoding="utf-8")
    return added


def write_events(path: Path, events: list) -> None:
    """JSON lines, sorted by timestamp (then id). PRIVATE: see the docstring."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for event in sorted(events, key=lambda e: (e["ts"], e["id"])):
            f.write(json.dumps(event, sort_keys=True) + "\n")


def _write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, sort_keys=True)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", action="append", default=None,
                        help="Claude Code transcript root; repeat it, or separate "
                             "roots with the OS path separator, for several "
                             "(default ~/.claude/projects)")
    parser.add_argument("--weeks", type=int, default=DEFAULT_WEEKS)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--weekly-out", type=Path, default=None,
                        help="also write weekly skill invocations here "
                             "(published as usage/weekly-local.json)")
    parser.add_argument("--events-out", type=Path, default=None,
                        help="also write one private JSON line per skill "
                             "invocation here (never published publicly)")
    parser.add_argument("--hook-logs", default=None,
                        help="agent-checks run logs, separated by the OS path "
                             "separator; missing files are skipped (default: "
                             "agent-checks' own default path)")
    parser.add_argument("--cloud-guidance", type=Path, default=None,
                        help="checkout of the private persistent/usage-events "
                             "branch; its events/*/cloud-guidance.jsonl are read "
                             "(never written) into cloud guidance rows")
    parser.add_argument("--skill-allowlist-root", type=Path, default=REPO_ROOT,
                        help="repo whose evals/ fixtures and non-coverage.yml "
                             "name the publishable skills (default: this "
                             "script's repo)")
    parser.add_argument("--now", default=None,
                        help="ISO-8601 instant to treat as now (tests and "
                             "scripts/publish_usage_census.sh's test seam); "
                             "default: the wall clock")
    args = parser.parse_args()

    try:
        _require_model_id_re()
    except ImportError:
        # PyYAML (via roster.py) is not installed on this machine. Printed
        # here, not raised: the durable machine that runs this script
        # (evals/usage/CENSUS.md) installs nothing by default,
        # and a bare ImportError traceback used to kill the import of this
        # module before argparse ever ran — even `--help` failed.
        print(PYYAML_MISSING_MESSAGE, file=sys.stderr)
        return 2

    roots = ([DEFAULT_PROJECTS] if args.projects is None else
             [Path(part) for value in args.projects
              for part in value.split(os.pathsep) if part])
    if not any(root.is_dir() for root in roots):
        # Say so and stop, rather than publishing a clean census of nothing —
        # never a clean census of nothing on a surface that cannot do the
        # job. The message names no path: this line reaches a scheduled
        # task's status report.
        print("no Claude Code transcript directory on this surface; "
              "nothing published", file=sys.stderr)
        return 2

    now = parse_ts(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print("--now is not an ISO-8601 instant", file=sys.stderr)
        return 2
    allowlist = None
    repos = private = frozenset()
    if args.weekly_out is not None or args.events_out is not None:
        import eval_coverage
        try:
            allowlist = skill_allowlist(args.skill_allowlist_root)
            repos = public_repos()
            private = private_plugins()
        except (eval_coverage.CensusRefusal, ValueError, OSError):
            # No detail: a refusal message can carry a path, and this line
            # reaches a scheduled task's status report. Nothing is written.
            print("skill allowlist could not be read from the evals "
                  "directory; nothing published", file=sys.stderr)
            return 2
    events = [] if args.events_out is not None else None
    counts, tally = census_all(roots, now, args.weeks, allowlist, events, private)
    hooks = None
    if allowlist is not None:
        paths = ([default_hook_log()] if args.hook_logs is None
                 else [p for p in args.hook_logs.split(os.pathsep) if p])
        hooks = hook_tally(paths, now, args.weeks, repos, events, machine_name())
    document = _document(counts, now, args.weeks)
    _write_json(args.out, document)

    # Non-identifying status line only: counts, and the OUTPUT path the caller
    # already knows — never a model id, never anything from under --projects.
    total = sum(sum(by_week.values()) for by_week in document["counts"].values())
    status = (f"census: {len(document['counts'])} models, {total} assistant turns, "
              f"{args.weeks} weeks -> {args.out}")
    if args.weekly_out is not None:
        cloud = (cloud_guidance_tally(args.cloud_guidance, now, args.weeks)
                 if args.cloud_guidance is not None and args.cloud_guidance.is_dir()
                 else None)
        _write_json(args.weekly_out,
                    build_weekly_document(tally, now, args.weeks, hooks, cloud))
        calls = sum(sum(by_week.values()) for by_week in tally["invocations"].values())
        status += f"; {calls} skill invocations -> {args.weekly_out}"
    if args.events_out is not None:
        write_events(args.events_out, events)
        status += f"; {len(events)} private events -> {args.events_out}"
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
