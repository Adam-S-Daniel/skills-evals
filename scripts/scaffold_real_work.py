#!/usr/bin/env python3
"""Scaffold one real-work fixture from one miner candidate, and gate it.

Part of https://github.com/Adam-S-Daniel/skills-evals/issues/65 and
https://github.com/Adam-S-Daniel/skills-evals/issues/98 (DESIGN.md "The
scaffolder and its gate"). Owner decision Q6, "Routine + own gate": the model
call runs in the ADR 0010 routine, and the scaffold gets its own review gate.
This script is every DETERMINISTIC part of that: the routine's model writes
only the spec (the task text, `interface_strings:` and the checker
selection), and everything else is read from git and GitHub.

    python3 scripts/scaffold_real_work.py snapshot --candidate OWNER__REPO__PR \\
        --out FILE --registry AG/repos.yml \\
        --sync-workflow AG/.github/workflows/sync.yml

    python3 scripts/scaffold_real_work.py build --candidates candidates.json \\
        --key OWNER__REPO__PR --clone PATH --spec spec.json \\
        [--issue-snapshot FILE] --dest evals/real-work

    python3 scripts/scaffold_real_work.py check --fixture DIR [--run]

    python3 scripts/scaffold_real_work.py resolve --event-name NAME \\
        --event-path PATH
    python3 scripts/scaffold_real_work.py gate --repo DIR --base REF \\
        --source REF --branch claude/scaffold-<id> [--expect-sha SHA] \\
        --out DIR --registry AG/repos.yml \\
        --sync-workflow AG/.github/workflows/sync.yml

BUILD writes `<dest>/<repo name>-<pr>/` in the shape of the first three
fixtures (#311): `seed/` is the base tree from `git archive`, with the fleet
agent context stripped (harness/seed_prep.py), the evaluated paths removed,
and oversized files, every symlink and every other e2e spec trimmed;
regular Python source stays through MAX_KEPT_LARGE_BYTES so its fix remains
applicable. `checker/` is the merge commit's copy of each selected test file;
`solution.patch` is the rest of the pull request's diff; and
`issue-before-fix.txt` is the closing issue's title and body as they stood
before the pull request's first commit, with the three provenance keys,
read with `gh api graphql` (a read). That is the one GraphQL read on the
routine's path: REST has no issue body revisions (`userContentEdits`), and a
Claude Code cloud session refuses GraphQL, so there BUILD stops naming the
gap (SNAPSHOT_NEEDS_GRAPHQL) rather than snapshot the issue's current body;
the routine passes the fire workflow's snapshot instead (SNAPSHOT below).
`fixture.yaml` is `draft: true` and `subject: any`. It reads the clone with
`git archive`, `git cat-file` and `git diff` only, and never writes the clone.

SNAPSHOT is that read on its own, for routine-eval-fire.yml: a Claude Code
cloud session refuses GitHub GraphQL, and an issue's body revisions
(`userContentEdits`) have no REST read, so the fire workflow, on Actions with
its read-only token, resolves the candidate's pull request and its closing
issue through REST, as the miner does (mine_real_work.closing_issues), and
the snapshot through GraphQL, and sends the result in the routine's
payload as `issue_snapshot` (Adam, 2026-10-06: "Fire workflow precomputes
(Recommended)"). It writes JSON: null when the pull request closes no issue,
else SNAPSHOT_FIELDS. The repository must be in the fleet, read from
`_agent-guidance`'s default branch as the miner reads it (owner in
SYNC_OWNERS, name in cron_coverage.fleet; Adam, 2026-10-06: "Pin to fleet
owners (Recommended)"), and its GitHub `full_name` must be the name given (a
renamed repository's old name redirects). Several closing issues are refused
(Adam, 2026-10-06: "Keep refusing (Recommended)"). BUILD's
`--issue-snapshot FILE` takes that JSON instead
of reading GitHub, and validates it strictly first; it is untrusted (the
routine wrote the file), so the gate below recomputes it.

CHECK is the validation, reusing the harness's own code: the fixture loads
as the harness loads it, the seed carries no agent context, the size caps
hold, and the answer-leak lint (harness/answer_leak.py) finds no hit
(LEAK_POLICY). With `--run` it also scores the seed (every fail_to_pass test
fails, every pass_to_pass passes) and the seed with solution.patch applied
(all pass), each scoring inside CAP_SECONDS. `--run` installs `deps:` with
network, as a fixture's setup does, and runs the checker: run it in the
routine, never in a workflow that holds a token.

RESOLVE and GATE are run by .github/workflows/routine-scaffold-gate.yml from
the default branch, never from the pushed branch. The branch is UNTRUSTED (a
model run wrote it). GATE reads it only through git plumbing
(scripts/ingest_routine_results.py's helpers): it must only ADD regular
files under `evals/real-work/<id>/`, `<id>` being the branch's own, within
the size caps; the files are then written to `--out` and CHECK runs on them
without `--run`, so nothing from the branch is executed. Then GATE recomputes
the issue snapshot from GitHub, for the pull request the fixture header
names (which must be the fixture id's), with SNAPSHOT's own code, and rejects
the branch unless `issue-before-fix.txt` is byte for byte the recomputed text
and the three provenance times are equal (or, with no closing issue, the
branch carries no snapshot): the routine cannot alter the task's issue text. The recompute runs later
than the fire, so if the chosen revision is deleted, or the issue passes the
100 revisions one query reads, in between, an honest branch is rejected:
fail closed (Adam, 2026-10-06: "Yes, fail closed (Recommended)").
Messages never quote file content.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import yaml  # noqa: E402

import answer_leak  # noqa: E402
import guidance  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import mine_real_work as miner  # noqa: E402
import run_eval  # noqa: E402
import seed_prep  # noqa: E402
from scorers import objective  # noqa: E402

# ---------------------------------------------------------------------------
# Policy, one named constant per choice.

#: What an answer-leak hit does: "reject" (refuse to build, fail the check and
#: the gate) or "warn" (report it for review). Adam, 2026-10-06: "Reject
#: (Recommended)". The miner still records a hit as a warning (Q3).
LEAK_POLICY = "reject"
#: Owner decision Q1: each red and green scoring finishes within 60 s.
CAP_SECONDS = 60
#: The label the gate puts on every scaffold pull request (#65's name).
DRAFT_LABEL = "eval-scaffold"

#: Paths a seed never carries: the agent context the A/B withholds and the
#: subjects under evaluation (Adam, 2026-10-06: "Strip subject + trim").
EVALUATED_PATHS = (".claude", "skills.lock", "agents-md", "skills", ".claude-plugin")
#: A seed file over this size is trimmed, unless KEPT_LARGE names it (the
#: lockfile `deps:` installs from, AGENTS.md's kept section) or it is the
#: seed's copy of a checker file. Regular .py files also stay through
#: MAX_KEPT_LARGE_BYTES, preserving implementation code and its fix patch.
TRIM_BYTES = 100 * 1024
KEPT_LARGE = frozenset({"package-lock.json", "npm-shrinkwrap.json", "AGENTS.md"})
#: e2e/ entries that are specs; only the checker's own stay (Adam,
#: 2026-10-06: "Trim other e2e specs").
E2E_SPEC_SUFFIXES = (".spec.js", ".test.js", ".spec.js-snapshots")
#: A seed plugin manifest's description lists the skills the seed no longer
#: has, so it is replaced with a neutral one; a repository with no entry here
#: is refused rather than guessed at.
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
NEUTRAL_MANIFEST_DESCRIPTIONS = {
    "cms-platform": "cms-platform: a Jekyll + Decap CMS + AWS site platform.",
}

#: Caps on one fixture directory. The largest committed fixture
#: (cms-platform-693) is about 3 MB in about 330 files.
MAX_FIXTURE_FILES = 2000
MAX_FIXTURE_BYTES = 8 * 1024 * 1024
MAX_KEPT_LARGE_BYTES = 1024 * 1024
MAX_YAML_BYTES = 256 * 1024
MAX_PATCH_BYTES = 1024 * 1024

FIXTURE_FILE = "fixture.yaml"
SNAPSHOT_FILE = "issue-before-fix.txt"
PATCH_FILE = "solution.patch"
CHECKER_DIR = "checker"
SEED_DIR = "seed"
#: Everything a fixture directory may hold at its top level.
TOP_LEVEL = frozenset({FIXTURE_FILE, SNAPSHOT_FILE, PATCH_FILE, CHECKER_DIR, SEED_DIR})
#: Directories under which a file may be executable (a seed keeps git's mode).
EXECUTABLE_OK = frozenset({SEED_DIR, CHECKER_DIR})
#: The keys a scaffolded fixture may set: nothing that runs a shell
#: (`setup:`), sets an environment (`env:`) or names a subject.
ALLOWED_KEYS = frozenset({
    "subject", "draft", "strip_agent_context", "deps", "prompt",
    "interface_strings", answer_leak.SNAPSHOT_KEY, *answer_leak.PROVENANCE_KEYS,
    "objective_checks"})
CHECK_ID = "hidden-tests"
CHECK_DESCRIPTION = "The pull request's own tests, hidden from the agent"

REAL_WORK_ROOT = "evals/real-work"
#: A fixture id is also part of a branch name, a REST query string, and a PR
#: title and body, so it is the only barrier there: no `&=?#%` or `/`, and at
#: most 72 characters (64 for the repository name, `-`, seven digits).
FIXTURE_ID = r"[A-Za-z0-9_][A-Za-z0-9._-]{0,63}-[1-9][0-9]{0,6}"
FIXTURE_ID_RE = re.compile(FIXTURE_ID)
BRANCH_RE = re.compile(rf"claude/scaffold-(?P<fixture_id>{FIXTURE_ID})")
REPO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

#: The routine's spec: what only a model can write.
SPEC_KEYS = frozenset({"task_text", "interface_strings", "checker", "deps", "trim", "issue"})
CHECKER_KEYS = frozenset({"files", "argv", "fail_to_pass", "pass_to_pass"})
MAX_TASK_CHARS = 65536
MAX_TRIM = 64

#: One GraphQL read: the issue as it stands, its body revisions and title
#: renames, and the pull request's first commit.
SNAPSHOT_QUERY = """\
query($owner: String!, $name: String!, $issue: Int!, $pr: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $issue) {
      title body createdAt lastEditedAt
      userContentEdits(first: 100) { totalCount nodes { editedAt deletedAt diff } }
      timelineItems(first: 100, itemTypes: [RENAMED_TITLE_EVENT]) {
        totalCount
        nodes { ... on RenamedTitleEvent { createdAt previousTitle currentTitle } }
      }
    }
    pullRequest(number: $pr) { commits(first: 1) { nodes { commit { committedDate } } } }
  }
}"""

#: A miner key, OWNER__REPO__PR: the fire workflow's pattern. An owner has no
#: `_`, so the first `__` ends it; the last `__` starts the number.
KEY_RE = re.compile(r"(?P<owner>[A-Za-z0-9-]+)__(?P<name>[A-Za-z0-9._-]+)__(?P<pr>[1-9][0-9]{0,6})")
#: The `issue_snapshot` the fire workflow sends, key for key and in order.
SNAPSHOT_FIELDS = ("repo", "pr", "issue", "title", "body", *answer_leak.PROVENANCE_KEYS)
#: GitHub caps a title at 256 characters and a body at 65,536; these leave
#: room, and the fire API's 65,536-character payload cap is the real bound.
MAX_TITLE_CHARS = 1024
MAX_BODY_CHARS = 65536
MAX_SNAPSHOT_FILE_BYTES = 1024 * 1024
SEVERAL_CLOSING = ("the pull request closes several issues; scaffold mode snapshots one, "
                   "so this candidate needs a person to choose")
#: The header line BUILD writes naming the pull request and its issue. The
#: gate reads the owner from it (the fixture id has only the name and number)
#: and recomputes from GitHub; the line itself is never trusted further.
SOURCE_LINE_RE = re.compile(
    r"# https://github\.com/(?P<repo>[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100})"
    r"/pull/(?P<pr>[1-9][0-9]{0,6})"
    r"(?:, the fix for https://github\.com/(?P=repo)/issues/(?P<issue>[1-9][0-9]{0,6}))?\.")


#: BUILD's refusal when GraphQL is refused (a Claude Code cloud session).
SNAPSHOT_NEEDS_GRAPHQL = (
    "the issue snapshot needs GitHub GraphQL, which is not available to this "
    "credential: an issue's body revisions (userContentEdits) have no REST read, "
    "so the body as it stood before the first commit cannot be recovered here, and "
    "the scaffold stops rather than use the current body; in the eval routine, "
    "pass the fire payload's issue_snapshot with --issue-snapshot")


class ScaffoldError(Exception):
    """Refusal: exit 2, nothing written."""


# ---------------------------------------------------------------------------
# Git, read-only.

def _git(clone: Path, *args: str) -> bytes:
    done = subprocess.run(["git", "-C", str(clone), *args], capture_output=True)
    if done.returncode:
        # Never echo git's stderr: it can quote repository content.
        raise ScaffoldError(f"git {args[0]} failed (exit {done.returncode})")
    return done.stdout


def _tree_entry(clone: Path, commit: str, path: str) -> tuple[str, str] | None:
    """(mode, blob id) of `path` in `commit`, or None when it is absent."""
    out = _git(clone, "ls-tree", "-z", "--full-tree", commit, "--", path)
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        if name.decode("utf-8", "surrogateescape") == path:
            mode, kind, oid = meta.decode("ascii").split(" ")
            return (mode, oid) if kind == "blob" else None
    return None


def _changed_paths(clone: Path, base: str, merge: str) -> list[str]:
    out = _git(clone, "diff", "--name-only", "-z", "--no-renames", base, merge)
    return sorted(p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p)


# ---------------------------------------------------------------------------
# The issue snapshot.

def _time(value, what: str) -> str:
    if not isinstance(value, str) or not TIME_RE.fullmatch(value):
        raise ScaffoldError(f"{what} is not an ISO-8601 UTC time")
    return value


def snapshot_from_graphql(doc: dict) -> dict:
    """The issue's title and body as they stood before the pull request's
    first commit, and the three provenance times, from SNAPSHOT_QUERY's answer.

    DESIGN.md "What 'pre-existing' rests on": never edited, the body as it
    stands and a null edit time; edited, the last revision at or before the
    first commit, with its time, or the original text (the oldest revision)
    with a null time. A title renamed after the first commit is read back to
    the title it had then.
    """
    try:
        repo = doc["data"]["repository"]
        issue = repo["issue"]
        commits = repo["pullRequest"]["commits"]["nodes"]
    except (KeyError, TypeError):
        raise ScaffoldError("the issue snapshot query returned no issue or pull request") from None
    if not isinstance(issue, dict) or not commits:
        raise ScaffoldError("the issue snapshot query returned no issue or pull request")
    created = _time(issue.get("createdAt"), "issue createdAt")
    first = _time(((commits[0] or {}).get("commit") or {}).get("committedDate"),
                  "first commit committedDate")
    if created > first:
        raise ScaffoldError("the issue was created after the pull request's first commit")
    edits_conn = issue.get("userContentEdits") or {}
    renames_conn = issue.get("timelineItems") or {}
    edits = [e for e in edits_conn.get("nodes") or [] if isinstance(e, dict)]
    renames = [r for r in renames_conn.get("nodes") or [] if isinstance(r, dict) and r]
    if (edits_conn.get("totalCount") or 0) > len(edits) \
            or (renames_conn.get("totalCount") or 0) > len(renames):
        raise ScaffoldError("the issue has more revisions than one query reads")
    if not edits:
        if issue.get("lastEditedAt") is not None:
            raise ScaffoldError("the issue reports an edit but no revisions")
        body, edited = issue.get("body"), None
    else:
        edits.sort(key=lambda e: _time(e.get("editedAt"), "revision editedAt"))
        earlier = [e for e in edits if e["editedAt"] <= first]
        if not earlier:
            raise ScaffoldError("no revision of the issue predates the first commit")
        chosen = earlier[-1]
        if chosen.get("deletedAt") is not None or not isinstance(chosen.get("diff"), str):
            raise ScaffoldError("the revision before the first commit was deleted")
        body = chosen["diff"]
        edited = None if chosen is edits[0] else chosen["editedAt"]
    title = issue.get("title")
    for rename in sorted(renames, key=lambda r: _time(r.get("createdAt"), "rename createdAt"),
                         reverse=True):
        if rename["createdAt"] > first:
            title = rename.get("previousTitle")
    if not isinstance(title, str) or not title.strip() or not isinstance(body, str):
        raise ScaffoldError("the issue snapshot has no title or body")
    snap = {"title": title, "body": body, answer_leak.CREATED_KEY: created,
            answer_leak.EDITED_KEY: edited, answer_leak.FIRST_COMMIT_KEY: first}
    return {**snap, "text": snapshot_text(snap)}


def snapshot_text(snap: dict) -> str:
    """`issue-before-fix.txt`: the title, a blank line, the body, LF endings."""
    text = snap["title"].strip() + "\n\n" + snap["body"].replace("\r\n", "\n").replace("\r", "\n")
    return text if text.endswith("\n") else text + "\n"


def read_snapshot(repo: str, issue: int, pr: int) -> dict:
    owner, name = repo.split("/", 1)
    try:
        doc = miner.gh_json("api", "graphql", "-f", f"query={SNAPSHOT_QUERY}",
                            "-F", f"owner={owner}", "-F", f"name={name}",
                            "-F", f"issue={issue}", "-F", f"pr={pr}")
    except miner.GhGraphQLUnavailable:
        raise ScaffoldError(SNAPSHOT_NEEDS_GRAPHQL) from None
    except (miner.MineError, miner.GhNotFound) as error:
        raise ScaffoldError(f"the issue snapshot read failed: {error}") from None
    return snapshot_from_graphql(doc)


def parse_key(key: str) -> tuple[str, int]:
    """(owner/name, pull request number) from a miner key."""
    match = KEY_RE.fullmatch(key) if isinstance(key, str) else None
    repo = f"{match['owner']}/{match['name']}" if match else ""
    if not match or not REPO_RE.fullmatch(repo):
        raise ScaffoldError("the candidate is not a miner key (OWNER__REPO__PR)")
    return repo, int(match["pr"])


def load_fleet(registry: Path, sync_workflow: Path) -> tuple[list[str], list[str]]:
    """(names, owners) from `_agent-guidance`'s default branch, read as the
    miner reads them: repos.yml's cron_coverage.fleet and sync.yml's
    SYNC_OWNERS."""
    try:
        return miner.load_fleet(registry, sync_workflow)
    except miner.MineError as error:
        raise ScaffoldError(f"the fleet registry is unreadable: {error}") from None


def check_fleet(repo: str, fleet: tuple[list[str], list[str]]) -> None:
    """Refuse a repository outside the fleet, before anything is read (Adam,
    2026-10-06: "Pin to fleet owners (Recommended)"). GitHub names are
    case-insensitive, so the comparison is too."""
    names, owners = fleet
    owner, name = repo.split("/", 1)
    if owner.casefold() not in {o.casefold() for o in owners}:
        raise ScaffoldError("the repository's owner is not a fleet owner (SYNC_OWNERS)")
    if name.casefold() not in {n.casefold() for n in names}:
        raise ScaffoldError("the repository is not in the fleet registry (cron_coverage.fleet)")


def issue_snapshot(repo: str, pr: int, fleet: tuple[list[str], list[str]]) -> dict | None:
    """SNAPSHOT_FIELDS for the merged pull request's one closing issue, or None
    when it closes none. The fire workflow and the gate both call this; the
    repository must be in the fleet and be what GitHub calls it (a renamed
    repository's old name redirects, and its full_name then differs)."""
    check_fleet(repo, fleet)
    try:
        pull = miner.gh_json("api", f"repos/{repo}/pulls/{pr}")
    except (miner.MineError, miner.GhNotFound) as error:
        raise ScaffoldError(f"the pull request read failed: {error}") from None
    if not isinstance(pull, dict) or pull.get("number") != pr or not pull.get("merged_at"):
        raise ScaffoldError("the candidate is not a merged pull request")
    try:
        view = miner.gh_json("api", f"repos/{repo}")
    except (miner.MineError, miner.GhNotFound) as error:
        raise ScaffoldError(f"the repository read failed: {error}") from None
    if not isinstance(view, dict) or view.get("full_name") != repo:
        raise ScaffoldError("the repository's full name on GitHub is not the one named "
                            "(renamed or redirected)")
    # The pull request's closing issues, read as the miner reads them (REST
    # only, #322), so the snapshot names the issue the routine's candidate
    # names.
    try:
        issues = miner.closing_issues(repo, pull, view.get("default_branch"))
    except (miner.MineError, miner.GhNotFound) as error:
        raise ScaffoldError(f"the closing issues read failed: {error}") from None
    if not issues:
        return None
    if len(issues) > 1:
        raise ScaffoldError(SEVERAL_CLOSING)
    snap = read_snapshot(repo, issues[0], pr)
    return {"repo": repo, "pr": pr, "issue": issues[0], "title": snap["title"],
            "body": snap["body"], **{k: snap[k] for k in answer_leak.PROVENANCE_KEYS}}


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


def _no_constant(name):
    raise ValueError(f"not JSON: {name}")


def load_issue_snapshot(path: Path):
    """The fire workflow's `issue_snapshot` JSON as the routine wrote it."""
    try:
        if path.stat().st_size > MAX_SNAPSHOT_FILE_BYTES:
            raise ScaffoldError(f"the issue snapshot is over {MAX_SNAPSHOT_FILE_BYTES} bytes")
        doc = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_no_duplicates,
                         parse_constant=_no_constant)
    except (OSError, UnicodeDecodeError, ValueError):
        raise ScaffoldError("the issue snapshot is not readable JSON") from None
    if doc is not None and not isinstance(doc, dict):
        raise ScaffoldError("the issue snapshot must be an object or null")
    return doc


