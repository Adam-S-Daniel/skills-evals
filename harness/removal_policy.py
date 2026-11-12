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
from datetime import datetime, timezone
from pathlib import Path

import yaml

import skill_usage
from timeweeks import week_monday, window_weeks

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "evals" / "removal-policy.yml"
SURFACES = (skill_usage.SURFACE_LOCAL, skill_usage.SURFACE_CLOUD)
KEYS = ("value_per_use_usd", "prefix_tokens", "reread_usd_per_session", "floor_weeks",
        "local_removal")


class PolicyError(Exception):
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
    return {"value_per_use_usd": doc["value_per_use_usd"], "prefix_tokens": doc["prefix_tokens"],
            "reread_usd_per_session": {s: reread[s] for s in SURFACES},
            "floor_weeks": doc["floor_weeks"], "local_removal": doc["local_removal"]}


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
    `local_removal` is true; the census `doc` is fresh; the skill had no use
    over the policy's `floor_weeks` weeks; every surface it reaches is
    counted back to the Monday starting that window (`counted_from`); and
    the accrued description cost (`accrued_usd`) is at least
    `value_per_use_usd`. The dict also carries `uses` (None when the census
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
        out["accrued_usd"] = accrued_usd(policy, d, out["exposure"])
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
