"""Approximate weekly-allowance points from a run's token counts by type.

The one adapter between this repo and the vendored usage-weights package
(`vendor/usage_weights/`). `evals/usage-weights.lock` names the release and the
weight table; this module reads it, checks every vendored file against its
sha256, loads the table once, and prices the token counts `harness/run_eval.py`
records per role (`usage.measured.<role>`: `models` per model id, and the
5-minute/1-hour cache-write split in `cache_creation`).

A point is 1% of the weekly allowance on one meter. Everything here is in
points; `evals/budget.yml` values are fractions of the week, so a caller
divides by 100. Nothing is rounded.

The 5-minute/1-hour split is recorded per role, not per model (the CLI reports
it for the main loop only), so it is applied only when one model made the
role's calls; with more than one, the cache writes are priced unsplit (the
5-minute weight with the wider range of both, the package's rule).

A role whose token counts are missing (a result without `modelUsage`, or a
summary from before tokens were kept) is priced from its dollars at
`evals/budget.yml` `legacy_usd_per_point`, and the estimate says so
(`complete` false, `legacy_usd`). With neither, the role is `unpriced` and a
caller falls back to whatever it did before.
"""

from __future__ import annotations

import functools
import hashlib
import math
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK = ROOT / "evals" / "usage-weights.lock"
VENDOR = ROOT / "vendor"
ROLES = ("agent", "judge", "guard")
#: The meters an estimate reports: the all-models weekly meter, which the
#: budget is held to, and the Fable weekly meter, which judge calls on Fable
#: also move (reported only; no cap reads it).
METERS = ("all_models", "fable")
#: `_role_usage` token names, as the package's token types.
TOKEN_NAMES = (("input_tokens", "input"), ("output_tokens", "output"),
               ("cache_read_input_tokens", "cache_read"))
CACHE_TOTAL = "cache_creation_input_tokens"
CACHE_SPLIT = (("ephemeral_5m_input_tokens", "cache_write_5m"),
               ("ephemeral_1h_input_tokens", "cache_write_1h"))
LOCK_KEYS = ("repo", "commit", "tag", "table", "files")
COMMIT = re.compile(r"[0-9a-f]{40}")


class LockError(ValueError):
    """The lock file is missing, malformed, or a vendored file does not match it."""


def _number(value) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value >= 0)


def read_lock(path: Path | None = None, vendor: Path | None = None) -> dict:
    """The validated lock: every vendored file present with the recorded
    sha256 and nothing vendored that the lock does not name."""
    path = Path(path) if path is not None else DEFAULT_LOCK
    vendor = Path(vendor) if vendor is not None else VENDOR
    try:
        lock = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LockError(f"{path.name} is missing: it names the usage-weights "
                        "release and weight table every allowance estimate uses, "
                        "and there is no default") from None
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise LockError(f"{path.name} could not be read: {type(error).__name__}") from None
    if not isinstance(lock, dict) or sorted(lock) != sorted(LOCK_KEYS):
        raise LockError(f"{path.name} must have exactly the keys {list(LOCK_KEYS)}")
    if not isinstance(lock["repo"], str) or lock["repo"].count("/") != 1:
        raise LockError(f"{path.name} `repo` must name the source repository as owner/name")
    if not isinstance(lock["commit"], str) or not COMMIT.fullmatch(lock["commit"]):
        raise LockError(f"{path.name} `commit` must be the release's full 40-hex commit")
    if lock["tag"] is not None and not isinstance(lock["tag"], str):
        raise LockError(f"{path.name} `tag` must be the release tag or null")
    table = lock["table"]
    if not isinstance(table, str) or not table or "/" in table or "\\" in table:
        raise LockError(f"{path.name} `table` must name one packaged weight table id")
    files = lock["files"]
    if not isinstance(files, dict) or not files:
        raise LockError(f"{path.name} `files` must map each vendored file to its sha256")
    root = vendor / "usage_weights"
    present = {p.relative_to(vendor).as_posix() for p in root.rglob("*")
               if p.is_file() and "__pycache__" not in p.parts} if root.is_dir() else set()
    if set(files) != present:
        missing, extra = sorted(set(files) - present), sorted(present - set(files))
        raise LockError(f"vendored usage_weights does not match {path.name}: "
                        f"missing {missing}, not in the lock {extra}")
    for name, digest in files.items():
        actual = hashlib.sha256((vendor / name).read_bytes()).hexdigest()
        if actual != digest:
            raise LockError(f"vendored {name} does not match its sha256 in {path.name}")
    if f"usage_weights/data/weights/{table}.json" not in files:
        raise LockError(f"{path.name} names table {table!r}, which is not vendored")
    return lock


