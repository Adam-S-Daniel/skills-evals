#!/usr/bin/env python3
"""Act on a `retire` verdict (#70, part 2): file or update an issue, or open
an auto-merging removal pull request in adam-agentskills.

  retire_skill.py --gates FILE --registry adam-agentskills=PATH
                  [--registry NAME=PATH ...] [--dry-run]
                  [--allow-mode proposal|auto ...] [--usage FILE]

`--gates` is scripts/compute_gates.py's output. A skill acts only when its
verdict there is `retire`, and this script re-checks what that verdict
means before acting: every (fixture, roster model) cell of the cells'
fixtures crossed with the gates file's roster models present exactly once,
every one `no-benefit`, `no-clear-effect`, `cannot-discriminate` or parked
(`gates.PARKED_CLASSES`: `ceiling`, `ceiling-unconfirmed`, or `paused` for
a fixture the eval scope pass paused), and at least one `no-benefit` or
`no-clear-effect`
(a cell with headroom; harness/gates.py, THE VERDICT). Any field of the
wrong type is a refusal, never a crash or a pass.
compute_gates lets one skill retire per evaluation; two `retire` verdicts
here are refused, never a pick.

THE MODE is the gates file's `retirement_mode` (from evals/gate-policy.yml;
anything but `auto` is `proposal`), lowered to `proposal` in three cases (the
removal path's `effective_mode`, as scripts/improve_gate.py lowers an
improvement to a draft):

  * the verdict's own `removal` is not `auto` (2026-11-03: a subject with
    one cell with headroom, or a cell that reached the run cap with no clear
    effect, is only ever proposed; harness/gates.py, THE VERDICT);
  * removing the skill would wait on adam-agentskills' plugin-runtime-review,
    which auto-merge cannot approve (adam-agentskills ADR 0021, decision 4):
    improve_gate.py's `auto_refusal`, a skill with its own `hooks/` or `bin/`
    or one a hook of its plugin names a path in;
  * the caller has no write credential for adam-agentskills this run
    (`--fallback-to-proposal` without `--allow-mode auto`): the scheduled
    workflow passes it when the GitHub App token was not minted.

The issue says why, and a human removes.

  * `proposal`: an issue in skills-evals, found by a marker comment in its
    body (`ISSUE_MARKER`) on an issue `github-actions[bot]` opened, is
    created or its body updated. One issue per skill, ever: an open one is
    updated, and a closed one means the skill is already decided, so nothing
    is filed again. A human removes. An issue anyone else wrote is ignored,
    whatever it quotes.
  * `auto` (Adam, 2026-10-25; docs/decisions/0014 and adam-agentskills ADR
    0021): a branch `retire-skill/<skill>` is prepared in the
    adam-agentskills checkout; it is pushed (and the push verified with
    `git merge-base --is-ancestor`), a ready pull request is opened, labeled
    `agent-authored`, and auto-merge (merge commit, `--match-head-commit`)
    is enabled and read back. No human review, so the branch must pass the
    registry's required checks on its own. Its first commit deletes
    `plugins/<plugin>/skills/<skill>/`, raises the plugin's MAJOR version in
    both manifests (adam-agentskills ADR 0009 requires a raise; removing a
    skill breaks every consumer that calls it, which the registry has bumped
    as major before, `adam-coding-local` 1.1.0 -> 2.0.0 for `sync-skills`),
    adds a `docs/skill-impact.md` entry, drops the skill from
    `scripts/plugin_layout.json` (the ADR 0013
    layout its tests pin) and regenerates the README skill table with the
    registry's own `scripts/generate_readme_table.py`. When `skills.lock`
    locks the plugin, a second commit re-pins it to the first with the
    registry's `scripts/generate_skills_lock.py --repin`, and
    `--check-current` must then pass (the order that script documents:
    content, commit, re-pin, commit). The two registry scripts run with a
    scrubbed environment (no token reaches them), from the checkout's
    default branch, which the registry's own CI already runs. Registry
    writes use the token in `REGISTRY_TOKEN` (the App's), never `GH_TOKEN`
    (this repository's, for the issue path).

`--allow-mode` lists the modes the caller has wired (default: `proposal`
only, the safe one; auto must be named). A gates file in a mode not allowed
exits 2 rather than doing nothing quietly, unless `--fallback-to-proposal`
lowers auto to proposal.

AUTO MODE OPENS NOTHING (exit 0, nothing written) while any loop pull
request is open in adam-agentskills (head `eval-improve/`, `draft-skill/` or
`retire-skill/`; the slot routine-improve-gate.yml's `registry-pr` job
checks): all three write the bundle version, `docs/skill-impact.md` and
`skills.lock`, so a second would conflict once the first merged
(adam-agentskills ADR 0021, decision 5). Nor while a closed pull request
from `retire-skill/<skill>` exists: a person closed it, so the skill is
decided, as a closed issue decides a proposal.

REFUSALS (exit 2, nothing written):

  * any run that is not `--dry-run` outside the scheduled workflow
    (`GITHUB_EVENT_NAME` must be `schedule`): never from a dispatch, a pull
    request or a terminal;
  * in auto mode, any run that is not `--dry-run` outside GitHub Actions
    (`GITHUB_ACTIONS` must be `true`) on the default branch (`GITHUB_REF`
    must be `refs/heads/main`);
  * in auto mode, a shallow adam-agentskills checkout (the lock re-pin and
    its check read the commit the lock pins, which a shallow clone lacks), a
    skill that is its plugin's last (emptying a plugin is a registry
    decision, and the lock generator refuses it), a
    `scripts/plugin_layout.json` that does not list the skill under its
    plugin, a skill whose removal that registry's `plugin-runtime-review`
    gate would hold for the owner although its plugin runs no code (a
    `hooks/` or `bin/` directory in the skill, or another plugin's hook
    naming a path inside it), which auto-merge cannot
    approve, a skill `scripts/skills_waivers.yml` waives a finding under
    (the waiver goes stale with it and `check_skills.py` exits 1), or a
    skill defining a test that a tracked source elsewhere cites by name (the
    registry's citation test would fail on the dangling name);
  * in auto mode, a skill whose basename is not found exactly once across
    every `--registry` checkout given, or whose one copy is not a real
    `plugins/<plugin>/skills/<skill>/` directory of adam-agentskills: none
    of `plugins/`, the plugin, its `skills/`, the skill, its manifests or
    `docs/skill-impact.md` may be a symlink or resolve outside the
    checkout. In proposal mode the issue says so instead, since a human
    removes.

Only adam-agentskills is ever written. The private registry,
adam-agentskills-private, is never a target (adam-agentskills ADR 0021,
decision 7): the scheduled job does not check it out, so a skill there has
no tested digest and never reaches `retire`, and a `--registry` copy found
anywhere but adam-agentskills is refused in auto mode.

`--dry-run` reads (the gates file, the checkouts, and open pull requests or
issues through `gh`), writes nothing, and prints the plan as JSON: the
action, the issue or pull request text, and the commands it would run.

Every GitHub call goes through one of two functions, `gh(args, stdin)` (the
`gh` CLI with `GH_TOKEN`: reads, and skills-evals issues) and
`registry_gh(args, stdin)` (with `REGISTRY_TOKEN`: adam-agentskills
writes), and every push through `push(checkout, branch)`, all injectable,
so tests need no network. An error from `gh` is reported by its exit code
only, never its output. Deterministic: no clock; the skill-impact date is
`--date` (the workflow passes the run's UTC date), else the gates file's
`as_of`.

`--usage` is the published `usage/weekly-local.json`; the issue body names
the skill's invocations over the four weeks ending at the gates file's
`as_of` (harness/skill_usage.weight), or says `unknown` when there is no
fresh census. It informs the human; it changes no decision.

The gate guards against honest mistakes, not forged results (Adam,
2026-10-26): anyone who can write the results can also remove a skill.

GUIDANCE SECTIONS (`--target guidance`, skills-evals#124; the functions
named `guidance_*` below, kept apart from the skill path). The gates file's
`guidance` block and `guidance_retirement_mode` decide, read the same way:

  * a `retire` verdict, re-checked as a skill's is, and its section-alone
    pair too (`guidance_proposal_only`: an alone pair with no cell, or with
    a cell that has not decided, allows only a proposal, 2026-11-03): in `proposal` mode an
    issue in skills-evals (`GUIDANCE_ISSUE_MARKER`); in `auto` mode (Adam:
    removal is automatic, 2026-10-10, and its pull requests auto-merge,
    2026-10-25) a branch `retire-guidance/<section>` in the
    `--guidance PATH` checkout of _agent-guidance that removes the
    section's extent from its file (the whole file for a sections/*.md file
    with no other `##`; for base.md, re-copied to the repository's own
    `.claude/hooks/fleet-guidance.md` payload), deletes its
    `agents-md/eval-coverage.yml` row,
    rewrites the manifest's bytes (`check-guidance-coverage.js
    --write-bytes`), adds a typed `remove` entry to
    `docs/guidance-impact.md` whose `Eval:` line names the fixtures, the
    pooled run count (`n=`) and the policy, and regenerates `AGENTS.md`
    exactly as that repository's own instructions say: managed output with
    its trailing newlines stripped, then everything from the `## Repo-
    specific additions` heading LINE (never the first occurrence of the
    substring, which the managed header quotes); pushed, opened, labeled
    `agent-authored` and armed to auto-merge (merge commit, matched to the
    removal head, read back), one at a time (`retire-guidance/` heads),
    and then a removal notice filed here (#557: an `agent-authored` issue,
    `GUIDANCE_NOTICE_MARKER`, that mentions Adam, links the removal pull
    request and says how to reverse it: close it, or press Revert once it
    has merged). The explorer lists every removed section from the impact
    file's `remove` entries (scripts/explorer_data.py `removed_sections`).
    These writes to _agent-guidance go through `registry_gh` and the push
    with `REGISTRY_TOKEN`, as the skill path's do; the issues stay on `gh`.
    With `--fallback-to-proposal`, `auto` mode without `auto` allowed (no
    token reached the run) files the issue instead of exiting 2, and the
    issue says why;
  * a `shorten-or-merge` verdict (the section helps only alone): an issue in
    skills-evals (`SHORTEN_ISSUE_MARKER`) in either mode, never a removal.

One action per evaluation: a `retire` first, else the first
`shorten-or-merge` section by name. As a closed `retire-skill/<skill>` pull
request decides a skill, a closed `retire-guidance/<section>` one decides a
section: no removal is opened for it again.

WITHDRAWAL (`--withdraw-stale`, with or without `--target guidance`; ADR
0014, the known limit round 8 recorded). It runs before each scheduled pass
and after every ingest (loop-pr-refresh.yml's `withdraw` job, ahead of its
refresh). It lists the target repository's open pull requests and, for
each the loop opened (head `retire-skill/` or `retire-guidance/`, the
`agent-authored` label, and `LOOP_AUTHOR` as author) that is not labeled
`on-hold`, re-reads its subject's verdict (`removal_support`). A verdict
that no longer supports an automatic removal (not `retire`, or a `retire`
lowered to a proposal; a `retire-pending` whose `raw_verdict` is `retire`
still supports it, since `finalize` only ranks it behind another subject)
withdraws it: auto-merge is turned off and read back, a comment gives the
new verdict, why and the override, the pull request is closed with its
branch kept, and the subject's retirement issue here (the proposal path's
marker) is filed, or the oldest open one gets a comment (its body is kept),
to record it; any open removal notice (#557) for the subject is closed as
not planned and then commented on, best effort. A closed removal pull request
decides its subject, so the loop never reopens it. Only verdicts newer than
a pull request's basis judge it: one whose body's "**retire** as of <as_of>"
is later than the document's `as_of` is kept; with no basis in its body,
one whose `created_at` is later, or with either time unknown, is kept. The
override is a person's: remove `agent-authored`, then reopen and merge by
hand; a pull request without the label is not the loop's. While the
target's mode is `proposal` (the one switch), and in either mode while the
verdict's data is incomplete (an `insufficient` verdict over a `missing` or
`insufficient` cell, or a section's `retire` lowered only by its unfinished
alone pair), a removal is only disarmed: left open, labeled `loop-disarmed`
and commented once. In `auto` mode a labeled one whose verdict supports it
again is armed again and unlabeled; one a person disarmed (no label) never
is. Unknown data never withdraws: a missing or
unreadable gates document (or no guidance block) withdraws nothing and
exits 0 with a status naming no subject, and a subject the document does
not list, whose verdict raised in compute_gates.py (`VERDICT_RAISED`) or
whose `retire` fails the re-check is kept. `withdrawal_decision` is the
pure decision; the pull request writes go through `registry_gh` (the App
token in `REGISTRY_TOKEN`) and the issues through `gh`, in GitHub Actions on
main only, and a missing token with something to withdraw exits 2.
`refresh_allowed` is the same verdict read for loop-pr-refresh.yml, which
brings a removal up to date only while it would still be kept.
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import compute_gates  # noqa: E402
import gates  # noqa: E402
import delivery  # noqa: E402
import guidance  # noqa: E402
import skill_usage  # noqa: E402
import improve_gate  # noqa: E402

TARGET = "adam-agentskills"
REGISTRY_REPO = "Adam-S-Daniel/adam-agentskills"
EVALS_REPO = "Adam-S-Daniel/skills-evals"
BRANCH_PREFIX = "retire-skill/"
#: Every loop pull request's head in adam-agentskills: improvement, new
#: skill, removal. One open at a time across all three (ADR 0021,
#: decision 5; routine-improve-gate.yml's registry-pr job checks the same).
LOOP_PREFIXES = ("eval-improve/", "draft-skill/", BRANCH_PREFIX)
#: The fleet label and marker for a contribution an agent made on Adam's
#: behalf (_agent-guidance ADR 0023), as the improvement gate writes them.
AGENT_LABEL = "agent-authored"
AGENT_MARKER = improve_gate.AGENT_MARKER
AGENT_TRAILER = "Agent: claude-code"
REGISTRY_ADR = improve_gate.REGISTRY_ADR
#: The environment variable holding the adam-agentskills write token (the
#: skills-evals GitHub App's installation token, minted by the workflow).
REGISTRY_TOKEN_ENV = "REGISTRY_TOKEN"
PR_URL_RE = re.compile(rf"https://github\.com/{re.escape(REGISTRY_REPO)}/pull/(\d+)")
GUIDANCE_NO_CREDENTIAL = ("no write credential for _agent-guidance reached this run "
                         "(the GitHub App token was not minted)")
#: The cell classes a `retire` verdict may hold, and those with headroom,
#: of which it needs one (harness/gates.py, THE VERDICT).
RETIRE_CELL_CLASSES = ("no-benefit", "no-clear-effect", "cannot-discriminate",
                       *sorted(gates.PARKED_CLASSES))
HEADROOM_CLASSES = ("no-benefit", "no-clear-effect")
NO_CREDENTIAL = ("no write credential for adam-agentskills reached this run (the "
                 "GitHub App token was not minted)")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ISSUE_MARKER = "<!-- skills-evals:retire-skill:{skill} -->"
IMPACT_FILE = "docs/skill-impact.md"
#: Who a removal notice mentions, so GitHub notifies him (#557).
NOTICE_OWNER = "Adam-S-Daniel"
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


def default_gh(args: list, stdin: str | None = None, token: str | None = None) -> str:
    """Run `gh` and return its stdout; its output is never echoed on failure,
    since an API error body can carry data a public log must not. `token`,
    when given, replaces GH_TOKEN for this call only."""
    env = {**os.environ, "GH_TOKEN": token} if token else None
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True,
                          text=True, check=False, env=env)
    if proc.returncode != 0:
        raise RetireError(f"gh {args[0]} exited {proc.returncode}")
    return proc.stdout


def _auth_env(token: str) -> dict:
    """git's environment with `token` as an HTTP header for github.com, set
    through GIT_CONFIG_* so it never appears in an argv or .git/config."""
    header = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return {**os.environ, "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {header}",
            "GIT_TERMINAL_PROMPT": "0"}


def default_push(checkout: Path, branch: str, token: str | None = None) -> None:
    """Push HEAD to `branch`, then prove it landed: a refused commit can
    still leave `git push` reporting success, so the pushed ref is fetched
    back and HEAD must be its ancestor (the fleet's push rule)."""
    if not token:
        raise RetireError(f"no {REGISTRY_TOKEN_ENV} to push with")
    env = _auth_env(token)
    for args in (["push", "origin", f"HEAD:refs/heads/{branch}"],
                 ["fetch", "-q", "--no-tags", "origin",
                  f"+refs/heads/{branch}:refs/remotes/origin/{branch}"],
                 ["merge-base", "--is-ancestor", "HEAD", f"refs/remotes/origin/{branch}"]):
        proc = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True,
                              text=True, check=False, env=env)
        if proc.returncode != 0:
            raise RetireError(f"git {args[0]} exited {proc.returncode}"
                              + (": the pushed branch does not hold the removal commit"
                                 if args[0] == "merge-base" else ""))


