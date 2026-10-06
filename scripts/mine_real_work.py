#!/usr/bin/env python3
"""Mine merged fleet pull requests into real-work fixture candidates.

Part of https://github.com/Adam-S-Daniel/skills-evals/issues/65 and
https://github.com/Adam-S-Daniel/skills-evals/issues/98 (DESIGN.md "Real-work
fixtures from merged pull requests"). READ-ONLY: it calls only `gh` read verbs
and `git archive`, writes only the `--out` path, and refuses an `--out` inside
this repository.

    python3 scripts/mine_real_work.py mine \\
        --registry PATH/_agent-guidance/repos.yml --out /tmp/candidates.json \\
        [--sync-workflow PATH/_agent-guidance/.github/workflows/sync.yml] \\
        [--limit 2000]

    python3 scripts/mine_real_work.py prepare --clone PATH --base SHA \\
        --merge SHA --test-file PATH ... --out /tmp/rg/<repo>-<pr>

    python3 scripts/mine_real_work.py admit --candidates /tmp/candidates.json \\
        --results /tmp/rg --out /tmp/admitted.json [--cap-seconds 60]

MINE. The fleet is `cron_coverage.fleet` in `_agent-guidance`'s `repos.yml`,
never a search. That list holds bare names; the owners are `SYNC_OWNERS` in
the sibling `sync.yml`, read by parsing the YAML. Every name is resolved
under EVERY owner (`gh repo view`), and a name no owner resolves is an error:
the denominator must not shrink silently. A name that resolves to the same
repository under two owners (a rename redirect) counts once. Only PUBLIC
repositories are mined (owner decision Q3); a private one is listed under
`skipped`. Bot pull requests (head ref or author) and `on-hold` ones are
excluded. A candidate is a merged pull request that changes a test file and
a non-test, non-doc file, and whose body (the task text, Q3) is non-empty.
Each candidate records its merge date (Q8: pre/post training-cutoff fixtures
are reported apart, not excluded), its base and an `answer_leak` flag: the
body quotes a line the pull request added. The base is a true merge's first
parent, else (squash or rebase merge) the PR's `baseRefOid`, which can predate
the base branch at merge time; `base_from` says which. A repo whose pull
requests 404, or a PR with no readable merge commit, is skipped with a warning.

PREPARE is the `redgreen.sh` tree step: `git archive` of base and merge into
`<out>/red` and `<out>/green`, with the merge's test files laid over `red`.
It runs nothing. Run the checker in each tree yourself, with no network,
writing JUnit XML to `<results>/<key>/red.xml` and `green.xml`, and the two
durations in seconds to `run.json` (`{"red_secs": .., "green_secs": ..,
"timed_out": false}`), where `<key>` is the candidate's `key`:

    unshare --user --map-current-user --net --pid --fork --mount-proc -- \\
        python3 -m pytest -q -p no:cacheprovider --junitxml=red.xml <tests>

ADMIT reads those results. FAIL_TO_PASS is every test that fails on red and
passes on green. A test that fails on green too, or whose red failure is a
missing package or the network, is ENVIRONMENTAL and is excluded (fixture 8,
_agent-guidance#82: `node_modules/yaml is missing`). A red failure that is a
missing name the fix invented (`is not a function`, `ImportError`,
`AttributeError`) is INTERFACE-COUPLED (fixture 4, cms-platform#430) and
rejects the candidate unless the task text names that interface. A candidate
is admitted only with FAIL_TO_PASS >= 1, no interface coupling and both runs
inside the cap (owner decision Q1: per-test selection under 60 s).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _repo_roots() -> list[Path]:
    """This checkout and, when it is a worktree, the main checkout too."""
    roots = [REPO_ROOT]
    done = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--path-format=absolute",
                           "--git-common-dir"], capture_output=True, text=True)
    if done.returncode == 0 and done.stdout.strip():
        common = Path(done.stdout.strip()).resolve()
        if common.name == ".git" and common.parent not in roots:
            roots.append(common.parent)
    return roots

#: Head refs that automation opens (session-23 classify.py, plus DESIGN.md's
#: own `scaffold/`).
BOT_HEAD = re.compile(r"^(cms/|agents-md-sync|skills-lock-bump|dependabot|platform/"
                      r"|roster/|automated|persistent/|scaffold/)")
TEST_PATH = re.compile(r"(^|/)(test|tests|e2e|spec|__tests__)/|_test\.(py|go|rb|sh)$"
                       r"|\.test\.(js|ts|mjs)$|\.spec\.(js|ts)$|(^|/)test_[^/]*\.py$|\.bats$")
DOC_PATH = re.compile(r"\.(md|txt)$")
TOUCHES = {
    "adr": re.compile(r"(^|/)docs/decisions/\d{4}-"),
    "workflows": re.compile(r"^\.github/workflows/"),
    "e2e-specs": re.compile(r"(^|/)e2e/.*\.(spec|test)\.js$"),
    "shell": re.compile(r"\.sh$"),
    "skill-md": re.compile(r"(^|/)SKILL\.md$"),
    "guidance": re.compile(r"agents-md/(base\.md|sections/)"),
}
PR_FIELDS = ("number,title,body,files,closingIssuesReferences,mergeCommit,headRefName,"
             "additions,deletions,author,mergedAt,labels,url,baseRefOid")
#: A quoted diff line shorter than this is too generic to call a leak.
LEAK_MIN_CHARS = 20
#: `gh pr list` returns at most this many files per pull request.
FILES_CAP = 100
DEFAULT_CAP_SECONDS = 60

#: A red failure that says the ENVIRONMENT is missing something.
ENV_SIGNS = re.compile(
    r"node_modules/\S+ is missing|No module named|Cannot find module|command not found"
    r"|ENOTFOUND|EAI_AGAIN|getaddrinfo|Could not resolve host|Network is unreachable"
    r"|Temporary failure in name resolution")
#: A red failure that says a NAME the fix introduced does not exist yet.
INTERFACE_NAMES = (
    re.compile(r"([\w$.]+) is not a (?:function|constructor)"),
    re.compile(r"cannot import name '([\w.]+)'"),
    re.compile(r"has no attribute '(\w+)'"),
    re.compile(r"does not provide an export named '(\w+)'"),
    re.compile(r"'?(\w+)'? is not exported"),
)
INTERFACE_SIGNS = re.compile(r"ImportError|AttributeError|is not a (?:function|constructor)"
                             r"|does not provide an export named|is not exported")
MODULE_NAMED = re.compile(r"No module named '([\w.]+)'|Cannot find module '([^']+)'")


class MineError(Exception):
    """Refusal: exit 2, nothing written."""


# ── gh (read verbs only) ─────────────────────────────────────────────────────

class GhNotFound(Exception):
    pass


def gh_json(*args: str):
    done = subprocess.run(["gh", *args], capture_output=True, text=True)
    if done.returncode:
        err = done.stderr or ""
        if "Could not resolve to a Repository" in err or "HTTP 404" in err:
            raise GhNotFound(" ".join(args[:3]))
        # Status only: never echo an API body.
        raise MineError(f"gh {' '.join(args[:2])} failed (exit {done.returncode})")
    return json.loads(done.stdout)


def gh_text(*args: str) -> str:
    done = subprocess.run(["gh", *args], capture_output=True, text=True)
    if done.returncode:
        raise MineError(f"gh {' '.join(args[:2])} failed (exit {done.returncode})")
    return done.stdout


# ── the fleet ────────────────────────────────────────────────────────────────

def _find_key(node, key):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            yield from _find_key(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _find_key(item, key)


def load_fleet(registry: Path, sync_workflow: Path) -> tuple[list[str], list[str]]:
    import yaml

    try:
        doc = yaml.safe_load(registry.read_text(encoding="utf-8"))
        names = doc["cron_coverage"]["fleet"]
    except (OSError, yaml.YAMLError, KeyError, TypeError) as error:
        raise MineError(f"{registry}: no cron_coverage.fleet ({type(error).__name__})")
    if not names or not all(isinstance(n, str) and n for n in names):
        raise MineError(f"{registry}: cron_coverage.fleet is empty or malformed")
    try:
        workflow = yaml.safe_load(sync_workflow.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise MineError(f"{sync_workflow}: unreadable ({type(error).__name__})")
    values = {str(v) for v in _find_key(workflow, "SYNC_OWNERS")}
    if len(values) != 1:
        raise MineError(f"{sync_workflow}: expected one SYNC_OWNERS value, found {len(values)}")
    owners = values.pop().split()
    if not owners:
        raise MineError(f"{sync_workflow}: SYNC_OWNERS is empty")
    return names, owners


def resolve_fleet(names: list[str], owners: list[str]) -> list[dict]:
    """Every name under every owner; a name no owner resolves is an error."""
    resolved, unresolved, seen = [], [], set()
    for name in names:
        hits = []
        for owner in owners:
            try:
                view = gh_json("repo", "view", f"{owner}/{name}", "--json",
                               "nameWithOwner,visibility,isFork,isArchived")
            except GhNotFound:
                continue
            hits.append(view)
        if not hits:
            unresolved.append(name)
            continue
        for view in hits:
            if view["nameWithOwner"] not in seen:
                seen.add(view["nameWithOwner"])
                resolved.append(view)
    if unresolved:
        raise MineError(f"fleet names no owner in {owners} resolves (a 404 can also mean "
                        f"this credential cannot see them): {unresolved}")
    return resolved


# ── classification ───────────────────────────────────────────────────────────

def is_bot(pr: dict) -> bool:
    author = pr.get("author") or {}
    login = author.get("login") or ""
    return bool(BOT_HEAD.search(pr.get("headRefName") or "") or author.get("is_bot")
                or login.startswith("app/") or login.endswith("[bot]"))


def on_hold(pr: dict) -> bool:
    return any((label or {}).get("name") == "on-hold" for label in pr.get("labels") or [])


def split_files(pr: dict) -> tuple[list[str], list[str]]:
    paths = [f["path"] for f in pr.get("files") or []]
    tests = [p for p in paths if TEST_PATH.search(p)]
    source = [p for p in paths if not TEST_PATH.search(p) and not DOC_PATH.search(p)]
    return tests, source


def added_lines(diff: str) -> list[str]:
    """Added lines of non-doc files in a unified diff, stripped."""
    lines, current = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].removeprefix("b/")
        elif line.startswith("+") and not DOC_PATH.search(current):
            lines.append(line[1:].strip())
    return lines


def answer_leak(body: str, diff: str) -> dict:
    flat = " ".join(body.split())
    quoted = []
    for line in added_lines(diff):
        text = " ".join(line.split())
        if len(text) >= LEAK_MIN_CHARS and text in flat and text not in quoted:
            quoted.append(text)
    return {"flag": bool(quoted), "quoted_lines": quoted[:5]}


def mine(registry: Path, sync_workflow: Path, limit: int) -> dict:
    names, owners = load_fleet(registry, sync_workflow)
    repos = resolve_fleet(names, owners)
    out = {"registry": str(registry), "owners": owners, "fleet": names,
           "skipped": [], "summary": [], "candidates": []}
    for view in repos:
        repo = view["nameWithOwner"]
        if view.get("visibility") != "PUBLIC":
            out["skipped"].append({"repo": repo, "reason": "not-public"})
            continue
        try:
            prs = gh_json("pr", "list", "--repo", repo, "--state", "merged",
                          "--limit", str(limit), "--json", PR_FIELDS)
        except GhNotFound:
            print(f"mine_real_work: warning: {repo}: pull requests not readable (404); skipped",
                  file=sys.stderr)
            out["skipped"].append({"repo": repo, "reason": "pr-list-404"})
            continue
        counts = {"repo": repo, "merged": len(prs), "bot": 0, "on_hold": 0,
                  "not_replayable": 0, "no_task_text": 0, "no_merge_commit": 0,
                  "candidates": 0}
        for pr in prs:
            if is_bot(pr):
                counts["bot"] += 1
                continue
            if on_hold(pr):
                counts["on_hold"] += 1
                continue
            tests, source = split_files(pr)
            if not (tests and source):
                counts["not_replayable"] += 1
                continue
            body = (pr.get("body") or "").strip()
            if not body:
                counts["no_task_text"] += 1
                continue
            merge_sha = (pr.get("mergeCommit") or {}).get("oid")
            commit = None
            if merge_sha:
                try:
                    commit = gh_json("api", f"repos/{repo}/commits/{merge_sha}")
                except GhNotFound:
                    commit = None
            if commit is None:
                print(f"mine_real_work: warning: {repo}#{pr['number']}: no readable merge "
                      "commit; skipped", file=sys.stderr)
                counts["no_merge_commit"] += 1
                continue
            parents = [p["sha"] for p in commit.get("parents") or []]
            # A true merge's first parent is the base. A single-parent merge
            # commit is a squash or a rebase merge, and for a rebase merge the
            # first parent is the previous rebased commit, so the base is the
            # PR's own baseRefOid (which may predate the base branch's tip at
            # merge time).
            if len(parents) >= 2:
                base_sha, base_from = parents[0], "merge-first-parent"
            else:
                base_sha, base_from = pr.get("baseRefOid"), "pr-base-ref-oid"
            diff = gh_text("pr", "diff", str(pr["number"]), "--repo", repo)
            paths = [f["path"] for f in pr.get("files") or []]
            out["candidates"].append({
                "key": f"{repo.replace('/', '__')}__{pr['number']}",
                "repo": repo, "pr": pr["number"], "url": pr.get("url"),
                "title": pr.get("title"), "task_text": body,
                "spec_style": "sketch" if "```" in body else "symptom",
                "merged_at": pr.get("mergedAt"), "merge_sha": merge_sha,
                "base_sha": base_sha, "base_from": base_from,
                "head_ref": pr.get("headRefName"),
                "closing_issues": [i.get("number") for i in pr.get("closingIssuesReferences") or []],
                "churn": (pr.get("additions") or 0) + (pr.get("deletions") or 0),
                "test_files": tests, "source_files": source,
                "files_truncated": len(paths) >= FILES_CAP,
                "touches": sorted(k for k, rx in TOUCHES.items() if any(rx.search(p) for p in paths)),
                "answer_leak": answer_leak(body, diff),
            })
            counts["candidates"] += 1
        out["summary"].append(counts)
    return out


# ── prepare (redgreen.sh's tree step) ────────────────────────────────────────

def _extract(clone: Path, ref: str, dest: Path) -> None:
    done = subprocess.run(["git", "-C", str(clone), "archive", "--format=tar",
                           "--end-of-options", ref],
                          capture_output=True)
    if done.returncode:
        raise MineError(f"git archive {ref} failed (exit {done.returncode})")
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(done.stdout)) as tar:
        tar.extractall(dest, filter="data")


def prepare(clone: Path, base: str, merge: str, test_files: list[str], out: Path) -> None:
    if out.exists():
        raise MineError(f"{out} already exists")
    red, green = out / "red", out / "green"
    _extract(clone, base, red)
    _extract(clone, merge, green)
    for rel in test_files:
        source = (green / rel).resolve()
        target = (red / rel).resolve()
        if not (source.is_relative_to(green.resolve()) and target.is_relative_to(red.resolve())):
            raise MineError(f"test file escapes the tree: {rel}")
        if not source.is_file():
            raise MineError(f"test file not in the merge tree: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


# ── admit ────────────────────────────────────────────────────────────────────

def read_junit(path: Path) -> dict[str, dict]:
    """{test id: {"outcome": pass|fail|skip, "message": str}}."""
    cases = {}
    for case in ET.parse(path).getroot().iter("testcase"):
        test_id = "::".join(x for x in (case.get("classname"), case.get("name")) if x)
        outcome, message = "pass", ""
        for child in case:
            if child.tag in ("failure", "error"):
                outcome = "fail"
                message = " ".join(x for x in (child.get("message"), child.text) if x)
                break
            if child.tag == "skipped":
                outcome = "skip"
        # A repeated id (a retry, a parametrized name) never lets a later
        # pass hide an earlier failure.
        if cases.get(test_id, {}).get("outcome") == "fail":
            continue
        cases[test_id] = {"outcome": outcome, "message": message}
    return cases


def _interface_name(message: str) -> str | None:
    for rx in INTERFACE_NAMES:
        match = rx.search(message)
        if match:
            return match.group(1).split(".")[-1]
    return None


def _missing_module_is_ours(message: str, source_files: list[str]) -> bool:
    """`Cannot find module './x'` or `No module named 'x'` where x is a file
    the pull request touched: the fix invented it (interface), not the env."""
    match = MODULE_NAMED.search(message)
    if not match:
        return False
    if match.group(2) is not None:
        return match.group(2).startswith((".", "/"))
    stems = {Path(p).stem for p in source_files}
    return match.group(1).split(".")[-1] in stems


def admit(candidate: dict, red: dict, green: dict, run: dict,
          cap_seconds: int = DEFAULT_CAP_SECONDS) -> dict:
    task = candidate.get("task_text") or ""
    sources = candidate.get("source_files") or []
    environmental, coupled, fail_to_pass, pass_to_pass = [], [], [], []
    for test_id, result in sorted(red.items()):
        after = green.get(test_id, {}).get("outcome")
        if result["outcome"] == "pass":
            if after == "pass":
                pass_to_pass.append(test_id)
            continue
        if result["outcome"] != "fail":
            continue
        message = result["message"]
        if after != "pass":
            environmental.append(test_id)
        elif _missing_module_is_ours(message, sources):
            coupled.append({"test": test_id, "name": None})
        elif ENV_SIGNS.search(message):
            environmental.append(test_id)
        elif INTERFACE_SIGNS.search(message):
            name = _interface_name(message)
            if name and re.search(rf"\b{re.escape(name)}\b", task):
                fail_to_pass.append(test_id)
            else:
                coupled.append({"test": test_id, "name": name})
        else:
            fail_to_pass.append(test_id)
    reasons = []
    if run.get("timed_out") or max(run.get("red_secs", 0), run.get("green_secs", 0)) > cap_seconds:
        reasons.append("over-cap")
    if coupled:
        reasons.append("interface-coupled")
    if not fail_to_pass:
        reasons.append("environmental" if environmental else "no-fail-to-pass")
    return {"key": candidate["key"], "admitted": not reasons, "reasons": reasons,
            "fail_to_pass": fail_to_pass, "pass_to_pass": pass_to_pass,
            "environmental": environmental, "interface_coupled": coupled,
            "merged_at": candidate.get("merged_at")}


def admit_all(candidates: Path, results: Path, cap_seconds: int) -> dict:
    doc = json.loads(candidates.read_text(encoding="utf-8"))
    rows, missing = [], []
    for cand in doc["candidates"]:
        where = results / cand["key"]
        if not (where / "red.xml").is_file() or not (where / "green.xml").is_file():
            missing.append(cand["key"])
            continue
        run_path = where / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8")) if run_path.is_file() else {"timed_out": True}
        try:
            red, green = read_junit(where / "red.xml"), read_junit(where / "green.xml")
        except ET.ParseError:
            rows.append({"key": cand["key"], "admitted": False,
                         "reasons": ["unreadable-results"], "fail_to_pass": [],
                         "pass_to_pass": [], "environmental": [], "interface_coupled": [],
                         "merged_at": cand.get("merged_at")})
            continue
        rows.append(admit(cand, red, green, run, cap_seconds))
    return {"cap_seconds": cap_seconds, "admissions": rows, "not_run": missing}


# ── CLI ──────────────────────────────────────────────────────────────────────

def _outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    for root in _repo_roots():
        if resolved.is_relative_to(root):
            raise MineError(f"--out {path} is inside {root}; this script never writes the repo")
    return resolved


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False,
                                     encoding="utf-8", suffix=".tmp") as handle:
        json.dump(doc, handle, indent=1)
        handle.write("\n")
    Path(handle.name).replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("mine")
    m.add_argument("--registry", type=Path, required=True)
    m.add_argument("--sync-workflow", type=Path)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--limit", type=int, default=2000)
    p = sub.add_parser("prepare")
    p.add_argument("--clone", type=Path, required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--merge", required=True)
    p.add_argument("--test-file", action="append", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("admit")
    a.add_argument("--candidates", type=Path, required=True)
    a.add_argument("--results", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--cap-seconds", type=int, default=DEFAULT_CAP_SECONDS)
    args = parser.parse_args(argv)
    try:
        out = _outside_repo(args.out)
        if args.command == "mine":
            sync = args.sync_workflow or args.registry.parent / ".github/workflows/sync.yml"
            doc = mine(args.registry, sync, args.limit)
            _write(out, doc)
            print(f"mine: {len(doc['candidates'])} candidates from "
                  f"{len(doc['summary'])} public repos, {len(doc['skipped'])} skipped")
        elif args.command == "prepare":
            prepare(args.clone, args.base, args.merge, args.test_file, out)
            print(f"prepare: red and green trees under {out}")
        else:
            doc = admit_all(args.candidates, args.results, args.cap_seconds)
            _write(out, doc)
            admitted = sum(row["admitted"] for row in doc["admissions"])
            print(f"admit: {admitted} of {len(doc['admissions'])} admitted, "
                  f"{len(doc['not_run'])} not run")
    except MineError as error:
        print(f"mine_real_work: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
