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
* at most MAX_FILE_BYTES per file and MAX_TOTAL_BYTES in all;
* each new fixture.yaml carries a valid top-level `origin:` mapping
  (`origin_problem`, below).

ORIGIN (Adam, 2026-11-03, skills-evals#656: fixture requests built from
real fleet work replace the scaffold lane, and how many are real work, what
they cost and whether they run is tracked, scripts/fixture_queue.py). Every
fixture a fix PR adds says where it came from, as exactly these three keys:

  origin:
    kind: real-work | invented
    source: https://github.com/<owner>/<repo>/pull/<N>   (null when invented)
    request: https://github.com/Adam-S-Daniel/skills-evals/issues/<issue>

`real-work` needs a pull request URL whose owner is one of the fleet's two
(stakes.FLEET_OWNERS; GitHub owner names compare case-insensitively);
`invented` needs `source: null`; `request` must be the issue the pull
request answers, exactly. The gate never fetches the source: the URL is a
pointer for the dashboard and the record, and the fixture itself is
invented data either way. The harness ignores the key (it reads no
whitelist of top-level fixture keys). A trigger set carries no origin.

A TRIGGER SET (skills-evals#662) answers a `needs-trigger-set` issue
instead. ELIGIBLE then means the whole diff is exactly ONE added regular,
non-executable file (mode 100644), `evals/<skill>/trigger-eval-set.json`
for the issue's skill, absent on the base and the merge base, at most
MAX_FILE_BYTES, that propose_skill_edit.load_trigger_eval_set accepts and
that, after the loop's own normalization (whitespace collapsed, a repeated
query dropped), holds at least propose_skill_edit.TRIGGER_ONLY_MIN_CLASS
queries of each class and leaves both of skill-creator's splits with both
classes (`trigger_set_problems`). The blob is read with `git cat-file` as
data and parsed as JSON; nothing from the branch runs. The one other change
allowed is README.md's layout entry for the skill's directory: README.md
stays a regular file and the change adds exactly one line, removes none, and
that line is the directory (`<skill>/`, indented) with at most a `#`
comment, at most README_LINE_MAX characters (`readme_entry_ok`).

Output, for $GITHUB_OUTPUT: `lane=`, `eligible=`, `issue=`, `reason=` (fixed
text, never file content). Exit 0 on any decision; exit 2 on bad input.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import draft_new_skill  # noqa: E402
import propose_skill_edit  # noqa: E402
import stakes  # noqa: E402

AUTHOR = "Adam-S-Daniel"
LABEL = "agent-authored"
ISSUE_AUTHOR = "github-actions[bot]"
REGISTRY = "https://github.com/Adam-S-Daniel/adam-agentskills"
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 5_000_000
#: The longest README.md layout line a trigger-set pull request may add.
README_LINE_MAX = 200
_REF = re.compile(r"\b(?:refs|close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+"
                  r"(?:(?:https://github\.com/)?Adam-S-Daniel/skills-evals(?:/issues/|#)|#)"
                  r"([1-9][0-9]{0,6})\b", re.I)
_NEED = re.compile(r"<!-- skills-evals:(needs-fixtures|needs-harder-fixtures|needs-trigger-set)"
                   r":(\S+) -->")
TRIGGER_NEED = "needs-trigger-set"
_SKILL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
#: `origin.kind` values (module docstring, ORIGIN).
ORIGIN_KINDS = ("real-work", "invented")
#: How the `readiness` note of a guidance fixture's evals/scheduled.yml row
#: starts when a fix PR appends it. The schedule tests tell these rows from the
#: reviewed list and from `scaffold_real_work.py promote` rows by this prefix
#: and the fixture's valid `origin:` (test_issue_scheduled_fixtures.py).
FIXTURE_PR_NOTE = "Added by a fixture pull request"
#: `origin.request` is this prefix plus the answered issue's number.
REQUEST_PREFIX = "https://github.com/Adam-S-Daniel/skills-evals/issues/"
_REQUEST = re.compile(re.escape(REQUEST_PREFIX) + r"([1-9][0-9]{0,6})")
#: `origin.source` for real work: a pull request URL; the owner is checked
#: against stakes.FLEET_OWNERS separately.
_SOURCE = re.compile(r"https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
                     r"([A-Za-z0-9._-]{1,100})/pull/([1-9][0-9]{0,6})")


class GateError(Exception):
    """Bad input: the gate cannot judge."""


def _git(repo: Path, *args: str) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if done.returncode != 0:
        raise GateError(f"git {args[0]} failed")
    return done.stdout


def origin_problem(origin, issue: int | None = None) -> str | None:
    """Why `origin` (a fixture.yaml's `origin:` value) is not valid, as fixed
    text, or None (module docstring, ORIGIN). With `issue`, `request` must
    name that issue; without it, any skills-evals issue URL passes
    (scripts/fixture_queue.py reads committed fixtures this way)."""
    if not isinstance(origin, dict) or set(origin) != {"kind", "source", "request"}:
        return "a new fixture.yaml has no origin mapping of exactly kind, source and request"
    if origin["kind"] not in ORIGIN_KINDS:
        return "a new fixture's origin kind is not real-work or invented"
    request = origin["request"]
    if not isinstance(request, str) or not _REQUEST.fullmatch(request) \
            or (issue is not None and request != f"{REQUEST_PREFIX}{issue}"):
        return "a new fixture's origin request is not the issue this pull request answers"
    source = origin["source"]
    if origin["kind"] == "invented":
        return None if source is None else "an invented fixture's origin source is not null"
    match = _SOURCE.fullmatch(source) if isinstance(source, str) else None
    if match is None:
        return "a real-work fixture's origin source is not a pull request URL"
    if match.group(1).casefold() not in {o.casefold() for o in stakes.FLEET_OWNERS}:
        return "a real-work fixture's origin source is not in a fleet owner's repository"
    return None


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


