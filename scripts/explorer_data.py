#!/usr/bin/env python3
"""Write `explorer/latest.json`: the public data behind the Evals Explorer (#72).

  explorer_data.py --results-tree DIR --roster evals/roster.yml
                   --policy evals/gate-policy.yml --as-of TIME
                   --repository-commit SHA --results-commit SHA --out FILE
                   [--evals-dir DIR] [--guidance-manifest eval-coverage.yml]
                   [--guidance DIR] [--registry NAME=PATH ...]
                   [--regression-issues FILE] [--context-repo OWNER/REPO=PATH ...]
                   [--fire-runs FILE] [--fixture-queue FILE]
                   [--lessons DIR] [--lesson-records DIR] [--draft-prs FILE]
                   [--lesson-issues FILE] [--public-repos FILE] [--activity FILE]
                   [--removal-state FILE]
                   [--agent-checks DIR] [--hook-policy FILE] [--export-policy FILE]
                   [--lesson-funnel FILE] [--source-repository OWNER/REPO]
  explorer_data.py --subjects private --registry PRIVATE_NAME=PATH
                   --results-tree DIR --roster ... --out FILE (not latest.json)
  explorer_data.py context-drift-report --results-tree DIR --as-of TIME
                   [--evals-dir DIR] [--context-repo OWNER/REPO=PATH ...]

It reuses scripts/compute_gates.py for the validated run index
(`build_index`) and the verdicts (`compute`), then reshapes them for a page
that anyone can read. The document is PUBLIC, so what it leaves out matters
more than what it carries:

  * PRIVACY GATE. A skill is listed only if the census
    (`<results-tree>/coverage/latest.json`) names it in a registry with
    `private: false`. A skill with runs but no such census row (a private
    registry's skill, or a retired one) is dropped, and so is every alert
    about it. The census is the one source of what is public.
  * No session id, digest (except a 12-hex prefix under `copies` and in a
    `loaded-copy` alert), harness commit, transcript or e-mail is ever
    copied from a run. `finish` is the last gate: it refuses (exit 2) a
    document containing a session-id prefix, an `@` outside a URL or a
    64-hex digest, so a future field added by mistake fails loudly instead
    of publishing; under `copies` and in `loaded-copy` alerts it also
    refuses any value that is not a 12-hex prefix or a known
    `unknown:<reason>`, and any hex run longer than 12 (the 40-hex commits in
    `source` are outside that scope). It also holds each `confidence.cells`
    row to exactly CONFIDENCE_CELL_KEYS.

Each skill and section also carries `discarded_runs` (Adam, 2026-11-07):
the recorded arm runs its current verdict does not count, as
{"total", "cost_usd", "cost_unknown", "by_reason": {slug: {"runs",
"cost_usd", "cost_unknown"}}} (harness/gates.py, DISCARDED RUNS, names the
slugs), null without a verdict; the document's `discarded_runs` sums them
over the listed skills, sections and `all`. Counts, agent dollars at full
precision and fixed slugs only: never a path, session or title.

Each skill and section also carries `run_utility` and `decisions` (Adam,
2026-11-07): every recorded arm run of it summed per (UTC day, arm model,
utility class, discard reason) with its agent cost, and its cell versions
with what each decided and when (harness/gates.py, RUN UTILITY); null
without a verdict. Days, model ids, fixture names, fixed classes and slugs,
counts and dollars only: never a run id, path, session or title. The
explorer sums the rows over a period, per subject and for the fleet.

Each skill and section also carries `confidence` (the levels its gate
bounds reach, and per cell the gain measured so far and the range it likely
falls in, `subject_confidence`; a cell's `task` is its fixture name, which
for a listed subject is a public registry's fixture under evals/) and `next_test` (its place in the
planner's eval queue or its next re-check, `test_queue`; none (no place, no due) for a subject
whose verdict is retire or retire-pending, which is removed instead) and `removal` (only for a
subject being removed or with a removal pull request or issue: `state`, `url`, `since`, from
`--removal-state`, `removal_of`; `unknown` without that file) and `stakes`
(its evals/stakes.yml level, `normal` with no row; scripts/stakes.py); each
skill carries
`usage`, its invocations in `usage/weekly-local.json`, whose window is the
top-level `usage` (None without a census: unknown, not zero).

Each skill also carries `copies` (#562, 2026-11-02): which copies of it
sessions loaded in the last COPY_WEEKS ISO weeks, from the `skill-digest`
rows of `usage/weekly-local.json` joined by (name, the registry's public
`owner/repo` from harness/registries.yml). `main` is the 12-hex prefix of
the skill's lock digest at the registry checkout's HEAD (`--registry`), and
each `loaded` entry (digest or `unknown:<reason>`, surface, invocations) says
`vs_main`: `current`, `in-window` (a digest main had at some first-parent
commit in the window, or at its start), `older` or `unknown`. `alert` holds,
per surface, whether the leading copy (most invocations; a tie counts every
tied copy) is none of main's in-window digests: null without a fresh
`skill-records` source for that surface (14 days), without a known loaded
copy, or without main's history (a shallow checkout reads unknown, never
clean). `copies` is null without a readable usage file or any
`skill-records` source (unknown, not zero). A true one becomes a report-only
`loaded-copy` alert naming the skill, the surface and the two prefixes. It
lags a main change by up to the window, since a copy main had inside the
window stays quiet.

One report-only alert watches the scheduled in-place skill fixtures (#545).
It sees a fixture only after the HEALTH FILTER (`health_fixtures`): an exact
`evals/scheduled.yml` entry that is committed, a skill subject with a public
census row, not private (`plan_week.fixture_hold_reason` and
`plan_week.private_skills`), with a `context:` block. The alert carries only
the kind, the skill, the fixture key, the public consumer repository and a
date; never a SHA, digest, path, count or a sibling skill's name.

  * `context-drift` (#545): the other skills deployed beside the subject (its
    own bundle when adopted, every bundle otherwise) moved on the consumer's
    default branch since the pin, and stayed moved for `CONTEXT_DRIFT_DAYS`.
    `drift_since` is the committer date of the lock commit that last left the
    pin's entries. `context_drift_unknown` counts the undecided fixtures.
    A drifted fixture whose evidence is in use (`drift_evidence`: runs at its
    current pin that are not due a re-check, or its skill in the open batch,
    or no digest) emits no alert, because re-pinning would restart that
    evidence; `context_drift_held` counts them. Only a free fixture alerts,
    and scripts/repin_drifted_fixtures.py (the daily routine-fixture-supply
    job) re-pins it.
    `context-drift-report` prints the per-fixture detail locally (never in CI).

#544's `broken` alert (reason `pin-deploys-older-copy`: the pin's lock
deploys an older copy of the skill than main) is retired (#559): keep-or-
remove runs now test main's copy of the subject, not the deployed one, so an
older deployed copy no longer keeps a with arm from pooling. The context
beside the subject is still the pin's, which is why `context-drift` stays.

`fires_without_results` (#555, 2026-11-02) is a document-level, report-only
summary of the last FIRE_WINDOW_DAYS of successful eval fires
(`routine-eval-fire.yml` runs, `--fire-runs`): `since` (the oldest counted
fire), `without_results` (fires no results came back for), `rejected`
(results came back but none validated; per fixture when an arm summary's
model cannot be read) and `sweeps` (the without-results fires grouped by
starts at most FIRE_SWEEP_GAP apart: start, end, count). `counted` is how many
fires the window counted in all, so a reader can say "N of M". Only fires on
the SCOPE FILTER's fixtures count (`fire_scope`: public, non-private,
scheduled skill fixtures and manifest guidance sections), so a private fire
moves nothing; no name, title or run id is published. None is unknown (no
readable fire file, or a `fetched_at` out of bounds), never 0. The per-cell
alert waits for #570.

`agent_made` (Adam, 2026-11-04) is scripts/agent_made.py's block: for each
fleet check, skill and guidance section this document lists, the commit that
created it (a `Captures:` trailer, else its first appearance in the
`--guidance` or `--registry` checkout's full history), whether an agent, a
loop App or a person made it, whether that was after the guidance told
agents to capture lessons, and its impact copied from this document. Null in
private mode or without `--guidance`; a subject whose checkout is missing or
shallow has origin null.

`fixture_queue` (Adam, 2026-11-03) is scripts/fixture_queue.py's report,
`--fixture-queue`, carried as is: the fixture requests the weekly sweep
filed, the pull requests answering them, the fixtures they added (real fleet
work or invented, from each fixture's `origin:`) with their runs, pass rates
and cost, and the queue's findings. That script decides what it holds (issue
numbers, validated names, URLs, counts and dollars; never a title or body),
and `finish` checks it with the rest. None is unknown: no readable report,
or one that is not schema 1. Its own `generated_at` moves with every build,
so explorer-data.yml's publish step ignores it beside the document's.

`lessons` (Adam, 2026-11-03) lists the session miner's lesson proposals
(`--lessons`: adam-agentskills-private's `lessons/proposals/` on
`persistent/lessons`, read with scripts/lesson_evidence.py's `newest_day`),
from the newest day's directory only. The proposals come from private local
sessions, so each item carries EXACTLY `kind`, `subject`, `evidence_count`,
`first_seen` and `last_seen` (and `draft` for a new skill), never a
proposal's `examples`, `repos`, `id` or `check_sketch`, and only for a
public subject (`lesson_item`): a new skill for a generic tool name
(`tool-<tool>[-<word>]`) or for red CI in a public repository (`red-ci-<slug>`,
the slug of a public `--registry`, a `--context-repo` or this repository); a
skill edit or fixture idea for a skill that passes the PRIVACY GATE and is
not a private one; a guidance edit or fixture idea for a section in the
guidance manifest. Everything else is only counted in `left_out`
(`memory_note`, `agent_check`, `private` for a skill or repository that
fails the gate, `other`). A new skill's `draft` is its newest
`draft-skill/<subject>` pull request in adam-agentskills from `--draft-prs`
(number, state and a URL built here), or None. Each item also carries
`sources` (the sorted machine surfaces its records came from, `wsl`,
`windows` or `cloud`, any other label `other`) and `signals` ({signal: records},
mine_sessions.py's LESSON_SIGNALS only), counted over the records under
`--lesson-records` that mine_sessions.py `route` files under the item's
(subject, kind) (`record_target`); both None without that directory. A
record's excerpt, session, record id and repository are never published; the
excerpt and repository are read in memory only, through route's own
functions, to tell which proposal a record belongs to, and the record id only
to count a record once, as route does.

`lessons.issues` (`--lesson-issues`, Adam, 2026-11-03) adds lessons from two
other sources: `memory`, the memory curation routine's `Memory promotion
<date>: <n> facts for <target>` issues in a public repository of either fleet
owner, and `proposal`, the owner's own `skill-proposal` issues in
adam-agentskills with a "Skill name:" line (draft_new_skill.py's rules).
Each carries EXACTLY source, repo, number, state, opened, count (from the
title, or None), target (a safe file path, `<n> files` or `agent-checks`
from a memory title; the skill name of a proposal) and a URL built here;
never a body or any other title text. None without the file. `lessons` is None
when neither the proposals directory nor the issues file is readable; with
only the issues, its `date`, `items` and `left_out` are None (unknown, not
empty). `finish` holds every item and issue to its keys.

THE PUBLIC DATA CONTRACT (2026-11-04) makes this document the single public data contract
of the Evals Explorer and the project dashboard, still `schema_version` 1:
the change only adds fields, so a reader of the earlier document keeps
working. `explorer/schema.json`
describes all of it, and `main` validates the document against it after
`finish` and before writing (no jsonschema: nothing is written). The new
sections are built in scripts/explorer_public.py, each from public inputs
only: `evals` (the dashboard's scored runs and summaries,
scripts/eval_facts.py, for listed subjects only), `hooks` (the git hook
check catalog, its weekly use with non-public repositories folded into one
bucket, and a verdict from evals/hook-policy.yml), `lesson_funnel` (lessons
by outcome), `activity` (pull requests, open issues and workflow runs in the
fleet owners' public repositories, `--activity`, named only when
`--public-repos` reads them `private: false`) and `spend` (weekly totals,
only with evals/public-export.yml `include_spend: true`). `finish` also
refuses any session, thread, message or trigger id anywhere, a repository in
`activity` or `hooks` that is not on the visibility list, and any row of a
new section with a field outside its key set.

PRIVATE MODE (`--subjects private`, 2026-11-04) builds the same schema for a
private registry's own dashboard, run inside that private repository on its
own results branch (adam-agentskills-private's explorer-private.yml writes
`explorer/private.json` there); its output must never be published. The
default, `--subjects public`, is the public document above, unchanged. In
private mode:

  * Every `--registry` must name a registry harness/registries.yml marks
    `private: true`, and at least one is required; `--out` may not be named
    `latest.json`. Either refusal exits 2 and writes nothing.
  * The subjects are those registries' skills, read from their checkouts
    (scripts/eval_coverage.py `enumerate_skills`, `count_fixtures` and
    `build_census`, `private_census`); no `coverage/latest.json` is read, and
    `plan_week.private_skills` is not subtracted, so `evals` covers them.
  * The public-only inputs (`--context-repo`, `--fire-runs`, `--fixture-queue`,
    `--lessons`, `--lesson-records`, `--lesson-issues`, `--draft-prs`,
    `--public-repos`, `--activity`, `--agent-checks`, `--lesson-funnel`,
    `--removal-state`) are
    refused, and `hooks`, `activity`, `lessons`, `lesson_funnel`,
    `fixture_queue`, `fires_without_results` and `spend` are null.
  * `source.repository` comes from `--source-repository` (the default,
    Adam-S-Daniel/skills-evals, is the public document's).
  * `finish` and `validate` still run.

Only paired skill runs are listed (a `with` and a `without` arm of one run
directory, fixture and model). A guidance run lists whichever of its modes
ran, except that a section's section-alone results (the `section` mode,
`alone_verdict`, and its alone cells in `current_text_runs`) are published
only when they factor into its decision: when its in-situ verdict is
`retire` (`alone_decides`), which is when harness/gates.py
`guidance_verdict` reads them, `shorten-or-merge` included (owner,
2026-11-03). The `none` mode is always kept: the page's whole-guidance
headline (full vs none) is a separate question and pools every section's
runs. A run left with no mode is not listed. Counts are per arm over the scored trials (infrastructure failures and
agent-errored trials are left out, as in the gate). Rates are not computed
here and nothing is rounded: the page rounds at display.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_made  # noqa: E402
import compute_gates  # noqa: E402
import draft_new_skill  # noqa: E402
import eval_coverage  # noqa: E402
import eval_facts  # noqa: E402
import explorer_public  # noqa: E402
import context as context_mod  # noqa: E402  (harness/, via compute_gates)
import gates  # noqa: E402  (harness/ is on sys.path via compute_gates)
import improve_outcomes  # noqa: E402
import lesson_evidence  # noqa: E402
import mine_sessions  # noqa: E402
import model_usage_census  # noqa: E402
import plan_week  # noqa: E402
import regression  # noqa: E402  (harness/, via compute_gates)
import retire_skill  # noqa: E402
import run_eval  # noqa: E402  (harness/, via compute_gates)
import skill_digest  # noqa: E402
import skill_usage  # noqa: E402
import stakes as stakes_mod  # noqa: E402
import timeweeks  # noqa: E402  (harness/)

SCHEMA_VERSION = 1
#: `source.repository` unless `--source-repository` names another.
DEFAULT_SOURCE_REPOSITORY = "Adam-S-Daniel/skills-evals"
#: Inputs only the public document reads; private mode refuses each.
PUBLIC_ONLY_FLAGS = ("context_repo", "fire_runs", "fixture_queue", "lessons", "lesson_records",
                     "lesson_issues", "draft_prs", "public_repos", "activity", "agent_checks",
                     "lesson_funnel", "removal_state")
SCHEMA_PATH = REPO_ROOT / "explorer" / "schema.json"
SHA_RE = re.compile(r"[0-9a-f]{40}")
#: A guidance pair's role in the gate -> the mode the page names it by.
MODE_NAMES = {("in_situ", "with"): "full", ("in_situ", "without"): "full_minus_section",
              ("alone", "with"): "section", ("alone", "without"): "none"}
#: The section-alone pair's own arm, published only when `alone_decides`. Its
#: control, `none`, is kept for the whole-guidance headline (full vs none).
ALONE_MODES = frozenset({MODE_NAMES[("alone", "with")]})
REGRESSION_MARKER = "skills-evals:regression:"
_URL_RE = re.compile(r"https?://\S+")
_DIGEST_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
#: #562: the loaded-copy window, in ISO weeks ending with the as-of week.
COPY_WEEKS = 2
#: A `skill-records` source read longer ago than this decides no alert.
COPY_SOURCE_DAYS = 14
_PREFIX_RE = re.compile(r"[0-9a-f]{12}")
_COPY_VALUE_RE = re.compile(r"[0-9a-f]{12}|unknown:(?:%s)"
                            % "|".join(map(re.escape, skill_usage.UNKNOWN_REASONS)))
_LONG_HEX_RE = re.compile(r"[0-9a-fA-F]{13,}")


class Refused(Exception):
    """The document would leak something the contract forbids."""


def iso(stamp: str | None) -> str | None:
    """`YYYYMMDDTHHMMSSZ` as `YYYY-MM-DDTHH:MM:SSZ`."""
    if stamp is None:
        return None
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"


def bare_version(versions: list) -> str | None:
    """`2.1.304` from `2.1.304 (Claude Code)`; None when unknown."""
    for value in versions:
        if isinstance(value, str) and value.split():
            return value.split()[0]
    return None


def arm_numbers(record: dict) -> dict | None:
    """One arm of one run reduced to the contract's counts, or None when no
    trial counted. Only scored trials count: an infrastructure failure or an
    agent-errored trial has no checks to add up (harness/gates.py
    `trial_record`)."""
    scored = [t for t in record["trials"] if t.get("scored")]
    if not scored:
        return None
    judges = [t["judge"] for t in scored if t.get("judge") is not None]
    costs = [t["cost_usd"] for t in scored if t.get("cost_usd") is not None]
    return {"trials": len(scored),
            "checks_passed": sum(sum(1 for ok in t["checks"].values() if ok) for t in scored),
            "checks_total": sum(len(t["checks"]) for t in scored),
            "judge_mean": sum(judges) / len(judges) if judges else None,
            "cost_usd": sum(costs) if costs else None}


def _newest_first(runs: list) -> list:
    return sorted(runs, key=lambda r: (r["at"], r["report_url"]), reverse=True)


def skill_runs(index: dict) -> dict:
    """{skill: [run entries, newest first]}: only runs with both arms
    counted, paired by run directory, fixture and requested model."""
    groups: dict = {}
    for record in index["runs"]:
        groups.setdefault((record["skill"], record["path"], record["fixture"],
                           record["model"]), {}).setdefault(record["role"], record)
    out: dict = {}
    for (skill, _path, fixture, model), arms in groups.items():
        numbers = {role: arm_numbers(arms[role]) for role in ("with", "without") if role in arms}
        if len(numbers) != 2 or None in numbers.values():
            continue
        first = arms["with"]
        out.setdefault(skill, []).append({
            "fixture": fixture, "model": model, "at": iso(first["timestamp"]),
            "cli_version": bare_version(first["cli_versions"] + arms["without"]["cli_versions"]),
            "with": numbers["with"], "without": numbers["without"],
            "report_url": gates._link(first["report"])["url"]})
    return {skill: _newest_first(runs) for skill, runs in out.items()}


#: A `remove` entry's heading in _agent-guidance's docs/guidance-impact.md,
#: as scripts/retire_skill.py `guidance_impact_entry` writes it.
REMOVED_HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — ([a-z0-9][a-z0-9-]{0,63}) — remove\s*$",
                                re.MULTILINE)
GUIDANCE_REPO_URL = "https://github.com/Adam-S-Daniel/_agent-guidance"
_NEXT_ENTRY_RE = re.compile(r"^## ", re.MULTILINE)


def _removal_pr_url(text: str, heading_end: int, repo: str) -> str | None:
    """The first pull request of `repo` that the entry body (the text after
    its heading up to the next `## ` line) names, as a full URL, or None: a
    pull request URL (so also a `[#N](URL)` link) or a bare `PR #N`; issue
    links never count."""
    nxt = _NEXT_ENTRY_RE.search(text, heading_end)
    body = text[heading_end:nxt.start() if nxt else len(text)]
    base = f"https://github.com/Adam-S-Daniel/{repo}"
    found = re.search(rf"{re.escape(base)}/pull/(\d+)(?!\d)|\bPR #(\d+)(?!\d)(?!\]\()", body)
    if found is None:
        return None
    return f"{base}/pull/{found.group(1) or found.group(2)}"


def removed_sections(guidance_dir: Path | None) -> list:
    """The guidance sections removed so far (#557: Adam, 2026-11-02, every
    removal tracked and reversible), newest first, from the `remove` entries
    of _agent-guidance's docs/guidance-impact.md: {"id", "date",
    "reverse_url"}, the last the removal pull request the entry names, else a
    search for a `retire-guidance/<id>` branch, whose Revert button restores
    it. [] without a checkout or that file."""
    if guidance_dir is None:
        return []
    try:
        text = (guidance_dir / "docs" / "guidance-impact.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out = [{"id": m.group(2), "date": m.group(1),
            "reverse_url": (_removal_pr_url(text, m.end(), "_agent-guidance")
                            or f"{GUIDANCE_REPO_URL}/pulls?q=is%3Apr+head%3Aretire-guidance%2F"
                               f"{m.group(2)}")}
           for m in REMOVED_HEADING_RE.finditer(text)]
    return sorted(out, key=lambda r: (r["date"], r["id"]), reverse=True)


#: A skill removal's heading in a registry's docs/skill-impact.md, as
#: scripts/retire_skill.py `impact_entry` writes it. cms-platform's headings
#: carry `cms-platform` in the plugin slot.
REMOVED_SKILL_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — ([a-z0-9-]+)/([a-z0-9][a-z0-9-]*) — remove\s*$",
                              re.MULTILINE)


def removed_skills(registries: dict | None) -> list:
    """The skills removed so far from the public registries (#557: Adam,
    2026-11-02, every removal tracked and reversible; 2026-11-13: every
    registry, not only adam-agentskills), newest first, from the `remove`
    entries of each `private: false` registry checkout's docs/skill-impact.md:
    {"name", "registry", "plugin", "date", "reverse_url"}, the last the
    removal pull request the entry names, else a search for a
    `retire-skill/<name>` branch in that registry's repository, whose Revert
    button restores it. A registry without a checkout or that file adds
    nothing."""
    out = []
    for registry, repo in sorted(public_registry_repos().items()):
        entry = (registries or {}).get(registry)
        # compute_gates.flag_registries' entries carry the checkout as `path`.
        root = entry.get("path") if isinstance(entry, dict) else entry
        if root is None:
            continue
        try:
            text = (Path(root) / "docs" / "skill-impact.md").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        name_of_repo = repo["repo"].split("/", 1)[-1]
        out += [{"name": m.group(3), "registry": registry, "plugin": m.group(2),
                 "date": m.group(1),
                 "reverse_url": (_removal_pr_url(text, m.end(), name_of_repo)
                                 or f"https://github.com/Adam-S-Daniel/{name_of_repo}/pulls"
                                    f"?q=is%3Apr+head%3Aretire-skill%2F{m.group(3)}")}
                for m in REMOVED_SKILL_RE.finditer(text)]
    return sorted(out, key=lambda r: (r["date"], r["name"], r["registry"]), reverse=True)


def mark_removed(skills: list, removed: list, registries: dict | None) -> None:
    """A skill listed in `removed` (same name and registry) whose registry
    checkout does not have it any more reads `removal: removed` with the
    removal pull request's link (in place), whatever its verdict: it was
    removed in its own registry, outside this repository's retire loop. A
    checkout that is absent, or still has the skill (restored since), leaves
    the subject alone: unknown is never "removed". An existing `removed`
    state (the loop's own merged removal pull request) stands."""
    newest = {}
    for row in removed:
        newest.setdefault((row["registry"], row["name"]), row)
    for subject in skills:
        row = newest.get((subject.get("registry"), subject["name"]))
        if row is None or (subject.get("removal") or {}).get("state") == "removed":
            continue
        entry = (registries or {}).get(row["registry"])
        root = entry.get("path") if isinstance(entry, dict) else entry
        if root is None or not Path(root).is_dir() \
                or any(Path(root).glob(f"**/{row['name']}/SKILL.md")):
            continue
        subject["removal"] = {"state": "removed", "url": row["reverse_url"], "since": row["date"]}


def guidance_runs(index: dict) -> dict:
    """{section: [run entries, newest first]}, each with the modes that ran."""
    groups: dict = {}
    for record in index["guidance_runs"]:
        mode = MODE_NAMES[(record["pair"], record["role"])]
        numbers = arm_numbers(record)
        if numbers is None:
            continue
        group = groups.setdefault((record["skill"], record["path"], record["fixture"],
                                   record["model"]), {"record": record, "modes": {}})
        group["modes"].setdefault(mode, numbers)
    out: dict = {}
    for (section, _path, fixture, model), group in groups.items():
        record = group["record"]
        out.setdefault(section, []).append({
            "fixture": fixture, "model": model, "at": iso(record["timestamp"]),
            "cli_version": bare_version(record["cli_versions"]),
            "modes": dict(sorted(group["modes"].items())),
            "report_url": gates._link(record["report"])["url"]})
    return {section: _newest_first(runs) for section, runs in out.items()}


def load_census(tree: Path) -> dict:
    """The coverage census, which is the privacy gate's only input."""
    try:
        doc = json.loads((tree / "coverage" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"no readable coverage census in the results tree: {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("registries"), list):
        raise ValueError("the coverage census has no registries list")
    return doc


def public_census(census: dict) -> tuple[dict, dict]:
    """({skill: census row} over the registries with `private: false`, the
    census totals over those registries). The first registry listing a name
    wins."""
    rows: dict = {}
    totals = {"covered": 0, "skipped": 0, "gap": 0, "total": 0}
    for registry in census["registries"]:
        if not isinstance(registry, dict) or registry.get("private") is not False:
            continue
        counts = registry.get("counts") or {}
        for key in totals:
            totals[key] += counts[key] if isinstance(counts.get(key), int) else 0
        for row in registry.get("skills") or []:
            if isinstance(row, dict) and isinstance(row.get("skill"), str):
                rows.setdefault(row["skill"], {**row, "registry": registry.get("name")})
    publication = census.get("publication")
    as_of = publication.get("as_of") if isinstance(publication, dict) else None
    return rows, {"as_of": as_of, **totals}


def private_registry_names() -> frozenset:
    """The registries harness/registries.yml marks `private: true`."""
    return frozenset(e["name"] for e in run_eval._load_registries_config()
                     if e.get("private") is True)


def private_census(registry_flags: list[str], evals_dir: Path) -> tuple[dict, dict]:
    """Private mode's subjects, in `public_census`' shape: ({skill: census
    row} over the `--registry` checkouts, which must all be private
    registries, the totals over them). Read from the checkouts with
    scripts/eval_coverage.py's own enumeration and fixture count, so no
    `coverage/latest.json` is needed; a skill with no fixture is a `gap` (the
    operator-held private skip file is not read here). ValueError when a
    registry is not private or none is given."""
    flagged = compute_gates.flag_registries(registry_flags)
    if not registry_flags or not flagged:
        raise ValueError("--subjects private needs a --registry NAME=PATH naming a private "
                         "registry checkout")
    if set(flagged) - private_registry_names():
        raise ValueError("--subjects private takes private registries only")
    if len(flagged) != len(registry_flags):
        raise ValueError("a --registry checkout given with --subjects private is not a directory")
    every = run_eval.resolve_registries(registry_flags, None, REPO_ROOT, None)
    try:
        fixtures = eval_coverage.count_fixtures(evals_dir, every)
        census = eval_coverage.build_census(flagged, fixtures, {})
    except eval_coverage.CensusRefusal as exc:
        raise ValueError(f"the private census refused: {exc}") from exc
    rows: dict = {}
    totals = {"covered": 0, "skipped": 0, "gap": 0, "total": 0}
    for registry in census["registries"]:
        for key in totals:
            totals[key] += registry["counts"][key]
        for row in registry["skills"]:
            rows.setdefault(row["skill"], {**row, "registry": registry["name"]})
    return rows, {"as_of": None, **totals}


def load_manifest(path: Path | None) -> list:
    if path is None:
        return []
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("the guidance manifest is not a list")
    return [r for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)]


_MARKER_RE = re.compile(re.escape(REGRESSION_MARKER) + r"(?:guidance:)?[A-Za-z0-9._-]+")


def issue_markers(listing: list) -> dict:
    """{marker: issue url} from `gh issue list --json url,body` rows. The
    bodies are untrusted text: only a marker pattern is read from one, and
    only a github.com URL is kept."""
    out: dict = {}
    for row in listing:
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            continue
        for marker in _MARKER_RE.findall(row.get("body") or ""):
            out.setdefault(marker, row["url"])
    return out


def regression_url(issues: dict, subject: str, name: str):
    marker = REGRESSION_MARKER + ("guidance:" if subject == "guidance" else "") + name
    url = issues.get(marker, issues.get(marker[len(REGRESSION_MARKER):]))
    return url if isinstance(url, str) and url.startswith("https://github.com/") else None


def build_alerts(gates_doc: dict, regressions: dict | None, issues: dict,
                 skill_names: set, section_ids: set, cells: list = ()) -> list:
    """Retire verdicts, regression rows and held scheduled cells, about listed
    subjects only. A held cell (plan_week.eval_cells) of a listed skill is a
    `not-schedulable` alert with its reason; a private cell is never one."""
    alerts = []
    for name, verdict in sorted(gates_doc["skills"].items()):
        if verdict["verdict"] == "retire" and name in skill_names:
            alerts.append({"kind": "retire", "subject": "skill", "name": name,
                           "text": f"{name} shows no measurable benefit and is due for "
                                   f"retirement: {verdict['reason']}.", "url": None})
    for name, verdict in sorted((gates_doc.get("guidance") or {}).items()):
        if verdict["verdict"] == "retire" and name in section_ids:
            alerts.append({"kind": "retire", "subject": "guidance", "name": name,
                           "text": f"The guidance section {name} shows no measurable benefit and "
                                   f"is due for retirement: {verdict['reason']}.", "url": None})
    for row in (regressions or {}).get("rows") or []:
        if not isinstance(row, dict) or row.get("verdict") not in ("regressed", "lost-delta"):
            continue
        subject, name = row.get("subject"), row.get("id")
        listed = skill_names if subject == "skill" else section_ids
        if subject not in ("skill", "guidance") or name not in listed:
            continue
        policy = ((regressions or {}).get("policy") or {}).get("skills" if subject == "skill" else "guidance")
        detail = regression.bad_detail(row, policy) if isinstance(policy, dict) else None
        alert = {"kind": "regression", "subject": subject, "name": name,
                 "model": row.get("model"), "fixture": row.get("fixture"),
                 "verdict": row["verdict"], **(detail or {}),
                 "text": f"{name} {row['verdict']}"
                         + (f" on {row['fixture']}" if row.get("fixture") else "")
                         + (f": {row['reason']}" if row.get("reason") else "") + ".",
                 "url": regression_url(issues, subject, name)}
        alerts.append(alert)
    for cell in cells:
        if cell.get("schedulable", True) or cell.get("hold_reason") not in ("no context", "null pin") \
                or cell["skill"] not in skill_names:
            continue
        alerts.append({"kind": "not-schedulable", "subject": "skill", "name": cell["skill"],
                       "model": cell["model"], "fixture": cell["fixture"],
                       "reason": cell["hold_reason"],
                       "text": f"The task {cell['fixture']} is not scheduled: "
                               f"{cell['hold_reason']}.", "url": None})
    return alerts


#: #545's re-pin cadence, not a noise filter. A consumer's skills.lock is bumped
#: every 1 to 3 days, and on 2026-11-02 the measured split was bimodal: a
#: fixture's in-scope entries had either just moved (0 days) or moved 10 to 30
#: days ago and stayed moved. 7 days sits in that gap, so the alert asks for a
#: re-pin about every 10 days instead of after every bump.
CONTEXT_DRIFT_DAYS = 7
_LOCK_FILE = "skills.lock"


class _Undecided(Exception):
    """A health check could not decide a fixture: it counts as unknown."""


def health_fixtures(evals_dir: Path, skill_names: set) -> list:
    """The HEALTH FILTER (#545), applied before any Git read or count:
    each scheduled fixture (an exact, committed `evals/scheduled.yml` entry)
    whose subject is a listed (public census) skill, that is not private
    (`fixture_hold_reason` and `private_skills`, so a private fixture whose
    skill name collides with a public one hides the name for both), and that
    has a `context:` mapping. [{fixture, skill, bundle, context}],
    in schedule order. A guidance or `subject: any` row is never a subject."""
    committed = plan_week.schedule.committed_fixtures(evals_dir.parent)
    scheduled = plan_week.schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    private = plan_week.private_skills(evals_dir)
    out = []
    for fixture in scheduled:
        directory = evals_dir.parent / fixture
        if plan_week.fixture_hold_reason(directory) == plan_week.HOLD_PRIVATE:
            continue
        try:
            doc = yaml.safe_load((directory / "fixture.yaml").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        doc = doc if isinstance(doc, dict) else {}
        skill = doc.get("skill")
        if doc.get("subject") in ("guidance", "any") or not isinstance(skill, str) \
                or skill not in skill_names or skill in private \
                or not isinstance(doc.get("context"), dict):
            continue
        out.append({"fixture": fixture, "skill": skill,
                    "bundle": doc["bundle"] if isinstance(doc.get("bundle"), str) else None,
                    "context": doc["context"]})
    return out


class _LockHistory:
    """The read-only Git reads #545 needs on a consumer checkout, kept apart
    from `context._Git` on purpose: that class's whitelist is the audited
    surface of frozen-context resolution and is never widened for a report.
    Same hardening (no ambient GIT_* override, no system or global config, no
    replace refs, no hooks) and its own closed list of argument shapes. A lock
    is read with `cat-file blob`, never `show`, so no textconv driver runs."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                        GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")

    @staticmethod
    def _allowed(args: tuple) -> bool:
        sha = context_mod._SHA.fullmatch
        return (args == ("rev-parse", "--is-shallow-repository")
                or (len(args) == 4 and args[:2] == ("merge-base", "--is-ancestor")
                    and bool(sha(args[2])) and bool(sha(args[3])))
                or (len(args) == 3 and args[:2] == ("rev-list", "--first-parent")
                    and bool(sha(args[2])))
                or (len(args) == 6 and args[:3] == ("rev-list", "--first-parent", "--reverse")
                    and args[4:] == ("--", _LOCK_FILE) and args[3].count("..") == 1
                    and all(sha(part) for part in args[3].split("..")))
                or (len(args) == 3 and args[:2] == ("cat-file", "blob")
                    and args[2].endswith(":" + _LOCK_FILE)
                    and bool(sha(args[2][:-len(_LOCK_FILE) - 1])))
                or (len(args) == 4 and args[:3] == ("show", "-s", "--format=%ct")
                    and bool(sha(args[3]))))

    def run(self, *args: str) -> subprocess.CompletedProcess:
        if not self._allowed(args):
            raise _Undecided("unsupported Git read")
        try:
            return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(self.path),
                                   *args], env=self.env, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except OSError as exc:
            raise _Undecided("git did not run") from exc

    def out(self, *args: str) -> bytes:
        result = self.run(*args)
        if result.returncode:
            raise _Undecided(f"git {args[0]} failed")
        return result.stdout


def _skills_map(raw: bytes) -> dict:
    """`skills.lock`'s {bundle/skill: digest}, through context._lock's checks."""
    return dict(context_mod._lock(raw)[0]["skills"])


def _subject_keys(skills: dict, skill: str, bundle: str | None) -> list:
    """The lock keys that adopt the subject, as delivery.resolve_skill_subject
    matches an adopted tree: the skill name, and the bundle when the fixture
    names one. Only the bundle matters here: an adopted subject's own bundle is
    the context #545 scopes to, whichever registry's main copy the run then
    tests."""
    return sorted(k for k in skills if k.split("/", 1)[1] == skill
                  and (bundle is None or k.split("/", 1)[0] == bundle))


def check_fixture_health(entry: dict, repositories: dict, now: datetime,
                         cache: dict) -> dict:
    """One in-scope fixture's #545 state. {"drift": "alert" | "ok" | "n/a" |
    "unknown", "drift_since": ISO time or None, "detail": the local report's
    row}. No lock at the pin is "n/a"; a lock that does not adopt the subject
    scopes to every bundle. Any read that cannot be made is "unknown", never a
    silent pass."""
    out = {"drift": "unknown", "drift_since": None,
           "detail": {"adopted": None, "scope": None, "changed": None, "added": None,
                      "removed": None, "drift_since": None}}
    ctx = entry["context"]
    try:
        context_mod.validate_context({"context": ctx}, entry["fixture"])
        identity = ctx["repository"]
        key = (identity, ctx["revision"])
        if key not in cache:
            try:
                git = context_mod._Git(identity, repositories)
                pin = git.revision(ctx["revision"])
                raw = git.read(git.tree(pin), _LOCK_FILE, optional=True)
                cache[key] = (git, pin, None if raw is None else _skills_map(raw))
            except context_mod.ContextError as exc:
                cache[key] = exc
        if isinstance(cache[key], Exception):
            return out
        git, pin, base = cache[key]
    except context_mod.ContextError:
        return out
    if base is None:
        out["drift"] = "n/a"
        return out
    adopted = _subject_keys(base, entry["skill"], entry["bundle"])
    if len(adopted) > 1:  # adopted under two bundles: delivery's ambiguous_skill
        return out
    out["detail"]["adopted"] = bool(adopted)
    scope = adopted[0].split("/", 1)[0] if adopted else None
    out["detail"]["scope"] = scope or "all bundles"

    def in_scope(skills: dict) -> dict:
        # The subject is never its own context: any bundle's copy of it is out.
        return {k: v for k, v in skills.items() if k.split("/", 1)[1] != entry["skill"]
                and (scope is None or k.split("/", 1)[0] == scope)}

    try:
        since = _drift_since(git, pin, in_scope, base, repositories[identity], cache)
    except (_Undecided, context_mod.ContextError):
        return out
    head = since.pop("head")
    pinned_scope = in_scope(base)
    out["detail"].update(
        changed=sum(1 for k in pinned_scope if k in head and head[k] != pinned_scope[k]),
        added=sum(1 for k in head if k not in pinned_scope),
        removed=sum(1 for k in pinned_scope if k not in head),
        drift_since=since["at"])
    out["drift_since"] = since["at"]
    if since["at"] is None:
        out["drift"] = "ok"
    else:
        moment = datetime.strptime(since["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        out["drift"] = "alert" if moment <= now - timedelta(days=CONTEXT_DRIFT_DAYS) else "ok"
    return out


def _drift_since(git, pin: str, in_scope, base: dict, path: Path, cache: dict) -> dict:
    """{"at": when the in-scope entries last left the pin's (None while HEAD
    still has them), "head": HEAD's in-scope entries}, or _Undecided. Walks
    the first-parent lock commits after the pin: the last one whose in-scope
    entries equal the pin's is where the context last matched, and the next
    lock commit is when it drifted, so a change that was reverted and made
    again dates from the second change. A shallow clone, a pin that is not a
    first-parent ancestor of HEAD, or an unreadable lock is undecided."""
    history = _LockHistory(path)
    if history.out("rev-parse", "--is-shallow-repository").strip() != b"false":
        raise _Undecided("shallow or unreadable repository")
    head = git.revision("HEAD")
    if history.run("merge-base", "--is-ancestor", pin, head).returncode:
        raise _Undecided("the pin is not an ancestor of HEAD")
    chain_key = ("first-parent", str(path), head)
    if chain_key not in cache:
        cache[chain_key] = frozenset(history.out("rev-list", "--first-parent", head)
                                     .decode("ascii").split())
    if pin not in cache[chain_key]:
        raise _Undecided("the pin is not on HEAD's first-parent chain")

    def lock_at(sha: str) -> dict:
        lock_key = ("lock", str(path), sha)
        if lock_key not in cache:
            cache[lock_key] = _skills_map(history.out("cat-file", "blob", f"{sha}:{_LOCK_FILE}"))
        return cache[lock_key]

    wanted = in_scope(base)
    head_scope = in_scope(lock_at(head))
    if head_scope == wanted:
        return {"at": None, "head": head_scope}
    commits = history.out("rev-list", "--first-parent", "--reverse", f"{pin}..{head}",
                          "--", _LOCK_FILE).decode("ascii").split()
    last_equal = -1
    for index, sha in enumerate(commits):
        if in_scope(lock_at(sha)) == wanted:
            last_equal = index
    if last_equal + 1 >= len(commits):
        raise _Undecided("HEAD's lock differs but no lock commit says when")
    stamp = history.out("show", "-s", "--format=%ct", commits[last_equal + 1]).strip()
    try:
        moment = datetime.fromtimestamp(int(stamp), tz=timezone.utc)
    except ValueError as exc:
        raise _Undecided("no committer time") from exc
    return {"at": plan_week._iso(moment), "head": head_scope}


def drift_evidence(entry: dict, runs: list, batch_skills, stakes_level: str,
                   now: datetime, digest: str | None) -> str:
    """"held" or "free": whether a drifted fixture's pin still has evidence in
    use. Owner policy (2026-11-13): a pin holds while its evidence is in use,
    and is re-pinned automatically only when the evidence would restart
    anyway, because a re-pin changes `fixture_digest` and every ingested run
    at the old pin stops pooling. `runs` is `compute_gates.build_index`'s
    "runs"; `digest` is `run_eval.fixture_digest` of the fixture directory.

    held   the digest is None (dirty or not in Git: never re-pin what cannot
           be measured), or the skill is a `kind: skill` member of the open
           batch (`batch_skills`), or the newest run at the current pin is
           younger than the re-check age (`plan_week.RECHECK_AFTER`, or
           RECHECK_AFTER_HIGH at stakes `high`).
    free   no run at the current pin, or the newest is older than that age
           (its evidence is due a re-check anyway)."""
    if digest is None or entry["skill"] in batch_skills:
        return "held"
    # The pooling's own naming: run_eval's positional rule, plus each old
    # name gates.FIXTURE_ALIASES pools into this fixture (the digest match
    # below is the alias's own check).
    name = run_eval.nested_fixture_name(Path(entry["fixture"]), entry["skill"]) or ""
    names = {name} | {old for (skill, old), target in gates.FIXTURE_ALIASES.items()
                      if skill == entry["skill"] and target == name}
    stamps = [plan_week._stamp_time(r["timestamp"]) for r in runs
              if r["skill"] == entry["skill"] and (r["fixture"] or "") in names
              and r["fixture_digest"] == digest]
    if not stamps:
        return "free"
    if None in stamps:
        return "held"
    age = plan_week.RECHECK_AFTER_HIGH if stakes_level == "high" else plan_week.RECHECK_AFTER
    return "free" if now - max(stamps) > age else "held"


def open_batch_skills(tree: Path) -> frozenset:
    """The skills that are `kind: skill` members of the open batch (empty
    with none). A malformed record raises plan_week.PlanError."""
    batch = plan_week.read_batch(tree)
    return frozenset(m["subject"] for m in (batch or {}).get("members", [])
                     if m["kind"] == "skill")


def health_alerts(evals_dir: Path, skill_names: set, repositories: dict | None,
                  now: datetime, runs: list | None = None, batch_skills=frozenset(),
                  stakes_level=lambda skill: "normal") -> tuple:
    """(alerts, context_drift_unknown, report rows, context_drift_held) over
    the HEALTH FILTER's fixtures only, so a private fixture moves no count.
    A fixture in `alert` state whose evidence is held (`drift_evidence`)
    emits no alert and is counted in the last element; `runs` None means no
    run is known, so every alerting fixture is free. Each row's `evidence` is
    held or free for an alerting fixture, else None."""
    alerts, rows, cache = [], [], {}
    drift_unknown = held_count = 0
    for entry in health_fixtures(evals_dir, skill_names):
        state = check_fixture_health(entry, repositories or {}, now, cache)
        drift_unknown += state["drift"] == "unknown"
        evidence = None
        if state["drift"] == "alert":
            evidence = "free" if runs is None else drift_evidence(
                entry, runs, batch_skills, stakes_level(entry["skill"]), now,
                run_eval.fixture_digest(evals_dir.parent / entry["fixture"]))
        rows.append({"fixture": entry["fixture"], "drift": state["drift"],
                     "evidence": evidence, **state["detail"]})
        if evidence == "held":
            held_count += 1
        elif evidence == "free":
            alerts.append({"kind": "context-drift", "subject": "skill", "name": entry["skill"],
                           "fixture": entry["fixture"], "model": None,
                           "repository": entry["context"]["repository"],
                           "drift_since": state["drift_since"]})
    return alerts, drift_unknown, rows, held_count


#: #555 (2026-11-02): the fire-runs window the workflow fetches and the
#: summary covers. A fire leaves it as it ages, which is a real change.
FIRE_WINDOW_DAYS = 14
#: Fires without results whose starts are at most this far apart are one
#: sweep (a routine-eval-weekly run dispatches its fires minutes apart).
FIRE_SWEEP_GAP = plan_week.OUTAGE_GAP
#: The fetch time is the workflow's own clock, so it is checked against the
#: build's wall clock (no later than this past it) and against the results
#: tip (no earlier than this before it): a stale or forged file is unknown.
FETCH_SKEW = timedelta(minutes=5)
FETCH_MAX_LAG = timedelta(days=1)


def load_fixture_queue(path: Path | None) -> dict | None:
    """scripts/fixture_queue.py's report, or None (unknown): no path, an
    unreadable file, or not a schema 1 report with its list and totals."""
    if path is None:
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(doc, dict) or doc.get("schema") != 1 or not all(
            isinstance(doc.get(k), list) for k in ("requests", "fixtures", "findings")) \
            or not isinstance(doc.get("totals"), dict):
        return None
    return doc


#: The lesson kinds the page lists, in its order (`lessons`).
LESSON_KINDS = ("new-skill", "skill-edit", "guidance-edit", "fixture-candidate")
LESSON_ITEM_KEYS = frozenset({"kind", "subject", "evidence_count", "first_seen",
                              "last_seen", "sources", "signals", "draft"})
#: The machine surfaces a record's `source` may name (mine_sessions.py
#: `--root LABEL=PATH`, `wsl` by default); any other label is `other`.
LESSON_SOURCES = frozenset({"wsl", "windows", "cloud"})
#: A records file larger than this is not read (records are one-line JSON).
MAX_RECORDS_FILE = 64 * 1024 * 1024
LESSON_LEFT_OUT = ("memory_note", "agent_check", "private", "other")
#: A generic tool subject from mine_sessions.py `cluster_subject`.
_TOOL_SUBJECT_RE = re.compile(r"tool-[a-z]+(-[a-z0-9-]+)?")
_RED_CI_RE = re.compile(r"red-ci-(?P<slug>[a-z0-9][a-z0-9-]*)")
_GUIDANCE_SUBJECT_RE = re.compile(r"guidance:(?P<id>[a-z0-9][a-z0-9-]{0,63})")
_DRAFT_HEAD_RE = re.compile(r"draft-skill/(?P<subject>[a-z0-9][a-z0-9:-]{0,127})")
DRAFT_PR_URL = "https://github.com/Adam-S-Daniel/adam-agentskills/pull/{number}"


def _lesson_day(value) -> str | None:
    """`value` when it is a real `YYYY-MM-DD` date, else None."""
    if not isinstance(value, str) or not lesson_evidence.DATE_RE.fullmatch(value):
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value


def repo_slugs(name: str) -> set:
    """The `red-ci-<slug>` forms of a repository name (`owner/` dropped):
    dots turned to dashes, and mine_sessions.py's `_slug` of it, which also
    drops a leading underscore (`_agent-guidance` -> `agent-guidance`)."""
    repo = name.rsplit("/", 1)[-1].lower()
    return {repo.replace(".", "-"),
            re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", repo)).strip("-")} - {""}


def load_draft_prs(path: Path | None) -> dict | None:
    """{subject: {"number", "state", "url"}} of adam-agentskills' newest
    `draft-skill/<subject>` pull request per subject, from `--draft-prs` (a
    list of {head, number, state: open|closed, merged: bool}), or None when
    the file is absent or not a list. A row off that shape is ignored; the
    URL is built here from the number, never copied."""
    if path is None:
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(rows, list):
        return None
    out: dict = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("head"), str):
            continue
        match = _DRAFT_HEAD_RE.fullmatch(row["head"])
        number, state, merged = row.get("number"), row.get("state"), row.get("merged")
        if (match is None or type(number) is not int or not 0 < number < 10 ** 9
                or state not in ("open", "closed") or type(merged) is not bool
                or (merged and state == "open")):
            continue
        subject = match["subject"]
        if subject in out and out[subject]["number"] >= number:
            continue
        out[subject] = {"number": number,
                        "state": "merged" if merged else state,
                        "url": DRAFT_PR_URL.format(number=number)}
    return out


def lesson_item(doc, public_skills: set, public_slugs: set,
                section_ids: set) -> tuple[str, dict | None]:
    """(bucket, item) for one proposal: bucket `item` with the public item,
    `skip` for a file off the schema, or a `left_out` key with None. Only
    the fields the item names are ever read."""
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 \
            or not isinstance(doc.get("kind"), str) or not isinstance(doc.get("subject"), str):
        return "skip", None
    kind, subject = doc["kind"], doc["subject"]
    if kind == "memory-note":
        return "memory_note", None
    if kind == "agent-check":
        return "agent_check", None
    count = doc.get("evidence_count")
    first, last = _lesson_day(doc.get("first_seen")), _lesson_day(doc.get("last_seen"))
    if type(count) is not int or not 1 <= count <= lesson_evidence.MAX_EVIDENCE \
            or first is None or last is None:
        return "skip", None
    bucket = "other"
    skill = lesson_evidence.SKILL_SUBJECT_RE.fullmatch(subject)
    section = _GUIDANCE_SUBJECT_RE.fullmatch(subject)
    red_ci = _RED_CI_RE.fullmatch(subject)
    if kind == "new-skill":
        if _TOOL_SUBJECT_RE.fullmatch(subject):
            bucket = "item"
        elif red_ci:
            bucket = "item" if red_ci["slug"] in public_slugs else "private"
    elif kind in ("skill-edit", "fixture-candidate") and skill:
        bucket = "item" if skill["name"] in public_skills else "private"
    elif kind in ("guidance-edit", "fixture-candidate") and section:
        bucket = "item" if section["id"] in section_ids else "other"
    if bucket != "item":
        return bucket, None
    item = {"kind": kind, "subject": subject, "evidence_count": count,
            "first_seen": first, "last_seen": last}
    if kind == "new-skill":
        item["draft"] = None
    return "item", item


def record_target(record) -> tuple[str, str] | None:
    """The (subject, kind) proposal mine_sessions.py `route` files a lesson
    record under, by route's own rules (`check_sketch`, `_kind`,
    `cluster_subject`): None for a usage record or one that stays a record.
    The excerpt and repository are read only here, in memory, through those
    functions, to tell which proposal a record belongs to; neither is kept."""
    if not isinstance(record, dict) or record.get("schema_version") != mine_sessions.SCHEMA:
        return None
    signal, subj = record.get("signal"), record.get("subject")
    if signal not in mine_sessions.LESSON_SIGNALS or not isinstance(subj, dict):
        return None
    skind, sname = subj.get("kind", "none"), subj.get("name", "")
    excerpt, repo = record.get("excerpt", ""), record.get("repo", "")
    if not all(isinstance(v, str) for v in (skind, sname, excerpt, repo)):
        return None
    subject = mine_sessions.subject_label({"kind": skind, "name": sname})
    if mine_sessions.check_sketch(excerpt):
        return subject, "agent-check"
    kind = mine_sessions._kind(signal, skind)
    if kind is not None:
        return subject, kind
    if skind == "none":
        cluster = mine_sessions.cluster_subject(
            {"signal": signal, "excerpt": excerpt, "repo": repo})
        if cluster:
            return cluster, "new-skill"
    return None


def lesson_origins(records_dir: Path | None) -> dict | None:
    """{(subject, kind): {"sources": Counter-like dict, "signals": dict}}
    over every lesson record under `records_dir` (`lessons/records/*.jsonl`),
    or None without a readable directory. Only `source` (allowlisted, else
    `other`) and `signal` are counted, once per `record_id` as route counts;
    no other field leaves this function."""
    if records_dir is None:
        return None
    try:
        paths = sorted(records_dir.glob("*.jsonl")) if records_dir.is_dir() else None
    except OSError:
        return None
    if paths is None:
        return None
    out: dict = {}
    seen: set = set()
    for path in paths:
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RECORDS_FILE:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except (ValueError, RecursionError):
                continue
            target = record_target(record)
            # route keeps the first record per record_id; the id is compared
            # in memory only, never kept past this function.
            rid = record.get("record_id") if target is not None else None
            if not isinstance(rid, str) or not rid or rid in seen:
                continue
            seen.add(rid)
            source = record.get("source")
            entry = out.setdefault(target, {"sources": set(), "signals": {}})
            entry["sources"].add(source if source in LESSON_SOURCES else "other")
            entry["signals"][record["signal"]] = entry["signals"].get(record["signal"], 0) + 1
    return out


#: The two owners the fleet spans; a memory promotion issue elsewhere is dropped.
FLEET_OWNERS = ("Adam-S-Daniel", "jodidaniel")
LESSON_ISSUE_KEYS = frozenset({"source", "repo", "number", "state", "opened", "count",
                               "target", "url"})
_REPO_RE = re.compile(r"(?P<owner>[A-Za-z0-9-]{1,39})/(?P<name>[A-Za-z0-9._-]{1,100})")
#: The memory curation routine's issue titles (_agent-guidance
#: docs/routines/memory-curation.md, step 4).
_MEMORY_TITLE_RE = re.compile(
    r"Memory promotion (?P<date>\d{4}-\d{2}-\d{2}): (?P<n>[0-9]{1,6}) "
    r"(?:(?:facts?) for (?:(?P<files>[0-9]{1,6}) files|(?P<file>\S+))|(?P<checks>agent-checks?))")
#: A file a memory promotion names: a relative path of plain segments.
_SAFE_PATH_RE = re.compile(r"(?!\.)(?!.*\.\.)[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+){0,7}")
ISSUE_URL = "https://github.com/{repo}/issues/{number}"


def _issue_core(row) -> dict | None:
    """The validated (number, state, opened) of an issue row, or None."""
    if not isinstance(row, dict):
        return None
    number, state, created = row.get("number"), row.get("state"), row.get("created_at")
    opened = _lesson_day(created[:10]) if isinstance(created, str) else None
    if type(number) is not int or not 0 < number < 10 ** 9 \
            or state not in ("open", "closed") or opened is None:
        return None
    return {"number": number, "state": state, "opened": opened}


def memory_issue(row) -> dict | None:
    """A published memory promotion item from one reduced search row
    ({repo, number, state, created_at, title, private}), or None: a
    repository that is not exactly `private: false`, outside the fleet's
    owners, or a title off the routine's shape. Only the count and the target
    are taken from the title."""
    core = _issue_core(row)
    if core is None or row.get("private") is not False or not isinstance(row.get("repo"), str) \
            or not isinstance(row.get("title"), str):
        return None
    repo = _REPO_RE.fullmatch(row["repo"])
    title = _MEMORY_TITLE_RE.fullmatch(row["title"].strip())
    if repo is None or repo["owner"] not in FLEET_OWNERS or title is None:
        return None
    if title["checks"]:
        target = "agent-checks"
    elif title["files"]:
        target = f"{int(title['files'])} files"
    else:
        target = title["file"] if _SAFE_PATH_RE.fullmatch(title["file"]) \
            and len(title["file"]) <= 120 else None
    return {"source": "memory", "repo": row["repo"], **core, "count": int(title["n"]),
            "target": target, "url": ISSUE_URL.format(repo=row["repo"], number=core["number"])}


def proposal_issue(row) -> dict | None:
    """A published skill proposal item from one `skill-proposal` issue row of
    adam-agentskills, or None: not the owner's own issue in that label, a pull
    request, or no valid "Skill name:" line (draft_new_skill.py's rules). The
    body is read here only for that line and is never published."""
    core = _issue_core(row)
    if core is None or "pull_request" in row:
        return None
    user, labels, body = row.get("user"), row.get("labels"), row.get("body")
    if (row.get("author_association") != "OWNER" or not isinstance(user, dict)
            or user.get("login") != draft_new_skill.ISSUE_OWNER or not isinstance(labels, list)
            or not any(isinstance(label, dict) and label.get("name") == draft_new_skill.ISSUE_LABEL
                       for label in labels)
            or not isinstance(body, str)):
        return None
    subject = draft_new_skill.issue_subject(body)
    if subject is None:
        return None
    repo = f"{draft_new_skill.ISSUE_OWNER}/{draft_new_skill.REGISTRY_NAME}"
    return {"source": "proposal", "repo": repo, **core, "count": None, "target": subject,
            "url": ISSUE_URL.format(repo=repo, number=core["number"])}


def load_lesson_issues(path: Path | None) -> list | None:
    """`lessons.issues` from `--lesson-issues` ({"memory": [rows], "proposals":
    [issue rows]}, written by explorer-data.yml), or None when the file is
    absent or not that shape. Bad rows are dropped."""
    if path is None:
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("memory"), list) \
            or not isinstance(doc.get("proposals"), list):
        return None
    items = {}
    for row, read in ([(r, memory_issue) for r in doc["memory"]]
                      + [(r, proposal_issue) for r in doc["proposals"]]):
        item = read(row)
        if item is not None:
            items[(item["repo"], item["number"])] = item
    # Memory first, then proposals; newest opened first; then repo and number.
    ordered = sorted(items.values(), key=lambda i: (i["repo"], i["number"]))
    ordered.sort(key=lambda i: i["opened"], reverse=True)
    ordered.sort(key=lambda i: i["source"] != "memory")
    return ordered


def build_lessons(proposals: Path | None, public_skills: set, public_slugs: set,
                  section_ids: set, drafts: dict | None,
                  origins: dict | None = None, issues: list | None = None) -> dict | None:
    """The document's `lessons`: the newest day's public proposals and the
    counts of what was left out, plus `issues` (`load_lesson_issues`' items,
    None without the file). Without a readable proposals directory `date`,
    `items` and `left_out` are None; with neither source, `lessons` is None."""
    day = lesson_evidence.newest_day(proposals) if proposals is not None else None
    if day is None:
        return None if issues is None else {"date": None, "items": None, "left_out": None,
                                             "issues": issues}
    left_out = dict.fromkeys(LESSON_LEFT_OUT, 0)
    items: dict = {}
    for path in sorted(day.glob("*.json")):
        try:
            if path.is_symlink() or not path.is_file() \
                    or path.stat().st_size > lesson_evidence.MAX_FILE:
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, RecursionError):
            continue
        bucket, item = lesson_item(doc, public_skills, public_slugs, section_ids)
        if bucket == "skip":
            continue
        if item is None:
            left_out[bucket] += 1
            continue
        key = (item["kind"], item["subject"])
        origin = None if origins is None else origins.get((item["subject"], item["kind"]))
        item["sources"] = None if origins is None else sorted((origin or {}).get("sources", ()))
        item["signals"] = (None if origins is None else
                           {k: v for k, v in sorted((origin or {}).get("signals", {}).items())})
        if key not in items or items[key]["evidence_count"] < item["evidence_count"]:
            if item["kind"] == "new-skill":
                item["draft"] = (drafts or {}).get(item["subject"])
            items[key] = item
    ordered = sorted(items.values(), key=lambda i: (LESSON_KINDS.index(i["kind"]),
                                                    -i["evidence_count"], i["subject"]))
    return {"date": day.name, "items": ordered, "left_out": left_out, "issues": issues}


def load_fire_runs(path: Path | None):
    """{"fetched_at": the wrapper's string, "runs": [run rows]} from
    `--fire-runs` (`{"fetched_at", "pages"}`, the pages of a slurped
    `gh api --paginate` over the runs API), or None when the file is absent,
    unreadable or not that shape. The file is UNTRUSTED: nothing in it is
    printed, and only the rows' fields `fire_counts` reads are ever used."""
    if path is None:
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("pages"), list):
        return None
    runs = []
    for page in doc["pages"]:
        if not isinstance(page, dict) or not isinstance(page.get("workflow_runs"), list):
            return None
        runs += page["workflow_runs"]
    return {"fetched_at": doc.get("fetched_at"), "runs": runs}


def fire_scope(evals_dir: Path, skill_names: set, section_ids: set) -> dict:
    """#555's SCOPE FILTER, applied before any fire is counted: {fixture
    path: ("skill", skill, fixture name or None) | ("guidance", section,
    fixture name)} over the exact, committed `evals/scheduled.yml` entries
    that are not private (`fixture_hold_reason`), whose skill is a listed
    (public census) one outside `private_skills`, or whose section is in the
    guidance manifest: `health_fixtures`' rules without its `context:`
    requirement. The subject comes from `plan_week._fixture_subject`, as
    eval_cells reads it, never from the directory name. A real-work row,
    unreadable fixture or other subject is out, so a private fire never
    moves a count."""
    committed = plan_week.schedule.committed_fixtures(evals_dir.parent)
    scheduled = plan_week.schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    private = plan_week.private_skills(evals_dir)
    out = {}
    for fixture in scheduled:
        if plan_week.fixture_hold_reason(evals_dir.parent / fixture) == plan_week.HOLD_PRIVATE:
            continue
        try:
            subject, ident = plan_week._fixture_subject(evals_dir, fixture)
        except (plan_week.PlanError, OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        parts = fixture.split("/")
        if subject == "skill" and ident in skill_names and ident not in private \
                and len(parts) in (2, 3):
            out[fixture] = ("skill", ident, parts[2] if len(parts) == 3 else None)
        elif subject == "guidance" and ident in section_ids:
            out[fixture] = ("guidance", ident, parts[3])
    return out


def _delivered(index: dict, target: tuple, model: str, start: datetime, end: datetime) -> bool:
    """A validated run of the fire's cell stamped in [start, end]. Skill and
    guidance records share `skill` (a guidance record's is the bare section
    id), so the run path tells them apart: a guidance run sits under
    `/guidance/<section>/`. Bare runs are left out: a bare fire is never
    counted, so a bare run never answers one."""
    kind, ident, name = target
    for record in (*index["runs"], *index["guidance_runs"]):
        path = "/" + record["path"] + "/"
        in_guidance = "/guidance/" in path
        if (kind == "guidance") != in_guidance or (
                kind == "guidance" and f"/guidance/{ident}/" not in path):
            continue
        if record["skill"] != ident or record["fixture"] != name or record["model"] != model:
            continue
        stamp = plan_week._stamp_time(record["timestamp"])
        if stamp is not None and start <= stamp <= end:
            return True
    return False


def _arrived(summaries: dict, target: tuple, model: str, start: datetime, end: datetime) -> bool:
    """An ingested routine folder (`routine-results/<run id>/`) holds an arm
    summary for the fire's fixture, stamped (the harness timestamp, key[2]) in
    [start, end]: results came back, valid or not. The summary's model
    (`cross_model.model`) and, for guidance, its `fixture_name` are read
    through compute_gates' bounded `_read` and must match when readable; an
    unreadable one matches on the fixture (guidance: the section) alone, so
    the count is then per fixture, not per cell. Guidance keys never carry
    the fixture (`_summaries` skips those that do)."""
    kind, ident, name = target
    key = f"guidance/{ident}" if kind == "guidance" else ident
    for (run_dir, subject, stamp_text, fixture, _arm), entry in summaries.items():
        if not run_dir.startswith("routine-results/") or subject != key:
            continue
        if kind == "skill" and fixture != name:
            continue
        stamp = plan_week._stamp_time(stamp_text)
        if stamp is None or not start <= stamp <= end:
            continue
        doc = compute_gates._read(entry["summary"]) if entry["summary"] else None
        if doc is not None:
            found = compute_gates.run_eval._arm_model([doc])
            if found is not None and found != model:
                continue
            if kind == "guidance" and isinstance(doc.get("fixture_name"), str) \
                    and doc["fixture_name"] != name:
                continue
        return True
    return False


def fire_counts(fires: dict | None, index: dict, summaries: dict, scope: dict,
                as_of: datetime, wall_clock: datetime):
    """#555's document-level `fires_without_results`, or None (unknown, never
    0) with no readable fire file or a `fetched_at` past the wall clock plus
    FETCH_SKEW or before `as_of` minus FETCH_MAX_LAG. `now` is `fetched_at`,
    so the result depends on the file and the tree, not on when it is built.

    A fire counts when its title passes improve_outcomes.parse_title (mode
    eval, not bare, a model: a model-less fire is skipped as the planner skips
    it), it concluded `success`, its target is in `scope` (`fire_scope`), it
    started inside the window and at least plan_week.FIRE_RESULT_WINDOW
    before `now`. A pair fire (`m1,m2`, plan_week's PAIR FIRES) counts once
    per model, as the planner judges each of its cells. Each counted fire is
    delivered (`_delivered` within the window after its start), rejected
    (results arrived, `_arrived`, but none validated) or without results.
    Only times and counts are published;
    dropped rows are counted to stderr by reason, never by title."""
    if fires is None:
        return None
    fetched = improve_outcomes.parse_time(fires.get("fetched_at"))
    if fetched is None or fetched > wall_clock + FETCH_SKEW or fetched < as_of - FETCH_MAX_LAG:
        return None
    now = fetched.astimezone(timezone.utc)
    oldest = now - timedelta(days=FIRE_WINDOW_DAYS)
    dropped: dict = {}
    seen, counted = set(), []
    for run in fires["runs"]:
        reason = None
        title = improve_outcomes.parse_title(run.get("display_title")) if isinstance(run, dict) else None
        start = improve_outcomes.parse_time(run.get("run_started_at") or run.get("created_at")) \
            if isinstance(run, dict) else None
        if title is None:
            reason = "not a fire row"
        elif not isinstance(run.get("id"), int) or run["id"] in seen:
            reason = "no id or a duplicate"
        elif title["mode"] != "eval" or title["bare"] or not title["model"]:
            reason = "not a paired eval fire with a model"
        elif run.get("conclusion") != "success" or start is None:
            reason = "not a successful fire"
        elif title["target"] not in scope:
            reason = "out of scope"
        elif not oldest <= start <= now - plan_week.FIRE_RESULT_WINDOW:
            reason = "outside the window"
        if reason:
            dropped[reason] = dropped.get(reason, 0) + 1
            continue
        seen.add(run["id"])
        # A pair fire (plan_week, PAIR FIRES) is a fire of each model's cell.
        counted += [(start.astimezone(timezone.utc), scope[title["target"]], model)
                    for model in improve_outcomes.title_models(title)]
    for reason, n in sorted(dropped.items()):
        print(f"explorer_data: fire rows dropped ({reason}): {n}", file=sys.stderr)
    without, rejected = [], 0
    for start, target, model in sorted(counted, key=lambda c: c[0]):
        end = start + plan_week.FIRE_RESULT_WINDOW
        if _delivered(index, target, model, start, end):
            continue
        if _arrived(summaries, target, model, start, end):
            rejected += 1
        else:
            without.append(start)
    # The chaining rule the planner reports outages with (plan_week.fire_sweeps):
    # one rule for both, so the two cannot drift apart.
    sweeps = [[s[0], s[-1], len(s)] for s in plan_week.fire_sweeps(without, FIRE_SWEEP_GAP)]
    return {"window_days": FIRE_WINDOW_DAYS,
            "since": plan_week._iso(min(c[0] for c in counted)) if counted else None,
            "counted": len(counted),
            "without_results": len(without), "rejected": rejected,
            "sweeps": [{"start": plan_week._iso(a), "end": plan_week._iso(b), "fires": n}
                       for a, b, n in sweeps]}


def skill_description(registries: dict | None, registry: str | None, name: str) -> str | None:
    """What the skill is for: the `description` in its SKILL.md front matter, in
    the census registry's checkout, whitespace collapsed. None when the checkout
    is absent, the skill has no single SKILL.md there, or it has no description.
    An `@` is dropped (a package name such as `@scope/pkg` reads the same
    without it), so a description never trips `finish`."""
    entry = (registries or {}).get(registry or "")
    if not entry or not compute_gates.run_eval._SKILL_NAME_RE.fullmatch(name):
        return None
    root = Path(entry["path"])
    matches = [p for p in sorted(root.glob(f"**/skills/{name}/SKILL.md"))
               if p.is_file() and not p.is_symlink()]
    if len(matches) != 1:
        return None
    try:
        text = matches[0].read_text(encoding="utf-8")
        if not text.startswith("---"):
            return None
        front = yaml.safe_load(text.split("---", 2)[1])
    except (OSError, UnicodeDecodeError, IndexError, yaml.YAMLError):
        return None
    desc = front.get("description") if isinstance(front, dict) else None
    if not isinstance(desc, str) or not desc.strip():
        return None
    return " ".join(desc.replace("@", "").split())


def alone_decides(verdict: dict) -> bool:
    """Whether a guidance section's section-alone results factor into its
    decision: its in-situ verdict is `retire`, the one case
    harness/gates.py `guidance_verdict` reads the alone cells (to make it
    `shorten-or-merge`). A verdict document without `in_situ_verdict` falls
    back on the section verdict, `retire` or `shorten-or-merge`."""
    in_situ = verdict.get("in_situ_verdict")
    if in_situ is not None:
        return in_situ == "retire"
    return verdict.get("verdict") in ("retire", "shorten-or-merge")


def without_alone(runs: list) -> list:
    """`runs` (`guidance_runs`' entries) with the section-alone arm
    (`section`) left out, and a run left with no mode dropped. `none` stays:
    the whole-guidance headline reads it."""
    out = []
    for run in runs:
        modes = {k: v for k, v in run["modes"].items() if k not in ALONE_MODES}
        if modes:
            out.append({**run, "modes": modes})
    return out


def current_text_runs(verdict: dict, alone: bool = True) -> int:
    """How many eval runs were made on the subject's CURRENT text: the with-arm
    run entries across its verdict cells (a guidance section's in-situ cells and,
    when `alone`, its `alone` cells). Only the with arm counts because `gates.pool_cells` keeps
    a with-arm run only when its `tested_digest` equals the subject's digest on
    main, so an edit empties it; a without-arm run pools across text changes and
    says nothing about the current text. A cell with no `with` key counts 0, and
    a subject with no verdict has 0.

    For a guidance section the meaning stays "runs on its current text" under
    either `rest_policy` (harness/gates.py, IN-SITU GUIDANCE CELLS): under
    `pooled-with-current-guard` an in-situ cell's with arm holds the runs on
    the section's current text beside EVERY rest of the guidance, so an edit
    to another section no longer empties it, while an edit to the section
    itself still does. How many of a cell's pairs are beside the current rest
    is the cell's own `current_rest_pairs`, not this count."""
    cells = list(verdict.get("cells") or [])
    if alone:
        cells += (verdict.get("alone") or {}).get("cells") or []
    return sum(len((c.get("runs") or {}).get("with") or []) for c in cells)


#: The objective keep routes `subject_confidence` reads: the cell's keep
#: test, and a pooled in-situ cell's keep test over the current rest alone
#: (harness/gates.py, THE POOLED KEEP; each pooled route's p is already
#: doubled, so `1 - m x min p` reads the cell's level either way).
KEEP_ROUTES = ("objective", "objective-current-rest")


def no_help_level(cell: dict) -> float:
    """A cell's no-help level: its objective's `no_help_confidence`, or for a
    pooled in-situ cell (`rest_guard`) the level its removal evidence
    reached, which is what decides its removal (the pooled adversarial
    round 3's m4). 0 when absent."""
    guard = cell.get("rest_guard")
    if isinstance(guard, dict):
        return guard.get("remove_evidence_confidence", 0.0)
    return (cell.get("objective") or {}).get("no_help_confidence", 0.0)


def subject_confidence(verdict: dict) -> dict:
    """How sure the gate is, as levels in [0, 1) of its betting tests
    (harness/gates.py, THE BOUNDS): `helps`, the subject's keep level, 1 - m
    x the smallest objective keep-test p over its cells and routes
    (`KEEP_ROUTES`; m its keep family, `keep_family`; 1 without one), and
    `no_help`, the lowest no-help level (`no_help_level`) over its cells
    with headroom (the cells that vote on removal: neither
    parked, `gates.PARKED_CLASSES`, nor `cannot-discriminate`; a cell with no objective figure
    gives 0). The judge does not vote, so it is not read. Both None while no
    cell has an objective figure. The keep and remove rules compare these
    with the policy levels; the page shows them as percentages.

    The page also draws how far each level is from its line, so four more
    keys carry the evidence behind them (each an int, or None when absent):
    `keep_pairs`, the objective pair count (a pooled in-situ cell's usable
    current-rest pairs, `rest_guard.usable_current_rest_pairs`, the count
    its chart row shows) of the cell `helps` comes from (the
    one with the smallest objective keep p); `no_help_pairs`, the pair count
    of the voting cell `no_help` comes from (the lowest no-help level);
    `max_pairs`, the largest objective pair count over figured cells (progress
    toward the per-cell run cap); and `keep_family`, the family size used for
    `helps`. All four are None while no cell has an objective figure.

    `cells` (the page's gain range chart) lists every cell of `verdict["cells"]`
    with an objective figure, by `confidence_cell`, sorted by model then task;
    [] when none has one. A guidance section's `alone` cells are not listed:
    they decide neither its keep nor its removal."""
    none = {"helps": None, "no_help": None, "keep_pairs": None,
            "no_help_pairs": None, "max_pairs": None, "keep_family": None, "cells": []}
    cells = verdict.get("cells") or []
    figured = [c for c in cells if isinstance(c.get("objective"), dict)]
    if not figured:
        return none

    def pairs_of(cell):
        # A pooled in-situ cell's pace is its current-rest pairs, the ones
        # its cap and its guard count (the pooled adversarial round 4's
        # m(b)), not every rest's pairs.
        if isinstance(cell.get("rest_guard"), dict):
            # The usable ones (the round 5 review's m4), the same count as
            # the gain chart's row (`rest_guard.current_objective`).
            n = cell["rest_guard"].get("usable_current_rest_pairs")
        else:
            n = (cell.get("objective") or {}).get("pairs")
        return n if isinstance(n, int) and not isinstance(n, bool) else None

    family = verdict.get("keep_family")
    family = family if isinstance(family, int) and family >= 1 else 1
    tests = [(t["p"], c) for c in cells for t in (c.get("keep_tests") or [])
             if isinstance(t, dict) and t.get("route") in KEEP_ROUTES
             and isinstance(t.get("p"), (int, float))]
    voting = [c for c in cells if c.get("class") not in gates.PARKED_CLASSES
              and c.get("class") != "cannot-discriminate"]
    levels = [(no_help_level(c), c) for c in voting]
    keep_p, keep_cell = min(tests, key=lambda t: t[0]) if tests else (None, None)
    weakest = min(levels, key=lambda t: t[0]) if levels else (None, None)
    all_pairs = [n for n in map(pairs_of, figured) if n is not None]
    return {"helps": max(0.0, 1 - family * keep_p) if tests else 0.0,
            "no_help": weakest[0],
            "keep_pairs": pairs_of(keep_cell) if keep_cell else None,
            "no_help_pairs": pairs_of(weakest[1]) if weakest[1] else None,
            "max_pairs": max(all_pairs) if all_pairs else None,
            "keep_family": family,
            "cells": sorted((row for row in map(confidence_cell, figured) if row is not None),
                            key=lambda r: (r["model"], r["task"] or ""))}


#: The keys of one `confidence.cells` row; `finish` holds every row to them.
CONFIDENCE_CELL_KEYS = frozenset({"model", "task", "pairs", "gain", "low", "high",
                                  "votes", "status"})

#: A cell's class as the page's range chart colors it; any other is "open".
CELL_STATUS = {"benefit": "keeps", "no-benefit": "removes-ready", "ceiling": "no-room",
               "ceiling-unconfirmed": "no-room", "paused": "paused"}


def confidence_cell(cell: dict) -> dict | None:
    """One row of the gain range chart from a verdict cell with an objective
    figure (harness/gates.py `sequence_block`), or None when a number is
    missing or not finite: `gain` the mean paired difference, `low` the keep
    test's lower end, `high` the remove test's upper end, each in percentage
    points of checks passed, clamped to [-100, 100] and rounded to one
    decimal only here; `votes` whether the cell votes on removal (neither
    parked nor `cannot-discriminate`); `status` from CELL_STATUS. A pooled
    cell (`rest_guard`) charts its current rest's own figures
    (`rest_guard.current_objective`, None with no current-rest pair), as
    its pace and confidence do, never the pooled block."""
    objective = cell["objective"]
    guard = cell.get("rest_guard")
    if guard is not None:
        current = guard.get("current_objective") if isinstance(guard, dict) else None
        objective = current if isinstance(current, dict) else {}
    numbers = [objective.get(k) for k in ("delta", "benefit_lower", "retire_upper")]
    pairs = objective.get("pairs")
    model = cell.get("model")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
               for v in numbers) or not isinstance(model, str) \
            or not isinstance(pairs, int) or isinstance(pairs, bool):
        return None
    # + 0.0 turns a rounded -0.0 into 0.0.
    gain, low, high = (round(min(100.0, max(-100.0, v * 100)), 1) + 0.0 for v in numbers)
    task = cell.get("fixture")
    return {"model": model, "task": task if isinstance(task, str) and task else None,
            "pairs": pairs, "gain": gain, "low": low, "high": high,
            "votes": cell.get("class") not in gates.PARKED_CLASSES
            and cell.get("class") != "cannot-discriminate",
            "status": CELL_STATUS.get(cell.get("class"), "open")}


#: A subject with one of these verdicts is being removed, so it gets no
#: re-check and its page says where the removal stands.
RETIRING = ("retire", "retire-pending")
#: The repositories a removal pull request comes from, by subject kind.
REMOVAL_REPOS = {"skill": ("Adam-S-Daniel/adam-agentskills", "Adam-S-Daniel/cms-platform",
                           "Adam-S-Daniel/adamdaniel.ai"),
                 "guidance": ("Adam-S-Daniel/_agent-guidance",)}
_REMOVAL_HEAD_RE = re.compile(r"retire-(?P<kind>skill|guidance)/(?P<subject>[A-Za-z0-9][A-Za-z0-9._:-]{0,127})")
_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T[0-9:.]+Z")
REMOVAL_PR_URL = "https://github.com/{repo}/pull/{number}"


def _removal_when(row: dict, *keys) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and _ISO_RE.fullmatch(value):
            return value
    return None


def load_removal_state(path: Path | None, repository: str = DEFAULT_SOURCE_REPOSITORY) -> dict | None:
    """`--removal-state`: {"prs": [...], "issues": [...]}, or None when the file
    is absent or unreadable (every removal is then "unknown", never guessed).

    A pull request row is {repo, number, head, state: open|closed, merged:
    bool, auto_merge: bool, created_at?, merged_at?, closed_at?, author?,
    labels?, closed_by?} (the last three decide whether the loop itself
    withdrew a closed one, as `retire_skill.loop_withdrawn` reads it) for a head
    `retire-skill/<skill>` (repo adam-agentskills, cms-platform or
    adamdaniel.ai) or `retire-guidance/<section>` (repo _agent-guidance).
    An issue row is {number, state: open|closed, labels: [names],
    body_markers: {target: skill|guidance, subject, kind: proposal|agent|
    withdrawal|legacy|null}, created_at?, closed_at?} for a skills-evals issue the
    bot opened with a `skills-evals:retire-skill:` or `retire-guidance:`
    marker. The result's rows are validated and keyed {(kind, subject):
    [row]}, and every URL is built here from the repo and number, never
    copied; a row off the shape is ignored."""
    if path is None:
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("prs"), list) \
            or not isinstance(doc.get("issues"), list):
        return None
    prs: dict = {}
    for row in doc["prs"]:
        if not isinstance(row, dict) or not isinstance(row.get("head"), str):
            continue
        match = _REMOVAL_HEAD_RE.fullmatch(row["head"])
        number, state, merged = row.get("number"), row.get("state"), row.get("merged")
        if (match is None or row.get("repo") not in REMOVAL_REPOS[match["kind"]]
                or type(number) is not int or not 0 < number < 10 ** 9
                or state not in ("open", "closed") or type(merged) is not bool
                or (merged and state == "open")):
            continue
        prs.setdefault((match["kind"], match["subject"]), []).append({
            "number": number, "state": state, "merged": merged,
            "url": REMOVAL_PR_URL.format(repo=row["repo"], number=number),
            # A pull request the loop withdrew is a pause, not a decline
            # (retire_skill.deciding); its rule is that function's.
            "withdrawn": retire_skill.loop_withdrawn(
                {"merged": merged, "author": row.get("author"),
                 "labels": row.get("labels"), "closed_by": row.get("closed_by")}),
            "since": _removal_when(row, "merged_at", "closed_at", "created_at")
            if state == "closed" else _removal_when(row, "created_at")})
    issues: dict = {}
    for row in doc["issues"]:
        if not isinstance(row, dict):
            continue
        markers, number, state = row.get("body_markers"), row.get("number"), row.get("state")
        labels = row.get("labels")
        if (not isinstance(markers, dict) or markers.get("target") not in ("skill", "guidance")
                or not isinstance(markers.get("subject"), str)
                or not _REMOVAL_HEAD_RE.fullmatch(f"retire-{markers['target']}/{markers['subject']}")
                or type(number) is not int or not 0 < number < 10 ** 9
                or state not in ("open", "closed") or not isinstance(labels, list)):
            continue
        kind = markers.get("kind")
        if kind == "withdrawal":
            continue  # the pause cap's notice, not a removal in flight
        issues.setdefault((markers["target"], markers["subject"]), []).append({
            "number": number, "state": state,
            # No stamp ("legacy") reads as a proposal, as retire_skill.issue_origin does.
            "proposal": kind in ("proposal", "legacy"),
            "labels": {x for x in labels if isinstance(x, str)},
            "url": ISSUE_URL.format(repo=repository, number=number),
            "since": _removal_when(row, "closed_at" if state == "closed" else "created_at",
                                   "created_at")})
    return {"prs": prs, "issues": issues}


def removal_of(kind: str, name: str, verdict, state: dict | None) -> dict | None:
    """Where a subject's removal stands: {"state", "url"?, "since"?}, or None
    for a subject that is not being removed. `state` is `load_removal_state`'s
    result (None: unknown). First match: a merged removal pull request
    (removed), an open one (pr-open), an open proposal issue the worker has
    not taken (owner: it waits on the owner), one labeled agent-blocked
    (blocked), one labeled agent-ready or agent-working (worker), then the
    verdict alone: retire-pending (waiting-turn), a closed issue or
    closed-unmerged pull request (declined), else queued for the bot's next
    daily run. A closed pull request the loop withdrew is a pause, so it
    reads queued, not declined. An open issue labeled `on-hold` is the
    owner's (`reason: on-hold`). A merged or closed removal only counts while the verdict is
    still a retire one, so a skill that came back is not shown as removed."""
    retiring = verdict in RETIRING
    if state is None:
        return {"state": "unknown"} if retiring else None
    prs = sorted(state["prs"].get((kind, name), []), key=lambda r: -r["number"])
    issues = sorted(state["issues"].get((kind, name), []), key=lambda r: -r["number"])
    opened = [i for i in issues if i["state"] == "open"]

    def found(label, row, reason=None):
        out = {"state": label, "url": row["url"]}
        if reason:
            out["reason"] = reason
        if row["since"]:
            out["since"] = row["since"]
        return out

    for row in prs:
        if row["merged"] and retiring:
            return found("removed", row)
    for row in prs:
        if row["state"] == "open":
            return found("pr-open", row)
    working = ("agent-ready", "agent-working")
    for row in opened:
        if "on-hold" in row["labels"]:
            return found("owner", row, "on-hold")
    for row in opened:
        if row["proposal"] and not row["labels"] & set(working):
            return found("owner", row, "proposal")
    for row in opened:
        if "agent-blocked" in row["labels"]:
            return found("blocked", row)
    for row in opened:
        if row["labels"] & set(working) or not row["proposal"]:
            return found("worker", row)
    if not retiring:
        return None
    if verdict == "retire-pending":
        return {"state": "waiting-turn"}
    declined = [r for r in prs if r["state"] == "closed" and not r["merged"]
                and not r["withdrawn"]] \
        + [r for r in issues if r["state"] == "closed"]
    if declined:
        return found("declined", max(declined, key=lambda r: (r["since"] or "", r["number"])))
    return {"state": "queued"}


def without_test(subjects: list) -> None:
    """A subject being removed (verdict retire or retire-pending) whose
    removal is in motion, done or unknown is not tested again, so it has no
    place in line and no re-check due (in place); the planner's rule
    (`plan_week.removal_frozen`) over the subject's `removal`, so a declined
    or owner-held removal keeps the next test the planner would plan. A
    removal that is done (`removed`) leaves nothing to test, so the subject
    has no band either and is not scheduled."""
    for subject in subjects:
        state = (subject.get("removal") or {}).get("state")
        if state == "removed":
            subject["next_test"] = {**subject["next_test"], "position": None, "band": None,
                                    "due": None, "scheduled": False}
        elif plan_week.removal_frozen(subject["verdict"], state):
            subject["next_test"] = {**subject["next_test"], "position": None, "due": None}


#: The eval bands the page lists as the test queue, in the planner's order
#: (plan_week.BANDS without its improve and bare bands).
QUEUE_BANDS = ("safety", "missing", "near", "focus", "recheck", "guidance-rest")


def test_queue(cells: list, model_weights: dict, now,
               guidance_policy: dict | None = None, batch: dict | None = None) -> dict:
    """{(kind, name): {"position", "band", "due"}} for every subject with a
    scheduled cell: `position` (1 = next) is the subject's first cell in the
    planner's eval bands, in `plan_week.allocate`'s order before the budget
    cuts it off; a subject with no cell in a band gets `due`, the earliest
    re-check of a cell the planner re-checks (newest run + plan_week.recheck_after), or
    neither when no test is planned. `scheduled` is False (from the caller)
    for a subject with no fixture on `evals/scheduled.yml`. The
    budget decides how far down the queue a sweep gets, so this is an order,
    not a date. `guidance_policy` (the verdict document's) sets the levels
    the planner's guidance focus is normalized by; open removal pull
    requests are not read here, so a section whose removal is open can
    still show a focus place the planner would not give it. `batch` is the
    published batch record (plan_week.BATCH_RECORD), or None: with one, only
    its members are queued in the bands the batch restricts, as the planner
    does while it is open."""
    # The focus's blocking rule reads every cell of a section, held ones too.
    ctx = {"cells": cells, "model_weights": model_weights, "removal_prs": [],
           "guidance_policy": guidance_policy,
           "reservation": 1.0, "overrun": 1.0, "points_per_usd": None,
           "batch": {"record": batch} if batch else None}
    cells = [c for c in cells if c.get("schedulable", True)]
    bands, _work = plan_week.eval_items(ctx, now)

    def key(cell_or_item):
        section = next((c["section"] for c in cells if c["fixture"] == cell_or_item["fixture"]
                        and c.get("section")), None)
        return ("guidance", section) if section else ("skill", cell_or_item["skill"])

    out, position = {}, 0
    for band in QUEUE_BANDS:
        for item in sorted(bands[band], key=lambda i: (*i["order"], i["cost"], i["fixture"],
                                                       i["model"], i["skill"])):
            subject = key(item)
            if subject not in out:
                position += 1
                out[subject] = {"position": position, "band": band, "due": None,
                                "scheduled": True}
    for cell in cells:
        subject = key(cell)
        newest = plan_week._stamp_time(cell["newest"])
        if subject in out and out[subject]["position"] is not None:
            continue
        entry = out.setdefault(subject, {"position": None, "band": None, "due": None,
                                         "scheduled": True})
        if newest is None or cell.get("stakes") == "none" \
                or (cell["class"] in ("missing", "insufficient") and cell.get("verdict") != "keep"):
            continue
        due = plan_week._iso(newest + plan_week.recheck_after(cell))
        if entry["due"] is None or due < entry["due"]:
            entry["due"] = due
    return out


def renumber(subjects: list) -> None:
    """Number the queued subjects of one list 1, 2, ... in queue order (in
    place), so a place in line counts only subjects the page lists: an
    unlisted (private) subject ahead in the planner's queue leaves no gap."""
    queued = sorted((s for s in subjects if s["next_test"]["position"] is not None),
                    key=lambda s: s["next_test"]["position"])
    for rank, subject in enumerate(queued, 1):
        subject["next_test"] = {**subject["next_test"], "position": rank}


def usage_counts(tree: Path) -> tuple:
    """({skill: invocations}, the window) from `usage/weekly-local.json`:
    every week of the file summed, so a skill the census never saw is 0 while
    the file exists. ({}, None) without a readable file (unknown, not zero).
    The census already folds every non-public name into `other`; the caller
    attaches a count only to a listed skill."""
    doc = skill_usage.load(tree / "usage" / "weekly-local.json")
    if doc is None:
        return {}, None
    counts = {}
    for row in doc["rows"]:
        if row["kind"] == "skill" and isinstance(row.get("invocations"), int):
            counts[row["name"]] = counts.get(row["name"], 0) + row["invocations"]
    source = next((s for s in doc["sources"] if s.get("scope") == "transcripts"), {})
    window = {"from": source.get("from"), "to": source.get("to"),
              "sessions_scanned": source.get("sessions_scanned"), "surface": source.get("surface")}
    return counts, window


def usage_digests(tree: Path) -> dict | None:
    """{"rows": skill-digest rows, "sources": {surface: skill-records source}}
    from `usage/weekly-local.json`; None without a readable file or without
    any skill-records source (copies unknown, not zero)."""
    doc = skill_usage.load(tree / "usage" / "weekly-local.json")
    if doc is None:
        return None
    sources = {s.get("surface"): s for s in doc["sources"]
               if s.get("scope") == skill_usage.DIGEST_SCOPE}
    if not sources:
        return None
    return {"rows": [r for r in doc["rows"] if r["kind"] == skill_usage.DIGEST_KIND],
            "sources": sources}


def public_registry_repos() -> dict:
    """{registry name: {"repo": canonical owner/repo, "layout": glob}} of
    the `private: false` registries in harness/registries.yml."""
    return {entry["name"]: {"repo": model_usage_census.github_repo(entry["url"]),
                            "layout": entry["layout"]}
            for entry in compute_gates.run_eval._load_registries_config()
            if entry["private"] is False and model_usage_census.github_repo(entry["url"])}


def main_history(checkout, layout: str, name: str, start: datetime) -> tuple | None:
    """(main's 12-hex prefix, every prefix main had in the window) for skill
    `name` in the registry checkout, or None when it cannot be told (no
    single copy at HEAD, a shallow checkout, any git failure). The window's
    prefixes are main's at the last first-parent commit before `start` plus
    at every first-parent commit since that touched the skill's path; a path
    that moved inside the window yields only its post-move digests, which can
    only make the alert louder, never quieter."""
    try:
        shallow = skill_digest.git_read(checkout, "rev-parse", "--is-shallow-repository")
        if shallow.returncode != 0 or shallow.stdout.strip() != b"false":
            return None
        relpath = skill_digest.skill_relpath(checkout, layout, name)
        main = skill_digest.tree_digest(checkout, "HEAD", relpath)[:12]
        before = skill_digest.git_read(
            checkout, "rev-list", "-1", "--first-parent",
            "--before=" + start.strftime("%Y-%m-%dT%H:%M:%SZ"), "HEAD")
        if before.returncode != 0:
            return None
        base = before.stdout.decode("ascii", "replace").strip()
        seen = {main}
        if base:
            try:
                seen.add(skill_digest.tree_digest(checkout, base, relpath)[:12])
            except OSError:
                pass  # the skill did not exist at the window's start
        since = skill_digest.git_read(checkout, "rev-list", "--first-parent",
                                      f"{base}..HEAD" if base else "HEAD", "--", relpath)
        if since.returncode != 0:
            return None
        for sha in since.stdout.decode("ascii", "replace").split():
            try:
                seen.add(skill_digest.tree_digest(checkout, sha, relpath)[:12])
            except OSError:
                continue  # the commit that deleted the path
        return main, seen
    except (OSError, ValueError, skill_digest.DigestRefused, skill_digest.DigestTooLarge):
        return None


def skill_copies(name: str, repo: str, digests: dict, history: tuple | None,
                 now: datetime) -> tuple[dict, list]:
    """(`copies` for one public skill, its `loaded-copy` alerts)."""
    mondays = sorted(skill_usage.week_monday(label)
                     for label in timeweeks.window_weeks(now, COPY_WEEKS))
    main, in_window = history if history is not None else (None, set())
    totals: dict = {}
    for row in digests["rows"]:
        if (row.get("name") == name and row.get("repo") == repo and row["week"] in mondays
                and isinstance(row.get("digest"), str)
                and _COPY_VALUE_RE.fullmatch(row["digest"])
                and isinstance(row.get("invocations"), int)):
            key = (row["digest"], row.get("surface"))
            totals[key] = totals.get(key, 0) + row["invocations"]
    loaded = []
    for (digest, surface), invocations in sorted(totals.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if not _PREFIX_RE.fullmatch(digest) or history is None:
            vs_main = "unknown"
        elif digest == main:
            vs_main = "current"
        else:
            vs_main = "in-window" if digest in in_window else "older"
        loaded.append({"digest": digest, "surface": surface, "invocations": invocations,
                       "vs_main": vs_main})
    alert, alerts = {}, []
    for surface in (skill_usage.SURFACE_LOCAL, skill_usage.SURFACE_CLOUD):
        alert[surface] = None
        source = digests["sources"].get(surface)
        read = skill_usage.parse_ts(source.get("to")) if source else None
        known = [e for e in loaded if e["surface"] == surface and _PREFIX_RE.fullmatch(e["digest"])]
        if (read is None or read > now or now - read > timedelta(days=COPY_SOURCE_DAYS)
                or not known or history is None):
            continue
        top = max(e["invocations"] for e in known)
        leading = sorted(e["digest"] for e in known if e["invocations"] == top)
        # A tie that includes any of main's in-window copies stays quiet.
        alert[surface] = not any(digest in in_window for digest in leading)
        if alert[surface]:
            alerts.append({"kind": "loaded-copy", "subject": "skill", "name": name,
                           "surface": surface, "loaded": leading[0], "main": main})
    return {"main": main, "window": {"from": mondays[0], "to": now.date().isoformat()},
            "loaded": loaded, "alert": alert}, alerts


def discarded_runs(verdict: dict) -> dict | None:
    """A subject's `discarded_runs` (harness/gates.py, DISCARDED RUNS): the
    recorded arm runs its current verdict does not count, by reason, with
    their agent cost. Counts, dollars and the fixed reason slugs only; None
    without a verdict (unknown, not zero)."""
    found = verdict.get("discarded_runs") if isinstance(verdict, dict) else None
    if not isinstance(found, dict):
        return None
    rows = {slug: {k: row[k] for k in ("runs", "cost_usd", "cost_unknown")}
            for slug, row in (found.get("by_reason") or {}).items()
            if slug in gates.DISCARD_REASONS}
    return gates.merge_discards({"by_reason": rows})


_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MODEL = re.compile(r"[a-z0-9][a-z0-9.-]*")


def _day(value):
    return value if isinstance(value, str) and _DAY.fullmatch(value) else None


def _model(value):
    return value if isinstance(value, str) and _MODEL.fullmatch(value) else None


def run_utility(verdict: dict) -> list | None:
    """A subject's `run_utility` (harness/gates.py, RUN UTILITY): its arm
    runs per (UTC day, arm model, class, reason) with their agent cost. Only
    days, model ids, the fixed classes and reason slugs, counts and dollars;
    None without a verdict (unknown, not zero)."""
    found = verdict.get("run_utility") if isinstance(verdict, dict) else None
    if not isinstance(found, list):
        return None
    rows = [{"date": _day(r.get("date")), "model": _model(r.get("model")),
             "class": r["class"], "reason": r.get("reason"),
             "runs": r["runs"], "cost_usd": r["cost_usd"], "cost_unknown": r["cost_unknown"]}
            for r in found
            if isinstance(r, dict) and r.get("class") in gates.UTILITY_CLASSES
            and (r.get("reason") is None or r.get("reason") in gates.DISCARD_REASONS)]
    return gates.merge_utility(rows)


def decisions(verdict: dict) -> list | None:
    """A subject's `decisions` (harness/gates.py, RUN UTILITY, CELL
    VERSIONS): per cell version, its fixture name, model, run days, class
    and decision day. None without a verdict."""
    found = verdict.get("decisions") if isinstance(verdict, dict) else None
    if not isinstance(found, list):
        return None
    out = []
    for d in found:
        if not isinstance(d, dict) or not _model(d.get("model")) \
                or not isinstance(d.get("class"), str) \
                or not re.fullmatch(r"[a-z-]+", d["class"]):
            continue
        fixture = d.get("fixture")
        out.append({"fixture": fixture if isinstance(fixture, str) else None,
                    "model": d["model"], "current": d.get("current") is True,
                    "from": _day(d.get("from")), "to": _day(d.get("to")),
                    "class": d["class"], "decided": _day(d.get("decided")),
                    "pair": d.get("pair") if d.get("pair") in ("in_situ", "alone") else None})
    return out


def fleet_discards(skills: list, sections: list) -> dict:
    """The document's `discarded_runs`: `discarded_runs` summed over the
    listed skills, the listed sections, and both (`all`). A subject with
    none (null) adds nothing."""
    of_skills = gates.merge_discards(*(s["discarded_runs"] for s in skills))
    of_sections = gates.merge_discards(*(s["discarded_runs"] for s in sections))
    return {"all": gates.merge_discards(of_skills, of_sections),
            "skills": of_skills, "guidance": of_sections}


def build(tree: Path, roster_path: Path, policy_path: Path, evals_dir: Path, as_of: str,
          repository_commit: str, results_commit: str, registries: dict | None = None,
          guidance_dir: Path | None = None, manifest: list | None = None,
          issues: dict | None = None, context_repos: dict | None = None,
          fire_runs: dict | None = None, wall_clock: datetime | None = None,
          fixture_queue: dict | None = None, lessons: Path | None = None,
          draft_prs: dict | None = None, lesson_records: Path | None = None,
          lesson_issues: list | None = None, visible_repos: frozenset | None = None,
          activity: Path | None = None, agent_checks_dir: Path | None = None,
          hook_policy: dict | None = None, spend: bool = False,
          lesson_funnel: Path | None = None, lesson_issues_path: Path | None = None,
          private_subjects: tuple | None = None,
          source_repository: str = DEFAULT_SOURCE_REPOSITORY,
          removal_state: dict | None = None) -> dict:
    """The public document. `fire_runs` is `load_fire_runs`' result (None:
    `fires_without_results` is unknown) and `wall_clock` the build's clock,
    used only to bound the fire file's `fetched_at` (#555). `fixture_queue`
    is `load_fixture_queue`'s result, carried as `fixture_queue`. `lessons`
    is the proposals directory and `draft_prs` `load_draft_prs`' result,
    which `build_lessons` turns into `lessons`, with each item's sources and
    signals counted from the records directory `lesson_records`, and
    `lesson_issues` (`load_lesson_issues`' result) as `lessons.issues`.

    The contract's added sections (scripts/explorer_public.py): `visible_repos` is the fleet
    owners' GitHub visibility list (None: unknown, so no repository is named
    in `hooks` and `activity` is None); `activity` the `--activity` file;
    `agent_checks_dir` _agent-guidance's templates/agent-checks/;
    `hook_policy` evals/hook-policy.yml; `spend` evals/public-export.yml's
    `include_spend`; `lesson_funnel` the `--lesson-funnel` file and
    `lesson_issues_path` the raw `--lesson-issues` file it shares.

    `private_subjects` is `private_census`' result, for PRIVATE MODE: the
    subjects come from it instead of the results tree's census, no private
    skill is subtracted, and the public-only sections are None.
    `source_repository` is `source.repository`. `removal_state` is
    `load_removal_state`'s result (None: each removal reads "unknown")."""
    private = private_subjects is not None
    compact = compute_gates.parse_as_of(as_of)
    gates_doc = compute_gates.compute(tree, roster_path, policy_path, evals_dir, compact,
                                      registries, guidance_dir)
    index = compute_gates.build_index(tree, evals_dir, compact)
    census_rows, coverage = (private_subjects if private
                             else public_census(load_census(tree)))
    roster = yaml.safe_load(roster_path.read_text(encoding="utf-8"))
    by_skill, by_section = skill_runs(index), guidance_runs(index)
    now = plan_week._stamp_time(compact)
    queue, cells = {}, []
    if (evals_dir / "scheduled.yml").is_file():
        cells = plan_week.eval_cells(evals_dir, gates_doc, [], now)
        try:
            batch = plan_week.read_batch(tree)
        except plan_week.PlanError:
            batch = None  # the planner stops on it; the page shows the unbatched queue
        queue = test_queue(cells, plan_week.model_weights(tree, gates_doc["roster_models"]), now,
                           gates_doc.get("guidance_policy"), batch)
    counts, usage_window = usage_counts(tree)
    unqueued = {"position": None, "band": None, "due": None, "scheduled": False}
    table = stakes_mod.load(evals_dir / "stakes.yml", evals_dir)

    def stakes_of(kind, name):
        entry = table.get((kind, name))
        return {"level": entry["stakes"], "reason": entry["reason"],
                "covered_by": entry["covered_by"]} if entry else {"level": "normal"}

    digests = usage_digests(tree)
    public_repos = public_registry_repos() if digests is not None else {}
    copy_alerts = []
    skills = []
    for name, row in sorted(census_rows.items()):
        copies = None
        public = public_repos.get(row["registry"])
        if digests is not None and public is not None:
            checkout = (registries or {}).get(row["registry"], {}).get("path")
            start = datetime.fromisoformat(min(
                skill_usage.week_monday(label) for label in
                timeweeks.window_weeks(now, COPY_WEEKS))).replace(tzinfo=timezone.utc)
            history = (main_history(checkout, public["layout"], name, start)
                       if checkout is not None else None)
            copies, found = skill_copies(name, public["repo"], digests, history, now)
            copy_alerts += found
        verdict = gates_doc["skills"].get(name) or {}
        skills.append({"name": name, "registry": row["registry"], "bundle": row.get("bundle"),
                       "description": skill_description(registries, row["registry"], name),
                       "status": row.get("status"), "skip_reason": row.get("reason"),
                       "verdict": verdict.get("verdict"), "verdict_reason": verdict.get("reason"),
                       "current_text_runs": current_text_runs(verdict),
                       "confidence": subject_confidence(verdict),
                       "next_test": queue.get(("skill", name), unqueued),
                       "stakes": stakes_of("skill", name),
                       "usage": None if usage_window is None
                       else {"invocations": counts.get(name, 0)},
                       "copies": copies,
                       "discarded_runs": discarded_runs(verdict),
                       "run_utility": run_utility(verdict),
                       "decisions": decisions(verdict),
                       "runs": by_skill.get(name, [])})

    for subject in skills:
        removal = removal_of("skill", subject["name"], subject["verdict"], removal_state)
        if removal:
            subject["removal"] = removal
    removed_list = removed_skills(registries)
    mark_removed(skills, removed_list, registries)
    without_test(skills)
    renumber(skills)

    guidance_verdicts = gates_doc.get("guidance") or {}
    rows = manifest or [{"id": s, "heading": s, "status": "covered"} for s in sorted(by_section)]
    sections = []
    for row in rows:
        verdict = guidance_verdicts.get(row["id"]) or {}
        # The section-alone results only when they factor into its decision.
        alone = alone_decides(verdict)
        runs = by_section.get(row["id"], [])
        sections.append({
            "id": row["id"], "heading": row.get("heading", row["id"]),
            "bytes": row.get("bytes"), "status": row.get("status"),
            "skip_reason": row.get("reason"), "verdict": verdict.get("verdict"),
            "verdict_reason": verdict.get("reason"),
            "current_text_runs": current_text_runs(verdict, alone),
            "alone_verdict": (verdict.get("alone") or {}).get("verdict") if alone else None,
            "confidence": subject_confidence(verdict),
            "next_test": queue.get(("guidance", row["id"]), unqueued),
            "stakes": stakes_of("guidance", row["id"]),
            "discarded_runs": discarded_runs(verdict),
            "run_utility": run_utility(verdict),
            "decisions": decisions(verdict),
            "runs": runs if alone else without_alone(runs)})

    for subject in sections:
        removal = removal_of("guidance", subject["id"], subject["verdict"], removal_state)
        if removal:
            subject["removal"] = removal
    without_test(sections)
    renumber(sections)

    try:
        regressions = json.loads((tree / "regressions" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        regressions = None
    alerts = build_alerts(gates_doc, regressions if isinstance(regressions, dict) else None,
                          issues or {}, {s["name"] for s in skills}, {s["id"] for s in sections}, cells)
    alerts += copy_alerts
    drift_unknown = drift_held = 0
    if (evals_dir / "scheduled.yml").is_file():
        try:
            batch_skills = open_batch_skills(tree)
        except plan_week.PlanError:
            batch_skills = frozenset()  # as the queue above: the unbatched view
        health, drift_unknown, _rows, drift_held = health_alerts(
            evals_dir, {s["name"] for s in skills}, context_repos, now, index["runs"],
            batch_skills, lambda skill: stakes_mod.level_of(table, "skill", skill))
        alerts += health
    fires = None
    if (evals_dir / "scheduled.yml").is_file():
        scope = fire_scope(evals_dir, {s["name"] for s in skills},
                           {r["id"] for r in (manifest or [])})
        fires = fire_counts(fire_runs, index, compute_gates._summaries(tree), scope, now,
                            wall_clock or datetime.now(timezone.utc))
    public_slugs = set(repo_slugs("Adam-S-Daniel/skills-evals"))
    for name in context_repos or {}:
        public_slugs |= repo_slugs(name)
    public_registries = public_registry_repos() if registries else {}
    for name in registries or {}:
        public = public_registries.get(name)
        if public is not None:
            public_slugs |= repo_slugs(name) | repo_slugs(public["repo"])
    listed_skills = {s["name"] for s in skills}
    if not private:
        listed_skills -= plan_week.private_skills(evals_dir)
    evals_doc = explorer_public.build_evals(tree, gates.RESULTS_BLOB, listed_skills,
                                            {s["id"] for s in sections}, spend and not private)
    if private:
        # The public-only sections: unknown here, never read.
        lesson_doc = hooks = funnel = activity_doc = fixture_queue = fires = None
        spend = False
    else:
        lesson_doc = build_lessons(
            lessons, listed_skills, public_slugs, {r["id"] for r in (manifest or [])},
            draft_prs, lesson_origins(lesson_records), lesson_issues)
        hooks = explorer_public.build_hooks(
            tree, now, agent_checks_dir, context_repos, visible_repos,
            hook_policy or dict(explorer_public.HOOK_POLICY_DEFAULTS))
        funnel = explorer_public.build_lesson_funnel(lesson_funnel, lesson_issues_path,
                                                     draft_prs, memory_issue, proposal_issue)
        activity_doc = explorer_public.build_activity(activity, visible_repos, now,
                                                      wall_clock or datetime.now(timezone.utc))
    stamps = [r["at"] for s in (*skills, *sections) for r in s["runs"]]
    policy = gates_doc["policy"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(compact),
        "newest_run": max(stamps, default=None),
        "source": {"repository": source_repository,
                   "repository_commit": repository_commit, "results_commit": results_commit},
        "roster": {"arms": [{"model": a["id"], "reason": a.get("reason")}
                            for a in roster["arms"]],
                   "judge": {"model": roster["judge"]["id"],
                             "reason": roster["judge"].get("reason")}},
        # max_runs_per_cell (2026-11-03) is absent from an older gates file.
        "policy": {**{k: policy[k] for k in ("benefit_confidence", "retire_confidence",
                                             "min_cli_versions", "objective_margin")},
                   "max_runs_per_cell": policy.get("max_runs_per_cell")},
        "skills": skills, "removed_skills": removed_list,
        "guidance": {"sections": sections, "removed": removed_sections(guidance_dir)},
        "discarded_runs": fleet_discards(skills, sections),
        "coverage": coverage, "alerts": alerts,
        "context_drift_unknown": drift_unknown,
        "context_drift_held": drift_held, "fires_without_results": fires,
        "fixture_queue": fixture_queue, "lessons": lesson_doc, "usage": usage_window,
        "evals": evals_doc, "hooks": hooks, "lesson_funnel": funnel, "activity": activity_doc,
        "spend": explorer_public.build_spend(tree, spend)}


def finish(doc: dict, public_repos: frozenset | None = None) -> str:
    """The document as text, or Refused: the last gate before it is public.
    `public_repos` is the visibility list the document was built with: every
    repository `activity` or `hooks` names must be on it (`hooks` may also say
    explorer_public.PRIVATE_BUCKET or null)."""
    text = json.dumps(doc, indent=1, sort_keys=True, allow_nan=False) + "\n"
    for forbidden in ("cse_", "session_"):
        if forbidden in text:
            raise Refused(f"the document contains {forbidden!r}")
    if explorer_public.FORBIDDEN_ID_RE.search(text):
        raise Refused("the document contains a session, thread, message or trigger id")
    if "@" in _URL_RE.sub("", text):
        raise Refused("the document contains an '@' outside a URL")
    if _DIGEST_RE.search(text):
        raise Refused("the document contains a 64-hex digest")
    # #562: the one place a digest prefix is allowed, held to its shape.
    for skill in doc.get("skills") or []:
        copies = skill.get("copies") if isinstance(skill, dict) else None
        if copies is None:
            continue
        values = [copies.get("main")] + [e.get("digest") for e in copies.get("loaded") or []]
        if any(v is not None and not (isinstance(v, str) and _COPY_VALUE_RE.fullmatch(v))
               for v in values) or _LONG_HEX_RE.search(json.dumps(copies)):
            raise Refused("a skill's copies carry a value that is not a prefix or a known reason")
    for alert in doc.get("alerts") or []:
        if isinstance(alert, dict) and alert.get("kind") == "loaded-copy":
            if (not all(isinstance(alert.get(k), str) and _PREFIX_RE.fullmatch(alert[k])
                        for k in ("loaded", "main"))
                    or _LONG_HEX_RE.search(json.dumps(alert))):
                raise Refused("a loaded-copy alert carries a value that is not a prefix")
    # The gain range chart's rows hold their fields only.
    for subject in [*(doc.get("skills") or []),
                    *((doc.get("guidance") or {}).get("sections") or [])]:
        rows = ((subject.get("confidence") or {}).get("cells")
                if isinstance(subject, dict) else None) or []
        if not isinstance(rows, list) or not all(
                isinstance(r, dict) and set(r) == CONFIDENCE_CELL_KEYS for r in rows):
            raise Refused("a confidence cell carries a field it may not publish")
    # The lessons come from private sessions: each item holds its fields only.
    lessons = doc.get("lessons")
    if lessons is not None:
        if not isinstance(lessons, dict) or set(lessons) != {"date", "items", "left_out", "issues"} \
                or (lessons["items"] is not None and (
                    not isinstance(lessons["left_out"], dict)
                    or set(lessons["left_out"]) != set(LESSON_LEFT_OUT)
                    or not isinstance(lessons["items"], list))) \
                or not isinstance(lessons["issues"], (list, type(None))):
            raise Refused("the lessons are not in their published shape")
        for issue in lessons["issues"] or []:
            if not isinstance(issue, dict) or set(issue) != LESSON_ISSUE_KEYS \
                    or issue["source"] not in ("memory", "proposal") \
                    or issue["url"] != ISSUE_URL.format(repo=issue["repo"], number=issue["number"]):
                raise Refused("a lesson issue carries a field it may not publish")
        for item in lessons["items"] or []:
            want = (LESSON_ITEM_KEYS if isinstance(item, dict) and item.get("kind") == "new-skill"
                    else LESSON_ITEM_KEYS - {"draft"})
            if not isinstance(item, dict) or set(item) != want:
                raise Refused("a lesson item carries a field it may not publish")
            sources, signals = item.get("sources"), item.get("signals")
            if (sources is not None and (not isinstance(sources, list) or not all(
                    v in LESSON_SOURCES | {"other"} for v in sources))) or (
                    signals is not None and (not isinstance(signals, dict) or not all(
                        k in mine_sessions.LESSON_SIGNALS and type(v) is int
                        for k, v in signals.items()))):
                raise Refused("a lesson's sources or signals are off their allowlists")
            draft = item.get("draft")
            if draft is not None and (not isinstance(draft, dict)
                                      or set(draft) != {"number", "state", "url"}):
                raise Refused("a lesson's draft carries a field it may not publish")
    _finish_contract(doc, public_repos or frozenset())
    return text


def _strings(value):
    """Every string in `value`, keys included (a number's digits are not a
    hex run)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _exact(rows, keys, what: str) -> None:
    if not isinstance(rows, list) or not all(isinstance(r, dict) and set(r) == set(keys)
                                             for r in rows):
        raise Refused(f"{what} carries a field it may not publish")


def _finish_contract(doc: dict, public: frozenset) -> None:
    """`finish`'s checks of the contract's added sections (scripts/explorer_public.py)."""
    pub = explorer_public
    evals = doc.get("evals")
    if evals is not None:
        _exact(evals.get("runs"), pub.RUN_KEYS, "an eval run")
        _exact(evals.get("bare_runs"), pub.BARE_KEYS, "a bare run")
        _exact(evals.get("latest"), eval_facts.LATEST_KEYS, "a latest eval row")
        if any(_LONG_HEX_RE.search(v) for v in _strings(evals)):
            raise Refused("an eval row carries a hex run longer than 12")
    hooks = doc.get("hooks")
    if hooks is not None:
        rows = [c for c in hooks.get("checks") or []]
        _exact(rows, ("name", "where", "repo", "source_url", "use", "window_totals", "verdict",
                      "verdict_reason", "overrides_measured"), "a hook check")
        cells = [u for c in rows for u in c["use"] or []]
        cells += [u for surface in (hooks.get("totals") or {}).values() for u in surface]
        _exact(cells, ("week", "surface", "repo", "invocations", "blocked", "overridden"),
               "a hook use row")
        for repo in [c["repo"] for c in rows] + [u["repo"] for u in cells]:
            if repo is not None and repo not in public and repo != pub.PRIVATE_BUCKET:
                raise Refused("a hook row names a repository that is not public")
            if repo == pub.PRIVATE_BUCKET and not hooks.get("private_repos_shown"):
                raise Refused("the private repos bucket is shown below its minimum")
    activity = doc.get("activity")
    if activity is not None:
        if not public:
            raise Refused("activity without a visibility list")
        for key, keys, url in (("pulls", pub.PR_KEYS, "https://github.com/{repo}/pull/{number}"),
                               ("issues", pub.ISSUE_KEYS, "https://github.com/{repo}/issues/{number}"),
                               ("runs", pub.RUN_ACTIVITY_KEYS,
                                "https://github.com/{repo}/actions/runs/{run_id}")):
            _exact(activity.get(key), keys, f"an activity {key[:-1]}")
            for row in activity[key]:
                if row["repo"] not in public:
                    raise Refused("activity names a repository that is not public")
                if row["url"] != url.format(**row):
                    raise Refused("an activity URL is not the one built for its row")
        if not set(activity.get("repos") or []) <= public:
            raise Refused("activity names a repository that is not public")
    spend = doc.get("spend")
    if spend is not None:
        if set(spend) != {"generated_at", "weeks", "total"}:
            raise Refused("spend carries a field it may not publish")
        _exact(spend["weeks"], pub.SPEND_WEEK_KEYS, "a spend week")
        if spend["total"] is not None:
            _exact([spend["total"]], pub.SPEND_TOTAL_KEYS, "the spend total")
    funnel = doc.get("lesson_funnel")
    if funnel is not None:
        counts = [v for k, v in funnel.items() if k in pub.OUTCOMES] + [
            v for c in (funnel.get("by_source") or {}).values() for v in c.values()]
        if set(funnel) != {*pub.OUTCOMES, "by_source", "sources_missing"} \
                or not all(type(v) is int for v in counts):
            raise Refused("the lesson funnel carries a field it may not publish")


def validate(doc: dict) -> None:
    """Refused unless `doc` validates against explorer/schema.json. Fails
    closed: without jsonschema nothing is written."""
    try:
        import jsonschema
    except ImportError as exc:
        raise Refused("jsonschema is not installed, so the document cannot be validated") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc),
                    key=lambda e: list(e.absolute_path))
    if errors:
        where = "/".join(map(str, errors[0].absolute_path)) or "(root)"
        raise Refused(f"the document does not match explorer/schema.json at {where}: "
                      f"{errors[0].validator} ({len(errors)} errors)")


def context_drift_report(argv: list[str]) -> int:
    """`context-drift-report`: the HEALTH FILTER's fixtures as a local table
    (fixture, adopted?, scope, changed/added/removed in-scope entries since
    the pin, drift_since). A tool for re-pinning by hand; CI never runs it,
    and it names bundles and counts the public document never carries."""
    parser = argparse.ArgumentParser(prog="explorer_data.py context-drift-report")
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--context-repo", action="append", metavar="OWNER/REPO=PATH")
    args = parser.parse_args(argv)
    try:
        now = plan_week._stamp_time(compute_gates.parse_as_of(args.as_of))
        names = set(public_census(load_census(args.results_tree))[0])
        compact = compute_gates.parse_as_of(args.as_of)
        index = compute_gates.build_index(args.results_tree, args.evals_dir, compact)
        table = stakes_mod.load(args.evals_dir / "stakes.yml", args.evals_dir)
        _alerts, _du, rows, _held = health_alerts(
            args.evals_dir, names, context_mod.parse_context_repos(args.context_repo), now,
            index["runs"], open_batch_skills(args.results_tree),
            lambda skill: stakes_mod.level_of(table, "skill", skill))
    except (ValueError, OSError, plan_week.PlanError, context_mod.ContextError) as exc:
        print(f"explorer_data: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    cols = ("fixture", "drift", "evidence", "adopted", "scope", "changed", "added", "removed",
            "drift_since")
    table = [cols] + [tuple("-" if r[c] is None else str(r[c]) for c in cols) for r in rows]
    widths = [max(len(line[i]) for line in table) for i in range(len(cols))]
    for line in table:
        print("  ".join(cell.ljust(w) for cell, w in zip(line, widths)).rstrip())
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["context-drift-report"]:
        return context_drift_report(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--guidance-manifest", type=Path, metavar="PATH",
                        help="_agent-guidance's agents-md/eval-coverage.yml")
    parser.add_argument("--guidance", type=Path, metavar="PATH",
                        help="an _agent-guidance checkout, passed to compute_gates")
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--regression-issues", type=Path, metavar="FILE",
                        help="JSON {marker: issue url}, or the raw `gh issue list --json url,body` "
                             "list, for the regression alerts")
    parser.add_argument("--context-repo", action="append", metavar="OWNER/REPO=PATH",
                        help="a consumer checkout (full history) for the #545 alert; "
                             "repeatable, as run_eval's flag")
    parser.add_argument("--fire-runs", type=Path, metavar="FILE",
                        help="{fetched_at, pages}: the slurped runs-API pages of "
                             "routine-eval-fire.yml (#555); absent or unreadable is unknown")
    parser.add_argument("--fixture-queue", type=Path, metavar="FILE",
                        help="scripts/fixture_queue.py's report; absent or unreadable "
                             "is unknown")
    parser.add_argument("--lessons", type=Path, metavar="DIR",
                        help="adam-agentskills-private's lessons/proposals/; absent or "
                             "unreadable is unknown")
    parser.add_argument("--lesson-records", type=Path, metavar="DIR",
                        help="adam-agentskills-private's lessons/records/, for each "
                             "lesson's sources and signals; absent is unknown")
    parser.add_argument("--lesson-issues", type=Path, metavar="FILE",
                        help="{memory: [rows], proposals: [issue rows]}: memory promotion "
                             "and skill-proposal issues; absent is unknown")
    parser.add_argument("--draft-prs", type=Path, metavar="FILE",
                        help="[{head, number, state, merged}] of adam-agentskills' pull "
                             "requests, for each new-skill lesson's draft")
    parser.add_argument("--public-repos", type=Path, metavar="FILE",
                        help="{repos: [{full_name, private}]}: the fleet owners' repositories "
                             "as GitHub lists them; absent is unknown (no repository named)")
    parser.add_argument("--activity", type=Path, metavar="FILE",
                        help="{fetched_at, pulls, issues, runs} of the public repositories; "
                             "absent or unreadable is unknown")
    parser.add_argument("--agent-checks", type=Path, metavar="DIR",
                        help="_agent-guidance's templates/agent-checks/, for the hook catalog")
    parser.add_argument("--hook-policy", type=Path, metavar="FILE",
                        default=REPO_ROOT / "evals" / "hook-policy.yml")
    parser.add_argument("--export-policy", type=Path, metavar="FILE",
                        default=REPO_ROOT / "evals" / "public-export.yml",
                        help="include_spend: whether `spend` is published")
    parser.add_argument("--lesson-funnel", type=Path, metavar="FILE",
                        help="{hook_proposals: [issue rows], lesson_check_prs: [{head, number, "
                             "state, merged}]}; absent is unknown")
    parser.add_argument("--removal-state", type=Path, metavar="FILE",
                        help="{prs: [...], issues: [...]}: removal pull requests and issues "
                             "(load_removal_state); absent is unknown")
    parser.add_argument("--subjects", choices=("public", "private"), default="public",
                        help="private: PRIVATE MODE, the --registry private registries' skills "
                             "(never published)")
    parser.add_argument("--source-repository", default=DEFAULT_SOURCE_REPOSITORY,
                        metavar="OWNER/REPO", help="the document's source.repository")
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--results-commit", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        for sha in (args.repository_commit, args.results_commit):
            if not SHA_RE.fullmatch(sha):
                raise ValueError("a commit is not a 40-character lowercase hex sha")
        private_subjects = None
        if args.subjects == "private":
            if args.out.name == "latest.json":
                raise ValueError("--subjects private may not write latest.json, the public "
                                 "document's name")
            given = [f"--{f.replace('_', '-')}" for f in PUBLIC_ONLY_FLAGS
                     if getattr(args, f) is not None]
            if given:
                raise ValueError(f"--subjects private does not read {', '.join(given)}")
            private_subjects = private_census(args.registry or [], args.evals_dir)
        public_repos = explorer_public.load_public_repos(args.public_repos)
        issues = (json.loads(args.regression_issues.read_text(encoding="utf-8"))
                  if args.regression_issues else {})
        if isinstance(issues, list):  # raw `gh issue list --json url,body`
            issues = issue_markers(issues)
        if not isinstance(issues, dict):
            raise ValueError("--regression-issues is not a JSON object or issue list")
        doc = build(args.results_tree, args.roster, args.policy, args.evals_dir,
                    args.as_of, args.repository_commit, args.results_commit,
                    compute_gates.flag_registries(args.registry), args.guidance,
                    load_manifest(args.guidance_manifest), issues,
                    context_mod.parse_context_repos(args.context_repo),
                    load_fire_runs(args.fire_runs), datetime.now(timezone.utc),
                    load_fixture_queue(args.fixture_queue), args.lessons,
                    load_draft_prs(args.draft_prs), args.lesson_records,
                    load_lesson_issues(args.lesson_issues), public_repos, args.activity,
                    args.agent_checks,
                    explorer_public.load_policy(args.hook_policy,
                                                explorer_public.HOOK_POLICY_DEFAULTS),
                    explorer_public.include_spend(args.export_policy),
                    args.lesson_funnel, args.lesson_issues, private_subjects,
                    args.source_repository,
                    load_removal_state(args.removal_state, args.source_repository))
        # The agent-made checks, skills and sections (_agent-guidance#451);
        # public mode only, since it dates subjects from public history.
        doc["agent_made"] = (
            agent_made.build(doc, args.guidance,
                             {n: e["path"] for n, e in
                              compute_gates.flag_registries(args.registry).items()},
                             load_manifest(args.guidance_manifest))
            if args.guidance is not None and private_subjects is None else None)
        text = finish(doc, public_repos)
        validate(doc)
    except Refused as exc:
        print(f"explorer_data: refusing to publish: {exc}", file=sys.stderr)
        return 2
    except (gates.GatePolicyError, ValueError, OSError, KeyError, RecursionError,
            yaml.YAMLError, context_mod.ContextError) as exc:
        print(f"explorer_data: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
