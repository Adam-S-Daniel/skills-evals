#!/usr/bin/env python3
"""The eval scope pass: decide which scheduled fixtures are worth running.

Adam, 2026-11-03: make the call on which fixtures and subjects deserve evals
autonomous and automatic, and run it often. This script is that call. `plan`
reads the committed schedule, the explorer document and the usage census and
writes the pauses and resumes the rules below produce; `apply` makes them in
the tree; `summary` renders a plan as Markdown. `.github/workflows/eval-scope.yml`
runs the three and opens one auto-merging pull request.

Rules, each deterministic (thresholds are the constants below):

  ceiling   a scheduled fixture with at least CEILING_MIN_RUNS runs after the
            fixture directory's last commit whose WITHOUT arm passes
            CEILING_SHARE of its checks on average, and (when the without arm
            has judge figures) scores at least CEILING_JUDGE. It cannot show a
            gain. Paused. Read per cell: every roster model's own runs must
            trip it, since the gate decides per model and a pooled mean can
            hide a model with room to gain.
  floor     the same run filter, both arms pass at most FLOOR_SHARE, again on
            every roster model's own runs. Paused.
  keep      neither ceiling nor floor pauses a subject whose explorer verdict
            is keep or whose confidence that it helps is at least KEEP_GUARD.
            The gate keeps a paused fixture's cells as parked `paused` cells
            (decided keep and no-benefit cells still count), so the guard is
            not needed for safety; it keeps a kept subject's fixtures measured.
  zero-use  a skill with no recorded use in real work over the census's
            CENSUS_WEEKS weeks (`skill_usage.has_recorded_use` is False: a
            fresh census that tracks the skill by name and counts no use).
            All of its scheduled fixtures are paused, `stakes: high` skills
            included, and they resume on its first recorded use. Adam,
            2026-11-13: "Do we/should we run evals on skills before they have
            been recorded used in real work? I think we should not." There is
            no exposure minimum (the earlier 500 full-listing sessions are
            for an irreversible removal, `harness/removal_policy.py`, not for
            pausing an eval that comes back). Unknown (a missing or stale
            census, an untracked skill) does nothing. A skill in
            evals/usage-unknown.yml keeps being evaluated and an earlier
            zero-use pause of it resumes: its use cannot be measured, so
            "no recorded use" says nothing about it, and the eval verdict is
            its only path to removal.
  removed   a skill fixture whose skill no longer exists in its registry
            (Adam, 2026-11-13: "remove it" acts with no approval, and the
            dashboard shows what happened). The skill's registry is the
            `registry` field of its explorer entry; its checkout is given with
            `--registry NAME=PATH` and its layout is harness/registries.yml's.
            Confirmed absent means: the checkout is a readable directory, the
            layout matches at least one skill there (so a sparse or empty
            checkout is never read as "everything was removed"), and none of
            the visible checkouts has the skill. All of its scheduled fixtures
            are paused. The fixtures are kept (Adam, 2026-11-12), and they
            resume when the skill is back. Unknown (no checkout, an
            unreadable one, an entry naming no registry) does nothing. This
            reads the checkout rather than the registry's `remove` entry in
            docs/skill-impact.md: the directory is what the eval would
            install, so a restored skill resumes with no entry to retract,
            and an entry written before its removal merges pauses nothing.
  resume    a fixture this pass paused earlier returns when its content digest
            differs from the one recorded at the pause, its subject is now
            kept, or its runs no longer trip the rule per model (ceiling,
            floor); when `has_recorded_use` is True (zero-use); or when the
            skill exists again (removed).

Never touched: fixtures of `stakes: high` subjects (by ceiling or floor; zero-use
does pause them), `draft: true` fixtures, and
any evals/unscheduled.yml row this pass did not write (a human decision
stands). Every pause is recorded in evals/scope-auto.yml with what resume
needs. A pause removes the path from evals/scheduled.yml and, for a skill
fixture, adds an evals/unscheduled.yml row whose reason starts "Auto scope (";
a resume reverses all of it.

Usage:
  eval_scope.py plan --repo-root . --explorer E.json --usage U.json \\
      [--registry-layout plugin_layout.json] [--registry NAME=PATH ...] \\
      --now ISO --out plan.json
  eval_scope.py apply --plan plan.json [--repo-root .]
  eval_scope.py summary --plan plan.json
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import skill_usage  # noqa: E402
import stakes as stakes_file  # noqa: E402

CEILING_MIN_RUNS = 4
CEILING_SHARE = 0.85
CEILING_JUDGE = 8.5
FLOOR_SHARE = 0.10
#: A subject whose explorer confidence that it helps is at least this, or
#: whose verdict is keep, is never paused for ceiling or floor. The gate keeps
#: a paused fixture's cells as parked `paused` cells (decided keep and
#: no-benefit cells still count), so this is not needed for safety; it keeps a
#: kept subject's fixtures measured.
KEEP_GUARD = 0.5
CENSUS_WEEKS = skill_usage.CENSUS_WEEKS
LOCAL_ONLY_PLUGINS = ("adam-coding-local", "adam-non-coding-local")
RULES = ("ceiling", "floor", "zero-use", "removed")
REGISTRIES_YML = REPO_ROOT / "harness" / "registries.yml"
AUTO_PREFIX = "Auto scope ("

SCHEDULED = "evals/scheduled.yml"
UNSCHEDULED = "evals/unscheduled.yml"
SCOPE_AUTO = "evals/scope-auto.yml"
#: Skills whose recorded use is not their real use (#668): zero use is unknown.
USAGE_UNKNOWN = "evals/usage-unknown.yml"
SCHEMA = 1

SCOPE_AUTO_HEADER = """\
# Fixtures the eval scope pass (scripts/eval_scope.py, eval-scope.yml) paused,
# with what it needs to bring each back. Adam, 2026-11-03: decide which
# fixtures are worth running automatically, and decide often.
#
# `rule` is ceiling, floor, zero-use or removed. `fixture_digest` is the sha256 of the
# fixture directory when it was paused (sorted relative paths and bytes): a
# ceiling or floor pause ends when the digest changes, a zero-use pause when
# the skill is used again, a removed pause when the skill exists again. `readiness` is the evals/scheduled.yml note, kept
# so a resume restores it. A skill fixture also has an evals/unscheduled.yml
# row whose reason starts "Auto scope ("; a guidance fixture has none.
# test/issues/test_issue_eval_scope.py holds the shape, and that no row's path
# is also scheduled. Edit by script, not by hand.
"""


class ScopeError(Exception):
    pass


# --- reading -------------------------------------------------------------


def _load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ScopeError(f"{path.name} could not be read as YAML") from exc


def read_rows(root: Path, rel: str, key: str) -> list[dict]:
    path = root / rel
    if not path.is_file():
        return []
    doc = _load_yaml(path)
    rows = doc.get(key) if isinstance(doc, dict) else None
    if rows is None:
        return []
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ScopeError(f"{rel}: `{key}` must be a list of mappings")
    return rows


def usage_unknown(root: Path) -> dict[str, str]:
    """{skill: reason} from USAGE_UNKNOWN; empty when the file is absent."""
    found = {}
    for row in read_rows(root, USAGE_UNKNOWN, "skills"):
        skill, reason = row.get("skill"), row.get("reason")
        if not isinstance(skill, str) or not skill or not isinstance(reason, str) or not reason:
            raise ScopeError(f"{USAGE_UNKNOWN}: each row needs a skill and a reason")
        found[skill] = reason
    return found


def fixture_digest(directory: Path) -> str:
    """sha256 over the sorted relative paths and bytes of every file under
    `directory`."""
    digest = hashlib.sha256()
    for file in sorted(p for p in directory.rglob("*") if p.is_file()):
        rel = file.relative_to(directory).as_posix()
        digest.update(len(rel.encode()).to_bytes(4, "big") + rel.encode())
        data = file.read_bytes()
        digest.update(len(data).to_bytes(8, "big") + data)
    return digest.hexdigest()


def last_commit_time(root: Path, rel: str) -> datetime | None:
    """Committer time of the newest commit touching `rel`, None when git does
    not know the path (no history, or an uncommitted directory)."""
    try:
        out = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cI", "--", rel],
                             capture_output=True, text=True, check=True, timeout=120).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not out:
        return None
    try:
        return datetime.fromisoformat(out)
    except ValueError:
        return None


def _parse_now(text: str) -> datetime:
    parsed = skill_usage.parse_ts(text)
    if parsed is None:
        raise ScopeError("--now must be an ISO 8601 time")
    return parsed


def _share(arm) -> float | None:
    if not isinstance(arm, dict):
        return None
    passed, total = arm.get("checks_passed"), arm.get("checks_total")
    if not isinstance(passed, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return None
    return passed / total


def _judge(arm) -> float | None:
    value = arm.get("judge_mean") if isinstance(arm, dict) else None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def subject_of(path: str) -> tuple[str, str]:
    """('guidance', section) for evals/guidance/<section>/..., else
    ('skill', skill) for evals/<skill>[/...]."""
    parts = path.split("/")
    if len(parts) >= 3 and parts[1] == "guidance":
        return "guidance", parts[2]
    return "skill", parts[1]


def _arms(kind: str, run: dict) -> tuple[dict | None, dict | None]:
    """(with-side arm, without-side arm) of one run: skills `with`/`without`,
    guidance `full`/`full_minus_section`."""
    if kind == "skill":
        return run.get("with"), run.get("without")
    modes = run.get("modes") if isinstance(run.get("modes"), dict) else {}
    return modes.get("full"), modes.get("full_minus_section")


def fixture_runs(explorer: dict, kind: str, name: str, path: str, since: datetime) -> list[dict]:
    """The subject's runs of the fixture at `path` made after `since`."""
    if kind == "skill":
        entries = [s for s in explorer.get("skills") or [] if isinstance(s, dict) and s.get("name") == name]
    else:
        entries = [s for s in (explorer.get("guidance") or {}).get("sections") or []
                   if isinstance(s, dict) and s.get("id") == name]
    out = []
    for entry in entries:
        for run in entry.get("runs") or []:
            if not isinstance(run, dict):
                continue
            fixture = run.get("fixture")
            where = (f"evals/guidance/{name}/{fixture}" if kind == "guidance"
                     else (f"evals/{name}/{fixture}" if fixture else f"evals/{name}"))
            at = skill_usage.parse_ts(run.get("at"))
            if where == path and at is not None and at > since:
                out.append(run)
    return out


