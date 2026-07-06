"""LLM-as-judge scoring — STUB.

Interface is settled; implementation is deliberately deferred until the open
decisions in DESIGN.md (judge model, invocation mechanism) are confirmed.

The judge receives the fixture's rubric, the agent transcript, and the diff of
the workspace, and must return per-dimension scores with rationales as JSON.
"""

from __future__ import annotations


def score(rubric: str, transcript: str, workspace_diff: str) -> dict:
    """Return {"dimensions": [{"name", "score", "rationale"}], "overall": float}.

    Planned implementation: a single Claude call (temperature 0) with a JSON
    schema-constrained response. See DESIGN.md — "Open decisions".
    """
    raise NotImplementedError(
        "LLM judge not wired yet — run with --arm objective-only. See DESIGN.md."
    )