def _int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_snapshot(doc, repo: str, pr: int, issue: int | None) -> dict | None:
    """The precomputed snapshot checked against the candidate and the spec's
    issue, with its text; None when there is none. Strict: the routine
    passed it on, so nothing about it is assumed."""
    if doc is None:
        if issue is not None:
            raise ScaffoldError("the fire workflow found no closing issue, but the spec names one")
        return None
    if issue is None:
        raise ScaffoldError("the spec names no issue, but the fire workflow sent a snapshot")
    if list(doc) != list(SNAPSHOT_FIELDS):
        raise ScaffoldError(f"the issue snapshot's keys must be exactly {list(SNAPSHOT_FIELDS)}")
    if doc["repo"] != repo:
        raise ScaffoldError("the issue snapshot is for another repository")
    if not _int(doc["pr"]):
        raise ScaffoldError("the issue snapshot's pr is not a pull request number")
    if doc["pr"] != pr:
        raise ScaffoldError("the issue snapshot is for another pull request")
    if not _int(doc["issue"]):
        raise ScaffoldError("the issue snapshot's issue is not an issue number")
    if doc["issue"] != issue:
        raise ScaffoldError(f"the issue snapshot names issue {doc['issue']}, the spec issue {issue}")
    title, body = doc["title"], doc["body"]
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE_CHARS:
        raise ScaffoldError(f"the issue snapshot's title must be nonblank text of at most "
                            f"{MAX_TITLE_CHARS} characters")
    if not isinstance(body, str) or len(body) > MAX_BODY_CHARS:
        raise ScaffoldError(f"the issue snapshot's body must be text of at most "
                            f"{MAX_BODY_CHARS} characters")
    if "\x00" in title or "\x00" in body:
        raise ScaffoldError("the issue snapshot holds a NUL byte")
    created = _time(doc[answer_leak.CREATED_KEY], "issue snapshot issue_created_at")
    first = _time(doc[answer_leak.FIRST_COMMIT_KEY], "issue snapshot first_commit_at")
    edited = doc[answer_leak.EDITED_KEY]
    if edited is not None:
        _time(edited, "issue snapshot issue_last_edited_at")
    if created > first:
        raise ScaffoldError("the issue was created after the pull request's first commit")
    if edited is not None and not created <= edited <= first:
        raise ScaffoldError("the issue snapshot's edit time is not between its creation "
                            "and the first commit")
    text = snapshot_text(doc)
    if len(text.encode("utf-8")) > answer_leak.MAX_SNAPSHOT_BYTES:
        raise ScaffoldError(f"the issue snapshot is over {answer_leak.MAX_SNAPSHOT_BYTES} bytes")
    return {**{k: doc[k] for k in answer_leak.PROVENANCE_KEYS}, "text": text}


