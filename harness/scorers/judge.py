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


def score(rubric: str, transcript: str, workspace_diff: str, *,
         model: str | None = None, timeout: int = 120) -> dict:
    """Return {"dimensions": [{"name", "score", "rationale"}], "overall": float}.

    Runs a second headless `claude -p` call whose prompt embeds the rubric,
    transcript, and diff, and demands JSON-only output. Raises RuntimeError if
    the CLI call itself fails or produces unparseable outer JSON (timeout,
    nonzero exit, invalid JSON) — this is NOT caught here; callers must catch
    it and record a judge error rather than crash the run. Raises ValueError
    if the judge's own response doesn't match the required shape.
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

    if not isinstance(parsed.get("overall"), (int, float)):
        parsed["overall"] = sum(scores) / len(scores) if scores else 0.0

    return parsed
