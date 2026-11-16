#!/usr/bin/env python3
"""The rule for removing a skill nobody uses (Adam, 2026-11-12).

`evals/removal-policy.yml` holds the numbers (read by `load`, which refuses a
missing, negative or wrong-typed key); `scripts/retire_skill.py` acts on
`unused_removal`'s answer with reason `unused`. The rule is cost against
value: a skill listed in every session costs `d` description tokens of
re-read context in each, so after enough sessions with no use the skill has
cost more than one use is worth (`value_per_use_usd`).

    accrued = sum over surfaces s of exposure_s * d * R_s / P      (USD)
    N*_s    = V * P / (d * R_s)       sessions on s that alone reach V

Full numeric precision is kept; only the text a person reads is rounded.

Stdlib and `yaml`, no network; the caller supplies `now`.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import skill_usage
from timeweeks import week_monday, window_weeks

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "evals" / "removal-policy.yml"
SURFACES = (skill_usage.SURFACE_LOCAL, skill_usage.SURFACE_CLOUD)
KEYS = ("value_per_use_usd", "prefix_tokens", "reread_usd_per_session", "floor_weeks",
        "local_removal", "first_use_weeks")


class PolicyError(ValueError):
    """A removal policy that is missing, unreadable or invalid."""


def _positive_number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def parse(text: str) -> dict:
    """The policy in `text`, checked; PolicyError naming the key otherwise.
    Every key is required and an unknown one is refused. Numbers must be
    positive (a zero re-read cost would make the threshold infinite)."""
    try:
        doc = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError):
        raise PolicyError("the removal policy is not valid YAML") from None
    if not isinstance(doc, dict):
        raise PolicyError("the removal policy must be a mapping")
    missing = [k for k in KEYS if k not in doc]
    if missing:
        raise PolicyError(f"the removal policy lacks {', '.join(missing)}")
    extra = sorted(str(k) for k in doc if k not in KEYS)
    if extra:
        raise PolicyError(f"the removal policy has unknown key(s) {', '.join(extra)}")
    if not _positive_number(doc["value_per_use_usd"]):
        raise PolicyError("value_per_use_usd must be a positive number")
    if type(doc["prefix_tokens"]) is not int or doc["prefix_tokens"] <= 0:
        raise PolicyError("prefix_tokens must be a positive integer")
    reread = doc["reread_usd_per_session"]
    if not isinstance(reread, dict) or set(reread) != set(SURFACES):
        raise PolicyError("reread_usd_per_session must give exactly cloud and local")
    if not all(_positive_number(reread[s]) for s in SURFACES):
        raise PolicyError("reread_usd_per_session values must be positive numbers")
    if type(doc["floor_weeks"]) is not int or doc["floor_weeks"] < 1:
        raise PolicyError("floor_weeks must be an integer of at least 1")
    if not isinstance(doc["local_removal"], bool):
        raise PolicyError("local_removal must be true or false")
    if type(doc["first_use_weeks"]) is not int or doc["first_use_weeks"] < 1:
        raise PolicyError("first_use_weeks must be an integer of at least 1")
    return {"value_per_use_usd": doc["value_per_use_usd"], "prefix_tokens": doc["prefix_tokens"],
            "reread_usd_per_session": {s: reread[s] for s in SURFACES},
            "floor_weeks": doc["floor_weeks"], "local_removal": doc["local_removal"],
            "first_use_weeks": doc["first_use_weeks"]}


def load(path: Path | None = None) -> dict:
    """`parse` of the file at `path` (default evals/removal-policy.yml)."""
    path = Path(path) if path is not None else DEFAULT_POLICY
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise PolicyError(f"the removal policy {path.name} could not be read") from None
    return parse(text)


def description_tokens(skill_md_text: str) -> int:
    """d: ceil(bytes / 4) of the frontmatter's `name` and `description`
    values (UTF-8 bytes, the two values together). The frontmatter is the
    YAML between the first two `---` lines, parsed with `yaml`; PolicyError
    when it is missing, unreadable, or has no text `name` or `description`."""
    lines = skill_md_text.split("\n") if isinstance(skill_md_text, str) else []
    if not lines or lines[0].strip() != "---":
        raise PolicyError("the skill has no frontmatter")
    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        raise PolicyError("the skill's frontmatter is not closed")
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
    except (yaml.YAMLError, ValueError):
        raise PolicyError("the skill's frontmatter is not valid YAML") from None
    if not isinstance(meta, dict):
        raise PolicyError("the skill's frontmatter is not a mapping")
    name, description = meta.get("name"), meta.get("description")
    if not isinstance(name, str) or not isinstance(description, str) or not description:
        raise PolicyError("the skill's frontmatter has no text name and description")
    return math.ceil((len(name.encode("utf-8")) + len(description.encode("utf-8"))) / 4)


def threshold(policy: dict, d: int, surface: str) -> float:
    """N* = V * P / (d * R_surface): the sessions on `surface` alone whose
    re-read cost of a `d`-token description equals the value of one use."""
    if surface not in SURFACES:
        raise PolicyError(f"{surface} is not a surface")
    if type(d) is not int or d <= 0:
        raise PolicyError("d must be a positive integer")
    return (policy["value_per_use_usd"] * policy["prefix_tokens"]
            / (d * policy["reread_usd_per_session"][surface]))


def accrued_usd(policy: dict, d: int, exposure: dict) -> float:
    """sum over surfaces of exposure * d * R / P: what the description has
    cost, in USD of context re-read."""
    return sum(n * d * policy["reread_usd_per_session"][s] / policy["prefix_tokens"]
               for s, n in exposure.items())


def floor_start(now: datetime, floor_weeks: int) -> datetime:
    """The Monday (UTC) that starts the `floor_weeks`-week window ending with
    `now`'s week."""
    monday = week_monday(window_weeks(now, floor_weeks)[-1])
    return datetime.fromisoformat(monday).replace(tzinfo=timezone.utc)


