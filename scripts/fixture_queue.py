#!/usr/bin/env python3
"""Track the fixture queue end to end, and file an issue when it stalls
(Adam, 2026-11-03: "Make sure the proper functioning and cost and
benefits/impacts/instances of requesting harder fixtures, creating them from
real fleet work when possible and putting those to use is tracked, acted on
when broken, and included in the dashboard").

  fixture_queue.py report --issues FILE --pulls FILE --repo DIR
                          --results-tree DIR --now TIME --out FILE
  fixture_queue.py alerts --report FILE [--dry-run] [--run-url URL]

THE QUEUE. The weekly sweep files one `agent-ready` issue per fixture
request (scripts/work_item_issues.py: `needs-fixtures`,
`needs-harder-fixtures`, `needs-trigger-set`); the fleet worker answers one
with a pull request that names it with `Refs`; scripts/fixture_pr_gate.py
arms auto-merge when the pull request only adds fixtures, each with an
`origin:` mapping saying whether it was rebuilt from real fleet work or
invented and which request it answers; the weekly schedule then runs it.
`report` follows each step, and `alerts` acts when one stops.

`report` (`build_report`, pure: every input passed in, `now` included) reads:

* `--issues`: the REST issue listing (`gh api --paginate --slurp`, a list
  of pages or one list). A request is an issue github-actions[bot] opened
  whose body holds a request marker line; its kind and subject come from
  that line, validated, never from the title or the prose.
* `--pulls`: the REST pull request listing, the same shapes. A pull
  request belongs to a request when its body names it with `Refs` or a
  closing keyword (fixture_pr_gate's reference rule).
* `--repo`: a skills-evals checkout with full history. Every
  `evals/**/fixture.yaml` whose `origin:` passes
  `fixture_pr_gate.origin_problem` is a fixture of the queue; `added_at` is
  the committer time of the first commit that added the file (null outside
  history: unknown).
* `--results-tree`: persistent/eval-results. The validated runs come from
  scripts/compute_gates.py's `build_index`, as scripts/explorer_data.py
  reads them; a fixture's `runs` is its distinct run directories,
  `with_pass_rate` and `without_pass_rate` the checks passed over checks run
  in its scored trials per arm (explorer_data.arm_numbers; a guidance
  fixture's in-situ pair: `full` and `full_minus_section`), null with no
  scored check. `cost_usd` and `cost_points` add up the
  `routine-results/<run id>/cost_estimate.json` files of its runs
  (scripts/ingest_routine_results.py `estimate`); a run outside
  routine-results, a routine run that also holds another fixture's results,
  or a run without an estimate (or without points) makes that figure null:
  unknown, never a guess.

The report is PUBLIC (explorer-data.yml puts it in `explorer/latest.json` as
`fixture_queue`): issue numbers, kinds, validated subject names, states,
times, pull request numbers, fixture paths, origin URLs that passed their
patterns, counts and dollars. Never a title, a body or a branch name.

FINDINGS, each `{finding_id, kind, severity, subject, url}`, the fleet
health audit's vocabulary (_agent-guidance docs/routines/fleet-health-audit.md):

  skills-evals/fixture-queue-stale-request-<issue>   idle, medium
      an open request STALE_REQUEST_DAYS old that no open or merged pull
      request names: the worker has not taken it.
  skills-evals/fixture-queue-stuck-pr-<pr>           broken, high
      a lane pull request (fixture_pr_gate.AUTHOR, its LABEL) naming a
      request, open STUCK_PR_DAYS with auto-merge off: the gate refused it
      (an origin missing, say) or nobody looked.
  skills-evals/fixture-queue-unused-fixture-<slug>   broken, high
      a fixture with an origin, committed UNUSED_FIXTURE_DAYS ago, with no
      ingested run: it never reached the schedule, or its runs fail.

High is the audit's "blocks the self-improvement loop": a stuck pull request
or an unrun fixture is a request answered and wasted. A stale request only
waits on the worker, so medium.

`alerts` files them in skills-evals in the audit's format: label
`half-built-or-broken` (created when missing, never edited; work_item_issues
`ensure_labels`), a body that starts with `Kind:`, `Severity:` and
`Finding-ID:` lines, then the marker line
`<!-- skills-evals:fixture-queue:<id> -->` that finds it again. One issue per
finding: no issue creates one; a closed one is reopened with a comment (the
audit's "the finding is back"); an open one stands. An open issue whose
finding is gone is closed with a comment, unless it is labeled `on-hold`.
Every finding is validated again before it reaches a title or body, since the
report crossed a job boundary as an artifact. A failed `gh` call for one
finding is recorded and the others still run; the exit code is then 1. Exit 2
is bad input. A report that is missing or unreadable files nothing and
closes nothing.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import explorer_data  # noqa: E402
import fixture_pr_gate  # noqa: E402
import retire_skill  # noqa: E402
import work_item_issues  # noqa: E402

SCHEMA = 1
EVALS_REPO = work_item_issues.EVALS_REPO
REPO_URL = f"https://github.com/{EVALS_REPO}"
#: An open request this old with no open or merged pull request is stale.
STALE_REQUEST_DAYS = 7
#: A lane pull request open this long with auto-merge off is stuck.
STUCK_PR_DAYS = 2
#: A fixture with an origin committed this long ago with no run is unused.
UNUSED_FIXTURE_DAYS = 3
#: The fleet health audit's label; created when missing, never edited.
ALERT_LABEL = "half-built-or-broken"
ALERT_LABELS = {ALERT_LABEL: ("b60205", "A half-built or broken feature (fleet health audit)")}
#: An open alert issue with this label is never closed (the owner holds it).
HOLD_LABEL = "on-hold"
ALERT_PREFIX = "skills-evals/fixture-queue-"
_ALERT_MARKER = re.compile(r"<!-- skills-evals:fixture-queue:(\S+) -->")
_FINDING_ID = re.compile(re.escape(ALERT_PREFIX)
                         + r"(?:(stale-request|stuck-pr)-([1-9][0-9]{0,6})"
                           r"|(unused-fixture)-([a-z0-9][a-z0-9-]{0,200}))")
_ISSUE_URL = re.compile(re.escape(REPO_URL) + r"/issues/([1-9][0-9]{0,6})")
_PULL_URL = re.compile(re.escape(REPO_URL) + r"/pull/([1-9][0-9]{0,6})")
_FIXTURE_URL = re.compile(re.escape(REPO_URL) + r"/tree/main/(evals/[A-Za-z0-9._/-]{1,200})")
_SUBJECT = re.compile(r"(?:guidance/)?[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_REQUEST_MARKER = re.compile(r"<!-- skills-evals:(" + "|".join(work_item_issues.READY_KINDS)
                             + r"):(\S+) -->")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
KINDS = {"stale-request": ("idle", "medium"), "stuck-pr": ("broken", "high"),
         "unused-fixture": ("broken", "high")}


class QueueError(ValueError):
    """Bad input: no report can be built, or no alert filed."""


def _time(value) -> str | None:
    """A GitHub or git timestamp as `YYYY-MM-DDTHH:MM:SSZ` UTC, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _older(stamp: str | None, now: datetime, days: int) -> bool:
    """Whether `stamp` is at least `days` before `now`; False when unknown."""
    if stamp is None:
        return False
    return now - datetime.fromisoformat(stamp.replace("Z", "+00:00")) >= timedelta(days=days)


