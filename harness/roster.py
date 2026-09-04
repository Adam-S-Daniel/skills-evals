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
               scripts/model_usage_census.py. Optional: absent, older than the
               policy's freshness window, dated in the future, or empty over
               the window, and the roster falls back to "newest per tier" and
               says which of those it was in every reason.
  policy       evals/roster-policy.yml — every threshold, plus the tier ladder.
  previous     the last published roster, for added/retired-since-last.

TWO OF THOSE THREE COME OFF A PUBLIC BRANCH, written by other jobs on other
machines. They are inputs, not invariants: an entry without a string `id`, a
count that is not a number, a `previous.arms` entry that is not a dict — each
is skipped with a one-line named message, never a traceback, and never with
the offending value echoed into a public log.

Output — roster/latest.json on `eval-results`:
  {generated_at, source: {models_api_at, census_at, admin_report_at},
   arms: [{id, reason}], judge: {id, reason, is_arm}, preflight: {id, reason},
   unranked: [{id, reason}], excluded: [{id, reason}],
   compared_to_previous: bool, previous_state: "compared"|"none"|"unavailable",
   retired_since_last: [...], added_since_last: [...]}

Every entry carries its reason IN WORDS. The explorer tool renders them, and a
roster nobody can explain is one nobody will override when it is wrong.
`judge.is_arm` is the one thing a reason cannot carry: the runner has to refuse
a judge that is also an arm, and it cannot do that by reading prose.

NO MODEL ID APPEARS IN THIS FILE. Tier comes from the family word in the id
itself, matched against the ladder in roster-policy.yml.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from timeweeks import parse_ts, window_weeks
from timeweeks import iso_week  # noqa: F401 -- re-exported: identity-checked
                                 # by test_roster_and_census_share_one_week_implementation

# The Models API has no price field, so "cheapest" and "most capable" are both
# read off the tier ladder rather than off a number. Within one tier the newest
# model is taken as the current one — which is true of every tier transition so
# far (a new version supersedes its predecessor at the same or lower price).
# If that ever stops holding, this is the assumption to revisit first.

#: An id that is another id plus a date is a pinned snapshot of it, not a
#: second model. See `alias_map`.
SNAPSHOT_SUFFIX = re.compile(r"^(?P<base>.+)-[0-9]{8}$")


def _stderr(message: str) -> None:
    print(f"roster: {message}", file=sys.stderr)