def unused_removal(policy: dict, doc, skill: str, surfaces: tuple, d: int, now: datetime,
                   exempt) -> dict:
    """Whether `skill` should be removed as unused, with the figures behind it.

    `remove` is True only when ALL hold: the skill is not in `exempt`
    (evals/usage-unknown.yml); `surfaces` include cloud, or the policy's
    `local_removal` is true; the census `doc` is fresh and ends where the
    window does (its `generated_at` and every reached surface's source `to`
    within 1 day of `now`, `census_current`); the census tracks the skill by
    name (`is_tracked`); the skill had no use over the policy's `floor_weeks`
    weeks; every surface it reaches is counted back to the Monday starting
    that window (`counted_from`); the exposure of EVERY surface it reaches is
    known (cloud is unknown unless its records carry the install and listing
    fields, so a cloud-reaching skill is not removed on such a census); and
    the accrued description cost (`accrued_usd`) is at least
    `value_per_use_usd`. A removal is irreversible, unlike the eval pause
    (`skill_usage.has_recorded_use`, no exposure minimum, 2026-11-13). The dict also carries `uses` (None when the census
    is unknown), `exposure` and `threshold` (N*) per surface, `d`,
    `accrued_usd`, `value_usd`, `floor_weeks`, `window_start`, `surfaces`,
    `exempt`, `known` (a fresh census was read) and `why`.
    """
    weeks = policy["floor_weeks"]
    start = floor_start(now, weeks)
    surfaces = tuple(s for s in SURFACES if s in surfaces)
    out = {"skill": skill, "surfaces": list(surfaces), "d": d, "floor_weeks": weeks,
           "window_start": start.date().isoformat(), "value_usd": policy["value_per_use_usd"],
           "exempt": skill in exempt, "known": False, "uses": None, "exposure": {},
           "threshold": {s: threshold(policy, d, s) for s in surfaces}, "accrued_usd": None,
           "remove": False}

    def refuse(why: str) -> dict:
        return {**out, "why": why}

    fresh = doc is not None and skill_usage.is_fresh(doc, now)
    if fresh:
        out["uses"] = skill_usage.weight(doc, skill, now, weeks)
        out["exposure"] = skill_usage.exposure_by_surface(doc, now, surfaces, weeks) or {}
        out["accrued_usd"] = accrued_usd(
            policy, d, {s: n for s, n in out["exposure"].items() if n is not None})
        out["known"] = out["uses"] is not None
    if out["exempt"]:
        return refuse("it is listed in evals/usage-unknown.yml, so its use is not read "
                      "from the census")
    if not surfaces:
        return refuse("it reaches no surface")
    if skill_usage.SURFACE_CLOUD not in surfaces and not policy["local_removal"]:
        return refuse("it reaches only the local surface, and local removal is off "
                      "(a local-only skill is paused, never removed on usage)")
    if not out["known"]:
        return refuse("there is no fresh usage census")
    if out["uses"] > 0:
        return refuse(f"it had {out['uses']} use(s) in the last {weeks} weeks")
    if not skill_usage.is_tracked(doc, skill):
        return refuse("the census does not track it by name, so its uses would be "
                      "counted under other and read as zero")
    if not skill_usage.census_current(doc, surfaces, now):
        return refuse("the census does not end within 1 day of the date the floor "
                      "window ends")
    unknown = [s for s in surfaces if out["exposure"].get(s) is None]
    if unknown:
        return refuse(f"its exposure on the {', '.join(unknown)} surface is unknown (the "
                      "records do not show the registry installed and a full listing)")
    for surface in surfaces:
        counted = skill_usage.counted_from(doc, surface)
        if counted is None or counted > start:
            return refuse(f"the census does not count the {surface} surface back to "
                          f"{out['window_start']}, the start of the {weeks}-week floor")
    if out["accrued_usd"] < policy["value_per_use_usd"]:
        return refuse(f"its description has cost ${out['accrued_usd']:.2f} of context, "
                      f"under the ${policy['value_per_use_usd']:g} one use is worth")
    return {**out, "remove": True,
            "why": f"no use in {weeks} weeks, and its description has cost "
                   f"${out['accrued_usd']:.2f} of context, at least the "
                   f"${policy['value_per_use_usd']:g} one use is worth"}


