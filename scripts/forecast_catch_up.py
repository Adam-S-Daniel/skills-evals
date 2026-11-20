#!/usr/bin/env python3
"""Forecast eval catch-up time and the ongoing weekly eval budget.

How long until every open skill and guidance section reaches a verdict
(catch-up), and what keeping up then costs each week (keep-up), from the
same inputs and the same per-cell projection the weekly planner uses:

  * the verdict document (`scripts/compute_gates.py`), so the open cells,
    the zero-use / ceiling / floor / removed pauses and the guidance
    current-rest guard are exactly what the planner sees;
  * `plan_week.pairs_to_verdict`, the planner's own projection of the pairs
    each open cell needs before its keep or remove test decides, capped at
    the cell's remaining pairs under `max_runs_per_cell`;
  * `evals/budget.yml` for the weekly cap and the dollars a point buys,
    `evals/batch-policy.yml` for the planner's prior of pairs per unpriced
    cell, `evals/gate-policy.yml` (through the verdict document) for the
    cap and the re-check ages.

Never restate a policy number in the report: read it here and print it with
the file it came from (docs/rules.md, "Never restate a rule's number").

A subject's cost is DEEP-FIRST, as the planner funds it (plan_week
`depth_order`): a keep in any cell ends the subject, so a subject with a
projected keep route costs its cheapest keep cell (central) and, if that
keep fails, every open cell (high); a subject heading for removal or the
cap needs every open cell. A cell with no measured gain yet costs the
batch policy's `pairs_per_cell` (central), at most its remaining pairs.

Usage:
  python3 scripts/forecast_catch_up.py --gates gates.json \
      --results-tree <persistent/eval-results checkout> \
      --as-of 2026-11-15T14:27:23Z --out-json forecast.json [--assumptions a.yml]

`--assumptions` (YAML) supplies the measured rates the verdict document
does not hold; each key is documented in ASSUMPTION_KEYS. The arrival rates
(new git hooks, skills and sections a week, and the share of new skills and
sections that get evaluated) default to `arrivals/targets.json` in the
results tree (or `--arrivals`), counted daily from git history by
scripts/target_arrivals.py; a stale document or an incomplete kind is not
used. The assumptions file and `--set` override it. Every value the run
used is echoed in the output, with its source (`assumption_sources`).

`--automatic-spend` (scripts/automatic_spend.py) breaks the non-eval meter
use down by category (`non_eval_points_breakdown`): each category's meter
dollars at the mid $/point, plus `interactive_points_per_week` for people's
own threads and local sessions; their sum is non_eval_points_per_week unless
that is set.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import allowance_guard  # noqa: E402
import allowance_points  # noqa: E402
import plan_week  # noqa: E402
import stakes  # noqa: E402

#: Assumptions the verdict document cannot supply. Each is (default, what
#: it is); a run's --assumptions file overrides any of them, and the output
#: records every value used.
ASSUMPTION_KEYS = {
    "usd_per_point_low": (None, "low end of the measured $ per weekly-meter point; "
                                "default: budget.yml legacy_usd_per_point"),
    "usd_per_point_high": (None, "high end of the same; default: as low"),
    "measured_usd_per_pair": (None, "mean run cost per pair over recent fires (cost_estimate.json); "
                                    "scales the verdict document's per-model costs to it"),
    "fire_overhead_usd": (0.19, "routine session cost per eval fire, outside the run's own calls"),
    "pairs_per_fire": (2.0, "pairs (one fixture x one model, both arms) one fire carries"),
    "api_credit_usd_per_week": (0.0, "extra eval dollars a week from the monthly API credit lane"),
    "new_hooks_per_week": (None, "git hooks added per week; default: arrivals/targets.json "
                                 "(reported at $0: a hook's verdict comes from its usage, "
                                 "evals/hook-policy.yml, not from eval runs)"),
    "new_skills_per_week": (None, "skills added per week; default: arrivals/targets.json, "
                                  "else batches/current.json rate"),
    "new_sections_per_week": (None, "guidance sections added per week; default: as skills"),
    "first_use_share": (None, "share of new skills that get a recorded use and so are evaluated; "
                              "default: arrivals/targets.json, else 1"),
    "evaluated_section_share": (None, "share of new sections that get fixtures (not skipped); "
                                      "default: arrivals/targets.json, else 1"),
    "new_fixtures_per_week_open": (0.0, "fixtures added per week to subjects still open"),
    "skill_text_edits_per_week": (0.0, "evaluated skills whose text changes per week "
                                       "(restarts their evidence)"),
    "guidance_rest_changes_per_week": (0.0, "agents-md changes per week that move every section's "
                                            "current rest, so each guidance keep must be re-proved"),
    "non_eval_points_per_week": (None, "meter points a week used by everything but evals "
                                       "(threads, routines, local sessions); with budget.yml's "
                                       "account stop it can cap the eval points; default when both "
                                       "--automatic-spend and interactive_points_per_week are given: "
                                       "their sum"),
    "loop_jobs_in_cap": (True, "the continuous improvement system's own automatic jobs "
                               "(--automatic-spend, in_loop) spend from the same weekly cap "
                               "as evals (Adam, 2026-11-15), so evals get the cap less them"),
    "eval_points_per_hour": (None, "meter points an hour evals spend from the weekly reset until "
                                   "the cap; when set, evals run first in the week and the account "
                                   "stop binds only on other use that accrues meanwhile"),
    "pace_hold": (True, "allowance_guard.py's pace hold (2026-11-20): no loop fire while the "
                        "account is ahead of its pace line, so evals no longer run first in the "
                        "week and get at most the account stop less other use; 0 models the "
                        "guard before it"),
    "interactive_points_per_week": (None, "meter points a week used by people's own threads and "
                                          "local sessions, outside every automatic job"),
    "start": (None, "ISO time evals resume (after the reset and the Monday pause)"),
}


#: The assumptions arrivals/targets.json (scripts/target_arrivals.py,
#: published daily by target-arrivals.yml) supplies: key -> (kind, rate field).
ARRIVAL_KEYS = {
    "new_hooks_per_week": ("git-hook", "added_per_week"),
    "new_skills_per_week": ("skill", "added_per_week"),
    "new_sections_per_week": ("guidance-section", "added_per_week"),
    "first_use_share": ("skill", "eligible_share"),
    "evaluated_section_share": ("guidance-section", "eligible_share"),
}
#: An arrivals document older than this at --as-of is not used.
ARRIVALS_MAX_AGE = timedelta(days=8)


def arrival_assumptions(doc, now: datetime) -> dict:
    """{assumption key: value} from an arrivals document: each rate of a
    kind whose sources were all read (`complete`) and that is a number. {}
    for a missing, malformed or stale document (older than ARRIVALS_MAX_AGE
    at `now`, or dated after it): unknown, so the run falls back."""
    if not isinstance(doc, dict) or doc.get("schema") != 1 or not isinstance(doc.get("rates"), dict):
        return {}
    try:
        as_of = datetime.fromisoformat(str(doc.get("as_of")).replace("Z", "+00:00"))
    except ValueError:
        return {}
    if as_of.tzinfo is None or not timedelta(0) <= now - as_of <= ARRIVALS_MAX_AGE:
        return {}
    out = {}
    for key, (kind, field) in ARRIVAL_KEYS.items():
        rate = doc["rates"].get(kind)
        if isinstance(rate, dict) and rate.get("complete") is True and _number(rate.get(field)):
            out[key] = float(rate[field])
    return out


def merge_assumptions(given: dict, arrivals: dict) -> tuple[dict, dict]:
    """(assumptions, {key: source}): the --assumptions file and --set values
    win; arrivals fill only the keys they leave unset."""
    merged = dict(arrivals)
    merged.update(given)
    sources = {k: "arrivals/targets.json" for k in arrivals}
    sources.update({k: "assumptions" for k in given})
    return merged, sources


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value)


def cell_estimate(cell: dict, ctx: dict, prior_pairs: float) -> dict:
    """{central, low, high, keep_route, projected, model} pairs for one open
    cell. `central` is the planner's projection capped at the cell's
    remaining pairs; a cell with no measured gain yet costs `prior_pairs`
    (at most its remaining). `high` is always the remaining pairs: the
    cell runs to its cap. `low` is the keep route alone when it is the
    nearer, else central."""
    guidance = bool(cell.get("section"))
    cap = plan_week.gate_cap(ctx, "guidance" if guidance else "skill") or 0
    held = cell.get("pairs") if isinstance(cell.get("pairs"), int) else 0
    remaining = max(0, cap - held)
    projection = plan_week.pairs_to_verdict(cell, ctx)
    out = {"model": cell.get("model"), "remaining": remaining, "projected": projection is not None}
    if projection is None:
        central = min(prior_pairs, remaining)
        out.update(central=central, low=central, high=remaining, keep_route=False)
        return out
    if projection.get("remaining") is not None:
        remaining = projection["remaining"]
        out["remaining"] = remaining
    pairs = projection["pairs"]
    if projection.get("blocked"):
        # Waiting on a second Claude Code version: no pairs move it, a new
        # CLI release does. Charge the cell nothing more until then.
        central = 0
    elif projection.get("past_cap") or not _number(pairs):
        central = remaining
    else:
        central = min(math.ceil(pairs), remaining)
    keep = projection.get("keep")
    remove = projection.get("remove")
    remove = math.inf if remove is None else remove
    keep_route = _number(keep) and keep <= remove \
        and math.ceil(keep) <= remaining
    out.update(central=central, low=central, high=remaining, keep_route=bool(keep_route))
    return out


def subject_estimate(cells: list) -> dict:
    """Deep-first pairs for one subject from its open cells' estimates: a
    keep in any cell ends the subject, a removal needs every cell."""
    keeps = [c for c in cells if c["keep_route"]]
    every = {k: sum(c[k] for c in cells) for k in ("central", "low", "high")}
    if keeps:
        best = min(keeps, key=lambda c: c["central"])
        return {"route": "keep", "central": best["central"], "low": best["central"],
                "high": every["high"], "cells": cells}
    return {"route": "remove-or-cap", **every, "cells": cells}


def pair_usd(gates: dict) -> dict:
    """{model: mean $ per pair} over every counted cell in the verdict
    document: each cell's `cost_usd` (both arms, judge included) over its
    `pairs`."""
    spent, pairs = {}, {}
    for kind in ("skills", "guidance"):
        for subject in (gates.get(kind) or {}).values():
            for cell in subject.get("cells") or []:
                n = cell.get("pairs")
                usd = cell.get("cost_usd")
                if isinstance(n, int) and n > 0 and _number(usd) and usd > 0:
                    spent[cell["model"]] = spent.get(cell["model"], 0.0) + usd
                    pairs[cell["model"]] = pairs.get(cell["model"], 0) + n
    return {m: spent[m] / pairs[m] for m in spent}


def subject_usd(subject: dict, costs: dict, overhead_per_pair: float, key: str) -> float:
    """Dollars for `key` (central, low or high) pairs of a subject, pricing
    each cell at its model's mean pair cost plus the fire overhead. A keep
    route charges only its best cell for central and low."""
    cells = subject["cells"]
    fallback = sum(costs.values()) / len(costs) if costs else 0.0
    if subject["route"] == "keep" and key in ("central", "low"):
        best = min((c for c in cells if c["keep_route"]), key=lambda c: c["central"])
        cells = [best]
        return best["central"] * (costs.get(best["model"], fallback) + overhead_per_pair)
    return sum(c[key] * (costs.get(c["model"], fallback) + overhead_per_pair) for c in cells)


def open_subjects(ctx: dict, cells: list, prior_pairs: float) -> dict:
    """{(kind, name): subject estimate} for every subject with at least one
    cell the planner would fire (`plan_week._produces_item`). A cell of a
    subject already kept (not on a provisional keep) is left out: the planner
    fires it only at its re-check age (`eval_items`), which the re-check
    keep-up item prices."""
    grouped: dict = {}
    for cell in cells:
        if not plan_week._produces_item(cell):
            continue
        if cell.get("verdict") == "keep" and not cell.get("provisional_keep"):
            continue
        kind = "guidance" if cell.get("section") else "skill"
        name = cell.get("section") or cell.get("skill")
        grouped.setdefault((kind, name), []).append(cell_estimate(cell, ctx, prior_pairs))
    return {key: subject_estimate(group) for key, group in grouped.items()}


def paused_subjects(gates: dict) -> dict:
    """{(kind, name): rule} for subjects every one of whose cells is paused
    by the scope pass, by its rule (zero-use, ceiling, floor, removed)."""
    out = {}
    for kind, block in (("skill", "skills"), ("guidance", "guidance")):
        for name, subject in (gates.get(block) or {}).items():
            cells = subject.get("cells") or []
            if cells and all(c.get("class") == "paused" for c in cells):
                rules = sorted({str((c.get("scope_paused") or {}).get("rule")
                                    if isinstance(c.get("scope_paused"), dict)
                                    else c.get("scope_paused")) for c in cells})
                out[(kind, name)] = ",".join(rules)
    return out


def dormant_usd(gates: dict, costs: dict, overhead: float, prior_pairs: float) -> float:
    """Dollars to bring back every skill paused only for zero use, should
    each get its first use: each paused cell at the prior pairs, priced at
    its model."""
    fallback = sum(costs.values()) / len(costs) if costs else 0.0
    total = 0.0
    for (kind, name), rule in paused_subjects(gates).items():
        if kind != "skill" or rule != "zero-use":
            continue
        for cell in gates["skills"][name]["cells"]:
            total += prior_pairs * (costs.get(cell.get("model"), fallback) + overhead)
    return total


def recheck_usd_per_week(gates: dict, costs: dict, overhead: float,
                         skipped_sections: frozenset = frozenset(),
                         stakes_table: dict | None = None) -> float:
    """Dollars a week of re-checks of kept subjects: each kept cell's
    `recheck.projected_pairs` (harness/gates.py, THE RE-CHECK WINDOW and
    THE RE-CHECK CARRY; the cap when absent), priced at its model's pair
    cost plus the fire overhead, over its re-check age (`recheck_weeks_high`
    for a high-stakes subject in evals/stakes.yml, else `recheck_weeks`)."""
    fallback = sum(costs.values()) / len(costs) if costs else 0.0
    total = 0.0
    for block, kind, key in (("skills", "skill", "policy"),
                             ("guidance", "guidance", "guidance_policy")):
        policy = gates.get(key) or gates["policy"]
        for name, subject in (gates.get(block) or {}).items():
            if subject.get("verdict") != "keep" or (block == "guidance"
                                                   and name in skipped_sections):
                continue
            high = stakes_table is not None and \
                stakes.level_of(stakes_table, kind, name) == "high"
            age = policy["recheck_weeks_high" if high else "recheck_weeks"]
            for cell in subject.get("cells") or []:
                recheck = cell.get("recheck")
                projected = recheck.get("projected_pairs") if isinstance(recheck, dict) else None
                pairs = projected if _number(projected) else policy["max_runs_per_cell"]
                total += pairs * (costs.get(cell.get("model"), fallback) + overhead) / age
    return total


#: A Monday 17:00 UTC weekly reset of the account allowance (evals/budget.yml).
RESET_ANCHOR = datetime(2026, 10, 26, 17, tzinfo=timezone.utc)


def measured_usd_per_point(results_tree: Path, legacy_rate) -> dict | None:
    """Eval dollars per allowance point measured on the ingested runs under
    `results_tree`: each routine run's trial `usage.measured` blocks priced
    from token counts by type (`allowance_points.estimate_blocks`, as
    allowance_guard.run_points and dashboard/build.py eval_run_points read
    them), summed over the runs priced wholly from tokens. `central` is those
    dollars over the estimate's points; `low` is over its high points and
    `high` over its low points (more points per dollar means fewer dollars per
    point). None when no run is priced wholly from tokens."""
    usd = points = low = high = 0.0
    runs = 0
    for run_dir in allowance_guard.all_runs(results_tree):
        blocks = []
        for path in allowance_guard._summary_paths(run_dir):
            summary = allowance_guard._load_summary(path)
            use = summary.get("usage") if isinstance(summary, dict) else None
            measured = use.get("measured") if isinstance(use, dict) else None
            if isinstance(measured, dict) and measured.get("scope") == "trial":
                blocks.append(measured)
        if not blocks:
            continue
        found = allowance_points.estimate_blocks(blocks, legacy_rate)
        if not (found["complete"] and found["roles_from_tokens"]) or found["points"] <= 0:
            continue
        usd += sum(float(block[role]["cost_usd"]) for block in blocks
                   for role in allowance_points.ROLES
                   if isinstance(block.get(role), dict) and block[role].get("calls")
                   and allowance_points._number(block[role].get("cost_usd")))
        points += found["points"]
        low += found["low"]
        high += found["high"]
        runs += 1
    if not runs or not usd or not points or not high:
        return None
    return {"central": usd / points, "low": usd / high,
            "high": usd / low if low else usd / points, "runs": runs,
            "usd": usd, "points": points, "points_low": low, "points_high": high}


def meter_non_eval_points(readings: list, eval_runs: list, end: datetime,
                          min_days: float = 2.0) -> dict | None:
    """Measured non-eval meter points a week over the account's current
    allowance week (from the newest Monday reset before `end`; the week
    before it when fewer than `min_days` have passed), from the `seven_day`
    meter readings (adam-agentskills-private
    persistent/usage-events:spend/meter-history.csv).

    A whole week, not a recent stretch: use comes in bursts, and a quiet
    early week and a busy weekend average out only over the week (Adam,
    2026-11-15: 94% with 86% of the week gone and no manual reset). Eval
    points (routine-results/*/cost_estimate.json) come off the rise, but
    never more than the meter rose while evals ran (first run to an hour
    after the last), since their calibration can overstate them. The rise
    sums increases between consecutive readings. The readings are whole
    percents the usage endpoint rounds, so the rise is also a range
    (`meter_rise_points_low`/`_high`, and `points_per_week_low`/`_high`
    with the eval points taken off as they are): each run of readings that
    never falls is one `allowance_points.delta_range`, and the runs add. None
    when fewer than two readings fall in the span."""
    start = RESET_ANCHOR + timedelta(days=7) * math.floor(
        (end - RESET_ANCHOR) / timedelta(days=7))
    if (end - start) < timedelta(days=min_days):
        start -= timedelta(days=7)
        end = start + timedelta(days=7)
    span = sorted((t, p) for t, p in readings if start <= t <= end)
    if len(span) < 2:
        return None

    def rise(lo, hi):
        # From the last reading at or before lo to the first at or after hi.
        first = max((i for i, x in enumerate(span) if x[0] <= lo), default=0)
        last = min((i for i, x in enumerate(span) if x[0] >= hi), default=len(span) - 1)
        pts = span[first:last + 1]
        low = high = 0.0
        begin = 0
        for k in range(1, len(pts) + 1):
            if k == len(pts) or pts[k][1] < pts[k - 1][1]:
                if k - 1 > begin:
                    seg = allowance_points.delta_range(
                        pts[begin][1], pts[k - 1][1], allowance_points.USAGE_ENDPOINT)
                    low += max(0.0, seg[0])
                    high += max(0.0, seg[1])
                begin = k
        return sum(max(0.0, b[1] - a[1]) for a, b in zip(pts, pts[1:])), low, high

    total, total_low, total_high = rise(span[0][0], span[-1][0])
    runs = sorted((t, p) for t, p in eval_runs if span[0][0] <= t <= span[-1][0])
    calibrated = sum(p for _, p in runs)
    while_running = rise(runs[0][0], runs[-1][0] + timedelta(hours=1))[0] if runs else 0.0
    evals = min(calibrated, while_running)
    covered = (span[-1][0] - span[0][0]).total_seconds() / 86400
    return {"points_per_week": max(0.0, total - evals) * 7 / covered,
            "points_per_week_low": max(0.0, total_low - evals) * 7 / covered,
            "points_per_week_high": max(0.0, total_high - evals) * 7 / covered,
            "meter_rise_points": total, "meter_rise_points_low": total_low,
            "meter_rise_points_high": total_high, "eval_points": evals,
            "eval_points_calibrated": calibrated, "eval_rise_while_running": while_running,
            "from": span[0][0].isoformat(), "to": span[-1][0].isoformat(),
            "readings": len(span)}


def weeks_to_clear(backlog: float, capacity: float, keep_up: float) -> float:
    """Weeks to spend `backlog` dollars at `capacity` a week less the
    keep-up spend; inf when keep-up takes the whole capacity."""
    room = capacity - keep_up
    if backlog <= 0:
        return 0.0
    return backlog / room if room > 0 else math.inf


def forecast(gates: dict, cells: list, budget: dict, batch_policy: dict,
             batch: dict | None, assumptions: dict,
             skipped_sections: frozenset = frozenset(),
             stakes_table: dict | None = None,
             automatic: dict | None = None,
             measured_non_eval: dict | None = None,
             measured_rate: dict | None = None) -> dict:
    """The forecast document: backlog, keep-up and catch-up, each a
    central figure with a low-high range, and every input with its source."""
    ctx = {"policy": gates.get("policy"), "guidance_policy": gates.get("guidance_policy")}
    prior_pairs = float(batch_policy["pairs_per_cell"])
    a = {k: assumptions.get(k, default) for k, (default, _) in ASSUMPTION_KEYS.items()}
    # Eval runs are charged from tokens by type (harness/allowance_points.py);
    # the forecast works in dollars. Dollars per point is measured on the
    # ingested runs' own estimates (`measured_rate`, from
    # `measured_usd_per_point`: low and high from the estimate's high and
    # low points); with no run priced from tokens it falls back to the
    # legacy rate, the eval mix's measured dollars per point (night 1,
    # 2026-11-19), the lower of its two models. An assumption wins.
    rate = measured_rate["central"] if measured_rate else budget["legacy_usd_per_point"]
    low_rate = a["usd_per_point_low"] or (measured_rate["low"] if measured_rate else rate)
    high_rate = a["usd_per_point_high"] or (
        measured_rate["high"] if measured_rate and not a["usd_per_point_low"] else low_rate)
    rate_source = (
        f"measured on {measured_rate['runs']} ingested runs priced from token counts "
        "(routine-results trial usage.measured through allowance_points.estimate_blocks)"
        if measured_rate else "evals/budget.yml legacy_usd_per_point")
    cap_points = budget["weekly_cap"] * 100
    # Non-eval meter use by category (scripts/automatic_spend.py): each
    # automatic category's meter points, estimated from its fires' token
    # counts (a breakdown from before points: its dollars at the mid
    # $/point), plus people's own use. It sets non_eval_points_per_week
    # unless that is given.
    breakdown = None
    mid = (low_rate + high_rate) / 2

    def meter_points(doc, key):
        points = doc.get(key.replace("_usd_", "_points_"))
        return points if points is not None else (doc.get(key) or 0) / mid

    if automatic is not None:
        breakdown = {c["label"]: meter_points(c, "meter_usd_per_week")
                     for c in automatic.get("categories") or [] if meter_points(c, "meter_usd_per_week")}
        # Measured total less the automatic jobs is people's own use.
        if a["interactive_points_per_week"] is None and measured_non_eval is not None:
            a["interactive_points_per_week"] = max(
                0.0, measured_non_eval["points_per_week"] - sum(breakdown.values()))
        if a["interactive_points_per_week"] is not None:
            breakdown["Interactive threads and local sessions"] = a["interactive_points_per_week"]
            if a["non_eval_points_per_week"] is None:
                a["non_eval_points_per_week"] = sum(breakdown.values())
    # Each scheduled task on the meter, in points a week (Adam, 2026-11-20:
    # "add individual scheduled tasks"). A task outside the loop is named
    # by its category only: personal tasks' names can be private, and this
    # document is committed to a public repository.
    tasks = None
    if automatic is not None:
        labels = {c.get("id"): c.get("label") for c in automatic.get("categories") or []}
        tasks = []
        for job in automatic.get("jobs") or []:
            if job.get("kind") != "scheduled task" or job.get("lane") != "meter":
                continue
            points = job.get("points_per_week")
            if points is None and job.get("usd_per_week") is not None:
                points = job["usd_per_week"] / mid
            in_loop = job.get("in_loop")
            tasks.append({
                "task": job.get("name") if in_loop else
                f"{labels.get(job.get('category')) or 'Other'} (outside the loop)",
                "in_loop": in_loop, "model": job.get("model") if in_loop else None,
                "fires_per_week": job.get("fires_per_week"), "points_per_week": points})
        tasks.sort(key=lambda t: (t["points_per_week"] is None, -(t["points_per_week"] or 0.0),
                                  str(t["task"])))
    # The loop's own automatic jobs share the cap with evals (Adam,
    # 2026-11-15: all automated parts of the system fit in the 25%).
    loop_points = None
    if automatic is not None and (automatic.get("loop_meter_points_per_week") is not None
                                  or automatic.get("loop_meter_usd_per_week") is not None):
        loop_points = meter_points(automatic, "loop_meter_usd_per_week")
        if a["loop_jobs_in_cap"]:
            cap_points = max(0.0, cap_points - loop_points)
    # The account stop: evals halt once the whole meter passes it, so other
    # use leaves them at most the stop less that use.
    stop = budget.get("stop_when_account_above")
    squeeze = None
    if a["non_eval_points_per_week"] is not None and stop is not None:
        other = a["non_eval_points_per_week"]
        pace = a["eval_points_per_hour"]
        # The pace hold (allowance_guard.py, 2026-11-20) refuses every fire
        # while the account is above stop * week gone, so evals no longer
        # spend the cap first: over a week they get the stop less other use.
        if pace and not a["pace_hold"]:
            # Evals run first: the guard's fixed cap is a floor
            # (allowance_guard.py `room`), so from the Monday reset they fire
            # until the cap is spent, and the stop binds only on the other
            # use that accrues meanwhile (E + other * E / (pace * 168) = stop).
            cap_points = min(cap_points, stop * 100 / (1 + other / (pace * 168)))
            # What that leaves the owner's own use: the week's total past 100
            # comes off the end of the week, at the non-eval rate.
            over = cap_points + other - 100
            squeeze = {"week_total_points": cap_points + other,
                       "days_at_limit_before_reset": max(0.0, over) / (other / 7) if other else 0.0}
        else:
            cap_points = max(0.0, min(cap_points, stop * 100 - other))
    costs = pair_usd(gates)
    if a["measured_usd_per_pair"] and costs:
        scale = a["measured_usd_per_pair"] / (sum(costs.values()) / len(costs))
        costs = {m: c * scale for m, c in costs.items()}
    overhead = a["fire_overhead_usd"] / a["pairs_per_fire"]

    subjects = open_subjects(ctx, [c for c in cells
                                   if c.get("section") not in skipped_sections], prior_pairs)
    rows = []
    for (kind, name), s in sorted(subjects.items()):
        rows.append({"kind": kind, "subject": name, "route": s["route"],
                     "open_cells": len(s["cells"]),
                     "unprojected_cells": sum(1 for c in s["cells"] if not c["projected"]),
                     **{f"pairs_{k}": s[k] for k in ("central", "low", "high")},
                     **{f"usd_{k}": subject_usd(s, costs, overhead, k)
                        for k in ("central", "low", "high")}})
    backlog = {k: sum(r[f"usd_{k}"] for r in rows) for k in ("central", "low", "high")}
    pairs = {k: sum(r[f"pairs_{k}"] for r in rows) for k in ("central", "low", "high")}

    # Keep-up: what arrives each week, priced at this backlog's median subject.
    per_subject = sorted(r["usd_central"] for r in rows) or [0.0]
    median = per_subject[len(per_subject) // 2]
    mean_pair = sum(costs.values()) / len(costs) + overhead if costs else 0.0
    rates = (batch or {}).get("rates") or {}
    new_skills = a["new_skills_per_week"] if a["new_skills_per_week"] is not None \
        else rates.get("skill", batch_policy["rates"]["skill"])
    new_sections = a["new_sections_per_week"] if a["new_sections_per_week"] is not None \
        else rates.get("guidance", batch_policy["rates"]["guidance"])
    first_use = a["first_use_share"] if a["first_use_share"] is not None else 1.0
    evaluated = a["evaluated_section_share"] if a["evaluated_section_share"] is not None else 1.0
    models = len(gates.get("roster_models") or costs or [1])
    decided = sum(1 for block in ("skills", "guidance")
                  for name, s in (gates.get(block) or {}).items()
                  if s.get("verdict") == "keep"
                  and not (block == "guidance" and name in skipped_sections))
    # Under keep_stands_until_recheck (gate-policy.yml) a rest change no
    # longer reopens a guidance keep; the re-check item prices it instead.
    stands = bool((gates.get("guidance_policy") or {}).get("keep_stands_until_recheck"))
    rest_changes = 0.0 if stands else a["guidance_rest_changes_per_week"]
    keep_up_items = {
        "new skills (first use only)": new_skills * first_use * median,
        "new guidance sections": new_sections * evaluated * median,
        "new fixtures on open subjects": a["new_fixtures_per_week_open"] * models
        * prior_pairs * mean_pair,
        "skill text edits": a["skill_text_edits_per_week"] * median,
        "re-checks of kept subjects": recheck_usd_per_week(gates, costs, overhead,
                                                           skipped_sections, stakes_table),
        # A git hook's verdict comes from its usage (evals/hook-policy.yml),
        # not from eval runs, so new hooks cost no eval dollars.
        "new git hooks": 0.0,
        "guidance keeps re-proved after a rest change": rest_changes
        * sum(r["usd_central"] for r in rows if r["kind"] == "guidance" and r["route"] == "keep"),
    }
    keep_up = sum(keep_up_items.values())

    capacity = {"plan_low": cap_points * low_rate, "plan_high": cap_points * high_rate}
    capacity["plan_central"] = (capacity["plan_low"] + capacity["plan_high"]) / 2
    api = a["api_credit_usd_per_week"]
    start = datetime.fromisoformat(a["start"].replace("Z", "+00:00")) if a["start"] else None

    def scenario(extra: float) -> dict:
        cap_c = capacity["plan_central"] + extra
        out = {"capacity_usd": cap_c,
               "weeks_central": weeks_to_clear(backlog["central"], cap_c, keep_up),
               # Fastest: the low backlog at the high capacity; slowest: the
               # high backlog at the low capacity.
               "weeks_fast": weeks_to_clear(backlog["low"], capacity["plan_high"] + extra, keep_up),
               "weeks_slow": weeks_to_clear(backlog["high"], capacity["plan_low"] + extra, keep_up)}
        if start:
            for k in ("weeks_central", "weeks_fast", "weeks_slow"):
                w = out[k]
                out[k.replace("weeks", "done")] = None if math.isinf(w) else \
                    (start + timedelta(weeks=w)).isoformat()
        return out

    return {
        "inputs": {
            "verdict_as_of": gates.get("as_of"), "newest_run": gates.get("newest_run"),
            "weekly_cap_points": cap_points, "usd_per_point": [low_rate, high_rate],
            "usd_per_point_central": rate,
            "points_per_usd_source": rate_source,
            "max_runs_per_cell": gates["policy"]["max_runs_per_cell"],
            "pairs_per_cell_prior": prior_pairs,
            "pair_usd_by_model": costs, "fire_overhead_per_pair_usd": overhead,
            "assumptions": a, "batch_rates": rates,
            "non_eval_points_breakdown": breakdown,
            "scheduled_tasks": tasks,
            "loop_jobs_points_per_week": loop_points,
            "measured_non_eval": measured_non_eval,
            "owner_squeeze": squeeze,
            "automatic_spend_as_of": (automatic or {}).get("as_of"),
            # A count, not names: job names can be private, and this
            # document is committed to a public repository.
            "automatic_unmeasured_jobs": len((automatic or {}).get("unmeasured") or []),
        },
        "subjects": rows,
        "paused_subjects": {f"{k}:{n}": r for (k, n), r in sorted(paused_subjects(gates).items())},
        "skipped_sections": sorted(skipped_sections),
        "dormant_zero_use_usd": dormant_usd(gates, costs, overhead, prior_pairs),
        "backlog_usd": backlog, "backlog_pairs": pairs,
        "backlog_points_central": backlog["central"] / ((low_rate + high_rate) / 2),
        "keep_up_usd_per_week": keep_up, "keep_up_items": keep_up_items,
        "median_subject_usd": median, "kept_subjects": decided,
        "capacity_usd_per_week": capacity,
        "scenarios": {"plan_cap_only": scenario(0.0),
                      "plan_cap_plus_api_credit": scenario(api)},
    }


def _iso(text: str) -> datetime:
    t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def eval_run_points(results_tree: Path) -> list:
    """(start time, meter points) of each routine eval run, from its run id
    (YYYYMMDDTHHMMSSZ-...) and cost_estimate.json `points`."""
    out = []
    for path in sorted((results_tree / "routine-results").glob("*/cost_estimate.json")):
        try:
            when = datetime.strptime(path.parent.name[:16], "%Y%m%dT%H%M%SZ") \
                .replace(tzinfo=timezone.utc)
            points = json.loads(path.read_text(encoding="utf-8")).get("points")
        except (ValueError, OSError):
            continue
        # cost_estimate.json `points` is a fraction of the allowance, as
        # budget.yml's values are: 0.01 is one meter point.
        if isinstance(points, (int, float)):
            out.append((when, float(points) * 100))
    return out


def eval_pace(runs: list, cap_points: float, now: datetime) -> dict | None:
    """Meter points an hour evals spent from each weekly reset until they
    had spent `cap_points`, over the weeks before `now` that reached it; the
    median. None when no week did."""
    paces = []
    start = RESET_ANCHOR
    while start < now:
        total = 0.0
        for t, points in sorted(runs):
            if start <= t < start + timedelta(days=7):
                total += points
                if total >= cap_points:
                    hours = (t - start).total_seconds() / 3600
                    if hours > 0:
                        paces.append(cap_points / hours)
                    break
        start += timedelta(days=7)
    if not paces:
        return None
    paces.sort()
    return {"points_per_hour": paces[len(paces) // 2], "weeks": len(paces)}


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--gates", type=Path, required=True,
                   help="verdict document from scripts/compute_gates.py")
    p.add_argument("--results-tree", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    p.add_argument("--assumptions", type=Path, default=None)
    p.add_argument("--guidance", type=Path, default=None,
                   help="_agent-guidance checkout: its eval-coverage skipped rows are left out")
    p.add_argument("--arrivals", type=Path, default=None,
                   help="arrivals document (scripts/target_arrivals.py); default: "
                        "arrivals/targets.json in --results-tree")
    p.add_argument("--automatic-spend", type=Path, default=None,
                   help="breakdown from scripts/automatic_spend.py: non-eval points by category")
    p.add_argument("--meter-history", type=Path, default=None,
                   help="meter readings CSV (ts_utc, meter_name, percent; adam-agentskills-private "
                        "persistent/usage-events:spend/meter-history.csv): measures the non-eval "
                        "total over the allowance week, less eval runs' points from --results-tree")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                   help="override one assumption (a number, or text for start); repeatable")
    p.add_argument("--out-json", type=Path, required=True)
    args = p.parse_args(argv)
    gates = json.loads(args.gates.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
    now = (now if now.tzinfo else now.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    cells, _, _ = plan_week.eval_cells_and_outages(
        args.evals_dir, gates, [], now, plan_week.routine_git_version(args.results_tree))
    budget = yaml.safe_load((args.evals_dir / "budget.yml").read_text(encoding="utf-8"))
    batch_policy = yaml.safe_load((args.evals_dir / "batch-policy.yml").read_text(encoding="utf-8"))
    batch_path = args.results_tree / "batches" / "current.json"
    batch = json.loads(batch_path.read_text(encoding="utf-8")) if batch_path.is_file() else None
    assumptions = yaml.safe_load(args.assumptions.read_text(encoding="utf-8")) \
        if args.assumptions else {}
    assumptions = dict(assumptions or {})
    for item in args.set:
        key, _, value = item.partition("=")
        try:
            number = float(value)
        except ValueError:
            assumptions[key] = value
            continue
        if not math.isfinite(number):
            p.error(f"--set {key}: not a finite number")
        assumptions[key] = number
    unknown = set(assumptions) - set(ASSUMPTION_KEYS)
    if unknown:
        p.error(f"unknown assumption keys: {sorted(unknown)}")
    arrivals_path = args.arrivals or args.results_tree / "arrivals" / "targets.json"
    try:
        arrivals_doc = json.loads(arrivals_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        if args.arrivals:
            p.error(f"--arrivals {args.arrivals}: not a readable JSON file")
        arrivals_doc = None
    from_arrivals = arrival_assumptions(arrivals_doc, now)
    assumptions, sources = merge_assumptions(assumptions, from_arrivals)
    skipped = plan_week.guidance_skipped(args.guidance) or frozenset()
    table = stakes.load(args.evals_dir / "stakes.yml", args.evals_dir)
    automatic = json.loads(args.automatic_spend.read_text(encoding="utf-8")) \
        if args.automatic_spend else None
    measured = None
    if args.meter_history:
        readings = [(_iso(r["ts_utc"]), float(r["percent"]))
                    for r in csv.DictReader(args.meter_history.open(encoding="utf-8"))
                    if r.get("meter_name") == "seven_day"]
        measured = meter_non_eval_points(readings, eval_run_points(args.results_tree), now)
        if measured is None:
            p.error("--meter-history: fewer than two seven_day readings in the allowance week")
    if "eval_points_per_hour" not in assumptions:
        measured_pace = eval_pace(eval_run_points(args.results_tree),
                                  budget["weekly_cap"] * 100, now)
        if measured_pace:
            assumptions["eval_points_per_hour"] = measured_pace["points_per_hour"]
            sources["eval_points_per_hour"] = (
                f"routine-results: median over {measured_pace['weeks']} week(s) of the hours "
                "from the reset until evals spent the cap")
    doc = forecast(gates, cells, budget, batch_policy, batch, assumptions, skipped, table,
                   automatic, measured,
                   measured_usd_per_point(args.results_tree, budget["legacy_usd_per_point"]))
    if automatic is not None and "non_eval_points_per_week" not in assumptions:
        if assumptions.get("interactive_points_per_week") is not None:
            sources["non_eval_points_per_week"] = \
                "--automatic-spend categories + interactive_points_per_week"
        elif measured is not None:
            sources["non_eval_points_per_week"] = \
                "--automatic-spend categories + the rest of --meter-history's measured total"
            sources["interactive_points_per_week"] = \
                "--meter-history measured total less --automatic-spend categories"
    doc["inputs"]["assumption_sources"] = sources
    # Why an arrival rate fell back, so a reader can tell a default from data.
    doc["inputs"]["arrivals_status"] = (
        "missing" if arrivals_doc is None
        else "unused: stale, malformed or no complete kind" if not from_arrivals
        else "used for " + ", ".join(sorted(from_arrivals)))
    doc["inputs"]["arrivals_as_of"] = arrivals_doc.get("as_of") \
        if isinstance(arrivals_doc, dict) and any(v == "arrivals/targets.json"
                                                  for v in sources.values()) else None
    args.out_json.write_text(json.dumps(doc, indent=1, default=str) + "\n", encoding="utf-8")
    s = doc["scenarios"]["plan_cap_only"]
    print(f"open subjects {len(doc['subjects'])}, backlog ${doc['backlog_usd']['central']:.0f} "
          f"(${doc['backlog_usd']['low']:.0f}-${doc['backlog_usd']['high']:.0f}), keep-up "
          f"${doc['keep_up_usd_per_week']:.0f}/wk, capacity ${s['capacity_usd']:.0f}/wk, "
          f"catch-up {s['weeks_central']:.1f} wk")
    for task in doc["inputs"]["scheduled_tasks"] or []:
        points = task["points_per_week"]
        print(f"  scheduled task {task['task']}: "
              + ("unmeasured" if points is None else f"{points:.1f} points/wk")
              + ("" if task["in_loop"] else ", outside the loop"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
