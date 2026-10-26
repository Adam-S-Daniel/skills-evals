#!/usr/bin/env python3
"""Act on a `retire` verdict (#70, part 2): file or update an issue, or open
an auto-merging removal pull request in adam-agentskills.

  retire_skill.py --gates FILE --registry adam-agentskills=PATH
                  [--registry NAME=PATH ...] [--dry-run]
                  [--allow-mode proposal|auto ...]

`--gates` is scripts/compute_gates.py's output. A skill acts only when its
verdict there is `retire`, and this script re-checks what that verdict
means before acting: at least one cell, every cell `no-benefit`, and the
cells' models exactly the gates file's roster models (every current roster
arm, as harness/gates.py defines the verdict). compute_gates lets one skill
retire per evaluation; two `retire` verdicts here are refused, never a pick.

THE MODE is the gates file's `retirement_mode` (from evals/gate-policy.yml;
anything but `auto` is `proposal`):

  * `proposal`: an issue in skills-evals, found by a marker comment in its
    body (`ISSUE_MARKER`), is created or its body updated. A human removes.
  * `auto` (Adam, 2026-10-25; docs/decisions/0014): a branch
    `retire-skill/<skill>` is prepared in the adam-agentskills checkout that
    deletes `plugins/<plugin>/skills/<skill>/`, raises the plugin's patch
    version in both manifests (adam-agentskills ADR 0009) and adds a
    `docs/skill-impact.md` entry; it is pushed, a pull request is opened, and
    auto-merge (merge commit) is enabled. No human review.

`--allow-mode` lists the modes the caller has wired (default: both). The
scheduled workflow allows only `proposal`, since auto mode needs a write
credential for adam-agentskills that does not exist yet; a gates file in a
mode not allowed exits 2 rather than doing nothing quietly.

REFUSALS (exit 2, nothing written):

  * any run that is not `--dry-run` outside the scheduled workflow
    (`GITHUB_EVENT_NAME` must be `schedule`): never from a dispatch, a pull
    request or a terminal;
  * in auto mode, while any removal pull request (head `retire-skill/...`) is
    open in adam-agentskills: at most one at a time, and an open one holds
    the slot whatever the newest verdict says;
  * in auto mode, a skill whose basename is not found exactly once across
    every `--registry` checkout given, or whose one copy is not a real
    `plugins/<plugin>/skills/<skill>/` directory of adam-agentskills. In
    proposal mode the issue says so instead, since a human removes.

`--dry-run` reads (the gates file, the checkouts, and open pull requests or
issues through `gh`), writes nothing, and prints the plan as JSON: the
action, the issue or pull request text, and the commands it would run.

Every GitHub call goes through one function, `gh(args, stdin)` (the `gh`
CLI), and every push through `push(checkout, branch)`, both injectable, so
tests need no network. An error from `gh` is reported by its exit code
only, never its output. Deterministic: no clock; the skill-impact date is
the gates file's `as_of`.

The gate guards against honest mistakes, not forged results (Adam,
2026-10-26): anyone who can write the results can also remove a skill.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import delivery  # noqa: E402

TARGET = "adam-agentskills"
REGISTRY_REPO = "Adam-S-Daniel/adam-agentskills"
EVALS_REPO = "Adam-S-Daniel/skills-evals"
BRANCH_PREFIX = "retire-skill/"
ISSUE_MARKER = "<!-- skills-evals:retire-skill:{skill} -->"
IMPACT_FILE = "docs/skill-impact.md"
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
ADR = ("https://github.com/Adam-S-Daniel/skills-evals/blob/main/docs/decisions/"
       "0014-removal-pull-requests-merge-without-review.md")
COMMIT_NAME = "github-actions[bot]"
COMMIT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class RetireError(Exception):
    """A refusal: nothing is written."""


def default_gh(args: list, stdin: str | None = None) -> str:
    """Run `gh` and return its stdout; its output is never echoed on failure,
    since an API error body can carry data a public log must not."""
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True,
                          text=True, check=False)
    if proc.returncode != 0:
        raise RetireError(f"gh {args[0]} exited {proc.returncode}")
    return proc.stdout


def default_push(checkout: Path, branch: str) -> None:
    proc = subprocess.run(["git", "-C", str(checkout), "push", "origin",
                           f"HEAD:refs/heads/{branch}"],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RetireError(f"git push exited {proc.returncode}")


def _git(checkout: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(checkout), *args],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RetireError(f"git {args[0]} exited {proc.returncode}")
    return proc.stdout


def check_event(env) -> None:
    if env.get("GITHUB_EVENT_NAME") != "schedule":
        raise RetireError("refusing: only the scheduled workflow acts on a retire "
                          f"verdict (GITHUB_EVENT_NAME is {env.get('GITHUB_EVENT_NAME')!r})")


def load_gates(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise RetireError(f"cannot read the gates file ({type(exc).__name__})") from None
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 \
            or not isinstance(doc.get("skills"), dict) \
            or not isinstance(doc.get("roster_models"), list) \
            or not isinstance(doc.get("as_of"), str) \
            or not re.fullmatch(r"\d{8}T\d{6}Z", doc["as_of"]):
        raise RetireError("the gates file is not compute_gates.py schema 1")
    return doc


def mode_of(gates: dict) -> str:
    return "auto" if gates.get("retirement_mode") == "auto" else "proposal"


def retiring(gates: dict) -> str | None:
    """The one skill whose verdict is `retire`, re-checked; None when none.
    RetireError for two, or for a `retire` the cells do not support."""
    names = sorted(n for n, v in gates["skills"].items()
                   if isinstance(v, dict) and v.get("verdict") == "retire")
    if not names:
        return None
    if len(names) > 1:
        raise RetireError(f"{len(names)} skills have a retire verdict; compute_gates "
                          "allows one per evaluation")
    skill, verdict = names[0], gates["skills"][names[0]]
    if not SKILL_RE.fullmatch(skill):
        raise RetireError("the retiring skill's name is not a skill basename")
    cells = verdict.get("cells")
    roster = sorted(gates["roster_models"])
    if not isinstance(cells, list) or not cells or not roster:
        raise RetireError(f"{skill}: a retire verdict with no cell")
    if any(not isinstance(c, dict) or c.get("class") != "no-benefit" for c in cells):
        raise RetireError(f"{skill}: a retire verdict with a cell that is not no-benefit")
    if sorted({c.get("model") for c in cells}) != roster:
        raise RetireError(f"{skill}: the retire verdict's cells do not cover exactly "
                          "the roster models")
    return skill


def locate(registries: dict, skill: str) -> dict:
    """{"plugin", "path"} of the one copy of `skill`, in adam-agentskills;
    RetireError otherwise."""
    if TARGET not in registries:
        raise RetireError(f"no {TARGET} checkout was given (--registry {TARGET}=PATH)")
    try:
        matches = delivery._registry_matches(registries, None, skill)
    except delivery.DeliveryError:
        raise RetireError(f"{skill}: a copy escapes its checkout") from None
    root = Path(registries[TARGET]["path"])
    dirs = sorted(p for p in root.glob(f"plugins/*/skills/{skill}") if p.exists()
                  or p.is_symlink())
    if len(matches) != 1 or len(dirs) != 1:
        raise RetireError(f"{skill}: basename found {len(matches)} time(s) across the "
                          f"registries given, not exactly once")
    identity, plugin, directory = matches[0]
    if directory != dirs[0] or not directory.is_relative_to(root):
        raise RetireError(f"{skill}: its one copy is not in {TARGET}")
    if directory.is_symlink() or not directory.is_dir():
        raise RetireError(f"{skill}: its copy is not a real directory")
    rel = directory.relative_to(root).as_posix()
    if rel != f"plugins/{plugin}/skills/{skill}":
        raise RetireError(f"{skill}: unexpected location {rel}")
    return {"plugin": plugin, "path": rel}


def _json_lines(text: str) -> list:
    out = []
    for line in text.splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                out.append(item)
    return out


def open_removal_prs(gh) -> list:
    text = gh(["api", "--paginate",
               f"repos/{REGISTRY_REPO}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text)
            if isinstance(p.get("head"), str) and p["head"].startswith(BRANCH_PREFIX)]


def open_issue(gh, skill: str) -> int | None:
    text = gh(["api", "--paginate",
               f"repos/{EVALS_REPO}/issues?state=open&per_page=100",
               "--jq", ".[] | select(.pull_request == null) | "
                       "{number: .number, body: (.body // \"\")}"])
    marker = ISSUE_MARKER.format(skill=skill)
    found = sorted(i["number"] for i in _json_lines(text)
                   if isinstance(i.get("body"), str) and marker in i["body"])
    return found[0] if found else None


def _figure(block, field):
    if not isinstance(block, dict) or not isinstance(block.get(field), (int, float)):
        return "n/a"
    return f"{block[field]:.3f}"


def evidence(gates: dict, skill: str) -> str:
    """A Markdown table of the verdict's cells."""
    rows = ["| Fixture | Model | Runs with | Runs without | Objective upper | "
            "Judge upper | Looks |", "|---|---|---|---|---|---|---|"]
    for cell in gates["skills"][skill]["cells"]:
        arms = [cell.get(a) if isinstance(cell.get(a), dict) else {}
                for a in ("with", "without")]
        looks = ", ".join(str(look.get("n")) for look in cell.get("looks") or []
                          if isinstance(look, dict))
        rows.append(f"| {cell.get('fixture') or '(flat)'} | {cell.get('model')} | "
                    f"{arms[0].get('runs', 'n/a')} | {arms[1].get('runs', 'n/a')} | "
                    f"{_figure(cell.get('objective'), 'retire_upper')} | "
                    f"{_figure(cell.get('judge'), 'retire_upper')} | {looks} |")
    return "\n".join(rows)