# ---------------------------------------------------------------------------
# Inputs.

def _relative(value, what: str) -> str:
    if (not isinstance(value, str) or not value.strip() or "\x00" in value
            or "\\" in value or value.startswith("/")
            or any(part in ("", ".", "..", ".git") for part in value.split("/"))):
        raise ScaffoldError(f"{what} must be a relative path inside the repository")
    return value


def load_candidate(candidates: Path, key: str) -> dict:
    try:
        doc = json.loads(candidates.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ScaffoldError(f"{candidates}: not a readable candidates file") from None
    found = [c for c in doc.get("candidates") or [] if isinstance(c, dict) and c.get("key") == key]
    if len(found) != 1:
        raise ScaffoldError(f"{candidates}: no single candidate with key {key!r}")
    cand = found[0]
    if not isinstance(cand.get("repo"), str) or not REPO_RE.fullmatch(cand["repo"]):
        raise ScaffoldError("the candidate's repo is not owner/name")
    if isinstance(cand.get("pr"), bool) or not isinstance(cand.get("pr"), int) or cand["pr"] < 1:
        raise ScaffoldError("the candidate's pr is not a pull request number")
    for field in ("base_sha", "merge_sha"):
        if not isinstance(cand.get(field), str) or not SHA_RE.fullmatch(cand[field]):
            raise ScaffoldError(f"the candidate's {field} is not a 40-hex commit id")
    return cand


def load_spec(path: Path, candidate: dict) -> dict:
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ScaffoldError(f"{path}: not a readable JSON spec") from None
    if not isinstance(spec, dict):
        raise ScaffoldError("the spec must be a JSON object")
    unknown = set(spec) - SPEC_KEYS
    if unknown:
        raise ScaffoldError(f"the spec has unknown keys {sorted(unknown)}")
    task = spec.get("task_text")
    if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK_CHARS:
        raise ScaffoldError(f"task_text must be nonblank text of at most {MAX_TASK_CHARS} characters")
    checker = spec.get("checker")
    if not isinstance(checker, dict) or set(checker) - CHECKER_KEYS \
            or not {"files", "argv", "fail_to_pass"} <= set(checker):
        raise ScaffoldError(f"checker must be an object with keys from {sorted(CHECKER_KEYS)}, "
                            "including files, argv and fail_to_pass")
    files = checker["files"]
    if not isinstance(files, list) or not files:
        raise ScaffoldError("checker.files must name the pull request's test files")
    tests = set(candidate.get("test_files") or [])
    for rel in files:
        _relative(rel, "checker.files entry")
        if rel not in tests:
            raise ScaffoldError(f"checker.files entry {rel!r} is not one of the candidate's test files")
    if len(set(files)) != len(files):
        raise ScaffoldError("checker.files repeats a file")
    try:
        seed_prep._deps_entries(spec.get("deps"))
    except guidance.GuidanceError as error:
        raise ScaffoldError(str(error)) from None
    trim = spec.get("trim") or []
    if not isinstance(trim, list) or len(trim) > MAX_TRIM:
        raise ScaffoldError(f"trim must be a list of at most {MAX_TRIM} paths")
    for rel in trim:
        _relative(rel, "trim entry")
    issue = spec.get("issue", "closing")
    if issue == "closing":
        closing = candidate.get("closing_issues") or []
        if len(closing) > 1:
            raise ScaffoldError("the pull request closes several issues; the spec must name one")
        issue = closing[0] if closing else None
    if issue is not None and (isinstance(issue, bool) or not isinstance(issue, int) or issue < 1):
        raise ScaffoldError("issue must be an issue number, or null for none")
    return {**spec, "trim": trim, "issue": issue}


# ---------------------------------------------------------------------------
# Build.

def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def trim_seed(seed: Path, checker_files: list[str], extra: list[str], repo_name: str) -> list[str]:
    """Strip and trim the seed in place; the trimmed paths, sorted."""
    trimmed = []
    seed_prep.strip_agent_context(seed)
    for rel in (*EVALUATED_PATHS, *extra):
        if os.path.lexists(seed / rel):
            _remove(seed / rel)
            trimmed.append(rel)
    checker_names = {Path(rel).name for rel in checker_files if rel.startswith("e2e/")}
    e2e = seed / "e2e"
    if e2e.is_dir() and not e2e.is_symlink():
        for entry in sorted(e2e.iterdir()):
            if entry.name.endswith(E2E_SPEC_SUFFIXES) and entry.name not in checker_names:
                _remove(entry)
                trimmed.append(f"e2e/{entry.name}")
    keep = set(checker_files)
    for directory, dirnames, filenames in os.walk(seed):
        for name in sorted(dirnames + filenames):
            path = Path(directory) / name
            rel = path.relative_to(seed).as_posix()
            if path.is_symlink():
                path.unlink()
                trimmed.append(rel)
            elif path.is_file() and path.stat().st_size > TRIM_BYTES \
                    and name not in KEPT_LARGE and rel not in keep \
                    and not (path.suffix == ".py"
                             and path.stat().st_size <= MAX_KEPT_LARGE_BYTES):
                path.unlink()
                trimmed.append(rel)
        dirnames[:] = [d for d in dirnames if (Path(directory) / d).is_dir()
                       and not (Path(directory) / d).is_symlink()]
    for manifest in MANIFESTS:
        path = seed / manifest
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            doc = json.loads(text)
        except (OSError, ValueError):
            raise ScaffoldError(f"seed {manifest} is not readable JSON") from None
        if isinstance(doc, dict) and "description" in doc:
            if repo_name not in NEUTRAL_MANIFEST_DESCRIPTIONS:
                raise ScaffoldError(f"seed {manifest} describes the stripped skills and "
                                    f"NEUTRAL_MANIFEST_DESCRIPTIONS has no entry for {repo_name}")
            # Replace the one value in place, keeping the file's own layout.
            old = f'"description": {json.dumps(doc["description"], ensure_ascii=False)}'
            new = f'"description": {json.dumps(NEUTRAL_MANIFEST_DESCRIPTIONS[repo_name])}'
            if text.count(old) != 1:
                raise ScaffoldError(f"seed {manifest}: its description is not written once, plainly")
            path.write_text(text.replace(old, new), encoding="utf-8")
            if json.loads(path.read_text(encoding="utf-8")) != {
                    **doc, "description": NEUTRAL_MANIFEST_DESCRIPTIONS[repo_name]}:
                raise ScaffoldError(f"seed {manifest}: the description did not change cleanly")
    return sorted(set(trimmed))


class _Literal(yaml.SafeDumper):
    pass


def _str(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Literal.add_representer(str, _str)


def render_fixture(data: dict, header: list[str]) -> str:
    body = yaml.dump(data, Dumper=_Literal, sort_keys=False, allow_unicode=True,
                     width=4096, default_flow_style=None)
    text = "".join(f"# {line}".rstrip() + "\n" for line in header) + "\n" + body
    if yaml.safe_load(text) != data:
        raise ScaffoldError("fixture.yaml does not read back as written")
    return text


def build(candidates: Path, key: str, clone: Path, spec_path: Path, dest: Path,
          issue_snapshot: Path | None = None) -> Path:
    cand = load_candidate(candidates, key)
    spec = load_spec(spec_path, cand)
    repo, pr, base, merge = cand["repo"], cand["pr"], cand["base_sha"], cand["merge_sha"]
    repo_name = repo.split("/", 1)[1]
    fixture_id = f"{repo_name}-{pr}"
    if not FIXTURE_ID_RE.fullmatch(fixture_id):
        raise ScaffoldError(f"{fixture_id!r} is not a fixture directory name")
    target = dest / fixture_id
    if os.path.lexists(target):
        raise ScaffoldError(f"{target} already exists")
    for sha in (base, merge):
        _git(clone, "cat-file", "-e", f"{sha}^{{commit}}")
    checker_files = spec["checker"]["files"]
    for rel in checker_files:
        entry = _tree_entry(clone, merge, rel)
        if entry is None or entry[0] not in ("100644", "100755"):
            raise ScaffoldError(f"checker file {rel!r} is not a regular file in the merge commit")
    if issue_snapshot is not None:
        snapshot = validate_snapshot(load_issue_snapshot(issue_snapshot), repo, pr, spec["issue"])
    elif spec["issue"] is not None:
        snapshot = read_snapshot(repo, spec["issue"], pr)
    else:
        snapshot = None

    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".scaffold-", dir=dest) as tmp:
        work = Path(tmp) / fixture_id
        miner._extract(clone, base, work / SEED_DIR)
        trimmed = trim_seed(work / SEED_DIR, checker_files, spec["trim"], repo_name)
        for rel in checker_files:
            path = work / CHECKER_DIR / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_git(clone, "cat-file", "blob", f"{merge}:{rel}"))
        # The stripped and trimmed paths are not in the seed, so the fix's
        # edits to them (an AGENTS.md note, a skill) could not apply.
        excluded = (set(checker_files) | set(seed_prep.GUIDANCE_FILES)
                    | set(seed_prep.REMOVED_PATHS) | set(EVALUATED_PATHS) | set(trimmed))
        prefixes = tuple(p + "/" for p in excluded)
        patch_paths = [p for p in _changed_paths(clone, base, merge)
                       if p not in excluded and not p.startswith(prefixes)]
        if not patch_paths:
            raise ScaffoldError("the pull request changes nothing outside its tests")
        patch = _git(clone, "diff", "--no-color", "--no-ext-diff", "--no-textconv",
                     "--no-renames", base, merge, "--", *patch_paths)
        (work / PATCH_FILE).write_bytes(patch)

        check = {"id": CHECK_ID, "type": "repo_tests", "description": CHECK_DESCRIPTION,
                 "overlay": CHECKER_DIR, "argv": spec["checker"]["argv"],
                 "fail_to_pass": spec["checker"]["fail_to_pass"]}
        if spec["checker"].get("pass_to_pass"):
            check["pass_to_pass"] = spec["checker"]["pass_to_pass"]
        data = {"subject": run_eval.SUBJECT_ANY, "draft": True, "strip_agent_context": True}
        if spec.get("deps"):
            data["deps"] = spec["deps"]
        data["prompt"] = spec["task_text"].replace("\r\n", "\n")
        if spec.get("interface_strings") is not None:
            data["interface_strings"] = spec["interface_strings"]
        specs = [p for p in trimmed if p.startswith("e2e/") and p.count("/") == 1
                 and p.endswith(E2E_SPEC_SUFFIXES)]
        others = [p for p in trimmed if p not in specs]
        url = f"https://github.com/{repo}"
        header = [f"Real-work fixture: {repo_name}#{pr}, scaffolded by scripts/scaffold_real_work.py.",
                  f"{url}/pull/{pr}"
                  + (f", the fix for {url}/issues/{spec['issue']}." if spec["issue"] else "."),
                  "DRAFT. The prompt and interface_strings below were written by a model in",
                  "the eval routine; a person confirms them before removing `draft: true`.",
                  f"  base  {base} ({cand.get('base_from') or 'base'})",
                  f"  merge {merge}",
                  f"Checker overlay: the merge commit's {', '.join(checker_files)}.",
                  f"Trimmed from the seed: {', '.join(others) if others else 'nothing'}."]
        if specs:
            header.append(f"Also every e2e spec but the checker's own ({len(specs)} trimmed).")
        if snapshot is not None:
            (work / SNAPSHOT_FILE).write_text(snapshot["text"], encoding="utf-8")
            data[answer_leak.SNAPSHOT_KEY] = SNAPSHOT_FILE
            for field in answer_leak.PROVENANCE_KEYS:
                data[field] = snapshot[field]
            header.append(f"{SNAPSHOT_FILE} is {repo}#{spec['issue']} as it stood before the "
                          "pull request's first commit (read with gh api graphql).")
        data["objective_checks"] = [check]
        (work / FIXTURE_FILE).write_text(render_fixture(data, header), encoding="utf-8")

        problems, warnings = static_problems(work, detail=True)
        for line in warnings:
            print(f"scaffold_real_work: warning: {line}", file=sys.stderr)
        if problems:
            raise ScaffoldError("the scaffold does not validate: " + "; ".join(problems))
        work.rename(target)
    return target


