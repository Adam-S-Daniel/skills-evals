#!/usr/bin/env python3
"""Compute the model roster: which models this harness runs against today.

A PURE FUNCTION OVER FILES. `compute_roster()` takes already-parsed documents
and a frozen `now`, and returns the roster dict — no network, no clock, no
environment. The one network call in the whole feature lives in
`scripts/refresh_models.py`, which produces this module's `models_doc`.

Inputs
  models_doc   {"fetched_at": ..., "models": [{id, created_at, ...}, ...]} —
               availability, straight from GET /v1/models.
  census_doc   {"generated_at": ..., "weeks": [...], "counts": {model: {week: n}}}
               — usage, published to `eval-results` as usage/latest.json by
               scripts/model_usage_census.py. Optional: absent or older than
               the policy's freshness window and the roster falls back to
               "newest per tier" and says so in every reason.
  policy       evals/roster-policy.yml — every threshold, plus the tier ladder.
  previous     the last published roster, for added/retired-since-last.

Output — roster/latest.json on `eval-results`:
  {generated_at, source: {models_api_at, census_at, admin_report_at},
   arms: [{id, reason}], judge: {id, reason}, preflight: {id, reason},
   retired_since_last: [...], added_since_last: [...]}

Every entry carries its reason IN WORDS. The explorer tool renders them, and a
roster nobody can explain is one nobody will override when it is wrong.

NO MODEL ID APPEARS IN THIS FILE. Tier comes from the family word in the id
itself, matched against the ladder in roster-policy.yml.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

# The Models API has no price field, so "cheapest" and "most capable" are both
# read off the tier ladder rather than off a number. Within one tier the newest
# model is taken as the current one — which is true of every tier transition so
# far (a new version supersedes its predecessor at the same or lower price).
# If that ever stops holding, this is the assumption to revisit first.


def load_policy(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: str | Path | None) -> dict | None:
    """Read a JSON document, treating absent/empty/corrupt as absent.

    CI materializes the optional inputs with `git show ... || true`, which
    leaves an EMPTY file behind when the branch or the path does not exist yet
    — the first run, every time. That is a legitimate "no census", not a
    failure, so it must not raise.
    """
    if path is None:
        return None
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def parse_ts(value: str | None) -> datetime | None:
    """Parse an RFC 3339 timestamp, `Z` included. None on anything unparseable."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def iso_week(moment: datetime) -> str:
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"


def window_weeks(now: datetime, count: int) -> list[str]:
    """The `count` ISO week labels ending with the one `now` falls in."""
    return [iso_week(now - timedelta(weeks=offset)) for offset in range(count)]


def tier_of(model_id: str, tiers: list[str]) -> str | None:
    """The model's tier, from the family word in its own id.

    Token match on `-`, not a substring search: a substring test would let an
    id that merely CONTAINS a family word inside a longer token claim that
    tier. Unrecognised family word -> None -> unranked.
    """
    tokens = set(str(model_id).lower().split("-"))
    for tier in tiers:
        if tier in tokens:
            return tier
    return None


def usage_share(counts: dict, model_id: str, weeks: list[str]) -> float:
    """Percent of ALL census usage over `weeks` that `model_id` carries.

    The denominator counts every model the census saw, including ones the
    Models API no longer lists — the question is what share of the fleet's real
    work this model did, and work done on a since-retired model still happened.
    """
    total = 0
    mine = 0
    for candidate, by_week in (counts or {}).items():
        for week, n in (by_week or {}).items():
            if week in weeks:
                total += n
                if candidate == model_id:
                    mine += n
    return 0.0 if total == 0 else 100.0 * mine / total