def flatten(listing) -> list:
    """A REST listing, slurped pages or one list, as one list of objects."""
    if not isinstance(listing, list):
        raise QueueError("a listing is not a JSON list")
    out = []
    for item in listing:
        out += [i for i in item if isinstance(i, dict)] if isinstance(item, list) \
            else [item] if isinstance(item, dict) else []
    return out


def requests_of(issues: list) -> list:
    """[{issue, kind, subject, state, opened_at, closed_at}] for every
    request issue, by number."""
    out = []
    for issue in issues:
        number = issue.get("number")
        if "pull_request" in issue or type(number) is not int or number < 1 \
                or (issue.get("user") or {}).get("login") != retire_skill.ISSUE_AUTHOR \
                or issue.get("state") not in ("open", "closed"):
            continue
        for line in (issue.get("body") or "").splitlines():
            match = _REQUEST_MARKER.fullmatch(line.strip())
            if match and _SUBJECT.fullmatch(match.group(2)):
                out.append({"issue": number, "kind": match.group(1), "subject": match.group(2),
                            "state": issue["state"], "opened_at": _time(issue.get("created_at")),
                            "closed_at": _time(issue.get("closed_at"))})
                break
    return sorted(out, key=lambda r: r["issue"])


def pulls_of(pulls: list, numbers: set) -> dict:
    """{request issue: [pull request rows]} over the pull requests whose
    body names a request; each row {number, state, merged_at, auto_merge}
    plus, for the findings only, `_lane` and `_opened_at`."""
    out: dict = {}
    for pr in pulls:
        number = pr.get("number")
        if type(number) is not int or number < 1 or pr.get("state") not in ("open", "closed"):
            continue
        named = {int(n) for n in fixture_pr_gate._REF.findall(pr.get("body") or "")} & numbers
        merged_at = _time(pr.get("merged_at"))
        labels = {lab.get("name") for lab in pr.get("labels") or [] if isinstance(lab, dict)}
        row = {"number": number,
               "state": "merged" if merged_at else pr["state"],
               "merged_at": merged_at, "auto_merge": bool(pr.get("auto_merge")),
               "_lane": ((pr.get("user") or {}).get("login") == fixture_pr_gate.AUTHOR
                         and fixture_pr_gate.LABEL in labels),
               "_opened_at": _time(pr.get("created_at"))}
        for issue in named:
            out.setdefault(issue, []).append(row)
    return {k: sorted(v, key=lambda r: r["number"]) for k, v in out.items()}


