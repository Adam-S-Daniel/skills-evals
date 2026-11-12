#!/usr/bin/env python3
"""The public-by-construction sections of `explorer/latest.json` (the public
data contract, added fields only, so `schema_version` stays 1).

scripts/explorer_data.py calls these builders; each takes only public inputs
and returns None when its input is missing or unreadable (unknown, never zero
or empty). explorer_data.py `finish` and `explorer/schema.json` check every
field again before the document is written.

  * `evals`: the dashboard's scored eval facts (scripts/eval_facts.py), only
    for subjects the document lists (a public census skill outside
    `plan_week.private_skills`, or a listed guidance section). The meter
    readings (`meter_points`, `account_week_after`) are spend: null unless
    evals/public-export.yml has `include_spend: true`.
  * `hooks`: the git hook checks. The catalog is the fleet runner's check ids
    (_agent-guidance templates/agent-checks/agent-checks, parsed with the
    pinned Tree-sitter Bash grammar: every literal `note_ran <id>` call and
    the `lesson_checks` list; `repo-local` is listed per repository instead)
    plus one `repo-local` entry per public repository whose checkout has
    `.agent-checks/local.sh`. Weekly use comes from the `kind: hook` rows of
    `usage/weekly-local.json` and `usage/weekly-ci.json`. Cloud sessions' runs
    (`surface: cloud` rows) count only when the local file has a cloud
    `hook-records` source: then `totals.cloud` is published and `cloud_from`
    is that source's `from` (a date); with no such source `totals` has no
    `cloud` key and no `cloud_from`, which reads as "cloud not counted",
    never as zero runs. A repository is
    named only when the GitHub visibility list (`--public-repos`) reads it
    `private: false`; every other one, and the producers' own `other` and
    `private` folds, become PRIVATE_BUCKET, whose rows are published only when
    at least `min_private_repos` distinct named non-public repositories fed it
    (so with the producers' folds alone it never shows). The verdicts follow
    evals/hook-policy.yml.
  * `lesson_funnel`: how lessons ended (a check, a skill, guidance, nothing,
    still open), counted over public issues and pull requests only.
  * `activity`: the last ACTIVITY_DAYS of pull requests (open, or merged in the
    window), open issues and workflow runs in the fleet owners' public
    repositories, from `--activity`, leaving out explorer-data.yml's own runs. Never a body; a title only when
    `safe_text` accepts it.
  * `spend`: weekly totals from `spend/weekly.json`, only with
    `include_spend: true` (SPEND_WEEK_KEYS; never a per-session or per-thread
    row).
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import eval_facts
import improve_outcomes
import skill_usage
import timeweeks  # harness/, put on sys.path by explorer_data's imports

FLEET_OWNERS = ("Adam-S-Daniel", "jodidaniel")
PRIVATE_BUCKET = "private repos"
GUIDANCE_REPO = "Adam-S-Daniel/_agent-guidance"
RUNNER_URL = f"https://github.com/{GUIDANCE_REPO}/blob/main/templates/agent-checks/agent-checks"
CI_JOB_NAME = "agent-checks"
REPO_LOCAL = "repo-local"
REPO_RE = re.compile(r"(?P<owner>[A-Za-z0-9-]{1,39})/(?P<name>[A-Za-z0-9._-]{1,100})")
_CHECK_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_DAY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
#: Identifiers that must never be published: a session, project thread,
#: message, trigger or scheduled-task id (a prefix, `_`, then an id with a
#: digit or a capital, so a field name such as `thread_spend_usd` is not one).
#: `finish` refuses them anywhere in the document.
FORBIDDEN_ID_RE = re.compile(r"(?:cse|session|cmsg|trig|trigger|thread|thr)_"
                             r"(?=[a-z]*[0-9A-Z])[A-Za-z0-9]{6,}")
_LONG_HEX_RE = re.compile(r"[0-9a-fA-F]{13,}")
TITLE_MAX = 200
ACTIVITY_DAYS = 14
FETCH_SKEW = timedelta(minutes=5)
FETCH_MAX_LAG = timedelta(days=1)

HOOK_POLICY_DEFAULTS = {"window_weeks": 8, "max_override_rate": 0.20, "min_private_repos": 3}
VERDICTS = ("earning", "never-blocked", "never-ran", "overridden-often")


# --- shared readers ------------------------------------------------------------

def _read_json(path: Path | None):
    if path is None:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None


def _count(value) -> bool:
    return type(value) is int and value >= 0


def _number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def _stamp(value) -> str | None:
    """A GitHub time as `YYYY-MM-DDTHH:MM:SSZ`, or None."""
    moment = improve_outcomes.parse_time(value)
    if moment is None:
        return None
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_text(value, limit: int = TITLE_MAX) -> str | None:
    """A title or name fit to publish, whitespace collapsed, `@` dropped (a
    mention reads the same without it), cut to `limit`; None when it is not a
    string or carries an identifier `finish` refuses or a hex run longer than
    12 (a digest, a commit, a session id's hex)."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.replace("@", "").split())[:limit]
    if not text or FORBIDDEN_ID_RE.search(text) or _LONG_HEX_RE.search(text):
        return None
    return text


def load_public_repos(path: Path | None) -> frozenset | None:
    """The fleet owners' public repositories from `--public-repos`
    ({"repos": [{"full_name", "private"}]}, GitHub's own visibility), or None
    when the file is absent or off that shape. A row is kept only when it
    reads exactly `private: false` and names a fleet owner."""
    doc = _read_json(path)
    rows = doc.get("repos") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        return None
    out = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("private") is not False:
            continue
        name = row.get("full_name")
        match = REPO_RE.fullmatch(name) if isinstance(name, str) else None
        if match and match["owner"] in FLEET_OWNERS:
            out.add(name)
    return frozenset(out)


def load_policy(path: Path | None, defaults: dict) -> dict:
    """`defaults` overlaid by the YAML mapping at `path`, each value checked
    against its default's type. A missing file is the defaults; a bad value is
    an error, since the file is committed."""
    out = dict(defaults)
    if path is None:
        return out
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: not a mapping")
    for key, value in doc.items():
        if key not in defaults:
            raise ValueError(f"{path}: unknown key {key!r}")
        want = type(defaults[key])
        if isinstance(value, bool) != (want is bool) or not isinstance(
                value, (int, float) if want is float else want):
            raise ValueError(f"{path}: {key} must be a {want.__name__}")
        out[key] = value
    return out


def include_spend(path: Path | None) -> bool:
    """evals/public-export.yml's `include_spend` (default False: spend is
    published only when the owner says so)."""
    return load_policy(path, {"include_spend": False})["include_spend"]


# --- evals -------------------------------------------------------------------------

RUN_KEYS = ("run_id", "fired_at", "fixture", "skill", "model", "trials", "with_skill",
            "without_skill", "checks", "gain", "with_judge", "without_judge", "judge",
            "with_share", "without_share", "cost_usd", "meter_points", "account_week_after",
            "cli", "report_url")
BARE_KEYS = ("run_id", "fired_at", "fixture", "skill", "model", "trials", "bare", "checks",
             "bare_share", "cost_usd", "report_url", "paired_at", "with_share", "without_share")
SPEND_RUN_KEYS = ("meter_points", "account_week_after")
_RUN_ID_RE = re.compile(r"\d{8}T\d{6}Z(?:-[0-9a-f]{1,12})?")


def build_evals(tree: Path, report_base: str, skill_names: set, section_ids: set,
                spend: bool) -> dict:
    """The dashboard's eval facts for listed subjects only: `runs` (every
    scored paired run), `latest` (the newest per test and model), `summary`
    (skill vs no skill per model), `latest_summary`, `bare_runs` and
    `bare_summary`. A row whose subject is not listed is dropped before any
    summary is made, so a private run moves no number."""
    rows, bare = eval_facts.scored_runs(str(tree), report_base)

    def listed(row) -> bool:
        skill = str(row.get("skill"))
        if skill.startswith("guidance/"):
            return skill[len("guidance/"):] in section_ids
        return skill in skill_names

    def clean(row, keys):
        out = {k: row.get(k) for k in keys}
        if not spend:
            out.update({k: None for k in SPEND_RUN_KEYS if k in out})
        if not (isinstance(out["run_id"], str) and _RUN_ID_RE.fullmatch(out["run_id"])):
            return None
        return out

    runs = [r for r in (clean(r, RUN_KEYS) for r in rows if listed(r)) if r is not None]
    bare_runs = [r for r in (clean(r, BARE_KEYS) for r in bare if listed(r)) if r is not None]
    return {"runs": runs, "latest": eval_facts.latest_per_test(runs),
            "summary": eval_facts.skill_vs_no_skill(runs),
            "latest_summary": eval_facts.latest_summary(runs),
            "bare_runs": bare_runs, "bare_summary": eval_facts.bare_summary(bare_runs)}


# --- hooks -------------------------------------------------------------------------

def fleet_checks(agent_checks_dir: Path | None) -> list | None:
    """The fleet runner's check ids, from its source parsed as Bash (never a
    line scan): the literal first argument of every `note_ran` call, and the
    words of the `lesson_checks` assignment. None without a readable runner
    or the parser, or when the source does not parse."""
    if agent_checks_dir is None:
        return None
    try:
        source = (Path(agent_checks_dir) / "agent-checks").read_bytes()
        from scorers import bash_ast  # harness/scorers
        root = bash_ast.parse_bash(source)
    except (OSError, ValueError, ImportError):
        return None
    ids: set = set()
    pending = [root]
    while pending:
        node = pending.pop()
        pending.extend(node.named_children)
        if node.type == "command":
            name = node.child_by_field_name("name")
            args = node.children_by_field_name("argument")
            if name is not None and name.text == b"note_ran" and args and args[0].type == "word":
                ids.add(args[0].text.decode("utf-8", "replace"))
        elif node.type == "variable_assignment":
            var, value = node.child_by_field_name("name"), node.child_by_field_name("value")
            if var is not None and var.text == b"lesson_checks" and value is not None \
                    and not any(c.type in ("expansion", "simple_expansion", "command_substitution")
                                for c in value.named_children):
                ids.update(value.text.decode("utf-8", "replace").strip("\"'").split())
    ids = {i for i in ids if _CHECK_ID_RE.fullmatch(i)} - {REPO_LOCAL}
    return [{"name": i, "where": "fleet", "repo": None, "source_url": RUNNER_URL}
            for i in sorted(ids)]


def repo_checks(context_repos: dict | None, public: frozenset | None) -> list:
    """One `repo-local` entry per public repository whose checkout carries
    `.agent-checks/local.sh` (a regular file, not a link)."""
    out = []
    for repo, path in sorted((context_repos or {}).items()):
        if public is None or repo not in public:
            continue
        local = Path(path) / ".agent-checks" / "local.sh"
        try:
            ok = local.is_file() and not local.is_symlink()
        except OSError:
            ok = False
        if ok:
            out.append({"name": REPO_LOCAL, "where": "repo", "repo": repo,
                        "source_url": f"https://github.com/{repo}/blob/HEAD/.agent-checks/local.sh"})
    return out


def _bucket(repo, public: frozenset | None, private_seen: set):
    """The published repository of a usage row: None stays None (no GitHub
    remote), a public repository its name, anything else PRIVATE_BUCKET; a
    named non-public repository is remembered to count the bucket."""
    if repo is None:
        return None
    if isinstance(repo, str) and public is not None and repo in public:
        return repo
    if isinstance(repo, str) and REPO_RE.fullmatch(repo):
        private_seen.add(repo)
    return PRIVATE_BUCKET


def _add(a, b):
    if a is None:
        return b if _count(b) else None
    return a + b if _count(b) else a


def _cloud_hook_source(tree: Path) -> dict | None:
    """The cloud `hook-records` source of usage/weekly-local.json, or None:
    cloud hook runs are counted only when the usage file says it read records."""
    doc = _read_json(tree / "usage" / "weekly-local.json")
    if not isinstance(doc, dict) or doc.get("schema") != skill_usage.SCHEMA \
            or not isinstance(doc.get("sources"), list):
        return None
    for source in doc["sources"]:
        if isinstance(source, dict) and source.get("surface") == "cloud" \
                and source.get("scope") == skill_usage.CLOUD_HOOK_SCOPE \
                and isinstance(_stamp(source.get("from")), str):
            return source
    return None


def _hook_rows(tree: Path, cloud: bool = False) -> list | None:
    """Every `kind: hook` row of the two weekly files, or None when neither
    is readable. A cloud row is kept only when `cloud` says the usage file has
    a cloud hook source."""
    # Not skill_usage.load: the CI file's `repo` rows carry a null
    # `invocations`, which that loader rejects for the whole file. Only the
    # hook rows are read, each held to its own shape.
    rows, found = [], False
    for name in ("weekly-local.json", "weekly-ci.json"):
        doc = _read_json(tree / "usage" / name)
        if not isinstance(doc, dict) or doc.get("schema") != skill_usage.SCHEMA \
                or not isinstance(doc.get("rows"), list):
            continue
        found = True
        rows += [r for r in doc["rows"] if isinstance(r, dict) and r.get("kind") == "hook"
                 and isinstance(r.get("week"), str) and _DAY_RE.fullmatch(r["week"])
                 and isinstance(r.get("name"), str) and r.get("surface") in (("local", "ci", "cloud") if cloud else ("local", "ci"))
                 # A CI row may carry a null count: the CI producer records
                 # which checks refused, not which ran.
                 and (_count(r.get("invocations"))
                      or r.get("surface") == "ci" and r.get("invocations") is None)]
    return rows if found else None


def build_hooks(tree: Path, now: datetime, agent_checks_dir: Path | None,
                context_repos: dict | None, public: frozenset | None, policy: dict) -> dict | None:
    """The document's `hooks`, or None with neither a catalog nor a usage file."""
    catalog = fleet_checks(agent_checks_dir)
    cloud_source = _cloud_hook_source(tree)
    rows = _hook_rows(tree, cloud_source is not None)
    if catalog is None and rows is None:
        return None
    checks = {(c["name"], c["repo"]): dict(c) for c in (catalog or []) + repo_checks(context_repos, public)}
    fleet_names = {c["name"] for c in catalog or []}
    private_seen: set = set()
    use: dict = {}
    surfaces = ("local", "ci") + (("cloud",) if cloud_source is not None else ())
    totals: dict = {s: {} for s in surfaces}
    unlisted = 0
    for row in rows or []:
        name, surface = row["name"], row["surface"]
        repo = _bucket(row.get("repo"), public, private_seen)
        whole = name == "all" and surface in ("local", "cloud") \
            or name == CI_JOB_NAME and surface == "ci"
        if whole:
            target = totals[surface]
        elif name in fleet_names:
            target = use.setdefault((name, None), {})
        elif name == REPO_LOCAL:
            checks.setdefault((REPO_LOCAL, repo), {"name": REPO_LOCAL, "where": "repo",
                                                    "repo": repo, "source_url": None})
            target = use.setdefault((REPO_LOCAL, repo), {})
        else:
            unlisted += 1
            continue
        key = (row["week"], surface, repo)
        cell = target.setdefault(key, {"week": row["week"], "surface": surface, "repo": repo,
                                       "invocations": 0, "blocked": None, "overridden": None})
        # The CI file's per-check rows say which checks refused a red run,
        # not which ran: their `invocations` is 0 (older files) or null, and
        # neither is a count. Published as null so no check shows fewer runs
        # than blocks. The whole-job CI row is a real count.
        runs = row["invocations"]
        if surface == "ci" and not whole and not runs:
            runs = None
        cell["invocations"] = None if cell["invocations"] is None or runs is None \
            else cell["invocations"] + runs
        cell["blocked"] = _add(cell["blocked"], row.get("blocked"))
        # The CI file's `overridden` repeats its `blocked` (a red CI run is
        # counted as both), so it is not an override count and is never read.
        if surface != "ci":
            cell["overridden"] = _add(cell["overridden"], row.get("overridden"))
    shown = len(private_seen) >= policy["min_private_repos"]
    if not shown:
        checks.pop((REPO_LOCAL, PRIVATE_BUCKET), None)

    def rows_of(cells: dict) -> list:
        out = [c for c in cells.values() if shown or c["repo"] != PRIVATE_BUCKET]
        return sorted(out, key=lambda c: (c["week"], c["surface"], c["repo"] or ""), reverse=True)

    start = min(timeweeks.week_monday(label)
                for label in timeweeks.window_weeks(now, policy["window_weeks"]))
    entries = []
    for key, entry in sorted(checks.items(), key=lambda kv: (kv[0][1] or "", kv[0][0])):
        mine = rows_of(use.get(key, {})) if rows is not None else None
        entry.update(use=mine, **verdict(mine, start, policy))
        entries.append(entry)
    out = {"window": {"weeks": policy["window_weeks"], "from": start,
                       "to": now.date().isoformat()},
            "policy": {k: policy[k] for k in ("max_override_rate", "min_private_repos")},
            "checks": entries,
            "totals": None if rows is None else {s: rows_of(totals[s]) for s in surfaces},
            "unlisted": None if rows is None else unlisted,
            "private_repos_shown": shown}
    # Only with a cloud source, so the public file is unchanged until a
    # cloud record exists.
    if cloud_source is not None:
        out["cloud_from"] = _stamp(cloud_source["from"])[:10]
    return out


def verdict(rows: list | None, start: str, policy: dict) -> dict:
    """{"window_totals", "verdict", "verdict_reason", "overrides_measured"}
    over the rows in the window. The override rate is overridden over blocked
    across the rows that count overrides; the CI file's copy of `blocked` is
    not one (`build_hooks` drops it), and the local hook log counts none, so
    a check is usually unmeasured. A check that blocked with no override
    count is `earning` with `overrides_measured: false`; `overridden-often`
    needs a measured rate. No rows (no usage file) is unknown."""
    if rows is None:
        return {"window_totals": None, "verdict": None, "verdict_reason": "no usage file",
                "overrides_measured": None}
    recent = [r for r in rows if r["week"] >= start]
    blocked = sum(r["blocked"] or 0 for r in recent)
    known = [r for r in recent if r["overridden"] is not None]
    known_blocked = sum(r["blocked"] or 0 for r in known)
    overridden = sum(r["overridden"] for r in known)
    rate = overridden / known_blocked if known_blocked else None
    measured = rate is not None
    uncounted = any(r["invocations"] is None for r in recent)
    counted = sum(r["invocations"] for r in recent if r["invocations"] is not None)
    # `invocations` is the run count only when every row counts its runs;
    # `invocations_counted` is what the rows that do count add up to.
    totals = {"invocations": None if uncounted else counted, "invocations_counted": counted,
              "blocked": blocked, "overridden": overridden if known else None, "override_rate": rate}
    weeks, limit = policy["window_weeks"], policy["max_override_rate"]
    out = {"window_totals": totals, "overrides_measured": measured}
    if blocked == 0:
        if uncounted:
            return {**out, "verdict": "never-blocked",
                    "verdict_reason": f"runs not counted; no block in {weeks} weeks"}
        if counted == 0:
            return {**out, "verdict": "never-ran",
                    "verdict_reason": f"no recorded runs in {weeks} weeks (CI runs are not counted per check)"}
        return {**out, "verdict": "never-blocked",
                "verdict_reason": f"ran {counted} {'time' if counted == 1 else 'times'} in {weeks} weeks, blocked none"}
    if not measured:
        return {**out, "verdict": "earning",
                "verdict_reason": f"blocked in {weeks} weeks; no source counts its overrides"}
    if rate > limit:
        return {**out, "verdict": "overridden-often",
                "verdict_reason": f"override rate above {limit:.0%}"}
    return {**out, "verdict": "earning",
            "verdict_reason": f"blocked in {weeks} weeks, override rate at most {limit:.0%}"}


# --- lesson funnel -------------------------------------------------------------

OUTCOMES = ("check", "skill", "guidance", "nothing", "open", "unknown")
_LESSON_CHECK_HEAD_RE = re.compile(r"agent/lesson-check-[a-z0-9][a-z0-9-]{0,63}")
HOOK_PROPOSAL_LABEL = "hook-proposal"


def _closed_as(row) -> str:
    """`open`, `completed`, `not_planned` or `unknown` for an issue row."""
    if row.get("state") == "open":
        return "open"
    reason = row.get("state_reason")
    return reason if reason in ("completed", "not_planned", "duplicate") else "unknown"


def _issue_outcome(row, done: str) -> str:
    closed = _closed_as(row)
    return {"open": "open", "completed": done, "not_planned": "nothing",
            "duplicate": "nothing"}.get(closed, "unknown")


def _pr_outcome(state: str, done: str) -> str:
    return {"open": "open", "merged": done, "closed": "nothing"}[state]


def build_lesson_funnel(funnel_path: Path | None, lesson_issues_path: Path | None,
                        drafts: dict | None, memory_issue, proposal_issue) -> dict | None:
    """Lessons by outcome over public sources only, or None when none is
    readable. `memory_issue` and `proposal_issue` are explorer_data's own
    validators of the `--lesson-issues` rows (a memory row counts only in a
    repository that reads exactly `private: false`), so this reads nothing
    they would not publish. Sources:

      * hook-proposal issues in skills-evals (`--lesson-funnel` `hook_proposals`):
        closed completed is a check, closed not planned or as a duplicate nothing;
      * lesson-check pull requests (`agent/lesson-check-<id>` in
        _agent-guidance, `--lesson-funnel` `lesson_check_prs`): merged is a check;
      * memory promotion issues: closed completed is a check when its target is
        `agent-checks`, else guidance;
      * new-skill drafts (`draft-skill/<subject>` pull requests, `--draft-prs`):
        merged is a skill; and skill-proposal issues whose subject has no draft,
        closed completed is a skill.

    A closed issue with no recorded reason is `unknown`."""
    funnel = _read_json(funnel_path)
    funnel = funnel if isinstance(funnel, dict) else None
    issues = _read_json(lesson_issues_path)
    issues = issues if isinstance(issues, dict) else None
    if funnel is None and issues is None and drafts is None:
        return None
    by_source: dict = {}

    def note(source: str, outcome: str) -> None:
        counts = by_source.setdefault(source, dict.fromkeys(OUTCOMES, 0))
        counts[outcome] += 1

    missing = []
    if funnel is not None and isinstance(funnel.get("hook_proposals"), list):
        seen = set()
        for row in funnel["hook_proposals"]:
            if (not isinstance(row, dict) or "pull_request" in row
                    or type(row.get("number")) is not int or row["number"] in seen
                    or row.get("state") not in ("open", "closed")
                    or not any(isinstance(lb, dict) and lb.get("name") == HOOK_PROPOSAL_LABEL
                               for lb in row.get("labels") or [])):
                continue
            seen.add(row["number"])
            note("hook-proposal", _issue_outcome(row, "check"))
    else:
        missing.append("hook-proposal")
    if funnel is not None and isinstance(funnel.get("lesson_check_prs"), list):
        seen = set()
        for row in funnel["lesson_check_prs"]:
            if (not isinstance(row, dict) or not isinstance(row.get("head"), str)
                    or not _LESSON_CHECK_HEAD_RE.fullmatch(row["head"])
                    or type(row.get("number")) is not int or row["number"] in seen
                    or row.get("state") not in ("open", "closed")
                    or type(row.get("merged")) is not bool):
                continue
            seen.add(row["number"])
            note("lesson-check", _pr_outcome("merged" if row["merged"] else row["state"], "check"))
    else:
        missing.append("lesson-check")
    if issues is not None and isinstance(issues.get("memory"), list):
        for row in issues["memory"]:
            item = memory_issue(row)
            if item is not None:
                note("memory", _issue_outcome(row, "check" if item["target"] == "agent-checks"
                                              else "guidance"))
    else:
        missing.append("memory")
    if drafts is not None:
        for draft in drafts.values():
            note("draft-skill", _pr_outcome(draft["state"], "skill"))
    else:
        missing.append("draft-skill")
    if issues is not None and isinstance(issues.get("proposals"), list):
        for row in issues["proposals"]:
            item = proposal_issue(row)
            if item is not None and item["target"] not in (drafts or {}):
                note("skill-proposal", _issue_outcome(row, "skill"))
    else:
        missing.append("skill-proposal")
    totals = dict.fromkeys(OUTCOMES, 0)
    for counts in by_source.values():
        for k, v in counts.items():
            totals[k] += v
    return {**totals, "by_source": dict(sorted(by_source.items())),
            "sources_missing": sorted(missing)}


# --- activity ------------------------------------------------------------------

PR_KEYS = ("repo", "number", "title", "state", "created_at", "updated_at", "merged_at", "url")
ISSUE_KEYS = ("repo", "number", "title", "state", "created_at", "updated_at", "url")
RUN_ACTIVITY_KEYS = ("repo", "run_id", "workflow", "title", "event", "state", "conclusion",
                     "created_at", "updated_at", "url")
_EVENT_RE = re.compile(r"[a-z_]{1,40}")
#: explorer-data.yml's own runs, left out of `activity.runs` (read by its
#: `path`, which is never published).
OWN_WORKFLOW = ("Adam-S-Daniel/skills-evals", ".github/workflows/explorer-data.yml")
_RUN_STATES = frozenset({"queued", "in_progress", "completed", "waiting", "requested",
                         "pending", "action_required"})
_CONCLUSIONS = frozenset({"success", "failure", "cancelled", "skipped", "timed_out",
                          "neutral", "action_required", "stale", "startup_failure"})


def build_activity(path: Path | None, public: frozenset | None, as_of: datetime,
                   wall_clock: datetime) -> dict | None:
    """The document's `activity` from `--activity` ({"fetched_at", "pulls",
    "issues", "runs"}, already reduced by explorer-data.yml), or None: no
    file, no visibility list, or a `fetched_at` past the wall clock plus
    FETCH_SKEW or before `as_of` minus FETCH_MAX_LAG. Every row's repository
    must be on the visibility list; URLs are built here, never copied."""
    doc = _read_json(path)
    if public is None or not isinstance(doc, dict) or not all(
            isinstance(doc.get(k), list) for k in ("pulls", "issues", "runs")):
        return None
    fetched = improve_outcomes.parse_time(doc.get("fetched_at"))
    if fetched is None or fetched > wall_clock + FETCH_SKEW or fetched < as_of - FETCH_MAX_LAG:
        return None
    since = (fetched - timedelta(days=ACTIVITY_DAYS)).astimezone(timezone.utc)
    since_text = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    def base(row):
        if not isinstance(row, dict) or row.get("repo") not in public:
            return None
        return row["repo"]

    pulls, seen = [], set()
    for row in doc["pulls"]:
        repo, number = base(row), row.get("number") if isinstance(row, dict) else None
        if repo is None or type(number) is not int or not 0 < number < 10 ** 9 \
                or (repo, number) in seen:
            continue
        merged = _stamp(row.get("merged_at"))
        state = "merged" if merged else row.get("state")
        if state not in ("open", "merged") or (state == "merged" and merged < since_text):
            continue
        seen.add((repo, number))
        pulls.append({"repo": repo, "number": number, "title": safe_text(row.get("title")),
                      "state": state, "created_at": _stamp(row.get("created_at")),
                      "updated_at": _stamp(row.get("updated_at")), "merged_at": merged,
                      "url": f"https://github.com/{repo}/pull/{number}"})
    issues, seen = [], set()
    for row in doc["issues"]:
        repo, number = base(row), row.get("number") if isinstance(row, dict) else None
        if repo is None or type(number) is not int or not 0 < number < 10 ** 9 \
                or row.get("state") != "open" or (repo, number) in seen:
            continue
        seen.add((repo, number))
        issues.append({"repo": repo, "number": number, "title": safe_text(row.get("title")),
                       "state": "open", "created_at": _stamp(row.get("created_at")),
                       "updated_at": _stamp(row.get("updated_at")),
                       "url": f"https://github.com/{repo}/issues/{number}"})
    runs, seen = [], set()
    for row in doc["runs"]:
        repo, run_id = base(row), row.get("id") if isinstance(row, dict) else None
        created = _stamp(row.get("created_at")) if isinstance(row, dict) else None
        if repo is None or type(run_id) is not int or not 0 < run_id < 10 ** 13 \
                or created is None or created < since_text or (repo, run_id) in seen:
            continue
        if (repo, row.get("path")) == OWN_WORKFLOW:
            continue  # this document's own builds would change it on every run
        seen.add((repo, run_id))
        event, status, conclusion = row.get("event"), row.get("status"), row.get("conclusion")
        runs.append({"repo": repo, "run_id": run_id, "workflow": safe_text(row.get("workflow"), 100),
                     "title": safe_text(row.get("title")),
                     "event": event if isinstance(event, str) and _EVENT_RE.fullmatch(event) else None,
                     "state": status if status in _RUN_STATES else None,
                     "conclusion": conclusion if conclusion in _CONCLUSIONS else None,
                     "created_at": created, "updated_at": _stamp(row.get("updated_at")),
                     "url": f"https://github.com/{repo}/actions/runs/{run_id}"})
    newest = lambda r: (r["updated_at"] or r["created_at"] or "", r["repo"])  # noqa: E731
    return {"fetched_at": _stamp(doc["fetched_at"]), "since": since_text,
            "repos": sorted(public),
            "pulls": sorted(pulls, key=newest, reverse=True),
            "issues": sorted(issues, key=newest, reverse=True),
            "runs": sorted(runs, key=newest, reverse=True)}


# --- spend -----------------------------------------------------------------------

#: The one published shape of a spend week. `spend/weekly.json` (written by
#: the dashboard refresh; explorer/schema.json `$defs.spend_file` documents
#: it) may carry more; only these keys are copied.
SPEND_WEEK_KEYS = ("week", "eval_runs", "plan_meter_points", "api_usd", "thread_spend_usd",
                   "cost_per_verdict", "plan")
_PLAN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,39}")


