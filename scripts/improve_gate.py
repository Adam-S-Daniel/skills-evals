#!/usr/bin/env python3
"""Validate a routine's `claude/eval-improve-<run id>` branch and apply it.

The improvement loop's routine mode (ADR 0005 amendment 1; ADR 0010). The
eval routine runs `scripts/propose_skill_edit.py` and, when its candidate is
ACCEPTED, pushes one branch holding exactly

    eval-improve/<run id>/summary.json   the loop's record (`<ts>.json`)
    eval-improve/<run id>/report.md      its pull-request body (`<ts>.pr-body.md`)
    eval-improve/<run id>/skill.patch    its registry patch (`<ts>.patch`)

and nothing else. It never opens a pull request. The branch is UNTRUSTED
input (a model run wrote it): `.github/workflows/routine-improve-gate.yml`
runs this script from the default branch's checkout, and it reads the branch
only through git plumbing (`git diff --raw`, `git cat-file`), reusing
`ingest_routine_results.py`'s helpers. Nothing from the branch is executed,
imported or checked out; `apply` hands the validated patch to `git apply` in
a registry checkout, as data.

`eval-improve/` is not `eval-results/`: `claude/eval-improve-*` also matches
the results signal's `claude/eval-*` branch filter, and only the two path
filters keep an improve push from starting a results ingest (and a results
push from starting this gate).

What a branch must look like to pass:

  * its name is `claude/eval-improve-<YYYYMMDDTHHMMSSZ>-<6 hex>`;
  * against its merge-base with the default branch it ADDS exactly the three
    files above, regular and non-executable, under its own run id;
  * summary.json is an `accepted` record (schema 1) for the adam-agentskills
    registry at a full commit sha, whose `skill_md` is that registry's
    `plugins/<plugin>/skills/<skill>/SKILL.md` for the record's own skill,
    and the skill has fixtures under `evals/<skill>/` on the default branch;
  * skill.patch is a unified diff of that one path and nothing else, every
    hunk's line counts agreeing with its header;
  * report.md opens with the loop's own title and holds no closing keyword
    or @mention (it becomes a pull-request body in another repository);
  * every file is under its size cap and valid UTF-8 with no control
    characters.

Subcommands (output is `key=value` lines of validated values, for
$GITHUB_OUTPUT):

  resolve  --event-name NAME --event-path PATH
  validate --repo DIR --base REF --source REF --branch NAME
           [--expect-sha SHA] --out DIR
  apply    --staged DIR --tree DIR --skill-md PATH
  pr-body  --staged DIR --run-id ID --sha SHA --branch NAME   (body on stdout)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingest_routine_results as ingest  # noqa: E402
from ingest_routine_results import Rejected  # noqa: E402

BRANCH_RE = re.compile(rf"claude/eval-improve-(?P<run_id>{ingest.RUN_ID})")
BRANCH_SHAPE = "claude/eval-improve-<run id>"
#: The one top-level directory an improve branch adds to.
SOURCE_ROOT = "eval-improve"
#: Every file the branch must add, with its byte cap.
SIZE_CAPS = {"summary.json": 256 * 1024, "report.md": 64 * 1024,
             "skill.patch": 128 * 1024}

#: The only registry a draft pull request is opened in. ADR 0010 decision 1
#: lets routine arms run only the registries' default branches; this gate
#: further limits the loop's output to the one registry it targets.
REGISTRY_NAME = "adam-agentskills"
REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
NAME = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
#: adam-agentskills' layout (harness/registries.yml: plugins/*/skills/*/SKILL.md).
SKILL_MD_RE = re.compile(rf"plugins/(?P<plugin>{NAME})/skills/(?P<skill>{NAME})/SKILL\.md")
NAME_RE = re.compile(NAME)
#: The branch the draft pull request comes from in adam-agentskills: one per
#: skill, so a second accepted candidate waits until a person has dealt with
#: the first (ADR 0005, "the idempotency check on an open eval-improve/<skill>
#: branch").
TARGET_BRANCH = "eval-improve/{skill}"

#: The repository secrets the draft-PR job mints its GitHub App token from
#: (owner decision, Adam: "GitHub App (Recommended)"): the App's client id
#: and its private key in PEM form. Neither name holds one of gitleaks'
#: generic-api-key keywords (ADR 0010 decision 5).
APP_CLIENT_ID_SECRET = "EVAL_IMPROVE_APP_CLIENT_ID"
APP_PEM_SECRET = "EVAL_IMPROVE_APP_PEM"

#: propose_skill_edit.improve()'s record keys (the suite reads them from its
#: AST and checks they stay inside these sets).
RECORD_REQUIRED = ("schema", "skill", "timestamp", "registry", "split",
                   "trials", "status", "reasons", "baseline", "candidate",
                   "description_half", "body_half", "table", "files")
RECORD_ALLOWED = RECORD_REQUIRED + (
    "local_exhibit", "no_judge", "min_gain", "models", "runs", "trigger_set",
    "phase", "exit_code")
MAX_RECORD_STRING = 32 * 1024
MAX_RECORD_DEPTH = 10
MAX_RECORD_ITEMS = 512

REPORT_TITLE = "## Proposed `{skill}` SKILL.md edit (validation-gated)"
#: GitHub closes an issue or pull request named after one of these keywords
#: in a merged pull request's body, in any repository; a model-written
#: report must not be able to do that. Matched against the text with its
#: Markdown emphasis, code and link syntax stripped (`closing_text`), so
#: `**Fixes** #1` or `Fixes [#1](...)` cannot hide one; a link's target URL
#: is kept, so `Closes [x](https://github.com/o/r/issues/7)` is caught too.
_KEYWORD = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[\s:<]*"
CLOSING_RE = re.compile(
    _KEYWORD + r"(?:(?:[\w.-]+/[\w.-]+)?#\d+"
    r"|https?://github\.com/[^\s/]+/[^\s/]+/(?:issues|pull)/\d+)", re.I)
#: A keyword with an issue or pull request URL anywhere later on its line
#: (a link label can sit between the two). Over-rejects; that is fine.
CLOSING_URL_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[^\n]*?"
    r"https?://github\.com/[^\s/]+/[^\s/]+/(?:issues|pull)/\d+", re.I)
#: Markdown that can sit between a keyword and its reference.
_MARKDOWN_NOISE = re.compile(r"[*_`~\[\]]")
_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)[^)]*\)")
#: An @mention notifies a person. Only a letter or digit right before the @
#: (an email address, an `action@sha` pin) makes it something else;
#: punctuation does not, so this over-rejects rather than miss one.
MENTION_RE = re.compile(r"(?<![A-Za-z0-9])@[A-Za-z0-9][A-Za-z0-9-]*")
HUNK_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?")


# ---------------------------------------------------------------------------
# Content.

def bounded(value, where: str, depth: int = 0) -> None:
    """Any JSON value, within the record's depth, string and size limits
    (larger than a result summary's: a record carries the proposal's diff
    and rationale)."""
    if depth > MAX_RECORD_DEPTH:
        raise Rejected(f"{where}: nested too deep")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if not ingest.is_number(value):
            raise Rejected(f"{where}: not a finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_RECORD_STRING:
            raise Rejected(f"{where}: string too long")
        return
    if isinstance(value, (list, dict)):
        if len(value) > MAX_RECORD_ITEMS:
            raise Rejected(f"{where}: too many items")
        items = value.items() if isinstance(value, dict) else enumerate(value)
        for key, item in items:
            if isinstance(key, str) and len(key) > 128:
                raise Rejected(f"{where}: key too long")
            bounded(item, where, depth + 1)
        return
    raise Rejected(f"{where}: unexpected JSON type")


def check_record(doc, where: str, repo: str) -> dict:
    ingest._object(doc, where, RECORD_ALLOWED, RECORD_REQUIRED)
    bounded(doc, where)
    if doc["schema"] != 1 or isinstance(doc["schema"], bool):
        raise Rejected(f"{where}: unknown schema")
    if doc["status"] != "accepted":
        raise Rejected(f"{where}: status is not accepted; the routine pushes "
                       "only an accepted candidate")
    skill = doc["skill"]
    if not isinstance(skill, str) or not NAME_RE.fullmatch(skill):
        raise Rejected(f"{where}: bad skill name")
    if not isinstance(doc["timestamp"], str) \
            or not ingest.TIMESTAMP_RE.fullmatch(doc["timestamp"]):
        raise Rejected(f"{where}: bad timestamp")
    ingest._integer(doc["trials"], f"{where}: trials", 1, ingest.MAX_TRIALS)
    reasons = doc["reasons"]
    if not isinstance(reasons, list) or not reasons \
            or not all(isinstance(r, str) for r in reasons):
        raise Rejected(f"{where}: reasons must be a list of strings")

    registry = doc["registry"]
    keys = ("name", "url", "sha", "skill_md")
    ingest._object(registry, f"{where}: registry", keys, keys)
    if registry["name"] != REGISTRY_NAME or registry["url"] != REGISTRY_URL:
        raise Rejected(f"{where}: registry is not {REGISTRY_NAME}")
    if not isinstance(registry["sha"], str) \
            or not ingest.SHA_RE.fullmatch(registry["sha"]):
        raise Rejected(f"{where}: registry sha is not a 40-hex commit id")
    match = SKILL_MD_RE.fullmatch(registry["skill_md"]) \
        if isinstance(registry["skill_md"], str) else None
    if not match or match.group("skill") != skill \
            or ".." in registry["skill_md"].split("/"):
        raise Rejected(f"{where}: registry skill_md is not this skill's "
                       "SKILL.md")

    split = doc["split"]
    ingest._object(split, f"{where}: split",
                   ("rotation", "train", "validation", "holdout"),
                   ("rotation", "train", "validation"))
    names = split["train"] if isinstance(split["train"], list) else [None]
    names = names + [split["validation"]] + (
        [split["holdout"]] if "holdout" in split else [])
    if not all(isinstance(n, str) and NAME_RE.fullmatch(n) for n in names):
        raise Rejected(f"{where}: bad fixture name in split")

    if not (Path(repo) / "evals" / skill).is_dir():
        raise Rejected(f"{where}: skill has no evals/ directory on the "
                       "default branch")
    return {"skill": skill, "registry_sha": registry["sha"],
            "skill_md": registry["skill_md"]}


def check_patch(text: str, where: str, skill_md: str) -> None:
    """A unified diff of `skill_md` only, as difflib writes it."""
    if not text.endswith("\n"):
        raise Rejected(f"{where}: does not end with a newline")
    lines = text[:-1].split("\n")
    if lines[:2] != [f"--- a/{skill_md}", f"+++ b/{skill_md}"]:
        raise Rejected(f"{where}: must change {skill_md!r} and nothing else")
    i, changed, hunks = 2, 0, 0
    while i < len(lines):
        header = HUNK_RE.fullmatch(lines[i])
        if not header:
            raise Rejected(f"{where}: line {i + 1} is not a hunk header")
        old = int(header.group(2) if header.group(2) is not None else 1)
        new = int(header.group(4) if header.group(4) is not None else 1)
        hunks += 1
        i += 1
        while old or new:
            if i >= len(lines):
                raise Rejected(f"{where}: hunk {hunks} is shorter than its "
                               "header")
            mark = lines[i][:1]
            if mark == " " and old and new:
                old, new = old - 1, new - 1
            elif mark == "-" and old:
                old, changed = old - 1, changed + 1
            elif mark == "+" and new:
                new, changed = new - 1, changed + 1
            else:
                raise Rejected(f"{where}: line {i + 1} does not fit hunk "
                               f"{hunks}")
            i += 1
    if not hunks or not changed:
        raise Rejected(f"{where}: changes nothing")


def closing_text(text: str) -> str:
    """`text` with each Markdown link reduced to its label and target, and
    emphasis, code and bracket characters removed."""
    return _MARKDOWN_NOISE.sub("", _LINK.sub(r"\1 \2", text))


def check_report(text: str, where: str, skill: str) -> None:
    if text.split("\n", 1)[0] != REPORT_TITLE.format(skill=skill):
        raise Rejected(f"{where}: does not open with the loop's title for "
                       "this skill")
    stripped = closing_text(text)
    if CLOSING_RE.search(text) or CLOSING_RE.search(stripped) \
            or CLOSING_URL_RE.search(stripped):
        raise Rejected(f"{where}: has a closing keyword before an issue or "
                       "pull request reference")
    if MENTION_RE.search(text):
        raise Rejected(f"{where}: has an @mention")


# ---------------------------------------------------------------------------
# Subcommands.

def validate(repo: str, base: str, source: str, branch: str,
             expect_sha: str | None, out: Path) -> dict:
    match = BRANCH_RE.fullmatch(branch)
    if not match:
        raise Rejected(f"branch name is not {BRANCH_SHAPE}")
    run_id = match.group("run_id")
    tip = ingest.resolve_commit(repo, source)
    if expect_sha is not None:
        if not ingest.SHA_RE.fullmatch(expect_sha):
            raise Rejected("expected sha is not a 40-hex commit id")
        if tip != expect_sha:
            raise Rejected("the branch moved since the push that triggered "
                           "this run; that newer push triggers its own gate")
    base_sha = ingest.resolve_commit(repo, base)
    merge_base = ingest.git(repo, "merge-base", base_sha, tip).decode().strip()
    if not ingest.SHA_RE.fullmatch(merge_base):
        raise Rejected("the branch shares no history with the default branch")

    prefix = f"{SOURCE_ROOT}/{run_id}/"
    files = {}
    for name, _, oid in ingest.added_files(repo, merge_base, tip):
        if not name.startswith(prefix):
            raise Rejected(f"{name!r}: not under {prefix!r}")
        kind = name[len(prefix):]
        if kind not in SIZE_CAPS:
            raise Rejected(f"{name!r}: not a file an improve branch carries")
        size = int(ingest.git(repo, "cat-file", "-s", oid).decode().strip())
        if size > SIZE_CAPS[kind]:
            raise Rejected(f"{name!r}: {size} bytes is over the {kind} cap")
        data = ingest.git(repo, "cat-file", "blob", oid)
        if len(data) != size:
            raise Rejected(f"{name!r}: size changed while reading")
        files[kind] = (repr(name), data)
    missing = sorted(set(SIZE_CAPS) - set(files))
    if missing:
        raise Rejected(f"{missing}: missing under {prefix!r}")

    where, data = files["summary.json"]
    found = check_record(
        ingest.load_json(ingest.decode_text(data, where), where), where, repo)
    where, data = files["skill.patch"]
    check_patch(ingest.decode_text(data, where), where, found["skill_md"])
    where, data = files["report.md"]
    check_report(ingest.decode_text(data, where), where, found["skill"])

    if out.exists() and any(out.iterdir()):
        raise Rejected("the staging directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
    for kind, (_, data) in files.items():
        (out / kind).write_bytes(data)
    return {"run_id": run_id, "sha": tip, **found,
            "target_branch": TARGET_BRANCH.format(skill=found["skill"])}


def _frontmatter(text: str, where: str) -> dict:
    if not text.startswith("---\n") or "\n---\n" not in text[3:]:
        raise Rejected(f"{where}: has no frontmatter")
    try:
        data = yaml.safe_load(text[4:text.index("\n---\n", 3)])
    except yaml.YAMLError:
        raise Rejected(f"{where}: frontmatter is not YAML") from None
    if not isinstance(data, dict):
        raise Rejected(f"{where}: frontmatter is not a mapping")
    return data


def apply(staged: Path, tree: Path, skill_md: str) -> dict:
    """Apply the staged patch to a registry checkout at `tree`. Only
    `skill_md` may change, and only its frontmatter's `description` may
    change there (propose_skill_edit.set_description's rule: the name is
    fixed, the description is the trigger half's, and nothing else moves)."""
    if not SKILL_MD_RE.fullmatch(skill_md) or ".." in skill_md.split("/"):
        raise Rejected("skill_md is not a registry SKILL.md path")
    cursor = tree
    for part in Path(skill_md).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise Rejected(f"{skill_md!r}: the registry path has a symlink")
    target = tree / skill_md
    if not target.is_file():
        raise Rejected(f"{skill_md!r}: not in the registry checkout")
    before = _frontmatter(target.read_text(encoding="utf-8"), skill_md)
    patch = str((staged / "skill.patch").resolve())
    for args in (("apply", "--check", patch), ("apply", patch)):
        result = subprocess.run(["git", "-C", str(tree), *args],
                                capture_output=True, check=False)
        if result.returncode != 0:
            raise Rejected("the patch does not apply to the registry at the "
                           "recorded sha")
    after = _frontmatter(target.read_text(encoding="utf-8"), skill_md)
    if {k: v for k, v in after.items() if k != "description"} \
            != {k: v for k, v in before.items() if k != "description"} \
            or ("description" in after) != ("description" in before):
        raise Rejected(f"{skill_md!r}: the patch changes the frontmatter "
                       "beyond its description")
    changed = ingest.git(str(tree), "status", "--porcelain=v1", "-z").decode()
    if changed.split("\0")[:-1] != [f" M {skill_md}"]:
        raise Rejected("the patch changed more than the one SKILL.md")
    return {"changed": skill_md}


def pr_body(staged: Path, run_id: str, sha: str, branch: str) -> str:
    report = (staged / "report.md").read_text(encoding="utf-8")
    return "\n".join([
        f"Draft from the skills-evals improvement loop, run `{run_id}`: the "
        "eval routine pushed "
        f"[`{branch}`](https://github.com/Adam-S-Daniel/skills-evals/tree/{sha}) "
        f"at `{sha}`, and `routine-improve-gate.yml` validated it without "
        "running it and applied its `skill.patch` here.",
        "",
        "A person reviews and merges this, or declines it; nothing merges "
        "itself. Merging it counts toward the three human-reviewed loop pull "
        "requests that must merge before any scheduled loop "
        "([skills-evals#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)). The "
        "numbers below are a local exhibit (skills-evals ADR 0010 decision "
        "3), not badge input.",
        "",
        "Part of https://github.com/Adam-S-Daniel/skills-evals/issues/71.",
        "",
        "---",
        "",
        report.rstrip("\n"),
        ""])


def resolve(event_name: str, event_path: str) -> dict:
    return ingest.resolve(event_name, event_path, BRANCH_RE, BRANCH_SHAPE)


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
    p = sub.add_parser("apply")
    p.add_argument("--staged", required=True, type=Path)
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--skill-md", required=True)
    p = sub.add_parser("pr-body")
    p.add_argument("--staged", required=True, type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--branch", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            result = resolve(args.event_name, args.event_path)
        elif args.command == "validate":
            result = validate(args.repo, args.base, args.source, args.branch,
                              args.expect_sha or None, args.out)
        elif args.command == "apply":
            result = apply(args.staged, args.tree, args.skill_md)
        else:
            if not BRANCH_RE.fullmatch(args.branch) \
                    or not ingest.SHA_RE.fullmatch(args.sha) \
                    or BRANCH_RE.fullmatch(args.branch).group("run_id") != args.run_id:
                raise Rejected("pr-body takes only validated values")
            sys.stdout.write(pr_body(args.staged, args.run_id, args.sha,
                                     args.branch))
            return 0
    except Rejected as exc:
        message = "".join(c if c.isprintable() else repr(c)[1:-1]
                          for c in str(exc))
        print(f"rejected: {message}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