def _first_added(repo: Path, rel: str) -> str | None:
    """The committer time of the first commit that added `rel`, or None."""
    done = subprocess.run(["git", "-C", str(repo), "log", "--diff-filter=A", "--format=%cI",
                           "--", rel], capture_output=True, text=True, check=False)
    lines = done.stdout.split() if done.returncode == 0 else []
    return _time(lines[-1]) if lines else None


def origin_fixtures(repo: Path) -> list:
    """[{path, subject, origin_kind, source, request, added_at}] for every
    committed fixture.yaml with a valid `origin:`, by path."""
    out = []
    evals = repo / "evals"
    for path in sorted(evals.rglob("fixture.yaml")) if evals.is_dir() else []:
        if path.is_symlink():
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if not isinstance(doc, dict) or fixture_pr_gate.origin_problem(doc.get("origin")):
            continue
        rel = path.parent.relative_to(repo).as_posix()
        parts = rel.split("/")
        subject = (f"guidance/{parts[2]}" if parts[1] == "guidance" and len(parts) > 2
                   else parts[1] if len(parts) > 1 else None)
        if subject is None or not _SUBJECT.fullmatch(subject):
            continue
        origin = doc["origin"]
        out.append({"path": rel, "subject": subject, "origin_kind": origin["kind"],
                    "source": origin["source"], "request": origin["request"],
                    "added_at": _first_added(repo, f"{rel}/fixture.yaml")})
    return out


def _record_path(record: dict, guidance: bool) -> str:
    if guidance:
        return f"evals/guidance/{record['skill']}/{record['fixture']}"
    return "/".join(p for p in ("evals", record["skill"], record["fixture"]) if p)


def _run_id(run_dir: str) -> str | None:
    parts = run_dir.split("/")
    return parts[1] if parts[0] == "routine-results" and len(parts) > 1 else None


