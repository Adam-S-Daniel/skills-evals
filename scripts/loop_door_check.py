#!/usr/bin/env python3
"""Run adam-agentskills' own one-way-door check on a loop branch before it is
pushed (adam-agentskills#134), and file an issue instead of a pull request
when it fails.

Why: since adam-agentskills#134, the registry's required `pytest` job fails a
`draft-skill/`, `eval-improve/` or `retire-skill/` pull request, draft or
not, that steps outside ADR 0021 (anything in the skill but plain Markdown,
`hooks` or `allowed-tools` in its frontmatter, a `skills.lock` change beyond
its own entry, a removal without `Adversarial-review: pass`). Such a pull
request would sit red and hold the loop's one slot, since nothing in the
loop closes it. So every lane runs the same check, from the registry
checkout's own default-branch copy, on the commit it is about to push, as
the pull request the App would open, and only a pass is pushed.

  loop_door_check.py check --tree REG --base REF --head REF --branch NAME
                           [--body-file PATH]
      exit 0 pass, 1 the check fails (its messages on stdout, one per line),
      2 it could not run. REG is the registry clone holding both commits;
      the script is the one BASE holds (`git show`), never the working
      tree's, which the branch being judged wrote. A base with no check
      script (before #134) passes. Needs pyyaml and markdown-it-py.

  loop_door_check.py issue --lane draft-skill|eval-improve --subject NAME
                           --errors-file PATH --source URL
      file one issue per lane and subject in skills-evals (`ISSUE_MARKER`,
      opened by github-actions[bot], any state: a closed one is a person's
      answer and is not asked again), with GH_TOKEN (the job's own token).

The check runs with no credential in its environment (PATH, HOME and LANG
only) and reads only git objects. Its messages name repo-relative paths and
skill names, JSON-quoted, never file contents; the issue still puts them in
a fenced block, so no message can render as markup or mention anyone.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK = "scripts/check_one_way_doors.py"
REGISTRY_REPO = "Adam-S-Daniel/adam-agentskills"
#: The registry branch every loop pull request targets. The check refuses a
#: loop pull request whose base is not the default branch, so the simulated
#: one names both (adam-agentskills#138).
REGISTRY_BRANCH = "main"
EVALS_REPO = "Adam-S-Daniel/skills-evals"
#: The App every loop pull request is opened under (retire_skill.LOOP_AUTHOR;
#: adam-agentskills scripts/loop_prs.json).
LOOP_AUTHOR = "skills-evals-improve[bot]"
FAIL_PREFIX = "one-way-doors: FAIL: "
LANES = ("draft-skill", "eval-improve")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ISSUE_MARKER = "<!-- skills-evals:loop-door:{lane}:{subject} -->"
ISSUE_AUTHOR = "github-actions[bot]"
AGENT_MARKER = "<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>"
MESSAGE_LIMIT = 400
CHECK_TIMEOUT = 300


class DoorError(Exception):
    """The check could not run, or an input is malformed."""


def _base_script(tree: Path, base: str) -> str | None:
    """The check script as the base commit holds it, or None when it has
    none (a registry before #134). Never the working tree, which the branch
    being judged has written."""
    proc = subprocess.run(["git", "-C", str(tree), "cat-file", "-e", f"{base}:{CHECK}"],
                          capture_output=True)
    if proc.returncode != 0:
        exists = subprocess.run(["git", "-C", str(tree), "rev-parse", "--verify", "-q",
                                 f"{base}^{{commit}}"], capture_output=True)
        if exists.returncode != 0:
            raise DoorError("the base is not a commit in the registry clone")
        return None
    proc = subprocess.run(["git", "-C", str(tree), "show", f"{base}:{CHECK}"],
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise DoorError("could not read the check script at the base")
    return proc.stdout


def check(tree: Path, base: str, head: str, branch: str, body: str = "") -> list:
    """The check's failure messages for `branch` at `head` against `base` in
    the registry clone `tree`, with the script from `base`; [] on a pass.
    DoorError when it cannot run."""
    source = _base_script(Path(tree), base)
    if source is None:
        return []
    pr = {"number": None, "draft": False, "body": body,
          "user": {"login": LOOP_AUTHOR, "type": "Bot"},
          "head": {"ref": branch, "repo": {"full_name": REGISTRY_REPO}},
          "base": {"ref": REGISTRY_BRANCH,
                   "repo": {"full_name": REGISTRY_REPO, "default_branch": REGISTRY_BRANCH}}}
    git_dir = subprocess.run(["git", "-C", str(tree), "rev-parse", "--absolute-git-dir"],
                             capture_output=True, text=True)
    if git_dir.returncode != 0 or not git_dir.stdout.strip():
        raise DoorError("the registry clone is not a git repository")
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ}
    env.update({"GIT_DIR": git_dir.stdout.strip(), "GIT_WORK_TREE": str(Path(tree).resolve()),
                "PYTHONDONTWRITEBYTECODE": "1"})
    with tempfile.TemporaryDirectory(prefix="skills-evals-door-check-") as tmp:
        # The base's copy, in a directory holding nothing else but the pull
        # request, run from there: its name is spelled literally at the call
        # so the suite's spawn audit (test/run_tests.py, S-B-a-2) can prove
        # it is not the test runner, and git finds the registry through
        # GIT_DIR and GIT_WORK_TREE.
        (Path(tmp) / "check_one_way_doors.py").write_text(source, encoding="utf-8")
        path = Path(tmp) / "pr.json"
        path.write_text(json.dumps(pr), encoding="utf-8")
        try:
            proc = subprocess.run([sys.executable, "check_one_way_doors.py", "--base", base,
                                   "--head", head, "--pr-json", str(path)], cwd=tmp,
                                  env=env, capture_output=True, text=True,
                                  timeout=CHECK_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DoorError(f"the check could not run ({type(exc).__name__})") from None
    if proc.returncode == 0:
        return []
    if proc.returncode != 1:
        raise DoorError(f"the check could not run (exit {proc.returncode})")
    errors = [line[len(FAIL_PREFIX):] for line in proc.stdout.splitlines()
              if line.startswith(FAIL_PREFIX)]
    if not errors:
        raise DoorError("the check failed and named no rule")
    return errors


def fenced(lines: list) -> str:
    safe = [" ".join(line.split())[:MESSAGE_LIMIT].replace("~~~", "~ ~ ~") for line in lines]
    return "~~~text\n" + "\n".join(safe) + "\n~~~"


def issue_body(lane: str, subject: str, errors: list, source: str) -> str:
    return (f"{ISSUE_MARKER.format(lane=lane, subject=subject)}\n"
            f"@Adam-S-Daniel: the evals loop's `{lane}` change for `{subject}` was not "
            "opened as a pull request in adam-agentskills, because that registry's "
            "one-way-door check (adam-agentskills#134) would fail it, and a red loop "
            "pull request would hold the loop's one slot.\n\n"
            f"What the check reported:\n\n{fenced(errors)}\n\n"
            f"Source: {source}\n\n"
            f"**To proceed:** take the change to a branch outside `{lane}/` in "
            "adam-agentskills and open it for review. **To drop it:** close this issue; "
            "a closed issue is not filed again.\n\n"
            "Filed by skills-evals' scripts/loop_door_check.py.\n\n" + AGENT_MARKER + "\n")


def default_gh(args: list, stdin: str | None = None) -> str:
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        raise DoorError(f"gh exited {proc.returncode}")
    return proc.stdout


def file_issue(lane: str, subject: str, errors: list, source: str, gh=default_gh) -> str:
    """Create the issue unless one with its marker exists in any state."""
    if lane not in LANES or not NAME_RE.fullmatch(subject):
        raise DoorError("the lane or subject is malformed")
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9._/-]+", source):
        raise DoorError("the source is not a github.com URL")
    marker = ISSUE_MARKER.format(lane=lane, subject=subject)
    listing = gh(["api", "--paginate", f"repos/{EVALS_REPO}/issues?state=all&per_page=100",
                  "--jq", ".[] | select(.pull_request == null) | "
                          "{number, author: .user.login, body: (.body // \"\")}"])
    for line in listing.splitlines():
        item = json.loads(line)
        if item.get("author") == ISSUE_AUTHOR and marker in (item.get("body") or ""):
            return f"issue #{item.get('number')} already records {lane}/{subject}; none filed"
    gh(["issue", "create", "-R", EVALS_REPO,
        "--title", f"Loop change needs a person: {lane}/{subject}",
        "--label", "agent-authored", "--body-file", "-"],
       issue_body(lane, subject, errors, source))
    return f"filed an issue for {lane}/{subject}"


def main(argv: list | None = None, *, gh=default_gh, out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check")
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--body-file", type=Path, default=None)
    p = sub.add_parser("issue")
    p.add_argument("--lane", required=True, choices=LANES)
    p.add_argument("--subject", required=True)
    p.add_argument("--errors-file", required=True, type=Path)
    p.add_argument("--source", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            body = args.body_file.read_text(encoding="utf-8") if args.body_file else ""
            errors = check(args.tree, args.base, args.head, args.branch, body)
            for error in errors:
                out.write(" ".join(error.split()) + "\n")
            return 1 if errors else 0
        errors = [ln for ln in args.errors_file.read_text(encoding="utf-8").splitlines()
                  if ln.strip()]
        if not errors:
            raise DoorError("no check messages to record")
        out.write(file_issue(args.lane, args.subject, errors, args.source, gh) + "\n")
        return 0
    except (DoorError, OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"loop_door_check: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