# ---------------------------------------------------------------------------
# Check.

def _walk(root: Path):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "node_modules"]
        for name in dirnames + filenames:
            yield Path(directory) / name


def static_problems(fixture_dir: Path, detail: bool = False) -> tuple[list[str], list[str]]:
    """(problems, warnings) for one fixture directory, executing nothing.

    With `detail`, an answer-leak message quotes the leaked runs; without it
    (the gate, reading an untrusted branch) it gives only their count.
    """
    fixture_dir = Path(fixture_dir)
    problems: list[str] = []
    top = {p.name for p in fixture_dir.iterdir()}
    if top - TOP_LEVEL:
        problems.append(f"unexpected top-level entries {sorted(map(repr, top - TOP_LEVEL))}")
    for required in (FIXTURE_FILE, PATCH_FILE, CHECKER_DIR, SEED_DIR):
        if required not in top:
            problems.append(f"{required} is missing")
    if problems:
        return problems, []
    count = total = 0
    for path in _walk(fixture_dir):
        if path.is_symlink():
            problems.append(f"{str(path.relative_to(fixture_dir))!r} is a symlink")
            continue
        if not path.is_file():
            continue
        count += 1
        size = path.stat().st_size
        total += size
        rel = path.relative_to(fixture_dir).as_posix()
        if rel.startswith(SEED_DIR + "/") and size > TRIM_BYTES \
                and ((path.name not in KEPT_LARGE and path.suffix != ".py")
                     or size > MAX_KEPT_LARGE_BYTES):
            problems.append(f"{rel!r} is over the seed's size cap")
    if count > MAX_FIXTURE_FILES or total > MAX_FIXTURE_BYTES:
        problems.append(f"the fixture holds {count} files and {total} bytes, over the caps "
                        f"({MAX_FIXTURE_FILES} files, {MAX_FIXTURE_BYTES} bytes)")
    if (fixture_dir / FIXTURE_FILE).stat().st_size > MAX_YAML_BYTES:
        return problems + ["fixture.yaml is over its size cap"], []
    if (fixture_dir / PATCH_FILE).stat().st_size > MAX_PATCH_BYTES:
        problems.append("solution.patch is over its size cap")
    path = fixture_dir / FIXTURE_FILE
    try:
        fixture = run_eval.load_fixture(fixture_dir)
        unknown = set(fixture) - ALLOWED_KEYS
        if unknown:
            problems.append("fixture.yaml sets keys a scaffold may not: "
                            + (str(sorted(map(str, unknown))) if detail else f"{len(unknown)} key(s)"))
        if fixture.get("draft") is not True:
            problems.append("fixture.yaml is not `draft: true`")
        if fixture.get("subject") != run_eval.SUBJECT_ANY:
            problems.append("fixture.yaml is not `subject: any`")
        if fixture.get("strip_agent_context") is not True:
            problems.append("fixture.yaml is not `strip_agent_context: true`")
        if not isinstance(fixture.get("prompt"), str) or not fixture["prompt"].strip():
            problems.append("fixture.yaml has no prompt")
        checks = fixture.get("objective_checks")
        if not (isinstance(checks, list) and len(checks) == 1 and isinstance(checks[0], dict)
                and checks[0].get("type") == "repo_tests"
                and checks[0].get("overlay") == CHECKER_DIR):
            problems.append("objective_checks must be one repo_tests check on the checker overlay")
        if problems:
            return problems, []
        run_eval.apply_runtime_subject(fixture, None, None, "objective-only", path)
        answer_leak.validate_fixture(fixture, path)
        seed_prep.validate_fixture(fixture, fixture_dir)
    except (guidance.GuidanceError, yaml.YAMLError, UnicodeDecodeError, OSError) as error:
        message = str(error) if detail else type(error).__name__
        return problems + [f"fixture.yaml does not load: {message}"], []
    seed = fixture_dir / SEED_DIR
    problems += [f"seed: {v}" for v in seed_prep.agent_context_violations(seed)]
    problems += [f"seed carries the evaluated path {rel}" for rel in EVALUATED_PATHS
                 if os.path.lexists(seed / rel)]
    try:
        hits = answer_leak.leaked_runs(
            fixture["prompt"], "\n".join(answer_leak.fixture_added_lines(fixture_dir)),
            fixture.get("interface_strings", ()), answer_leak.preexisting_text(fixture, fixture_dir))
    except (UnicodeDecodeError, OSError) as error:
        return problems + [f"the answer-leak lint could not read the fixture: "
                           f"{type(error).__name__}"], []
    warnings = []
    if hits:
        message = (f"the task text shares {len(hits)} four-word run(s) with lines the pull "
                   "request added" + (f": {hits[:5]}" if detail else ""))
        (problems if LEAK_POLICY == "reject" else warnings).append(message)
    return problems, warnings