def measure(kind: str, runs: list[dict]) -> dict:
    """What the ceiling and floor rules read from a fixture's filtered runs."""
    without = [(_share(_arms(kind, r)[1]), _judge(_arms(kind, r)[1])) for r in runs]
    without_shares = [s for s, _ in without if s is not None]
    judges = [j for s, j in without if s is not None and j is not None]
    both = [(_share(_arms(kind, r)[0]), _share(_arms(kind, r)[1])) for r in runs]
    both = [(a, b) for a, b in both if a is not None and b is not None]
    return {
        "without_runs": len(without_shares),
        "without_share": _mean(without_shares) if without_shares else None,
        "without_judge": _mean(judges) if judges else None,
        "both_runs": len(both),
        "with_share": _mean([a for a, _ in both]) if both else None,
        "both_without_share": _mean([b for _, b in both]) if both else None,
    }


def roster_models(explorer: dict) -> list[str]:
    """The roster's models from the explorer document, in roster order."""
    arms = (explorer.get("roster") or {}).get("arms") if isinstance(explorer.get("roster"), dict) else None
    return [a["model"] for a in arms or [] if isinstance(a, dict) and isinstance(a.get("model"), str)]


def per_model(kind: str, runs: list[dict], models: list[str]) -> tuple[str, str] | None:
    """(rule, why) when EVERY model's cell trips the same rule.

    The gate decides per cell (model), so a pooled mean can hide a model whose
    without arm still has room to show a gain. Every model in `models` (the
    roster; the models seen in `runs` when the roster is unknown) needs its
    own cell to trip the rule on its own runs.
    """
    groups: dict = {}
    for run in runs:
        groups.setdefault(run.get("model"), []).append(run)
    wanted = models or list(groups)
    if not wanted:
        return None
    found = [ceiling_or_floor(measure(kind, groups.get(model, []))) for model in wanted]
    rules = {f[0] if f else None for f in found}
    if len(rules) != 1 or None in rules:
        return None
    rule = rules.pop()
    if len(wanted) == 1:
        return found[0]
    why = "; ".join(f"{model or 'unknown model'}: {f[1].split(', so it')[0]}"
                    for model, f in zip(wanted, found))
    return rule, (f"on every roster model, {why}, so it cannot show a gain; it returns when "
                  "the fixture's content changes")