def _rank(model: dict, tiers: list[str]) -> tuple:
    """Capability sort key: tier first, then newest, then id for determinism."""
    tier = tier_of(model["id"], tiers)
    created = parse_ts(model.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
    return (tiers.index(tier), created, model["id"])


def compute_roster(models_doc: dict, census_doc: dict | None, policy: dict,
                   previous: dict | None, now: datetime,
                   admin_doc: dict | None = None) -> dict:
    tiers = list(policy["tiers"])
    available = [m for m in (models_doc.get("models") or [])
                 if tier_of(m["id"], tiers) is not None]
    available.sort(key=lambda m: _rank(m, tiers))
    by_id = {m["id"]: m for m in available}

    # --- is the census usable? -------------------------------------------
    census_at = parse_ts((census_doc or {}).get("generated_at"))
    counts = (census_doc or {}).get("counts") or {}
    max_age = timedelta(days=policy["census_max_age_days"])
    if census_doc is None or census_at is None:
        fresh, stale_note = False, "no fresh census (none published)"
    elif now - census_at > max_age:
        age = (now - census_at).days
        fresh = False
        stale_note = (f"no fresh census (last published {age} days ago, over the "
                      f"{policy['census_max_age_days']}-day window)")
    else:
        fresh, stale_note = True, ""

    enter_weeks = window_weeks(now, policy["arm_enter_window_weeks"])
    exit_weeks = window_weeks(now, policy["arm_exit_window_weeks"])
    previous_arms = [a["id"] for a in ((previous or {}).get("arms") or [])]

    newest_by_tier: dict[str, str] = {}
    for model in available:  # sorted weakest-first, oldest-first within a tier
        newest_by_tier[tier_of(model["id"], tiers)] = model["id"]

    # --- who is an arm, and why ------------------------------------------
    arms: list[dict] = []
    for model in available:
        model_id = model["id"]
        tier = tier_of(model_id, tiers)
        created = parse_ts(model.get("created_at"))
        age_days = (now - created).days if created else None
        is_newest = newest_by_tier.get(tier) == model_id
        old_enough = age_days is not None and age_days >= policy["cooling_off_days"]

        reason = None
        if fresh:
            share = usage_share(counts, model_id, enter_weeks)
            if share >= policy["arm_enter_usage_pct"]:
                reason = (f"carries {share:.1f}% of census usage over the last "
                          f"{policy['arm_enter_window_weeks']} weeks "
                          f"(at or above the {policy['arm_enter_usage_pct']}% entry bar)")
        if reason is None and is_newest and old_enough:
            newest_words = (f"newest model in the {tier} tier, {age_days} days old "
                            f"(past the {policy['cooling_off_days']}-day cooling-off)")
            reason = newest_words if fresh else f"{stale_note}; fell back to newest per tier — {newest_words}"
        if reason is None and fresh and model_id in previous_arms:
            held = usage_share(counts, model_id, exit_weeks)
            if held >= policy["arm_exit_usage_pct"]:
                reason = (f"held over from the previous roster: still "
                          f"{held:.1f}% of census usage over the last "
                          f"{policy['arm_exit_window_weeks']} weeks (at or above "
                          f"the {policy['arm_exit_usage_pct']}% exit bar)")
        if reason:
            arms.append({"id": model_id, "reason": reason})

    arm_ids = {a["id"] for a in arms}

    # --- judge -------------------------------------------------------------
    # Preference order, and the last rung is not decorative: with no census the
    # arm set is "newest per tier", which on a catalogue holding one current
    # model per tier is EVERY available model — the state of the very first run,
    # before any census has been published. Emitting a null judge there would
    # ship a roster with a hole in it, so the fallback names the strongest model
    # available and says out loud that it is also an arm, leaving the caller to
    # decide rather than leaving it to find out.
    strongest_arm_tier = max((tiers.index(tier_of(a, tiers)) for a in arm_ids),
                             default=None)
    non_arms = [m for m in available if m["id"] not in arm_ids]
    above = ([m for m in non_arms
              if tiers.index(tier_of(m["id"], tiers)) > strongest_arm_tier]
             if strongest_arm_tier is not None else [])

    if above:
        pick = above[-1]
        judge = {"id": pick["id"],
                 "reason": (f"most capable available model at least one tier above "
                            f"the strongest arm model ({tier_of(pick['id'], tiers)} "
                            f"over {tiers[strongest_arm_tier]}), and not itself an arm")}
    elif non_arms:
        pick = non_arms[-1]
        arm_tier_words = (f" — nothing available sits above the strongest arm's "
                          f"{tiers[strongest_arm_tier]} tier"
                          if strongest_arm_tier is not None else "")
        judge = {"id": pick["id"],
                 "reason": f"strongest available model that is not an arm{arm_tier_words}"}
    elif available:
        pick = available[-1]
        judge = {"id": pick["id"],
                 "reason": ("strongest available model — every available model is "
                            "currently an arm, so no non-arm judge exists; do not "
                            "run this model as the arm and the judge of the same run")}
    else:
        judge = {"id": None,
                 "reason": "the Models API returned no model this policy can rank"}

    # --- preflight ---------------------------------------------------------
    # Cheapest = the lowest tier the API still returns, and the newest model
    # within it (the Models API exposes no price; the ladder is the proxy).
    cheapest = by_id[newest_by_tier[tier_of(available[0]["id"], tiers)]] if available else None
    preflight = ({"id": cheapest["id"],
                  "reason": (f"cheapest available model: the {tier_of(cheapest['id'], tiers)} "
                             f"tier is the lowest the Models API still returns, and this "
                             f"is the newest model in it")}
                 if cheapest else {"id": None, "reason": "the Models API returned no "
                                                         "model this policy can rank"})

    # --- what moved --------------------------------------------------------
    added: list[dict] = []
    retired: list[dict] = []
    if previous is not None:
        added = [a for a in arms if a["id"] not in previous_arms]
        for model_id in previous_arms:
            if model_id in arm_ids:
                continue
            if model_id not in by_id:
                why = "no longer returned by the Models API"
            elif not fresh:
                why = (f"{stale_note}; the fallback roster is newest-per-tier and this "
                       f"model is not the newest in its tier")
            else:
                held = usage_share(counts, model_id, exit_weeks)
                why = (f"below the {policy['arm_exit_usage_pct']}% exit bar for the last "
                       f"{policy['arm_exit_window_weeks']} weeks ({held:.1f}%)")
            retired.append({"id": model_id, "reason": why})

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "models_api_at": models_doc.get("fetched_at"),
            "census_at": (census_doc or {}).get("generated_at") if fresh else None,
            "admin_report_at": (admin_doc or {}).get("fetched_at") if admin_doc else None,
        },
        "arms": arms,
        "judge": judge,
        "preflight": preflight,
        "retired_since_last": retired,
        "added_since_last": added,
    }


