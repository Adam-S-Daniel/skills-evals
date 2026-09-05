"""Hard-wrap reconstruction, shared by two callers that must agree.

`judge._normalize_draft_text` levels every draft to one line shape before the
judge sees it, and `objective.strip_seed_material` decides provenance a
SENTENCE at a time. Both first have to answer the same question: which line
breaks did the writer MEAN, and which did a wrap column put there? A wrap is
not a fact in the text — it has to be reconstructed — and two
reconstructions that disagreed would put the judge and the objective column
on different readings of the same draft, so there is one implementation and
both import it.
"""

from __future__ import annotations

import re
import statistics

LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s")
# A Markdown table row: a leading `|` with something after it. A row is a
# deliberate line, never a wrap — the writer ended it because the row ended.
TABLE_ROW_RE = re.compile(r"^\s*\|.*\S")

# The shortest column anybody hard-wraps prose at. A pooled sample under this
# is not measuring a wrap; it is measuring deliberate short lines — a
# sign-off, a run of one-sentence lines, an address block — and using it as
# the column would join lines the writer meant to break.
MIN_WRAP_COLUMN = 40

# A paragraph shows evidence of having been wrapped only once it runs to
# three lines: two could be a sign-off ("Thanks," / "Adam Daniel") or a
# heading and its one-line body, and pooling those in put the sign-off's own
# 7-character line into the sample.
WRAP_EVIDENCE_LINES = 3


def paragraphs(lines: list[str]) -> list[list[str]]:
    """`lines` grouped into blank-line-delimited paragraphs."""
    out: list[list[str]] = []
    block: list[str] = []
    for line in lines:
        if line.strip():
            block.append(line)
        elif block:
            out.append(block)
            block = []
    if block:
        out.append(block)
    return out


def wrap_width(blocks: list[list[str]]) -> float:
    """The draft's estimated wrap column.

    The median non-final line of every paragraph that runs to at least
    `WRAP_EVIDENCE_LINES` lines. Three properties are needed and no single
    statistic over every line has all three:

    - **Robust to one long line.** The column used to be the draft's longest
      line, so a single unbreakable URL — and the skill under test tells the
      writer to hyperlink — became the width, no line looked wrapped any
      more, and the unwrap switched itself off for that draft alone. A
      median ignores it.
    - **Not fooled by a short paragraph.** A two-line sign-off is not
      evidence of a wrap. Pooling every non-final line in the draft made it
      evidence: a model-shaped draft (one long line per paragraph) has the
      sign-off's `Thanks,` as its ONLY sample, the median came out at 7, and
      the sign-off was joined — deterministically, on every trial, in the
      agent's draft alone, on a dimension the rubric scores.
    - **Usable when nothing was wrapped at all.** With no qualifying
      paragraph there is nothing to join, so the width falls back to the
      draft's longest line rather than to zero.

    The same fallback catches a sample that is real but implausible as a
    column: a paragraph of deliberate one-line sentences is three lines
    long and pools a median well under `MIN_WRAP_COLUMN`, and joining on it
    would erase breaks the writer made.
    """
    sample = [len(line) for block in blocks
              if len(block) >= WRAP_EVIDENCE_LINES
              for line in block[:-1]]
    longest = max((len(line) for block in blocks for line in block), default=0)
    if not sample:
        return longest
    width = statistics.median(sample)
    return max(width, longest) if width < MIN_WRAP_COLUMN else width


def unwrap_block(lines: list[str], width: float) -> list[str]:
    """One paragraph's lines, with hard wrapping — and only that — undone.

    A line is a continuation of the one above it when the line above was too
    full for this line's first word to have fitted on it. That is what hard
    wrapping IS, and `width` is the estimated wrap column: the ragged last
    line of a wrapped paragraph ("than through a form.") is just as short as
    a sign-off, and only reconstructing the wrap tells them apart — the line
    above a ragged tail is full, the line above a sign-off is not.

    A line that STARTS a list item or a table row is never joined into the
    line above it, and nothing is joined into a table row: a list can follow
    a full line ("...easiest to see as a list:") and a row ends because the
    row ended. A list item's OWN continuation line is joined, though: it
    used not to be, and a hard-wrapped list therefore normalised to twice as
    many lines as its unwrapped twin — the exact line-shape tell this
    reconstruction exists to remove, surviving inside every draft that uses
    a list.

    Joined lines are collected and joined once at the end rather than
    appended onto a growing string: `out[-1] += ...` is quadratic in the
    paragraph's length, and a 12 MB draft took 94 seconds in it.
    """
    joined: list[list[str]] = [[lines[0]]]
    for previous, line in zip(lines, lines[1:]):
        first_word = line.split(" ", 1)[0]
        wrapped = len(previous) + 1 + len(first_word) > width
        if (wrapped and not LIST_ITEM_RE.match(line)
                and not TABLE_ROW_RE.match(line)
                and not TABLE_ROW_RE.match(previous)):
            joined[-1].append(line)
        else:
            joined.append([line])
    return [" ".join(part) for part in joined]