def protected(explorer: dict, kind: str, name: str) -> str | None:
    """Why `name` must not be paused for ceiling or floor, or None."""
    if kind == "skill":
        entries = [s for s in explorer.get("skills") or [] if isinstance(s, dict) and s.get("name") == name]
    else:
        entries = [s for s in (explorer.get("guidance") or {}).get("sections") or []
                   if isinstance(s, dict) and s.get("id") == name]
    for entry in entries:
        if entry.get("verdict") == "keep":
            return "its verdict is keep"
        helps = (entry.get("confidence") or {}).get("helps") if isinstance(
            entry.get("confidence"), dict) else None
        if isinstance(helps, (int, float)) and not isinstance(helps, bool) and helps >= KEEP_GUARD:
            return f"the confidence that it helps is {helps:.2f}"
    return None


def ceiling_or_floor(m: dict) -> tuple[str, str] | None:
    """(rule, why) when measurements trip the ceiling or the floor."""
    if m["without_runs"] >= CEILING_MIN_RUNS and m["without_share"] >= CEILING_SHARE and (
            m["without_judge"] is None or m["without_judge"] >= CEILING_JUDGE):
        judge = ("" if m["without_judge"] is None
                 else f" and the judge scored it {m['without_judge']:.1f}")
        return "ceiling", (f"the without arm passed {m['without_share']:.2f} of its checks{judge} "
                           f"over {m['without_runs']} runs since the fixture last changed, so it "
                           "cannot show a gain; it returns when the fixture's content changes")
    if (m["both_runs"] >= CEILING_MIN_RUNS and m["with_share"] <= FLOOR_SHARE
            and m["both_without_share"] <= FLOOR_SHARE):
        return "floor", (f"both arms passed at most {FLOOR_SHARE:.2f} of their checks "
                         f"(with {m['with_share']:.2f}, without {m['both_without_share']:.2f}) over "
                         f"{m['both_runs']} runs since the fixture last changed, so it cannot show "
                         "a gain; it returns when the fixture's content changes")
    return None