def _git(checkout: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(checkout), *args],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RetireError(f"git {args[0]} exited {proc.returncode}")
    return proc.stdout


def check_event(env, events=("schedule",)) -> None:
    """Only the named events write: the schedule acts on a verdict, and
    withdrawal (`WITHDRAW_EVENTS`) also runs after every ingest."""
    if env.get("GITHUB_EVENT_NAME") not in events:
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
        if not isinstance(c, dict) or c.get("class") not in RETIRE_CELL_CLASSES:
            raise RetireError(f"{skill}: a retire verdict with a cell that is not "
                              f"{', '.join(RETIRE_CELL_CLASSES)}")
        fixture = c.get("fixture")
        if not (fixture is None or isinstance(fixture, str) and NAME_RE.fullmatch(fixture)) \
                or not isinstance(c.get("model"), str):
            raise RetireError(f"{skill}: a retire verdict with a malformed cell")
    if not any(c["class"] in HEADROOM_CLASSES for c in cells):
        raise RetireError(f"{skill}: a retire verdict with no cell with headroom")
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


def open_loop_prs(gh) -> list:
    """Open adam-agentskills pull requests whose head is any loop's."""
    text = gh(["api", "--paginate",
               f"repos/{REGISTRY_REPO}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text)
            if isinstance(p.get("head"), str) and p["head"].startswith(LOOP_PREFIXES)]


def closed_removal_prs(gh, skill: str) -> list:
    """Closed adam-agentskills pull requests from `retire-skill/<skill>`."""
    owner = REGISTRY_REPO.split("/")[0]
    text = gh(["api", "--paginate",
               f"repos/{REGISTRY_REPO}/pulls?state=closed&per_page=100"
               f"&head={owner}:{BRANCH_PREFIX}{skill}",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text) if p.get("head") == f"{BRANCH_PREFIX}{skill}"]


def runtime_refusal(checkout: Path, plugin: str, skill: str) -> str | None:
    """improve_gate.py's `auto_refusal`: why removing `skill` would wait on
    plugin-runtime-review, or None."""
    try:
        return improve_gate.auto_refusal(checkout, plugin, skill)
    except improve_gate.Rejected as exc:
        raise RetireError(str(exc)) from None


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
            "Judge upper |", "|---|---|---|---|---|---|"]
    for cell in gates["skills"][skill]["cells"]:
        arms = [cell.get(a) if isinstance(cell.get(a), dict) else {}
                for a in ("with", "without")]
        rows.append(f"| {cell.get('fixture') or '(flat)'} | {cell.get('model')} | "
                    f"{arms[0].get('runs', 'n/a')} | {arms[1].get('runs', 'n/a')} | "
                    f"{_figure(cell.get('objective'), 'retire_upper')} | "
                    f"{_figure(cell.get('judge'), 'retire_upper')} |")
    return "\n".join(rows)


def _date(as_of: str) -> str:
    return f"{as_of[0:4]}-{as_of[4:6]}-{as_of[6:8]}"


def _runs(cells) -> int:
    return sum(c[arm]["runs"] for c in cells for arm in ("with", "without")
               if isinstance(c.get(arm), dict) and type(c[arm].get("runs")) is int)


def impact_entry(gates: dict, skill: str, plugin: str, run_url: str | None,
                 versions: tuple, date: str | None = None) -> str:
    """The registry's entry format (docs/skill-impact.md, "Entry format"):
    the date the removal is opened, one line each, links in full since the
    file lives in another repository."""
    cells = gates["skills"][skill]["cells"]
    fixtures = sorted({c.get("fixture") or "(flat)" for c in cells})
    paths = [f"evals/{skill}" if f == "(flat)" else f"evals/{skill}/{f}" for f in fixtures]
    where = f"workflow run {run_url}" if run_url else "its scheduled workflow"
    return (f"## {date or _date(gates['as_of'])} — {plugin}/{skill} — remove\n\n"
            f"- Motivation: the retirement verdict is `retire` "
            f"([skills-evals#70](https://github.com/{EVALS_REPO}/issues/70)): every cell "
            f"({len(fixtures)} fixture(s) x {len(gates['roster_models'])} roster model(s)) "
            f"shows no benefit at the retire confidence level.\n"
            f"- Change: `plugins/{plugin}/skills/{skill}/` removed, the skill dropped from "
            f"`{LAYOUT_FILE}` and the README table, bundle `{plugin}` {versions[0]} -> "
            f"{versions[1]} (a removal is a breaking change), by skills-evals' "
            f"`scripts/retire_skill.py` ({where}).\n"
            f"- Eval: n={_runs(cells)} pooled arm runs (with vs without the skill) as of "
            f"{gates['as_of']}, fixtures {', '.join(paths)}, "
            f"policy evals/gate-policy.yml; per-cell bounds in the pull request.\n"
            f"- Outcome: pending merge; auto-merges once required checks pass, with no "
            f"human review ([ADR 0021]({REGISTRY_ADR})).\n")


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
    """The next MAJOR version: a removal breaks every consumer that calls the
    skill. check_plugin_versions.py asks only that it rise; the registry
    bumped major for its last skill removal (sync-skills, 1.1.0 -> 2.0.0)."""
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if not match:
        raise RetireError("a plugin version is not MAJOR.MINOR.PATCH")
    return f"{int(match.group(1)) + 1}.0.0"


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