def _package():
    if str(VENDOR) not in sys.path:
        sys.path.insert(0, str(VENDOR))
    import usage_weights  # noqa: PLC0415 (vendored, path set above)
    return usage_weights


@functools.lru_cache(maxsize=None)
def _locked_table(path: str, vendor: str) -> dict:
    lock = read_lock(Path(path), Path(vendor))
    return _package().load_table(lock["table"])


def table(path: Path | None = None) -> dict:
    """The locked weight table, loaded once per process."""
    return _locked_table(str(Path(path) if path is not None else DEFAULT_LOCK), str(VENDOR))


def role_records(block) -> list[dict] | None:
    """The package records for one `usage.measured.<role>` block, or None
    when its token counts are not all known. A role that made no call has
    none."""
    if not isinstance(block, dict) or not block.get("calls"):
        return []
    models = block.get("models")
    if not isinstance(models, dict) or not models:
        return None
    records = []
    for model, counts in models.items():
        if not isinstance(counts, dict):
            return None
        tokens = {}
        for name, kind in TOKEN_NAMES:
            if not _number(counts.get(name)):
                return None
            tokens[kind] = int(counts[name])
        if not _number(counts.get(CACHE_TOTAL)):
            return None
        tokens["cache_write"] = int(counts[CACHE_TOTAL])
        records.append({"model": model, "tokens": tokens,
                        "usd": counts.get("cost_usd")})
    split = block.get("cache_creation")
    if len(records) == 1 and isinstance(split, dict) \
            and all(_number(split.get(name)) for name, _ in CACHE_SPLIT):
        tokens = records[0]["tokens"]
        parts = {kind: int(split[name]) for name, kind in CACHE_SPLIT}
        if sum(parts.values()) <= tokens["cache_write"]:
            tokens["cache_write"] -= sum(parts.values())
            tokens.update(parts)
    return records


def _zero() -> dict:
    return {meter: {"points": 0.0, "low": 0.0, "high": 0.0} for meter in METERS}


def estimate_blocks(blocks, legacy_usd_per_point=None, lock: Path | None = None) -> dict:
    """The allowance estimate of a list of `usage.measured` blocks (one per
    trial, each with its `agent`, `judge` and `guard` roles), as
    `usage.allowance_estimate`.

    `points`, `low` and `high` are the all-models meter; `fable` is the
    Fable meter. Roles with no token counts add their dollars at
    `legacy_usd_per_point` (a point estimate, no range of its own) and are
    counted in `legacy_roles` and `legacy_usd`, as is a model the table does
    not price; one with neither tokens nor dollars, or without a legacy rate,
    is counted in `unpriced_roles`, and then the estimate is a floor."""
    weights = table(lock)
    package = _package()
    known = {m for meter in weights["meters"].values() for m in meter["models"]}
    rate = legacy_usd_per_point if _number(legacy_usd_per_point) \
        and legacy_usd_per_point > 0 else None
    records, legacy_usd, legacy_roles, unpriced, priced = [], 0.0, 0, 0, 0

    def legacy(usd) -> None:
        nonlocal legacy_usd, legacy_roles, unpriced
        if _number(usd) and rate is not None:
            legacy_usd += float(usd)
            legacy_roles += 1
        else:
            unpriced += 1

    for measured in blocks:
        for role in ROLES:
            block = measured.get(role) if isinstance(measured, dict) else None
            found = role_records(block)
            if found is None:
                legacy(block.get("cost_usd") if isinstance(block, dict) else None)
                continue
            # A model the table does not price (an older or newer model) is
            # charged its own dollars at the legacy rate.
            for record in found:
                if package.records.resolve_model(record["model"], known) is None:
                    legacy(record["usd"])
                else:
                    records.append(record)
            priced += bool(found)
    totals = _zero()
    for meter in METERS:
        result = package.estimate(records, weights, meter=meter)
        totals[meter] = {"points": result.points, "low": result.low, "high": result.high}
    legacy = legacy_usd / rate if legacy_roles else 0.0
    main = totals["all_models"]
    return {"table": weights["id"],
            "points": main["points"] + legacy,
            "low": main["low"] + legacy,
            "high": main["high"] + legacy,
            "fable": totals["fable"],
            "roles_from_tokens": priced,
            "legacy_roles": legacy_roles,
            "legacy_usd": legacy_usd,
            "unpriced_roles": unpriced,
            "complete": legacy_roles == 0 and unpriced == 0}
