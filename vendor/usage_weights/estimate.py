"""Estimate weekly-allowance points (and API dollars) for a set of records."""
from __future__ import annotations

from dataclasses import dataclass

from .records import TOKEN_TYPES, record_tokens, resolve_model


@dataclass(frozen=True)
class Estimate:
    meter: str
    table: str
    points: float
    low: float
    high: float
    by_model: dict
    by_type: dict
    by_basis: dict
    tokens: dict
    skipped: dict



def _all_models(table: dict) -> set:
    return {m for meter in table["meters"].values() for m in meter["models"]}


def _resolve(model_id, known, on_unknown, table_id, skipped):
    resolved = resolve_model(model_id, known)
    if resolved is None:
        if on_unknown == "error":
            raise ValueError(
                f"unknown model {model_id!r} in table {table_id}; known models: {', '.join(sorted(known))}"
            )
        skipped[model_id] = skipped.get(model_id, 0) + 1
    return resolved


def _check_on_unknown(on_unknown):
    if on_unknown not in ("error", "skip"):
        raise ValueError(f"on_unknown must be 'error' or 'skip', got {on_unknown!r}")


def estimate(records, table: dict, meter: str = "all_models", on_unknown: str = "error") -> Estimate:
    _check_on_unknown(on_unknown)
    if meter not in table["meters"]:
        raise ValueError(f"unknown meter {meter!r}; table {table['id']} has: {', '.join(table['meters'])}")
    rows = table["meters"][meter]["models"]
    known = _all_models(table)
    pts = {"point": 0.0, "low": 0.0, "high": 0.0}
    by_model, by_type, by_basis, tokens, skipped = {}, {}, {}, {}, {}
    for rec in records:
        tok = record_tokens(rec)
        model = _resolve(rec["model"], known, on_unknown, table["id"], skipped)
        if model is None:
            continue
        row = rows.get(model)
        if row is None:  # known model, but it does not count on this meter
            continue
        m = by_model.setdefault(model, {"points": 0.0, "low": 0.0, "high": 0.0})
        for t, n in tok.items():
            if n == 0:
                continue
            if t == "cache_write":
                w5, w1 = row["cache_write_5m"], row["cache_write_1h"]
                point, low, high, basis = w5["point"], min(w5["low"], w1["low"]), max(w5["high"], w1["high"]), w5["basis"]
            else:
                w = row[t]
                point, low, high, basis = w["point"], w["low"], w["high"], w["basis"]
            p = n / 1e6 * point
            m["points"] += p
            m["low"] += n / 1e6 * low
            m["high"] += n / 1e6 * high
            pts["point"] += p
            pts["low"] += n / 1e6 * low
            pts["high"] += n / 1e6 * high
            by_type[t] = by_type.get(t, 0.0) + p
            by_basis[basis] = by_basis.get(basis, 0.0) + p
            tokens[t] = tokens.get(t, 0) + n
    return Estimate(meter, table["id"], pts["point"], pts["low"], pts["high"], by_model, by_type, by_basis, tokens, skipped)


def api_usd(records, prices: dict, on_unknown: str = "error") -> float:
    """Dollars at API list prices; unsplit cache writes are priced at the 5-minute rate."""
    _check_on_unknown(on_unknown)
    known = set(prices["models"])
    skipped = {}
    total = 0.0
    for rec in records:
        tok = record_tokens(rec)
        model = _resolve(rec["model"], known, on_unknown, prices.get("id", "?"), skipped)
        if model is None:
            continue
        row = prices["models"][model]
        for t, n in tok.items():
            rate = row["cache_write_5m"] if t == "cache_write" else row[t]
            total += n / 1e6 * rate
    return total