def load_policy(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_json(path: str | Path | None) -> tuple[dict | None, str | None]:
    """(document, problem). Absent is not a problem; unreadable is.

    CI materializes the optional inputs with `git show ... || true`, which
    leaves an EMPTY file behind when the branch or the path does not exist yet
    — the first run, every time. That is a legitimate "not published", not a
    failure, so it must not raise and must not be reported as a problem. A
    file that IS there and cannot be parsed is a different thing, and the
    summary says so rather than claiming nothing was published.
    """
    if path is None:
        return None, None
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        return None, None
    try:
        with open(p, encoding="utf-8") as f:
            document = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return None, f"{p.name} is present but unreadable ({type(exc).__name__})"
    if not isinstance(document, dict):
        return None, f"{p.name} is not a JSON object"
    return document, None


def load_json(path: str | Path | None) -> dict | None:
    """read_json without the problem half, for callers that cannot act on it."""
    return read_json(path)[0]


def tier_rungs(policy: dict) -> list[list[str]]:
    """The capability ladder, weakest rung first, each rung a list of peers.

    A rung is written as a bare family word, or as a list of words that rank
    identically (`[fable, mythos]` — same tier, same price, different access
    programme). Peers matter: a model whose family word the ladder does not
    know is unranked, takes no seat, and — worse — used to sit in the usage
    denominator, shrinking every ranked model's share towards zero.
    """
    rungs: list[list[str]] = []
    for rung in policy["tiers"]:
        words = [rung] if isinstance(rung, str) else list(rung)
        rungs.append([str(word).lower() for word in words])
    return rungs


def tier_words(policy: dict) -> list[str]:
    """Every family word on the ladder, flattened."""
    return [word for rung in tier_rungs(policy) for word in rung]


def rung_of(model_id: str, rungs: list[list[str]]) -> int | None:
    """The model's rung index, from the family word in its own id.

    Token match on `-`, not a substring search: a substring test would let an
    id that merely CONTAINS a family word inside a longer token claim that
    tier. Unrecognised family word -> None -> unranked.
    """
    tokens = set(str(model_id).lower().split("-"))
    for index, rung in enumerate(rungs):
        if tokens.intersection(rung):
            return index
    return None


def rung_label(rungs: list[list[str]], index: int) -> str:
    """What to call a rung in a reason: `opus`, or `fable/mythos` for peers."""
    return "/".join(rungs[index])


def alias_map(ids) -> dict[str, str]:
    """{dated snapshot id: the undated alias it pins}, for ids that both exist.

    An id of the form `<alias>-YYYYMMDD` is the same model as `<alias>` with a
    version pinned to it. Left alone the two take two arm seats and split one
    model's usage across two census keys. The collapse only happens when the
    alias is itself present in `ids` — a catalogue that publishes only dated
    ids has no alias to collapse onto, and every one of them stands on its own.
    """
    known = {i for i in ids if isinstance(i, str)}
    mapping: dict[str, str] = {}
    for model_id in sorted(known):
        match = SNAPSHOT_SUFFIX.match(model_id)
        if match and match.group("base") in known:
            mapping[model_id] = match.group("base")
    return mapping


def usage_share(counts: dict, model_id: str, weeks: list[str],
                rungs: list[list[str]], aliases: dict | None = None) -> float:
    """Percent of RANKED census usage over `weeks` that `model_id` carries.

    The denominator counts every model the census saw THAT THE LADDER CAN
    PLACE, including ones the Models API no longer lists — work done on a
    since-retired model still happened, and the question is what share of the
    fleet's real work this model did. It EXCLUDES models the ladder cannot
    place, and the census's own `other` bucket with them: an unranked model
    takes no roster seat, so leaving its usage in the denominator only pushes
    every ranked model under the entry bar (measured: a model at 60 turns a
    week computed at 5.7% against 1000 unranked turns a week).

    A dated snapshot's usage is folded onto its alias — one model, one share.
    """
    aliases = aliases or {}
    wanted = set(weeks)
    target = aliases.get(model_id, model_id)
    total = 0
    mine = 0
    for candidate, by_week in (counts or {}).items():
        if rung_of(candidate, rungs) is None:
            continue
        folded = aliases.get(candidate, candidate)
        for week, n in (by_week or {}).items():
            if week in wanted:
                total += n
                if folded == target:
                    mine += n
    return 0.0 if total == 0 else 100.0 * mine / total


def _version_key(model_id: str) -> tuple:
    """Version components compared NUMERICALLY: `-4-10` sorts above `-4-9`.

    Only the tie-break — `created_at` decides first — but on a tie it decides
    which model is "the newest in its tier", and a string compare gets that
    exactly backwards for any family that reaches a two-digit minor.

    `isdecimal()`, not `isdigit()`: `isdigit()` is True for characters (e.g.
    the superscript `²`) that `int()` then refuses with a ValueError.
    `isdecimal()` is exactly the set `int()` accepts.
    """
    parts = []
    for token in str(model_id).split("-"):
        parts.append((1, int(token), "") if token.isdecimal() else (0, 0, token))
    return tuple(parts)


def _rank(model: dict, rungs: list[list[str]]) -> tuple:
    """Capability sort key: rung first, then newest, then version."""
    created = parse_ts(model.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
    return (rung_of(model["id"], rungs), created, _version_key(model["id"]))


def _clean_models(models_doc: dict, warn) -> list[dict]:
    """Model entries that are dicts with a string `id`. Everything else named.

    The Models API is trusted; the FILE is not — it is written by another job
    and read off a public branch, and a `models` list holding a string or an
    entry with no id used to raise a TypeError three frames down.
    """
    entries = (models_doc or {}).get("models")
    if not isinstance(entries, list):
        warn("models document has no `models` list; treating the catalogue as empty")
        return []
    clean = []
    skipped = 0
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]:
            clean.append(entry)
        else:
            skipped += 1
    if skipped:
        warn(f"models document: skipped {skipped} entry/entries without a string `id`")
    return clean


def _clean_counts(counts, warn) -> dict:
    """{model: {week: int}}, coerced. Nothing that fails coercion is counted.

    No offending VALUE is ever quoted back: the census is public, and an old
    census on the branch predates the key allowlist that keeps it that way.
    """
    if counts is None:
        return {}
    if not isinstance(counts, dict):
        warn("census `counts` is not an object; treating the census as empty")
        return {}
    cleaned: dict[str, dict[str, int]] = {}
    bad_rows = 0
    bad_cells = 0
    for model_id, by_week in counts.items():
        if not isinstance(model_id, str) or not isinstance(by_week, dict):
            bad_rows += 1
            continue
        for week, n in by_week.items():
            if not isinstance(week, str):
                bad_cells += 1
                continue
            # `int(float('inf'))` raises OverflowError, not TypeError or
            # ValueError — an uncaught OverflowError used to exit this
            # script by traceback on a census cell of `1e400` (which JSON
            # overflows to inf) or the literal `Infinity`/`NaN`, both of
            # which Python's `json` module accepts by default. Rejecting
            # non-finite floats before `int()` catches it without relying on
            # the exception ever firing.
            if isinstance(n, float) and not math.isfinite(n):
                bad_cells += 1
                continue
            try:
                value = int(n)
            except (TypeError, ValueError, OverflowError):
                bad_cells += 1
                continue
            # A negative count is not a real turn tally — accepting it at
            # face value let it sum straight into usage_share's totals
            # (a `-99` cell once yielded a 'carries 10000.0%' reason, and a
            # cancelling +/- pair could zero a census's only ranked usage
            # while `_census_verdict` still read it as usable).
            if value < 0:
                bad_cells += 1
                continue
            cleaned.setdefault(model_id, {})[week] = value
    if bad_rows:
        warn(f"census `counts`: skipped {bad_rows} row(s) that are not "
             f"model -> {{week: count}}")
    if bad_cells:
        warn(f"census `counts`: skipped {bad_cells} weekly count(s) that are "
             f"not a number")
    return cleaned


def _clean_previous_arms(previous, warn) -> list[str]:
    """The previous roster's arm ids. A malformed entry is skipped, not fatal."""
    if previous is None:
        return []
    entries = previous.get("arms") if isinstance(previous, dict) else None
    if entries is None:
        return []
    if not isinstance(entries, list):
        warn("previous roster: `arms` is not a list; comparing against nothing")
        return []
    ids = []
    skipped = 0
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]:
            if entry["id"] not in ids:
                ids.append(entry["id"])
        else:
            skipped += 1
    if skipped:
        warn(f"previous roster: skipped {skipped} `arms` entry/entries that are "
             f"not an object with a string `id`")
    return ids