def _estimate(tree: Path, run_id: str) -> tuple:
    """(usd, points) of one routine run's cost_estimate.json; None for each
    figure that is absent or not a number."""
    try:
        doc = json.loads((tree / "routine-results" / run_id / "cost_estimate.json")
                         .read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None, None

    def number(value):
        return float(value) if isinstance(value, (int, float)) \
            and not isinstance(value, bool) and value >= 0 else None

    return (number(doc.get("usd")), number(doc.get("points"))) if isinstance(doc, dict) \
        else (None, None)


def fixture_runs(tree: Path, evals_dir: Path, as_of: str) -> tuple:
    """({fixture path: {"runs": set of run dirs, "with": [passed, total],
    "without": [passed, total]}}, {routine run id: set of fixture paths}):
    the validated runs, as explorer_data reads them."""
    index = compute_gates.build_index(tree, evals_dir, as_of)
    by_path: dict = {}
    by_run: dict = {}
    for records, guidance in ((index["runs"] + index["bare_runs"], False),
                              (index["guidance_runs"], True)):
        for record in records:
            path = _record_path(record, guidance)
            entry = by_path.setdefault(path, {"runs": set(), "with": [0, 0], "without": [0, 0]})
            entry["runs"].add(record["path"])
            run_id = _run_id(record["path"])
            if run_id is not None:
                by_run.setdefault(run_id, set()).add(path)
            if guidance and record.get("pair") != "in_situ":
                continue
            numbers = explorer_data.arm_numbers(record)
            if numbers is not None and record["role"] in ("with", "without"):
                entry[record["role"]][0] += numbers["checks_passed"]
                entry[record["role"]][1] += numbers["checks_total"]
    return by_path, by_run


def _sum(values: list):
    return None if any(v is None for v in values) else sum(values)


def build_report(issues: list, pulls: list, fixtures: list, runs: dict, by_run: dict,
                 tree: Path, now: datetime) -> dict:
    """The report (module docstring). `fixtures` is `origin_fixtures`',
    `runs` and `by_run` `fixture_runs`' result; `now` is a UTC datetime."""
    stamp = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    requests = requests_of(issues)
    linked = pulls_of(pulls, {r["issue"] for r in requests})
    findings = []
    seen_prs = {}
    for request in requests:
        rows = linked.get(request["issue"], [])
        request["prs"] = [{k: v for k, v in row.items() if not k.startswith("_")}
                          for row in rows]
        if request["state"] == "open" and _older(request["opened_at"], now, STALE_REQUEST_DAYS) \
                and not any(row["state"] in ("open", "merged") for row in rows):
            findings.append(finding("stale-request", request["issue"], request["subject"],
                                    f"{REPO_URL}/issues/{request['issue']}"))
        for row in rows:
            seen_prs.setdefault(row["number"], (row, request["subject"]))
    for number, (row, subject) in sorted(seen_prs.items()):
        if row["_lane"] and row["state"] == "open" and not row["auto_merge"] \
                and _older(row["_opened_at"], now, STUCK_PR_DAYS):
            findings.append(finding("stuck-pr", number, subject, f"{REPO_URL}/pull/{number}"))
    out_fixtures = []
    for fixture in fixtures:
        entry = runs.get(fixture["path"], {"runs": set(), "with": [0, 0], "without": [0, 0]})
        # One cost per routine run, which may hold several of the fixture's
        # run directories (a fire's model cells); unknown for a run outside
        # routine-results or shared with another fixture.
        costs = [(None, None) if rid is None or by_run.get(rid) != {fixture["path"]}
                 else _estimate(tree, rid)
                 for rid in sorted({_run_id(d) for d in entry["runs"]}, key=str)]
        usd, points = [c[0] for c in costs], [c[1] for c in costs]
        row = {**fixture, "runs": len(entry["runs"]),
               "with_pass_rate": entry["with"][0] / entry["with"][1] if entry["with"][1] else None,
               "without_pass_rate": (entry["without"][0] / entry["without"][1]
                                     if entry["without"][1] else None),
               "cost_points": _sum(points), "cost_usd": _sum(usd)}
        out_fixtures.append(row)
        if row["runs"] == 0 and _older(fixture["added_at"], now, UNUSED_FIXTURE_DAYS):
            findings.append(finding("unused-fixture", slug(fixture["path"]), fixture["subject"],
                                    f"{REPO_URL}/tree/main/{fixture['path']}"))
    merged = {n for n, (row, _s) in seen_prs.items() if row["state"] == "merged"}
    totals = {
        "requests_open": sum(r["state"] == "open" for r in requests),
        "requests_closed": sum(r["state"] == "closed" for r in requests),
        "prs_merged": len(merged),
        "fixtures_real_work": sum(f["origin_kind"] == "real-work" for f in out_fixtures),
        "fixtures_invented": sum(f["origin_kind"] == "invented" for f in out_fixtures),
        "fixture_runs": sum(f["runs"] for f in out_fixtures),
        "cost_points": _sum([f["cost_points"] for f in out_fixtures]),
        "cost_usd": _sum([f["cost_usd"] for f in out_fixtures]),
    }
    return {"schema": SCHEMA, "generated_at": stamp, "requests": requests,
            "fixtures": out_fixtures, "totals": totals,
            "findings": sorted(findings, key=lambda f: f["finding_id"])}


def slug(path: str) -> str:
    """A fixture path as a Finding-ID slug: `evals/` dropped, lowercase,
    every run of other characters one hyphen."""
    rest = path[len("evals/"):] if path.startswith("evals/") else path
    return re.sub(r"[^a-z0-9]+", "-", rest.lower()).strip("-")


def finding(kind: str, ident, subject: str, url: str) -> dict:
    issue_kind, severity = KINDS[kind]
    return {"finding_id": f"{ALERT_PREFIX}{kind}-{ident}", "kind": issue_kind,
            "severity": severity, "subject": subject, "url": url}


# ---------------------------------------------------------------------------
# Alerts.

def checked(item) -> dict:
    """A finding from the report, every field validated against what
    `finding` writes, or QueueError."""
    if not isinstance(item, dict) or set(item) != {"finding_id", "kind", "severity",
                                                   "subject", "url"}:
        raise QueueError("a finding is not {finding_id, kind, severity, subject, url}")
    match = _FINDING_ID.fullmatch(item["finding_id"]) \
        if isinstance(item["finding_id"], str) else None
    if match is None:
        raise QueueError("a finding has no valid finding_id")
    kind = match.group(1) or match.group(3)
    ident = match.group(2) or match.group(4)
    url_re = {"stale-request": _ISSUE_URL, "stuck-pr": _PULL_URL,
              "unused-fixture": _FIXTURE_URL}[kind]
    url = item["url"] if isinstance(item["url"], str) else ""
    url_match = url_re.fullmatch(url)
    if url_match is None or (kind != "unused-fixture" and url_match.group(1) != ident) \
            or (kind == "unused-fixture" and slug(url_match.group(1)) != ident) \
            or ".." in url:
        raise QueueError("a finding's url does not match its finding_id")
    if (item["kind"], item["severity"]) != KINDS[kind] \
            or not isinstance(item["subject"], str) or not _SUBJECT.fullmatch(item["subject"]):
        raise QueueError("a finding's kind, severity or subject is not valid")
    return {**item, "_type": kind, "_ident": ident,
            "_path": url_match.group(1) if kind == "unused-fixture" else None}


def alert_body(item: dict, checked_at: str, run_url: str | None) -> tuple:
    """(title, body) of a finding's issue: fixed text and validated values."""
    kind, ident, subject, url = item["_type"], item["_ident"], item["subject"], item["url"]
    if kind == "stale-request":
        title = f"Fixture queue: request #{ident} has no PR after {STALE_REQUEST_DAYS} days"
        evidence = (f"The fixture request {url} (subject `{subject}`) has been open for "
                    f"{STALE_REQUEST_DAYS} days or more, and no open or merged pull request "
                    "names it with `Refs`.")
        recommendation = ("fix: check that the fleet worker's issue pass still picks up "
                          "`agent-ready` issues in this repository, and that the request's "
                          "body asks for something a worker can do.")
    elif kind == "stuck-pr":
        title = (f"Fixture queue: pull request #{ident} open {STUCK_PR_DAYS}+ days "
                 "without auto-merge")
        evidence = (f"The fleet worker's pull request {url}, answering a fixture request for "
                    f"`{subject}`, has been open for {STUCK_PR_DAYS} days or more with "
                    "auto-merge off.")
        recommendation = ("fix: read the pull request's `fixture-pr-gate.yml` run: its "
                          "`reason=` line says why `scripts/fixture_pr_gate.py` did not arm "
                          "it (a fixture without a valid `origin:`, a change outside the new "
                          "fixture directories), then correct the pull request or the gate.")
    else:
        title = (f"Fixture queue: fixture {item['_path']} has no runs "
                 f"{UNUSED_FIXTURE_DAYS} days after it landed")
        evidence = (f"The fixture {url} (subject `{subject}`), added for a fixture request, "
                    f"was committed {UNUSED_FIXTURE_DAYS} days ago or more and has no "
                    "ingested run on `persistent/eval-results`.")
        recommendation = ("fix: check that it reached `evals/scheduled.yml` (a skill fixture "
                          "waits in `evals/unscheduled.yml` until "
                          "`scripts/contextualize_fixtures.py` gives it a context), and that "
                          "its eval fires deliver results.")
    lines = [f"Kind: {item['kind']}", f"Severity: {item['severity']}",
             f"Finding-ID: {item['finding_id']}", alert_marker(item["finding_id"]), "",
             evidence, f"Checked {checked_at} UTC (scripts/fixture_queue.py).", "",
             f"Recommendation: {recommendation}", "",
             "This issue closes itself once the finding clears."]
    if run_url:
        lines += ["", f"{work_item_issues.RUN_PREFIX}{run_url}"]
    lines += ["", "---", "_Filed by explorer-data.yml (scripts/fixture_queue.py)._"]
    return title, "\n".join(lines) + "\n"


def alert_marker(finding_id: str) -> str:
    return f"<!-- skills-evals:fixture-queue:{finding_id} -->"


def plan_alerts(report: dict, issues: list, run_url: str | None) -> list:
    """The actions for the report's findings against github-actions[bot]'s
    issues (work_item_issues.fetch_issues' rows)."""
    if not isinstance(report, dict) or report.get("schema") != SCHEMA \
            or not isinstance(report.get("findings"), list) \
            or not (isinstance(report.get("generated_at"), str)
                    and _TIME.fullmatch(report["generated_at"])):
        raise QueueError("the report is not a schema 1 fixture queue report")
    findings = {}
    for item in report["findings"]:
        one = checked(item)
        findings[one["finding_id"]] = one
    known: dict = {}
    for issue in sorted(issues, key=lambda i: i["number"]):
        for line in issue["body"].splitlines():
            match = _ALERT_MARKER.fullmatch(line.strip())
            if match:
                slot = known.setdefault(match.group(1), {"open": None, "closed": None})
                if slot[issue["state"]] is None:
                    slot[issue["state"]] = issue
                break
    actions = []
    for fid, item in sorted(findings.items()):
        slot = known.get(fid, {"open": None, "closed": None})
        if slot["open"]:
            actions.append({"finding_id": fid, "issue": slot["open"]["number"],
                            "action": "none", "reason": "the open issue stands"})
            continue
        title, body = alert_body(item, report["generated_at"], run_url)
        if slot["closed"]:
            actions.append({"finding_id": fid, "issue": slot["closed"]["number"],
                            "action": "reopen-issue", "reason": "the finding is back",
                            "comment": f"The finding is back as of {report['generated_at']} "
                                       f"UTC: {item['url']}. Reopening."
                                       + (f"\n\n{work_item_issues.RUN_PREFIX}{run_url}"
                                          if run_url else "")})
            continue
        actions.append({"finding_id": fid, "issue": None, "action": "create-issue",
                        "reason": "no issue", "title": title, "body": body})
    for fid, slot in sorted(known.items()):
        found = slot["open"]
        if fid in findings or found is None:
            continue
        if HOLD_LABEL in (found.get("labels") or []):
            actions.append({"finding_id": fid, "issue": found["number"], "action": "none",
                            "reason": "the owner holds the issue (on-hold)"})
            continue
        actions.append({"finding_id": fid, "issue": found["number"], "action": "close-issue",
                        "reason": "the finding cleared",
                        "comment": f"The fixture queue report of {report['generated_at']} UTC "
                                   "no longer lists this finding. Closing."
                                   + (f"\n\n{work_item_issues.RUN_PREFIX}{run_url}"
                                      if run_url else "")})
    return actions


def alert_commands(action: dict) -> list:
    issue = str(action["issue"])
    if action["action"] == "create-issue":
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 "--label", ALERT_LABEL, "--body-file", "-"]]
    if action["action"] == "reopen-issue":
        return [["gh", "issue", "reopen", issue, "-R", EVALS_REPO],
                ["gh", "issue", "comment", issue, "-R", EVALS_REPO, "--body-file", "-"]]
    if action["action"] == "close-issue":
        return [["gh", "issue", "comment", issue, "-R", EVALS_REPO, "--body-file", "-"],
                ["gh", "issue", "close", issue, "-R", EVALS_REPO, "--reason", "completed"]]
    return []