def _date(as_of: str) -> str:
    return f"{as_of[0:4]}-{as_of[4:6]}-{as_of[6:8]}"


def impact_entry(gates: dict, skill: str, plugin: str, run_url: str | None) -> str:
    cells = gates["skills"][skill]["cells"]
    fixtures = sorted({c.get("fixture") or "(flat)" for c in cells})
    where = f"workflow run {run_url}" if run_url else "the scheduled workflow"
    return (f"## {_date(gates['as_of'])} — {plugin}/{skill} — remove\n\n"
            f"- Motivation: skills-evals#70's retirement verdict is `retire`: every cell "
            f"({len(fixtures)} fixture(s) x {len(gates['roster_models'])} roster model(s)) "
            f"shows no benefit at two fixed looks.\n"
            f"- Change: `plugins/{plugin}/skills/{skill}/` removed and the "
            f"`{plugin}` patch version raised, by skills-evals' scheduled retirement "
            f"({where}).\n"
            f"- Eval: pooled runs as of {gates['as_of']}, policy evals/gate-policy.yml; "
            f"fixtures {', '.join(fixtures)}; per-cell bounds in the pull request.\n"
            f"- Outcome: auto-merges once required checks pass, with no human review "
            f"(skills-evals ADR 0014, Adam's 2026-10-25 decision).\n")


