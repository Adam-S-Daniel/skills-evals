#!/usr/bin/env python3
"""Write `explorer/latest.json`: the public data behind the Skill Evals Explorer (#72).

  explorer_data.py --results-tree DIR --roster evals/roster.yml
                   --policy evals/gate-policy.yml --as-of TIME
                   --repository-commit SHA --results-commit SHA --out FILE
                   [--evals-dir DIR] [--guidance-manifest eval-coverage.yml]
                   [--guidance DIR] [--registry NAME=PATH ...]
                   [--regression-issues FILE] [--context-repo OWNER/REPO=PATH ...]
  explorer_data.py context-drift-report --results-tree DIR --as-of TIME
                   [--evals-dir DIR] [--registry NAME=PATH ...]
                   [--context-repo OWNER/REPO=PATH ...]

It reuses scripts/compute_gates.py for the validated run index
(`build_index`) and the verdicts (`compute`), then reshapes them for a page
that anyone can read. The document is PUBLIC, so what it leaves out matters
more than what it carries:

  * PRIVACY GATE. A skill is listed only if the census
    (`<results-tree>/coverage/latest.json`) names it in a registry with
    `private: false`. A skill with runs but no such census row (a private
    registry's skill, or a retired one) is dropped, and so is every alert
    about it. The census is the one source of what is public.
  * No session id, digest, harness commit, transcript or e-mail is ever
    copied from a run. `finish` is the last gate: it refuses (exit 2) a
    document containing a session-id prefix, an `@` outside a URL or a
    64-hex digest, so a future field added by mistake fails loudly instead
    of publishing.

Each skill and section also carries `confidence` (the levels its gate
bounds reach, `subject_confidence`) and `next_test` (its place in the
planner's eval queue or its next re-check, `test_queue`) and `stakes`
(its evals/stakes.yml level, `normal` with no row; scripts/stakes.py); each
skill carries
`usage`, its invocations in `usage/weekly-local.json`, whose window is the
top-level `usage` (None without a census: unknown, not zero).

Two report-only alerts watch the scheduled in-place skill fixtures (#544,
#545). Both see a fixture only after the HEALTH FILTER (`health_fixtures`):
an exact `evals/scheduled.yml` entry that is committed, a skill subject with a
public census row, not private (`plan_week.fixture_hold_reason` and
`plan_week.private_skills`), with a `context:` block. Each alert carries only
the kind, the skill, the fixture key, the public consumer repository and a
date; never a SHA, digest, path, count or a sibling skill's name.

  * `broken`, reason `pin-deploys-older-copy` (#544): the consumer's
    `skills.lock` at the fixture's pin adopts the skill, and its digest
    differs from the skill on main (`compute_gates.tested_digest`). The run
    then tests the old deployed copy, its with arm never pools
    (gates.pool_cells), and every fire is spent for nothing until a re-pin.
    `broken_unknown` counts the fixtures it could not decide.
  * `context-drift` (#545): the other skills deployed beside the subject (its
    own bundle when adopted, every bundle otherwise) moved on the consumer's
    default branch since the pin, and stayed moved for `CONTEXT_DRIFT_DAYS`.
    `drift_since` is the committer date of the lock commit that last left the
    pin's entries. `context_drift_unknown` counts the undecided fixtures.
    `context-drift-report` prints the per-fixture detail locally (never in CI).

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
import plan_week  # noqa: E402
import skill_usage  # noqa: E402
import stakes as stakes_mod  # noqa: E402

SCHEMA_VERSION = 1
SHA_RE = re.compile(r"[0-9a-f]{40}")
#: A guidance pair's role in the gate -> the mode the page names it by.
MODE_NAMES = {("in_situ", "with"): "full", ("in_situ", "without"): "full_minus_section",
              ("alone", "with"): "section", ("alone", "without"): "none"}
REGRESSION_MARKER = "skills-evals:regression:"
_URL_RE = re.compile(r"https?://\S+")
_DIGEST_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")


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


def removed_sections(guidance_dir: Path | None) -> list:
    """The guidance sections removed so far (#557: Adam, 2026-11-02, every
    removal tracked and reversible), newest first, from the `remove` entries
    of _agent-guidance's docs/guidance-impact.md: {"id", "date",
    "reverse_url"}, the last the section's removal pull requests, whose
    Revert button restores it. [] without a checkout or that file."""
    if guidance_dir is None:
        return []
    try:
        text = (guidance_dir / "docs" / "guidance-impact.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out = [{"id": section, "date": date,
            "reverse_url": (f"{GUIDANCE_REPO_URL}/pulls?q=is%3Apr+head%3Aretire-guidance%2F"
                            f"{section}")}
           for date, section in REMOVED_HEADING_RE.findall(text)]
    return sorted(out, key=lambda r: (r["date"], r["id"]), reverse=True)


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
#: The one reason #544's `broken` alert carries today.
REASON_OLDER_COPY = "pin-deploys-older-copy"
_LOCK_FILE = "skills.lock"


class _Undecided(Exception):
    """A health check could not decide a fixture: it counts as unknown."""


def health_fixtures(evals_dir: Path, skill_names: set) -> list:
    """The HEALTH FILTER (#544, #545), applied before any Git read or count:
    each scheduled fixture (an exact, committed `evals/scheduled.yml` entry)
    whose subject is a listed (public census) skill, that is not private
    (`fixture_hold_reason` and `private_skills`, so a private fixture whose
    skill name collides with a public one hides the name for both), and that
    has a `context:` mapping. [{fixture, skill, bundle, registry, context}],
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
                    "registry": doc.get("registry"), "context": doc["context"]})
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
    names one. The registry does not narrow it: run_eval's `_in_place_plan`
    passes a registry only when NO adopted tree matches, so an adopted copy is
    what a run tests whatever registry the fixture names."""
    return sorted(k for k in skills if k.split("/", 1)[1] == skill
                  and (bundle is None or k.split("/", 1)[0] == bundle))


def check_fixture_health(entry: dict, registries: dict, repositories: dict,
                         now: datetime, cache: dict) -> dict:
    """One in-scope fixture's #544 and #545 states. {"broken": "alert" | "ok" |
    "n/a" | "unknown", "drift": the same, "drift_since": ISO time or None,
    "detail": the local report's row}. No lock at the pin, or a lock that does
    not adopt the subject, is "n/a" for #544 (nothing deployed to be stale);
    #545 then scopes to every bundle. Any read that cannot be made is
    "unknown", never a silent pass."""
    out = {"broken": "unknown", "drift": "unknown", "drift_since": None,
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
        out["broken"] = out["drift"] = "n/a"
        return out
    adopted = _subject_keys(base, entry["skill"], entry["bundle"])
    if len(adopted) > 1:  # adopted under two bundles: delivery's ambiguous_skill
        return out
    out["detail"]["adopted"] = bool(adopted)
    if not adopted:
        out["broken"] = "n/a"
    else:
        pinned = context_mod._DIGEST.fullmatch(base[adopted[0]]).group(1).lower()
        main = compute_gates.tested_digest(registries or {}, entry["skill"], entry["registry"])
        if main is not None:
            out["broken"] = "alert" if pinned != main else "ok"

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


def health_alerts(evals_dir: Path, skill_names: set, registries: dict | None,
                  repositories: dict | None, now: datetime) -> tuple:
    """(alerts, broken_unknown, context_drift_unknown, report rows) over the
    HEALTH FILTER's fixtures only, so a private fixture moves no count."""
    alerts, rows, cache = [], [], {}
    broken_unknown = drift_unknown = 0
    for entry in health_fixtures(evals_dir, skill_names):
        state = check_fixture_health(entry, registries or {}, repositories or {}, now, cache)
        broken_unknown += state["broken"] == "unknown"
        drift_unknown += state["drift"] == "unknown"
        rows.append({"fixture": entry["fixture"], "broken": state["broken"],
                     "drift": state["drift"], **state["detail"]})
        if state["broken"] == "alert":
            alerts.append({"kind": "broken", "subject": "skill", "name": entry["skill"],
                           "fixture": entry["fixture"], "model": None,
                           "reasons": [REASON_OLDER_COPY]})
        if state["drift"] == "alert":
            alerts.append({"kind": "context-drift", "subject": "skill", "name": entry["skill"],
                           "fixture": entry["fixture"], "model": None,
                           "repository": entry["context"]["repository"],
                           "drift_since": state["drift_since"]})
    return alerts, broken_unknown, drift_unknown, rows


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
    confidence at which some cell's delta (objective or judge) is above 0, and
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
    return {"helps": max(helps), "no_help": min(no_help)}