def build_spend(tree: Path, enabled: bool) -> dict | None:
    """The document's `spend`: None unless `enabled` and `spend/weekly.json`
    is a schema 1 file with a `weeks` list. Each week copies SPEND_WEEK_KEYS
    only, numbers kept at full precision; a week with a bad value is dropped
    whole, and `plan` falls back to the file's top-level `plan`."""
    if not enabled:
        return None
    doc = _read_json(tree / "spend" / "weekly.json")
    if not isinstance(doc, dict) or doc.get("schema") != 1 or not isinstance(doc.get("weeks"), list):
        return None
    default_plan = doc.get("plan")
    weeks = []
    for row in doc["weeks"]:
        if not isinstance(row, dict) or not isinstance(row.get("week"), str) \
                or not _DAY_RE.fullmatch(row["week"]):
            continue
        plan = row.get("plan", default_plan)
        if plan is not None and not (isinstance(plan, str) and _PLAN_RE.fullmatch(plan)):
            continue
        runs = row.get("eval_runs")
        numbers = [row.get(k) for k in ("plan_meter_points", "api_usd", "thread_spend_usd",
                                        "cost_per_verdict")]
        if not (runs is None or _count(runs)) or not all(v is None or _number(v) for v in numbers):
            continue
        weeks.append({"week": row["week"], "eval_runs": runs,
                      **dict(zip(("plan_meter_points", "api_usd", "thread_spend_usd",
                                  "cost_per_verdict"), numbers)), "plan": plan})
    weeks.sort(key=lambda w: w["week"], reverse=True)
    return {"generated_at": _stamp(doc.get("generated_at")), "weeks": weeks}
