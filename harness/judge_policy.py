"""Which model judges an arm (#371 items 3 and 4, ADR 0013).

For an arm model in tier T the judge is the newest roster ARM in the lowest
tier above T; when no roster arm sits above T it is the roster's own `judge`.
A judge is never the model it grades and never in that model's tier: when the
rule cannot give one, there is no judge and the caller fails closed.

Derived at run time from the committed roster. Nothing here computes, renders
or admits a roster, and the roster's schema is unchanged (ADRs 0001 to 0004).
A model's tier is `harness/roster.py`'s reading of its id against the ladder
in `evals/roster-policy.yml`; this module parses no model name itself.

The committed roster carries no `created_at`, so "newest" within a tier is
`roster._version_key`, the id's version compared numerically: the tie-break
`roster.py` ranks by after `created_at`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

import roster

#: The tier ladder (`tiers:`), committed and pull-request-only like the roster.
TIER_POLICY = Path(__file__).resolve().parent.parent / "evals" / "roster-policy.yml"

RULE_TIER_ABOVE = "tier-above-arm"
RULE_ROSTER_JUDGE = "roster-judge"
RULE_FIXTURE_PIN = "fixture-pin"


def read_rungs() -> tuple[list[list[str]] | None, str | None]:
    """(the ladder, weakest rung first, or None; a problem naming the file by
    its basename, or None). Never raises."""
    path = Path(TIER_POLICY)
    try:
        policy = roster.load_policy(path)
        roster.validate_policy(policy)
        return roster.tier_rungs(policy), None
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError,
            RecursionError) as exc:
        return None, (f"the tier ladder at {path.name} is unreadable "
                      f"({type(exc).__name__})")


def tier_label(model: str | None, rungs: list[list[str]] | None) -> str | None:
    """The model's tier as a summary records it (`opus`, `fable/mythos`), or
    None when there is no ladder or the ladder cannot place the model."""
    index = roster.rung_of(model, rungs) if model and rungs else None
    return None if index is None else roster.rung_label(rungs, index)


def selection(model: str, rule: str, arm_model: str | None,
              rungs: list[list[str]] | None) -> dict:
    """A summary's `judge_selection` block."""
    return {"model": model, "rule": rule,
            "arm_tier": tier_label(arm_model, rungs),
            "judge_tier": tier_label(model, rungs)}


def judge_for_arm(arm_model: str, arm_ids: list[str], roster_judge: str | None,
                  rungs: list[list[str]]) -> tuple[dict | None, str | None]:
    """(the `judge_selection` for this arm, or None; why there is none).

    `arm_ids` are the roster's arms and `roster_judge` its `judge` id. The arm
    model itself need not be one of them: `--model` and a fixture's `model:`
    pin name an arm too, and the rule reads that model's own tier.
    """
    tier = roster.rung_of(arm_model, rungs)
    if tier is None:
        return None, (f"the arm model `{arm_model}` has no tier on the "
                      "ladder, so no judge is known to sit above it")
    label = roster.rung_label(rungs, tier)
    above = [(rung, arm) for rung, arm in
             ((roster.rung_of(arm, rungs), arm) for arm in arm_ids)
             if rung is not None and rung > tier]
    if above:
        lowest = min(rung for rung, _ in above)
        newest = max((arm for rung, arm in above if rung == lowest),
                     key=roster._version_key)
        return selection(newest, RULE_TIER_ABOVE, arm_model, rungs), None
    nothing_above = f"no roster arm sits above the {label} tier of `{arm_model}`"
    if not roster_judge:
        return None, f"{nothing_above}, and the roster names no usable judge"
    if roster_judge == arm_model:
        return None, (f"{nothing_above}, and the roster's judge is that same "
                      "model; a model must not grade its own run")
    judge_tier = roster.rung_of(roster_judge, rungs)
    if judge_tier is None:
        return None, (f"{nothing_above}, and the roster's judge "
                      f"`{roster_judge}` has no tier on the ladder")
    if judge_tier <= tier:
        return None, (f"{nothing_above}, and the roster's judge "
                      f"`{roster_judge}` is in the "
                      f"{roster.rung_label(rungs, judge_tier)} tier, which is "
                      "not above it")
    return selection(roster_judge, RULE_ROSTER_JUDGE, arm_model, rungs), None
