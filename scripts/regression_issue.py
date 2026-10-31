#!/usr/bin/env python3
"""Write `regressions/latest.json` and keep one issue per regressed subject (#69, #121).

  regression_issue.py --results-tree DIR --roster evals/roster.yml
                      --policy evals/regression-policy.yml --as-of TIME --out FILE
                      [--evals-dir DIR] [--registry NAME=PATH ...] [--guidance PATH]
                      [--dry-run] [--run-url URL]

The document is harness/regression.py's, over the index
scripts/compute_gates.py builds from the results tree (the same roster arms,
the same `--as-of`). It is written to `--out` whatever else happens.

ONE ISSUE PER SKILL OR GUIDANCE SECTION, in skills-evals, for both subjects.
This departs from #121, which wanted the guidance issues in _agent-guidance:
the scheduled job's token reaches only skills-evals, and the eval-improve
GitHub App holds no issues permission. The body still links the
_agent-guidance commits (`--guidance`).

The issue is found by its marker, a line of its own in the body:
`<!-- skills-evals:regression:<skill> -->` for a skill and
`<!-- skills-evals:regression:guidance:<section> -->` for a section. A whole
line is matched, and a skill name cannot hold a colon, so no skill marker
equals a guidance one. Only issues github-actions[bot] opened count
(retire_skill.ISSUE_AUTHOR).

LIFECYCLE, per (subject, id), acting on the lowest-numbered open issue:

  regressed or lost-delta, no open issue    create-issue
  regressed or lost-delta, open issue       update-issue (none when the body is
                                            unchanged, apart from the run URL)
  stable or improved, open issue            close-issue (a comment, then close)
  insufficient, open issue                  none: no evidence either way
  anything else                             none

A failed `gh` call for one subject is recorded and the others still run; the
exit code is then 1. Exit 2 is bad input (policy, roster, `--as-of`). `gh`
output is never echoed on failure (retire_skill.default_gh). `--dry-run`
prints the plan as JSON and writes nothing to GitHub. Issue bodies are
public: numbers, paths, links and shas only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import delivery  # noqa: E402
import regression  # noqa: E402
import retire_skill  # noqa: E402
import run_eval  # noqa: E402

EVALS_REPO = retire_skill.EVALS_REPO
GUIDANCE_REPO = retire_skill.GUIDANCE_REPO
GUIDANCE_PATHS = ("agents-md/base.md", "agents-md/sections")
#: The registries a commit link may name, by their `--registry` name.
REGISTRY_REPOS = {"adam-agentskills": "Adam-S-Daniel/adam-agentskills",
                  "cms-platform": "Adam-S-Daniel/cms-platform",
                  "adamdaniel.ai": "Adam-S-Daniel/adamdaniel.ai"}
MARKERS = {"skill": "<!-- skills-evals:regression:{id} -->",
           "guidance": "<!-- skills-evals:regression:guidance:{id} -->"}
RUN_PREFIX = "Workflow run: "
CLOSING = ("This issue is closed by the next measurement that is no longer a regression "
           "(the daily `regression` job in skill-coverage.yml), never by editing it.")
TIMESTAMP_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")


def default_git(checkout: Path, args: list) -> str:
    """git's stdout in `checkout`; its output is discarded on failure."""
    return retire_skill._git(checkout, *args)


def marker(subject: str, ident: str) -> str:
    return MARKERS[subject].format(id=ident)


def fetch_issues(gh) -> list:
    """Every issue github-actions[bot] opened in skills-evals, any state:
    [{"number", "body", "state"}]."""
    text = gh(["api", "--paginate", f"repos/{EVALS_REPO}/issues?state=all&per_page=100",
               "--jq", ".[] | select(.pull_request == null) | "
                       "{number: .number, body: (.body // \"\"), "
                       "author: .user.login, state: .state}"])
    out = []
    for item in retire_skill._json_lines(text):
        if item.get("author") != retire_skill.ISSUE_AUTHOR:
            continue
        number, state, body = item.get("number"), item.get("state"), item.get("body")
        if type(number) is not int or number < 1 or state not in ("open", "closed") \
                or not isinstance(body, str):
            raise retire_skill.RetireError("an issue record from the API is malformed")
        out.append({"number": number, "body": body, "state": state})
    return out


def open_issue(issues: list, subject: str, ident: str):
    """The lowest-numbered open issue whose body holds this subject's marker
    as a whole line, or None."""
    line = marker(subject, ident)
    found = [i for i in issues if i["state"] == "open"
             and line in (b.strip() for b in i["body"].splitlines())]
    return min(found, key=lambda i: i["number"]) if found else None


def iso(timestamp: str) -> str:
    """`YYYYMMDDTHHMMSSZ` as ISO 8601 with Z."""
    match = TIMESTAMP_RE.fullmatch(timestamp)
    if not match:
        raise ValueError("not a results timestamp")
    y, mo, d, h, mi, s = match.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}Z"


