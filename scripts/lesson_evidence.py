#!/usr/bin/env python3
"""Per-skill evidence counts from the session miner's lesson proposals.

https://github.com/Adam-S-Daniel/skills-evals/issues/657: the miner
(scripts/mine_sessions.py) writes one proposal per subject and kind to
adam-agentskills-private's `persistent/lessons` branch,
`lessons/proposals/<YYYY-MM-DD>/<subject>__<kind>.json` (schema in that
repository's lessons/README.md). Each day's directory is a full snapshot, so
only the newest one is read; older days are history.

Two kinds are read here, as a ranking signal only:

* `fixture-candidate` steers scripts/scaffold_real_work.py `pick` (the
  fixture-supply lane) toward real-work candidates for a skill that failed
  in real sessions;
* `skill-edit` boosts that skill's improve candidate in scripts/plan_week.py.

Nothing else from a proposal is used: no excerpt, example, repo name or id
leaves this module, only `{skill basename: evidence_count}` for subjects of
the form `skill:<basename>`. Proposals are untrusted data (a bot-written
branch): a file that is a symlink, oversized, not strict JSON or off the
schema is skipped. The callers keep only names they would publish anyway
(public skills), so a private skill's name never reaches a public output.

The other kinds have other readers: `new-skill` is scripts/draft_new_skill.py's,
`agent-check` _agent-guidance's fleet worker's (its ADR 0027), and
`memory-note` and `guidance-edit` belong to _agent-guidance's memory
curation, which does not read them yet (#657).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

#: The proposal kinds this module reads.
KINDS = ("fixture-candidate", "skill-edit")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
#: A skill subject: `skill:` and a skill directory basename.
SKILL_SUBJECT_RE = re.compile(r"skill:(?P<name>[a-z0-9][a-z0-9-]{0,63})")
MAX_FILE = 64 * 1024
MAX_EVIDENCE = 10 ** 6


def newest_day(proposals: Path) -> Path | None:
    """The newest `<YYYY-MM-DD>/` directory under `proposals`, or None."""
    try:
        days = sorted(p for p in proposals.iterdir()
                      if p.is_dir() and not p.is_symlink() and DATE_RE.fullmatch(p.name))
    except OSError:
        return None
    return days[-1] if days else None


def skill_evidence(proposals: Path | None, kind: str) -> dict[str, int]:
    """`{skill: evidence_count}` from the newest day's proposals of `kind`
    whose subject is a skill. Empty when `proposals` is None or unreadable."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    day = newest_day(proposals) if proposals is not None else None
    if day is None:
        return {}
    out: dict[str, int] = {}
    for path in sorted(day.glob(f"*__{kind}.json")):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, RecursionError):
            continue
        if not isinstance(doc, dict) or doc.get("schema_version") != 1 \
                or doc.get("kind") != kind or not isinstance(doc.get("subject"), str):
            continue
        match = SKILL_SUBJECT_RE.fullmatch(doc["subject"])
        count = doc.get("evidence_count")
        if match is None or type(count) is not int or not 1 <= count <= MAX_EVIDENCE:
            continue
        out[match["name"]] = max(out.get(match["name"], 0), count)
    return out