def _in_window_totals(counts: dict, weeks: set[str],
                      rungs: list[list[str]]) -> tuple[int, int]:
    """(raw_total, ranked_total) of census usage over `weeks`.

    `ranked_total` mirrors `usage_share`'s own denominator — it excludes
    `other` and every id the tier ladder cannot place, the same as a roster
    seat would. Computed once and handed to `_census_verdict`, so its
    "is there usage evidence" check agrees with the number every arm's share
    is actually divided by, rather than reading raw counts that can be
    nonzero while the ranked denominator is zero (a census entirely routed
    through Bedrock/Vertex/a proxy lands every count under `other`).
    """
    raw_total = 0
    ranked_total = 0
    for candidate, by_week in (counts or {}).items():
        ranked = rung_of(candidate, rungs) is not None
        for week, n in (by_week or {}).items():
            if week in weeks:
                raw_total += n
                if ranked:
                    ranked_total += n
    return raw_total, ranked_total


#: `_census_verdict`'s machine-readable half. Reasons are for humans; this is
#: for callers deciding what else follows (e.g. whether `census_at` is
#: recorded), so they do not have to reconstruct it from a string prefix.
CENSUS_UNREADABLE = "unreadable"
CENSUS_ABSENT = "absent"
CENSUS_FUTURE = "future"
CENSUS_STALE = "stale"
CENSUS_EMPTY = "empty"
CENSUS_UNRANKED = "unranked"
CENSUS_FRESH = "fresh"

