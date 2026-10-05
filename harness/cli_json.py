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


# Paths in a CLI diagnostic: a quoted absolute path (spaces allowed), a
# file:// URL, a ~/ path, a Windows drive path, then a bare absolute path.
_PATH_PATTERNS = (
    (re.compile(r"(['\"`])(?:/|~/|[A-Za-z]:[\\/])[^'\"`\n]*\1"), r"\1<path>\1"),
    (re.compile(r"file:///?[^\s'\"`]*"), "<path>"),
    (re.compile(r"(?<![\w/.-])~/[^\s'\"`]*"), "<path>"),
    (re.compile(r"(?<![\w])[A-Za-z]:\\[^\s'\"`]*"), "<path>"),
    (re.compile(r"(?<![\w:/.-])/(?:[\w.@+-]+/)+[\w.@+-]*"), "<path>"),
)
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
        text = redact_paths(text)
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


# ---------------------------------------------------------------------------
# Tool-call trace (#89). `raw.json` keeps only the result objects, so a run's
# tool calls were invisible after the fact. `tool_trace` keeps a compact,
# bounded, redacted line per tool call and per tool result, written beside
# raw.json as `transcripts/tool_trace.json`. That directory is gitignored and
# never committed to `persistent/eval-results`, but eval.yml uploads the whole
# `results/` tree as a workflow artifact, which on a public repository anyone
# signed in can download, so every string is redacted before it is kept.

TOOL_TRACE_SCHEMA_VERSION = 1
#: Characters kept of a tool call's input summary and of a tool result.
TRACE_INPUT_CHARS = 200
TRACE_OUTPUT_CHARS = 300
TRACE_NAME_CHARS = 100
#: Hard cap on the serialized events of one trial (every CLI call of one arm
#: run). Events past it are counted in `omitted_events`, never kept.
TRACE_MAX_BYTES = 64 * 1024
#: Redaction reads this much of a string before it is truncated, so a secret
#: that starts inside the kept head is seen whole.
_REDACT_WINDOW = 4096
#: A tool-use id, kept only when it has this shape (it pairs calls with
#: results); anything else is dropped rather than echoed.
_TOOL_USE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
#: Input keys that name what a call did, most telling first; an input with
#: none of them is summarized as its JSON.
_INPUT_KEYS = ("command", "file_path", "path", "pattern", "url", "query",
               "skill", "subagent_type", "description", "prompt")

REDACTED = "<redacted>"
# Environment variable names whose values are credentials.
_SECRET_NAME = re.compile(
    r"(?i)(token|secret|passw(or)?d|api_?key|access_?key|private_?key|"
    r"credential|auth|cookie|session)")
#: Shapes of credentials, wherever they appear.
_SECRET_PATTERNS = (
    (re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?"
                r"(?:-----END[A-Z ]*PRIVATE KEY-----|\Z)"), REDACTED),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), REDACTED),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
     REDACTED),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), REDACTED),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), REDACTED),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"),
     REDACTED),
    (re.compile(r"(?i)\b(authorization\s*:\s*(?:bearer|token|basic)\s+)\S+"),
     r"\1" + REDACTED),
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{16,}"), r"\1" + REDACTED),
    # NAME=value / "name": "value" where the name says credential: `env`
    # output, an export, a config file read back.
    (re.compile(r"(?i)\b([A-Za-z0-9_.-]*(?:token|secret|passw(?:or)?d|api_?key|"
                r"access_?key|private_?key|credential|auth|cookie)[A-Za-z0-9_.-]*"
                r"[\"']?\s*[=:]\s*[\"']?)[^\s\"',;}]+"),
     r"\1" + REDACTED),
)


