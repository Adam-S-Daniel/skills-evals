#!/usr/bin/env python3
"""Plan the monthly API-credit lane's next eval.yml dispatch.

Adam, 2026-11-15: the monthly Claude Platform credit grant is spent on
eval.yml dispatches automatically, by .github/workflows/credit-lane.yml,
instead of by hand. This script decides, and never dispatches:

    python3 scripts/credit_lane.py plan --policy evals/credit-policy.yml \\
        --results-tree <persistent/eval-results checkout> \\
        --runs-json <eval.yml runs, from the Actions API> \\
        --guidance-tree <_agent-guidance checkout holding the window file> \\
        [--evals evals] [--now ISO]

It prints one JSON object: {dispatch, reason, model, fixtures, spent_usd,
est_usd}. The rules, first match wins:

  1. Outside [grant_day, grant_day + window_days) of the current UTC month:
     no.
  2. The eval pause (scripts/guidance_merge_window.py eval-pause): paused,
     or the window file unreadable (fail closed): no.
  3. Any eval.yml run not yet completed: no, one dispatch at a time.
  4. Any eval.yml workflow_dispatch run created in this window that ended
     failure, cancelled or timed_out: no, for the rest of the window. The
     reason names the run; its failure-watch issue alerts.
  5. Targets: the guidance subjects waiting in the results tree's
     batches/current.json, in file order, and each one's committed fixtures
     that are not in-place (no top-level `context:`; eval.yml refuses
     those). None: no.
  6. The model with fewer API-lane fixture runs this window (a tie goes to
     the first in the policy), then up to group_max fixtures with the fewest
     runs on that model this window (target order breaks ties), shrunk so
     the window's spend plus the estimate stays within soft_cap_usd. Spend is
     the API-equivalent dollars of the results under `results/` (eval.yml,
     billed to the credit; `routine-results/` bills the plan) stamped inside
     the window, from scripts/run_costs.py. Nothing fits: no, "cap reached".

Every input is data; nothing here calls the network or reads the clock
unless --now is left out.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guidance_merge_window  # noqa: E402
import run_costs  # noqa: E402

POLICY_KEYS = ("grant_day", "window_days", "soft_cap_usd", "models", "trials",
               "group_max", "est_usd_per_fixture")
ACTIVE = frozenset({"queued", "in_progress", "waiting", "pending", "requested"})
FAILED = frozenset({"failure", "cancelled", "timed_out"})


class PolicyError(ValueError):
    """The policy file is missing, unreadable or malformed."""


def _positive_int(policy: dict, key: str, low: int, high: int) -> int:
    value = policy[key]
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise PolicyError(f"{key} must be an integer from {low} to {high}, got {value!r}")
    return value


def load_policy(path: Path) -> dict:
    """The validated policy; every key required, no defaults."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PolicyError(f"{path}: the credit policy file is missing") from None
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PolicyError(f"{path}: unreadable ({type(exc).__name__})") from None
    if not isinstance(doc, dict):
        raise PolicyError(f"{path}: expected a mapping")
    missing = [key for key in POLICY_KEYS if key not in doc]
    if missing:
        raise PolicyError(f"{path}: missing key(s) {', '.join(missing)}")
    _positive_int(doc, "grant_day", 1, 28)
    _positive_int(doc, "window_days", 1, 31)
    _positive_int(doc, "trials", 1, 3)
    _positive_int(doc, "group_max", 1, 20)
    cap = doc["soft_cap_usd"]
    if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not cap > 0:
        raise PolicyError(f"soft_cap_usd must be a number above 0, got {cap!r}")
    models = doc["models"]
    if (not isinstance(models, list) or not models
            or not all(isinstance(m, str) and m for m in models)
            or len(set(models)) != len(models)):
        raise PolicyError("models must be a non-empty list of distinct roster arm ids")
    est = doc["est_usd_per_fixture"]
    if not isinstance(est, dict):
        raise PolicyError("est_usd_per_fixture must map each model to dollars")
    for model in models:
        value = est.get(model)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
            raise PolicyError(f"est_usd_per_fixture.{model} must be a number above 0")
    return doc


def window(policy: dict, now: datetime) -> tuple[datetime, datetime]:
    start = datetime(now.year, now.month, policy["grant_day"], tzinfo=timezone.utc)
    return start, start + timedelta(days=policy["window_days"])