#: Verdicts whose census WAS published and current enough to be worth citing
#: as provenance, even though it is not usable evidence — see `CENSUS_EMPTY`
#: and `CENSUS_UNRANKED` below. `CENSUS_UNREADABLE` is deliberately absent:
#: a file that failed to parse has no `generated_at` to cite.
CENSUS_PUBLISHED_CODES = (CENSUS_EMPTY, CENSUS_UNRANKED, CENSUS_FRESH)


def _census_verdict(census_doc, raw_total: int, ranked_total: int, policy, now,
                    census_problem: str | None = None):
    """(usable, note, code) — is there usage evidence for the window, and why not.

    Six ways to have none, and they are NOT the same fact: a file that is
    present but failed to parse (distinct from nothing being published at
    all — `read_json` already tells the two apart, but `main()` used to
    collapse them by discarding the problem and passing `census_doc=None`
    either way), nothing published, a timestamp in the future (clock skew or
    a hand edit — every week then falls outside the window while the age
    check reads as fresh), a census older than the freshness window, a
    census that is present and current and simply holds nothing for these
    weeks, and a census that holds usage but none of it is usage the tier
    ladder can rank (every count fell under `other` or an unranked id). Each
    says so in its own words, because "fell back to newest per tier" without
    the cause is a roster nobody can debug.
    """
    if census_problem:
        # `read_json`'s message already names the file and the exception
        # class only — never file content — so it is safe to surface
        # verbatim as far down as an arm's own reason.
        return False, census_problem, CENSUS_UNREADABLE
    census_at = parse_ts((census_doc or {}).get("generated_at"))
    if census_doc is None or census_at is None:
        return False, "no fresh census (none published)", CENSUS_ABSENT
    if census_at > now:
        return False, ("no fresh census (its generated_at is in the future, so "
                       "every week of usage falls outside the window — clock "
                       "skew or a hand edit)"), CENSUS_FUTURE
    age = (now - census_at).days
    if now - census_at > timedelta(days=policy["census_max_age_days"]):
        return False, (f"no fresh census (last published {age} days ago, over the "
                       f"{policy['census_max_age_days']}-day window)"), CENSUS_STALE
    if raw_total == 0:
        return False, ("census published but empty over the window (no usage "
                       "recorded for any model in these weeks)"), CENSUS_EMPTY
    if ranked_total == 0:
        return False, ("census published but holds no usage this policy can "
                       "rank over the window (every count in these weeks is "
                       "`other` or an id the tier ladder cannot place)"), \
            CENSUS_UNRANKED
    return True, "", CENSUS_FRESH