def skill_location(registries: dict, skill: str):
    """(repository, checkout, path in it) of the one copy of `skill` in the
    known registries given, or None."""
    found = []
    for name in sorted(registries):
        if name not in REGISTRY_REPOS:
            continue
        entry = registries[name]
        try:
            matches = delivery._registry_matches({name: entry}, None, skill)
        except (delivery.DeliveryError, OSError):
            return None
        root = Path(entry["path"])
        found += [(REGISTRY_REPOS[name], root, d.relative_to(root).as_posix())
                  for _identity, _plugin, d in matches]
    return found[0] if len(found) == 1 else None


def commit_lines(subject: str, ident: str, rows: list, registries: dict,
                 guidance_dir, git) -> list:
    """The suspect commits between the windows, as markdown lines."""
    if subject == "skill":
        if not run_eval._SKILL_NAME_RE.fullmatch(ident):
            return ["- Commit range unavailable."]
        location = skill_location(registries, ident)
        if location is None:
            return ["- Registry not checked out."]
        repo, checkout, paths = location[0], location[1], [location[2]]
    else:
        if guidance_dir is None:
            return ["- Registry not checked out."]
        repo, checkout, paths = GUIDANCE_REPO, Path(guidance_dir), list(GUIDANCE_PATHS)
    afters = [r["boundary"]["after"] for r in rows if r["boundary"]["after"]]
    befores = [r["boundary"]["before"] for r in rows if r["boundary"]["before"]]
    if not afters or not befores:
        return ["- Commit range unavailable."]
    try:
        after, before = iso(min(afters)), iso(max(befores))
        text = git(checkout, ["log", "--format=%H", f"--after={after}",
                              f"--before={before}", "--", *paths])
    except (retire_skill.RetireError, ValueError, OSError):
        return ["- Commit range unavailable."]
    shas = [s for s in text.split() if re.fullmatch(r"[0-9a-f]{40}", s)]
    head = f"- Commits to `{' '.join(paths)}` in {repo} from {after} to {before}:"
    if not shas:
        return [head + " none."]
    return [head] + [f"  - [`{sha[:7]}`](https://github.com/{repo}/commit/{sha})"
                     for sha in shas]


def _fixed(value: float) -> str:
    return f"{value:.3f}"


def _pair(figure) -> str:
    return "n/a" if figure is None else \
        f"{_fixed(figure['previous'])} → {_fixed(figure['current'])}"


def title_of(subject: str, ident: str, rows: list) -> str:
    models = ", ".join(sorted({r["model"] for r in rows}))
    if subject == "skill":
        return f"Regression: {ident} no longer helps on {models}"
    return f'Regression: fleet guidance section "{ident}" no longer helps on {models}'


def _links(rows: list, window: str) -> str:
    seen = {}
    for row in rows:
        for run in row["windows"][window]:
            seen[run["report"]["url"]] = run["report"]["path"]
    return ", ".join(f"[{path}]({url})" for url, path in sorted(seen.items(),
                                                                key=lambda kv: kv[1]))


