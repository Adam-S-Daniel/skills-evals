#!/usr/bin/env python3
"""Act on a `retire` verdict (#70, part 2): file or update an issue, or open
an auto-merging removal pull request in adam-agentskills.

  retire_skill.py --gates FILE --registry adam-agentskills=PATH
                  [--registry NAME=PATH ...] [--dry-run]
                  [--allow-mode proposal|auto ...]

`--gates` is scripts/compute_gates.py's output. A skill acts only when its
verdict there is `retire`, and this script re-checks what that verdict
means before acting: every (fixture, roster model) cell of the cells'
fixtures crossed with the gates file's roster models present exactly once,
and every one `no-benefit` (as harness/gates.py defines the verdict). Any
field of the wrong type is a refusal, never a crash or a pass.
compute_gates lets one skill retire per evaluation; two `retire` verdicts
here are refused, never a pick.

THE MODE is the gates file's `retirement_mode` (from evals/gate-policy.yml;
anything but `auto` is `proposal`):

  * `proposal`: an issue in skills-evals, found by a marker comment in its
    body (`ISSUE_MARKER`) on an issue `github-actions[bot]` opened, is
    created or its body updated. One issue per skill, ever: an open one is
    updated, and a closed one means the skill is already decided, so nothing
    is filed again. A human removes. An issue anyone else wrote is ignored,
    whatever it quotes.
  * `auto` (Adam, 2026-10-25; docs/decisions/0014): a branch
    `retire-skill/<skill>` is prepared in the adam-agentskills checkout; it
    is pushed, a pull request is opened, and auto-merge (merge commit) is
    enabled. No human review, so the branch must pass the registry's
    required checks on its own. Its first commit deletes
    `plugins/<plugin>/skills/<skill>/`, raises the plugin's patch version in
    both manifests (adam-agentskills ADR 0009), adds a `docs/skill-impact.md`
    entry, drops the skill from `scripts/plugin_layout.json` (the ADR 0013
    layout its tests pin) and regenerates the README skill table with the
    registry's own `scripts/generate_readme_table.py`. When `skills.lock`
    locks the plugin, a second commit re-pins it to the first with the
    registry's `scripts/generate_skills_lock.py --repin`, and
    `--check-current` must then pass (the order that script documents:
    content, commit, re-pin, commit). The two registry scripts run with a
    scrubbed environment (no token reaches them), from the checkout's
    default branch, which the registry's own CI already runs.

`--allow-mode` lists the modes the caller has wired (default: `proposal`
only, the safe one; auto must be named). The scheduled workflow allows only
`proposal`, since auto mode needs a write credential for adam-agentskills
that does not exist yet; a gates file in a mode not allowed exits 2 rather
than doing nothing quietly.

REFUSALS (exit 2, nothing written):

  * any run that is not `--dry-run` outside the scheduled workflow
    (`GITHUB_EVENT_NAME` must be `schedule`): never from a dispatch, a pull
    request or a terminal;
  * in auto mode, any run that is not `--dry-run` outside GitHub Actions
    (`GITHUB_ACTIONS` must be `true`) on the default branch (`GITHUB_REF`
    must be `refs/heads/main`);
  * in auto mode, while any removal pull request (head `retire-skill/...`) is
    open in adam-agentskills: at most one at a time, and an open one holds
    the slot whatever the newest verdict says;
  * in auto mode, a shallow adam-agentskills checkout (the lock re-pin and
    its check read the commit the lock pins, which a shallow clone lacks), a
    skill that is its plugin's last (emptying a plugin is a registry
    decision, and the lock generator refuses it), a
    `scripts/plugin_layout.json` that does not list the skill under its
    plugin, a skill whose removal that registry's `plugin-runtime-review`
    gate would hold for the owner (a `hooks/` or `bin/` directory in the
    skill, or a hook naming a path inside it), which auto-merge cannot
    approve, or a skill `scripts/skills_waivers.yml` waives a finding under
    (the waiver goes stale with it and `check_skills.py` exits 1);
  * in auto mode, a skill whose basename is not found exactly once across
    every `--registry` checkout given, or whose one copy is not a real
    `plugins/<plugin>/skills/<skill>/` directory of adam-agentskills: none
    of `plugins/`, the plugin, its `skills/`, the skill, its manifests or
    `docs/skill-impact.md` may be a symlink or resolve outside the
    checkout. In proposal mode the issue says so instead, since a human
    removes.

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

import yaml

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
LAYOUT_FILE = "scripts/plugin_layout.json"
README_FILE = "README.md"
LOCK_FILE = "skills.lock"
README_GENERATOR = "scripts/generate_readme_table.py"
LOCK_GENERATOR = "scripts/generate_skills_lock.py"
WAIVERS_FILE = "scripts/skills_waivers.yml"
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
ADR = ("https://github.com/Adam-S-Daniel/skills-evals/blob/main/docs/decisions/"
       "0014-removal-pull-requests-merge-without-review.md")
COMMIT_NAME = "github-actions[bot]"
ISSUE_AUTHOR = "github-actions[bot]"
DEFAULT_REF = "refs/heads/main"
COMMIT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# A fixture directory or a roster model id: no space, `|` or newline, so a
# value can never break the evidence table or mention anyone.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@\[\]/-]{0,127}$")


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


def check_auto_env(env) -> None:
    if env.get("GITHUB_ACTIONS") != "true" or env.get("GITHUB_REF") != DEFAULT_REF:
        raise RetireError("refusing: auto mode acts only in GitHub Actions on "
                          f"{DEFAULT_REF} (GITHUB_ACTIONS is "
                          f"{env.get('GITHUB_ACTIONS')!r}, GITHUB_REF is "
                          f"{env.get('GITHUB_REF')!r})")


def _names(value) -> bool:
    """A non-empty list of distinct NAME_RE strings."""
    return (isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and NAME_RE.fullmatch(v) for v in value)
            and len(set(value)) == len(value))


def load_gates(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise RetireError(f"cannot read the gates file ({type(exc).__name__})") from None
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 \
            or not isinstance(doc.get("skills"), dict) \
            or not _names(doc.get("roster_models")) \
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
    if not isinstance(verdict.get("reason"), str):
        raise RetireError(f"{skill}: a retire verdict whose reason is not text")
    cells = verdict.get("cells")
    roster = gates["roster_models"]
    if not isinstance(cells, list) or not cells or not _names(roster):
        raise RetireError(f"{skill}: a retire verdict with no cell")
    for c in cells:
        if not isinstance(c, dict) or c.get("class") != "no-benefit":
            raise RetireError(f"{skill}: a retire verdict with a cell that is not "
                              "no-benefit")
        fixture = c.get("fixture")
        if not (fixture is None or isinstance(fixture, str) and NAME_RE.fullmatch(fixture)) \
                or not isinstance(c.get("model"), str) \
                or not isinstance(c.get("looks"), list):
            raise RetireError(f"{skill}: a retire verdict with a malformed cell")
    pairs = [(c["fixture"], c["model"]) for c in cells]
    fixtures = {f for f, _ in pairs}
    want = {(f, m) for f in fixtures for m in roster}
    if len(set(pairs)) != len(pairs) or set(pairs) != want:
        raise RetireError(f"{skill}: the retire verdict's cells are not each fixture "
                          "crossed with each roster model exactly once (the cross product)")
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
    if directory.is_symlink():
        raise RetireError(f"{skill}: its copy is a symlink")
    if not directory.is_dir():
        raise RetireError(f"{skill}: its copy is not a real directory")
    rel = directory.relative_to(root).as_posix()
    if rel != f"plugins/{plugin}/skills/{skill}":
        raise RetireError(f"{skill}: unexpected location {rel}")
    contained(root, ["plugins", f"plugins/{plugin}", f"plugins/{plugin}/skills", rel])
    return {"plugin": plugin, "path": rel}


def contained(root: Path, rels) -> None:
    """RetireError unless each of `rels` under `root` is no symlink and
    resolves inside `root`, so no write follows a link out of the checkout."""
    base = root.resolve()
    for rel in rels:
        path = root / rel
        if path.is_symlink() or not path.resolve().is_relative_to(base):
            raise RetireError(f"{rel} is a symlink or resolves outside the {TARGET} "
                              "checkout")


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


def existing_issues(gh, skill: str) -> dict:
    """{"open": [...], "closed": [...]}: the numbers, ascending, of every
    issue, in any state, that github-actions[bot] opened with this skill's
    marker. An issue anyone else opened is ignored, whatever it quotes."""
    text = gh(["api", "--paginate",
               f"repos/{EVALS_REPO}/issues?state=all&per_page=100",
               "--jq", ".[] | select(.pull_request == null) | "
                       "{number: .number, body: (.body // \"\"), "
                       "author: .user.login, state: .state}"])
    marker = ISSUE_MARKER.format(skill=skill)
    found = {"open": [], "closed": []}
    for item in _json_lines(text):
        if item.get("author") != ISSUE_AUTHOR or not isinstance(item.get("body"), str) \
                or marker not in item["body"]:
            continue
        number, state = item.get("number"), item.get("state")
        if type(number) is not int or number < 1 or state not in found:
            raise RetireError("an issue record from the API is malformed")
        found[state].append(number)
    return {state: sorted(numbers) for state, numbers in found.items()}


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
    contained(checkout, [f"plugins/{plugin}/.claude-plugin",
                         *(f"plugins/{plugin}/{name}" for name in MANIFESTS), "docs",
                         IMPACT_FILE])
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


def layout_without(checkout: Path, plugin: str, skill: str) -> str:
    """`scripts/plugin_layout.json`'s text with `skill` dropped from
    `plugin`, in the registry's canonical form (json.dumps, indent 2, one
    trailing newline). RetireError unless the file lists the skill under the
    plugin, or when the skill is the plugin's last."""
    contained(checkout, ["scripts", LAYOUT_FILE])
    try:
        doc = json.loads((checkout / LAYOUT_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise RetireError(f"cannot read {LAYOUT_FILE}") from None
    plugins = doc.get("plugins") if isinstance(doc, dict) else None
    entry = plugins.get(plugin) if isinstance(plugins, dict) else None
    skills = entry.get("skills") if isinstance(entry, dict) else None
    if not isinstance(skills, list) or skills.count(skill) != 1:
        raise RetireError(f"{LAYOUT_FILE} does not list {skill} once under {plugin}")
    if len(skills) == 1:
        raise RetireError(f"{skill} is {plugin}'s last skill; emptying a plugin is a "
                          "registry decision, not a retirement")
    entry["skills"] = [s for s in skills if s != skill]
    return json.dumps(doc, indent=2) + "\n"


def lock_relevant(checkout: Path, plugin: str) -> bool:
    """Whether `skills.lock` locks `plugin`, so removing one of its skills
    makes the lock stale (adam-agentskills CI's `--check-current`)."""
    contained(checkout, [LOCK_FILE])
    path = checkout / LOCK_FILE
    if not path.exists():
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise RetireError(f"cannot read {LOCK_FILE}") from None
    bundles = doc.get("bundles") if isinstance(doc, dict) else None
    skills = doc.get("skills") if isinstance(doc, dict) else None
    if not isinstance(bundles, list) or not isinstance(skills, dict):
        raise RetireError(f"{LOCK_FILE} has no bundles list or skills map")
    return plugin in bundles or any(isinstance(k, str) and k.startswith(f"{plugin}/")
                                    for k in skills)


def check_registry(checkout: Path, location: dict, skill: str) -> None:
    """The auto-mode preconditions on the checkout itself; RetireError
    otherwise. Read-only, so a dry run refuses the same way."""
    if _git(checkout, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise RetireError(f"the {TARGET} checkout is shallow; the lock re-pin needs "
                          "full history (fetch-depth: 0)")
    plugin = location["plugin"]
    skills_dir = checkout / "plugins" / plugin / "skills"
    others = [p for p in skills_dir.iterdir() if p.name != skill
              and (p.is_dir() or p.is_symlink())]
    if not others:
        raise RetireError(f"{skill} is {plugin}'s last skill; emptying a plugin is a "
                          "registry decision, not a retirement")
    layout_without(checkout, plugin, skill)
    contained(checkout, [README_FILE, README_GENERATOR, LOCK_GENERATOR])
    for rel in (README_FILE, README_GENERATOR):
        if not (checkout / rel).is_file():
            raise RetireError(f"{TARGET} has no {rel}")
    if lock_relevant(checkout, plugin) and not (checkout / LOCK_GENERATOR).is_file():
        raise RetireError(f"{TARGET} has no {LOCK_GENERATOR}")
    runtime_gated(checkout, location["path"], skill)
    waived_paths(checkout, location["path"], skill)


def waived_paths(checkout: Path, path: str, skill: str) -> None:
    """RetireError when `scripts/skills_waivers.yml` waives a finding inside
    the skill: that waiver matches nothing once the skill is gone, and
    check_skills.py reports a `stale-waiver` and exits 1, so the pull request
    could never merge. Removing the waiver with the skill means editing a
    commented YAML file, which this does not do; the proposal path (a human)
    handles it. The file is parsed, never grepped — its comments name skills
    and would read as waivers."""
    contained(checkout, [WAIVERS_FILE])
    file = checkout / WAIVERS_FILE
    if not file.exists():
        return
    try:
        doc = yaml.safe_load(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        raise RetireError(f"cannot read {WAIVERS_FILE}") from None
    waivers = (doc or {}).get("waivers") if isinstance(doc, dict) else None
    if waivers is None:
        waivers = []
    if not isinstance(waivers, list):
        raise RetireError(f"{WAIVERS_FILE}: waivers is not a list")
    for waiver in waivers:
        where = waiver.get("path") if isinstance(waiver, dict) else None
        if isinstance(where, str) and (where == path or where.startswith(f"{path}/")):
            raise RetireError(f"{WAIVERS_FILE} waives a finding under {skill}; that "
                              "waiver goes stale when the skill does and check_skills.py "
                              "would exit 1, so a human retires the waiver with the skill")


def runtime_gated(checkout: Path, path: str, skill: str) -> None:
    """RetireError when deleting this skill would be a plugin RUNTIME change
    in adam-agentskills' sense (its ADR 0016 gate): a `hooks/` or `bin/`
    directory inside the skill, or a hook naming a path inside it. Such a
    pull request waits on the `plugin-runtime-review` environment for the
    owner's approval, which auto-merge cannot supply, so the branch would sit
    open forever and hold the one removal slot. No skill ships either today;
    this refuses the day one does, rather than wedging the queue."""
    for name in ("hooks", "bin"):
        if (checkout / path / name).exists():
            raise RetireError(f"{skill} ships a {name}/ directory, so removing it is a "
                              "plugin runtime change: adam-agentskills' "
                              "plugin-runtime-review gate holds such a pull request for "
                              "the owner, and auto-merge cannot approve it")
    needle = f"skills/{skill}/"
    for config in sorted(checkout.glob("plugins/*/hooks/*.json")) + [
            checkout / f"plugins/{p}/{m}" for p in
            sorted(d.name for d in (checkout / "plugins").iterdir() if d.is_dir())
            for m in MANIFESTS]:
        if config.is_symlink() or not config.is_file():
            continue
        try:
            text = config.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise RetireError(f"cannot read {config.relative_to(checkout).as_posix()}") \
                from None
        if needle in text:
            raise RetireError(
                f"{config.relative_to(checkout).as_posix()} names a path inside {skill}, "
                "so removing it is a plugin runtime change: adam-agentskills' "
                "plugin-runtime-review gate holds such a pull request for the owner, and "
                "auto-merge cannot approve it")


def run_registry_script(checkout: Path, script: str, *args: str) -> None:
    """Run one of the registry's own scripts in its checkout, with a scrubbed
    environment: no token or other secret from this workflow reaches it, and
    no bytecode is written into the checkout. Reported by exit code only."""
    contained(checkout, ["scripts", script])
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8",
           "HOME": os.environ.get("HOME", "/nonexistent"),
           "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, script, *args], cwd=str(checkout), env=env,
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RetireError(" ".join([script, *args, "exited", str(proc.returncode)]))


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


def _pr_body(gates, skill, location, versions, run_url, repin=False) -> str:
    bumps = "\n".join(f"- `{p}`: {old} -> {new}" for p, (old, new) in versions.items())
    lock = (f" A second commit re-pins `{LOCK_FILE}` to the removal commit."
            if repin else "")
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"Removes `{location['path']}`: its retirement verdict in "
            f"[skills-evals#70](https://github.com/{EVALS_REPO}/issues/70) is "
            f"**retire** as of {gates['as_of']} "
            f"({gates['skills'][skill].get('reason')}).\n\n{evidence(gates, skill)}\n\n"
            f"Version bumps:\n{bumps}\n\nAdds a `{IMPACT_FILE}` entry, drops the skill "
            f"from `{LAYOUT_FILE}` and regenerates the `{README_FILE}` skill table."
            f"{lock}\n\n"
            f"This pull request auto-merges once required checks pass, with no human "
            f"review, by Adam's 2026-10-25 decision ([skills-evals ADR 0014]({ADR})).\n"
            f"{run}\nOpened by skills-evals' scripts/retire_skill.py on its scheduled "
            "workflow.\n")


def plan(gates: dict, registries: dict, gh, run_url: str | None = None,
         allowed=("proposal",)) -> dict:
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
        issues = existing_issues(gh, skill)
        if not issues["open"] and issues["closed"]:
            return {"action": "none", "mode": mode, "skill": skill,
                    "issue": issues["closed"][0],
                    "reason": f"{skill} is already decided: issue "
                              f"#{issues['closed'][0]} is closed, so none is filed again"}
        number = issues["open"][0] if issues["open"] else None
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
    check_registry(checkout, location, skill)
    repin = lock_relevant(checkout, location["plugin"])
    entry = impact_entry(gates, skill, location["plugin"], run_url)
    return {"action": "removal", "mode": mode, "skill": skill, **location,
            "branch": f"{BRANCH_PREFIX}{skill}", "versions": versions,
            "impact_entry": entry, "repin": repin,
            "title": f"Remove {location['plugin']}/{skill}: no benefit (skills-evals#70)",
            "body": _pr_body(gates, skill, location, versions, run_url, repin)}


def prepare_branch(checkout: Path, action: dict) -> None:
    """The removal commit, and the lock re-pin when the plugin is locked, on
    a new branch of `checkout`, which must be clean."""
    if _git(checkout, "status", "--porcelain"):
        raise RetireError(f"the {TARGET} checkout has uncommitted changes")
    contained(checkout, ["plugins", f"plugins/{action['plugin']}",
                         f"plugins/{action['plugin']}/skills", action["path"],
                         f"plugins/{action['plugin']}/.claude-plugin", *action["versions"],
                         "docs", IMPACT_FILE])
    check_registry(checkout, action, action["skill"])
    layout = layout_without(checkout, action["plugin"], action["skill"])
    _git(checkout, "checkout", "-b", action["branch"])
    _git(checkout, "rm", "-r", "-q", "--", action["path"])
    for rel, (old, new) in action["versions"].items():
        path = checkout / rel
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or doc.get("version") != old:
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
    (checkout / LAYOUT_FILE).write_text(layout, encoding="utf-8")
    run_registry_script(checkout, README_GENERATOR)
    _git(checkout, "add", "--", IMPACT_FILE, LAYOUT_FILE, README_FILE, *action["versions"])
    _commit(checkout,
            f"Remove {action['plugin']}/{action['skill']}: no benefit on every roster model\n\n"
            "skills-evals#70's scheduled retirement found no benefit in every cell at "
            "two fixed looks.")
    if action.get("repin"):
        run_registry_script(checkout, LOCK_GENERATOR, "--repin")
        run_registry_script(checkout, LOCK_GENERATOR, "--check-current")
        _git(checkout, "add", "--", LOCK_FILE)
        _commit(checkout, f"Re-pin skills.lock after removing {action['plugin']}/"
                          f"{action['skill']}\n\n"
                          "The lock pinned a commit that still has the skill, so its "
                          "--check-current would fail; it now pins the removal commit.")
    if _git(checkout, "status", "--porcelain"):
        raise RetireError(f"the {TARGET} checkout has changes the removal did not commit")


def _commit(checkout: Path, message: str) -> None:
    _git(checkout, "-c", f"user.name={COMMIT_NAME}", "-c", f"user.email={COMMIT_EMAIL}",
         "commit", "-q", "-m", message)


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
                ["edit", LAYOUT_FILE, f"drop {action['skill']}"],
                ["python3", README_GENERATOR],
                ["git", "commit"],
                *([["python3", LOCK_GENERATOR, "--repin"],
                   ["python3", LOCK_GENERATOR, "--check-current"],
                   ["git", "commit"]] if action.get("repin") else []),
                ["git", "push", "origin", f"HEAD:refs/heads/{action['branch']}"],
                ["gh", "pr", "create", "-R", REGISTRY_REPO, "--base", "main",
                 "--head", action["branch"], "--title", action["title"], "--body-file", "-"],
                ["gh", "pr", "merge", "<new pull request url>", "-R", REGISTRY_REPO,
                 "--auto", "--merge"]]
    return []


def execute(action: dict, registries: dict, gh, push, env) -> str:
    kind = action["action"]
    if kind == "none":
        return action["reason"]
    if kind == "create-issue":
        gh(commands(action)[0][1:], action["body"])
        return f"filed an issue for {action['skill']}"
    if kind == "update-issue":
        gh(commands(action)[0][1:], action["body"])
        return f"updated issue #{action['issue']} for {action['skill']}"
    check_auto_env(env)
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
        allowed = tuple(args.allow_mode or ("proposal",))
        if not args.dry_run and mode_of(gates) == "auto" and "auto" in allowed:
            check_auto_env(env)
        action = plan(gates, registries, gh, run_url, allowed)
        if args.dry_run:
            out.write(json.dumps({"dry_run": True, **action,
                                  "would_run": commands(action)},
                                 indent=2, sort_keys=True) + "\n")
            return 0
        out.write(execute(action, registries, gh, push, env) + "\n")
    except (RetireError, ValueError) as exc:
        print(f"retire_skill: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
