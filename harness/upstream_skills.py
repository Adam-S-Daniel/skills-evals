#!/usr/bin/env python3
"""Skills made by Anthropic, which the self-improvement loop never touches.

Adam's decision of 2026-11-03: no loop evaluates, improves, trims, retires or
drafts an Anthropic skill, whether one of the claude.ai account skills
(synced as `anthropic-skills:<name>`) or one bundled in Claude Code, and the
draft loop never creates a skill that duplicates one. The names are data in
`harness/upstream_skills.yml`; this module loads and checks that file and
answers one question about a name. The draft loop's guards
(`scripts/draft_new_skill.py`) and the rule test
(`test/issues/test_issue_upstream_skills.py`) are its callers.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent / "upstream_skills.yml"
GROUPS = ("anthropic_account", "claude_code_bundled")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load(path: Path = DEFAULT_PATH) -> dict[str, frozenset[str]]:
    """The file's two groups as frozensets; ValueError on any other shape."""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or set(doc) != {"schema", *GROUPS}:
        raise ValueError(f"upstream skills: not exactly schema and {list(GROUPS)}")
    if doc["schema"] != 1 or type(doc["schema"]) is not int:
        raise ValueError("upstream skills: schema is not 1")
    out: dict[str, frozenset[str]] = {}
    for group in GROUPS:
        names = doc[group]
        if not isinstance(names, list) or not all(
                isinstance(n, str) and NAME_RE.fullmatch(n) for n in names):
            raise ValueError(f"upstream skills: {group} is not a list of skill names")
        if len(set(names)) != len(names):
            raise ValueError(f"upstream skills: {group} repeats a name")
        if names != sorted(names):
            raise ValueError(f"upstream skills: {group} is not sorted")
        out[group] = frozenset(names)
    return out


def upstream_source(name: str,
                    lists: dict[str, frozenset[str]] | None = None) -> str | None:
    """`anthropic_account`, `claude_code_bundled` or None for a skill name.

    Takes the bare name or a prefixed one (`anthropic-skills:pdf`): everything
    up to the last `:` is dropped. The account list is checked first.
    """
    lists = load() if lists is None else lists
    bare = name.rsplit(":", 1)[-1]
    for group in GROUPS:
        if bare in lists[group]:
            return group
    return None
