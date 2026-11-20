"""How the two meter readers report the weekly meter."""
from __future__ import annotations

CLI_METER_KEYS = {"all_models": "seven_day", "fable": "seven_day_overage_included"}


def reading_bounds(percent, reader: str) -> tuple[float, float]:
    """Half-open range [low, high) the true meter value lies in, given a whole-percent reading."""
    if reader == "cli":  # the CLI truncates
        return (percent, percent + 1)
    if reader == "usage_endpoint":  # the usage endpoint rounds to the nearest percent
        return (percent - 0.5, percent + 0.5)
    raise ValueError(f"unknown reader {reader!r}; use 'cli' or 'usage_endpoint'")


def percent_from_cli_fraction(x: float) -> int:
    """The CLI reports a fraction with two decimals (0.63 is 63%); over 1 is overage."""
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not (0 <= x <= 10):
        raise ValueError(f"CLI meter fraction out of range 0..10: {x!r}")
    return int(round(x * 100, 6))