def red_green(fixture_dir: Path, clock=time.monotonic) -> list[str]:
    """Score the seed (red) and the seed with solution.patch (green).

    Red: every fail_to_pass test fails and every pass_to_pass test passes.
    Green: all pass. Each scoring finishes within CAP_SECONDS. `deps:` are
    installed with network, as a fixture's setup installs them.
    """
    fixture_dir = Path(fixture_dir).resolve()
    path = fixture_dir / FIXTURE_FILE
    fixture = run_eval.apply_runtime_subject(run_eval.load_fixture(fixture_dir), None, None,
                                             "objective-only", path)
    [check] = fixture["objective_checks"]
    f2p, p2p = len(check["fail_to_pass"]), len(check.get("pass_to_pass") or [])
    seed = fixture_dir / SEED_DIR
    problems = []
    for name, fixed in (("red", False), ("green", True)):
        with tempfile.TemporaryDirectory(prefix=f"scaffold-{name}-") as tmp:
            workspace = Path(tmp) / "ws"
            shutil.copytree(seed, workspace, symlinks=True)
            seed_prep.prepare_seed(workspace, fixture)
            error = run_eval.run_setup(workspace, fixture) or seed_prep.seed_guard(workspace, fixture)
            if error is not None:
                problems.append(f"{name}: setup failed ({error['error']})")
                continue
            if fixed:
                done = subprocess.run(["git", "apply", "--whitespace=nowarn",
                                       str(fixture_dir / PATCH_FILE)],
                                      cwd=workspace, capture_output=True, timeout=60)
                if done.returncode:
                    problems.append("green: solution.patch does not apply to the seed")
                    continue
            start = clock()
            [result] = objective.run_checks(fixture, str(workspace), str(seed))
            elapsed = clock() - start
            want = f"fail_to_pass={f2p if fixed else 0}/{f2p} pass_to_pass={p2p}/{p2p}"
            if result["passed"] is not fixed or want not in result["detail"]:
                problems.append(f"{name}: wanted {want}, got {result['detail']}")
            if elapsed > CAP_SECONDS:
                problems.append(f"{name}: scoring took {elapsed:.1f} s, over the {CAP_SECONDS} s cap")
    return problems


