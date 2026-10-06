"""The answer-leak lint for real-work fixtures, and `interface_strings:`.

A real-work fixture's task text is the issue its pull request closed. Some of
those issues were edited after the fix and describe or quote it, so the task
text must not carry any run of four or more consecutive words that also
appears in a line the merged diff added (the same four-word rule #98 applies
to a guidance section). Words are lowercase letter and digit runs: the rule is
lexical, so a regex is the right tool here.

A hidden test sometimes checks an exact identifier or message (a status name,
an exported function, an `::error::` text). The task text has to name it, or
no fix can pass however correct. Each fixture declares those strings in
`interface_strings:` (Adam, 2026-10-06: "Exempt interface strings"), and a
four-word run made only of one declared string's own consecutive words is
not a leak. Everything else in the task text is held to the rule.
"""

from __future__ import annotations

import re

import guidance

RUN_WORDS = 4
KEY = "interface_strings"
MAX_STRINGS = 32
MAX_STRING_CHARS = 200
_WORD_RE = re.compile(r"[a-z0-9]+")


def words(text: str) -> list[str]:
    return _WORD_RE.findall(text.casefold())


def _runs(tokens: list[str]) -> list[tuple[str, ...]]:
    return [tuple(tokens[i:i + RUN_WORDS]) for i in range(len(tokens) - RUN_WORDS + 1)]


def added_lines(patch: str) -> list[str]:
    """The lines a unified diff adds, without the `+` and without file headers."""
    return [line[1:] for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")]


def leaked_runs(prompt: str, answer: str, interface_strings=()) -> list[str]:
    """Every four-word run of `prompt` that `answer` also contains, in prompt
    order and once each, except runs inside one declared interface string.

    `answer` is the merged diff's added text. A run is matched within one
    added line, so two unrelated lines never join into a phrase.
    """
    answer_runs = {run for line in answer.splitlines() for run in _runs(words(line))}
    exempt = {run for text in interface_strings for run in _runs(words(text))}
    found: list[str] = []
    for run in _runs(words(prompt)):
        text = " ".join(run)
        if run in answer_runs and run not in exempt and text not in found:
            found.append(text)
    return found


def validate_fixture(fixture: dict, fixture_path) -> None:
    """`interface_strings:` is absent, or a list of 1-32 nonblank strings."""
    if KEY not in fixture:
        return
    value = fixture[KEY]
    if (not isinstance(value, list) or not 1 <= len(value) <= MAX_STRINGS
            or any(not isinstance(item, str) or not item.strip()
                   or len(item) > MAX_STRING_CHARS for item in value)):
        raise guidance.GuidanceError(
            f"{fixture_path}: `{KEY}:` must be a list of 1 to {MAX_STRINGS} "
            f"nonblank strings of at most {MAX_STRING_CHARS} characters: the "
            "identifiers and messages a hidden test checks verbatim")