def compute_roster(models_doc: dict, census_doc: dict | None, policy: dict,
                   previous: dict | None, now: datetime,
                   admin_doc: dict | None = None, warn=None,
                   census_problem: str | None = None,
                   previous_problem: str | None = None) -> dict:
    warn = warn or _stderr
    rungs = tier_rungs(policy)

    entries = _clean_models(models_doc, warn)
    api_ids = [m["id"] for m in entries]
    ranked = [m for m in entries if rung_of(m["id"], rungs) is not None]
    unranked = [{"id": m["id"],
                 "reason": ("no family word from the tier ladder appears in its "
                            "id, so it cannot be ranked and takes no roster seat")}
                for m in entries if rung_of(m["id"], rungs) is None]
    unranked_ids = {u["id"] for u in unranked}

    counts = _clean_counts((census_doc or {}).get("counts"), warn)
    # Two alias maps, deliberately. SEATING may only collapse a snapshot onto
    # an alias the catalogue actually offers — an alias that exists solely as
    # an old census key is not a model anyone can run. USAGE folds over both,
    # so a seat keeps the usage recorded under either spelling of itself.
    seat_aliases = alias_map(api_ids)
    aliases = alias_map(api_ids + list(counts))
    snapshots = {m["id"]: seat_aliases[m["id"]]
                 for m in ranked if m["id"] in seat_aliases}

    available = [m for m in ranked if m["id"] not in snapshots]
    available.sort(key=lambda m: _rank(m, rungs))

    enter_weeks = window_weeks(now, policy["arm_enter_window_weeks"])
    exit_weeks = window_weeks(now, policy["arm_exit_window_weeks"])
    window_union = set(enter_weeks) | set(exit_weeks)
    raw_total, ranked_total = _in_window_totals(counts, window_union, rungs)
    usable, stale_note, census_code = _census_verdict(
        census_doc, raw_total, ranked_total, policy, now,
        census_problem=census_problem)
    # Provenance: the timestamp of the census this roster actually read. A
    # census that was published and simply held nothing usable for these
    # weeks HAS a timestamp worth recording — dropping it made "we read a
    # census and it said nothing" indistinguishable from "nobody published
    # one". A stale or future-dated census was not read, so it records
    # nothing. Branches on the verdict CODE, not on the reason string's
    # prefix — a human-facing sentence is not a stable thing to match on.
    census_at_published = ((census_doc or {}).get("generated_at")
                           if census_code in CENSUS_PUBLISHED_CODES
                           else None)
    previous_arms = _clean_previous_arms(previous, warn)

    newest_by_rung: dict[int, str] = {}
    for model in available:  # sorted weakest-first, oldest-first within a rung
        newest_by_rung[rung_of(model["id"], rungs)] = model["id"]

    # --- who is an arm, and why ------------------------------------------
    arms: list[dict] = []
    excluded: list[dict] = []
    for model in available:
        model_id = model["id"]
        rung = rung_of(model_id, rungs)
        label = rung_label(rungs, rung)
        raw_created = model.get("created_at")
        created = parse_ts(raw_created)
        age_days = (now - created).days if created else None
        is_newest = newest_by_rung.get(rung) == model_id
        old_enough = age_days is not None and age_days >= policy["cooling_off_days"]

        reason = None
        if usable:
            share = usage_share(counts, model_id, enter_weeks, rungs, aliases)
            if share >= policy["arm_enter_usage_pct"]:
                reason = (f"carries {share:.1f}% of census usage over the last "
                          f"{policy['arm_enter_window_weeks']} weeks "
                          f"(at or above the {policy['arm_enter_usage_pct']}% entry bar)")
        if reason is None and is_newest and old_enough:
            newest_words = (f"newest model in the {label} tier, {age_days} days old "
                            f"(past the {policy['cooling_off_days']}-day cooling-off)")
            reason = (newest_words if usable
                      else f"{stale_note}; fell back to newest per tier — {newest_words}")
        if reason is None and model_id in previous_arms:
            if usable:
                held = usage_share(counts, model_id, exit_weeks, rungs, aliases)
                if held >= policy["arm_exit_usage_pct"]:
                    reason = (f"held over from the previous roster: still "
                              f"{held:.1f}% of census usage over the last "
                              f"{policy['arm_exit_window_weeks']} weeks (at or above "
                              f"the {policy['arm_exit_usage_pct']}% exit bar)")
            else:
                # Staleness is not evidence of disuse. Retiring a previous arm
                # because nobody published a census retires it on NO evidence
                # — measured: an arm at 33% usage dropped when the census was
                # 21 days old. The only retirement a stale census supports is
                # a model that left the Models API, handled below.
                reason = (f"held over from the previous roster: {stale_note}, so "
                          f"there is no evidence to retire it")
        if reason:
            arms.append({"id": model_id, "reason": reason})
        elif created is None:
            why = "absent" if not raw_created else "unparseable"
            excluded.append({"id": model_id, "reason": (
                f"excluded from the arm set: its created_at is {why}, so the "
                f"{policy['cooling_off_days']}-day cooling-off cannot be checked")})
        elif is_newest and not old_enough:
            excluded.append({"id": model_id, "reason": (
                f"excluded from the arm set: newest in the {label} tier but only "
                f"{age_days} days old, inside the {policy['cooling_off_days']}-day "
                f"cooling-off")})

    for snapshot_id in sorted(snapshots):
        excluded.append({"id": snapshot_id, "reason": (
            f"dated snapshot of `{snapshots[snapshot_id]}`; collapsed onto that "
            f"alias for ranking, seating and usage, so it takes no seat of its own")})

    arm_ids = {a["id"] for a in arms}

    # --- judge -------------------------------------------------------------
    # Preference order, and the last rung is not decorative: with no census the
    # arm set is "newest per tier", which on a catalogue holding one current
    # model per tier is EVERY available model — the state of the very first run,
    # before any census has been published. Emitting a null judge there would
    # ship a roster with a hole in it, so the fallback names the strongest model
    # available and says out loud that it is also an arm, leaving the caller to
    # decide rather than leaving it to find out. `is_arm` carries that in a
    # field as well as in words: run_eval.py refuses such a judge for an
    # unpinned fixture, and it cannot read prose.
    strongest_arm_rung = max((rung_of(a, rungs) for a in arm_ids), default=None)
    non_arms = [m for m in available if m["id"] not in arm_ids]
    above = ([m for m in non_arms if rung_of(m["id"], rungs) > strongest_arm_rung]
             if strongest_arm_rung is not None else [])

    if above:
        pick = above[-1]
        judge = {"id": pick["id"],
                 "reason": (f"most capable available model at least one tier above "
                            f"the strongest arm model "
                            f"({rung_label(rungs, rung_of(pick['id'], rungs))} "
                            f"over {rung_label(rungs, strongest_arm_rung)}), and "
                            f"not itself an arm")}
    elif non_arms:
        pick = non_arms[-1]
        arm_tier_words = (f" — nothing available sits above the strongest arm's "
                          f"{rung_label(rungs, strongest_arm_rung)} tier"
                          if strongest_arm_rung is not None else "")
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
    judge["is_arm"] = judge["id"] in arm_ids

    # --- preflight ---------------------------------------------------------
    # Cheapest = the lowest tier the API still returns. Within it, prefer a
    # model that has cleared the cooling-off: a day-old cheapest-tier model
    # is exactly the kind an old or narrowly-scoped bearer may not yet be
    # entitled to invoke, and eval.yml's preflight step this feeds is FATAL
    # to the whole job — it used to canary on "newest in tier" with no
    # regard for age at all. Falls back to the newest regardless of age only
    # when nothing in the tier has cleared cooling-off yet: there being no
    # older model in the tier to prefer over it.
    cheapest = None
    cheapest_reason = None
    if available:
        lowest_rung = rung_of(available[0]["id"], rungs)
        rung_models = [m for m in available if rung_of(m["id"], rungs) == lowest_rung]
        label = rung_label(rungs, lowest_rung)
        cooled = []
        for m in rung_models:  # ascending order -> newest last
            created = parse_ts(m.get("created_at"))
            age_days = (now - created).days if created else None
            if age_days is not None and age_days >= policy["cooling_off_days"]:
                cooled.append(m)
        if cooled:
            cheapest = cooled[-1]
            cheapest_reason = (f"newest model in the {label} tier that is past the "
                               f"{policy['cooling_off_days']}-day cooling-off: the "
                               f"lowest tier the Models API still returns, and this "
                               f"is its cheapest safely-invocable pick")
        else:
            cheapest = rung_models[-1]
            cheapest_reason = (f"newest model in the {label} tier: the lowest tier "
                               f"the Models API still returns (still within the "
                               f"{policy['cooling_off_days']}-day cooling-off — "
                               f"nothing older in this tier has cleared it yet)")
    preflight = ({"id": cheapest["id"], "reason": cheapest_reason}
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
            if model_id not in api_ids:
                why = "no longer returned by the Models API"
            elif model_id in unranked_ids:
                why = ("still returned by the Models API, but no family word from "
                       "the tier ladder appears in its id, so it can no longer be "
                       "ranked or seated")
            elif model_id in snapshots:
                why = (f"collapsed onto its undated alias `{snapshots[model_id]}`, "
                       f"which holds the seat")
            elif not usable:
                why = (f"{stale_note}; the fallback roster is newest-per-tier and "
                       f"this model is not the newest in its tier")
            else:
                held = usage_share(counts, model_id, exit_weeks, rungs, aliases)
                why = (f"below the {policy['arm_exit_usage_pct']}% exit bar for the last "
                       f"{policy['arm_exit_window_weeks']} weeks ({held:.1f}%)")
            retired.append({"id": model_id, "reason": why})

    # Three states, not two: `previous is not None` alone collapses "the
    # previous roster was there but unreadable" into the same false as
    # "there is no previous roster (first run)" — the exact gap that let the
    # published JSON and the rendered Markdown disagree about what happened,
    # since main() derived the Markdown's state from `previous_problem`
    # directly while the JSON only ever recorded the boolean. Publishing the
    # state itself means every caller reads the same fact.
    previous_state = ("unavailable" if previous_problem
                      else "compared" if previous is not None else "none")

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "models_api_at": (models_doc or {}).get("fetched_at"),
            "census_at": census_at_published,
            "admin_report_at": (admin_doc or {}).get("fetched_at") if admin_doc else None,
        },
        "arms": arms,
        "judge": judge,
        "preflight": preflight,
        "unranked": unranked,
        "excluded": excluded,
        "compared_to_previous": previous_state == "compared",
        "previous_state": previous_state,
        "retired_since_last": retired,
        "added_since_last": added,
    }


