#!/usr/bin/env python3
"""Regression detection (#69, #121): has a skill, or a guidance section, stopped
helping since the last time it was measured?

Pure functions over the index `scripts/compute_gates.build_index` returns; no
network, no subprocess, no clock. `scripts/regression_issue.py` reads the
document this builds and files the issues. Thresholds live in
`evals/regression-policy.yml`, one block for skills and one for guidance.

THE CELL. One (subject, id, fixture, model, pair) is compared against its own
past: subject `skill` reads `index["runs"]` (id = the skill, no pair), subject
`guidance` reads `index["guidance_runs"]` (id = the section, pair one of
`gates.GUIDANCE_PAIRS`). Only models in the roster are read, and bare runs
(`index["bare_runs"]`) never are.

LIKE WITH LIKE. Within a cell only the runs whose `fixture_digest` equals the
newest run's are kept (None matches only None): an edited fixture is a
different test, so older runs of it say nothing about this one. The skill's
content (`tested_digest`), the CLI version and the arm context may differ
between the windows; those are what a regression is about, and the row
reports them as suspects.

WINDOWS. The cell's runs are reduced with `gates.prime` (both roles), only the
runs that count (`numbers["counted"]`) are kept, and each role is ordered by
`gates._order`. The current window is the newest `window_runs` runs of a role
and the previous window the `window_runs` before them. The `with` role
decides: a window of fewer than `min_window_runs` runs is `insufficient`.

THE NUMBERS. A window's objective figure is the mean of its runs' run means
(a run without one is left out), the drop is previous minus current, and the
NOISE is the pooled within-window standard deviation of run means: the square
root of the summed squared deviations from each window's own mean over
(n_previous + n_current - 2), 0 when that denominator is not above 0. The
judge figure is the same over the runs' judge means, read only when both
windows hold at least `min_window_runs` judged runs. A drop must clear the
noise as well as its threshold, so a noisy fixture does not alarm on noise.

VERDICTS, the first that matches:

1. `regressed`: the objective drop is at least `objective_drop` and larger
   than the noise, or the judge drop is at least `judge_drop` and larger than
   the judge noise.
2. `lost-delta`: the `without` role has at least `min_window_runs` runs in
   both of its own windows (built the same way), the previous delta (previous
   `with` mean minus previous `without` mean) is at least
   `lost_delta_min_previous` and the current delta is 0 or below.
3. `improved`: the symmetric rise, or the delta went from 0 or below to at
   least `lost_delta_min_previous`.
4. `stable`.

A subject's verdict (one per skill or section) is `regressed` if any row
regressed, else `lost-delta`, else `improved`, else `stable`, else
`insufficient`. Deterministic: sorted rows, no NaN or infinity.
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

import gates

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "evals" / "regression-policy.yml"
SUBJECTS = ("skill", "guidance")
VERDICTS = ("regressed", "lost-delta", "improved", "stable", "insufficient")
#: Verdicts an issue is kept open for.
BAD = ("regressed", "lost-delta")


class RegressionPolicyError(ValueError):
    """The regression policy is missing, unreadable or breaks a rule."""


def _count(low, high=None):
    return lambda v: (isinstance(v, int) and not isinstance(v, bool) and v >= low
                      and (high is None or v <= high))


POLICY_KEYS = {
    "window_runs": ("an integer of at least 2", _count(2)),
    "min_window_runs": ("an integer from 2 to window_runs", _count(2)),
    "objective_drop": ("a number above 0 and at most 1", gates._number(0, 1, low_open=True)),
    "judge_drop": ("a number above 0 and at most 10", gates._number(0, 10, low_open=True)),
    "lost_delta_min_previous": ("a number above 0 and at most 1",
                                gates._number(0, 1, low_open=True)),
}
SUBJECT_BLOCKS = {"skill": "skills", "guidance": "guidance"}


def parse_policy(text: str) -> dict:
    """{"skills": {...}, "guidance": {...}} from `text`, or
    RegressionPolicyError naming the key. Both blocks have the same keys and
    rules and are kept apart so the two can diverge."""
    try:
        document = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError):
        raise RegressionPolicyError("regression policy is not valid YAML") from None
    if not isinstance(document, dict) or set(document) != {"skills", "guidance"}:
        raise RegressionPolicyError("regression policy must be a mapping with the keys "
                                    "skills and guidance")
    return {name: _block(document[name], name) for name in ("skills", "guidance")}


def _block(block, name: str) -> dict:
    if not isinstance(block, dict):
        raise RegressionPolicyError(f"regression policy {name} must be a mapping")
    unknown = sorted(set(block) - set(POLICY_KEYS))
    if unknown:
        raise RegressionPolicyError(f"regression policy {name} has unknown keys {unknown}")
    out = {}
    for key, (words, valid) in POLICY_KEYS.items():
        if key not in block:
            raise RegressionPolicyError(f"regression policy {name} is missing {key}")
        if not valid(block[key]):
            raise RegressionPolicyError(f"regression policy {name}.{key} must be {words}")
        out[key] = block[key]
    if out["min_window_runs"] > out["window_runs"]:
        raise RegressionPolicyError(f"regression policy {name}.min_window_runs must be "
                                    "an integer from 2 to window_runs")
    return out


def load_policy(path: Path | None = None) -> dict:
    """`parse_policy` of the file at `path` (default evals/regression-policy.yml)."""
    path = Path(path) if path is not None else DEFAULT_POLICY
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise RegressionPolicyError(f"regression policy {path.name} could not be read") \
            from None
    return parse_policy(text)


# ---------------------------------------------------------------------------
# Windows and figures.

def _windows(runs: list, size: int) -> tuple:
    """(previous, current): the newest `size` of `runs` (ordered oldest
    first) and the `size` before them."""
    return runs[-2 * size:-size], runs[-size:]


def _figures(runs: list, field: str) -> list:
    return [r["numbers"][field] for r in runs if r["numbers"][field] is not None]


def _mean(values: list) -> float:
    return math.fsum(values) / len(values)


def _noise(previous: list, current: list) -> float:
    """The pooled within-window standard deviation (module docstring)."""
    denominator = len(previous) + len(current) - 2
    if denominator <= 0:
        return 0.0
    squares = [(v - _mean(window)) ** 2 for window in (previous, current)
               if window for v in window]
    return math.sqrt(math.fsum(squares) / denominator)


def _compare(previous: list, current: list) -> dict:
    """{"previous", "current", "change", "noise"} of two windows of figures."""
    before, after = _mean(previous), _mean(current)
    return {"previous": before, "current": after, "change": after - before,
            "noise": _noise(previous, current)}


def _entry(run: dict) -> dict:
    return {"timestamp": run["timestamp"], "path": run["path"],
            "report": gates._link(run["report"]), "tested_digest": run["tested_digest"],
            "cli_versions": sorted(run["cli_versions"]),
            "arm_context_digest": run["arm_context_digest"]}


def _suspects(subject: str, previous: list, current: list) -> list:
    """What differs between the two windows of the `with` role."""
    if not previous or not current:
        return []

    def differs(field):
        def values(runs):
            return {v for r in runs for v in (r[field] if field == "cli_versions"
                                              else [r[field]])}
        return values(previous) != values(current)
    out = []
    if differs("tested_digest"):
        out.append("skill content changed" if subject == "skill"
                   else "section content changed")
    if differs("cli_versions"):
        out.append("CLI version changed")
    if differs("arm_context_digest"):
        out.append("arm context changed")
    return out


def _ordered(runs: list, role: str) -> list:
    return sorted((r for r in runs if r["role"] == role), key=gates._order)


def _row(subject: str, ident: str, fixture, model: str, pair, runs: list,
         policy: dict) -> dict:
    """The row of one cell, from every run of it (module docstring)."""
    newest = max(runs, key=gates._order)["fixture_digest"]
    runs = [r for r in runs if r["fixture_digest"] == newest]
    gates.prime(runs)
    counted = [r for r in runs if r["numbers"]["counted"]]
    size, least = policy["window_runs"], policy["min_window_runs"]
    previous, current = _windows(_ordered(counted, "with"), size)
    out = {"subject": subject, "id": ident, "fixture": fixture, "model": model,
           "pair": pair, "verdict": "insufficient", "reason": None,
           "numbers": {"objective": None, "judge": None, "delta": None},
           "windows": {"previous": [_entry(r) for r in previous],
                       "current": [_entry(r) for r in current]},
           "suspects": _suspects(subject, previous, current),
           "boundary": {"after": previous[-1]["timestamp"] if previous else None,
                        "before": current[0]["timestamp"] if current else None}}
    objective_before, objective_after = _figures(previous, "run_mean"), \
        _figures(current, "run_mean")
    if len(previous) < least or len(current) < least \
            or not objective_before or not objective_after:
        out["reason"] = (f"fewer than {least} runs in a window "
                         f"(previous {len(previous)}, current {len(current)})")
        return out
    objective = _compare(objective_before, objective_after)
    judge_before, judge_after = _figures(previous, "judge_mean"), \
        _figures(current, "judge_mean")
    judge = (_compare(judge_before, judge_after)
             if len(judge_before) >= least and len(judge_after) >= least else None)
    before_out, after_out = _windows(_ordered(counted, "without"), size)
    means_before, means_after = _figures(before_out, "run_mean"), \
        _figures(after_out, "run_mean")
    delta = None
    if len(before_out) >= least and len(after_out) >= least \
            and means_before and means_after:
        delta = {"previous": objective["previous"] - _mean(means_before),
                 "current": objective["current"] - _mean(means_after)}
    out["numbers"] = {"objective": objective, "judge": judge, "delta": delta}
    out["verdict"], out["reason"] = _verdict(objective, judge, delta, policy)
    return out


def _moved(figure, threshold: float, sign: int) -> bool:
    """Whether `figure` (or None) moved by `threshold` in the direction of
    `sign` (-1 a drop, 1 a rise) and by more than its noise."""
    if figure is None:
        return False
    change = sign * figure["change"]
    return change >= threshold and change > figure["noise"]


def _verdict(objective: dict, judge, delta, policy: dict) -> tuple:
    """(verdict, reason) of a cell that has both windows (module docstring)."""
    need = policy["lost_delta_min_previous"]
    figures = (("objective", objective, policy["objective_drop"]),
               ("judge", judge, policy["judge_drop"]))
    for name, figure, threshold in figures:
        if _moved(figure, threshold, -1):
            return "regressed", (f"the {name} mean fell by {-figure['change']} "
                                 f"(threshold {threshold}, noise {figure['noise']})")
    if delta is not None and delta["previous"] >= need and delta["current"] <= 0:
        return "lost-delta", (f"with minus without went from {delta['previous']} "
                              f"to {delta['current']}")
    for name, figure, threshold in figures:
        if _moved(figure, threshold, 1):
            return "improved", (f"the {name} mean rose by {figure['change']} "
                                f"(threshold {threshold}, noise {figure['noise']})")
    if delta is not None and delta["previous"] <= 0 and delta["current"] >= need:
        return "improved", (f"with minus without went from {delta['previous']} "
                            f"to {delta['current']}")
    return "stable", "no figure moved past its threshold and its noise"


def subject_verdict(verdicts) -> str:
    """One verdict from a subject's rows (module docstring)."""
    verdicts = set(verdicts)
    for verdict in VERDICTS:
        if verdict in verdicts:
            return verdict
    return "insufficient"


def compute(index: dict, models: list, policies: dict, as_of: str) -> dict:
    """The regression document for `index` over the roster's arm `models`."""
    models = sorted(set(models))
    cells: dict = {}
    for subject, key in (("skill", "runs"), ("guidance", "guidance_runs")):
        for run in index.get(key, []):
            if run["model"] in models:
                cell = (subject, run["skill"], run["fixture"], run["model"],
                        run.get("pair") if subject == "guidance" else None)
                cells.setdefault(cell, []).append(run)
    rows = [_row(*cell, runs, policies[SUBJECT_BLOCKS[cell[0]]])
            for cell, runs in cells.items()]
    rows.sort(key=lambda r: (r["subject"], r["id"], r["fixture"] or "", r["model"],
                             r["pair"] or ""))
    subjects: dict = {"skill": {}, "guidance": {}}
    for subject in SUBJECTS:
        for ident in sorted({r["id"] for r in rows if r["subject"] == subject}):
            subjects[subject][ident] = subject_verdict(
                r["verdict"] for r in rows if r["subject"] == subject and r["id"] == ident)
    return {"schema_version": 1, "as_of": as_of, "policy": policies,
            "roster_models": models, "rows": rows, "subjects": subjects}