# ---------------------------------------------------------------------------
# Command line.

def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise QueueError(f"{path.name} is not readable JSON ({type(exc).__name__})") from None


def report_main(args) -> int:
    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
        if now.tzinfo is None:
            raise QueueError("--now has no time zone")
        issues, pulls = flatten(_load(args.issues)), flatten(_load(args.pulls))
        runs, by_run = fixture_runs(args.results_tree, args.repo / "evals",
                                    now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        report = build_report(issues, pulls, origin_fixtures(args.repo), runs, by_run,
                              args.results_tree, now)
        text = json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n"
    except (QueueError, ValueError, OSError, KeyError, TypeError) as exc:
        print(f"fixture_queue: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    totals = report["totals"]
    print(f"fixture queue: {totals['requests_open']} open request(s), "
          f"{len(report['fixtures'])} fixture(s) with an origin, "
          f"{len(report['findings'])} finding(s)")
    return 0


def alerts_main(args, gh, out) -> int:
    try:
        actions = plan_alerts(_load(args.report), work_item_issues.fetch_issues(gh),
                              args.run_url)
    except (QueueError, KeyError, TypeError) as exc:
        print(f"fixture_queue: {exc}", file=sys.stderr)
        return 2
    except retire_skill.RetireError as exc:
        print(f"fixture_queue: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        out.write(json.dumps({"dry_run": True, "actions": [
            {**a, "would_run": alert_commands(a)} for a in actions]},
            indent=2, sort_keys=True) + "\n")
        return 0
    if any(a["action"] == "create-issue" for a in actions):
        try:
            work_item_issues.ensure_labels(gh, [ALERT_LABEL], ALERT_LABELS)
        except retire_skill.RetireError as exc:
            print(f"fixture_queue: {exc}", file=sys.stderr)
            return 1
    failed = 0
    for action in actions:
        stdin = action.get("body") or action.get("comment")
        try:
            for command in alert_commands(action):
                gh(command[1:], stdin if "--body-file" in command else None)
        except retire_skill.RetireError as exc:
            failed += 1
            print(f"fixture_queue: {action['finding_id']}: {exc}", file=sys.stderr)
            continue
        if action["action"] != "none":
            out.write(f"{action['action']}: {action['finding_id']}"
                      + (f" (#{action['issue']})" if action["issue"] else "") + "\n")
    return 1 if failed else 0


def main(argv: list | None = None, *, gh=retire_skill.default_gh, out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("report")
    r.add_argument("--issues", type=Path, required=True)
    r.add_argument("--pulls", type=Path, required=True)
    r.add_argument("--repo", type=Path, required=True)
    r.add_argument("--results-tree", type=Path, required=True)
    r.add_argument("--now", required=True)
    r.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("alerts")
    a.add_argument("--report", type=Path, required=True)
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--run-url", default=None)
    args = parser.parse_args(argv)
    if args.command == "report":
        return report_main(args)
    return alerts_main(args, gh, out)


if __name__ == "__main__":
    sys.exit(main())