# ---------------------------------------------------------------------------
# Gate.

def _safe_rel(rel: str) -> bool:
    parts = rel.split("/")
    return all(p not in ("", ".", "..", ".git") and "\\" not in p
               and all(c.isprintable() for c in p) for p in parts)


def gate(repo: str, base: str, source: str, branch: str, expect_sha: str | None,
         out: Path, *, fleet: tuple[list[str], list[str]]) -> dict:
    """Validate an untrusted `claude/scaffold-<id>` branch and write the
    fixture it adds to `out/<id>/`, or raise ingest.Rejected."""
    match = BRANCH_RE.fullmatch(branch)
    if not match:
        raise ingest.Rejected("branch name is not claude/scaffold-<fixture id>")
    fixture_id = match.group("fixture_id")
    tip = ingest.resolve_commit(repo, source)
    if expect_sha is not None:
        if not SHA_RE.fullmatch(expect_sha):
            raise ingest.Rejected("expected sha is not a 40-hex commit id")
        if tip != expect_sha:
            raise ingest.Rejected("the branch moved since the push that triggered this run; "
                                  "that newer push triggers its own gate")
    base_sha = ingest.resolve_commit(repo, base)
    merge_base = ingest.git(repo, "merge-base", base_sha, tip).decode().strip()
    if not SHA_RE.fullmatch(merge_base):
        raise ingest.Rejected("the branch shares no history with the default branch")
    files = ingest.added_files(repo, merge_base, tip, modes=("100644", "100755"))
    if not files:
        raise ingest.Rejected("the branch adds no files")
    if len(files) > MAX_FIXTURE_FILES:
        raise ingest.Rejected(f"the branch adds more than {MAX_FIXTURE_FILES} files")
    prefix = f"{REAL_WORK_ROOT}/{fixture_id}/"
    if out.exists() and any(out.iterdir()):
        raise ingest.Rejected("the output directory is not empty")
    root = out / fixture_id
    total = 0
    for name, mode, oid in files:
        if not name.startswith(prefix):
            raise ingest.Rejected(f"{name!r}: not under {prefix!r}")
        rel = name[len(prefix):]
        if not _safe_rel(rel):
            raise ingest.Rejected(f"{name!r}: not a plain relative path")
        top = rel.split("/", 1)[0]
        if top not in TOP_LEVEL or (top in (FIXTURE_FILE, PATCH_FILE, SNAPSHOT_FILE)
                                    and rel != top):
            raise ingest.Rejected(f"{name!r}: not a file a scaffold writes")
        if mode == "100755" and top not in EXECUTABLE_OK:
            raise ingest.Rejected(f"{name!r}: executable outside seed/ and checker/")
        size = int(ingest.git(repo, "cat-file", "-s", oid).decode().strip())
        total += size
        if total > MAX_FIXTURE_BYTES:
            raise ingest.Rejected("the branch is over the fixture's total size cap")
        data = ingest.git(repo, "cat-file", "blob", oid)
        if len(data) != size:
            raise ingest.Rejected(f"{name!r}: size changed while reading")
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if mode == "100755":
            path.chmod(0o755)
    problems, _ = static_problems(root)
    if problems:
        raise ingest.Rejected("; ".join(problems[:5]))
    gate_snapshot(root, fixture_id, fleet)
    # Only pattern-checked values: no key may carry content read from the
    # branch (a title, the prompt) into the job that holds a write token.
    return {"fixture_id": fixture_id, "sha": tip, "files": str(len(files))}


