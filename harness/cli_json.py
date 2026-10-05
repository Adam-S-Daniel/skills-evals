"""Normalize the JSON output shapes of the headless CLI."""

import json
import re


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _sum_values(values: list) -> object:
    """Add numbers, merge dicts key by key and join lists; else the last value."""
    present = [v for v in values if v is not None]
    if present and all(_is_number(v) for v in present):
        return sum(present)
    if present and all(isinstance(v, dict) for v in present):
        keys = list(dict.fromkeys(k for v in present for k in v))
        return {k: _sum_values([v[k] for v in present if k in v]) for k in keys}
    if present and all(isinstance(v, list) for v in present):
        return [item for v in present for item in v]
    return values[-1] if values else None


def normalize_cli_result(decoded: object) -> dict:
    """Return the result object from an object or a message array.

    One headless invocation can end more than one turn: an agent that starts a
    background subagent answers, then answers again when the subagent's
    task-notification arrives, and the array carries one `type: result` object
    per turn (`result_index` 0, 1, ...; Claude Code 2.1.289). The agent's
    answer is the text of all of them, in order, so several results are
    merged:

    * `result` is their texts joined by a blank line;
    * `is_error` is true if any of them is;
    * `num_turns`, `duration_ms`, `duration_api_ms` and the numeric fields of
      `usage` are per turn on the CLI, so they are summed (lists such as
      `usage.iterations` are joined in turn order);
    * `total_cost_usd` and `modelUsage` are cumulative on the CLI ("read the
      latest result rather than summing"), so the last result's are kept,
      like every other field;
    * `merged_results` records the count.

    Zero results is still an error.

    Error details describe only the shape, never the CLI's response content.
    """
    if isinstance(decoded, dict):
        return decoded
    if not isinstance(decoded, list) or any(
            not isinstance(item, dict) for item in decoded):
        raise ValueError("CLI JSON must be an object or an array of objects")
    results = [item for item in decoded if item.get("type") == "result"]
    if not results:
        raise ValueError(
            "CLI JSON array must contain a result object (found 0)")
    if len(results) == 1:
        return results[0]
    merged = dict(results[-1])
    texts = [r.get("result") for r in results]
    merged["result"] = "\n\n".join(t for t in texts if isinstance(t, str) and t)
    merged["is_error"] = any(r.get("is_error") for r in results)
    for key in ("num_turns", "duration_ms", "duration_api_ms", "usage"):
        if any(key in r for r in results):
            merged[key] = _sum_values([r.get(key) for r in results])
    merged["merged_results"] = len(results)
    return merged


_ABSOLUTE_PATH = re.compile(r"(?<![\w:/.-])/(?:[\w.@+-]+/)+[\w.@+-]*")
_SUBTYPE = re.compile(r"[A-Za-z0-9_]{1,40}")


def failed_run_detail(stdout: str, stderr: str, limit: int = 300) -> str:
    """A bounded, content-free description of a CLI run that exited non-zero.

    Detail strings reach `summary.json` and `report.md` on the public results
    branch. With `--verbose` the failing run's stdout is the whole message
    array (cwd, tool and connector names, every tool call and its output), so
    stdout is never echoed. stderr is the CLI's own diagnostics: the first
    `limit` characters with absolute paths replaced. With no stderr the detail
    is the shape of stdout: the result's subtype and error flag when it parses,
    else its length.
    """
    text = stderr.strip()
    if text:
        text = _ABSOLUTE_PATH.sub("<path>", text)
        return text if len(text) <= limit else text[:limit] + "..."
    try:
        result = normalize_cli_result(json.loads(stdout))
    except (ValueError, TypeError):
        return f"stdout {len(stdout)} chars"
    subtype = result.get("subtype")
    parts = []
    if isinstance(subtype, str) and _SUBTYPE.fullmatch(subtype):
        parts.append(f"result subtype {subtype}")
    if isinstance(result.get("is_error"), bool):
        parts.append(f"is_error {str(result['is_error']).lower()}")
    return ", ".join(parts) or f"stdout {len(stdout)} chars"