# --- removed skills ------------------------------------------------------


def registry_layouts(path: Path = REGISTRIES_YML) -> dict[str, str]:
    """{registry name: layout glob} from harness/registries.yml."""
    doc = _load_yaml(path)
    rows = doc.get("registries") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        raise ScopeError("harness/registries.yml has no registries list")
    return {r["name"]: r["layout"] for r in rows
            if isinstance(r, dict) and isinstance(r.get("name"), str)
            and isinstance(r.get("layout"), str) and r["layout"].endswith("/*/SKILL.md")}


def parse_registry_flags(values: list[str] | None) -> dict[str, Path]:
    out = {}
    for value in values or []:
        name, sep, path = value.partition("=")
        if not sep or not name or not path:
            raise ScopeError("--registry must be NAME=PATH")
        out[name] = Path(path)
    return out


def skill_exists(skill: str, registry: str | None, checkouts: dict[str, Path],
                 layouts: dict[str, str]) -> bool | None:
    """True when a visible checkout has the skill, False when it is confirmed
    gone from its registry, None when that cannot be told (no checkout for the
    skill's registry, an unreadable or skill-less one, an unknown layout or
    registry): unknown must never pause anything."""
    if not skill or "/" in skill or skill.startswith("."):
        return None

    def probe(name: str):
        root, layout = checkouts.get(name), layouts.get(name)
        if root is None or layout is None or not root.is_dir():
            return None
        try:
            base = layout[: -len("*/SKILL.md")]
            if not any(root.glob(base + "*/SKILL.md")):
                return None  # an empty or sparse checkout says nothing
            return any(p.is_file() for p in root.glob(f"{base}{skill}/SKILL.md"))
        except OSError:
            return None

    own = probe(registry) if registry else None
    if own is None:
        return None
    if own:
        return True
    if any(probe(name) is True for name in checkouts if name != registry):
        return True
    return False