def insert_entry(text: str, entry: str) -> str:
    """`entry` newest first: right after the header's `---` rule."""
    lines = text.split("\n")
    try:
        rule = lines.index("---")
    except ValueError:
        raise RetireError(f"{IMPACT_FILE} has no `---` rule to insert after") from None
    head = "\n".join(lines[:rule + 1]).rstrip("\n")
    rest = "\n".join(lines[rule + 1:]).lstrip("\n")
    return f"{head}\n\n{entry}\n{rest}"


def bump(version: str) -> str:
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if not match:
        raise RetireError("a plugin version is not MAJOR.MINOR.PATCH")
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}"


def manifest_versions(checkout: Path, plugin: str) -> dict:
    """{manifest path: (old, new)}; both manifests must agree."""
    out = {}
    for name in MANIFESTS:
        rel = f"plugins/{plugin}/{name}"
        try:
            doc = json.loads((checkout / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            raise RetireError(f"cannot read {rel}") from None
        version = doc.get("version") if isinstance(doc, dict) else None
        out[rel] = (version, bump(version))
    if len({old for old, _ in out.values()}) != 1:
        raise RetireError(f"{plugin}'s two manifests disagree on its version")
    return out


def _issue_body(gates, skill, location, problem, run_url) -> str:
    where = (f"`{location['path']}` in {REGISTRY_REPO}" if location
             else f"not located: {problem}")
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"{ISSUE_MARKER.format(skill=skill)}\n"
            f"The retirement verdict for `{skill}` is **retire** as of "
            f"{gates['as_of']}: {gates['skills'][skill].get('reason')}.\n\n"
            f"`evals/gate-policy.yml` sets `retirement_mode: proposal`, so a human "
            f"removes it. Copy: {where}.\n\n{evidence(gates, skill)}\n{run}\n"
            "Filed by scripts/retire_skill.py on the scheduled workflow (#70).\n")


def _pr_body(gates, skill, location, versions, run_url) -> str:
    bumps = "\n".join(f"- `{p}`: {old} -> {new}" for p, (old, new) in versions.items())
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"Removes `{location['path']}`: its retirement verdict in "
            f"[skills-evals#70](https://github.com/{EVALS_REPO}/issues/70) is "
            f"**retire** as of {gates['as_of']} "
            f"({gates['skills'][skill].get('reason')}).\n\n{evidence(gates, skill)}\n\n"
            f"Version bumps:\n{bumps}\n\nAdds a `{IMPACT_FILE}` entry.\n\n"
            f"This pull request auto-merges once required checks pass, with no human "
            f"review, by Adam's 2026-10-25 decision ([skills-evals ADR 0014]({ADR})).\n"
            f"{run}\nOpened by skills-evals' scripts/retire_skill.py on its scheduled "
            "workflow.\n")


