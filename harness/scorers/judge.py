"""LLM-as-judge scoring.

The judge receives the fixture's rubric, the agent transcript, and the diff of
the workspace, and returns per-dimension scores with rationales as JSON.

Implementation: a second headless `claude -p ... --output-format json` call
whose prompt embeds the rubric/transcript/diff and demands JSON-only output.
See DESIGN.md — "Open decisions".
"""

from __future__ import annotations

import json
import os
import re
import subprocess

_REQUIRED_DIM_KEYS = ("name", "score", "rationale")


def _build_prompt(rubric: str, transcript: str, workspace_diff: str) -> str:
    return (
        "You are grading an AI coding agent's work against a rubric.\n\n"
        "## Rubric\n" + rubric.strip() + "\n\n"
        "## Agent transcript\n" + transcript.strip() + "\n\n"
        "## Workspace diff (git diff --cached)\n" + workspace_diff.strip() + "\n\n"
        "Respond with ONLY a JSON object, no other text, no Markdown code "
        "fences, matching exactly this shape (scores are 0-10):\n"
        '{"dimensions": [{"name": "...", "score": 0, "rationale": "..."}], '
        '"overall": 0.0}'
    )


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of judge output, tolerating fences/prose around it."""
    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    braces = text[text.find("{"): text.rfind("}") + 1] if "{" in text and "}" in text else ""
    for candidate in (text, fenced, braces):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"could not parse judge output as JSON: {text!r}")


def _weighted_overall(dimensions: list, weights: dict) -> float:
    """Weighted mean of the judge's per-dimension scores, on the 0-10 scale.

    Dimension names are matched case-insensitively and whitespace-trimmed, so
    a fixture writing `completeness` lines up with a judge answering
    "Completeness". A dimension the weights dict does not mention keeps weight
    1.0 — it is never silently dropped, because a judge that invents a fourth
    dimension should still count for something rather than vanish.

    A weight that isn't a non-negative real number (a fixture typo, `null`,
    a string) falls back to 1.0 rather than raising: the caller records a
    judge error on any exception, so raising here would blank the judge for
    the whole run over a YAML slip. If the applied weights sum to zero, the
    result degrades to the plain unweighted mean rather than reporting a
    misleading 0.0.
    """
    lookup = {str(name).strip().casefold(): w for name, w in weights.items()}

    weighted_sum, applied = 0.0, 0.0
    scores = []
    for dim in dimensions:
        score_value = dim["score"]
        scores.append(score_value)
        weight = lookup.get(str(dim.get("name", "")).strip().casefold(), 1.0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight < 0:
            weight = 1.0
        weighted_sum += score_value * weight
        applied += weight

    if applied > 0:
        return weighted_sum / applied
    return sum(scores) / len(scores) if scores else 0.0


def score(rubric: str, transcript: str, workspace_diff: str, *,
         model: str | None = None, timeout: int = 120,
         weights: dict[str, float] | None = None) -> dict:
    """Return {"dimensions": [{"name", "score", "rationale"}], "overall": float}.

    Runs a second headless `claude -p` call whose prompt embeds the rubric,
    transcript, and diff, and demands JSON-only output. Raises RuntimeError if
    the CLI call itself fails or produces unparseable outer JSON (timeout,
    nonzero exit, invalid JSON) — this is NOT caught here; callers must catch
    it and record a judge error rather than crash the run. Raises ValueError
    if the judge's own response doesn't match the required shape.

    `weights` maps dimension name -> weight. When a non-empty mapping is
    given, `overall` is recomputed as the weighted mean of the returned
    dimension scores and the judge's OWN `overall` is ignored — the model is
    trusted to score dimensions, not to do the arithmetic, and letting it
    self-report would silently defeat the weighting. Without weights (None or
    empty) the historical behaviour is unchanged: the judge's `overall` if it
    is numeric, else the unweighted mean.
    """
    judge_prompt = _build_prompt(rubric, transcript, workspace_diff)
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", judge_prompt,
          "--output-format", "json", "--permission-mode", "bypassPermissions"]
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"judge CLI call timed out after {timeout}s") from e

    if result.returncode != 0:
        raise RuntimeError(
            f"judge CLI call failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"judge CLI produced invalid JSON: {result.stdout[:500]!r}: {e}"
        ) from e

    judge_text = data.get("result", "")
    parsed = _extract_json(judge_text)

    if not isinstance(parsed, dict) or not isinstance(parsed.get("dimensions"), list):
        raise ValueError(f"judge output missing/malformed 'dimensions': {judge_text!r}")

    scores = []
    for dim in parsed["dimensions"]:
        if not isinstance(dim, dict) or not all(k in dim for k in _REQUIRED_DIM_KEYS):
            raise ValueError(f"judge dimension malformed: {dim!r}")
        scores.append(dim["score"])

    if weights:
        parsed["overall"] = _weighted_overall(parsed["dimensions"], weights)
    elif not isinstance(parsed.get("overall"), (int, float)):
        parsed["overall"] = sum(scores) / len(scores) if scores else 0.0

    return parsed