def explorer_registry(explorer: dict, skill: str) -> str | None:
    for entry in explorer.get("skills") or []:
        if isinstance(entry, dict) and entry.get("name") == skill and isinstance(
                entry.get("registry"), str):
            return entry["registry"]
    return None


# --- plan ----------------------------------------------------------------


def _skill_plugins(layout_path: Path | None) -> dict[str, str]:
    if layout_path is None:
        return {}
    try:
        doc = json.loads(layout_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ScopeError("the registry layout file could not be read") from exc
    out = {}
    for plugin, body in (doc.get("plugins") or {}).items():
        for skill in (body or {}).get("skills") or []:
            out[skill] = plugin
    return out


def _surfaces(skill: str, plugins: dict[str, str]) -> tuple:
    if plugins.get(skill) in LOCAL_ONLY_PLUGINS:
        return (skill_usage.SURFACE_LOCAL,)
    return (skill_usage.SURFACE_LOCAL, skill_usage.SURFACE_CLOUD)


def _is_draft(directory: Path) -> bool:
    try:
        doc = yaml.safe_load((directory / "fixture.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return True  # unreadable: leave it alone
    return isinstance(doc, dict) and doc.get("draft") is True


def build_plan(root: Path, explorer: dict, usage_doc, plugins: dict[str, str],
               now: datetime, checkouts: dict[str, Path] | None = None,
               layouts: dict[str, str] | None = None) -> dict:
    scheduled = read_rows(root, SCHEDULED, "fixtures")
    auto = read_rows(root, SCOPE_AUTO, "rows")
    table = stakes_file.load(root / "evals" / "stakes.yml", root / "evals")
    today = now.date().isoformat()

    unknown_use = usage_unknown(root)

    models = roster_models(explorer)
    checkouts = checkouts or {}
    layouts = layouts if layouts is not None else registry_layouts()

    def exists(skill: str) -> bool | None:
        return skill_exists(skill, explorer_registry(explorer, skill), checkouts, layouts)

    resume, resumed = [], set()
    for row in auto:
        path, rule = row.get("path"), row.get("rule")
        subject_kind, subject = subject_of(path)
        directory = root / path
        if rule in ("ceiling", "floor"):
            why = None
            if directory.is_dir() and fixture_digest(directory) != row.get("fixture_digest"):
                why = "the fixture's content changed since it was paused"
            elif directory.is_dir() and protected(explorer, subject_kind, subject):
                why = (f"{protected(explorer, subject_kind, subject)}, so its fixtures stay "
                       "measured (the gate keeps paused cells as parked `paused` ones)")
            elif directory.is_dir():
                since = last_commit_time(root, path)
                runs = ([] if since is None
                        else fixture_runs(explorer, subject_kind, subject, path, since))
                # No runs at all means the explorer no longer lists them, not
                # that the fixture has headroom: leave the pause alone.
                if runs and per_model(subject_kind, runs, models) is None:
                    why = ("the rule no longer holds on every roster model's own runs, "
                           "so the fixture may still show a gain")
            if why:
                resume.append({"path": path, "kind": subject_kind, "subject": subject, "rule": rule,
                               "why": why})
                resumed.add(path)
        elif rule == "removed" and subject_kind == "skill" and directory.is_dir():
            if exists(subject) is True:
                resume.append({"path": path, "kind": subject_kind, "subject": subject, "rule": rule,
                               "why": "the skill exists in its registry again"})
                resumed.add(path)
        elif rule == "zero-use" and subject_kind == "skill" and directory.is_dir():
            if subject in unknown_use:
                resume.append({"path": path, "kind": subject_kind, "subject": subject, "rule": rule,
                               "why": f"its use is unknown ({USAGE_UNKNOWN}: "
                                      f"{unknown_use[subject]})"})
                resumed.add(path)
                continue
            used = skill_usage.has_recorded_use(usage_doc, subject, now, weeks=CENSUS_WEEKS,
                                               surfaces=_surfaces(subject, plugins))
            if used is True:
                resume.append({"path": path, "kind": subject_kind, "subject": subject, "rule": rule,
                               "why": f"the skill was used in the last {CENSUS_WEEKS} weeks"})
                resumed.add(path)

    pause = []
    for entry in scheduled:
        path, readiness = entry.get("path"), entry.get("readiness")
        kind, subject = subject_of(path)
        directory = root / path
        if path in resumed or not directory.is_dir() or _is_draft(directory):
            continue
        # The high-stakes exemption covers the ceiling and floor rules only:
        # an eval on a skill nobody has used is not worth running at any stakes.
        found = None
        # A removed skill is paused first: nothing else about it matters.
        if kind == "skill" and exists(subject) is False:
            found = ("removed", "the skill no longer exists in its registry; the fixture is "
                     "kept, and its evals resume if the skill comes back")
        since = last_commit_time(root, path)
        if (found is None and since is not None and not protected(explorer, kind, subject)
                and stakes_file.level_of(table, kind, subject) != "high"):
            found = per_model(kind, fixture_runs(explorer, kind, subject, path, since), models)
        if found is None and kind == "skill" and subject not in unknown_use:
            used = skill_usage.has_recorded_use(usage_doc, subject, now, weeks=CENSUS_WEEKS,
                                               surfaces=_surfaces(subject, plugins))
            if used is False:
                found = ("zero-use", f"no recorded use in real work in the last {CENSUS_WEEKS} weeks; "
                         "its evals resume on its first recorded use")
        if found is None:
            continue
        pause.append({"path": path, "kind": kind, "subject": subject, "rule": found[0],
                      "why": found[1], "since": today, "fixture_digest": fixture_digest(directory),
                      "readiness": readiness})
    return {"schema": SCHEMA, "now": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pause": pause, "resume": resume}


# --- apply ---------------------------------------------------------------


def _scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _split_blocks(text: str, key: str) -> tuple[list[str], list[list[str]]]:
    """Header lines and one line-list per `  - ` entry of the `fixtures:`
    style file. Each block is checked by parsing it with yaml, so a file this
    cannot cut cleanly fails instead of being edited."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("  - ")]
    if not starts:
        return lines, []
    header = lines[:starts[0]]
    blocks = [lines[a:b] for a, b in zip(starts, starts[1:] + [len(lines)])]
    parsed = yaml.safe_load(text)[key]
    if len(parsed) != len(blocks):
        raise ScopeError("an entry could not be cut cleanly")
    for block, entry in zip(blocks, parsed):
        if yaml.safe_load(f"{key}:\n" + "".join(block))[key] != [entry]:
            raise ScopeError("an entry could not be cut cleanly")
    return header, blocks


def _remove(text: str, key: str, path: str) -> str:
    header, blocks = _split_blocks(text, key)
    kept = [b for b in blocks if yaml.safe_load(f"{key}:\n" + "".join(b))[key][0].get("path") != path]
    if len(kept) == len(blocks):
        raise ScopeError(f"{path} is not in the file")
    return "".join(header) + "".join("".join(b) for b in kept)


def _append(text: str, key: str, path: str, field: str, value: str) -> str:
    text = text + ("" if text.endswith("\n") else "\n")
    return text + f"  - path: {path}\n    {field}: {_scalar(value)}\n"


def render_scope_auto(rows: list[dict]) -> str:
    if not rows:
        return SCOPE_AUTO_HEADER + "rows: []\n"
    out = [SCOPE_AUTO_HEADER, "rows:\n"]
    for row in rows:
        out.append(f"  - path: {row['path']}\n")
        for field in ("rule", "since", "fixture_digest", "readiness"):
            out.append(f"    {field}: {_scalar(row[field])}\n")
    return "".join(out)


def apply_plan(root: Path, plan: dict) -> None:
    if plan.get("schema") != SCHEMA:
        raise ScopeError("the plan has an unknown schema")
    sched_path, unsched_path, auto_path = (root / SCHEDULED, root / UNSCHEDULED, root / SCOPE_AUTO)
    sched = sched_path.read_text(encoding="utf-8")
    unsched = unsched_path.read_text(encoding="utf-8")
    auto = read_rows(root, SCOPE_AUTO, "rows")
    scheduled_paths = [r.get("path") for r in read_rows(root, SCHEDULED, "fixtures")]
    unsched_rows = {r.get("path"): r for r in read_rows(root, UNSCHEDULED, "fixtures")}

    for item in plan.get("resume") or []:
        path = item["path"]
        row = next((r for r in auto if r.get("path") == path), None)
        if row is None or path in scheduled_paths:
            raise ScopeError(f"{path}: not a fixture this pass paused")
        sched = _append(sched, "fixtures", path, "readiness", row["readiness"])
        if item["kind"] == "skill":
            old = unsched_rows.get(path)
            if old is None or not str(old.get("reason", "")).startswith(AUTO_PREFIX):
                raise ScopeError(f"{path}: its unscheduled row is not this pass's")
            unsched = _remove(unsched, "fixtures", path)
        auto = [r for r in auto if r.get("path") != path]
        scheduled_paths.append(path)

    for item in plan.get("pause") or []:
        path = item["path"]
        if path not in scheduled_paths or any(r.get("path") == path for r in auto):
            raise ScopeError(f"{path}: not a scheduled fixture")
        if fixture_digest(root / path) != item["fixture_digest"]:
            raise ScopeError(f"{path}: changed since the plan was made")
        sched = _remove(sched, "fixtures", path)
        scheduled_paths.remove(path)
        if item["kind"] == "skill":
            if path in unsched_rows:
                raise ScopeError(f"{path}: already has an unscheduled row")
            reason = f"{AUTO_PREFIX}{item['rule']}), {item['since']}: {item['why']}."
            unsched = _append(unsched, "fixtures", path, "reason", reason)
        auto.append({"path": path, "rule": item["rule"], "since": item["since"],
                     "fixture_digest": item["fixture_digest"], "readiness": item["readiness"]})

    sched_path.write_text(sched, encoding="utf-8")
    unsched_path.write_text(unsched, encoding="utf-8")
    auto_path.write_text(render_scope_auto(auto), encoding="utf-8")
    # Everything must load back, and no paused path may stay scheduled.
    again = [r["path"] for r in read_rows(root, SCHEDULED, "fixtures")]
    read_rows(root, UNSCHEDULED, "fixtures")
    if set(again) & {r["path"] for r in read_rows(root, SCOPE_AUTO, "rows")}:
        raise ScopeError("a paused fixture is still scheduled")


def summary(plan: dict) -> str:
    lines = []
    for item in plan.get("pause") or []:
        lines.append(f"- Pause `{item['path']}` ({item['rule']}): {item['why']}.")
    for item in plan.get("resume") or []:
        lines.append(f"- Resume `{item['path']}` ({item['rule']}): {item['why']}.")
    return "\n".join(lines) + ("\n" if lines else "")


# --- command line --------------------------------------------------------


def _read_json(path: Path | None):
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ScopeError(f"{path.name} could not be read as JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--explorer", type=Path, required=True)
    p.add_argument("--usage", type=Path)
    p.add_argument("--registry-layout", type=Path)
    p.add_argument("--registry", action="append", metavar="NAME=PATH",
                   help="a registry checkout; the removed rule reads it (repeatable)")
    p.add_argument("--now", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("apply")
    a.add_argument("--plan", type=Path, required=True)
    a.add_argument("--repo-root", type=Path, default=Path("."))
    s = sub.add_parser("summary")
    s.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            explorer = _read_json(args.explorer)
            if not isinstance(explorer, dict):
                raise ScopeError("the explorer document is not an object")
            usage_doc = skill_usage.load(args.usage) if args.usage else None
            plan = build_plan(args.repo_root.resolve(), explorer, usage_doc,
                              _skill_plugins(args.registry_layout), _parse_now(args.now),
                              parse_registry_flags(args.registry))
            args.out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            print(f"count={len(plan['pause']) + len(plan['resume'])}")
        elif args.command == "apply":
            apply_plan(args.repo_root.resolve(), _read_json(args.plan))
        else:
            sys.stdout.write(summary(_read_json(args.plan)))
    except ScopeError as exc:
        print(f"eval_scope: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
