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

`claude_plan` names the subscription the meter belongs to, and decides
whether the 5-hour stop applies at all (`FIVE_HOUR_WINDOW`): required on a
plan Anthropic documents a 5-hour window for, refused on one it documents
none for. `working_hours` (optional) lowers that stop while the owner works,
and for the 5 hours before, so the loop does not hand the owner a nearly
spent window when their day starts.
"""

from __future__ import annotations

import math
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
#: The subscription plan (required): it decides whether the 5-hour stop
#: applies. Not a fraction, so not in KEYS.
PLAN_KEY = "claude_plan"
#: Optional: hours the owner works, when the 5-hour stop is lower.
WORKING_HOURS = "working_hours"
#: Whether each plan has a 5-hour usage window, per Anthropic's help center
#: as read on 2026-11-20. "yes": the budget must set
#: `stop_when_session_above`; "no": it must not (nor `working_hours`);
#: "unverified": only an account not yet verified has one, so the stop is
#: optional.
#:   pro, max5x: https://support.claude.com/en/articles/11145838 ("Pro and
#:     Max plans have a five-hour session limit and a weekly limit").
#:   ultra (formerly Max 20x): https://support.claude.com/en/articles/17728952
#:     ("Verified Ultra accounts don't have a five-hour limit. If your
#:     account isn't verified yet, a temporary limit applies.").
#:   team_standard, team_premium, enterprise_seat: per-seat limits on a
#:     five-hour session and a week,
#:     https://support.claude.com/en/articles/9797557 and /9266767.
#:   enterprise_usage: https://support.claude.com/en/articles/9797531
#:     ("Usage-based Enterprise plans ... have no plan or seat-level usage
#:     limits").
FIVE_HOUR_WINDOW = {"pro": "yes", "max5x": "yes", "ultra": "unverified",
                    "team_standard": "yes", "team_premium": "yes",
                    "enterprise_seat": "yes", "enterprise_usage": "no"}
#: How long a 5-hour window lasts: a window opened this long before the
#: working day starts can still be open when it does.
SESSION_WINDOW = timedelta(hours=5)
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
WORKING_HOURS_KEYS = ("timezone", "days", "start", "end", "session_stop")
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
    """The validated budget in `text`, or BudgetError: {key: float} for the
    fractions and `legacy_usd_per_point`, the `claude_plan` string, and the
    parsed `working_hours` (`_working_hours`) when set."""
    try:
        document = yaml.load(text, Loader=_UniqueLoader)
    except yaml.YAMLError:
        raise BudgetError("budget is not valid YAML") from None
    if not isinstance(document, dict):
        raise BudgetError("budget must be a mapping")
    unknown = sorted(set(document) - set(KEYS) - set(OPTIONAL_KEYS)
                     - {LEGACY_RATE, PLAN_KEY, WORKING_HOURS})
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
    _plan(document, budget)
    return budget


def _plan(document: dict, budget: dict) -> None:
    """Check `claude_plan` against the 5-hour stop and add it, and any
    `working_hours`, to `budget`."""
    plan = document.get(PLAN_KEY)
    if plan is None:
        raise BudgetError(f"budget is missing {PLAN_KEY} (one of "
                          f"{', '.join(FIVE_HOUR_WINDOW)}): it decides whether "
                          "the 5-hour stop applies")
    if plan not in FIVE_HOUR_WINDOW:
        raise BudgetError(f"budget {PLAN_KEY} must be one of {', '.join(FIVE_HOUR_WINDOW)}")
    budget[PLAN_KEY] = plan
    window = FIVE_HOUR_WINDOW[plan]
    stop = budget.get("stop_when_session_above")
    if window == "yes" and stop is None:
        raise BudgetError(f"budget {PLAN_KEY} {plan} has a 5-hour window: set "
                          "stop_when_session_above (harness/budget.py, FIVE_HOUR_WINDOW)")
    if window == "no" and (stop is not None or WORKING_HOURS in document):
        raise BudgetError(f"budget {PLAN_KEY} {plan} has no 5-hour window: remove "
                          f"stop_when_session_above and {WORKING_HOURS}")
    if WORKING_HOURS in document:
        if stop is None:
            raise BudgetError(f"budget {WORKING_HOURS} needs stop_when_session_above")
        budget[WORKING_HOURS] = _working_hours(document[WORKING_HOURS], stop)


def _clock(value, key: str) -> time:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        raise BudgetError(f"budget {WORKING_HOURS}.{key} must be HH:MM")
    try:
        return time(int(value[:2]), int(value[3:]))
    except ValueError:
        raise BudgetError(f"budget {WORKING_HOURS}.{key} must be HH:MM") from None


def _working_hours(value, stop: float) -> dict:
    """The validated `working_hours` mapping: an IANA `timezone`, `days` from
    WEEKDAYS, `start` before `end` as HH:MM on the same day, and a
    `session_stop` fraction no higher than `stop_when_session_above`."""
    if not isinstance(value, dict):
        raise BudgetError(f"budget {WORKING_HOURS} must be a mapping")
    unknown = sorted(set(value) - set(WORKING_HOURS_KEYS))
    missing = [key for key in WORKING_HOURS_KEYS if key not in value]
    if unknown or missing:
        raise BudgetError(f"budget {WORKING_HOURS} takes exactly the keys "
                          f"{', '.join(WORKING_HOURS_KEYS)}")
    zone = value["timezone"]
    try:
        if not isinstance(zone, str):
            raise ValueError
        tz = ZoneInfo(zone)
    except (ValueError, ZoneInfoNotFoundError):
        raise BudgetError(f"budget {WORKING_HOURS}.timezone must be an IANA "
                          "time zone, such as America/New_York") from None
    days = value["days"]
    if not isinstance(days, list) or not days or len(set(map(str, days))) != len(days) \
            or any(day not in WEEKDAYS for day in days):
        raise BudgetError(f"budget {WORKING_HOURS}.days must be a list of distinct "
                          f"days from {', '.join(WEEKDAYS)}")
    start, end = _clock(value["start"], "start"), _clock(value["end"], "end")
    if not start < end:
        raise BudgetError(f"budget {WORKING_HOURS}.start must be before end")
    session_stop = value["session_stop"]
    if isinstance(session_stop, bool) or not isinstance(session_stop, (int, float)) \
            or not math.isfinite(session_stop) or not 0 < session_stop <= stop:
        raise BudgetError(f"budget {WORKING_HOURS}.session_stop must be a number above 0 "
                          "and at most stop_when_session_above")
    return {"tz": tz, "days": frozenset(WEEKDAYS.index(day) for day in days),
            "start": start, "end": end, "session_stop": float(session_stop)}


def in_working_hours(hours: dict, now: datetime) -> bool:
    """Whether `now` (aware) falls in a working day's protected span: from
    SESSION_WINDOW before `start` to `end`, in the owner's time zone. The
    lead-in can begin the evening before."""
    local = now.astimezone(hours["tz"])
    for day in (local.date(), local.date() + timedelta(days=1)):
        if day.weekday() not in hours["days"]:
            continue
        begin = datetime.combine(day, hours["start"], hours["tz"]) - SESSION_WINDOW
        if begin <= now < datetime.combine(day, hours["end"], hours["tz"]):
            return True
    return False


def session_limit(budget: dict, now: datetime | None) -> float | None:
    """The 5-hour stop in force at `now`: `working_hours.session_stop` inside
    working hours (`in_working_hours`), else `stop_when_session_above`; None
    when the budget sets no 5-hour stop. With no `now`, the plain stop."""
    stop = budget.get("stop_when_session_above")
    hours = budget.get(WORKING_HOURS)
    if stop is not None and hours is not None and now is not None \
            and in_working_hours(hours, now):
        return hours["session_stop"]
    return stop


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