def render_summary(roster: dict) -> str:
    """Markdown for $GITHUB_STEP_SUMMARY. A roster change leads."""
    lines = ["### Model roster", ""]
    changed = roster["added_since_last"] or roster["retired_since_last"]
    if changed:
        lines.append("**Roster changed since the last run.**")
        for entry in roster["added_since_last"]:
            lines.append(f"- added `{entry['id']}` — {entry['reason']}")
        for entry in roster["retired_since_last"]:
            lines.append(f"- retired `{entry['id']}` — {entry['reason']}")
        lines.append("")
    else:
        lines += ["No change to the arm set since the last run.", ""]

    lines += ["| Role | Model | Why |", "| --- | --- | --- |"]
    for arm in roster["arms"]:
        lines.append(f"| arm | `{arm['id']}` | {arm['reason']} |")
    for role in ("judge", "preflight"):
        entry = roster[role]
        lines.append(f"| {role} | `{entry['id']}` | {entry['reason']} |")
    source = roster["source"]
    lines += ["", f"Models API `{source['models_api_at']}` · census "
                  f"`{source['census_at'] or 'none'}` · admin report "
                  f"`{source['admin_report_at'] or 'none'}`", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", required=True, type=Path,
                        help="models document from scripts/refresh_models.py")
    parser.add_argument("--policy", type=Path,
                        default=Path(__file__).resolve().parent.parent / "evals" / "roster-policy.yml")
    parser.add_argument("--census", type=Path, default=None,
                        help="usage/latest.json from eval-results; optional")
    parser.add_argument("--admin-report", type=Path, default=None,
                        help="optional Admin API usage report; recorded as provenance")
    parser.add_argument("--previous", type=Path, default=None,
                        help="the last published roster/latest.json; optional")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    models_doc = load_json(args.models)
    if models_doc is None:
        print(f"no models document at {args.models}", file=sys.stderr)
        return 1

    roster = compute_roster(
        models_doc=models_doc,
        census_doc=load_json(args.census),
        policy=load_policy(args.policy),
        previous=load_json(args.previous),
        now=datetime.now(timezone.utc),
        admin_doc=load_json(args.admin_report),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2)
        f.write("\n")
    print(render_summary(roster))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
