"""Application settings."""

DEFAULTS: dict[str, object] = {"port": 8080, "debug": False}


def merged(overrides: dict[str, object]) -> dict[str, object]:
    """Return the defaults with overrides applied."""
    return {**DEFAULTS, **overrides}
