"""The weekly allowance budget: `evals/budget.yml`, read and validated (#68).

One reader for the three layers that enforce Adam's 30% decision
(https://github.com/Adam-S-Daniel/skills-evals/issues/68#issuecomment-6097945979):
run_eval's in-run stop, scripts/allowance_guard.py's pre-fire check, and the
weekly planner (scripts/plan_scheduled_evals.py) through the guard. Every
value is a fraction of the subscription's weekly allowance, read the way the
CLI's meter reports it (`unifiedWindows.seven_day.utilization`, 0 to 1).

Strict, because a typo here is a spending decision nobody made: exactly the
four fraction keys plus `legacy_usd_per_point` (and the optional
`stop_when_session_above`), no duplicates, each fraction a finite number above
0 and at most 1 (a bool is not a number), and `per_run_cap` no larger than
`weekly_cap`. A
problem is a BudgetError whose message names the key and the rule, never a
value from the file.
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

#: The committed budget, beside the roster and the schedule.
DEFAULT_BUDGET = Path(__file__).resolve().parent.parent / "evals" / "budget.yml"
KEYS = ("weekly_cap", "per_run_cap", "per_run_overrun", "stop_when_account_above")
#: Keys a budget may leave out. `stop_when_session_above` (skills-evals#921)
#: is the same kind of stop as `stop_when_account_above`, read from the CLI's
#: 5-hour window (`unifiedWindows.five_hour.utilization`): a smaller plan's
#: sweep can use up a whole 5-hour window long before the week's meter moves
#: much. Absent, the 5-hour window is not read.
OPTIONAL_KEYS = ("stop_when_session_above",)
#: The one key that is not a fraction of the week: dollars of API-equivalent
#: spend per point, used only for calls recorded without token counts
#: (harness/allowance_points.py prices everything else from tokens by type).
#: Optional (absent, such a call is left unpriced and the run falls back to
#: the meter, as before 2026-11-03); when present, a finite number above 0
#: with no upper bound, as dollars per point. The committed budget sets it.
LEGACY_RATE = "legacy_usd_per_point"


class BudgetError(ValueError):
    """The budget file is missing, unreadable or breaks a rule."""


class _UniqueLoader(yaml.SafeLoader):
    """SafeLoader that refuses a repeated key, as plan_scheduled_evals does:
    PyYAML would otherwise keep the last one silently."""


def _mapping(loader, node):
    result = {}
    for key, value in loader.construct_pairs(node, deep=True):
        if not isinstance(key, str) or key in result:
            raise BudgetError("budget has a duplicate or non-string key")
        result[key] = value
    return result


_UniqueLoader.add_constructor("tag:yaml.org,2002:map", _mapping)


def parse_budget(text: str) -> dict:
    """The validated budget in `text`, as {key: float}, or BudgetError."""
    try:
        document = yaml.load(text, Loader=_UniqueLoader)
    except yaml.YAMLError:
        raise BudgetError("budget is not valid YAML") from None
    if not isinstance(document, dict):
        raise BudgetError("budget must be a mapping")
    unknown = sorted(set(document) - set(KEYS) - set(OPTIONAL_KEYS) - {LEGACY_RATE})
    if unknown:
        raise BudgetError(f"budget has unknown keys {unknown}")
    missing = [key for key in KEYS if key not in document]
    if missing:
        raise BudgetError(f"budget is missing keys {missing}")
    budget = {}
    for key in (*KEYS, *(key for key in OPTIONAL_KEYS if key in document)):
        value = document[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or not 0 < value <= 1:
            raise BudgetError(f"budget {key} must be a number above 0 and at most 1")
        budget[key] = float(value)
    if LEGACY_RATE in document:
        rate = document[LEGACY_RATE]
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) \
                or not math.isfinite(rate) or rate <= 0:
            raise BudgetError(f"budget {LEGACY_RATE} must be a finite number above 0")
        budget[LEGACY_RATE] = float(rate)
    if budget["per_run_cap"] > budget["weekly_cap"]:
        raise BudgetError("budget per_run_cap must not exceed weekly_cap")
    return budget


def load_budget(path: Path | None = None) -> dict:
    """`parse_budget` of the file at `path` (default: evals/budget.yml)."""
    path = Path(path) if path is not None else DEFAULT_BUDGET
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise BudgetError(f"budget file {path.name} could not be read") from None
    return parse_budget(text)


def run_reservation(budget: dict) -> float:
    """What one fire is charged before its spend is known: the per-run cap
    the in-run stop holds it to, plus the overrun past the last reading."""
    return budget["per_run_cap"] + budget["per_run_overrun"]