def gate_snapshot(fixture_dir: Path, fixture_id: str,
                  fleet: tuple[list[str], list[str]]) -> None:
    """Recompute the issue snapshot from GitHub and require the branch's to
    be the same bytes and times, or absent when there is no closing issue."""
    text = (fixture_dir / FIXTURE_FILE).read_text(encoding="utf-8")
    found = [m for line in text.splitlines() if (m := SOURCE_LINE_RE.fullmatch(line))]
    if len(found) != 1:
        raise ingest.Rejected("fixture.yaml's header does not name its pull request once, "
                              "as the scaffolder writes it")
    repo, pr = found[0]["repo"], int(found[0]["pr"])
    named = int(found[0]["issue"]) if found[0]["issue"] else None
    if f"{repo.split('/', 1)[1]}-{pr}" != fixture_id:
        raise ingest.Rejected("fixture.yaml's header names another pull request than the "
                              "fixture id")
    try:
        expected = issue_snapshot(repo, pr, fleet)
    except ScaffoldError as error:
        raise ingest.Rejected(f"the issue snapshot could not be recomputed: {error}") from None
    fixture = yaml.safe_load(text)
    path = fixture_dir / SNAPSHOT_FILE
    if expected is None:
        if named is not None or os.path.lexists(path) or answer_leak.SNAPSHOT_KEY in fixture:
            raise ingest.Rejected("the branch carries an issue snapshot, but the pull request "
                                  "has no closing issue")
        return
    if named != expected["issue"]:
        raise ingest.Rejected("fixture.yaml's header names another issue than the one the "
                              "pull request closes")
    if answer_leak.SNAPSHOT_KEY not in fixture or not path.is_file():
        raise ingest.Rejected("the fixture has no issue snapshot, but the pull request "
                              "closes an issue")
    if fixture[answer_leak.SNAPSHOT_KEY] != SNAPSHOT_FILE:
        raise ingest.Rejected(f"`{answer_leak.SNAPSHOT_KEY}:` must name {SNAPSHOT_FILE}")
    if path.read_bytes() != snapshot_text(expected).encode("utf-8"):
        raise ingest.Rejected(f"{SNAPSHOT_FILE} differs from the issue snapshot recomputed "
                              "from GitHub")
    for key in answer_leak.PROVENANCE_KEYS:
        if fixture.get(key) != expected[key]:
            raise ingest.Rejected(f"`{key}:` differs from the one recomputed from GitHub")