def plan(gates: dict, registries: dict, gh, run_url: str | None = None,
         allowed=("auto", "proposal")) -> dict:
    """What to do, read-only. RetireError for a refusal."""
    skill = retiring(gates)
    mode = mode_of(gates)
    if skill is None:
        return {"action": "none", "mode": mode, "reason": "no skill has a retire verdict"}
    if mode not in allowed:
        raise RetireError(f"retirement_mode is {mode}, which this caller has not wired "
                          f"(allowed: {', '.join(allowed)})")
    if mode == "proposal":
        try:
            location, problem = locate(registries, skill), None
        except RetireError as exc:
            location, problem = None, str(exc)
        number = open_issue(gh, skill)
        return {"action": "update-issue" if number else "create-issue", "mode": mode,
                "skill": skill, "issue": number,
                "title": f"Retire skill {skill}: no benefit on every roster model (#70)",
                "body": _issue_body(gates, skill, location, problem, run_url)}
    prs = open_removal_prs(gh)
    if prs:
        raise RetireError("a removal pull request is already open: "
                          + ", ".join(str(p.get("url")) for p in prs))
    location = locate(registries, skill)
    checkout = Path(registries[TARGET]["path"])
    versions = manifest_versions(checkout, location["plugin"])
    entry = impact_entry(gates, skill, location["plugin"], run_url)
    return {"action": "removal", "mode": mode, "skill": skill, **location,
            "branch": f"{BRANCH_PREFIX}{skill}", "versions": versions,
            "impact_entry": entry,
            "title": f"Remove {location['plugin']}/{skill}: no benefit (skills-evals#70)",
            "body": _pr_body(gates, skill, location, versions, run_url)}


