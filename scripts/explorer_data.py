#!/usr/bin/env python3
"""Write `explorer/latest.json`: the public data behind the Evals Explorer (#72).

  explorer_data.py --results-tree DIR --roster evals/roster.yml
                   --policy evals/gate-policy.yml --as-of TIME
                   --repository-commit SHA --results-commit SHA --out FILE
                   [--evals-dir DIR] [--guidance-manifest eval-coverage.yml]
                   [--guidance DIR] [--registry NAME=PATH ...]
                   [--regression-issues FILE] [--context-repo OWNER/REPO=PATH ...]
                   [--fire-runs FILE] [--fixture-queue FILE]
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
    `source` are outside that scope).

Each skill and section also carries `confidence` (the levels its gate
bounds reach, `subject_confidence`) and `next_test` (its place in the
planner's eval queue or its next re-check, `test_queue`) and `stakes`
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
starts at most FIRE_SWEEP_GAP apart: start, end, count). Only fires on
the SCOPE FILTER's fixtures count (`fire_scope`: public, non-private,
scheduled skill fixtures and manifest guidance sections), so a private fire
moves nothing; no name, title or run id is published. None is unknown (no
readable fire file, or a `fetched_at` out of bounds), never 0. The per-cell
alert waits for #570.

`fixture_queue` (Adam, 2026-11-03) is scripts/fixture_queue.py's report,
`--fixture-queue`, carried as is: the fixture requests the weekly sweep
filed, the pull requests answering them, the fixtures they added (real fleet
work or invented, from each fixture's `origin:`) with their runs, pass rates
and cost, and the queue's findings. That script decides what it holds (issue
numbers, validated names, URLs, counts and dollars; never a title or body),
and `finish` checks it with the rest. None is unknown: no readable report,
or one that is not schema 1. Its own `generated_at` moves with every build,
so explorer-data.yml's publish step ignores it beside the document's.

Only paired skill runs are listed (a `with` and a `without` arm of one run
directory, fixture and model). A guidance run lists whichever of its modes
ran. Counts are per arm over the scored trials (infrastructure failures and
agent-errored trials are left out, as in the gate). Rates are not computed
here and nothing is rounded: the page rounds at display.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import context as context_mod  # noqa: E402  (harness/, via compute_gates)
import gates  # noqa: E402  (harness/ is on sys.path via compute_gates)
import improve_outcomes  # noqa: E402
import model_usage_census  # noqa: E402
import plan_week  # noqa: E402
import skill_digest  # noqa: E402
import skill_usage  # noqa: E402
import stakes as stakes_mod  # noqa: E402
import timeweeks  # noqa: E402  (harness/)

SCHEMA_VERSION = 1
SHA_RE = re.compile(r"[0-9a-f]{40}")
#: A guidance pair's role in the gate -> the mode the page names it by.
MODE_NAMES = {("in_situ", "with"): "full", ("in_situ", "without"): "full_minus_section",
              ("alone", "with"): "section", ("alone", "without"): "none"}
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


#: A skill removal's heading in adam-agentskills' docs/skill-impact.md, as
#: scripts/retire_skill.py `impact_entry` writes it.
REMOVED_SKILL_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — ([a-z0-9-]+)/([a-z0-9][a-z0-9-]*) — remove\s*$",
                              re.MULTILINE)
SKILL_REGISTRY = "adam-agentskills"


def removed_skills(registries: dict | None) -> list:
    """The skills removed so far from the public registry (#557: Adam,
    2026-11-02, every removal tracked and reversible), newest first, from
    the `remove` entries of its docs/skill-impact.md: {"name", "plugin",
    "date", "reverse_url"}, the last the removal pull request the entry names,
    else a search for a `retire-skill/<name>` branch, whose Revert button
    restores it. [] without that checkout or file."""
    entry = (registries or {}).get(SKILL_REGISTRY)
    # compute_gates.flag_registries' entries carry the checkout as `path`.
    root = entry.get("path") if isinstance(entry, dict) else entry
    if root is None:
        return []
    try:
        text = (Path(root) / "docs" / "skill-impact.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out = [{"name": m.group(3), "plugin": m.group(2), "date": m.group(1),
            "reverse_url": (_removal_pr_url(text, m.end(), SKILL_REGISTRY)
                            or f"https://github.com/Adam-S-Daniel/{SKILL_REGISTRY}/pulls"
                               f"?q=is%3Apr+head%3Aretire-skill%2F{m.group(3)}")}
           for m in REMOVED_SKILL_RE.finditer(text)]
    return sorted(out, key=lambda r: (r["date"], r["name"]), reverse=True)


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
        alert = {"kind": "regression", "subject": subject, "name": name,
                 "model": row.get("model"),
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


def health_alerts(evals_dir: Path, skill_names: set, repositories: dict | None,
                  now: datetime) -> tuple:
    """(alerts, context_drift_unknown, report rows) over the HEALTH FILTER's
    fixtures only, so a private fixture moves no count."""
    alerts, rows, cache = [], [], {}
    drift_unknown = 0
    for entry in health_fixtures(evals_dir, skill_names):
        state = check_fixture_health(entry, repositories or {}, now, cache)
        drift_unknown += state["drift"] == "unknown"
        rows.append({"fixture": entry["fixture"], "drift": state["drift"], **state["detail"]})
        if state["drift"] == "alert":
            alerts.append({"kind": "context-drift", "subject": "skill", "name": entry["skill"],
                           "fixture": entry["fixture"], "model": None,
                           "repository": entry["context"]["repository"],
                           "drift_since": state["drift_since"]})
    return alerts, drift_unknown, rows


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
    before `now`. Each counted fire is delivered (`_delivered` within the
    window after its start), rejected (results arrived, `_arrived`, but none
    validated) or without results. Only times and counts are published;
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
        counted.append((start.astimezone(timezone.utc), scope[title["target"]], title["model"]))
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


def current_text_runs(verdict: dict) -> int:
    """How many eval runs were made on the subject's CURRENT text: the with-arm
    run entries across its verdict cells (a guidance section's in-situ cells and
    its `alone` cells). Only the with arm counts because `gates.pool_cells` keeps
    a with-arm run only when its `tested_digest` equals the subject's digest on
    main, so an edit empties it; a without-arm run pools across text changes and
    says nothing about the current text. A cell with no `with` key counts 0, and
    a subject with no verdict has 0."""
    cells = list(verdict.get("cells") or [])
    cells += (verdict.get("alone") or {}).get("cells") or []
    return sum(len((c.get("runs") or {}).get("with") or []) for c in cells)


def subject_confidence(verdict: dict) -> dict:
    """How sure the gate is, as levels in [0, 1): `helps`, the highest
    confidence at which some cell's delta (objective or judge) is above 0
    (with a per-subject keep family, `keep_family`, the family's level), and
    `no_help`, the highest at which every cell's objective delta is under the
    margin (a cell with no objective figure gives 0). Both None while no
    cell has a figure. The keep and remove rules compare these with the policy levels;
    the page shows them as percentages."""
    cells = verdict.get("cells") or []
    if not cells:
        return {"helps": None, "no_help": None}
    helps = [d["helps_confidence"] for c in cells for d in (c.get("objective"), c.get("judge"))
             if isinstance(d, dict) and "helps_confidence" in d]
    no_help = [(c.get("objective") or {}).get("no_help_confidence", 0.0) for c in cells]
    if not helps:
        return {"helps": None, "no_help": None}
    family = verdict.get("keep_family")
    if isinstance(family, int) and family >= 1:
        # The keep is per subject (#557 follow-up): its level is 1 - m x the
        # smallest keep-test p, which crosses the keep level exactly when the
        # subject keeps.
        ps = [t["p"] for c in cells for t in (c.get("keep_tests") or [])
              if isinstance(t, dict) and isinstance(t.get("p"), (int, float))]
        if ps:
            return {"helps": max(0.0, 1 - family * min(ps)), "no_help": min(no_help)}
    return {"helps": max(helps), "no_help": min(no_help)}


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


def build(tree: Path, roster_path: Path, policy_path: Path, evals_dir: Path, as_of: str,
          repository_commit: str, results_commit: str, registries: dict | None = None,
          guidance_dir: Path | None = None, manifest: list | None = None,
          issues: dict | None = None, context_repos: dict | None = None,
          fire_runs: dict | None = None, wall_clock: datetime | None = None,
          fixture_queue: dict | None = None) -> dict:
    """The public document. `fire_runs` is `load_fire_runs`' result (None:
    `fires_without_results` is unknown) and `wall_clock` the build's clock,
    used only to bound the fire file's `fetched_at` (#555). `fixture_queue`
    is `load_fixture_queue`'s result, carried as `fixture_queue`."""
    compact = compute_gates.parse_as_of(as_of)
    gates_doc = compute_gates.compute(tree, roster_path, policy_path, evals_dir, compact,
                                      registries, guidance_dir)
    index = compute_gates.build_index(tree, evals_dir, compact)
    census_rows, coverage = public_census(load_census(tree))
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
                       "runs": by_skill.get(name, [])})

    renumber(skills)

    guidance_verdicts = gates_doc.get("guidance") or {}
    rows = manifest or [{"id": s, "heading": s, "status": "covered"} for s in sorted(by_section)]
    sections = []
    for row in rows:
        verdict = guidance_verdicts.get(row["id"]) or {}
        sections.append({
            "id": row["id"], "heading": row.get("heading", row["id"]),
            "bytes": row.get("bytes"), "status": row.get("status"),
            "skip_reason": row.get("reason"), "verdict": verdict.get("verdict"),
            "verdict_reason": verdict.get("reason"),
            "current_text_runs": current_text_runs(verdict),
            "alone_verdict": (verdict.get("alone") or {}).get("verdict"),
            "confidence": subject_confidence(verdict),
            "next_test": queue.get(("guidance", row["id"]), unqueued),
            "stakes": stakes_of("guidance", row["id"]),
            "runs": by_section.get(row["id"], [])})

    renumber(sections)

    try:
        regressions = json.loads((tree / "regressions" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        regressions = None
    alerts = build_alerts(gates_doc, regressions if isinstance(regressions, dict) else None,
                          issues or {}, {s["name"] for s in skills}, {s["id"] for s in sections}, cells)
    alerts += copy_alerts
    drift_unknown = 0
    if (evals_dir / "scheduled.yml").is_file():
        health, drift_unknown, _rows = health_alerts(
            evals_dir, {s["name"] for s in skills}, context_repos, now)
        alerts += health
    fires = None
    if (evals_dir / "scheduled.yml").is_file():
        scope = fire_scope(evals_dir, {s["name"] for s in skills},
                           {r["id"] for r in (manifest or [])})
        fires = fire_counts(fire_runs, index, compute_gates._summaries(tree), scope, now,
                            wall_clock or datetime.now(timezone.utc))
    stamps = [r["at"] for s in (*skills, *sections) for r in s["runs"]]
    policy = gates_doc["policy"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(compact),
        "newest_run": max(stamps, default=None),
        "source": {"repository": "Adam-S-Daniel/skills-evals",
                   "repository_commit": repository_commit, "results_commit": results_commit},
        "roster": {"arms": [{"model": a["id"], "reason": a.get("reason")}
                            for a in roster["arms"]],
                   "judge": {"model": roster["judge"]["id"],
                             "reason": roster["judge"].get("reason")}},
        "policy": {k: policy[k] for k in ("benefit_confidence", "retire_confidence",
                                          "min_cli_versions", "objective_margin")},
        "skills": skills, "removed_skills": removed_skills(registries),
        "guidance": {"sections": sections, "removed": removed_sections(guidance_dir)},
        "coverage": coverage, "alerts": alerts,
        "context_drift_unknown": drift_unknown, "fires_without_results": fires,
        "fixture_queue": fixture_queue, "usage": usage_window}


def finish(doc: dict) -> str:
    """The document as text, or Refused: the last gate before it is public."""
    text = json.dumps(doc, indent=1, sort_keys=True, allow_nan=False) + "\n"
    for forbidden in ("cse_", "session_"):
        if forbidden in text:
            raise Refused(f"the document contains {forbidden!r}")
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
    return text


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
        _alerts, _du, rows = health_alerts(
            args.evals_dir, names, context_mod.parse_context_repos(args.context_repo), now)
    except (ValueError, OSError, context_mod.ContextError) as exc:
        print(f"explorer_data: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    cols = ("fixture", "drift", "adopted", "scope", "changed", "added", "removed",
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
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--results-commit", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        for sha in (args.repository_commit, args.results_commit):
            if not SHA_RE.fullmatch(sha):
                raise ValueError("a commit is not a 40-character lowercase hex sha")
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
                    load_fixture_queue(args.fixture_queue))
        text = finish(doc)
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
