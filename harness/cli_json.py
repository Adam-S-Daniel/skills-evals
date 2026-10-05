"""Normalize the JSON output shapes of the headless CLI."""


def normalize_cli_result(decoded: object) -> dict:
    """Return the result object from an object or a message array.

    One headless invocation can end more than one turn: an agent that starts a
    background subagent answers, then answers again when the subagent's
    task-notification arrives, and the array carries one `type: result` object
    per turn (`result_index` 0, 1, ...; seen on Claude Code 2.1.289). The
    agent's answer is the text of all of them, in order, so several results
    are merged: `result` is their texts joined by a blank line, `is_error` is
    true if any of them is, `merged_results` records the count, and every
    other field (cost, usage, turns, duration, model usage) is the last
    result's, which the CLI reports cumulatively. Zero results is still an
    error.

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
    merged["merged_results"] = len(results)
    return merged