def body_of(subject: str, ident: str, rows: list, registries: dict, guidance_dir, git,
            run_url) -> str:
    """The issue body for the regressed or lost-delta `rows` of one subject."""
    noun = "skill" if subject == "skill" else "guidance section"
    guidance = subject == "guidance"
    head = ["Fixture", "Model"] + (["Pair"] if guidance else []) + [
        "Verdict", "Objective", "Change", "Noise", "Judge", "Delta"]
    lines = [marker(subject, ident), "",
             f"The {noun} `{ident}` no longer helps in {len(rows)} cell(s): its newest "
             "runs score below the runs before them, or it stopped beating the arm "
             "without it.", "",
             "| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for row in rows:
        objective = row["numbers"]["objective"]
        judge = row["numbers"]["judge"]
        cells = [f"`{row['fixture']}`" if row["fixture"] else "(flat)", f"`{row['model']}`"]
        cells += [f"`{row['pair']}`"] if guidance else []
        cells += [row["verdict"], _pair(objective), _fixed(objective["change"]),
                  _fixed(objective["noise"]),
                  "n/a" if judge is None else f"{_pair(judge)} (change "
                  f"{_fixed(judge['change'])}, noise {_fixed(judge['noise'])})",
                  _pair(row["numbers"]["delta"])]
        lines.append("| " + " | ".join(cells) + " |")
    suspects = sorted({s for r in rows for s in r["suspects"]})
    lines += ["", "Reports, previous window: " + (_links(rows, "previous") or "none"),
              "", "Reports, current window: " + (_links(rows, "current") or "none"),
              "", "Suspects:"]
    lines += [f"- {s}" for s in suspects] or ["- none of skill content, CLI version or "
                                              "arm context differs between the windows"]
    lines += ["", "Commit range:"]
    lines += commit_lines(subject, ident, rows, registries, guidance_dir, git)
    lines += ["", CLOSING]
    if run_url:
        lines += ["", f"{RUN_PREFIX}{run_url}"]
    return "\n".join(lines) + "\n"


def _comparable(body: str) -> str:
    """`body` without its run URL line, which changes on every run."""
    return "\n".join(line for line in body.rstrip().splitlines()
                     if not line.startswith(RUN_PREFIX)).rstrip()


def plan(doc: dict, issues: list, registries: dict, guidance_dir, git, run_url) -> list:
    """One action per (subject, id) in the document, in order."""
    actions = []
    for subject in regression.SUBJECTS:
        for ident, verdict in sorted(doc["subjects"][subject].items()):
            action = {"subject": subject, "id": ident, "verdict": verdict,
                      "action": "none", "reason": "", "issue": None}
            found = open_issue(issues, subject, ident)
            if found:
                action["issue"] = found["number"]
            if verdict in regression.BAD:
                rows = [r for r in doc["rows"] if r["subject"] == subject
                        and r["id"] == ident and r["verdict"] in regression.BAD]
                action["title"] = title_of(subject, ident, rows)
                action["body"] = body_of(subject, ident, rows, registries, guidance_dir,
                                         git, run_url)
                if not found:
                    action.update(action="create-issue", reason="no open issue")
                elif _comparable(found["body"]) != _comparable(action["body"]):
                    action.update(action="update-issue", reason="the figures changed")
                else:
                    action["reason"] = "the open issue is current"
            elif verdict in ("stable", "improved") and found:
                action.update(
                    action="close-issue", reason=f"the verdict is {verdict}",
                    comment=f"The measurement as of {doc['as_of']} is {verdict} for "
                            f"`{ident}`, no longer a regression. Closing.")
            else:
                action["reason"] = ("insufficient evidence either way"
                                    if verdict == "insufficient" and found
                                    else "nothing to do")
            actions.append(action)
    return actions


def commands(action: dict) -> list:
    """The `gh` calls `execute` makes, for a dry run."""
    kind, issue = action["action"], str(action["issue"])
    if kind == "create-issue":
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 "--body-file", "-"]]
    if kind == "update-issue":
        return [["gh", "issue", "edit", issue, "-R", EVALS_REPO, "--title",
                 action["title"], "--body-file", "-"]]
    if kind == "close-issue":
        return [["gh", "issue", "comment", issue, "-R", EVALS_REPO, "--body-file", "-"],
                ["gh", "issue", "close", issue, "-R", EVALS_REPO, "--reason", "completed"]]
    return []


def execute(action: dict, gh) -> None:
    """Make the writes of one action."""
    kind = action["action"]
    stdin = {"create-issue": action.get("body"), "update-issue": action.get("body"),
             "close-issue": action.get("comment")}.get(kind)
    for command in commands(action):
        gh(command[1:], stdin if "--body-file" in command else None)


def main(argv: list | None = None, *, gh=retire_skill.default_gh, git=default_git,
         out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--guidance", type=Path, metavar="PATH",
                        help="an _agent-guidance checkout: the guidance commit range")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-url", default=None)
    args = parser.parse_args(argv)
    try:
        policies = regression.load_policy(args.policy)
        roster, problem = run_eval.read_roster(args.roster)
        if problem:
            raise ValueError(problem)
        arm_ids, _judge, _is_arm, malformed = run_eval.roster_models(roster)
        if not arm_ids or malformed:
            raise ValueError("the roster has no arm, or an arm that is not an id")
        as_of = compute_gates.parse_as_of(args.as_of)
        registries = compute_gates.flag_registries(args.registry)
        index = compute_gates.build_index(args.results_tree, args.evals_dir, as_of)
        doc = regression.compute(index, sorted(arm_ids), policies, as_of)
        text = json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (regression.RegressionPolicyError, ValueError, OSError, RecursionError) as exc:
        print(f"regression_issue: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    try:
        actions = plan(doc, fetch_issues(gh), registries, args.guidance, git, args.run_url)
    except retire_skill.RetireError as exc:
        print(f"regression_issue: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        out.write(json.dumps({"dry_run": True, "as_of": as_of, "actions": [
            {**a, "would_run": commands(a)} for a in actions]},
            indent=2, sort_keys=True) + "\n")
        return 0
    failed = 0
    for action in actions:
        try:
            execute(action, gh)
        except retire_skill.RetireError as exc:
            failed += 1
            print(f"regression_issue: {action['subject']} {action['id']}: {exc}",
                  file=sys.stderr)
            continue
        if action["action"] != "none":
            out.write(f"{action['action']}: {action['subject']} {action['id']}"
                      + (f" (#{action['issue']})" if action["issue"] else "") + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
