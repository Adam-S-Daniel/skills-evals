"""Turn usage records into token counts by type."""
from __future__ import annotations

TOKEN_TYPES = ("input", "output", "cache_read", "cache_write_5m", "cache_write_1h")


def _count(usage: dict, field: str) -> int:
    v = usage.get(field, 0)
    if v is None:
        v = 0
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{field}: not a number: {v!r}")
    if v < 0:
        raise ValueError(f"{field}: negative count {v!r}")
    return int(v)


def tokens_from_usage(usage: dict) -> dict:
    """Convert one API / CLI `usage` object to token counts by type.

    Cache writes split by lifetime when `cache_creation` says how; otherwise,
    or for a remainder the split does not explain, they go under "cache_write".
    """
    out = {
        "input": _count(usage, "input_tokens"),
        "output": _count(usage, "output_tokens"),
        "cache_read": _count(usage, "cache_read_input_tokens"),
    }
    total = _count(usage, "cache_creation_input_tokens")
    cc = usage.get("cache_creation")
    if isinstance(cc, dict):
        out["cache_write_5m"] = _count(cc, "ephemeral_5m_input_tokens")
        out["cache_write_1h"] = _count(cc, "ephemeral_1h_input_tokens")
        rest = total - out["cache_write_5m"] - out["cache_write_1h"]
        if rest > 0:
            out["cache_write"] = rest
    else:
        out["cache_write_5m"] = 0
        out["cache_write_1h"] = 0
        if total > 0:
            out["cache_write"] = total
    return out


def record_tokens(record: dict) -> dict:
    """Token counts for one record: `tokens`, else `usage`, else flat token keys."""
    if not isinstance(record, dict) or not isinstance(record.get("model"), str):
        raise ValueError("record needs a string 'model'")
    if isinstance(record.get("tokens"), dict):
        src = record["tokens"]
    elif isinstance(record.get("usage"), dict):
        return tokens_from_usage(record["usage"])
    elif any(t in record for t in TOKEN_TYPES + ("cache_write",)):
        src = record
    else:
        raise ValueError(f"record for model {record['model']!r} has no tokens, usage or token keys")
    out = {}
    for t in TOKEN_TYPES + ("cache_write",):
        if t in src:
            out[t] = _count(src, t)
    return out


def resolve_model(model_id: str, models) -> str | None:
    """Exact match, else the longest table key the id starts with (case-insensitive)."""
    mid = model_id.lower()
    best = None
    for key in models:
        k = key.lower()
        if mid == k:
            return key
        if mid.startswith(k) and (best is None or len(k) > len(best.lower())):
            best = key
    return best
