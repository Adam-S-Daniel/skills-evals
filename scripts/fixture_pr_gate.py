#!/usr/bin/env python3
"""Decide whether a fixture pull request answering a fixture-need issue may
merge itself (skills-evals#659 follow-up; Adam, 2026-10-26: "closed loop with
no human in the loop").

    fixture_pr_gate.py classify --repo DIR --base REF --source REF \\
        --pr FILE --issues FILE

The weekly sweep files one `agent-ready` issue per `needs-fixtures` or
`needs-harder-fixtures` skill or guidance section (scripts/work_item_issues.py).
The fleet worker's issue pass answers one with a pull request that adds
fixtures; it never merges. .github/workflows/fixture-pr-gate.yml runs this
from the default branch, never from the pull request, and arms auto-merge
(merge commit, `--match-head-commit`) when the answer is `eligible`, so the
required `test` check is what decides the merge. The exception is repo-settings
ADR 0018.

IN THE LANE (`lane=true`) means: the pull request's author is
`Adam-S-Daniel` (the account the fleet worker writes as), it carries the
`agent-authored` label, its head branch is in this repository, and its body
names, with `Refs` or a closing keyword, exactly one open issue
github-actions[bot] opened whose body holds a fixture-need marker line. Only
a pull request in the lane is ever armed or disarmed here; promotion,
eval-scope and scaffold pull requests arm themselves and are left alone.

ELIGIBLE (`eligible=true`) means, on top of the lane, over the diff from the
merge base to the head (git plumbing only; nothing from the branch runs):

* every change ADDS a regular file (mode 100644 or 100755) under a fixture
  directory that does not exist on the base: `evals/<skill>/<name>/` for a
  skill need, `evals/guidance/<section>/<name>/` for a section need;
* each new directory has a fixture.yaml that loads as a mapping naming that
  subject (`skill: <skill>` and the adam-agentskills registry, or
  `subject: guidance` and `section: <section>`) and is not `draft: true`;
* the only other change is to evals/unscheduled.yml (a skill fixture, listed
  with draft_new_skill.ISOLATION_REASON, so scripts/contextualize_fixtures.py
  gives it a context and schedules it) or evals/scheduled.yml (a guidance
  fixture), and that change only appends entries for the new directories;
* at most MAX_FILE_BYTES per file and MAX_TOTAL_BYTES in all.

Output, for $GITHUB_OUTPUT: `lane=`, `eligible=`, `issue=`, `reason=` (fixed
text, never file content). Exit 0 on any decision; exit 2 on bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import draft_new_skill  # noqa: E402

AUTHOR = "Adam-S-Daniel"
LABEL = "agent-authored"
ISSUE_AUTHOR = "github-actions[bot]"
REGISTRY = "https://github.com/Adam-S-Daniel/adam-agentskills"
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 5_000_000
_REF = re.compile(r"\b(?:refs|close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+"
                  r"(?:(?:https://github\.com/)?Adam-S-Daniel/skills-evals(?:/issues/|#)|#)"
                  r"([1-9][0-9]{0,6})\b", re.I)
_NEED = re.compile(r"<!-- skills-evals:(needs-fixtures|needs-harder-fixtures):(\S+) -->")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class GateError(Exception):
    """Bad input: the gate cannot judge."""


def _git(repo: Path, *args: str) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if done.returncode != 0:
        raise GateError(f"git {args[0]} failed")
    return done.stdout


def need_of(pr: dict, issues: list) -> tuple:
    """(lane, issue number, kind, subject key, reason)."""
    user = (pr.get("user") or {}).get("login")
    labels = {label.get("name") for label in pr.get("labels") or [] if isinstance(label, dict)}
    head_repo = ((pr.get("head") or {}).get("repo") or {}).get("full_name")
    base_repo = ((pr.get("base") or {}).get("repo") or {}).get("full_name")
    if user != AUTHOR or LABEL not in labels or not head_repo or head_repo != base_repo:
        return False, None, None, None, "not a fleet worker pull request"
    numbers = {int(n) for n in _REF.findall(pr.get("body") or "")}
    found = []
    for issue in issues:
        if issue.get("number") not in numbers or issue.get("state") != "open" \
                or (issue.get("user") or {}).get("login") != ISSUE_AUTHOR:
            continue
        for line in (issue.get("body") or "").splitlines():
            match = _NEED.fullmatch(line.strip())
            if match:
                found.append((issue["number"], *match.groups()))
                break
    if len(found) != 1:
        return False, None, None, None, "it names no single open fixture-need issue"
    number, kind, key = found[0]
    return True, number, kind, key, ""


def _entries(text: str | None) -> list:
    if text is None:
        return []
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or not isinstance(doc.get("fixtures"), list):
        raise ValueError("not a fixtures list")
    return doc["fixtures"]


def _appended(before: str, after: str, allowed: set, check) -> set:
    """The paths `after` appends to `before`, each in `allowed` and passing
    `check`; ValueError on any other change."""
    old, new = _entries(before), _entries(after)
    if new[:len(old)] != old or yaml.safe_load(before).keys() != yaml.safe_load(after).keys():
        raise ValueError("an existing entry changed")
    paths = set()
    for entry in new[len(old):]:
        if not isinstance(entry, dict) or entry.get("path") not in allowed or not check(entry):
            raise ValueError("an appended entry is not one of the new fixtures")
        paths.add(entry["path"])
    return paths


def classify(repo: Path, base: str, source: str, pr: dict, issues: list) -> dict:
    lane, number, kind, key, reason = need_of(pr, issues)
    out = {"lane": lane, "eligible": False, "issue": number or "", "reason": reason}
    if not lane:
        return out

    def refuse(why: str) -> dict:
        return {**out, "reason": why}

    section = key.startswith("guidance/")
    subject = key.split("/", 1)[1] if section else key
    prefix = f"evals/guidance/{subject}/" if section else f"evals/{subject}/"
    merge_base = _git(repo, "merge-base", base, source).decode().strip()
    raw = _git(repo, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", merge_base, source)
    fields = raw.split(b"\0")
    changes = []
    for i in range(0, len(fields) - 1, 2):
        meta, path = fields[i].decode(), fields[i + 1].decode("utf-8", "replace")
        parts = meta.lstrip(":").split()
        changes.append((parts[1], parts[3], parts[4], path))  # new mode, new sha, status, path
    new_dirs, others, total = set(), {}, 0
    for mode, sha, status, path in changes:
        if path in ("evals/scheduled.yml", "evals/unscheduled.yml") and status == "M":
            others[path] = sha
            continue
        if status != "A" or mode not in ("100644", "100755") or not path.startswith(prefix):
            return refuse("a change is not an added regular file under a new fixture directory")
        name = path[len(prefix):].split("/", 1)[0]
        if not _NAME.fullmatch(name) or "/" not in path[len(prefix):]:
            return refuse("a file is not inside a fixture directory")
        directory = prefix + name
        size = int(_git(repo, "cat-file", "-s", sha).decode().strip())
        if size > MAX_FILE_BYTES:
            return refuse("a file is over the size cap")
        total += size
        new_dirs.add(directory)
    if total > MAX_TOTAL_BYTES:
        return refuse("the pull request is over the total size cap")
    if not new_dirs:
        return refuse("it adds no fixture")
    for directory in sorted(new_dirs):
        if _git(repo, "ls-tree", merge_base, "--", directory).strip() \
                or _git(repo, "ls-tree", base, "--", directory).strip():
            return refuse("a fixture directory already exists on the base")
        try:
            doc = yaml.safe_load(_git(repo, "show", f"{source}:{directory}/fixture.yaml"))
        except (GateError, yaml.YAMLError):
            return refuse("a new fixture directory has no fixture.yaml that loads")
        if not isinstance(doc, dict) or doc.get("draft") is True:
            return refuse("a new fixture.yaml is not a mapping, or is a draft")
        if section and (doc.get("subject") != "guidance" or doc.get("section") != subject):
            return refuse("a new guidance fixture does not name its section")
        if not section and (doc.get("skill") != subject or doc.get("registry") != REGISTRY
                            or "subject" in doc):
            return refuse("a new skill fixture does not name its skill and adam-agentskills")
    allowed_list = "evals/scheduled.yml" if section else "evals/unscheduled.yml"
    if set(others) - {allowed_list}:
        return refuse("it edits the wrong fixture list for this subject")
    if allowed_list in others:
        def check(entry):
            if section:
                return set(entry) == {"path", "readiness"} and isinstance(entry["readiness"], str)
            return entry == {"path": entry["path"], "reason": draft_new_skill.ISOLATION_REASON}
        try:
            before = _git(repo, "show", f"{merge_base}:{allowed_list}").decode()
            after = _git(repo, "show", f"{source}:{allowed_list}").decode()
            _appended(before, after, new_dirs, check)
        except (ValueError, yaml.YAMLError, UnicodeDecodeError, AttributeError):
            return refuse(f"{allowed_list} changes more than appending the new fixtures")
    return {**out, "eligible": True, "reason": f"adds {len(new_dirs)} fixture(s) for {key}"}


def main(argv: list | None = None, out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--repo", type=Path, required=True)
    c.add_argument("--base", required=True)
    c.add_argument("--source", required=True)
    c.add_argument("--pr", type=Path, required=True)
    c.add_argument("--issues", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        pr = json.loads(args.pr.read_text(encoding="utf-8"))
        issues = json.loads(args.issues.read_text(encoding="utf-8"))
        if not isinstance(pr, dict) or not isinstance(issues, list):
            raise GateError("--pr is not an object or --issues is not a list")
        result = classify(args.repo, args.base, args.source, pr,
                          [i for i in issues if isinstance(i, dict)])
    except (GateError, OSError, ValueError) as exc:
        print(f"fixture_pr_gate: {exc}", file=sys.stderr)
        return 2
    for name in ("lane", "eligible"):
        out.write(f"{name}={'true' if result[name] else 'false'}\n")
    out.write(f"issue={result['issue']}\nreason={result['reason']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