def _changes(repo: Path, merge_base: str, source: str) -> list:
    """(new mode, new blob sha, status, path) per change from `merge_base`
    to `source`, from `git diff --raw`."""
    raw = _git(repo, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", merge_base, source)
    fields = raw.split(b"\0")
    changes = []
    for i in range(0, len(fields) - 1, 2):
        meta, path = fields[i].decode(), fields[i + 1].decode("utf-8", "replace")
        parts = meta.lstrip(":").split()
        changes.append((parts[1], parts[3], parts[4], path))
    return changes


def trigger_set_ok(data: bytes) -> bool:
    """Whether `data` is a trigger set the trigger-only loop would take:
    propose_skill_edit.load_trigger_eval_set's shape, then, deduplicated by
    whitespace-collapsed query as the loop does, at least
    TRIGGER_ONLY_MIN_CLASS queries of each class and no split problem."""
    try:
        items = propose_skill_edit.parse_trigger_eval_set(
            data, propose_skill_edit.TRIGGER_SET_FILE)
    except propose_skill_edit.Refusal:
        return False
    clean, seen = [], set()
    for item in items:
        query = " ".join(item["query"].split())
        if query not in seen:
            seen.add(query)
            clean.append({"query": query, "should_trigger": item["should_trigger"]})
    least = propose_skill_edit.TRIGGER_ONLY_MIN_CLASS
    if sum(i["should_trigger"] for i in clean) < least \
            or sum(not i["should_trigger"] for i in clean) < least:
        return False
    return not propose_skill_edit.trigger_set_problems(
        propose_skill_edit.trigger_split_counts(clean))


def readme_entry_ok(before: bytes, after: bytes, skill: str) -> bool:
    """Whether README.md went from `before` to `after` by adding exactly one
    line, removing none, that names the skill's directory as a layout entry
    (module docstring, A TRIGGER SET)."""
    try:
        old = before.decode("utf-8").splitlines()
        new = after.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return False
    changed = [op for op in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
               if op[0] != "equal"]
    if len(new) != len(old) + 1 or len(changed) != 1 or changed[0][0] != "insert":
        return False
    line = new[changed[0][3]]
    pattern = r" +" + re.escape(skill) + r"/(?: +#[^\r\n]*)?"
    return len(line) <= README_LINE_MAX and re.fullmatch(pattern, line) is not None


def classify_trigger_set(repo: Path, base: str, source: str, skill: str, out: dict) -> dict:
    """The needs-trigger-set half of `classify` (module docstring, A
    TRIGGER SET): fixed-text reasons, never file content."""
    def refuse(why: str) -> dict:
        return {**out, "reason": why}

    if not _SKILL.fullmatch(skill):
        return refuse("the issue names no valid skill")
    path = f"evals/{skill}/{propose_skill_edit.TRIGGER_SET_FILE}"
    merge_base = _git(repo, "merge-base", base, source).decode().strip()
    changes = _changes(repo, merge_base, source)
    readme = [c for c in changes if c[3] == "README.md"]
    changes = [c for c in changes if c[3] != "README.md"]
    if len(changes) != 1:
        return refuse("a trigger-set pull request must add exactly one file, "
                      "plus at most README.md's entry for it")
    if readme:
        r_mode, r_sha, r_status, _ = readme[0]
        if r_status != "M" or r_mode != "100644" or not readme_entry_ok(
                _git(repo, "show", f"{merge_base}:README.md"),
                _git(repo, "cat-file", "blob", r_sha), skill):
            return refuse("the README.md change is not one added layout line for the skill")
    mode, sha, status, changed = changes[0]
    if status != "A" or mode != "100644" or changed != path:
        return refuse("the change is not the skill's new trigger set as a regular file")
    if _git(repo, "ls-tree", merge_base, "--", path).strip() \
            or _git(repo, "ls-tree", base, "--", path).strip():
        return refuse("the trigger set already exists on the base")
    if int(_git(repo, "cat-file", "-s", sha).decode().strip()) > MAX_FILE_BYTES:
        return refuse("a file is over the size cap")
    if not trigger_set_ok(_git(repo, "cat-file", "blob", sha)):
        return refuse("the trigger set is not a valid set with enough queries of each class")
    return {**out, "eligible": True, "reason": f"adds the trigger set for {skill}"}


def classify(repo: Path, base: str, source: str, pr: dict, issues: list) -> dict:
    lane, number, kind, key, reason = need_of(pr, issues)
    out = {"lane": lane, "eligible": False, "issue": number or "", "reason": reason}
    if not lane:
        return out
    if kind == TRIGGER_NEED:
        return classify_trigger_set(repo, base, source, key, out)

    def refuse(why: str) -> dict:
        return {**out, "reason": why}

    section = key.startswith("guidance/")
    subject = key.split("/", 1)[1] if section else key
    prefix = f"evals/guidance/{subject}/" if section else f"evals/{subject}/"
    merge_base = _git(repo, "merge-base", base, source).decode().strip()
    changes = _changes(repo, merge_base, source)
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
        problem = origin_problem(doc.get("origin"), number)
        if problem:
            return refuse(problem)
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