def secret_values(*environments: dict) -> list[str]:
    """The values of every credential-named variable in `environments`,
    longest first, so one never leaves a tail of another behind. Values
    shorter than 8 characters are skipped: replacing `1` or `true` everywhere
    would only destroy the trace."""
    found = {value for env in environments for name, value in env.items()
             if isinstance(value, str) and len(value) >= 8
             and _SECRET_NAME.search(name)}
    return sorted(found, key=len, reverse=True)


def redact_paths(text: str) -> str:
    """Absolute paths replaced with `<path>` (the patterns above)."""
    for pattern, replacement in _PATH_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact(text: str, secrets: list[str] = ()) -> str:
    """`text` with known secret values, credential shapes and absolute paths
    replaced."""
    for value in secrets:
        text = text.replace(value, REDACTED)
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return redact_paths(text)


def _clip(text: str, limit: int, secrets: list[str]) -> str:
    """Redact the head of `text`, then cut it to `limit` characters."""
    kept = redact(text[:_REDACT_WINDOW], secrets)
    return kept if len(kept) <= limit else kept[:limit] + "..."


def _input_summary(value: object) -> str:
    if isinstance(value, dict):
        for key in _INPUT_KEYS:
            if isinstance(value.get(key), str):
                return value[key]
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return ""


def _result_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block.get("text", "") for block in content
                         if isinstance(block, dict)
                         and isinstance(block.get("text"), str))
    return ""


def _tool_use_id(value: object) -> str | None:
    return value if isinstance(value, str) and _TOOL_USE_ID.fullmatch(value) else None


def tool_events(decoded: object, secrets: list[str] = ()) -> list[dict]:
    """One redacted, truncated event per tool call and per tool result in a
    `--verbose` message array, in order. A single result object (no
    `--verbose`) has none. Never raises on an unexpected shape: a message or
    block that is not what the CLI documents is skipped."""
    if not isinstance(decoded, list):
        return []
    events = []
    for message in decoded:
        if not isinstance(message, dict) or message.get("type") not in (
                "assistant", "user"):
            continue
        body = message.get("message")
        content = body.get("content") if isinstance(body, dict) else None
        if not isinstance(content, list):
            continue
        subagent = message.get("parent_tool_use_id") is not None
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                summary = _input_summary(block.get("input"))
                name = block.get("name")
                events.append({
                    "kind": "tool_use",
                    "id": _tool_use_id(block.get("id")),
                    "name": _clip(name if isinstance(name, str) else "",
                                  TRACE_NAME_CHARS, secrets),
                    "input": _clip(summary, TRACE_INPUT_CHARS, secrets),
                    "input_chars": len(summary),
                    "subagent": subagent})
            elif block.get("type") == "tool_result":
                text = _result_text(block.get("content"))
                events.append({
                    "kind": "tool_result",
                    "id": _tool_use_id(block.get("tool_use_id")),
                    "is_error": block.get("is_error") is True,
                    "output": _clip(text, TRACE_OUTPUT_CHARS, secrets),
                    "output_chars": len(text),
                    "subagent": subagent})
    return events


def bounded_tool_trace(calls: list[list[dict]],
                       max_bytes: int = TRACE_MAX_BYTES) -> dict:
    """The `tool_trace.json` document for one trial: each CLI call's events
    (`tool_events`), tagged with the call's index (0 is the prompt, then each
    follow-up), kept in order until their serialized size would pass
    `max_bytes`; the rest are only counted."""
    events, size, omitted = [], 0, 0
    for index, call in enumerate(calls):
        for event in call:
            event = {"call": index, **event}
            cost = len(json.dumps(event).encode("utf-8"))
            if omitted or size + cost > max_bytes:
                omitted += 1
                continue
            size += cost
            events.append(event)
    return {
        "schema_version": TOOL_TRACE_SCHEMA_VERSION,
        "limits": {"input_chars": TRACE_INPUT_CHARS,
                   "output_chars": TRACE_OUTPUT_CHARS,
                   "max_bytes": max_bytes},
        "calls": len(calls),
        "events": events,
        "omitted_events": omitted,
    }
