"""When a routine fire that has delivered nothing is lost, per mode.

The eval runner routine stops itself at a per-mode limit (its prompt's
"Limits:" sentence; the routine reads docs/routine/eval-runner-instructions.md).
A fire still without results at that limit plus DEADLINE_MARGIN can no
longer deliver: the planner calls it empty and plans the cell again, so a
lost fire is re-fired within the hour, not after a fixed two hours (Adam,
2026-11-03: "so in the future it won't require special detection and
intervention"). test/issues/test_issue_fire_deadlines.py ties MODE_LIMITS to
the prompt file, so the two cannot drift apart.
"""

from __future__ import annotations

from datetime import timedelta

#: The routine prompt's own stop, per fire mode.
MODE_LIMITS = {
    "eval": timedelta(minutes=30),
    "scaffold": timedelta(minutes=30),
    "improve": timedelta(minutes=90),
    "guidance-improve": timedelta(minutes=90),
    "draft": timedelta(minutes=60),
}

#: Session start, the push and the ingest after the routine's own stop.
DEADLINE_MARGIN = timedelta(minutes=10)


def deadline(mode: str) -> timedelta:
    """How long after its start a `mode` fire with no results is lost."""
    return MODE_LIMITS[mode] + DEADLINE_MARGIN