def usage_line(usage: dict | None, skill: str, as_of: str) -> str:
    """One line on how often `skill` was invoked lately, for the human who
    decides; `unknown` when there is no fresh usage census at `as_of`."""
    now = datetime.strptime(as_of, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    count = skill_usage.weight(usage, skill, now)
    if count is None:
        return "Recent use: unknown (no fresh usage census)."
    return (f"Recent use: {count} local invocation(s) in the four weeks to {as_of} "
            "(usage/weekly-local.json).")


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
    dangling_citations(checkout, location["path"], skill)


TEST_NAME_RE = re.compile(r"\btest_[a-z0-9_]+")


def _defined_tests(checkout: Path, rels) -> set:
    """Function names (parsed, never grepped) and module stems of `rels`."""
    names = set()
    for rel in rels:
        if not rel.endswith(".py"):
            continue
        names.add(Path(rel).stem)
        try:
            tree = ast.parse((checkout / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            raise RetireError(f"cannot parse {rel}") from None
        names |= {node.name for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return {n for n in names if n.startswith("test_")}


def dangling_citations(checkout: Path, path: str, skill: str) -> None:
    """RetireError when a tracked source outside the skill cites, by name, a
    test that only the skill defines. adam-agentskills'
    test_every_test_this_repo_cites_by_name_exists scans every tracked
    non-test `*.py` and `*.sh` for `test_...` tokens and fails on one no
    tracked module defines, so removing the skill would turn that citation
    into a failing required check. Rewording someone's comment is not a
    removal's job; a human does that."""
    inside = _git(checkout, "ls-files", "-z", "--", path).split("\0")
    gone = _defined_tests(checkout, [r for r in inside if r])
    if not gone:
        return
    outside = [r for r in _git(checkout, "ls-files", "-z", "--", "*.py", "*.sh")
               .split("\0") if r and not (r == path or r.startswith(f"{path}/"))]
    gone -= _defined_tests(checkout, outside)
    for rel in outside:
        if Path(rel).name.startswith("test_"):
            continue
        try:
            text = (checkout / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise RetireError(f"cannot read {rel}") from None
        cited = sorted(set(TEST_NAME_RE.findall(text)) & gone)
        if cited:
            raise RetireError(f"{rel} cites {cited[0]}, a test only {skill} defines; "
                              "removing the skill leaves that citation dangling, which "
                              f"{TARGET}' test_every_test_this_repo_cites_by_name_exists "
                              "fails on")


def waived_paths(checkout: Path, path: str, skill: str) -> None:
    """RetireError when `scripts/skills_waivers.yml` waives a finding inside
    the skill: that waiver matches nothing once the skill is gone, and
    check_skills.py reports a `stale-waiver` and exits 1, so the pull request
    could never merge. Removing the waiver with the skill means editing a
    commented YAML file, which this does not do; a human does that. The
    file is parsed, never grepped — its comments name skills
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
    # Each target is spelled literally at its call so the suite's spawn audit
    # (run_tests.py, S-B-a-2) can prove it is not the test runner.
    if script == README_GENERATOR:
        proc = subprocess.run([sys.executable, "scripts/generate_readme_table.py", *args],
                              cwd=str(checkout), env=env, capture_output=True, text=True,
                              check=False)
    elif script == LOCK_GENERATOR:
        proc = subprocess.run([sys.executable, "scripts/generate_skills_lock.py", *args],
                              cwd=str(checkout), env=env, capture_output=True, text=True,
                              check=False)
    else:
        raise RetireError(f"{script} is not a registry script this tool runs")
    if proc.returncode != 0:
        raise RetireError(" ".join([script, *args, "exited", str(proc.returncode)]))


def _issue_body(gates, skill, location, problem, run_url, usage=None,
                mode_reason=None) -> str:
    where = (f"`{location['path']}` in {REGISTRY_REPO}" if location
             else f"not located: {problem}")
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    why = (f"`evals/gate-policy.yml` sets `retirement_mode: auto`, but {mode_reason}, "
           "so no removal pull request is opened and a human removes it"
           if mode_reason else
           "`evals/gate-policy.yml` sets `retirement_mode: proposal`, so a human "
           "removes it")
    return (f"{ISSUE_MARKER.format(skill=skill)}\n"
            f"The retirement verdict for `{skill}` is **retire** as of "
            f"{gates['as_of']}: {gates['skills'][skill].get('reason')}.\n\n"
            f"{usage_line(usage, skill, gates['as_of'])}\n\n"
            f"{why}. Copy: {where}.\n\n{evidence(gates, skill)}\n{run}\n"
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
            f"This pull request auto-merges (merge commit) once required checks pass, "
            f"with no human review, by Adam's 2026-10-25 decision "
            f"([skills-evals ADR 0014]({ADR}); [ADR 0021]({REGISTRY_ADR})). To decline "
            f"the removal, close it: a closed `{BRANCH_PREFIX}{skill}` pull request means "
            f"the skill is decided, and none is opened again.\n"
            f"{run}\nOpened by skills-evals' scripts/retire_skill.py on its scheduled "
            f"workflow.\n\n{AGENT_MARKER}\n")


#: Headroom cells, every one `no-benefit`, an automatic removal needs: the
#: gates' own constant, one source (round 2's m1).
AUTO_MIN_HEADROOM_CELLS = gates.AUTO_MIN_HEADROOM_CELLS


def cells_allow_auto(verdict: dict) -> bool:
    """Whether a `retire` verdict's cells allow an automatic removal, derived
    here rather than trusted from its `removal` field (the review's m3): at
    least AUTO_MIN_HEADROOM_CELLS headroom cells, every one `no-benefit`,
    and no parked cell (`gates.PARKED_CLASSES`) beside them."""
    cells = [c for c in verdict.get("cells") or [] if isinstance(c, dict)]
    headroom = [c for c in cells if c.get("class") in HEADROOM_CLASSES]
    return (len(headroom) >= AUTO_MIN_HEADROOM_CELLS
            and all(c["class"] == "no-benefit" for c in headroom)
            and not any(c.get("class") in gates.PARKED_CLASSES for c in cells))


def proposal_only(verdict: dict) -> str | None:
    """Why a `retire` verdict can only be a proposal, or None when it may be
    removed automatically: its `removal` must be `auto` AND its cells must
    allow it (`cells_allow_auto`); on any disagreement it is a proposal."""
    if verdict.get("removal") == "auto":
        if cells_allow_auto(verdict):
            return None
        return ("the verdict says auto, but its cells allow only a proposal: fewer "
                f"than {AUTO_MIN_HEADROOM_CELLS} headroom cells, one that is not "
                "no-benefit, or a parked cell (at the ceiling, or paused by the eval "
                "scope pass)")
    why = verdict.get("removal_reason")
    return ("the verdict allows only a proposal"
            + (f" ({why})" if isinstance(why, str) and why else ""))


def guidance_proposal_only(verdict: dict) -> str | None:
    """`proposal_only` for a guidance section's `retire` verdict, with its
    section-alone pair re-checked here too rather than trusted from its
    `removal` field: an unfinished alone pair (harness/gates.py
    `alone_unfinished`: no alone cell, or one that has not decided) could
    still turn the verdict into shorten-or-merge, so it allows only a
    proposal."""
    why = proposal_only(verdict)
    if why is not None:
        return why
    alone = verdict.get("alone")
    if alone is not None and not isinstance(alone, dict):
        return "the verdict's alone block is malformed"
    if gates.alone_unfinished((alone or {}).get("cells")):
        return gates.ALONE_UNFINISHED_REASON
    return None


def _lowered(mode_reason: str, allowed) -> str:
    """`proposal`, the mode auto falls back to; RetireError when the caller
    has not allowed it either."""
    if "proposal" not in allowed:
        raise RetireError(f"retirement_mode auto falls back to proposal ({mode_reason}), "
                          f"which this caller has not wired (allowed: {', '.join(allowed)})")
    return "proposal"


def plan(gates: dict, registries: dict, gh, run_url: str | None = None,
         allowed=("proposal",), usage: dict | None = None, fallback: bool = False,
         date: str | None = None) -> dict:
    """What to do, read-only. RetireError for a refusal."""
    skill = retiring(gates)
    mode = mode_of(gates)
    if skill is None:
        return {"action": "none", "mode": mode, "reason": "no skill has a retire verdict"}
    mode_reason = None
    if mode == "auto" and proposal_only(gates["skills"][skill]):
        mode_reason = proposal_only(gates["skills"][skill])
        mode = _lowered(mode_reason, allowed)
    if mode == "auto" and "auto" not in allowed and fallback:
        mode_reason = NO_CREDENTIAL
        mode = _lowered(mode_reason, allowed)
    if mode not in allowed:
        raise RetireError(f"retirement_mode is {mode}, which this caller has not wired "
                          f"(allowed: {', '.join(allowed)})")
    if mode == "auto":
        location = locate(registries, skill)
        checkout = Path(registries[TARGET]["path"])
        mode_reason = runtime_refusal(checkout, location["plugin"], skill)
        if mode_reason:
            mode = _lowered(mode_reason, allowed)
    if mode == "proposal":
        try:
            location, problem = locate(registries, skill), None
        except RetireError as exc:
            location, problem = None, str(exc)
        issues = existing_issues(gh, skill)
        lowered = {"mode_reason": mode_reason} if mode_reason else {}
        if not issues["open"] and issues["closed"]:
            return {"action": "none", "mode": mode, "skill": skill, **lowered,
                    "issue": issues["closed"][0],
                    "reason": f"{skill} is already decided: issue "
                              f"#{issues['closed'][0]} is closed, so none is filed again"}
        number = issues["open"][0] if issues["open"] else None
        return {"action": "update-issue" if number else "create-issue", "mode": mode,
                "skill": skill, "issue": number, **lowered,
                "title": f"Retire skill {skill}: no benefit on every roster model (#70)",
                "body": _issue_body(gates, skill, location, problem, run_url, usage, mode_reason)}
    prs = open_loop_prs(gh)
    if prs:
        return {"action": "none", "mode": mode, "skill": skill,
                "reason": "a loop pull request is already open in "
                          f"{REGISTRY_REPO}, so this removal waits for it: "
                          + ", ".join(str(p.get("url")) for p in prs)}
    closed = closed_removal_prs(gh, skill)
    if closed:
        return {"action": "none", "mode": mode, "skill": skill,
                "reason": f"{skill} is already decided: removal pull request "
                          f"{closed[0].get('url')} is closed, so none is opened again"}
    versions = manifest_versions(checkout, location["plugin"])
    check_registry(checkout, location, skill)
    repin = lock_relevant(checkout, location["plugin"])
    entry = impact_entry(gates, skill, location["plugin"], run_url,
                         next(iter(versions.values())), date)
    return {"action": "removal", "mode": mode, "skill": skill, **location,
            "branch": f"{BRANCH_PREFIX}{skill}", "versions": versions,
            "impact_entry": entry, "repin": repin,
            "notice": skill_notice(gates, skill, location, run_url),
            "title": f"Remove {location['plugin']}/{skill}: no benefit (skills-evals#70)",
            "body": _pr_body(gates, skill, location, versions, run_url, repin)}


#: The issue that tells Adam a skill is being removed and how to reverse it
#: (#557; Adam, 2026-11-02, as for guidance sections). `{removal_pr}` is
#: filled once the pull request exists.
SKILL_NOTICE_MARKER = "<!-- skills-evals:removed-skill:{skill} -->"


def skill_notice(gates: dict, skill: str, location: dict, run_url: str | None) -> dict:
    """The removal notice (#557): an issue here that mentions the owner,
    links the removal pull request and says how to reverse it."""
    verdict = gates["skills"][skill]
    marker = SKILL_NOTICE_MARKER.format(skill=skill)
    return {"marker": marker,
            "title": f"Skill {location['plugin']}/{skill} is being removed automatically (#557)",
            "body": (f"{marker}\n@{NOTICE_OWNER}: the skill `{location['plugin']}/{skill}` "
                     f"is being removed from adam-agentskills: its verdict is **retire** as of "
                     f"{gates['as_of']} ({verdict.get('reason')}). The rule is 90% confidence "
                     "that it does not improve results by 0.15 or more, on every cell with "
                     "room to show it (`evals/gate-policy.yml` `skills:`).\n\n"
                     "Removal pull request: {removal_pr} (auto-merges once its checks "
                     "pass).\n\n**To reverse it:** before it merges, close that pull "
                     "request. After it merges, open it and press **Revert**: GitHub opens "
                     "a pull request that restores the skill, its layout and README rows "
                     "and the bundle version; merge that. The removal is recorded as a "
                     f"`remove` entry in adam-agentskills' `{IMPACT_FILE}` and on the "
                     "explorer's list of removed skills.\n\n"
                     + evidence(gates, skill)
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py on the scheduled workflow."
                       "\n\n" + AGENT_MARKER + "\n")}


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
            "the retire confidence level.")
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
    """A commit by the bot identity, with the fleet's agent trailer (as the
    improvement gate's commits carry it)."""
    _git(checkout, "-c", f"user.name={COMMIT_NAME}", "-c", f"user.email={COMMIT_EMAIL}",
         "commit", "-q", "-m", f"{message}\n\n{AGENT_TRAILER}")


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
                ["git", "merge-base", "--is-ancestor", "HEAD",
                 f"refs/remotes/origin/{action['branch']}"],
                ["gh", "pr", "create", "-R", REGISTRY_REPO, "--base", "main",
                 "--head", action["branch"], "--title", action["title"], "--body-file", "-"],
                ["gh", "api", "-X", "POST",
                 f"repos/{REGISTRY_REPO}/issues/<new pull request number>/labels",
                 "-f", f"labels[]={AGENT_LABEL}"],
                ["gh", "pr", "merge", "<new pull request url>", "-R", REGISTRY_REPO,
                 "--auto", "--merge", "--match-head-commit", "<removal head sha>"],
                ["gh", "pr", "view", "<new pull request url>", "-R", REGISTRY_REPO,
                 "--json", "autoMergeRequest"],
                ["gh", "issue", "create", "-R", EVALS_REPO, "--title",
                 action["notice"]["title"], "--label", AGENT_LABEL, "--body-file", "-"]]
    return []


def execute(action: dict, registries: dict, gh, push, env, registry_gh=None) -> str:
    """Make the plan's writes: skills-evals issues through `gh`,
    adam-agentskills writes through `registry_gh` (default `gh`)."""
    registry_gh = registry_gh or gh
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
    head = _git(checkout, "rev-parse", "HEAD").strip()
    push(checkout, action["branch"])
    url = registry_gh(["pr", "create", "-R", REGISTRY_REPO, "--base", "main",
                       "--head", action["branch"], "--title", action["title"],
                       "--body-file", "-"], action["body"]).strip()
    match = PR_URL_RE.fullmatch(url)
    if not match:
        raise RetireError("creating the pull request printed no pull request URL")
    # Labeled before auto-merge: a pull request that could not be marked as
    # the loop's stays open for a person instead of merging.
    registry_gh(["api", "-X", "POST", f"repos/{REGISTRY_REPO}/issues/{match.group(1)}/labels",
                 "-f", f"labels[]={AGENT_LABEL}"])
    registry_gh(["pr", "merge", url, "-R", REGISTRY_REPO, "--auto", "--merge",
                 "--match-head-commit", head])
    method = registry_gh(["pr", "view", url, "-R", REGISTRY_REPO, "--json",
                          "autoMergeRequest", "--jq",
                          '.autoMergeRequest.mergeMethod // ""']).strip()
    if method != "MERGE":
        raise RetireError(f"auto-merge (merge commit) is not enabled on {url}")
    # The notice goes out once the removal is armed, through the job's own
    # token (skills-evals issues), never the registry one (#557).
    notice = action["notice"]
    gh(["issue", "create", "-R", EVALS_REPO, "--title", notice["title"],
        "--label", AGENT_LABEL, "--body-file", "-"],
       notice["body"].replace("{removal_pr}", url))
    return f"opened {url} with auto-merge, and filed the removal notice"


# ---------------------------------------------------------------------------
# Guidance sections (skills-evals#124): `--target guidance`. Kept apart from
# the skill path above; the two share only the gh/push plumbing, the issue
# lookup's shape and `insert_entry`'s neighbor `_date`.

GUIDANCE_REPO = "Adam-S-Daniel/_agent-guidance"
GUIDANCE_BRANCH_PREFIX = "retire-guidance/"
GUIDANCE_ISSUE_MARKER = "<!-- skills-evals:retire-guidance:{section} -->"
SHORTEN_ISSUE_MARKER = "<!-- skills-evals:shorten-guidance:{section} -->"
#: The issue that tells Adam a section is being removed and how to reverse
#: it (#557; Adam, 2026-11-02: "notify and track removals so I can always
#: decide to reverse something"). `{removal_pr}` is filled once the pull
#: request exists.
GUIDANCE_NOTICE_MARKER = "<!-- skills-evals:removed-guidance:{section} -->"
GUIDANCE_NOTICE_OWNER = NOTICE_OWNER
GUIDANCE_MANIFEST = "agents-md/eval-coverage.yml"
GUIDANCE_IMPACT = "docs/guidance-impact.md"
GUIDANCE_AGENTS = "AGENTS.md"
#: _agent-guidance's own fleet-memory payload: a hand-made byte copy of
#: base.md that nothing syncs (its scripts/check-fleet-guidance-mirror.js).
GUIDANCE_PAYLOAD = ".claude/hooks/fleet-guidance.md"
#: The heading LINE AGENTS.md is split on, never a substring of a line: the
#: managed block's own first line quotes it (_agent-guidance AGENTS.md).
REPO_SPECIFIC_LINE = "## Repo-specific additions"
DATED_HEADING_RE = re.compile(r"^\d{4}-\d{2}-\d{2} — ")


def guidance_mode(gates: dict) -> str:
    return "auto" if gates.get("guidance_retirement_mode") == "auto" else "proposal"


def guidance_block(gates: dict) -> dict:
    block = gates.get("guidance")
    if not isinstance(block, dict):
        raise RetireError("the gates file has no guidance block (a policy without "
                          "guidance:, or a compute_gates.py from before #124)")
    return block


def guidance_retiring(gates: dict) -> str | None:
    """The one section whose verdict is `retire`, re-checked exactly as a
    skill's is (`retiring`, over the guidance block)."""
    return retiring({**gates, "skills": guidance_block(gates)})


def guidance_shortening(gates: dict) -> list:
    """Sections whose verdict is `shorten-or-merge`, by name."""
    names = sorted(n for n, v in guidance_block(gates).items()
                   if isinstance(v, dict) and v.get("verdict") == "shorten-or-merge")
    for name in names:
        if not SKILL_RE.fullmatch(name):
            raise RetireError("a shorten-or-merge section's name is not a section id")
    return names


def guidance_open_prs(gh) -> list:
    text = gh(["api", "--paginate",
               f"repos/{GUIDANCE_REPO}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text)
            if isinstance(p.get("head"), str) and p["head"].startswith(GUIDANCE_BRANCH_PREFIX)]


def guidance_closed_removal_prs(gh, section: str) -> list:
    """Closed _agent-guidance pull requests from `retire-guidance/<section>`:
    closed by a person or withdrawn (`--withdraw-stale`), the section is
    decided, as `closed_removal_prs` decides a skill. The kept branch would
    also refuse a fresh removal's push."""
    owner = GUIDANCE_REPO.split("/")[0]
    text = gh(["api", "--paginate",
               f"repos/{GUIDANCE_REPO}/pulls?state=closed&per_page=100"
               f"&head={owner}:{GUIDANCE_BRANCH_PREFIX}{section}",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text)
            if p.get("head") == f"{GUIDANCE_BRANCH_PREFIX}{section}"]


def guidance_issues(gh, marker: str) -> dict:
    """As `existing_issues`, for any marker."""
    text = gh(["api", "--paginate",
               f"repos/{EVALS_REPO}/issues?state=all&per_page=100",
               "--jq", ".[] | select(.pull_request == null) | "
                       "{number: .number, body: (.body // \"\"), "
                       "author: .user.login, state: .state}"])
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


def guidance_evidence(verdict: dict) -> str:
    """The in-situ cells, then the alone cells for contrast."""
    tables = []
    for title, cells in (("Whole guidance with vs without the section (decides)",
                          verdict.get("cells")),
                         ("The section alone vs no guidance (contrast)",
                          (verdict.get("alone") or {}).get("cells"))):
        rows = [f"{title}:", "", "| Fixture | Model | Class | Runs with | Runs without | "
                "Objective upper | Judge upper |", "|---|---|---|---|---|---|---|"]
        for cell in cells if isinstance(cells, list) else []:
            if not isinstance(cell, dict):
                continue
            arms = [cell.get(a) if isinstance(cell.get(a), dict) else {}
                    for a in ("with", "without")]
            fixture, model, cls = (cell.get(k) for k in ("fixture", "model", "class"))
            rows.append(f"| {fixture if isinstance(fixture, str) and NAME_RE.fullmatch(fixture) else 'n/a'} "
                        f"| {model if isinstance(model, str) and NAME_RE.fullmatch(model) else 'n/a'} "
                        f"| {cls if isinstance(cls, str) and NAME_RE.fullmatch(cls) else 'n/a'} "
                        f"| {arms[0].get('runs', 'n/a')} | {arms[1].get('runs', 'n/a')} | "
                        f"{_figure(cell.get('objective'), 'retire_upper')} | "
                        f"{_figure(cell.get('judge'), 'retire_upper')} |")
        tables.append("\n".join(rows))
    return "\n\n".join(tables)


def guidance_row(checkout: Path, section: str) -> dict:
    """The section's manifest row in `checkout`, every path it touches
    checked to be no symlink and inside the checkout."""
    try:
        rows = guidance.load_manifest(checkout)
        row = guidance.find_row(rows, section, checkout)
    except guidance.GuidanceError:
        raise RetireError(f"{section}: no readable manifest row in the "
                          "_agent-guidance checkout") from None
    rel = row["file"]
    if rel != "agents-md/base.md" and not re.fullmatch(r"agents-md/sections/[a-z0-9-]+\.md", rel):
        raise RetireError(f"{section}: its file {rel!r} is neither base.md nor a sections file")
    contained(checkout, ["agents-md", "agents-md/sections", rel, GUIDANCE_MANIFEST, "docs",
                         GUIDANCE_IMPACT, GUIDANCE_AGENTS, "scripts", ".claude",
                         ".claude/hooks", GUIDANCE_PAYLOAD])
    return row


def _read_exact(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write_exact(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def guidance_without_section(text: str, heading: str) -> str | None:
    """`text` with the `##` extent named `heading` removed (harness/guidance.py
    `h2_extents`, the arithmetic check-guidance-coverage.js uses), or None
    when it was the file's only `##`, so the file goes."""
    spans = guidance.h2_extents(text)
    hits = [s for s in spans if s["heading"] == heading]
    if len(hits) != 1:
        raise RetireError(f"heading {heading!r} is not in its file exactly once")
    if len(spans) == 1:
        return None
    return text[:hits[0]["start"]] + text[hits[0]["end"]:]


def manifest_without_row(text: str, section: str) -> str:
    """The manifest with `section`'s row deleted, comments and layout kept:
    the row's lines are found on the composed YAML tree (its sequence item's
    start, to the next item's start or the end), never by a line scan."""
    try:
        doc = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        raise RetireError(f"{GUIDANCE_MANIFEST} is not valid YAML") from None
    if not isinstance(doc, yaml.SequenceNode):
        raise RetireError(f"{GUIDANCE_MANIFEST} is not a YAML list")
    items = doc.value
    hits = [i for i, node in enumerate(items) if isinstance(node, yaml.MappingNode)
            and any(k.value == "id" and isinstance(v, yaml.ScalarNode) and v.value == section
                    for k, v in node.value)]
    if len(hits) != 1:
        raise RetireError(f"{section}: not exactly one manifest row")
    lines = text.splitlines(keepends=True)
    start = items[hits[0]].start_mark.line
    end = items[hits[0] + 1].start_mark.line if hits[0] + 1 < len(items) else len(lines)
    return "".join(lines[:start] + lines[end:])


def guidance_impact_entry(gates: dict, section: str, run_url: str | None) -> str:
    """A typed `remove` entry whose Eval: line is a real result for
    check-guidance-touch.js: the fixtures, the pooled run count as `n=` and
    the policy."""
    verdict = guidance_block(gates)[section]
    cells = verdict["cells"]
    fixtures = sorted({c.get("fixture") or "(flat)" for c in cells})
    runs = _runs(cells)
    where = f"workflow run {run_url}" if run_url else "the scheduled workflow"
    return (f"## {_date(gates['as_of'])} — {section} — remove\n"
            f"- Motivation: skills-evals#124's retirement verdict is `retire`: the whole "
            f"guidance with and without the section shows no benefit in every cell "
            f"({len(fixtures)} fixture(s) x {len(gates['roster_models'])} roster model(s)) "
            f"at the retire confidence level.\n"
            f"- Change: removed the section and its eval-coverage.yml row, by "
            f"skills-evals' scheduled retirement ({where}).\n"
            f"- Eval: n={runs} pooled arm runs (full vs full-minus-section) as of "
            f"{gates['as_of']}, fixtures "
            f"{', '.join(f'evals/guidance/{section}/{f}' for f in fixtures)}, policy "
            f"evals/gate-policy.yml guidance:.\n"
            f"- Outcome: auto-merges once required checks pass, with no human review "
            f"(Adam, 2026-10-10 and 2026-10-25).\n")


def guidance_insert_entry(text: str, entry: str) -> str:
    """`entry` newest first: before the first dated `##` entry (after the
    file's header and its `## Entry format`), or at the end when none."""
    for span in guidance.h2_extents(text):
        if DATED_HEADING_RE.match(span["heading"]):
            return text[:span["start"]] + entry + "\n" + text[span["start"]:]
    return text.rstrip("\n") + "\n\n" + entry


def regenerate_agents_md(checkout: Path, managed: str) -> None:
    """AGENTS.md rebuilt as _agent-guidance's own AGENTS.md says: `managed`
    (build-agents-md.sh's stdout) with its trailing newlines stripped, a
    newline, then the file from its `## Repo-specific additions` heading
    LINE on, trailing newlines stripped, and one closing newline."""
    path = checkout / GUIDANCE_AGENTS
    lines = _read_exact(path).split("\n")
    marks = [i for i, line in enumerate(lines) if line.rstrip("\r") == REPO_SPECIFIC_LINE]
    if len(marks) != 1:
        raise RetireError(f"{GUIDANCE_AGENTS} has {len(marks)} `{REPO_SPECIFIC_LINE}` "
                          "heading lines, not exactly one")
    tail = "\n".join(lines[marks[0]:]).rstrip("\n")
    _write_exact(path, managed.rstrip("\n") + "\n" + tail + "\n")


def _run(checkout: Path, *args: str) -> str:
    proc = subprocess.run(list(args), cwd=checkout, capture_output=True, text=True,
                          check=False)
    if proc.returncode != 0:
        raise RetireError(f"{' '.join(args[:2])} exited {proc.returncode}")
    return proc.stdout


def guidance_issue_action(gates, section, kind, run_url, mode_reason=None) -> dict:
    """Create or update the section's issue (`kind` retire or shorten), or
    nothing when a closed one already decided it."""
    verdict = guidance_block(gates)[section]
    marker = (GUIDANCE_ISSUE_MARKER if kind == "retire" else SHORTEN_ISSUE_MARKER).format(
        section=section)
    return {"marker": marker, "section": section, "kind": kind,
            "title": (f"Retire guidance section {section}: no marginal benefit on every "
                      "roster model (#124)" if kind == "retire" else
                      f"Shorten or merge guidance section {section}: it helps only alone "
                      "(#124)"),
            "body": (f"{marker}\nThe guidance verdict for `{section}` is "
                     f"**{verdict.get('verdict')}** as of {gates['as_of']}: "
                     f"{verdict.get('reason')}.\n\n"
                     + ((f"`evals/gate-policy.yml` sets `guidance: retirement_mode: auto`, "
                         f"but {mode_reason}, so no removal pull request is opened and a "
                         "human removes it from _agent-guidance.\n\n" if mode_reason else
                         "`evals/gate-policy.yml` sets `guidance: retirement_mode: proposal`, "
                         "so a human removes it from _agent-guidance.\n\n")
                        if kind == "retire" else "Nothing is removed: the section teaches the behavior, and the "
                        "rest of the guidance already covers it. Shorten it or merge it into "
                        "the section that covers it.\n\n")
                     + guidance_evidence(verdict)
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py --target guidance on the "
                       "scheduled workflow (#124).\n")}


def guidance_plan(gates: dict, checkout: Path | None, gh, run_url: str | None = None,
                  allowed=("proposal",), fallback: bool = False) -> dict:
    """What to do for guidance, read-only. RetireError for a refusal."""
    mode = guidance_mode(gates)
    mode_reason = None
    section = guidance_retiring(gates)
    if section is None:
        shortening = guidance_shortening(gates)
        if not shortening:
            return {"action": "none", "mode": mode,
                    "reason": "no guidance section has a retire or shorten-or-merge verdict"}
        section, kind = shortening[0], "shorten"
    else:
        kind = "retire"
        if mode == "auto" and guidance_proposal_only(guidance_block(gates)[section]):
            mode_reason = guidance_proposal_only(guidance_block(gates)[section])
            mode = _lowered(mode_reason, allowed)
        if mode == "auto" and "auto" not in allowed and fallback:
            mode_reason = GUIDANCE_NO_CREDENTIAL
            mode = _lowered(mode_reason, allowed)
        if mode not in allowed:
            raise RetireError(f"guidance_retirement_mode is {mode}, which this caller has "
                              f"not wired (allowed: {', '.join(allowed)})")
    if kind == "shorten" or mode == "proposal":
        issue = guidance_issue_action(gates, section, kind, run_url, mode_reason)
        lowered = {"mode_reason": mode_reason} if mode_reason else {}
        found = guidance_issues(gh, issue["marker"])
        if not found["open"] and found["closed"]:
            return {"action": "none", "mode": mode, "section": section, **lowered,
                    "issue": found["closed"][0],
                    "reason": f"{section} is already decided: issue "
                              f"#{found['closed'][0]} is closed, so none is filed again"}
        number = found["open"][0] if found["open"] else None
        return {"action": "update-issue" if number else "create-issue", "mode": mode,
                "section": section, "issue": number, **lowered, "title": issue["title"],
                "body": issue["body"]}
    prs = guidance_open_prs(gh)
    if prs:
        raise RetireError("a guidance removal pull request is already open: "
                          + ", ".join(str(p.get("url")) for p in prs))
    closed = guidance_closed_removal_prs(gh, section)
    if closed:
        return {"action": "none", "mode": mode, "section": section,
                "reason": f"{section} is already decided: removal pull request "
                          f"{closed[0].get('url')} is closed, so none is opened again"}
    if checkout is None:
        raise RetireError("no _agent-guidance checkout was given (--guidance PATH)")
    row = guidance_row(checkout, section)
    verdict = guidance_block(gates)[section]
    return {"action": "guidance-removal", "mode": mode, "section": section,
            "notice": guidance_notice(gates, section, row, run_url),
            "file": row["file"], "heading": row["heading"],
            "branch": f"{GUIDANCE_BRANCH_PREFIX}{section}",
            "impact_entry": guidance_impact_entry(gates, section, run_url),
            "title": f"Remove guidance section {section}: no marginal benefit "
                     "(skills-evals#124)",
            "body": (f"Removes the `## {row['heading']}` section of `{row['file']}` "
                     f"and its `{GUIDANCE_MANIFEST}` row: its verdict in "
                     f"[skills-evals#124](https://github.com/{EVALS_REPO}/issues/124) is "
                     f"**retire** as of {gates['as_of']} ({verdict.get('reason')}).\n\n"
                     f"{guidance_evidence(verdict)}\n\nAdds a `{GUIDANCE_IMPACT}` `remove` "
                     f"entry and regenerates `{GUIDANCE_AGENTS}`.\n\nThis pull request "
                     "auto-merges once required checks pass, with no human review "
                     "(Adam, 2026-10-10 and 2026-10-25)."
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nOpened by skills-evals' scripts/retire_skill.py --target "
                       "guidance on its scheduled workflow.\n\n" + AGENT_MARKER + "\n")}


def guidance_notice(gates: dict, section: str, row: dict, run_url: str | None) -> dict:
    """The removal notice (#557): an issue in skills-evals that mentions the
    owner, links the removal pull request (`{removal_pr}`) and says how to
    reverse it in one click."""
    verdict = guidance_block(gates)[section]
    marker = GUIDANCE_NOTICE_MARKER.format(section=section)
    return {"marker": marker,
            "title": f"Guidance section {section} is being removed automatically (#557)",
            "body": (f"{marker}\n@{GUIDANCE_NOTICE_OWNER}: the guidance section `{section}` "
                     f"(`## {row['heading']}` in `{row['file']}`) is being removed: its "
                     f"verdict is **retire** as of {gates['as_of']} ({verdict.get('reason')}). "
                     "The rule is 90% confidence that it does not improve results by 0.15 "
                     "or more beside the current rest of the guidance, on every cell with "
                     "room to show it (`evals/gate-policy.yml` `guidance:`).\n\n"
                     "Removal pull request: {removal_pr} (auto-merges once its checks "
                     "pass).\n\n**To reverse it:** before it merges, close that pull "
                     "request. After it merges, open it and press **Revert**: GitHub opens "
                     "a pull request that restores the section, its coverage row and the "
                     "regenerated files; merge that. The removal is recorded as a `remove` "
                     f"entry in `{GUIDANCE_IMPACT}` and on the explorer's list of removed "
                     "sections.\n\n"
                     + guidance_evidence(verdict)
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py --target guidance on the "
                       "scheduled workflow.\n\n" + AGENT_MARKER + "\n")}


def guidance_prepare_branch(checkout: Path, action: dict) -> None:
    """The removal commit on a new branch of `checkout`, which must be
    clean: the section, its row, the bytes, the impact entry, AGENTS.md."""
    if _git(checkout, "status", "--porcelain"):
        raise RetireError("the _agent-guidance checkout has uncommitted changes")
    row = guidance_row(checkout, action["section"])
    if row["file"] != action["file"] or row["heading"] != action["heading"]:
        raise RetireError("the manifest row changed under the plan")
    _git(checkout, "checkout", "-q", "-b", action["branch"])
    source = checkout / row["file"]
    remaining = guidance_without_section(_read_exact(source), row["heading"])
    if remaining is None:
        _git(checkout, "rm", "-q", "--", row["file"])
    else:
        _write_exact(source, remaining)
        if row["file"] == "agents-md/base.md":
            (checkout / GUIDANCE_PAYLOAD).write_bytes(source.read_bytes())
    manifest = checkout / GUIDANCE_MANIFEST
    _write_exact(manifest, manifest_without_row(_read_exact(manifest), action["section"]))
    _run(checkout, "node", "scripts/check-guidance-coverage.js", "--write-bytes")
    impact = checkout / GUIDANCE_IMPACT
    _write_exact(impact, guidance_insert_entry(_read_exact(impact), action["impact_entry"]))
    regenerate_agents_md(checkout, _run(checkout, "bash", "scripts/build-agents-md.sh"))
    _git(checkout, "add", "-A", "--", "agents-md", GUIDANCE_IMPACT, GUIDANCE_AGENTS,
         GUIDANCE_PAYLOAD)
    _git(checkout, "-c", f"user.name={COMMIT_NAME}", "-c", f"user.email={COMMIT_EMAIL}",
         "commit", "-q", "-m",
         f"Remove guidance section {action['section']}: no marginal benefit\n\n"
         "skills-evals#124's scheduled retirement found no benefit of the whole "
         "guidance with the section over it without, in every cell at the retire confidence level."
         f"\n\n{AGENT_TRAILER}")


def guidance_commands(action: dict) -> list:
    """The writes `guidance_execute` makes, for a dry run."""
    kind = action["action"]
    if kind == "create-issue":
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 "--body-file", "-"]]
    if kind == "update-issue":
        return [["gh", "issue", "edit", str(action["issue"]), "-R", EVALS_REPO,
                 "--body-file", "-"]]
    if kind == "guidance-removal":
        return [["git", "checkout", "-b", action["branch"]],
                ["edit", action["file"], f"remove ## {action['heading']}"],
                *([["copy", "agents-md/base.md", GUIDANCE_PAYLOAD]]
                  if action["file"] == "agents-md/base.md" else []),
                ["edit", GUIDANCE_MANIFEST, f"delete row {action['section']}"],
                ["node", "scripts/check-guidance-coverage.js", "--write-bytes"],
                ["edit", GUIDANCE_IMPACT, "insert the remove entry"],
                ["bash", "scripts/build-agents-md.sh", "> AGENTS.md (managed half)"],
                ["git", "commit"],
                ["git", "push", "origin", f"HEAD:refs/heads/{action['branch']}"],
                ["git", "merge-base", "--is-ancestor", "HEAD",
                 f"refs/remotes/origin/{action['branch']}"],
                ["gh", "pr", "create", "-R", GUIDANCE_REPO, "--base", "main",
                 "--head", action["branch"], "--title", action["title"], "--body-file", "-"],
                ["gh", "api", "-X", "POST",
                 f"repos/{GUIDANCE_REPO}/issues/<new pull request number>/labels",
                 "-f", f"labels[]={AGENT_LABEL}"],
                ["gh", "pr", "merge", "<new pull request url>", "-R", GUIDANCE_REPO,
                 "--auto", "--merge", "--match-head-commit", "<removal head sha>"],
                ["gh", "pr", "view", "<new pull request url>", "-R", GUIDANCE_REPO,
                 "--json", "autoMergeRequest"],
                ["gh", "issue", "create", "-R", EVALS_REPO, "--title",
                 action["notice"]["title"], "--label", AGENT_LABEL, "--body-file", "-"]]
    return []


GUIDANCE_PR_URL_RE = re.compile(rf"https://github\.com/{re.escape(GUIDANCE_REPO)}/pull/(\d+)")


def guidance_execute(action: dict, checkout: Path | None, gh, push, env,
                     registry_gh=None) -> str:
    """Make the plan's writes: skills-evals issues through `gh`,
    _agent-guidance writes through `registry_gh` (default `gh`)."""
    registry_gh = registry_gh or gh
    kind = action["action"]
    if kind == "none":
        return action["reason"]
    if kind in ("create-issue", "update-issue"):
        gh(guidance_commands(action)[0][1:], action["body"])
        return (f"filed an issue for {action['section']}" if kind == "create-issue"
                else f"updated issue #{action['issue']} for {action['section']}")
    check_auto_env(env)
    guidance_prepare_branch(checkout, action)
    head = _git(checkout, "rev-parse", "HEAD").strip()
    push(checkout, action["branch"])
    url = registry_gh(["pr", "create", "-R", GUIDANCE_REPO, "--base", "main",
                       "--head", action["branch"], "--title", action["title"],
                       "--body-file", "-"], action["body"]).strip()
    match = GUIDANCE_PR_URL_RE.fullmatch(url)
    if not match:
        raise RetireError("creating the pull request printed no pull request URL")
    # Labeled before auto-merge, as the skill path does: a pull request that
    # could not be marked as the loop's stays open for a person.
    registry_gh(["api", "-X", "POST", f"repos/{GUIDANCE_REPO}/issues/{match.group(1)}/labels",
                 "-f", f"labels[]={AGENT_LABEL}"])
    registry_gh(["pr", "merge", url, "-R", GUIDANCE_REPO, "--auto", "--merge",
                 "--match-head-commit", head])
    method = registry_gh(["pr", "view", url, "-R", GUIDANCE_REPO, "--json",
                          "autoMergeRequest", "--jq",
                          '.autoMergeRequest.mergeMethod // ""']).strip()
    if method != "MERGE":
        raise RetireError(f"auto-merge (merge commit) is not enabled on {url}")
    # The notice goes out once the removal is armed, through the job's own
    # token (skills-evals issues), never the _agent-guidance one.
    notice = action["notice"]
    gh(["issue", "create", "-R", EVALS_REPO, "--title", notice["title"],
        "--label", AGENT_LABEL, "--body-file", "-"],
       notice["body"].replace("{removal_pr}", url))
    return f"opened {url} with auto-merge, and filed the removal notice"


# ---------------------------------------------------------------------------
# Withdrawal (ADR 0014, round 8's known limit): `--withdraw-stale`. An open
# removal pull request the loop made is armed to auto-merge on the verdict it
# was opened on. When a later verdict no longer supports it (more runs moved
# the subject to keep or insufficient, or its removal fell to a proposal),
# the pull request is disarmed, told why, closed, and the subject's proposal
# issue records the withdrawal. While the target's mode is `proposal` (the
# owner's switch), a removal the verdict still supports is only disarmed.
# `withdrawal_decision` decides, with no I/O; `withdraw_stale` does the calls.

#: The label the owner puts on work he has paused; a held pull request is
#: never touched (the fleet's on-hold rule).
ON_HOLD_LABEL = "on-hold"
#: The login every loop removal pull request is opened under: the
#: eval-improve GitHub App's bot (secrets EVAL_IMPROVE_APP_CLIENT_ID and
#: EVAL_IMPROVE_APP_PEM; skill-coverage.yml mints its token for both
#: adam-agentskills and _agent-guidance). Its `draft-skill/` and
#: `eval-improve/` pull requests in adam-agentskills carry this login. A
#: pull request opened by anyone else (a person, or an agent acting on a
#: proposal issue) is not the loop's, whatever its head or labels.
LOOP_AUTHOR = "skills-evals-improve[bot]"
WITHDRAWN_MARKER = "<!-- skills-evals:withdrawn-removal:{subject} -->"
DISARMED_MARKER = "<!-- skills-evals:disarmed-removal:{subject} -->"
REARMED_MARKER = "<!-- skills-evals:rearmed-removal:{subject} -->"
#: The label a pass puts on a removal whose auto-merge it turned off (PR #724
#: round 2's R2-5). Only a pull request carrying it is ever armed again: one
#: whose auto-merge a person turned off has no label and stays off.
DISARMED_LABEL = "loop-disarmed"
#: How a pass creates DISARMED_LABEL in a repository that lacks it (`gh label
#: create --force`, through the App token: GitHub lets an installation token
#: with pull-requests: write create a label, POST /repos/{owner}/{repo}/labels).
DISARMED_LABEL_COLOR = "BFD4F2"
#: GitHub caps a label description at 100 characters (REST "Create a label"),
#: so this is the requested text shortened to 99.
DISARMED_LABEL_DESCRIPTION = ("Eval loop turned off auto-merge on this removal PR; it re-arms "
                              "it when the verdict supports removal")
#: Cell classes that say a verdict's data is unfinished (harness/gates.py
#: `retirement`): `missing` (no run on a roster model, as for every cell on a
#: model the roster just added) and `insufficient` (a test that has not
#: decided). An `insufficient` verdict over one is incomplete, not stale.
INCOMPLETE_CELL_CLASSES = frozenset({"missing", "insufficient"})
#: The basis a removal pull request's body records (`_pr_body` and
#: `guidance_plan`): "**retire** as of <the gates document's as_of> (".
BASIS_RE = re.compile(r"\*\*retire\*\* as of (\S+) \(")
#: harness/gates.py's reason for a section `retire` whose alone pair is
#: unfinished (`removal_support` takes a parameter named `gates`).
ALONE_UNFINISHED_REASON = gates.ALONE_UNFINISHED_REASON
#: The events that may withdraw: the daily retirement job and the pass after
#: every ingest (loop-pr-refresh.yml). Withdrawal only disarms, closes and
#: files an issue; it never arms or opens anything.
WITHDRAW_EVENTS = ("schedule", "workflow_run")
#: Per target: the repository, the loop's head prefix, the gates document's
#: verdict block, and how its mode is read.
WITHDRAW_TARGETS = {
    "skill": {"repo": REGISTRY_REPO, "prefix": BRANCH_PREFIX, "block": "skills",
              "url_re": PR_URL_RE, "mode": mode_of},
    "guidance": {"repo": GUIDANCE_REPO, "prefix": GUIDANCE_BRANCH_PREFIX,
                 "block": "guidance", "url_re": GUIDANCE_PR_URL_RE, "mode": guidance_mode},
}


def _one_line(value) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


#: GitHub's `created_at` (UTC, `Z`) and the gates document's `as_of`.
_ISO_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)")


def _moment(value):
    """`value` (an `as_of` stamp, `YYYYMMDDTHHMMSSZ`, or an ISO 8601 time
    with its offset) as an aware datetime, or None when it is missing or
    unparseable."""
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z", value):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if _ISO_RE.fullmatch(value):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return None


def removal_support(gates: dict, entry, target: str = "skill") -> tuple:
    """Whether a verdict entry still supports an automatic removal:
    `("supported", why)`, `("incomplete", why)`, `("unknown", why)` or
    `("stale", why)`.

    Supported is a `retire` whose `removal` is `auto` and whose cells agree
    (`proposal_only`, or `guidance_proposal_only` for a section, None). A
    `retire-pending` whose `raw_verdict` is `retire` counts as that `retire`:
    compute_gates' `finalize` demotes all but one confirmed subject per
    evaluation, which ranks them and says nothing against this one (round
    1's M1). Unknown is a verdict that raised in compute_gates.py or a
    `retire` that fails the re-check.

    Incomplete (PR #724 round 3's M1) is undecided data, which argues
    neither way: an `insufficient` verdict over a `missing` or
    `insufficient` cell (INCOMPLETE_CELL_CLASSES; a roster model just added
    makes every cell on it `missing`), or a section's `retire` lowered only
    by its unfinished section-alone pair (ALONE_UNFINISHED_REASON)."""
    if not isinstance(entry, dict) or not isinstance(entry.get("verdict"), str) \
            or not isinstance(entry.get("reason"), str) \
            or entry["reason"].startswith(compute_gates.VERDICT_RAISED):
        return "unknown", "the subject's verdict could not be computed"
    cells = entry.get("cells")
    if cells is not None and not isinstance(cells, list):
        return "unknown", "the subject's cells are malformed"
    verdict = entry["verdict"]
    if verdict == "retire-pending" and entry.get("raw_verdict") == "retire":
        verdict = "retire"
    if verdict != "retire":
        if verdict == "insufficient" and any(
                isinstance(c, dict) and c.get("class") in INCOMPLETE_CELL_CLASSES
                for c in cells or []):
            return "incomplete", ("the verdict is insufficient because a cell is missing "
                                  "or insufficient (runs still to come, or a roster model "
                                  "with none yet)")
        return "stale", f"the verdict is {entry['verdict']}, not retire"
    try:
        retiring({**gates, "skills": {"subject": {**entry, "verdict": "retire"}}})
    except RetireError:
        return "unknown", "the subject's retire verdict is malformed"
    if target == "guidance":
        lowered = guidance_proposal_only(entry)
        if lowered is not None and cells_allow_auto(entry) and (
                lowered == ALONE_UNFINISHED_REASON
                or entry.get("removal_reason") == ALONE_UNFINISHED_REASON):
            return "incomplete", ALONE_UNFINISHED_REASON
    else:
        lowered = proposal_only(entry)
    if lowered is not None:
        return "stale", lowered
    return "supported", "the verdict is still retire with an automatic removal"


def _basis(body):
    """The `as_of` a removal pull request's body says it was opened on, as
    an aware datetime, or None when the body records none that parses."""
    match = BASIS_RE.search(body) if isinstance(body, str) else None
    return _moment(match.group(1)) if match else None


def withdrawal_decision(pr: dict, gates: dict | None, target: str = "skill") -> dict:
    """What to do with one open pull request, from the gates document alone.

    `{"action": "ignore" | "keep" | "disarm" | "rearm" | "withdraw",
    "why": text, ...}`: `ignore` for a pull request the loop did not make
    (head prefix, the `agent-authored` label and `LOOP_AUTHOR` as its author
    all required) or one held `on-hold`; `withdraw` when its subject's
    verdict no longer supports an automatic removal (`removal_support`
    "stale"), with the verdict fields the comment quotes; `disarm` (cause
    `incomplete`) in either mode when the verdict's data is incomplete
    (round 3's M1: undecided data argues neither way, so the removal is
    neither merged nor closed for good); otherwise `disarm` (cause
    `proposal`) while the target's mode is `proposal` (the one switch);
    `rearm` in `auto` mode for a supported removal labeled DISARMED_LABEL
    (R2-5), whatever armed state it is in, which `withdraw_stale` reads;
    else `keep`. Unknown data never withdraws: `gates` None, no verdict
    block, a subject the block does not list (an empty or partial block), a
    malformed entry or a verdict that raised all keep (or only disarm, in
    proposal mode).

    A pull request is withdrawn only by verdicts newer than the results it
    was opened on (round 3's M2): the `as_of` its body records
    ("**retire** as of <as_of> (", BASIS_RE) must not be later than the
    gates document's. A body with no parseable basis falls back to its
    `created_at` (R2-1): one created after the gates document's `as_of` is
    kept, as it is when either time is missing or unparseable. A pass that
    started on older results can otherwise close, for good, a removal the
    retirement job has just opened on newer ones."""
    spec = WITHDRAW_TARGETS[target]
    head, labels = pr.get("head"), pr.get("labels")
    if not isinstance(head, str) or not head.startswith(spec["prefix"]) \
            or not isinstance(labels, list) or AGENT_LABEL not in labels \
            or pr.get("author") != LOOP_AUTHOR:
        return {"action": "ignore", "why": "not a removal pull request the loop opened"}
    if ON_HOLD_LABEL in labels:
        return {"action": "ignore", "why": f"labeled {ON_HOLD_LABEL}"}
    subject = head[len(spec["prefix"]):]
    if not SKILL_RE.fullmatch(subject):
        return {"action": "keep", "why": "its head names no subject"}
    if not isinstance(gates, dict) or not isinstance(gates.get(spec["block"]), dict):
        return {"action": "keep", "subject": subject, "why": "the verdicts are unknown"}
    block = gates[spec["block"]]
    if subject not in block:
        state, why = "unknown", "the verdicts document does not list the subject"
    else:
        state, why = removal_support(gates, block[subject], target)
    if state == "incomplete":
        return {"action": "disarm", "cause": "incomplete", "subject": subject, "why": why}
    if state == "stale":
        judged = _moment(gates.get("as_of"))
        basis = _basis(pr.get("body"))
        if basis is not None and judged is not None:
            if basis > judged:
                return {"action": "keep", "subject": subject,
                        "why": "it was opened on newer results than these verdicts"}
        else:
            opened = _moment(pr.get("created_at"))
            if opened is None or judged is None:
                return {"action": "keep", "subject": subject,
                        "why": "its basis, its creation time or the verdicts' as_of "
                               "is unknown"}
            if opened > judged:
                return {"action": "keep", "subject": subject,
                        "why": "it was opened after the results these verdicts stand on"}
        entry = block[subject]
        return {"action": "withdraw", "subject": subject, "verdict": entry["verdict"],
                "removal": entry.get("removal") if isinstance(entry.get("removal"), str)
                else None,
                "reason": _one_line(entry["reason"]),
                "removal_reason": _one_line(entry.get("removal_reason")), "why": why}
    if spec["mode"](gates) != "auto":
        return {"action": "disarm", "cause": "proposal", "subject": subject,
                "why": f"the {spec['block']} retirement_mode is proposal ({why})"}
    if state == "supported" and DISARMED_LABEL in labels:
        return {"action": "rearm", "subject": subject, "why": why}
    return {"action": "keep", "subject": subject, "why": why}


OVERRIDE = ("To remove the subject anyway, take it over from the loop: remove the "
            f"`{AGENT_LABEL}` label first (a pull request without it is not the loop's, so "
            "no later pass touches it), then reopen this pull request if it is closed and "
            "merge it by hand.")


def withdrawal_comment(decision: dict, gates: dict, run_url: str | None) -> str:
    """The comment a withdrawn pull request gets: the new verdict, why, and
    how a person overrides it."""
    subject = decision["subject"]
    removal = f", removal `{decision['removal']}`" if decision.get("removal") else ""
    now = (f"The current verdict for `{subject}` as of {gates['as_of']} is "
           f"**{decision['verdict']}**{removal}: {decision['reason']}"
           + (f" ({decision['removal_reason']})" if decision.get("removal_reason") else "")
           + f". Why this withdraws the removal: {decision['why']}.")
    return (f"{WITHDRAWN_MARKER.format(subject=subject)}\n"
            "**Withdrawn automatically.** This removal pull request was opened on a "
            "`retire` verdict with an automatic removal, and the subject no longer has "
            f"one.\n\n{now}\n\n"
            "Auto-merge is turned off and the pull request is closed; its branch is "
            "kept. A closed removal pull request counts as decided, so the loop does not "
            "open it again; the subject's retirement issue in skills-evals records this "
            f"withdrawal. {OVERRIDE} Rule: [ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")


def disarm_comment(decision: dict, run_url: str | None, labeled: bool = True) -> str:
    """The one comment a removal a pass disarms gets: by the `proposal`
    switch, or (cause `incomplete`) on a verdict whose data is unfinished.
    `labeled` False: DISARMED_LABEL could not be added, so no pass arms it
    again, and the comment says so."""
    rearm = (f"the loop turns auto-merge back on (the `{DISARMED_LABEL}` label on this "
             "pull request marks it as the loop's to re-arm)" if labeled else
             f"turn auto-merge back on by hand (a merge commit): the `{DISARMED_LABEL}` "
             "label could not be added, so no pass does")
    if decision.get("cause") == "incomplete":
        why = ("The subject's verdict is not complete yet, so this removal neither "
               f"merges nor is withdrawn: {decision['why']}. This pull request stays "
               "open; once the verdict supports an automatic removal again in `auto` "
               f"mode, {rearm}, and if the verdict turns against the removal it is "
               "withdrawn.")
    else:
        why = ("The retirement mode in `evals/gate-policy.yml` is `proposal`, so no "
               f"removal merges without a person: {decision['why']}. This pull request "
               "stays open; merge it by hand to remove the subject, or close it to "
               "decline. If the mode returns to `auto` while the verdict still supports "
               f"the removal, {rearm}.")
    return (f"{DISARMED_MARKER.format(subject=decision['subject'])}\n"
            f"**Auto-merge turned off.** {why} Remove the `{AGENT_LABEL}` label before "
            "merging by hand, so no later pass touches it. Rule: "
            f"[ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")


def rearm_comment(decision: dict, run_url: str | None) -> str:
    """The comment a removal the loop disarmed gets when it is armed again."""
    return (f"{REARMED_MARKER.format(subject=decision['subject'])}\n"
            "**Auto-merge turned back on.** A pass turned it off earlier (the "
            f"`{DISARMED_LABEL}` label); the subject's verdict supports an automatic "
            f"removal again in `auto` mode: {decision['why']}. It merges (merge commit) "
            "once required checks pass. To decline the removal, close it. Rule: "
            f"[ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")


def removal_prs(gh, target: str) -> list:
    """The target repository's open pull requests, each with its number,
    head branch, URL, labels, author login, `created_at` (R2-1) and body
    (its basis, round 3's M2), read through the job's token.
    Whether auto-merge is armed is read later, per pull request, by
    `withdraw_stale` (`gh pr view`)."""
    repo = WITHDRAW_TARGETS[target]["repo"]
    text = gh(["api", "--paginate", f"repos/{repo}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url, "
                       "labels: [.labels[].name], author: .user.login, "
                       "created_at: .created_at, body: (.body // \"\")}"])
    return _json_lines(text)


def withdraw_commands(target: str, url: str) -> dict:
    """The calls one withdrawal, disarm or re-arm makes: (state) the pull
    request must still be open; (merge) auto-merge off, then (view) read
    back; (label) DISARMED_LABEL on, after (create_label) when the
    repository lacks it; (comment); (close), which keeps the branch. A re-arm reads (head) the head commit, arms (arm) as `execute`
    does, reads back (view) and takes the label off (unlabel)."""
    repo = WITHDRAW_TARGETS[target]["repo"]
    return {"state": ["pr", "view", url, "-R", repo, "--json", "state", "--jq", ".state"],
            "merge": ["pr", "merge", url, "-R", repo, "--disable-auto"],
            "view": ["pr", "view", url, "-R", repo, "--json", "autoMergeRequest", "--jq",
                     '.autoMergeRequest.mergeMethod // ""'],
            "label": ["pr", "edit", url, "-R", repo, "--add-label", DISARMED_LABEL],
            "create_label": ["label", "create", DISARMED_LABEL, "-R", repo, "--color",
                             DISARMED_LABEL_COLOR, "--description",
                             DISARMED_LABEL_DESCRIPTION, "--force"],
            "unlabel": ["pr", "edit", url, "-R", repo, "--remove-label", DISARMED_LABEL],
            "head": ["pr", "view", url, "-R", repo, "--json", "headRefOid", "--jq",
                     ".headRefOid"],
            "arm": ["pr", "merge", url, "-R", repo, "--auto", "--merge",
                    "--match-head-commit", "<head sha>"],
            "comment": ["pr", "comment", url, "-R", repo, "--body-file", "-"],
            "close": ["pr", "close", url, "-R", repo]}


def would_run(target: str, item: dict) -> list:
    """The dry run's list of the writes for one planned item."""
    c = withdraw_commands(target, item["url"])
    if item["action"] == "withdraw":
        return [c["state"], c["view"], c["merge"], c["view"], c["comment"], c["close"],
                ["issue", "create-or-comment", "-R", EVALS_REPO,
                 "<the subject's retirement issue>"],
                ["issue", "close", "<the subject's open removal notice>", "-R", EVALS_REPO,
                 "--reason", "not planned"],
                ["issue", "comment", "<the subject's open removal notice>", "-R", EVALS_REPO,
                 "--body-file", "-"]]
    if item["action"] == "disarm":
        return [c["state"], c["view"], c["merge"], c["view"], c["label"], c["comment"]]
    if item["action"] == "rearm":
        return [c["state"], c["view"], c["head"], c["arm"], c["view"], c["unlabel"],
                c["comment"]]
    return []


def withdraw_plan(gates: dict | None, prs: list, target: str) -> list:
    """Each listed pull request's decision, with its number and URL; a
    `withdraw`, `disarm` or `rearm` whose URL is not the target repository's pull
    request is refused rather than acted on."""
    spec = WITHDRAW_TARGETS[target]
    out = []
    for pr in prs:
        decision = withdrawal_decision(pr, gates, target)
        if decision["action"] == "ignore":
            continue
        url, number = pr.get("url"), pr.get("number")
        match = spec["url_re"].fullmatch(url) if isinstance(url, str) else None
        if decision["action"] in ("withdraw", "disarm", "rearm") and (
                not match or type(number) is not int or match.group(1) != str(number)):
            raise RetireError("an open pull request record from the API is malformed")
        out.append({**decision, "number": number, "url": url})
    return out


def withdrawal_issue(item: dict, gates: dict, target: str, gh, run_url: str | None) -> dict:
    """The subject's retirement proposal issue, filed or commented on to
    record the withdrawal (round 1's M4): the issue `--fallback-to-proposal`
    and proposal mode use (same marker, same author), so a withdrawn subject
    is never decided in silence. The oldest open one gets `comment` as a
    comment, its body (the proposal's evidence) left as it is (R2-6);
    otherwise one is filed with `body`."""
    subject = item["subject"]
    if target == "skill":
        marker = ISSUE_MARKER.format(skill=subject)
        found = existing_issues(gh, subject)
        title = f"Retire skill {subject}: automatic removal withdrawn (#70)"
    else:
        marker = GUIDANCE_ISSUE_MARKER.format(section=subject)
        found = guidance_issues(gh, marker)
        title = f"Retire guidance section {subject}: automatic removal withdrawn (#124)"
    note = (f"The automatic removal pull request {item['url']} was withdrawn "
            f"(turned off and closed, branch kept) on the verdicts as of {gates['as_of']}: "
            f"the verdict is now **{item['verdict']}**: {item['reason']}. Why: "
            f"{item['why']}.\n\nA closed removal pull request decides the subject, so the "
            f"loop opens no removal for it again. {OVERRIDE} Otherwise close this issue."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\nFiled by scripts/retire_skill.py --withdraw-stale (ADR 0014).\n\n"
            + AGENT_MARKER + "\n")
    number = found["open"][0] if found["open"] else None
    return {"action": "update-issue" if number else "create-issue", "issue": number,
            "title": title, "body": f"{marker}\n{note}", "comment": note}


def close_removal_notices(item: dict, gates: dict, target: str, gh,
                          run_url: str | None) -> list:
    """Close (not planned), then comment on, every open removal notice
    (#557) for the withdrawn subject, so none is left saying a removal is in
    flight (R2-3); the numbers closed, each `#n`, or `#n (no comment)` when
    only its comment failed. Closing first (round 3's m2) means a failure
    never leaves an open notice whose comment says it is closed."""
    subject = item["subject"]
    if target == "skill":
        marker = SKILL_NOTICE_MARKER.format(skill=subject)
    else:
        marker = GUIDANCE_NOTICE_MARKER.format(section=subject)
    note = (f"**Removal withdrawn.** The automatic removal pull request {item['url']} for "
            f"`{subject}` was withdrawn (turned off and closed, branch kept) on the "
            f"verdicts as of {gates['as_of']}: the verdict is now **{item['verdict']}**. "
            "Nothing is being removed, so this notice is closed; the subject's retirement "
            f"issue records the withdrawal. Rule: [ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")
    closed = []
    for number in guidance_issues(gh, marker)["open"]:
        gh(["issue", "close", str(number), "-R", EVALS_REPO, "--reason", "not planned"])
        try:
            gh(["issue", "comment", str(number), "-R", EVALS_REPO, "--body-file", "-"], note)
        except Exception:  # noqa: BLE001 - the notice is closed; say so, no detail
            closed.append(f"#{number} (no comment)")
        else:
            closed.append(f"#{number}")
    return closed


def add_disarmed_label(c: dict, registry_gh) -> bool:
    """DISARMED_LABEL on a pull request this pass disarmed; True once it is
    on. When the add fails (the repository has no such label yet), the
    label is created (`--force`, so an existing one is only updated) and
    the add is tried once more. Auto-merge is already off by then, so a
    failure only loses the later re-arm: False, never an exception, and no
    error detail is kept."""
    try:
        registry_gh(c["label"])
        return True
    except Exception:  # noqa: BLE001 - the disarm stands either way
        pass
    try:
        registry_gh(c["create_label"])
    except Exception:  # noqa: BLE001
        pass
    try:
        registry_gh(c["label"])
        return True
    except Exception:  # noqa: BLE001
        return False


def rearm(item: dict, c: dict, armed: bool, registry_gh, run_url: str | None) -> str:
    """Arm again a removal the loop disarmed (R2-5): auto-merge on with the
    command `execute` uses, at the head read now, read back, then the label
    off and one comment; the status line. An armed one only loses the
    label."""
    if not armed:
        head = registry_gh(c["head"]).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise RetireError(f"#{item['number']}'s head commit could not be read")
        registry_gh([*c["arm"][:-1], head])
        if registry_gh(c["view"]).strip() != "MERGE":
            raise RetireError(f"auto-merge (merge commit) is not enabled on #{item['number']}")
    registry_gh(c["unlabel"])
    if armed:
        return f"unlabeled #{item['number']}: auto-merge was already on"
    registry_gh(c["comment"], rearm_comment(item, run_url))
    return f"re-armed #{item['number']}: {item['why']}"


def withdraw_stale(gates: dict | None, prs: list, target: str, registry_gh,
                   run_url: str | None = None, gh=None) -> list:
    """Withdraw every stale loop removal pull request among `prs` (the
    listing `removal_prs` read), disarm every one the `proposal` switch or
    incomplete data holds, and re-arm every one the loop disarmed that is
    supported again in `auto` mode; the status lines. Pull request writes go through `registry_gh`;
    the retirement issue and the removal notice through `gh` (the job's
    token; default `registry_gh`)."""
    gh = gh or registry_gh
    lines = []
    for item in withdraw_plan(gates, prs, target):
        if item["action"] == "keep":
            lines.append(f"kept #{item['number']}: {item['why']}")
            continue
        c = withdraw_commands(target, item["url"])
        if registry_gh(c["state"]).strip() != "OPEN":
            lines.append(f"skipped #{item['number']}: it is no longer open")
            continue
        armed = bool(registry_gh(c["view"]).strip())
        if item["action"] == "rearm":
            lines.append(rearm(item, c, armed, registry_gh, run_url))
            continue
        if armed:
            registry_gh(c["merge"])
            if registry_gh(c["view"]).strip():
                raise RetireError(f"auto-merge is still enabled on #{item['number']}")
        if item["action"] == "disarm":
            if armed:
                # Labeled only when this pass turned auto-merge off: a pull
                # request a person disarmed is never armed again (R2-5).
                labeled = add_disarmed_label(c, registry_gh)
                registry_gh(c["comment"], disarm_comment(item, run_url, labeled))
                lines.append(f"disarmed #{item['number']}: {item['why']}" + (
                    "" if labeled else f"; could not add the {DISARMED_LABEL} label, "
                                       "so no pass turns its auto-merge back on"))
            else:
                lines.append(f"left #{item['number']} open and disarmed: {item['why']}")
            continue
        registry_gh(c["comment"], withdrawal_comment(item, gates, run_url))
        registry_gh(c["close"])
        issue = withdrawal_issue(item, gates, target, gh, run_url)
        if issue["action"] == "update-issue":
            gh(["issue", "comment", str(issue["issue"]), "-R", EVALS_REPO, "--body-file", "-"],
               issue["comment"])
            filed = f"commented on issue #{issue['issue']}"
        else:
            gh(["issue", "create", "-R", EVALS_REPO, "--title", issue["title"],
                "--body-file", "-"], issue["body"])
            filed = "filed its retirement issue"
        # Best effort: the withdrawal has happened; a notice left open is
        # named in the status line, never a failed pass.
        try:
            closed = close_removal_notices(item, gates, target, gh, run_url)
        except Exception:  # noqa: BLE001
            filed += "; could not close its removal notice"
        else:
            if closed:
                filed += "; closed its removal notice " + ", ".join(closed)
        lines.append(f"withdrew #{item['number']}: {item['why']}; {filed}")
    return lines or ["no open removal pull request to withdraw"]


def withdraw_main(args, env, gh, registry_gh, run_url, out) -> int:
    """`--withdraw-stale`: unknown verdicts withdraw nothing and exit 0 with a
    status that names no subject; a refusal or a failed call exits 2."""
    try:
        gates = load_gates(args.gates)
    except RetireError:
        gates = None
    if gates is not None and args.target == "guidance" \
            and not isinstance(gates.get("guidance"), dict):
        gates = None
    if gates is None:
        out.write("retire_skill: withdrew nothing: the verdicts document is missing "
                  "or unreadable\n")
        return 0
    prs = removal_prs(gh, args.target)
    items = withdraw_plan(gates, prs, args.target)
    if args.dry_run:
        out.write(json.dumps({"dry_run": True, "withdraw": items, "would_run": [
            ["gh", *c] for i in items for c in would_run(args.target, i)]},
            indent=2, sort_keys=True) + "\n")
        return 0
    if any(i["action"] in ("withdraw", "disarm", "rearm") for i in items):
        check_auto_env(env)
    for line in withdraw_stale(gates, prs, args.target, registry_gh, run_url, gh):
        out.write(f"retire_skill: {line}\n")
    return 0


def refresh_allowed(gates: dict | None, head: str) -> tuple:
    """Whether loop-pr-refresh.yml may bring a pull request from `head` up to
    date (round 1's M2): `(True, why)` for a head that is not a removal's;
    for a `retire-skill/` or `retire-guidance/` head, only while its
    subject's verdict still supports an automatic removal AND the target's
    mode is `auto`. Anything else, unknown data included, is `(False, why)`,
    so a refresh never re-runs the checks of a removal that should not
    merge."""
    for target, spec in WITHDRAW_TARGETS.items():
        if not head.startswith(spec["prefix"]):
            continue
        subject = head[len(spec["prefix"]):]
        if not SKILL_RE.fullmatch(subject):
            return False, "its head names no subject"
        if not isinstance(gates, dict) or not isinstance(gates.get(spec["block"]), dict):
            return False, "the verdicts are unknown"
        if subject not in gates[spec["block"]]:
            return False, "the verdicts document does not list the subject"
        state, why = removal_support(gates, gates[spec["block"]][subject], target)
        if state != "supported":
            return False, why
        if spec["mode"](gates) != "auto":
            return False, f"the {spec['block']} retirement_mode is proposal"
        return True, why
    return True, "not a removal pull request"


def main(argv: list | None = None, *, env=None, gh=default_gh, push=None,
         registry_gh=None, out=sys.stdout) -> int:
    env = os.environ if env is None else env
    token = env.get(REGISTRY_TOKEN_ENV) or None
    if push is None:
        def push(checkout, branch):
            default_push(checkout, branch, token)
    if registry_gh is None and gh is not default_gh:
        registry_gh = gh  # an injected gh (a test's fake) answers both
    elif registry_gh is None:
        def registry_gh(args, stdin=None):
            if not token:
                raise RetireError(f"no {REGISTRY_TOKEN_ENV} for an adam-agentskills write")
            return default_gh(args, stdin, token)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gates", required=True, type=Path)
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--allow-mode", action="append", choices=("auto", "proposal"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fallback-to-proposal", action="store_true",
                        help="this caller has no write credential for the target repository: a "
                             "gates file in auto mode files the issue instead of exiting 2")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        help="the skill-impact entry's date (default: the gates file's "
                             "as_of date)")
    parser.add_argument("--target", choices=("skill", "guidance"), default="skill",
                        help="act on the skills' verdicts (default) or the guidance "
                             "sections' (#124)")
    parser.add_argument("--guidance", type=Path, metavar="PATH",
                        help="the _agent-guidance checkout a guidance removal edits")
    parser.add_argument("--usage", type=Path, default=None,
                        help="usage/weekly-local.json, for the issue's recent-use line")
    parser.add_argument("--withdraw-stale", action="store_true",
                        help="only withdraw the target's open removal pull requests whose "
                             "subject's verdict no longer supports them, and disarm the "
                             "rest while the mode is proposal (ADR 0014)")
    args = parser.parse_args(argv)
    run_url = None
    if env.get("GITHUB_RUN_ID") and env.get("GITHUB_REPOSITORY") == EVALS_REPO \
            and env["GITHUB_RUN_ID"].isdigit():
        run_url = (f"https://github.com/{EVALS_REPO}/actions/runs/{env['GITHUB_RUN_ID']}")
    try:
        if not args.dry_run:
            check_event(env, WITHDRAW_EVENTS if args.withdraw_stale else ("schedule",))
        if args.withdraw_stale:
            return withdraw_main(args, env, gh, registry_gh, run_url, out)
        if args.date is not None and not DATE_RE.fullmatch(args.date):
            raise RetireError("--date is not YYYY-MM-DD")
        gates = load_gates(args.gates)
        registries = compute_gates.flag_registries(args.registry)
        allowed = tuple(args.allow_mode or ("proposal",))
        if args.target == "guidance":
            if not args.dry_run and guidance_mode(gates) == "auto" and "auto" in allowed:
                check_auto_env(env)
            action = guidance_plan(gates, args.guidance, gh, run_url, allowed,
                                   fallback=args.fallback_to_proposal)
            if args.dry_run:
                out.write(json.dumps({"dry_run": True, **action,
                                      "would_run": guidance_commands(action)},
                                     indent=2, sort_keys=True) + "\n")
                return 0
            if action.get("mode_reason"):
                print(f"retire_skill: auto lowered to proposal: {action['mode_reason']}",
                      file=sys.stderr)
            out.write(guidance_execute(action, args.guidance, gh, push, env,
                                       registry_gh) + "\n")
            return 0
        if not args.dry_run and mode_of(gates) == "auto" and "auto" in allowed:
            check_auto_env(env)
        usage = skill_usage.load(args.usage) if args.usage is not None else None
        action = plan(gates, registries, gh, run_url, allowed, usage,
                      fallback=args.fallback_to_proposal, date=args.date)
        if args.dry_run:
            out.write(json.dumps({"dry_run": True, **action,
                                  "would_run": commands(action)},
                                 indent=2, sort_keys=True) + "\n")
            return 0
        if action.get("mode_reason"):
            print(f"retire_skill: auto lowered to proposal: {action['mode_reason']}",
                  file=sys.stderr)
        out.write(execute(action, registries, gh, push, env, registry_gh) + "\n")
    except (RetireError, ValueError) as exc:
        print(f"retire_skill: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
