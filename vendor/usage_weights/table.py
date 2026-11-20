"""Dated weight tables and price tables (JSON, schema 1)."""
from __future__ import annotations

import json
import math
import os
from importlib import resources

from .records import TOKEN_TYPES

BASES = ("measured", "joint", "assumed", "published")


def _packaged_dir(kind: str):
    return resources.files("usage_weights").joinpath("data", kind)


def _list(kind: str) -> list[str]:
    d = _packaged_dir(kind)
    return sorted(p.name[: -len(".json")] for p in d.iterdir() if p.name.endswith(".json"))


def list_tables() -> list[str]:
    """Ids of the packaged weight tables."""
    return _list("weights")


def _read(kind: str, name_or_path, what: str) -> dict:
    if name_or_path is None:
        raise ValueError(f"name a {what}: there is no implicit latest; pin one on purpose (known: {', '.join(_list(kind))})")
    if isinstance(name_or_path, os.PathLike) or (isinstance(name_or_path, str) and os.path.isfile(name_or_path)):
        with open(name_or_path, encoding="utf-8") as fh:
            return json.load(fh)
    name = str(name_or_path)
    ref = _packaged_dir(kind).joinpath(f"{name}.json")
    if "/" in name or "\\" in name or not ref.is_file():
        raise ValueError(f"unknown {what} {name!r}; packaged: {', '.join(_list(kind))}")
    return json.loads(ref.read_text(encoding="utf-8"))


def _num(x, where: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0:
        raise ValueError(f"{where}: expected a finite non-negative number, got {x!r}")
    return float(x)


def validate_table(table: dict) -> None:
    """Raise ValueError with a descriptive message if the table breaks schema 1."""
    if not isinstance(table, dict) or table.get("schema") != 1:
        raise ValueError(f"unsupported table schema {table.get('schema') if isinstance(table, dict) else table!r}; expected 1")
    tid = table.get("id", "?")
    meters = table.get("meters")
    if not isinstance(meters, dict) or not meters:
        raise ValueError(f"table {tid}: no meters")
    for mname, meter in meters.items():
        models = meter.get("models")
        if not isinstance(models, dict):
            raise ValueError(f"table {tid}: meter {mname} has no models")
        for model, row in models.items():
            for t in TOKEN_TYPES:
                where = f"table {tid}: {mname}/{model}/{t}"
                if t not in row:
                    raise ValueError(f"{where}: missing token type")
                w = row[t]
                if w.get("basis") not in BASES:
                    raise ValueError(f"{where}: unknown basis {w.get('basis')!r}")
                point, low, high = (_num(w.get(k), f"{where}.{k}") for k in ("point", "low", "high"))
                if low > point:
                    raise ValueError(f"{where}: low {low} is above point {point}")
                if point > high:
                    raise ValueError(f"{where}: point {point} is above high {high}")


def load_table(name_or_path=None) -> dict:
    """Load and validate a weight table by packaged id or by file path."""
    table = _read("weights", name_or_path, "table")
    validate_table(table)
    return table


def load_prices(name_or_path=None) -> dict:
    """Load an API price table by packaged id or by file path."""
    prices = _read("prices", name_or_path, "price table")
    if prices.get("schema") != 1 or not isinstance(prices.get("models"), dict):
        raise ValueError(f"bad price table {name_or_path!r}")
    for model, row in prices["models"].items():
        for t in TOKEN_TYPES:
            _num(row.get(t), f"prices {prices.get('id')}: {model}/{t}")
    return prices