def _monday(moment: datetime) -> datetime:
    """Midnight UTC of the Monday starting `moment`'s ISO week."""
    day = moment.astimezone(timezone.utc)
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc) - timedelta(
        days=day.weekday())


def unused_deadline(policy: dict, doc, skill: str, surfaces: tuple, d: int, now: datetime,
                    exempt) -> dict:
    """The last day a use of `skill` still keeps `unused_removal` from removing it.

    Returns {"state", "use_by", "removable_from", "last_use_week",
    "projected_usd", "why"}. `state`, first match:

    * `exempt`: listed in evals/usage-unknown.yml, never removed for use.
    * `local-only`: reaches no cloud surface and `local_removal` is false.
    * `unknown`: no fresh census, the census does not track the skill by name,
      a reached surface's exposure is unknown (cloud without
      `LISTING_RECORDED`) or has no `counted_from`, or a reached surface has
      no counted complete week to set a pace from.
    * `due`: `unused_removal` would remove it now.
    * `date`: the first week W (from `now`'s) at whose start the rule would
      hold, assuming no further use: (a) no use (`skill_usage.weight`'s rows)
      in the `floor_weeks` ISO weeks ending with W; (b) every reached
      surface's `counted_from` on or before the Monday starting that window;
      (c) the projected accrued cost over the window at least
      `value_per_use_usd`. A window week before `now`'s uses its actual
      full-listing exposure (`skill_usage.listing_by_week`, the rows
      `exposure_by_surface` counts). The census's data ends at the earliest
      `to` among the reached surfaces' sources and `generated_at`; that
      week, `now`'s week and every later one are projected: each surface at
      the larger of its pace and what the week has shown so far scaled up to
      a whole week (by the share of the week before the data ends), where the
      pace is its mean weekly full-listing sessions over its counted complete
      weeks, among the `floor_weeks` weeks before `now`'s, that end before
      the data does. Week W is counted whole, so the date errs early, never
      late. `removable_from` is W's Monday; `use_by` is the day before, less
      `skill_usage.CENSUS_MAX_AGE`, the age of census a removal may read, so
      a use on `use_by` is in the census a removal reads (ISO dates; a
      `use_by` before `now` means the skill can be removed this week).
    * `not-at-pace`: once W's whole window lies in projected weeks (and past
      both the use and coverage constraints) the accrual no longer changes,
      so a steady-state accrual under `value_per_use_usd` never reaches it:
      no date. The search is therefore bounded.

    `last_use_week` is the Monday of the latest census week with a use (None
    when the census shows none). `projected_usd` is the projected accrual at
    `removable_from`, the actual accrual for `due`, the steady state
    (`floor_weeks` weeks at the pace) for `not-at-pace`, else None. Full precision; `why` is short and names no
    figure beyond the policy's own.
    """
    out = {"state": "unknown", "use_by": None, "removable_from": None,
           "last_use_week": None, "projected_usd": None}

    def answer(state: str, why: str, **fields) -> dict:
        return {**out, **fields, "state": state, "why": why}

    reached = tuple(s for s in SURFACES if s in surfaces)
    if skill in exempt:
        return answer("exempt", "listed in evals/usage-unknown.yml")
    if not reached:
        return answer("unknown", "reaches no surface")
    if skill_usage.SURFACE_CLOUD not in reached and not policy["local_removal"]:
        return answer("local-only", "reaches only the local surface and local removal is off")
    if doc is None or not skill_usage.is_fresh(doc, now):
        return answer("unknown", "no fresh usage census")
    if not skill_usage.is_tracked(doc, skill):
        return answer("unknown", "the census does not track it by name")
    uses = skill_usage.uses_by_week(doc, skill)
    current = _monday(now)
    used = sorted(m for m, n in uses.items() if n > 0 and skill_usage.week_key(m) <= current)
    out["last_use_week"] = used[-1] if used else None
    listings, counted = {}, {}
    for surface in reached:
        listings[surface] = skill_usage.listing_by_week(doc, surface)
        counted[surface] = skill_usage.counted_from(doc, surface)
        if listings[surface] is None:
            return answer("unknown", f"its {surface} exposure is unknown")
        if counted[surface] is None:
            return answer("unknown", f"the census does not count the {surface} surface")

    decision = unused_removal(policy, doc, skill, reached, d, now, exempt)
    if decision["remove"]:
        return answer("due", "the removal rule holds now", removable_from=current.date().isoformat(),
                      projected_usd=decision["accrued_usd"])

    # The census's data ends at the earliest `to` of a reached surface's
    # sources (a carried cloud source can end days before `generated_at`); the
    # week holding it and every later week are projected, not actuals.
    ends = [skill_usage.parse_ts(doc.get("generated_at"))]
    ends += [skill_usage.parse_ts(source.get("to")) for source in doc.get("sources") or []
             if isinstance(source, dict) and source.get("surface") in reached]
    if any(end is None for end in ends):
        return answer("unknown", "the census does not say where its data ends")
    data_end = min(ends)
    projected_from = min(current, _monday(data_end))

    weeks, value = policy["floor_weeks"], policy["value_per_use_usd"]
    rate = {}
    for surface in reached:
        complete = [current - timedelta(weeks=k) for k in range(1, weeks + 1)]
        complete = [m for m in complete if counted[surface] <= m < projected_from]
        if not complete:
            return answer("unknown", f"no complete counted {surface} week to set a pace")
        rate[surface] = sum(listings[surface].get(m.date().isoformat(), 0)
                            for m in complete) / len(complete)

    def cost(week: datetime) -> float:
        actual = {s: listings[s].get(week.date().isoformat(), 0) for s in reached}
        if week >= projected_from:
            # A week the data ends in costs at least the pace, and at least
            # what it has shown so far scaled up to a whole week; later weeks
            # cost the pace (or more, should a row already show more).
            shown = (data_end - week) / timedelta(weeks=1) if week == projected_from else 1
            actual = {s: max(rate[s], actual[s] / shown if shown > 0 else actual[s])
                      for s in reached}
        return accrued_usd(policy, d, actual)

    last_use = (datetime.fromisoformat(out["last_use_week"]).replace(tzinfo=timezone.utc)
                if out["last_use_week"] else None)
    candidate = current
    while True:
        start = candidate - timedelta(weeks=weeks - 1)
        clear = last_use is None or last_use < start
        covered = all(counted[s] <= start for s in reached)
        if clear and covered:
            projected = sum(cost(start + timedelta(weeks=k)) for k in range(weeks))
            if projected >= value:
                last_day = candidate - timedelta(days=1) - skill_usage.CENSUS_MAX_AGE
                return answer("date", "projected at today's session pace",
                              use_by=last_day.date().isoformat(),
                              removable_from=candidate.date().isoformat(),
                              projected_usd=projected)
            if start >= current:
                # Every later window is all projected weeks at the pace,
                # which costs no more than this one: the rule is never met.
                return answer("not-at-pace", "at today's session pace its description never "
                              "costs what one use is worth",
                              projected_usd=weeks * accrued_usd(policy, d, rate))
        candidate += timedelta(weeks=1)
