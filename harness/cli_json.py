"""Normalize the two JSON output shapes of the headless CLI."""


def normalize_cli_result(decoded: object) -> dict:
    """Return the result object from an object or a message array.

    Error details describe only the shape, never the CLI's response content.
    """
    if isinstance(decoded, dict):
        return decoded
    if not isinstance(decoded, list) or any(
            not isinstance(item, dict) for item in decoded):
        raise ValueError("CLI JSON must be an object or an array of objects")
    results = [item for item in decoded if item.get("type") == "result"]
    if len(results) != 1:
        raise ValueError("CLI JSON array must contain exactly one result object")
    return results[0]