def prepare_branch(checkout: Path, action: dict) -> None:
    """The removal commit on a new branch of `checkout`, which must be clean."""
    if _git(checkout, "status", "--porcelain"):
        raise RetireError(f"the {TARGET} checkout has uncommitted changes")
    _git(checkout, "checkout", "-b", action["branch"])
    _git(checkout, "rm", "-r", "-q", "--", action["path"])
    for rel, (old, new) in action["versions"].items():
        path = checkout / rel
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("version") != old:
            raise RetireError(f"{rel} changed under the plan")
        text = path.read_text(encoding="utf-8")
        needle = f'"version": "{old}"'
        if text.count(needle) != 1:
            raise RetireError(f"{rel}: its version is not written once as {needle}")
        path.write_text(text.replace(needle, f'"version": "{new}"'), encoding="utf-8")
    impact = checkout / IMPACT_FILE
    try:
        text = impact.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise RetireError(f"cannot read {IMPACT_FILE}") from None
    impact.write_text(insert_entry(text, action["impact_entry"]), encoding="utf-8")
    _git(checkout, "add", "--", IMPACT_FILE, *action["versions"])
    _git(checkout, "-c", f"user.name={COMMIT_NAME}", "-c", f"user.email={COMMIT_EMAIL}",
         "commit", "-q", "-m",
         f"Remove {action['plugin']}/{action['skill']}: no benefit on every roster model\n\n"
         "skills-evals#70's scheduled retirement found no benefit in every cell at "
         "two fixed looks.")


def commands(action: dict) -> list:
    """The writes `execute` makes, for a dry run."""
    kind = action["action"]
    if kind == "create-issue":
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 "--body-file", "-"]]
    if kind == "update-issue":
        return [["gh", "issue", "edit", str(action["issue"]), "-R", EVALS_REPO,
                 "--body-file", "-"]]
    if kind == "removal":
        return [["git", "checkout", "-b", action["branch"]],
                ["git", "rm", "-r", "--", action["path"]],
                *[["edit", rel, f"version {old} -> {new}"]
                  for rel, (old, new) in action["versions"].items()],
                ["edit", IMPACT_FILE, "insert the entry"],
                ["git", "commit"],
                ["git", "push", "origin", f"HEAD:refs/heads/{action['branch']}"],
                ["gh", "pr", "create", "-R", REGISTRY_REPO, "--base", "main",
                 "--head", action["branch"], "--title", action["title"], "--body-file", "-"],
                ["gh", "pr", "merge", "<new pull request url>", "-R", REGISTRY_REPO,
                 "--auto", "--merge"]]
    return []


def execute(action: dict, registries: dict, gh, push) -> str:
    kind = action["action"]
    if kind == "none":
        return action["reason"]
    if kind == "create-issue":
        gh(commands(action)[0][1:], action["body"])
        return f"filed an issue for {action['skill']}"
    if kind == "update-issue":
        gh(commands(action)[0][1:], action["body"])
        return f"updated issue #{action['issue']} for {action['skill']}"
    checkout = Path(registries[TARGET]["path"])
    prepare_branch(checkout, action)
    push(checkout, action["branch"])
    url = gh(["pr", "create", "-R", REGISTRY_REPO, "--base", "main",
              "--head", action["branch"], "--title", action["title"],
              "--body-file", "-"], action["body"]).strip()
    gh(["pr", "merge", url, "-R", REGISTRY_REPO, "--auto", "--merge"])
    return f"opened {url} with auto-merge"


def main(argv: list | None = None, *, env=None, gh=default_gh, push=default_push,
         out=sys.stdout) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gates", required=True, type=Path)
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--allow-mode", action="append", choices=("auto", "proposal"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    run_url = None
    if env.get("GITHUB_RUN_ID") and env.get("GITHUB_REPOSITORY") == EVALS_REPO \
            and env["GITHUB_RUN_ID"].isdigit():
        run_url = (f"https://github.com/{EVALS_REPO}/actions/runs/{env['GITHUB_RUN_ID']}")
    try:
        if not args.dry_run:
            check_event(env)
        gates = load_gates(args.gates)
        registries = compute_gates.flag_registries(args.registry)
        action = plan(gates, registries, gh, run_url,
                      tuple(args.allow_mode or ("auto", "proposal")))
        if args.dry_run:
            out.write(json.dumps({"dry_run": True, **action,
                                  "would_run": commands(action)},
                                 indent=2, sort_keys=True) + "\n")
            return 0
        out.write(execute(action, registries, gh, push) + "\n")
    except (RetireError, ValueError) as exc:
        print(f"retire_skill: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
