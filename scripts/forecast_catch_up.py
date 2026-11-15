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
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import plan_week  # noqa: E402

#: Assumptions the verdict document cannot supply. Each is (default, what
#: it is); a run's --assumptions file overrides any of them, and the output
#: records every value used.
ASSUMPTION_KEYS = {
    "usd_per_point_low": (None, "low end of the measured $ per weekly-meter point; "
                                "default: budget.yml points_per_usd"),
    "usd_per_point_high": (None, "high end of the same; default: as low"),
    "measured_usd_per_pair": (None, "mean run cost per pair over recent fires (cost_estimate.json); "
                                    "scales the verdict document's per-model costs to it"),
    "fire_overhead_usd": (0.19, "routine session cost per eval fire, outside the run's own calls"),
    "pairs_per_fire": (2.0, "pairs (one fixture x one model, both arms) one fire carries"),
    "api_credit_usd_per_week": (0.0, "extra eval dollars a week from the monthly API credit lane"),
    "new_hooks_per_week": (None, "git hooks added per week; default: arrivals/targets.json "
                                 "(reported, not priced)"),
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
                                       "account stop it can cap the eval points"),
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


def weeks_to_clear(backlog: float, capacity: float, keep_up: float) -> float:
    """Weeks to spend `backlog` dollars at `capacity` a week less the
    keep-up spend; inf when keep-up takes the whole capacity."""
    room = capacity - keep_up
    if backlog <= 0:
        return 0.0
    return backlog / room if room > 0 else math.inf


def forecast(gates: dict, cells: list, budget: dict, batch_policy: dict,
             batch: dict | None, assumptions: dict,
             skipped_sections: frozenset = frozenset()) -> dict:
    """The forecast document: backlog, keep-up and catch-up, each a
    central figure with a low-high range, and every input with its source."""
    ctx = {"policy": gates.get("policy"), "guidance_policy": gates.get("guidance_policy")}
    prior_pairs = float(batch_policy["pairs_per_cell"])
    a = {k: assumptions.get(k, default) for k, (default, _) in ASSUMPTION_KEYS.items()}
    # budget.yml values are fractions of the allowance: 0.01 is one point.
    rate = 1 / (budget["points_per_usd"] * 100)
    low_rate = a["usd_per_point_low"] or rate
    high_rate = a["usd_per_point_high"] or low_rate
    cap_points = budget["weekly_cap"] * 100
    # The account stop: evals halt once the whole meter passes it, so other
    # use leaves them at most the stop less that use.
    stop = budget.get("stop_when_account_above")
    if a["non_eval_points_per_week"] is not None and stop is not None:
        cap_points = max(0.0, min(cap_points, stop * 100 - a["non_eval_points_per_week"]))
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
    recheck_weeks = gates["policy"]["recheck_weeks"]
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
        "re-checks of kept subjects": decided * median / recheck_weeks,
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
            "points_per_usd_source": "evals/budget.yml points_per_usd",
            "max_runs_per_cell": gates["policy"]["max_runs_per_cell"],
            "pairs_per_cell_prior": prior_pairs,
            "pair_usd_by_model": costs, "fire_overhead_per_pair_usd": overhead,
            "assumptions": a, "batch_rates": rates,
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
    doc = forecast(gates, cells, budget, batch_policy, batch, assumptions, skipped)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