#: The eval bands the page lists as the test queue, in the planner's order.
QUEUE_BANDS = ("safety", "missing", "near", "recheck")


def test_queue(cells: list, model_weights: dict, now) -> dict:
    """{(kind, name): {"position", "band", "due"}} for every subject with a
    scheduled cell: `position` (1 = next) is the subject's first cell in the
    planner's eval bands, in `plan_week.allocate`'s order before the budget
    cuts it off; a subject with no cell in a band gets `due`, the earliest
    re-check of a cell the planner re-checks (newest run + plan_week.recheck_after), or
    neither when no test is planned. `scheduled` is False (from the caller)
    for a subject with no fixture on `evals/scheduled.yml`. The
    budget decides how far down the queue a sweep gets, so this is an order,
    not a date."""
    cells = [c for c in cells if c.get("schedulable", True)]
    ctx = {"cells": cells, "model_weights": model_weights, "removal_prs": [],
           "reservation": 1.0, "overrun": 1.0, "points_per_usd": None}
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


def build(tree: Path, roster_path: Path, policy_path: Path, evals_dir: Path, as_of: str,
          repository_commit: str, results_commit: str, registries: dict | None = None,
          guidance_dir: Path | None = None, manifest: list | None = None,
          issues: dict | None = None, context_repos: dict | None = None) -> dict:
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
        queue = test_queue(cells, plan_week.model_weights(tree, gates_doc["roster_models"]), now)
    counts, usage_window = usage_counts(tree)
    unqueued = {"position": None, "band": None, "due": None, "scheduled": False}
    table = stakes_mod.load(evals_dir / "stakes.yml", evals_dir)

    def stakes_of(kind, name):
        entry = table.get((kind, name))
        return {"level": entry["stakes"], "reason": entry["reason"],
                "covered_by": entry["covered_by"]} if entry else {"level": "normal"}

    skills = []
    for name, row in sorted(census_rows.items()):
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
    broken_unknown = drift_unknown = 0
    if (evals_dir / "scheduled.yml").is_file():
        health, broken_unknown, drift_unknown, _rows = health_alerts(
            evals_dir, {s["name"] for s in skills}, registries, context_repos, now)
        alerts += health
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
        "skills": skills,
        "guidance": {"sections": sections, "removed": removed_sections(guidance_dir)},
        "coverage": coverage, "alerts": alerts, "broken_unknown": broken_unknown,
        "context_drift_unknown": drift_unknown, "usage": usage_window}


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
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--context-repo", action="append", metavar="OWNER/REPO=PATH")
    args = parser.parse_args(argv)
    try:
        now = plan_week._stamp_time(compute_gates.parse_as_of(args.as_of))
        names = set(public_census(load_census(args.results_tree))[0])
        _alerts, _bu, _du, rows = health_alerts(
            args.evals_dir, names, compute_gates.flag_registries(args.registry),
            context_mod.parse_context_repos(args.context_repo), now)
    except (ValueError, OSError, context_mod.ContextError) as exc:
        print(f"explorer_data: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    cols = ("fixture", "broken", "drift", "adopted", "scope", "changed", "added", "removed",
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
                        help="a consumer checkout (full history) for the #544/#545 alerts; "
                             "repeatable, as run_eval's flag")
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
                    context_mod.parse_context_repos(args.context_repo))
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
