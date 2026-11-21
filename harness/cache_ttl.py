"""Prompt-cache TTL policy for the CLI children and the operator's settings.

Claude Code picks a cache TTL per request in two buckets: the main
conversation, and "subagent" (subagents, workflows, background helpers).
Owner's rule (Adam, 2026-11-20): use the 1-hour cache "Where it's cheaper or
nominally the same cost, since at the same cost it can only save money due to
more cache hits." Cost here is the locked meter weight table's
`cache_write_5m` against `cache_write_1h` (points per million tokens). On an
API-billed lane dollars decide instead (1h writes cost 2x base input, 5m
1.25x), so those lanes stay 5m.

Precedence in the CLI (2.1.328): FORCE_PROMPT_CACHING_5M=1, then env
CLAUDE_CODE_PROMPT_CACHE_TTL / CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL, then
settings `promptCacheTtl` / `subagentPromptCacheTtl`, then agent frontmatter,
then ENABLE_PROMPT_CACHING_1H, then the default (main bucket 1h on a
subscription inside included usage, 5m elsewhere; subagent bucket 5m).

    python3 harness/cache_ttl.py verdict
    python3 harness/cache_ttl.py apply-settings --settings PATH [--dry-run]
    python3 harness/cache_ttl.py verify --projects DIR [--since-hours 24]

Output is numbers and fixed text only (it lands on a dashboard).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: A 1h weight at most this far above the 5m weight is "nominally the same".
#: The weight table's own notes treat 3% as the measurement floor ("a joint
#: range is never narrower than 3% either side of its point").
NOMINAL_TOLERANCE = 0.03
SETTINGS_KEY = "subagentPromptCacheTtl"
#: Any of these set non-empty means the child bills the API, not a subscription.
API_LANE_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_IDENTITY_TOKEN_FILE",
                "ANTHROPIC_IDENTITY_TOKEN", "CLAUDE_CODE_USE_BEDROCK",
                "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")
#: Ambient TTL knobs removed from an API-lane child.
TTL_ENV = ("CLAUDE_CODE_PROMPT_CACHE_TTL", "CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL",
           "ENABLE_PROMPT_CACHING_1H")
INVALID_SETTINGS = "settings file is not a valid JSON object"


def _point(row, key):
    cell = row.get(key) if isinstance(row, dict) else None
    point = cell.get("point") if isinstance(cell, dict) else None
    ok = (isinstance(point, (int, float)) and not isinstance(point, bool)
          and point >= 0)
    return (float(point) if ok else None), (cell.get("basis") if ok else None)


def model_verdicts(weights_doc) -> dict:
    """Per model: "1h" only if on every meter it appears in the 1h weight is
    at most the 5m weight plus NOMINAL_TOLERANCE. A missing row is "5m"."""
    meters = (weights_doc or {}).get("meters") or {}
    seen: dict[str, list] = {}
    for meter, block in meters.items():
        models = (block or {}).get("models") or {}
        for model, row in models.items():
            seen.setdefault(model, []).append((meter, row))
    out = {}
    for model, rows in seen.items():
        verdict = {"ttl": "1h", "w5m": None, "w1h": None, "basis_5m": None,
                   "basis_1h": None, "meters": [], "reasons": []}
        for meter, row in rows:
            w5, b5 = _point(row, "cache_write_5m")
            w1, b1 = _point(row, "cache_write_1h")
            if w5 is None or w1 is None:
                verdict["ttl"] = "5m"
                verdict["reasons"].append(f"{meter}: a cache write row is missing")
                continue
            if verdict["w5m"] is None:
                verdict.update(w5m=w5, w1h=w1, basis_5m=b5, basis_1h=b1)
            cheaper = w1 <= w5 * (1 + NOMINAL_TOLERANCE)
            verdict["meters"].append({"meter": meter, "w5m": w5, "w1h": w1,
                                      "ttl": "1h" if cheaper else "5m"})
            if not cheaper:
                verdict["ttl"] = "5m"
                verdict["reasons"].append(f"{meter}: 1h costs more than 5m")
        if not verdict["meters"]:
            verdict["ttl"] = "5m"
        out[model] = verdict
    return out


def subscription_ttl(weights_doc) -> tuple[str, list]:
    """"1h" iff every model's verdict is 1h (the CLI setting is not per model)."""
    verdicts = model_verdicts(weights_doc)
    if not verdicts:
        return "5m", ["no models in the weight table"]
    reasons = [f"{model}: {reason}" for model, v in sorted(verdicts.items())
               for reason in v["reasons"]]
    return ("1h" if all(v["ttl"] == "1h" for v in verdicts.values()) else "5m"), reasons


def lane_bills_api(env) -> bool:
    return any((env or {}).get(name) for name in API_LANE_ENV)


