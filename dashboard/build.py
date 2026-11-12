#!/usr/bin/env python3
"""Build the project dashboard's snapshot datasets.

Every dataset is computed from three kinds of input, so nothing on the page is
typed by hand that a read could supply:

  --results  an extracted copy of the `persistent/eval-results` branch
             (test runs, the allowance meter, usage counts)
  --inputs   JSON dumps the refresh session collects each run from GitHub and
             the project (threads, scheduled tasks, workflow runs, issues and
             PRs labeled needs-owner, environment reviews, loop status);
             see README.md, "Inputs"
  --config   the owner's own lists that no read can supply (cleanup items,
             gate conditions, decisions, routine descriptions, loop design);
             kept outside this public repo, see config.example/

The repo's own evals/budget.yml and evals/roster.yml are read directly.

It also uploads the public evals document unchanged as the `explorer`
dataset, which most of the page reads, and with --spend writes the weekly cost
totals in the shape of `spend/weekly.json` (explorer/schema.json, `spend_file`)
for the refresh to put on the results branch.

Usage:
  python3 dashboard/build.py --results <dir> --inputs <dir> --config <dir> --out <dir> [--now ISO] [--spend <file>]
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from eval_facts import (add_costs, arm_model, cli_version, cost, fired_at, iso, judge,  # noqa: E402,F401
                        objective, scored_runs)

PLACEHOLDER_ID = "none"
HB_FIXED_WINDOW = timedelta(days=7)


def parse(ts):
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load(path, default=None):
    if not os.path.exists(path):
        if default is None:
            sys.exit(f"missing input {path}")
        return default
    with open(path) as f:
        return json.load(f)


def model_name(model_id):
    """claude-sonnet-5-5 -> Sonnet 5.5"""
    parts = (model_id or "").split("-")
    if len(parts) < 3 or parts[0] != "claude":
        return model_id
    return parts[1].capitalize() + " " + ".".join(parts[2:])


# --- Tests tab -----------------------------------------------------------------

def eval_rows(er, report_base):
    """Paired runs (with/without a skill or guidance section) and bare baseline runs
    (scripts/eval_facts.py `scored_runs`), each list given one placeholder row when empty."""
    rows, bare = scored_runs(er, report_base)
    if not bare:
        bare = [{"run_id": PLACEHOLDER_ID, "fired_at": None, "fixture": "No bare runs yet", "skill": None,
                 "model": None, "trials": None, "bare": None, "checks": None, "bare_share": None,
                 "cost_usd": None, "report_url": None, "paired_at": None, "with_share": None,
                 "without_share": None}]
    if not rows:
        rows = [{"run_id": PLACEHOLDER_ID, "fired_at": None, "fixture": "No scored runs yet", "skill": None,
                 "model": None, "trials": None, "with_skill": None, "without_skill": None, "checks": None,
                 "gain": None, "with_judge": None, "without_judge": None, "judge": None, "with_share": None,
                 "without_share": None, "cost_usd": None, "meter_points": None, "account_week_after": None,
                 "cli": None, "report_url": None}]
    return rows, bare


#: Hours between dashboard refreshes (7:29 AM and 7:29 PM ET), the one place the
#: interval is written: a snapshot dataset's `staleAfterHours` in page/datasets.json
#: must exceed it, which test_issue_dashboard_build checks.
REFRESH_INTERVAL_HOURS = 12


def allowance(er, now):
    sys.path.insert(0, str(REPO / "scripts"))
    sys.path.insert(0, str(REPO / "harness"))
    import yaml
    import allowance_guard as g
    limits = yaml.safe_load(open(REPO / "evals" / "budget.yml"))
    # The guard caps spend since the account's last weekly reset (`window_start`; the
    # guard's own reset, or a manual one), not a rolling seven days. Every figure below
    # is the guard's own number for that window, so the page never recomputes it.
    # Fires still waiting for results are unknown here (no fire log), so `pending` is
    # 0 and `room_points` is what the guard would say with no fire in flight.
    since = g.window_start(now)
    runs = g.ingested_runs(Path(er), now, since)
    st = g.account(Path(er), limits, now, (len(runs), 0), since=since)
    found = g.newest_snapshot(runs)
    # The next scheduled reset (Monday 17:00 UTC), even when a manual reset started this window.
    resets = iso(g.ACCOUNT_WEEK_RESET + ((now - g.ACCOUNT_WEEK_RESET) // g.WINDOW + 1) * g.WINDOW)
    return [{
        "measure": "eval_spend_since_reset", "window_start": iso(since), "points": st["spent"] * 100, "runs": st["runs"],
        "account_week_used": None if st["account_used"] is None else st["account_used"] * 100,
        "account_reading_at": iso(found[0]) if found else None, "week_resets_at": resets,
        "week_elapsed": st["week_elapsed"], "pace_room_points": st["pace_room"] * 100,
        "room_points": g.room(st) * 100, "committed_points": st["committed"] * 100,
        "pending_points": st["pending"] * 100,
        "stop_left_points": None if st["stop_left"] is None else st["stop_left"] * 100,
        "reservation_points": st["reservation"] * 100, "computed_at": iso(now),
    }]


BUDGET_KEYS = ["weekly_cap", "per_run_cap", "per_run_overrun", "stop_when_account_above"]


def budget():
    import yaml
    b = yaml.safe_load(open(REPO / "evals" / "budget.yml"))
    return [{"setting": k, "value": b[k]} for k in BUDGET_KEYS if k in b]


def roster(cfg):
    """Model list rows from evals/roster.yml; `why` text and dropped models come from config."""
    import yaml
    r = yaml.safe_load(open(REPO / "evals" / "roster.yml"))
    why = cfg.get("why", {})
    link = cfg.get("link")
    rows = [{"model": model_name(a["id"]), "id": a["id"], "role": "Tested", "status": "In use",
             "why": why.get(a["id"], " ".join((a.get("reason") or "").split())), "link": link}
            for a in r.get("arms", [])]
    for key, role in (("judge", "Judge"), ("preflight", "Quick check")):
        m = r.get(key) or {}
        if m.get("id"):
            rows.append({"model": model_name(m["id"]), "id": m["id"], "role": role, "status": "In use",
                         "why": why.get(m["id"], " ".join((m.get("reason") or "").split())), "link": link})
    seen = {x["id"] for x in rows}
    rows += [d for d in cfg.get("dropped", []) if d["id"] not in seen]
    return rows


# --- Impact tab ----------------------------------------------------------------

# Outcome keys from _agent-guidance scripts/impact-report.js (kind "repo" rows from CI).
OUTCOME_KEYS = ["prs_opened", "prs_merged", "prs_closed_unmerged", "prs_reverted", "agent_prs_merged", "ci_red_after"]

# Each producer names what it read in its own field: the transcript census counts sessions,
# the local hook log counts git hook runs, the CI report counts repos, the cloud guidance
# records count cloud sessions.
# #562 (2026-11-02): the loaded-copy records count skill uses.
SCANNED_KEYS = [("sessions_scanned", "sessions"), ("runs_scanned", "git hook runs"), ("repos_scanned", "repos"),
                ("records_scanned", "cloud sessions"), ("events_scanned", "skill uses")]


def scanned(s):
    for key, unit in SCANNED_KEYS:
        if s.get(key) is not None:
            return s[key], unit
    return None, None


def usage(er):
    """Concatenate every usage/weekly-*.json (schema 1); counts stay exact.

    Returns (rows, sources, digests). A `skill-digest` row (#562) is a second
    view of the same skill uses, by loaded copy, so it goes to `digests` and
    never to `rows`, where a sum over skills would count every use twice.
    This is the one place it is split off, so the page needs no filter."""
    rows, sources, digests = [], [], []
    for path in sorted(glob.glob(os.path.join(er, "usage", "weekly-*.json"))):
        name = os.path.basename(path)
        d = load(path)
        if d.get("schema") != 1:
            sys.exit(f"{name}: schema {d.get('schema')!r}, expected 1; update build.py and the Impact tab")
        for s in d.get("sources", []):
            count, unit = scanned(s)
            # Scope alone repeats once a scope has a source per surface (#562).
            sources.append({"key": f"{name}|{s.get('scope')}|{s.get('surface')}", "file": name, "surface": s.get("surface"),
                            "scope": s.get("scope"), "from": s.get("from"), "to": s.get("to"),
                            "scanned": count, "scanned_unit": unit, "generated_at": d.get("generated_at")})
        for r in d.get("rows", []):
            if r["kind"] == "skill-digest":
                digests.append({"week": r["week"], "name": r["name"], "repo": r.get("repo") or "(no public repo)",
                                "surface": r.get("surface"), "digest": r.get("digest"),
                                "invocations": r.get("invocations", 0), "sessions": r.get("sessions")})
                continue
            o = r.get("outcome") or {}
            # A git hook row named "all" is that week's total across checks; its own kind keeps
            # per-check sums from counting it twice.
            kind = "hook_all" if r["kind"] == "hook" and r["name"] == "all" else r["kind"]
            rows.append({"week": r["week"], "kind": kind, "name": r["name"], "repo": r.get("repo") or "(any repo)",
                         "surface": r.get("surface"), "invocations": r.get("invocations", 0),
                         "sessions": r.get("sessions"), "blocked": r.get("blocked"),
                         "overridden": r.get("overridden"), **{k: o.get(k) for k in OUTCOME_KEYS}})
    if not sources:
        sources = [{"key": PLACEHOLDER_ID, "file": PLACEHOLDER_ID, "surface": None, "scope": None, "from": None,
                    "to": None, "scanned": None, "scanned_unit": None, "generated_at": None}]
    if not rows:
        rows = [{"week": None, "kind": PLACEHOLDER_ID, "name": "No usage counts yet", "repo": None, "surface": None,
                 "invocations": 0, "sessions": None, "blocked": None, "overridden": None,
                 **{k: None for k in OUTCOME_KEYS}}]
    if not digests:
        digests = [{"week": None, "name": "No loaded-copy counts yet", "repo": None, "surface": None,
                    "digest": PLACEHOLDER_ID, "invocations": 0, "sessions": None}]
    return rows, sources, digests


RED_RUN_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+$")


def ci_red_runs(er):
    """Every red agent-checks CI run the impact report lists (usage/weekly-ci.json `red_runs`), newest
    first. A URL that is not a GitHub Actions run page is dropped; a private repo's entry has none."""
    d = load(os.path.join(er, "usage", "weekly-ci.json"), {}) or {}
    out = []
    for i, r in enumerate(d.get("red_runs") or []):
        if not isinstance(r, dict):
            continue
        url = r.get("url") if isinstance(r.get("url"), str) and RED_RUN_URL.match(r["url"]) else None
        out.append({"key": url or f"{r.get('week')}|{r.get('repo')}|{i}", "week": r.get("week"),
                    "repo": r.get("repo"), "created_at": r.get("created_at"),
                    "conclusion": r.get("conclusion"), "url": url})
    out.sort(key=lambda r: (r["week"] or "", r["created_at"] or ""), reverse=True)
    return out or [{"key": PLACEHOLDER_ID, "week": None, "repo": None, "created_at": None,
                    "conclusion": None, "url": None}]


# --- Overview tab: threads, routines, check-ins, waiting -------------------------

THREAD_STATES = {"done": "Done", "working": "Working", "review_ready": "Ready for review",
                 "blocked": "Waiting on you", "failed": "Failed", "stopped": "Stopped"}


def thread_state(s):
    """A thread's label. A resolved thread is done whatever its last state was;
    an unresolved review-ready one waits on the owner."""
    if s.get("resolved"):
        return "Done"
    if s.get("state") == "review_ready":
        return "Ready for your review"
    return THREAD_STATES.get(s.get("state"), s.get("state"))


def threads(dump, site, branches=None):
    """Rows from a list_threads dump (its `sessions` list, all pages joined).

    `session` (the id after `cse_`/`session_`) and `branch` (the thread's own git
    branch, from `thread_branches.json`) let the page tell which thread opened a PR.
    """
    titles = site.get("thread_titles", {})
    branches = branches or {}
    sess = lambda s: re.sub(r"^(cse|session)_", "", s.get("session_id") or "")
    rows = [{"title": titles.get(s["thread_id"], s["title"]),
             "state": thread_state(s),
             "last_active": s.get("last_activity_at"),
             "session": sess(s),
             "branch": branches.get(sess(s), ""),
             "link": site["thread_url"] + s["thread_id"]} for s in dump]
    rows.sort(key=lambda r: r["last_active"] or "", reverse=True)
    return rows


def next_cron(expr, after):
    """Next fire time of a five-field UTC cron with numeric minute/hour/day-of-week fields."""
    try:
        minute, hour, dom, month, dow = expr.split()
    except ValueError:
        return None
    if dom != "*" or month != "*":
        return None

    def values(field, lo, hi):
        if field == "*":
            return set(range(lo, hi + 1))
        out = set()
        for part in field.split(","):
            if "-" in part:
                a, b = part.split("-")
                out |= set(range(int(a), int(b) + 1))
            else:
                out.add(int(part))
        return out
    try:
        mins, hours, days = values(minute, 0, 59), values(hour, 0, 23), {d % 7 for d in values(dow, 0, 7)}
    except ValueError:
        return None
    t = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(8 * 24 * 60):
        if t.minute in mins and t.hour in hours and (t.isoweekday() % 7) in days:
            return iso(t)
        t += timedelta(minutes=1)
    return None


TRIGGER_RESULT = {"ROUTINE_RUN_STATUS_SUCCEEDED": "Succeeded", "ROUTINE_RUN_STATUS_FAILED": "Failed",
                  "ROUTINE_RUN_STATUS_RUNNING": "Running", "ROUTINE_RUN_STATUS_PENDING": "Running"}
RUN_RESULT = {"success": "Succeeded", "failure": "Failed", "cancelled": "Cancelled", "timed_out": "Failed",
              "skipped": "Skipped"}


def routines(cfg, triggers, workflow_runs, now, workflow_states=None):
    """One row per routine. Config gives the words; the last and next run and health come from reads."""
    rows = []
    for r in cfg:
        if r.get("retired"):
            continue  # the table and its "N of M healthy" count cover live routines only
        src = r.get("source") or {}
        last_run = last_result = next_run = None
        enabled = True
        if src.get("kind") == "trigger":
            t = (triggers.get(src["id"]) or {}).get("trigger") or triggers.get(src["id"]) or {}
            lr = t.get("last_run") or {}
            last_run = lr.get("fired_at")
            last_result = TRIGGER_RESULT.get(lr.get("status"), lr.get("status")) if lr else None
            next_run = t.get("next_run_at")
            enabled = t.get("enabled", True)
        elif src.get("kind") == "workflow":
            key = src["repo"] + ":" + src["workflow"]
            runs = workflow_runs.get(key) or []
            # A workflow turned off in GitHub (disabled_manually, disabled_inactivity) reads as Paused.
            enabled = (workflow_states or {}).get(key, "active") == "active"
            runs = sorted(runs, key=lambda x: x.get("created_at") or "", reverse=True)
            if runs:
                last_run = runs[0].get("created_at")
                last_result = ("Running" if runs[0].get("status") != "completed"
                               else RUN_RESULT.get(runs[0].get("conclusion"), runs[0].get("conclusion")))
            if src.get("cron"):
                next_run = next_cron(src["cron"], now)
        last_run = iso(parse(last_run)) if last_run else r.get("last_run")
        next_run = iso(parse(next_run)) if next_run else None
        if not enabled:
            health = "Paused"
        elif last_result == "Failed":
            health = "Failing"
        elif last_result == "Cancelled":
            health = "Check"
        elif not last_run:
            # No recorded run is never "OK". It is "Late" once a run was due (its next run
            # is past, or it expects runs and none is scheduled), else "Not run yet".
            due = (next_run and parse(next_run) <= now) or (r.get("expect_every_hours") and not next_run)
            health = "Late" if due else "Not run yet"
        elif r.get("expect_every_hours") and now - parse(last_run) > timedelta(hours=2 * r["expect_every_hours"]):
            health = "Late"
        else:
            health = "OK"
        rows.append({"name": r["name"], "what": r["what"], "schedule": r["schedule"], "last_run": last_run,
                     "last_result": last_result, "next_run": next_run,
                     "health": health, "note": r.get("note", ""), "id": src.get("id") or src.get("workflow"),
                     "link": r.get("link")})
    return rows


WORKFLOW_STATE = {"queued": "Queued", "waiting": "Queued", "pending": "Queued", "requested": "Queued",
                  "in_progress": "Running"}
CONCLUSION_STATE = {"success": "Succeeded", "failure": "Failed", "timed_out": "Failed",
                    "startup_failure": "Failed", "cancelled": "Cancelled", "skipped": "Skipped",
                    "neutral": "Skipped", "action_required": "Needs approval"}
ROUTINE_STATE = {"SUCCEEDED": "Succeeded", "FAILED": "Failed", "PENDING": "Running", "RUNNING": "Running"}
STREAM_DAYS = 7
STREAM_CAP = 500
PROBLEM_STATES = ("Failed", "Cancelled", "Needs approval")


def run_stream(dump, now):
    """Recent workflow runs and scheduled-task runs, newest first, for the console tab."""
    cutoff = now - timedelta(days=STREAM_DAYS)
    seen = {}

    def add(key, at, row):
        when = parse(at)
        if key and when and when >= cutoff and key not in seen:
            seen[key] = {"key": key, "at": iso(when), **row}

    for w in dump.get("workflow_runs") or []:
        if w.get("status") == "completed":
            c = w.get("conclusion") or ""
            state = CONCLUSION_STATE.get(c, c.replace("_", " ").capitalize() or "Done")
            start, end = parse(w.get("created_at")), parse(w.get("updated_at"))
            dur = int((end - start).total_seconds()) if start and end else None
        else:
            state = WORKFLOW_STATE.get(w.get("status"), str(w.get("status") or "").replace("_", " ").capitalize())
            dur = None
        add(w.get("html_url"), w.get("created_at"), {
            "kind": "workflow", "source": (w.get("repo") or "").split("/")[-1], "name": w.get("workflow"),
            "title": w.get("display_title") or w.get("workflow"), "state": state,
            "duration_s": max(dur, 0) if dur is not None else None, "link": w.get("html_url")})
    for r in dump.get("routine_runs") or []:
        status = str(r.get("status") or "").replace("ROUTINE_RUN_STATUS_", "")
        done = status not in ("PENDING", "RUNNING") and r.get("finished_at")
        dur = int((parse(r["finished_at"]) - parse(r["fired_at"])).total_seconds()) if done and r.get("fired_at") else None
        add(f"{r.get('trigger_id')}@{r.get('fired_at')}", r.get("fired_at"), {
            "kind": "routine", "source": "scheduled task", "name": r.get("name"), "title": r.get("name"),
            "state": ROUTINE_STATE.get(status, status.replace("_", " ").capitalize()),
            "duration_s": max(dur, 0) if dur is not None else None,
            "link": "https://claude.ai/scheduled-task/" + str(r.get("trigger_id"))})
    # Problems stay for the whole window; the cap trims only the rest, so a busy week cannot hide a failure.
    rows = sorted(seen.values(), key=lambda r: r["at"], reverse=True)
    problems = [r for r in rows if r["state"] in PROBLEM_STATES]
    keep = {id(r) for r in problems} | {id(r) for r in [r for r in rows if r["state"] not in PROBLEM_STATES][:STREAM_CAP]}
    rows = [r for r in rows if id(r) in keep]
    return rows or [{"key": PLACEHOLDER_ID, "at": None, "kind": None, "source": None,
                     "name": "No runs in the last 7 days", "title": None, "state": None,
                     "duration_s": None, "link": None}]


def checkins(trigger_list, channel_id, now):
    """Pending one-shot scheduled tasks of this project (list_triggers, recurring=false)."""
    rows = [{"when": t["run_once_at"], "what": t.get("name") or "Check-in", "id": t["id"]}
            for t in trigger_list
            if t.get("run_once_at") and t.get("enabled", True) and parse(t["run_once_at"]) > now
            and (not channel_id or t.get("hearth_channel_id") == channel_id)]
    rows.sort(key=lambda r: r["when"])
    return rows or [{"when": None, "what": "None scheduled right now", "id": PLACEHOLDER_ID}]


def waiting(snap, needs_owner, reviews, open_heads, thread_dump, link_states, site):
    """Everything that waits on the owner, from reads first and the manual list last.

    A run waiting on an environment review counts only on the current head of an open
    PR: older runs on the same branch stay `waiting` forever and decide nothing.
    """
    rows = []
    for it in needs_owner:
        labels = {(lb.get("name") if isinstance(lb, dict) else lb) for lb in it.get("labels") or []}
        if "on-hold" in labels or it.get("state", "open") != "open":
            continue
        repo = it.get("repository") or "/".join((it.get("repository_url") or "").split("/")[-2:])
        rows.append({"item": it["title"], "why": "Labeled needs-owner", "since": it.get("created_at"),
                     "link": it["html_url"], "where": repo})
    for rv in reviews:
        if rv.get("head_sha") not in set(open_heads.get(rv["repo"], [])):
            continue
        rows.append({"item": f"Approve the {rv['environment']} review for {rv['name']}",
                     "why": "A required environment review waits on you", "since": rv.get("created_at"),
                     "link": rv["job_url"], "where": rv["repo"]})
    why = {"blocked": "The thread waits on your answer", "review_ready": "Ready for your review"}
    for s in thread_dump:
        if s.get("state") in why and not s.get("resolved"):
            rows.append({"item": site.get("thread_titles", {}).get(s["thread_id"], s["title"]),
                         "why": why[s["state"]], "since": s.get("last_activity_at"),
                         "link": site["thread_url"] + s["thread_id"], "where": "Thread"})
    groups = {}
    for c in snap.get("cleanup", []):
        if c.get("waiting_on_you") and c["status"] != "Done":
            groups.setdefault(c["waiting_on_you"], []).append(c)
    for reason, items in groups.items():
        rows.append({"item": "Cleanup items " + ", ".join(c["id"] for c in items), "why": reason,
                     "since": min((c.get("waiting_since") or "") for c in items) or None,
                     "link": None, "where": "Cleanup list"})
    for m in snap.get("waiting_manual", []):
        if m.get("link") and link_states.get(m["link"]) in ("closed", "merged"):
            continue
        rows.append(m)
    for r in rows:
        r["id"] = r.get("link") or r["item"]
    return rows or [{"item": "Nothing waiting on you", "why": None, "since": None, "link": None,
                     "where": None, "id": PLACEHOLDER_ID}]


def clean_cleanup(items):
    return [{k: v for k, v in c.items() if k not in ("waiting_on_you", "waiting_since")} for c in items]


# --- Loop tab ------------------------------------------------------------------

GAP_WORDS = {"open": "Not started", "in progress": "In progress", "done": "Done"}


def loop(cfg, status, site):
    gaps = [{"gap": g["gap"], "title": g["title"], "status": GAP_WORDS.get(g["status"], g["status"]),
             "owner": g.get("owner") or "", "link": g.get("pr")} for g in status["gaps"]]
    by = {g["gap"]: g for g in gaps}
    home = site["thread_url"] + cfg["home_thread_id"]

    def derive(ids, override):
        if override:
            return override
        s = [by[i]["status"] for i in ids if i in by]
        if s and all(x == "Done" for x in s):
            return "Done"
        if s and all(x == "Not started" for x in s):
            return "Not started"
        return "In progress"
    stages = []
    for st in cfg["stages"]:
        links = [by[i]["link"] for i in st["gaps"] if i in by and by[i]["link"]]
        stages.append({"order": st["order"], "kind": st["kind"], "stage": st["stage"], "what": st["what"],
                       "status": derive(st["gaps"], st.get("override")), "gaps": ", ".join(st["gaps"]),
                       "link": links[0] if links else home})
    lanes = [{"lane": ln["lane"], "thread": ln["thread"], "link": site["thread_url"] + ln["thread_id"],
              "does": ln["does"], "latest": ln["latest"], "latest_link": ln.get("latest_link")}
             for ln in cfg["lanes"]]
    return stages, cfg["grid"], lanes, gaps


# --- Cost and benefit tab --------------------------------------------------------

# A cost week starts Monday 17:00 UTC (the account's weekly reset) and is labeled by that date.
COST_START = datetime(2026, 10, 19, 17, 0, tzinfo=timezone.utc)
WEEK = timedelta(days=7)
DEFAULT_POINTS_PER_USD = 0.07
BAR_DUE = "2026-12-15"
BAR_JUDGED_AT = datetime(2026, 12, 16, tzinfo=timezone.utc)
BAR_MIN_CHANGES = 3
BAR_MAX_BUILD_POINTS = 10
# The run-level `usage.reasons.meter` of an API-billed summary (harness/run_eval.py `_API_BILLED`);
# a test holds this copy to the harness's.
API_BILLED = "API-billed run: the subscription's account meter does not apply"
# Loop PR head-branch prefix -> kind of change.
LOOP_KINDS = {"eval-improve/": "edit", "draft-skill/": "new skill", "retire-skill/": "removal",
              "eval-guidance-improve/": "guidance edit", "retire-guidance/": "guidance removal"}


def load_jsonl(path):
    """Rows of a JSON-lines file; a missing file is empty and a damaged line is skipped."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("v", 1) == 1:
                rows.append(row)
    return rows


def week_starts(start, now):
    out = [start]
    while out[-1] + WEEK <= now:
        out.append(out[-1] + WEEK)
    return out if now >= start else []


def week_of(t, starts):
    """Index of the week holding instant t, or None outside the weeks."""
    if t is None or not starts or t < starts[0] or t >= starts[-1] + WEEK:
        return None
    return int((t - starts[0]) / WEEK)


def spread(amount, a, b, starts):
    """{week index: share} of `amount` spread uniformly over [a, b]; an empty span is one instant (a)."""
    if not amount or amount <= 0:
        return {}
    if b <= a:
        i = week_of(a, starts)
        return {} if i is None else {i: amount}
    out = {}
    for i, s in enumerate(starts):
        overlap = (min(b, s + WEEK) - max(a, s)).total_seconds()
        if overlap > 0:
            out[i] = amount * overlap / (b - a).total_seconds()
    return out


def session_spend(samples, starts):
    """({week index: dollars}, {week indexes holding backfilled spend}) from session_costs rows.

    Per session, spend between two samples is the rise in cumulative cost (never negative), spread over
    the time between them. A session's cost before its first sample is spread from its creation to
    min(last update, first sample), so it is an estimate."""
    usd, estimated = {}, set()
    by = {}
    for r in samples:
        at = parse(r.get("at"))
        if r.get("cost_usd") is None or not r.get("session_id") or at is None:
            continue
        by.setdefault(r["session_id"], []).append((at, float(r["cost_usd"]), r))
    for rows in by.values():
        rows.sort(key=lambda x: x[0])
        at0, cost0, first = rows[0]
        created = parse(first.get("created_at")) or at0
        updated = parse(first.get("updated_at")) or at0
        for i, share in spread(cost0, created, min(updated, at0), starts).items():
            usd[i] = usd.get(i, 0) + share
            if share > 0:
                estimated.add(i)
        for (a, ca, _), (b, cb, _) in zip(rows, rows[1:]):
            for i, share in spread(max(0, cb - ca), a, b, starts).items():
                usd[i] = usd.get(i, 0) + share
    return usd, estimated


def points_per_usd(rows, build_usd, starts, now):
    """(points per dollar, basis, weeks used): the account meter's reading over all API-equivalent spend.

    For each complete cost week with an account reading (the largest `account_week_after`, a percent, so
    points, among plan runs fired in it): reading divided by that week's thread spend plus plan-run dollars,
    summed over the weeks. Without such a week, the default."""
    points = usd = weeks = 0
    for i, s in enumerate(starts):
        if s + WEEK > now:
            continue
        mine = [r for r in rows if week_of(parse(r["fired_at"]), starts) == i]
        seen = [r["account_week_after"] for r in mine if r.get("account_week_after") is not None]
        if not seen:
            continue
        points += max(seen)
        usd += build_usd.get(i, 0) + sum(r["cost_usd"] or 0 for r in mine)
        weeks += 1
    if not weeks or usd <= 0:
        return DEFAULT_POINTS_PER_USD, f"default {DEFAULT_POINTS_PER_USD}: no complete week with an account reading yet", 0
    return points / usd, (f"account meter \u00f7 all API-equivalent spend over {weeks} complete weeks; assumes nearly "
                          "all account use is this project, so it is an upper bound on points per dollar"), weeks


def api_billed_usd(er, starts):
    """{week index: dollars} of API-billed eval runs (eval.yml's `results/` tree).

    The marker is the run-level `usage.reasons.meter` that harness/run_eval.py writes into every summary
    of an API-billed run; the week is the summary's `usage.started_at`. Trial summaries are skipped:
    their arm's summary already carries their sum."""
    out = {}
    for path in sorted(glob.glob(os.path.join(er, "results", "**", "summary.json"), recursive=True)):
        if "trial-" in path:
            continue
        try:
            d = json.load(open(path))
        except ValueError:
            continue
        usage_ = d.get("usage") if isinstance(d, dict) else None
        if not isinstance(usage_, dict) or (usage_.get("reasons") or {}).get("meter") != API_BILLED:
            continue
        i = week_of(parse(usage_.get("started_at") or usage_.get("ended_at")), starts)
        spent = cost(d)
        if i is not None and spent:
            out[i] = out.get(i, 0) + spent
    return out


def loop_changes(prs):
    """Merged loop PRs: {repo, number, url, kind, subject, merged_at}; unmerged ones are not changes."""
    out, seen = [], set()
    for p in prs:
        ref, merged = p.get("head_ref") or "", parse(p.get("merged_at"))
        kind = next((k for pre, k in LOOP_KINDS.items() if ref.startswith(pre)), None)
        key = (p.get("repo"), p.get("number"))
        if not kind or merged is None or key in seen:
            continue
        seen.add(key)
        out.append({"repo": p.get("repo"), "number": p.get("number"), "url": p.get("url"), "kind": kind,
                    "subject": ref.split("/", 1)[1].split("/")[0], "merged_at": merged})
    return out


def decided_count(explorer):
    """Skills plus guidance sections whose verdict is a decided one (anything but none or insufficient)."""
    rows = list(explorer.get("skills") or []) + list((explorer.get("guidance") or {}).get("sections") or [])
    return sum(1 for r in rows if r.get("verdict") not in (None, "insufficient"))


def week_uses(change, label, usage_rows):
    """Uses in one cost week of a change's subject: a skill's invocations, or the sessions that loaded guidance."""
    if change["kind"].startswith("guidance"):
        return sum(r.get("sessions") or 0 for r in usage_rows
                   if r["kind"] == "guidance" and r["name"] == "full" and r["week"] == label)
    return sum(r.get("invocations") or 0 for r in usage_rows
               if r["kind"] == "skill" and r["name"] == change["subject"] and r["week"] == label)


def r2(v):
    return None if v is None else round(v, 2)


def cost_benefit(er, plan_rows, usage_rows, decisions, samples, owner_msgs, prs, explorer, now, start=COST_START,
                 raw=None):
    """(weeks rows, summary rows) for the Impact group's cost panel. `raw`, a
    dict, receives the week rows and the cost per verdict before rounding."""
    plan = [r for r in plan_rows if r.get("run_id") != PLACEHOLDER_ID]
    usage_rows = [r for r in usage_rows if r["kind"] != PLACEHOLDER_ID]
    starts = week_starts(start, now)
    build_usd, build_est = session_spend(samples, starts)
    ppu, basis, _ = points_per_usd(plan, build_usd, starts, now)
    api = api_billed_usd(er, starts)
    changes = [c for c in loop_changes(prs) if week_of(c["merged_at"], starts) is not None]
    verdicts = decided_count(explorer)
    msgs = {m["message_id"]: m for m in owner_msgs if m.get("message_id") and parse(m.get("sent_at"))}
    weeks, run_usd, week_run_usds = [], 0, []
    for i, s in enumerate(starts):
        label, end = s.date().isoformat(), s + WEEK
        mine = [r for r in plan if week_of(parse(r["fired_at"]), starts) == i]
        run_meter_points = sum(r["meter_points"] or 0 for r in mine)
        week_run_usd = sum(r["cost_usd"] or 0 for r in mine)
        run_usd += week_run_usd
        week_run_usds.append(week_run_usd)
        run_points_est = week_run_usd * ppu
        build_points = build_usd.get(i, 0) * ppu
        api_usd = api.get(i, 0)
        weeks.append({
            "week": label, "run_count": len(mine), "run_points_est": run_points_est, "run_meter_points": run_meter_points, "api_usd": api_usd,
            "build_usd": build_usd.get(i, 0), "build_points": build_points, "build_estimated": i in build_est,
            "total_points": run_points_est + build_points + api_usd * ppu,
            "changes": sum(1 for c in changes if week_of(c["merged_at"], starts) == i),
            "real_work_reach": sum(week_uses(c, label, usage_rows) for c in changes if c["merged_at"] < end),
            "owner_messages": sum(1 for m in msgs.values() if week_of(parse(m["sent_at"]), starts) == i),
            "decisions": sum(1 for d in decisions
                             if week_of(parse(d["date"] + "T17:00:00Z"), starts) == i),
            "verdicts": verdicts if i == len(starts) - 1 else None})
    complete = [w for w, s in zip(weeks, starts) if s + WEEK <= now]
    last = complete[-1] if complete else None
    total_usd = run_usd + sum(build_usd.values()) + sum(api.values())
    reached = 0
    for c in changes:
        if any(week_uses(c, s.date().isoformat(), usage_rows) for s in starts if c["merged_at"] < s + WEEK):
            reached += 1
    bar_changes = reached >= BAR_MIN_CHANGES
    bar_build = last is not None and last["build_points"] < BAR_MAX_BUILD_POINTS
    due = f"Due {BAR_DUE}"
    status = lambda ok: "Met" if ok else "Not met"
    summary = [
        {"key": "cost_per_verdict", "label": "Cost per decided verdict", "value": total_usd / verdicts if verdicts else None,
         "target": None, "status": None,
         "note": f"API-equivalent dollars since {start.date()}: ${total_usd:,.2f} over {verdicts} decided verdicts"},
        {"key": "decision_yield", "label": "Decision yield", "value": f"{len(changes)} of {verdicts}",
         "target": None, "status": None,
         "note": "Loop changes merged since " + str(start.date()) + " out of decided verdicts"
                 + ("" if verdicts else " (no decided verdicts yet)")},
        {"key": "real_work_reach", "label": "Real-work reach, latest complete week",
         "value": last["real_work_reach"] if last else None, "target": None, "status": None,
         "note": "Uses of changed skills and guidance in the week of " + last["week"] if last else "No complete week yet"},
        {"key": "bar_changes", "label": "Changes used in real work", "value": reached,
         "target": f"at least {BAR_MIN_CHANGES}", "status": status(bar_changes),
         "note": f"{due}. Merged loop changes whose subject was used at least once after the merge"},
        {"key": "bar_build", "label": "Build cost, latest complete week", "value": r2(last["build_points"]) if last else None,
         "target": f"< {BAR_MAX_BUILD_POINTS} points a week", "status": status(bar_build),
         "note": f"{due}. " + ("Build spend in the week of " + last["week"] if last else "No complete week yet")},
        {"key": "points_per_usd", "label": "Points per dollar", "value": round(ppu, 4), "target": None,
         "status": None, "note": basis},
    ]
    if now >= BAR_JUDGED_AT:
        summary.append({"key": "bar_verdict", "label": "Dec 15 bar", "target": None, "status": None,
                        "value": "Met: keep the eval system" if bar_changes and bar_build
                        else "Missed: cut back to guidance-only evals", "note": f"Both bars were due {BAR_DUE}"})
    if raw is not None:
        raw["weeks"] = [{**w, "run_usd": u} for w, u in zip(weeks, week_run_usds)]
        raw["cost_per_verdict"] = summary[0]["value"]
        raw["total"] = {"since": start.date().isoformat(), "usd": total_usd, "run_usd": run_usd,
                        "thread_spend_usd": sum(build_usd.values()), "api_usd": sum(api.values()),
                        "verdicts": verdicts, "cost_per_verdict": summary[0]["value"]}
    if not weeks:
        weeks = [{"week": PLACEHOLDER_ID, "run_count": None, "run_points_est": None, "run_meter_points": None, "api_usd": None, "build_usd": None,
                  "build_points": None, "build_estimated": None, "total_points": None, "changes": None,
                  "real_work_reach": None, "owner_messages": None, "decisions": None, "verdicts": None}]
    for w in weeks:
        for k in ("run_points_est", "run_meter_points", "api_usd", "build_usd", "build_points", "total_points"):
            w[k] = r2(w[k])
    for row in summary:
        if isinstance(row["value"], float):
            row["value"] = r2(row["value"]) if row["key"] != "points_per_usd" else row["value"]
    return weeks, summary


def half_built(dump, now):
    """(issue rows, summary rows) for the Overview banner: open half-built or broken findings, plus those fixed in 7 days."""
    dump = dump if isinstance(dump, dict) else {}
    checked = parse(dump.get("checked_at"))
    order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    rows = []
    for it in dump.get("items") or []:
        closed = parse(it.get("closed_at"))
        is_open = it.get("state") == "open"
        if not is_open and (closed is None or now - closed > HB_FIXED_WINDOW):
            continue
        opened = parse(it.get("created_at"))
        rows.append({
            "key": f"{it.get('repo')}#{it.get('number')}", "repo": it.get("repo"), "number": it.get("number"),
            "url": it.get("url"), "title": it.get("title"), "state": "open" if is_open else "closed",
            "kind": it.get("kind") or "unknown", "severity": it.get("severity") or "unknown",
            "finding_id": it.get("finding_id"),
            "needs_owner": "needs you" if "needs-owner" in (it.get("labels") or []) else "", "opened": opened.date().isoformat() if opened else None,
            "age_days": max((now - opened).days, 0) if opened else None, "closed_at": None if is_open else iso(closed)})
    # High severity first, then what needs Adam, then the rest by severity; oldest first within each.
    rows.sort(key=lambda r: (r["state"] != "open", r["severity"] != "high", not r["needs_owner"],
                             order.get(r["severity"], 3), -(r["age_days"] or 0)))
    opened_ = [r for r in rows if r["state"] == "open"]
    count = lambda field, v: sum(1 for r in opened_ if r[field] == v)
    status = "not-checked" if checked is None else "attention" if opened_ else "clear"
    summary = [{"key": "all", "open": len(opened_), "high": count("severity", "high"), "broken": count("kind", "broken"),
                "partial": count("kind", "partial"), "implied_only": count("kind", "implied-only"),
                "idle": count("kind", "idle"), "needs_owner": count("needs_owner", "needs you"), "fixed_7d": len(rows) - len(opened_),
                "checked_at": iso(checked) if checked else None, "incomplete": bool(dump.get("incomplete")), "status": status}]
    return rows or [{"key": PLACEHOLDER_ID, "repo": None, "number": None, "url": None, "title": None, "state": None,
                     "kind": None, "severity": None, "finding_id": None, "needs_owner": "", "opened": None, "age_days": None,
                     "closed_at": None}], summary


def spend_file(raw, now, plan=None):
    """The weekly totals in spend/weekly.json's shape (explorer/schema.json,
    `spend_file`), from cost_benefit's unrounded weeks: totals only, never a
    session or thread row. Each week carries its three dollar parts (`run_usd`,
    `thread_spend_usd`, `api_usd`); cost per verdict is a total over all weeks,
    so it lives once in `total`, never on a week."""
    out = [{"week": w["week"], "eval_runs": w["run_count"], "plan_meter_points": w["run_meter_points"],
            "run_usd": w.get("run_usd"), "api_usd": w["api_usd"], "thread_spend_usd": w["build_usd"]}
           for w in raw.get("weeks") or []]
    doc = {"schema": 1, "generated_at": iso(now), "weeks": out}
    if raw.get("total"):
        doc["total"] = raw["total"]
    if plan:
        doc["plan"] = plan
    return doc


# --- main ----------------------------------------------------------------------

# Datasets the page reads only when they exist: build() never writes them.
OPTIONAL_DATASETS = {"explorer_private"}

def build(results, inputs, config, now, raw=None):
    site = load(os.path.join(config, "site.json"))
    snap = load(os.path.join(config, "snapshots.json"))
    inp = lambda name, default=None: load(os.path.join(inputs, name), default)
    thread_dump = inp("threads.json", [])
    trigger_dump = inp("triggers.json", {})
    out = {}
    # The page reads test runs from the explorer document; the rows here only
    # feed the cost weeks.
    plan_rows, _ = eval_rows(results, site["report_base"])
    out["eval_allowance"] = allowance(results, now)
    out["budget"] = budget()
    out["roster"] = roster(load(os.path.join(config, "roster.json"), {}))
    out["usage_rows"], out["usage_sources"], _ = usage(results)
    out["ci_red_runs"] = ci_red_runs(results)
    out["threads"] = threads(thread_dump, site, inp("thread_branches.json", {}))
    out["routines"] = routines(load(os.path.join(config, "routines.json")), trigger_dump,
                               inp("workflow_runs.json", {}), now, inp("workflow_states.json", {}))
    out["run_stream"] = run_stream(inp("run_stream.json", {}), now)
    out["checkins"] = checkins(inp("trigger_list.json", []), site.get("project_channel_id"), now)
    out["waiting"] = waiting(snap, inp("needs_owner.json", []), inp("waiting_reviews.json", []),
                             inp("open_pr_heads.json", {}), thread_dump, inp("link_states.json", {}), site)
    out["cleanup"] = clean_cleanup(snap["cleanup"])
    out["gate"] = snap["gate"]
    out["decisions"] = snap["decisions"]
    loop_cfg = os.path.join(config, "loop.json")
    explorer = load(os.path.join(results, "explorer", "latest.json"), {})
    if not isinstance(explorer, dict) or not isinstance(explorer.get("schema_version"), int):
        sys.exit("explorer: results/explorer/latest.json is missing or not an explorer document")
    out["explorer"] = explorer
    out["cost_benefit_weeks"], out["cost_benefit_summary"] = cost_benefit(
        results, plan_rows, out["usage_rows"], snap["decisions"],
        load_jsonl(os.path.join(inputs, "session_costs.jsonl")),
        load_jsonl(os.path.join(inputs, "owner_messages.jsonl")), inp("loop_prs.json", []), explorer, now,
        raw=raw)
    out["half_built_issues"], out["half_built_summary"] = half_built(inp("half_built_issues.json", {}), now)
    if os.path.exists(loop_cfg):
        (out["loop_stages"], out["loop_grid"], out["loop_lanes"],
         out["loop_gaps"]) = loop(load(loop_cfg), inp("loop_status.json"), site)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("results", "inputs", "config", "out"):
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--now", help="ISO time to build as of (default: now)")
    ap.add_argument("--spend", help="also write the weekly cost totals here, in spend/weekly.json's shape")
    a = ap.parse_args(argv)
    now = parse(a.now) if a.now else datetime.now(timezone.utc)
    raw = {}
    out = build(a.results, a.inputs, a.config, now, raw=raw)
    os.makedirs(a.out, exist_ok=True)
    for name, rows in out.items():
        if not rows:  # the page reads [] as "a source failed to load"
            sys.exit(f"{name}: empty dataset; give it a placeholder row")
        with open(os.path.join(a.out, name + ".json"), "w") as f:
            json.dump(rows, f, indent=1)
    if a.spend:
        site = load(os.path.join(a.config, "site.json"), {})
        with open(a.spend, "w") as f:
            json.dump(spend_file(raw, now, site.get("plan")), f, indent=1)
    print(" ".join(f"{k}={len(v)}" for k, v in out.items()))


if __name__ == "__main__":
    main()
