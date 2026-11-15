#!/usr/bin/env python3
"""Break down automatic Claude spend (scheduled or event-fired) by category.

Adam, 2026-11-15: the catch-up forecast's non-eval meter use must break down
into what runs on its own (creating new targets from transcripts,
centralizing targets and memories, the dashboard and Explorer, and every
other scheduled or event-fired job). This builds that breakdown from sources,
never from a hand count:

  * scheduled tasks: `list_triggers` dumps (`--triggers`, repeatable; a JSON
    list, `{"data": [...]}`, or the dashboard's `{id: row}`), named from the
    dump or from the dashboard's config/routines.json (`--routines`);
  * GitHub workflows: `--workflows-root`, a directory of
    `<repo>/.github/workflows/*.yml` checkouts (every repo in _agent-guidance
    repos.yml `cron_coverage.fleet`, both owners);
  * BOXY tasks: `--wsl-automation`, a wsl-automation checkout: the task names
    and times in scripts/register-tasks.ps1, and whether the task's script
    runs `claude -p`.

Rate (fires a week), first that applies: the task's own cron; for a task
fired by a workflow (`fired_by` in evals/automatic-spend.yml, matched by
task name), that
workflow's cron thinned to its cadence; zero for a task with no fire on
record; else the fires in the ledger over `--window-days`.
Cost per fire: the median of the fire ledger's costs for that task
(`--fires`, repeatable JSONL, the routine fire ledger's schema). A job with
no measured cost is listed under `unmeasured`, never guessed.

Lanes: `meter` (the subscription's weekly meter, which the forecast's
non-eval points come from), `eval_cap` (already inside the eval cap),
`api` (Anthropic API dollars, no meter), `actions_only` (GitHub Actions
minutes, counted as $0).

Usage:
  python3 scripts/automatic_spend.py --triggers t.json [--triggers more.json] \\
      --routines routines.json --fires routine-fires.jsonl \\
      --workflows-root wf/ --wsl-automation wsl-automation/ \\
      --as-of 2026-11-15T18:00:00Z --out-json automatic-spend.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Lexical markers in a workflow file (tokens, not code shape).
FIRES_ROUTINE = re.compile(r"claude_code/routines|_FIRE_BEARER\b")
SPENDS_API = re.compile(r"ANTHROPIC_API_KEY|anthropic_api_key|api\.anthropic\.com/v1/oauth/token")
DISPATCHES_EVAL_FIRE = re.compile(r"gh workflow run routine-eval-fire\.yml")
RUNS_CLAUDE = re.compile(r"""(?:\bclaude|"\$claude_bin"|\$\{?claude_bin\}?)\s+-p\b""")
#: Events a person starts; a workflow with only these runs on no schedule or event.
MANUAL_EVENTS = {"workflow_dispatch", "workflow_call"}


# --- cron -----------------------------------------------------------------

def _field(spec: str, lo: int, hi: int) -> set:
    out = set()
    for part in spec.split(","):
        step = 1
        if "/" in part:
            part, s = part.split("/", 1)
            step = int(s)
        if part == "*":
            a, b = lo, hi
        elif "-" in part:
            a, b = (int(x) for x in part.split("-", 1))
        else:
            a = b = int(part)
            if step != 1:
                b = hi
        out.update(range(a, b + 1, step))
    return out


def cron_fires_per_week(expr: str) -> float:
    """Average fires a week of a five-field cron line, over 52 whole weeks
    (a `CRON_TZ=` prefix is dropped: a zone moves fires, not their count).
    Day of month and day of week both restricted means either matches."""
    fields = expr.split()
    if fields and fields[0].startswith("CRON_TZ="):
        fields = fields[1:]
    if len(fields) != 5:
        raise ValueError(f"not a five-field cron line: {expr!r}")
    minute, hour, dom, month, dow = fields
    per_day = len(_field(minute, 0, 59)) * len(_field(hour, 0, 23))
    doms, months = _field(dom, 1, 31), _field(month, 1, 12)
    dows = {d % 7 for d in _field(dow, 0, 7)}
    start = date(2026, 1, 5)  # a Monday; any fixed year gives the same average
    days = 0
    for i in range(364):
        d = start + timedelta(days=i)
        if d.month not in months:
            continue
        dom_ok, dow_ok = d.day in doms, (d.isoweekday() % 7) in dows
        if dom != "*" and dow != "*":
            days += dom_ok or dow_ok
        else:
            days += dom_ok and dow_ok
    return per_day * days / 52


def cadence_fires_per_week(crons: list, cadence_hours: float) -> float:
    """Fires a week of a workflow whose cron lines each name a cadence slot
    and which fires a line only when that slot is at least `cadence_hours`
    (fleet-worker-fire.yml): taking lines rarest first, a line is kept while
    the kept lines together still fire no more often than the cadence."""
    total = 0.0
    for rate in sorted(cron_fires_per_week(c) for c in crons):
        if rate and 168 / (total + rate) >= cadence_hours - 1e-9:
            total += rate
        else:
            break
    return total


# --- sources --------------------------------------------------------------

def load_triggers(paths: list, routines: list) -> dict:
    names = {(r.get("source") or {}).get("id"): r.get("name") for r in routines
             if (r.get("source") or {}).get("kind") == "trigger"}
    out = {}
    for path in paths:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = doc.get("data", doc) if isinstance(doc, dict) else doc
        if isinstance(rows, dict):
            rows = [dict(v, id=k) for k, v in rows.items()]
        for row in rows:
            tid = row.get("id")
            if not tid:
                continue
            merged = dict(out.get(tid, {}))
            merged.update({k: v for k, v in row.items() if v not in (None, "")})
            merged.setdefault("name", names.get(tid) or tid)
            out[tid] = merged
    return out


def load_fires(paths: list) -> list:
    rows = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    seen, out = set(), []
    for r in rows:
        if r.get("session_id") in seen:
            continue
        seen.add(r.get("session_id"))
        out.append(r)
    return out


def _cost(row: dict):
    for k in ("total_cost_usd", "session_usage_cost_usd", "cost_usd"):
        if isinstance(row.get(k), (int, float)):
            return float(row[k])
    return None


def _when(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def scan_workflows(root: Path) -> list:
    """One row per workflow that runs on a schedule or an event."""
    out = []
    for path in sorted(root.glob("*/.github/workflows/*.y*ml")):
        repo = path.parts[-4]
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            doc = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            continue
        on = doc.get("on", doc.get(True)) if isinstance(doc, dict) else None
        events = [on] if isinstance(on, str) else list(on or [])
        auto = [e for e in events if e not in MANUAL_EVENTS]
        if not auto:
            continue
        crons = [c.get("cron") for c in (on.get("schedule") or [])] \
            if isinstance(on, dict) and isinstance(on.get("schedule"), list) else []
        out.append({"repo": repo, "file": path.name, "name": doc.get("name") or path.name,
                    "events": sorted(auto), "crons": [c for c in crons if c],
                    "fires_routine": bool(FIRES_ROUTINE.search(text)),
                    "spends_api": bool(SPENDS_API.search(text)),
                    "dispatches_eval_fire": bool(DISPATCHES_EVAL_FIRE.search(text))})
    return out


def scan_boxy_tasks(checkout: Path) -> list:
    """BOXY scheduled tasks from register-tasks.ps1's parameter defaults:
    `$<Key>TaskName = '<name>'` with `$<Key>Time` (daily, or weekly when the
    parameter help says so) or `$<Key>IntervalMinutes`."""
    ps1 = (checkout / "scripts" / "register-tasks.ps1").read_text(encoding="utf-8")
    defaults = {k: a or b for k, a, b in
                re.findall(r"\[(?:string|int)\]\$(\w+)\s*=\s*(?:'([^']*)'|(\d+))", ps1)}
    out = []
    for key, name in defaults.items():
        if not key.endswith("TaskName"):
            continue
        stem = key[: -len("TaskName")]
        help_text = re.search(rf"\.PARAMETER {stem}Time\s+(.*?)(?:\n\.PARAMETER|\Z)", ps1, re.S)
        if f"{stem}Time" in defaults:
            weekly = bool(help_text and re.search(r"\bweekly\b", help_text.group(1), re.I))
            per_week = 1.0 if weekly else 7.0
        elif f"{stem}IntervalMinutes" in defaults:
            per_week = 7 * 24 * 60 / max(1, int(defaults[f"{stem}IntervalMinutes"]))
        else:
            per_week = None
        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", stem).lower()
        scripts = sorted((checkout / "scripts").glob(f"*{kebab}*.sh"))
        runs_claude = any(RUNS_CLAUDE.search(p.read_text(encoding="utf-8", errors="replace"))
                          for p in scripts)
        out.append({"name": name, "fires_per_week": per_week, "runs_claude": runs_claude,
                    "scripts": [p.name for p in scripts]})
    return out


# --- breakdown ------------------------------------------------------------

def categorize(name: str, categories: list, extra: str = "") -> str:
    for c in categories:
        if any(re.search(m, name, re.I) or (extra and re.search(m, extra, re.I))
               for m in c["match"]):
            return c["id"]
    return "other"


def breakdown(config: dict, triggers: dict, fires: list, workflows: list,
              boxy: list, now: datetime, window_days: int) -> dict:
    cats = config["categories"]
    fired_by = config.get("fired_by") or {}
    eval_cap = config.get("eval_cap_triggers") or []
    eval_api = set(config.get("eval_api_workflows") or [])
    since = now - timedelta(days=window_days)
    by_trigger: dict = {}
    for r in fires:
        by_trigger.setdefault(r.get("trigger_id"), []).append(r)
    wf_by_path = {f"{w['repo']}/{w['file']}": w for w in workflows}
    jobs = []

    for tid, t in sorted(triggers.items()):
        if t.get("enabled") is False:
            continue
        rows = by_trigger.get(tid, [])
        costs = [c for c in (_cost(r) for r in rows) if c is not None]
        cron = t.get("cron_expression") or ""
        if cron:
            rate, rate_source = cron_fires_per_week(cron), "cron"
        elif (spec := next((v for k, v in fired_by.items()
                            if re.search(k, t["name"], re.I)), None)):
            w = wf_by_path.get(spec["workflow"])
            if w is None:
                rate, rate_source = None, f"firing workflow {spec['workflow']} not scanned"
            else:
                cad = spec.get("cadence_hours")
                rate = cadence_fires_per_week(w["crons"], cad) if cad \
                    else sum(cron_fires_per_week(c) for c in w["crons"])
                rate_source = f"{spec['workflow']} cron" + (f", every {cad} h" if cad else "")
        elif not t.get("last_run") and not rows:
            rate, rate_source = 0.0, "never fired"
        else:
            recent = [r for r in rows if (_when(r.get("fired_at")) or now) >= since]
            rate = len(recent) * 7 / window_days
            rate_source = f"ledger fires in {window_days} days"
        per_fire = statistics.median(costs) if costs else None
        lane = "eval_cap" if any(re.search(m, t["name"], re.I) for m in eval_cap) else "meter"
        jobs.append({"kind": "scheduled task", "id": tid, "name": t["name"],
                     "category": categorize(t["name"], cats), "lane": lane,
                     "fires_per_week": rate, "rate_source": rate_source,
                     "usd_per_fire": per_fire, "cost_fires": len(costs),
                     "usd_per_week": 0.0 if rate == 0 else
                     None if rate is None or per_fire is None else rate * per_fire})

    for w in workflows:
        path = f"{w['repo']}/{w['file']}"
        rate = sum(cron_fires_per_week(c) for c in w["crons"]) if w["crons"] else None
        if w["fires_routine"]:
            # Its cost is the scheduled task's; listed so nothing is hidden.
            lane, usd = "fires_scheduled_task", 0.0
        elif w["dispatches_eval_fire"] or path in eval_api:
            lane, usd = "eval_cap", None
        elif w["spends_api"]:
            lane, usd = "api", None
        else:
            lane, usd = "actions_only", 0.0
        jobs.append({"kind": "workflow", "id": path, "name": w["name"],
                     "category": categorize(w["name"], cats, path), "lane": lane,
                     "events": w["events"], "fires_per_week": rate,
                     "rate_source": "cron" if w["crons"] else "events only",
                     "usd_per_fire": None, "usd_per_week": usd})

    for b in boxy:
        lane = "meter" if b["runs_claude"] else "actions_only"
        jobs.append({"kind": "BOXY task", "id": b["name"], "name": b["name"],
                     "category": categorize(b["name"], cats), "lane": lane,
                     "fires_per_week": b["fires_per_week"], "rate_source": "register-tasks.ps1",
                     "usd_per_fire": None, "local_only": lane == "actions_only",
                     "usd_per_week": 0.0 if lane == "actions_only" else None})

    labels = {c["id"]: c["label"] for c in cats}
    labels["other"] = "Other automatic jobs"
    out_cats = []
    for cid in [c["id"] for c in cats] + ["other"]:
        members = [j for j in jobs if j["category"] == cid]
        if not members:
            continue
        lanes: dict = {}
        for j in members:
            if j["usd_per_week"] is not None:
                lanes[j["lane"]] = lanes.get(j["lane"], 0.0) + j["usd_per_week"]
        out_cats.append({"id": cid, "label": labels[cid], "jobs": len(members),
                         "usd_per_week_by_lane": lanes,
                         "meter_usd_per_week": lanes.get("meter", 0.0),
                         "unmeasured": sorted(j["name"] for j in members
                                              if j["usd_per_week"] is None
                                              and j["lane"] in ("meter", "api"))})
    meter = sum(c["meter_usd_per_week"] for c in out_cats)
    return {
        "schema": 1, "as_of": now.isoformat(), "window_days": window_days,
        "notes": ["GitHub Actions minutes are counted as $0 (lane actions_only).",
                  "lane meter adds to the forecast's non-eval points; eval_cap is "
                  "already inside the eval cap; api is Anthropic API dollars, no meter.",
                  "A job under `unmeasured` has no recorded cost and adds nothing."],
        "meter_usd_per_week": meter,
        "categories": out_cats,
        "jobs": jobs,
        "unmeasured": sorted(j["name"] for j in jobs
                             if j["usd_per_week"] is None and j["lane"] in ("meter", "api")),
    }


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--config", type=Path, default=REPO_ROOT / "evals" / "automatic-spend.yml")
    p.add_argument("--triggers", type=Path, action="append", default=[])
    p.add_argument("--routines", type=Path, default=None,
                   help="the dashboard's config/routines.json, for task names")
    p.add_argument("--fires", type=Path, action="append", default=[],
                   help="routine fire ledger (JSONL); repeatable")
    p.add_argument("--workflows-root", type=Path, default=None)
    p.add_argument("--wsl-automation", type=Path, default=None)
    p.add_argument("--window-days", type=int, default=14)
    p.add_argument("--as-of", required=True)
    p.add_argument("--out-json", type=Path, required=True)
    args = p.parse_args(argv)
    now = _when(args.as_of)
    now = (now if now.tzinfo else now.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    routines = json.loads(args.routines.read_text(encoding="utf-8")) if args.routines else []
    doc = breakdown(config, load_triggers(args.triggers, routines), load_fires(args.fires),
                    scan_workflows(args.workflows_root) if args.workflows_root else [],
                    scan_boxy_tasks(args.wsl_automation) if args.wsl_automation else [],
                    now, args.window_days)
    args.out_json.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    for c in doc["categories"]:
        print(f"{c['label']}: ${c['meter_usd_per_week']:.0f}/wk meter, {c['jobs']} jobs"
              + (f", unmeasured: {', '.join(c['unmeasured'])}" if c["unmeasured"] else ""))
    print(f"total meter ${doc['meter_usd_per_week']:.0f}/wk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
