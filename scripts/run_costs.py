#!/usr/bin/env python3
"""One row per ingested eval run, and the cost distribution that sizes the
budget (evals/budget.yml).

Adam, 2026-11-01: the per-run cap (`per_run_cap`) and the overrun
(`per_run_overrun`) were set from this data, and he asked that the script be
kept so they can be recalculated as runs accumulate.

    python3 scripts/run_costs.py --results-tree <persistent/eval-results checkout> \\
        [--evals evals] [--csv runs.csv]

It reads every `summary.json` under `routine-results/` (routine runs, billed
to the plan) and `results/` (older eval.yml runs, billed to API credit) as
data, never executing anything, and writes one CSV row per run. It prints:

  * the distribution of each metered run's weekly-meter delta in points
    (percent of the weekly allowance), with the 50th, 90th, 95th, 97.5th
    and 99th percentiles and the maximum;
  * points per dollar: all metered points over those runs' API-equivalent
    dollars for every call (agent, judge from `usage.measured.judge`, guard
    from `usage.measured.guard`) and, from it, each run's largest single
    call in points, the most the meter can miss when that call is the
    run's last (the evidence for `per_run_overrun`);
  * judge-call dollars per run.

The meter reports whole points and counts the whole account, so Adam's own
use during a run is in it: the deltas, and so the rate, lean high. Rounding
happens only in the printed lines; the CSV keeps full precision.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

STAMP_RE = re.compile(r"\d{8}T\d{6}Z")
TRIAL_RE = re.compile(r"trial-\d+")
PERCENTILES = (0.50, 0.90, 0.95, 0.975, 0.99)


def _time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _load(path: Path):
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _rubric(evals: Path | None, fixture: str) -> str:
    """Whether the fixture still in the repo has a judge rubric."""
    if evals is None or not fixture:
        return ""
    path = evals / fixture / "fixture.yaml"
    if not path.is_file():
        return "fixture not recorded" if (evals / fixture).is_dir() else "fixture gone"
    import yaml
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return "unreadable"
    return "yes" if isinstance(doc, dict) and doc.get("judge_rubric") else "no"


def _new_run(run_id: str, source: str) -> dict:
    return {"run_id": run_id, "source": source, "fixtures": set(), "arms": set(),
            "models": set(), "judge_models": set(), "trials": 0, "trial_errors": 0,
            "judged": 0, "objective_decided": 0, "judge_scores": [], "checks": 0,
            "checks_passed": 0, "agent_usd": 0.0, "trial_usd": [], "judge_usd": 0.0,
            "guard_usd": 0.0, "call_usd": [], "judge_costed": 0, "turns": 0, "out_tokens": 0, "agent_ms": 0, "usage": None,
            "subject_kind": None, "subject": None, "cli": None, "pairing": None, "mode": None}


def _fixture(doc: dict, parts: list, arm: str) -> str:
    fixture = doc.get("fixture")
    if isinstance(fixture, str) and fixture:
        fixture = fixture.removeprefix("evals/")
        skill = doc.get("skill")
        if "/" not in fixture and isinstance(skill, str) and fixture != skill:
            fixture = f"{skill}/{fixture}"
        return fixture
    if doc.get("section") and doc.get("fixture_name"):
        return f"guidance/{doc['section']}/{doc['fixture_name']}"
    return "/".join(parts[:-1]) if parts and parts[-1] == arm else "/".join(parts)


def collect(tree: Path) -> dict:
    """{run id: accumulated fields} over every summary in `tree`."""
    runs: dict = {}
    sources = [(tree / "routine-results", "routine"), (tree / "results", "eval.yml")]
    for base, source in sources:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("summary.json")):
            if path.is_symlink():
                continue
            doc = _load(path)
            if doc is None:
                continue
            rel = path.relative_to(base).parts[:-1]
            if source == "routine":
                run_id, parts = rel[0], list(rel[1:])
            else:
                stamp = next((p for p in rel if STAMP_RE.fullmatch(p)), "unknown")
                run_id, parts = f"eval.yml-{stamp}-{rel[0]}", list(rel)
            parts = [p for p in parts if not TRIAL_RE.fullmatch(p) and not STAMP_RE.fullmatch(p)]
            arm = doc.get("arm") if isinstance(doc.get("arm"), str) else (parts[-1] if parts else "")
            run = runs.setdefault(run_id, _new_run(run_id, source))
            run["fixtures"].add(_fixture(doc, parts, arm))
            run["arms"].add(arm)
            cross = doc.get("cross_model") if isinstance(doc.get("cross_model"), dict) else {}
            if isinstance(cross.get("model"), str):
                run["models"].add(cross["model"])
            harness = doc.get("harness") if isinstance(doc.get("harness"), dict) else {}
            run["cli"] = run["cli"] or harness.get("version")
            run["pairing"] = run["pairing"] or doc.get("pairing")
            run["mode"] = run["mode"] or doc.get("mode")
            subject = doc.get("context_subject") if isinstance(doc.get("context_subject"), dict) else {}
            if doc.get("section"):
                run["subject_kind"], run["subject"] = "guidance", doc["section"]
            elif subject.get("kind"):
                run["subject_kind"] = subject["kind"]
                run["subject"] = subject.get("skill") or subject.get("section")
            elif not run["subject"]:
                run["subject_kind"] = "skill"
                run["subject"] = doc.get("skill") or (parts[0] if parts else None)
            if isinstance(doc.get("usage"), dict) and run["usage"] is None:
                run["usage"] = doc["usage"]
            if "aggregate" in doc:
                continue  # an arm's roll-up: trials are counted from their own files
            run["trials"] += 1
            run["trial_errors"] += 1 if doc.get("error") else 0
            judge = doc.get("judge") if isinstance(doc.get("judge"), dict) else {}
            if judge.get("status") == "skipped":
                run["objective_decided"] += 1
            elif _number(judge.get("overall")):
                run["judged"] += 1
                run["judge_scores"].append(judge["overall"])
            measured = (doc.get("usage") or {}).get("measured") if isinstance(
                doc.get("usage"), dict) else None
            measured = measured if isinstance(measured, dict) else {}
            for role in ("judge", "guard"):
                call = measured.get(role) if isinstance(measured.get(role), dict) else {}
                if _number(call.get("cost_usd")):
                    run[f"{role}_usd"] += call["cost_usd"]
                    run["judge_costed"] += 1 if role == "judge" else 0
                    run["call_usd"].append(call["cost_usd"])
            for model in doc.get("judge_models_used") or []:
                if isinstance(model, str):
                    run["judge_models"].add(model)
            for check in doc.get("objective_checks") or []:
                if isinstance(check, dict):
                    run["checks"] += 1
                    run["checks_passed"] += 1 if check.get("passed") is True else 0
            agent = doc.get("agent") if isinstance(doc.get("agent"), dict) else {}
            if _number(agent.get("cost_usd")):
                run["agent_usd"] += agent["cost_usd"]
                run["trial_usd"].append(agent["cost_usd"])
                run["call_usd"].append(agent["cost_usd"])
            run["turns"] += agent.get("num_turns") if _number(agent.get("num_turns")) else 0
            run["agent_ms"] += agent.get("duration_ms") if _number(agent.get("duration_ms")) else 0
            usage = agent.get("usage") if isinstance(agent.get("usage"), dict) else {}
            if _number(usage.get("output_tokens")):
                run["out_tokens"] += usage["output_tokens"]
    return runs


def rows(runs: dict, evals: Path | None = None) -> list[dict]:
    """One CSV row per run, full precision, sorted by run id."""
    out = []
    for run in runs.values():
        usage = run["usage"] or {}
        delta = usage.get("meter_delta") if isinstance(usage.get("meter_delta"), dict) else {}
        week = (delta.get("windows") or {}).get("seven_day") or {}
        start, end = _time(usage.get("started_at")), _time(usage.get("ended_at"))
        stamp = STAMP_RE.search(run["run_id"])
        stop = usage.get("budget_stop")
        fixture = ";".join(sorted(f for f in run["fixtures"] if f))
        out.append({
            "run_id": run["run_id"], "source": run["source"],
            "fired_utc": datetime.strptime(stamp.group(0), "%Y%m%dT%H%M%SZ")
            .strftime("%Y-%m-%d %H:%M") if stamp else "",
            "subject_kind": run["subject_kind"] or "", "subject": run["subject"] or "",
            "fixture": fixture, "model": ";".join(sorted(run["models"])),
            "arms": ";".join(sorted(a for a in run["arms"] if a)), "mode": run["mode"] or "",
            "pairing": run["pairing"] or "", "trials": run["trials"],
            "trial_errors": run["trial_errors"],
            "fixture_has_judge_rubric": _rubric(evals, fixture.split(";")[0]),
            "judge_ran": "yes" if run["judged"] else "no", "judged_trials": run["judged"],
            "objective_decided_trials": run["objective_decided"],
            "mean_judge_score": sum(run["judge_scores"]) / len(run["judge_scores"])
            if run["judge_scores"] else "",
            "judge_models": ";".join(sorted(run["judge_models"])),
            "objective_checks": run["checks"], "objective_passed": run["checks_passed"],
            "meter_delta_points": week["delta"] * 100 if _number(week.get("delta")) else "",
            "meter_from_pct": week["from"] * 100 if _number(week.get("from")) else "",
            "meter_to_pct": week["to"] * 100 if _number(week.get("to")) else "",
            "window_reset": week.get("window_reset", ""),
            "budget_stop": stop.get("reason", "") if isinstance(stop, dict) else (stop or ""),
            "run_minutes": (end - start).total_seconds() / 60 if start and end else "",
            "agent_api_equiv_usd": run["agent_usd"],
            "max_trial_agent_usd": max(run["trial_usd"]) if run["trial_usd"] else "",
            "judge_usd": run["judge_usd"] if run["judge_costed"] else "",
            "guard_usd": run["guard_usd"],
            "total_usd": run["agent_usd"] + run["judge_usd"] + run["guard_usd"],
            "max_call_usd": max(run["call_usd"]) if run["call_usd"] else "",
            "agent_turns": run["turns"], "agent_output_tokens": run["out_tokens"],
            "agent_minutes": run["agent_ms"] / 60000,
            "cli_version": (run["cli"] or "").replace(" (Claude Code)", ""),
        })
    return sorted(out, key=lambda row: row["run_id"])


def percentile(values: list, share: float) -> float:
    """Linear interpolation between the nearest ranks (numpy's default)."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("no values")
    rank = (len(ordered) - 1) * share
    low = math.floor(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def summarize(table: list[dict]) -> dict:
    metered = [r for r in table if r["meter_delta_points"] != ""]
    points = [r["meter_delta_points"] for r in metered]
    summary = {"runs": len(table), "metered": len(metered)}
    if not points:
        return summary
    counts: dict = {}
    for value in points:
        counts[value] = counts.get(value, 0) + 1
    summary["distribution"] = dict(sorted(counts.items()))
    summary["mean"] = sum(points) / len(points)
    summary["percentiles"] = {share: percentile(points, share) for share in PERCENTILES}
    summary["max"] = max(points)
    priced = [r for r in metered if r["total_usd"] > 0]
    dollars = sum(r["total_usd"] for r in priced)
    if dollars:
        # Every call the run made (agent, judge, guard) is billed to the meter.
        rate = sum(r["meter_delta_points"] for r in priced) / dollars
        calls = [r["max_call_usd"] for r in priced]
        summary["points_per_usd"] = rate
        summary["largest_call_points"] = {share: percentile(calls, share) * rate
                                          for share in PERCENTILES}
        summary["largest_call_points"][1.0] = max(calls) * rate
    judged = [r["judge_usd"] for r in table if r["judge_usd"] != ""]
    summary["runs_with_judge_cost"] = len(judged)
    if judged:
        summary["judge_usd_per_run"] = {"median": percentile(judged, 0.5),
                                        "p95": percentile(judged, 0.95), "max": max(judged)}
    return summary


def report(summary: dict) -> list[str]:
    lines = [f"runs: {summary['runs']}, with a meter reading: {summary['metered']}"]
    if "distribution" not in summary:
        return lines
    lines.append("meter points per run: " + ", ".join(
        f"{value:g}: {count}" for value, count in summary["distribution"].items()))
    lines.append(f"mean {summary['mean']:.2f}; " + ", ".join(
        f"p{share * 100:g} {value:.2f}" for share, value in summary["percentiles"].items())
        + f"; max {summary['max']:.2f}")
    if "points_per_usd" in summary:
        lines.append(f"points per dollar (agent, judge and guard calls): "
                     f"{summary['points_per_usd']:.3f}")
        lines.append("each run's largest single call, in points (the most the meter can miss "
                     "when it is the last call): " + ", ".join(
                         f"{'max' if share == 1.0 else f'p{share * 100:g}'} {value:.3f}"
                         for share, value in summary["largest_call_points"].items()))
        # Adam, 2026-11-01: the overrun is the p95 of this, now and in future.
        lines.append("per_run_overrun for evals/budget.yml (p95 of the largest call): "
                     f"{summary['largest_call_points'][0.95] / 100:.4f}")
    if summary.get("runs_with_judge_cost"):
        judge = summary["judge_usd_per_run"]
        lines.append(f"judge dollars per run ({summary['runs_with_judge_cost']} runs): "
                     f"median {judge['median']:.4f}, p95 {judge['p95']:.4f}, "
                     f"max {judge['max']:.4f}")
    else:
        lines.append("judge dollars: no run records them yet")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--results-tree", type=Path, required=True,
                        help="a checkout of persistent/eval-results")
    parser.add_argument("--evals", type=Path, default=Path(__file__).resolve().parent.parent / "evals",
                        help="the evals directory, to look up each fixture's judge rubric")
    parser.add_argument("--csv", type=Path, help="write one row per run here")
    args = parser.parse_args(argv)
    table = rows(collect(args.results_tree), args.evals)
    if args.csv and table:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    for line in report(summarize(table)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