def _time(value) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def load_runs(path: Path) -> list[dict]:
    """eval.yml runs: the Actions API response object, or a list of runs."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    runs = doc.get("workflow_runs") if isinstance(doc, dict) else doc
    if not isinstance(runs, list) or not all(isinstance(r, dict) for r in runs):
        raise ValueError(f"{path}: expected a list of workflow runs")
    return runs


def blocking_run(runs: list[dict], start: datetime, now: datetime) -> str | None:
    """Why the runs forbid a dispatch now (rules 3 and 4), or None."""
    for run in runs:
        if run.get("status") in ACTIVE:
            return f"eval.yml run {run.get('id')} is {run.get('status')}: one dispatch at a time"
    for run in runs:
        created = _time(run.get("created_at"))
        if (run.get("event") == "workflow_dispatch" and run.get("conclusion") in FAILED
                and created is not None and start <= created <= now):
            link = run.get("html_url") or f"run {run.get('id')}"
            return (f"eval.yml dispatch {link} ended {run['conclusion']}: "
                    "the lane stops for the rest of this window")
    return None


def targets(results_tree: Path, evals: Path) -> list[str]:
    """Committed isolation fixtures (`evals/guidance/<subject>/<name>`) of the
    waiting guidance subjects, in batch order."""
    batch = json.loads((results_tree / "batches" / "current.json").read_text(encoding="utf-8"))
    waiting = batch.get("waiting") if isinstance(batch, dict) else None
    if not isinstance(waiting, list):
        raise ValueError("batches/current.json: no `waiting` list")
    out: list[str] = []
    for entry in waiting:
        if not isinstance(entry, dict) or entry.get("kind") != "guidance":
            continue
        subject = entry.get("subject")
        if not isinstance(subject, str) or not subject or "/" in subject or subject.startswith("."):
            continue
        for path in sorted((evals / "guidance" / subject).glob("*/fixture.yaml")):
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, yaml.YAMLError):
                continue
            if isinstance(doc, dict) and "context" not in doc:
                fixture = f"evals/guidance/{subject}/{path.parent.name}"
                if fixture not in out:
                    out.append(fixture)
    return out


def lane_runs(results_tree: Path, start: datetime, end: datetime) -> list[dict]:
    """run_costs rows for eval.yml results stamped inside [start, end)."""
    rows = []
    for row in run_costs.rows(run_costs.collect(results_tree)):
        if row["source"] != "eval.yml":
            continue
        stamp = run_costs.STAMP_RE.search(row["run_id"])
        if not stamp:
            continue
        fired = datetime.strptime(stamp.group(0), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if start <= fired < end:
            rows.append(row)
    return rows


def plan(policy: dict, *, results_tree: Path, runs: list[dict], guidance_tree: Path,
         evals: Path, now: datetime) -> dict:
    decision = {"dispatch": False, "reason": "", "model": None, "fixtures": [],
                "spent_usd": 0.0, "est_usd": 0.0}

    def no(reason: str) -> dict:
        decision["reason"] = reason
        return decision

    start, end = window(policy, now)
    if not start <= now < end:
        return no(f"outside the credit window {start:%Y-%m-%d} to {end:%Y-%m-%d} (UTC)")
    try:
        paused, message = guidance_merge_window.eval_pause(guidance_tree, now)
    except (guidance_merge_window.WindowError, ValueError, OSError) as exc:
        return no(f"the eval pause could not be read ({exc}); no eval may start")
    if paused:
        return no(f"the eval pause: {message}")
    blocked = blocking_run(runs, start, now)
    if blocked:
        return no(blocked)

    rows = lane_runs(results_tree, start, end)
    spent = sum(row["total_usd"] for row in rows)
    decision["spent_usd"] = spent
    fixtures = targets(results_tree, evals)
    if not fixtures:
        return no("no waiting guidance subject has an isolation fixture to run")

    per_model = {model: 0 for model in policy["models"]}
    per_fixture: dict[tuple[str, str], int] = {}
    for row in rows:
        for fixture in filter(None, row["fixture"].split(";")):
            if row["model"] in per_model:
                per_model[row["model"]] += 1
                key = (row["model"], f"evals/{fixture}")
                per_fixture[key] = per_fixture.get(key, 0) + 1
    model = min(policy["models"], key=lambda m: (per_model[m], policy["models"].index(m)))
    ranked = sorted(range(len(fixtures)),
                    key=lambda i: (per_fixture.get((model, fixtures[i]), 0), i))
    each = policy["est_usd_per_fixture"][model]
    room = policy["soft_cap_usd"] - spent
    fit = min(policy["group_max"], len(ranked), max(0, math.floor(room / each)))
    decision["model"] = model
    if fit < 1:
        return no(f"cap reached: ${spent:.2f} spent this window, one more fixture on "
                  f"{model} is about ${each:.2f}, the soft cap is ${policy['soft_cap_usd']:.2f}")
    decision["fixtures"] = [fixtures[i] for i in ranked[:fit]]
    decision["est_usd"] = each * fit
    decision["dispatch"] = True
    decision["reason"] = (f"{fit} fixture(s) on {model}: ${spent:.2f} spent this window, "
                          f"about ${each * fit:.2f} more, soft cap ${policy['soft_cap_usd']:.2f}")
    return decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--results-tree", type=Path, required=True)
    p.add_argument("--runs-json", type=Path, required=True)
    p.add_argument("--guidance-tree", type=Path, required=True)
    p.add_argument("--evals", type=Path,
                   default=Path(__file__).resolve().parent.parent / "evals")
    p.add_argument("--now", default=None, help="ISO instant (tests); default the clock")
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.policy)
        now = _time(args.now) if args.now else datetime.now(timezone.utc)
        if now is None:
            raise ValueError(f"--now {args.now!r} is not an ISO instant")
        decision = plan(policy, results_tree=args.results_tree,
                        runs=load_runs(args.runs_json), guidance_tree=args.guidance_tree,
                        evals=args.evals, now=now)
    except (PolicyError, ValueError, OSError) as exc:
        print(f"credit_lane: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(decision, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