def ttl_env(env, weights_doc) -> dict:
    """The child's whole environment with the TTL policy applied."""
    out = dict(env)
    if lane_bills_api(out):
        for name in TTL_ENV:
            out.pop(name, None)
        out["FORCE_PROMPT_CACHING_5M"] = "1"
        return out
    ttl, _ = subscription_ttl(weights_doc)
    out.pop("FORCE_PROMPT_CACHING_5M", None)
    out["CLAUDE_CODE_PROMPT_CACHE_TTL"] = ttl
    out["CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL"] = ttl
    return out


def locked_weights() -> dict:
    import allowance_points  # noqa: PLC0415
    return allowance_points.table()


def verdict_doc(weights_doc=None) -> dict:
    doc = weights_doc if weights_doc is not None else locked_weights()
    ttl, reasons = subscription_ttl(doc)
    return {"table": doc.get("id"), "subscription_ttl": ttl, "reasons": reasons,
            "per_model": model_verdicts(doc)}


def apply_settings(path, ttl, dry_run=False) -> str:
    """Set only `subagentPromptCacheTtl`. Returns "applied" or "unchanged";
    raises ValueError(INVALID_SETTINGS) for a file that is not a JSON object."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(INVALID_SETTINGS) from None
    if not isinstance(data, dict):
        raise ValueError(INVALID_SETTINGS)
    if data.get(SETTINGS_KEY) == ttl:
        return "unchanged"
    if dry_run:
        return "applied"
    data[SETTINGS_KEY] = ttl
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return "applied"


def tally(projects, since_hours=24.0, now=None) -> dict:
    """Cache-write tokens from transcripts modified in the window, by bucket
    (`isSidechain` true is the subagent bucket) and model."""
    now = time.time() if now is None else now
    cutoff = now - since_hours * 3600
    buckets = {"main": {}, "subagent": {}}
    root = Path(projects)
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        try:
            if path.stat().st_mtime < cutoff:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                entry = json.loads(line)
                message = entry["message"]
                created = message["usage"]["cache_creation"]
                w5 = created["ephemeral_5m_input_tokens"]
                w1 = created["ephemeral_1h_input_tokens"]
            except (ValueError, KeyError, TypeError):
                continue
            if not all(isinstance(n, int) and not isinstance(n, bool) and n >= 0
                       for n in (w5, w1)):
                continue
            model = message.get("model") if isinstance(message, dict) else None
            bucket = buckets["subagent" if entry.get("isSidechain") is True else "main"]
            row = bucket.setdefault(model if isinstance(model, str) else "unknown",
                                    {"w5m": 0, "w1h": 0})
            row["w5m"] += w5
            row["w1h"] += w1
    return buckets


def verify(projects, since_hours=24.0, weights_doc=None, now=None) -> dict:
    """Observed cache writes against the expected TTL per bucket: main is 1h,
    subagent follows the subscription verdict. API-billed sessions cannot be
    told apart in a transcript, so a 5m-heavy bucket is reported, not blamed."""
    doc = weights_doc if weights_doc is not None else locked_weights()
    want, _ = subscription_ttl(doc)
    buckets = tally(projects, since_hours, now)
    out = {"since_hours": since_hours, "buckets": {}}
    for name, expected in (("main", "1h"), ("subagent", want)):
        models = buckets[name]
        w5 = sum(r["w5m"] for r in models.values())
        w1 = sum(r["w1h"] for r in models.values())
        wrong = w5 if expected == "1h" else w1
        total = w5 + w1
        entry = {"expected": expected, "w5m": w5, "w1h": w1, "per_model": models}
        if total == 0:
            entry.update(ok=True, reason="no cache writes in the window")
        elif wrong == 0:
            entry.update(ok=True, reason="all writes match the expected TTL")
        else:
            entry.update(ok=False, reason=f"{wrong} of {total} cache write tokens "
                                          f"were not at the expected {expected} rate")
        out["buckets"][name] = entry
    out["ok"] = all(b["ok"] for b in out["buckets"].values())
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("verdict")
    a = sub.add_parser("apply-settings")
    a.add_argument("--settings", type=Path, required=True)
    a.add_argument("--dry-run", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("--projects", type=Path, required=True)
    v.add_argument("--since-hours", type=float, default=24.0)
    args = p.parse_args(argv)
    if args.command == "verdict":
        print(json.dumps(verdict_doc()))
        return 0
    if args.command == "apply-settings":
        ttl, _ = subscription_ttl(locked_weights())
        try:
            result = apply_settings(args.settings, ttl, args.dry_run)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps({"settings": result, "key": SETTINGS_KEY, "ttl": ttl,
                          "dry_run": args.dry_run}))
        return 0
    print(json.dumps(verify(args.projects, args.since_hours)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