# ---------------------------------------------------------------------------
# CLI.

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--candidates", type=Path, required=True)
    b.add_argument("--key", required=True)
    b.add_argument("--clone", type=Path, required=True)
    b.add_argument("--spec", type=Path, required=True)
    b.add_argument("--dest", type=Path, default=REPO_ROOT / REAL_WORK_ROOT)
    b.add_argument("--issue-snapshot", type=Path, default=None)
    s = sub.add_parser("snapshot")
    s.add_argument("--candidate", required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--registry", type=Path, required=True)
    s.add_argument("--sync-workflow", type=Path, required=True)
    c = sub.add_parser("check")
    c.add_argument("--fixture", type=Path, required=True)
    c.add_argument("--run", action="store_true")
    r = sub.add_parser("resolve")
    r.add_argument("--event-name", required=True)
    r.add_argument("--event-path", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--repo", required=True)
    g.add_argument("--base", required=True)
    g.add_argument("--source", required=True)
    g.add_argument("--branch", required=True)
    g.add_argument("--expect-sha", default="")
    g.add_argument("--out", required=True, type=Path)
    g.add_argument("--registry", type=Path, required=True)
    g.add_argument("--sync-workflow", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command in ("resolve", "gate"):
        try:
            if args.command == "resolve":
                result = ingest.resolve(args.event_name, args.event_path, BRANCH_RE,
                                        "claude/scaffold-<fixture id>")
            else:
                try:
                    fleet = load_fleet(args.registry, args.sync_workflow)
                except ScaffoldError as error:
                    raise ingest.Rejected(str(error)) from None
                result = gate(args.repo, args.base, args.source, args.branch,
                              args.expect_sha or None, args.out, fleet=fleet)
        except ingest.Rejected as exc:
            message = "".join(ch if ch.isprintable() else repr(ch)[1:-1] for ch in str(exc))
            print(f"rejected: {message}", file=sys.stderr)
            return 1
        for key, value in result.items():
            print(f"{key}={value}")
        return 0
    try:
        if args.command == "build":
            target = build(args.candidates, args.key, args.clone, args.spec, args.dest,
                           args.issue_snapshot)
            print(f"fixture={target}")
            return 0
        if args.command == "snapshot":
            repo, pr = parse_key(args.candidate)
            if os.path.lexists(args.out):
                raise ScaffoldError("the snapshot output already exists")
            doc = issue_snapshot(repo, pr, load_fleet(args.registry, args.sync_workflow))
            args.out.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
            # A status, never the issue's text.
            print("issue_snapshot=" + ("none" if doc is None else f"issue {doc['issue']}"))
            return 0
        problems, warnings = static_problems(args.fixture, detail=True)
        if not problems and args.run:
            problems = red_green(args.fixture)
    except ScaffoldError as error:
        print(f"scaffold_real_work: {error}", file=sys.stderr)
        return 2
    for line in warnings:
        print(f"warning: {line}")
    for line in problems:
        print(f"problem: {line}")
    print(f"check: {len(problems)} problem(s), {len(warnings)} warning(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    with contextlib.suppress(BrokenPipeError):
        sys.exit(main())