def render_summary(roster: dict, previous_state: str = "auto") -> str:
    """Markdown for $GITHUB_STEP_SUMMARY. A roster change leads.

    `previous_state` is "auto" (read the roster's own `previous_state`
    field — this is what every real caller does now that compute_roster
    fills it in, so the JSON and this Markdown cannot disagree) or an
    explicit override ("unavailable", "compared", "none") for exercising one
    state in isolation. The three cases are NOT interchangeable: printing
    "No change to the arm set since the last run" on a first run, or when
    the comparison never happened, is a claim about a comparison nobody made.
    """
    lines = ["### Model roster", ""]
    changed = roster["added_since_last"] or roster["retired_since_last"]
    if previous_state == "auto":
        previous_state = (roster.get("previous_state") or
                          ("compared" if roster.get("compared_to_previous")
                           else "none"))
    if previous_state == "unavailable":
        lines += ["**Roster inputs unavailable** — the previous roster could not "
                  "be read this run, so nothing was compared against it.", ""]
    elif changed:
        lines.append("**Roster changed since the last run.**")
        for entry in roster["added_since_last"]:
            lines.append(f"- added `{entry['id']}` — {entry['reason']}")
        for entry in roster["retired_since_last"]:
            lines.append(f"- retired `{entry['id']}` — {entry['reason']}")
        lines.append("")
    elif previous_state == "compared":
        lines += ["No change to the arm set since the last run.", ""]
    else:
        lines += ["First published roster here — no previous roster to compare "
                  "against.", ""]

    lines += ["| Role | Model | Why |", "| --- | --- | --- |"]
    for arm in roster["arms"]:
        lines.append(f"| arm | `{arm['id']}` | {arm['reason']} |")
    for role in ("judge", "preflight"):
        entry = roster[role]
        lines.append(f"| {role} | `{entry['id']}` | {entry['reason']} |")
    for role, entries in (("unranked", roster.get("unranked") or []),
                          ("excluded", roster.get("excluded") or [])):
        for entry in entries:
            lines.append(f"| {role} | `{entry['id']}` | {entry['reason']} |")
    if roster["judge"].get("is_arm"):
        lines += ["", "> **The judge is also an arm this run.** Do not run it as "
                      "the arm and the judge of the same eval."]
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

    models_doc, problem = read_json(args.models)
    if models_doc is None:
        print(problem or f"no models document at {args.models}", file=sys.stderr)
        return 1

    census_doc, census_problem = read_json(args.census)
    if census_problem:
        _stderr(census_problem)
    previous_doc, previous_problem = read_json(args.previous)
    if previous_problem:
        _stderr(previous_problem)

    roster = compute_roster(
        models_doc=models_doc,
        census_doc=census_doc,
        policy=load_policy(args.policy),
        previous=previous_doc,
        now=datetime.now(timezone.utc),
        admin_doc=load_json(args.admin_report),
        census_problem=census_problem,
        previous_problem=previous_problem,
    )

    if not roster["arms"]:
        # A roster with no arms is not a roster. It used to exit 0 and publish
        # an empty arm set — a run that silently evaluated nothing, which is
        # exactly the "went stale without anyone noticing" failure #67 exists
        # to remove. Nothing is written, so the last good roster stands.
        print("refusing to publish a roster with no arms: every ranked model is "
              "excluded (see the excluded/unranked reasons above)", file=sys.stderr)
        for entry in roster["excluded"] + roster["unranked"]:
            print(f"  {entry['id']}: {entry['reason']}", file=sys.stderr)
        return 3

    # Written via a temp file in the same directory and renamed: a partial
    # roster is worse than no roster, and the caller's "did the file appear?"
    # is the only signal the commit step has.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    staged = args.out.with_name(args.out.name + ".partial")
    with open(staged, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2)
        f.write("\n")
    staged.replace(args.out)

    print(render_summary(roster))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
