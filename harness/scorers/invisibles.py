"""Invisible-character folding, shared by two callers that must agree.

`objective` scores the agent's reply against the fixture's patterns and
decides provenance over it; `judge` renders every draft for the pairwise
prompt. A character one of them folds and the other does not is a character
that reads as nothing to the judge and as something to the objective column,
on the same draft — so there is one implementation and both import it.

It used to be an ENUMERATION on each side, kept in step by a test comparing
the two patterns. The enumeration was the defect: measured on the merged
tree, it named 20 of Unicode's 163 `Cf` code points and 20 of its 1,950
`Mn` ones, so a paste salted with a bidi override (U+202A-U+202E), a
directional isolate (U+2066-U+2069), a TAG character (U+E0000-U+E007F), a
supplementary variation selector (U+E0100-U+E01EF), a musical format
control (U+1D173-U+1D17A), an interlinear annotation mark (U+FFF9-U+FFFB)
or a Hangul filler walked past both — one such character inside `leverage`
switched the avoid-list ban off, and one mid-word in a pasted seed sentence
defeated provenance. All three `adam-writing-style` fixture headers assert
that a paste "salted with invisibles" is covered, so the enumeration was
also a documented property that was false.

The rule is a rule now, not a list:

1. **NFKC first.** Compatibility normalisation folds the width and ligature
   variants of a word onto the word itself, and — the part that matters
   here — it COMPOSES a base letter and its combining mark into the single
   precomposed character, so the acute in `cafe` + U+0301 becomes `café`
   and survives step 2 as an ordinary letter. Without it, dropping `Mn`
   would take the accent off every genuinely accented word.
2. **Then every `Cf` and every `Mn` code point goes.** That is the whole
   format-control and non-spacing-mark space, not a sample of it: whatever
   a future Unicode release adds to either category is covered the day the
   interpreter's tables carry it.
3. **Plus the handful that render as nothing without being either**: the
   Hangul fillers (`Lo`), the Braille pattern blank (`So`) — none of which
   `\\s` matches — and a stray NUL (`Cc`), which is not a control anybody
   types but is what an arm that produced nothing sometimes hands back.

What is deliberately NOT dropped: anything with a width. A confusable — a
Cyrillic `а` standing in for a Latin `a` — is a different letter, not an
invisible one, and NFKC does not map confusables onto each other. See the
`strip_seed` header in `evals/adam-writing-style/recruiter-reply/
fixture.yaml` for where that lands.
"""

from __future__ import annotations

import unicodedata

# Renders as nothing, categorised as something else. The Hangul fillers are
# `Lo` and the Braille pattern blank is `So`, so neither the category rule
# below nor `\s` touches them; NUL is `Cc`, and a draft of nothing but one
# used to pass the judge's non-empty guard.
ZERO_WIDTH_OTHERS = "ᅟᅠㅤﾠ⠀\x00"

# The two categories that carry no width by definition: format controls and
# non-spacing marks.
INVISIBLE_CATEGORIES = ("Cf", "Mn")

# `unicodedata.category` is a call per character and this runs over whole
# seed files; the answer depends on nothing but the character.
_DECIDED: dict[str, bool] = {}


def _drops(char: str) -> bool:
    verdict = _DECIDED.get(char)
    if verdict is None:
        verdict = (char in ZERO_WIDTH_OTHERS
                   or unicodedata.category(char) in INVISIBLE_CATEGORIES)
        _DECIDED[char] = verdict
    return verdict


def fold(text: str) -> str:
    """`text` NFKC-normalised, with every zero-width code point removed.

    The one function both `objective` and `judge` fold with. Applied to the
    agent's reply, to every draft the judge is shown, and to the seed files
    the provenance index is built from — a paste salted with an invisible
    the index was not salted with would otherwise not be a run of anything.
    """
    if not text:
        return ""
    return "".join(char for char in unicodedata.normalize("NFKC", text)
                   if not _drops(char))
