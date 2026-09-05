#!/usr/bin/env python3
"""Compute the model roster: which models this harness runs against today.

A PURE FUNCTION OVER FILES. `compute_roster()` takes already-parsed documents
and a frozen `now`, and returns the roster dict — no network, no clock, no
environment. The one network call in the whole feature lives in
`scripts/refresh_models.py`, which produces this module's `models_doc`.

Inputs
  models_doc   {"fetched_at": ..., "models": [{id, created_at, ...}, ...]} —
               availability, straight from GET /v1/models.
  census_doc   {"generated_at": ..., "weeks": [...], "counts": {model: {week: n}}}
               — usage, published to `eval-results` as usage/latest.json by
               scripts/model_usage_census.py. Optional: absent, older than the
               policy's freshness window, dated in the future, or empty over
               the window, and the roster falls back to "newest per tier" and
               says which of those it was in every reason.
  policy       evals/roster-policy.yml — every threshold, plus the tier ladder.
  previous     the last published roster, for added/retired-since-last.

TWO OF THOSE THREE COME OFF A PUBLIC BRANCH, written by other jobs on other
machines. They are inputs, not invariants: an entry without a string `id`, a
count that is not a number, a `previous.arms` entry that is not a dict — each
is skipped with a one-line named message, never a traceback, and never with
the offending value echoed into a public log.

Output — roster/latest.json on `eval-results`:
  {generated_at, source: {models_api_at, census_at, admin_report_at},
   arms: [{id, reason}], judge: {id, reason, is_arm}, preflight: {id, reason},
   unranked: [{id, reason}], excluded: [{id, reason}],
   compared_to_previous: bool, previous_state: "compared"|"none"|"unavailable",
   retired_since_last: [...], added_since_last: [...],
   catalogue_seen: [{id, last_seen}, ...]}

`catalogue_seen` is read back next run as `previous`'s own field of the same
name (property 5, DESIGN.md) — it round-trips through this same untrusted
branch, aged and capped; see `_update_catalogue_seen`.

Every entry carries its reason IN WORDS. The explorer tool renders them, and a
roster nobody can explain is one nobody will override when it is wrong.
`judge.is_arm` is the one thing a reason cannot carry: the runner has to refuse
a judge that is also an arm, and it cannot do that by reading prose.

NO MODEL ID APPEARS IN THIS FILE. Tier comes from the family word in the id
itself, matched against the ladder in roster-policy.yml.

This module must never read the environment, and must print nothing to
stdout but `render_summary`'s Markdown (N7, #129 review round 7). Neither
rule is visible from inside this file, which is why they are written here.
eval.yml's roster step exports the Models API bearer for
`scripts/refresh_models.py` and runs this module in the SAME shell, so that
credential IS in this process's environment even though nothing here wants
it; and that step's stdout goes to `$GITHUB_STEP_SUMMARY` and the public
job log, so anything else printed there is published. "A pure function over
files" is the property that makes both rules free to keep.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from timeweeks import parse_ts, window_weeks
from timeweeks import iso_week  # noqa: F401 -- re-exported: identity-checked
                                 # by test_roster_and_census_share_one_week_implementation

# The Models API has no price field, so "cheapest" and "most capable" are both
# read off the tier ladder rather than off a number. Within one tier the newest
# model is taken as the current one — which is true of every tier transition so
# far (a new version supersedes its predecessor at the same or lower price).
# If that ever stops holding, this is the assumption to revisit first.

#: An id that is another id plus a date is a pinned snapshot of it, not a
#: second model. See `alias_map`.
#: `\Z`, not `$`: `$` also matches just before a trailing newline, so a
#: census key `<alias>-YYYYMMDD\n` (a stray newline, not a real snapshot
#: id) folded onto `<alias>` and inflated its measured share — measured:
#: a false ~99.9% instead of a real 50.0% (N9, #129 review round 6).
SNAPSHOT_SUFFIX = re.compile(r"^(?P<base>.+)-[0-9]{8}\Z")


def _stderr(message: str) -> None:
    print(f"roster: {message}", file=sys.stderr)


def load_policy(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


#: Every numeric threshold roster.py reads from evals/roster-policy.yml,
#: with the check each one must pass. A missing, wrong-typed, or negative
#: value used to reach `compute_roster` unchecked and either KeyError deep
#: inside it or silently miscompute (a string threshold, say, compares
#: correctly against nothing) — `_validate_policy` fails loudly, naming the
#: key, before any of that.
_THRESHOLD_CHECKS = {
    "cooling_off_days": lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    "arm_enter_usage_pct": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0,
    "arm_enter_window_weeks": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
    "arm_exit_usage_pct": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0,
    "arm_exit_window_weeks": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
    "census_max_age_days": lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    "min_ranked_turns": lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
    "min_ranked_share": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1,
    "catalogue_seen_max_age_days": lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0,
}


def _valid_tier_rung(rung) -> bool:
    """A rung is a non-empty string, or a non-empty list of non-empty
    strings (peers ranking identically — see `tier_rungs`)."""
    if isinstance(rung, str):
        return bool(rung)
    if isinstance(rung, list):
        return bool(rung) and all(isinstance(word, str) and word for word in rung)
    return False


def validate_policy(policy: dict) -> None:
    """Raise `ValueError`, naming the offending key, for a missing,
    wrong-typed, `None`, or out-of-range threshold, or a malformed
    `tiers` ladder. Called from `main()` before any of
    `evals/roster-policy.yml` reaches `compute_roster`.

    `tiers` is not a numeric threshold, so it lived outside
    `_THRESHOLD_CHECKS` and a missing or malformed one sailed through
    unvalidated (N6, #129 review round 6) — `tier_rungs` then KeyErrored
    on a missing key, or silently misbehaved on a malformed rung, instead
    of failing loudly and by name at the same point every other bad
    threshold does.
    """
    if not isinstance(policy, dict):
        raise ValueError("roster policy is not a mapping")
    for key, check in _THRESHOLD_CHECKS.items():
        if key not in policy:
            raise ValueError(f"roster policy is missing `{key}`")
        if not check(policy[key]):
            raise ValueError(f"roster policy `{key}` is invalid: {policy[key]!r}")
    if "tiers" not in policy:
        raise ValueError("roster policy is missing `tiers`")
    tiers = policy["tiers"]
    if not (isinstance(tiers, list) and tiers and all(_valid_tier_rung(r) for r in tiers)):
        raise ValueError(f"roster policy `tiers` is invalid: {tiers!r}")


def read_json(path: str | Path | None) -> tuple[dict | None, str | None]:
    """(document, problem). Absent is not a problem; unreadable is.

    CI materializes the optional inputs with `git show ... || true`, which
    leaves an EMPTY file behind when the branch or the path does not exist yet
    — the first run, every time. That is a legitimate "not published", not a
    failure, so it must not raise and must not be reported as a problem. A
    file that IS there and cannot be parsed is a different thing, and the
    summary says so rather than claiming nothing was published.
    """
    if path is None:
        return None, None
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        return None, None
    try:
        with open(p, encoding="utf-8") as f:
            document = json.load(f)
    # `RecursionError` as well as the parse/IO errors (N4, #129 review
    # round 7): a deeply nested document — 100k open brackets is enough —
    # exhausts the decoder's stack rather than failing to parse, and used
    # to escape as a traceback carrying the runner's absolute paths, where
    # this module's docstring promises a one-line named message about
    # every untrusted input. `ValueError` covers `json.JSONDecodeError`
    # and `UnicodeDecodeError` (both subclasses) and anything else the
    # decoder raises for a value it cannot represent; both are named
    # anyway, because which one fired is the useful half of the message.
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError,
            RecursionError) as exc:
        return None, f"{p.name} is present but unreadable ({type(exc).__name__})"
    if not isinstance(document, dict):
        return None, f"{p.name} is not a JSON object"
    return document, None


def load_json(path: str | Path | None) -> dict | None:
    """read_json without the problem half, for callers that cannot act on it."""
    return read_json(path)[0]


def tier_rungs(policy: dict) -> list[list[str]]:
    """The capability ladder, weakest rung first, each rung a list of peers.

    A rung is written as a bare family word, or as a list of words that rank
    identically (`[fable, mythos]` — same tier, same price, different access
    programme). Peers matter: a model whose family word the ladder does not
    know is unranked, takes no seat, and — worse — used to sit in the usage
    denominator, shrinking every ranked model's share towards zero.
    """
    rungs: list[list[str]] = []
    for rung in policy["tiers"]:
        words = [rung] if isinstance(rung, str) else list(rung)
        rungs.append([str(word).lower() for word in words])
    return rungs


def tier_words(policy: dict) -> list[str]:
    """Every family word on the ladder, flattened."""
    return [word for rung in tier_rungs(policy) for word in rung]


def rung_of(model_id: str, rungs: list[list[str]]) -> int | None:
    """The model's rung index, from the family word in its own id.

    Token match on `-`, not a substring search: a substring test would let an
    id that merely CONTAINS a family word inside a longer token claim that
    tier. Unrecognised family word -> None -> unranked.
    """
    tokens = set(str(model_id).lower().split("-"))
    for index, rung in enumerate(rungs):
        if tokens.intersection(rung):
            return index
    return None


def rung_label(rungs: list[list[str]], index: int) -> str:
    """What to call a rung in a reason: `opus`, or `fable/mythos` for peers."""
    return "/".join(rungs[index])


#: A SAFETY shape for a previous-arm id, not a "is this a real model" check
#: — that's `rung_of`/`unranked_ids`, applied elsewhere, and deliberately
#: NOT required here: a previous arm whose family word has since left the
#: ladder must still be recognized (and retired FOR that reason) rather
#: than silently dropped as malformed. This shape only excludes what a
#: real id never contains and a control-character injection needs: no
#: newline, no `:`, no other punctuation — see `_clean_previous_arms`.
PREVIOUS_ARM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def alias_map(ids) -> dict[str, str]:
    """{dated snapshot id: the undated alias it pins}, for ids that both exist.

    An id of the form `<alias>-YYYYMMDD` is the same model as `<alias>` with a
    version pinned to it. Left alone the two take two arm seats and split one
    model's usage across two census keys. The collapse only happens when the
    alias is itself present in `ids` — a catalogue that publishes only dated
    ids has no alias to collapse onto, and every one of them stands on its own.
    """
    known = {i for i in ids if isinstance(i, str)}
    mapping: dict[str, str] = {}
    for model_id in sorted(known):
        match = SNAPSHOT_SUFFIX.match(model_id)
        if match and match.group("base") in known:
            mapping[model_id] = match.group("base")
    return mapping


def _usage_alias_map(api_ids, other_ids, seat_aliases: dict,
                     live_order) -> dict[str, str]:
    """{id: the id whose numerator its census turns belong to}, for USAGE.

    B1 (#129 review round 7). Round 6's B1 built ONE wide map,
    `alias_map(api_ids + counts + previous_arms + catalogue_seen)`, and
    `usage_share` used it for the MODEL's own target as well as for census
    keys. A catalogue listing TWO dated snapshots of one base, with the bare
    alias present only in the previous roster's `arms` or `catalogue_seen`,
    then folded BOTH snapshots onto that bare alias: each one's numerator
    collected the other's turns and both were published "carries 100.0%" —
    seating a snapshot on 0.99% of the window, keeping a previous arm with
    no turns of its own instead of retiring it at 0.0%, and consuming the
    last non-arm model so that the judge became an arm and
    `run_eval.select_models` refused every unpinned fixture. No hostile
    input is needed to reach it: a run whose catalogue lists the bare alias
    records it in `catalogue_seen` BY DESIGN, and the next run's own
    published roster is the input that reproduces it.

    The rule, in one line: AN ID THE MODELS API RETURNS THIS RUN IS NEVER
    RE-TARGETED BY THE WIDE MAP.

    1. A live catalogue id's target is its SEAT identity — `seat_aliases`,
       the catalogue-only map. Two catalogue ids the seat map keeps
       distinct therefore always have distinct targets, so their numerators
       are disjoint. (Two snapshots of a bare alias that IS itself in the
       catalogue are NOT kept distinct by the seat map: they are one model,
       one seat and one share, which is what that map is for.)
    2. Every other id — a departed previous arm, a `catalogue_seen` history
       entry, a census key naming neither — folds by the wide map, which is
       what keeps round 6's B1 fixed: a previous arm published under a dated
       id that has since left the API, whose usage the census records under
       the undated alias, still folds onto that alias and still counts in
       the denominator.
    3. One exception to 2, and it is what makes the documented
       dated-snapshot-ONLY catalogue shape work: a bare alias that is NOT
       itself in the catalogue while dated snapshots of it ARE names exactly
       one live model. `live_order` is the run's own capability order
       (weakest and oldest first), so the NEWEST live snapshot claims it —
       the same model that holds the seat. That keeps the whole map a
       FUNCTION: a census key is attributed to at most one live id.

    THREE INVARIANTS, each pinned by a test (A1, #129 review round 8):

    (i)   IDEMPOTENT. Folding a key twice gives what folding it once
          gives, for every key in the domain. Every consumer folds
          exactly once, so a key that needs two hops is a key whose
          turns land somewhere no numerator is looking.
    (ii)  Every VALUE is either a live catalogue id, or a non-live id
          that no live id claims. A value that is both non-live and
          claimed is a census key stranded one hop short of the model
          whose work it is.
    (iii) The numerators PARTITION the attributable denominator: every
          attributable ranked census key is credited to exactly one
          model — a live model, or, for a since-retired id nobody
          claims, itself — so the live models' shares plus the shares
          of unclaimed retired ids come to 100%. "No share sums past
          100%" is the weaker half of this and cannot see turns lost
          from every numerator at once.
    """
    live = {i for i in api_ids if isinstance(i, str)}
    wide = alias_map(list(api_ids) + list(other_ids))
    mapping: dict[str, str] = {}
    for model_id in live:  # (1)
        target = seat_aliases.get(model_id, model_id)
        if target != model_id:
            mapping[model_id] = target
    for model_id in other_ids:  # (2)
        if not isinstance(model_id, str) or model_id in live:
            continue
        target = wide.get(model_id, model_id)
        if target != model_id:
            mapping[model_id] = target
    claimed: dict[str, str] = {}
    for model_id in live_order:  # (3) — last write wins: the newest
        match = SNAPSHOT_SUFFIX.match(model_id)
        if match and match.group("base") not in live:
            claimed[match.group("base")] = model_id
    for base, model_id in claimed.items():
        mapping[base] = seat_aliases.get(model_id, model_id)
    # COMPOSE, and it is invariant (i) that needs it (A1, #129 review
    # round 8). Rules (2) and (3) each move a key ONE hop, and a key can
    # need both: a non-live dated id folds onto its bare alias by (2), and
    # that bare alias folds onward onto the newest live snapshot by (3).
    # Every consumer applies this map exactly once (`aliases.get(candidate,
    # candidate)`), so such a key used to land on the bare alias — which
    # `catalogue_seen` makes ATTRIBUTABLE, so its turns joined the
    # denominator, while it equalled no live model's target, so no
    # numerator collected them. Measured through the two-run chain
    # roster-policy.yml documents: 5000 turns inside the denominator and
    # outside every numerator, a live snapshot not seated at all, and a
    # previous arm retired "below the 2% exit bar (0.0% ...)" on its own
    # family's usage. Following each chain to its end is still a FUNCTION
    # into at most one id per key, so rule (1)'s disjointness survives.
    for model_id in list(mapping):
        seen = {model_id}
        target = mapping[model_id]
        while target in mapping and target not in seen:
            seen.add(target)
            target = mapping[target]
        mapping[model_id] = target
    return mapping


def _is_attributable(candidate: str, folded: str, api_ids: set[str] | None,
                     api_ids_folded: set[str] | None,
                     previous_arms: set[str], previous_arms_folded: set[str],
                     catalogue_seen: set[str]) -> bool:
    """Whether a census key names something this harness can actually
    credit. `api_ids=None` means "no catalogue context was given" — every
    caller inside compute_roster always gives one; the handful of tests
    that call usage_share()/_in_window_totals() directly, on already-real
    ids, with no context at all, get the old unfiltered behavior instead
    of an empty catalogue.

    Exactly three routes, checked below, and this IS the whole set (#129
    review round 6 deleted two more that used to sit beside them — see
    the end of this docstring):

    `folded in api_ids_folded` (`api_ids` run through the SAME alias map
    as `folded`) covers two shapes at once. An ordinary bare catalogue id
    is a fixed point of its own fold (nothing maps it further), so it
    reappears in `api_ids_folded` unchanged — this is what makes a bare
    `candidate in api_ids` check redundant, see below. And a candidate
    recorded under the bare alias of a dated-snapshot-ONLY catalogue entry
    (roster-policy.yml's own documented shape: the catalogue publishes
    ONLY `<alias>-YYYYMMDD`, never the bare `<alias>`) still matches,
    because `alias_map` folds the catalogue id ONTO that alias and lands
    it in `api_ids_folded` — measured: 2000 turns under a verbatim
    catalogue id once read as CENSUS_UNRANKED without this route.

    `previous_arms_folded` (`previous_arms` run through the SAME alias
    map) is the missing sibling of the route above, for a previous
    roster's arm instead of a live catalogue id: a previous arm published
    under a DATED id, whose usage the census records under the UNDATED
    alias, matches via the fold even after the dated id has left the
    Models API entirely — measured: dropping 5000 real turns from the
    denominator and inflating an unrelated model's share from ~2.0% to a
    false ~97.1% (B1, #129 review round 6 — the alias map compute_roster
    builds must itself fold `previous_arms`/`catalogue_seen` in for this
    route to have anything to match; see compute_roster's `aliases`
    comment).

    Two more routes used to sit here — bare, unfolded `candidate in
    api_ids`/`folded in api_ids`, and `candidate in previous_arms`/
    `folded in previous_arms` — and #129 review round 6 deleted them as
    PROVABLY dead, not merely untested: for any id `x` that is a genuine
    member of `api_ids` (or `previous_arms`), `api_ids_folded` (or
    `previous_arms_folded`) is built by folding EVERY element of that same
    set through the identical alias map, so `x`'s own fold is already one
    of its elements by construction — `x in api_ids` (or `previous_arms`)
    therefore never fires without `folded in api_ids_folded` (or
    `previous_arms_folded`) also firing for `x` as the candidate. Dropping
    them left every existing test green with no other code path changed.
    `catalogue_seen = set(api_ids) | previous.catalogue_seen`
    (compute_roster) is a superset of `api_ids` besides, which is a second,
    independent reason a bare `api_ids` check added nothing.

    Being ranked (a recognised family word in the id) is necessary but NOT
    sufficient: a proxy or routing alias can paste extra segments onto a
    real family word and still be `rung_of()`-ranked (see
    test/run_tests.py::TestIssue67Review3 for a worked example), without
    being a model this policy can seat or credit — nobody's numerator ever
    matches it, so letting it into a denominator only pushes every real
    arm's share toward zero, and letting it into `_in_window_totals`'s
    ranked total makes an otherwise entirely unattributable census read as
    "usable" evidence to retire a real previous arm at 0.0%. Closing that
    (see `_in_window_totals`) for a proxy alias is the same fix `other`
    already had for a value with no family word at all — a second route to
    the identical failure. Widening attribution to both spellings of the
    catalogue id (above) must not widen it to a proxy alias too: neither of
    TestIssue67Review3's worked proxy-alias examples folds to, or ever
    equals, an api id or a previous arm under either spelling —
    TestIssue67Review4 carries the regression floor for that.

    `catalogue_seen` is a THIRD, independent route to attribution, and
    replaces round 4's `_canonical_id_re` (an id-SHAPE check, withdrawn):
    shape cannot tell a since-retired real model from a plausibly-named
    proxy, and it shipped with three holes — a Unicode decimal digit in the
    version segment matched `\\d` and could false-retire a real arm; the
    pre-#67 legacy id shape (family word AFTER a leading numeric segment,
    rather than right after `claude-`) never matched at all, starving a
    since-retired legacy model out of the denominator; and a plausible but
    entirely invented version number, in no catalogue and never an arm,
    was attributed outright. TestIssue67Review5 carries the worked examples
    for all three. `catalogue_seen` is EVIDENCE instead of shape: the union of
    every id the Models API has ever listed across runs (see
    `compute_roster`), so a real model that has left the Models API and
    was never a previous arm is still credited for as long as this
    harness's own history has actually observed it — the property
    `usage_share`'s own docstring states — while a proxy/routing alias
    that merely carries a family word was never a catalogue id and so
    never enters `catalogue_seen` in the first place. FIRST-RUN CAVEAT:
    with no history yet (`catalogue_seen` empty, e.g. a genuine first run,
    or a previous roster that could not be read), a model retired before
    this harness ever observed it is unattributable — there is no evidence
    to credit, only the shape it USED to have, which is exactly the
    unreliable signal this replaces. This also covers the MIGRATION case:
    the `previous.json` already sitting on `eval-results` predates this
    field entirely, so the first run after this merges behaves exactly
    like a genuine first run. S3 (#129 review round 6) adds a SECOND
    migration, for `catalogue_seen`'s own shape change (a bare id string
    to `{id, last_seen}`) — see `_clean_catalogue_seen`.
    """
    if api_ids is None:
        return True
    return (folded in (api_ids_folded or ())
           or candidate in previous_arms_folded or folded in previous_arms_folded
           or candidate in catalogue_seen or folded in catalogue_seen)


def _fold_set(ids: set[str], aliases: dict) -> set[str]:
    """`ids` run through `aliases` — the recurring "fold a set the same way
    a single id gets folded" step `api_ids_folded` and `previous_arms_folded`
    both are."""
    return {aliases.get(i, i) for i in ids}


def _format_share(value: float, bar: float, *, under: bool = False) -> str:
    """A share percentage, rendered against its own bar.

    In the "at or above" direction (`under=False`, the default), landing
    exactly on the bar is correct, not contradictory — "carries 10.0% ...
    at or above the 10% entry bar" at a true 10.0% — so one decimal place
    always suffices.

    In the "below"/"under" direction (`under=True`), landing on the bar
    at one decimal reads as self-contradictory — "below the 2% exit bar
    (2.0%)" at a true 1.96%, or still at two decimals for 1.9999% — and a
    genuinely tiny NONZERO share can round all the way to "0.0" and read
    as no usage at all about a model that carried real turns. Escalate
    through 1, 2, 3, 4, then 6 decimal places until the rendering both
    differs from the bar and, for a nonzero value, does not read as
    "0.0...0"; `:.6g` catches a value so small even 6 decimal places round
    it away, and `:.17g` — enough digits to round-trip any float — is the
    last resort.

    EVERY rendering is checked against the bar, the fallbacks included (N3,
    #129 review round 7). `:.6g` used to be returned unchecked, and six
    SIGNIFICANT digits is not six decimal places: a share of 1.99999975%
    renders there as exactly "2", so the reason read "below the 2% exit bar
    (2% of rankable census usage)" — a sentence that contradicts itself
    about a share that really is under the bar.
    """
    if not under:
        return f"{value:.1f}"
    for spec in ("1f", "2f", "3f", "4f", "6f", "6g", "17g"):
        text = f"{value:.{spec}}"
        if float(text) != bar and (value == 0 or float(text) != 0.0):
            return text
    return f"{value:.17g}"


def usage_share(counts: dict, model_id: str, weeks: list[str],
                rungs: list[list[str]], aliases: dict | None = None,
                api_ids=None, previous_arms=None, catalogue_seen=None) -> float:
    """Percent of RANKED, ATTRIBUTABLE census usage over `weeks` that
    `model_id` carries.

    The denominator counts every model the census saw THAT THE LADDER CAN
    PLACE, including ones the Models API no longer lists — work done on a
    since-retired model still happened, and the question is what share of the
    fleet's real work this model did. It EXCLUDES models the ladder cannot
    place, and the census's own `other` bucket with them: an unranked model
    takes no roster seat, so leaving its usage in the denominator only pushes
    every ranked model under the entry bar (measured: a model at 60 turns a
    week computed at 5.7% against 1000 unranked turns a week).

    `api_ids`/`previous_arms`/`catalogue_seen`, when given, ALSO exclude a
    ranked-but-unattributable key — see `_is_attributable`. That exclusion
    is deliberately narrower than "not currently in the catalogue": a
    since-retired id this harness's own history has actually seen in the
    Models API (`catalogue_seen`) still counts here, which is what keeps
    the "including ones the Models API no longer lists" property above
    actually true rather than only in the docstring — only a proxy/routing
    alias that merely carries a family word is excluded, because it was
    never a catalogue id and so never entered `catalogue_seen` either.
    FIRST-RUN CAVEAT: with no `catalogue_seen` history yet, a model retired
    before this harness's first run is unattributable — its usage silently
    drops from the denominator until a run observes it directly (see
    `_is_attributable`) — including the MIGRATION case where the
    `previous.json` already on `eval-results` predates this field, so the
    first run after this merges behaves like a genuine first run; S3
    (#129 review round 6) adds a second migration on top, for
    `catalogue_seen`'s own bare-string-to-`{id, last_seen}` shape change.
    Every call inside compute_roster gives `api_ids` and `previous_arms`;
    omitted (both default None), the denominator is every ranked key
    regardless of catalogue membership, the pre-#67-review-round-3
    behavior a few direct tests of the raw arithmetic rely on.

    A dated snapshot's usage is folded onto its alias — one model, one share.
    """
    aliases = aliases or {}
    api_ids_set = None if api_ids is None else set(api_ids)
    api_ids_folded = None if api_ids_set is None else _fold_set(api_ids_set, aliases)
    previous_arms_set = set(previous_arms) if previous_arms else set()
    previous_arms_folded = _fold_set(previous_arms_set, aliases)
    catalogue_seen_set = set(catalogue_seen) if catalogue_seen else set()
    wanted = set(weeks)
    target = aliases.get(model_id, model_id)
    total = 0
    mine = 0
    for candidate, by_week in (counts or {}).items():
        if rung_of(candidate, rungs) is None:
            continue
        folded = aliases.get(candidate, candidate)
        if not _is_attributable(candidate, folded, api_ids_set, api_ids_folded,
                                previous_arms_set, previous_arms_folded,
                                catalogue_seen_set):
            continue
        for week, n in (by_week or {}).items():
            if week in wanted:
                total += n
                if folded == target:
                    mine += n
    # Integer multiplication FIRST, then a single true division of two ints
    # — not `100.0 * mine / total`, which multiplies the float `100.0` by
    # the int `mine` and so converts `mine` to a float before dividing at
    # all. `usage_share` is called directly by a few tests on hand-built
    # counts that bypass `_clean_counts`'s own bounds; this form stays safe
    # for those PROVIDED `mine`/`total` are ints, as every real cell is —
    # `_clean_counts` coerces and bounds every cell to `[0, MAX_WEEKLY_TURNS]`
    # before compute_roster ever calls this. For int cells, Python's int/int
    # true division computes the exact ratio's correctly-rounded float
    # without ever needing `mine` or `total` to fit in a float individually,
    # unlike `100.0 * mine`, which converts `mine` to a float FIRST and
    # overflows to `inf` near the top of a float's range. It is NOT safe on
    # its own for a FLOAT cell bypassing `_clean_counts`: ONE cell around
    # `1e308` overflows just `100 * mine` to `inf`, dividing out to `inf`
    # (published as "carries inf% of census usage"); TWO such cells can
    # additionally overflow `total` itself (their sum, `2e308`, is also
    # past a float's max) to `inf`, and `inf / inf` is `nan`. Nor is it safe
    # for an int pair whose quotient is itself too large to represent as a
    # float (raises OverflowError converting it) — none of these shapes are
    # reachable through compute_roster's own int-coerced, bounded cells,
    # only through a hand-built dict a test constructs directly.
    return 0.0 if total == 0 else (100 * mine) / total


def _version_key(model_id: str) -> tuple:
    """Version components compared NUMERICALLY: `-4-10` sorts above `-4-9`.

    Only the tie-break — `created_at` decides first — but on a tie it decides
    which model is "the newest in its tier", and a string compare gets that
    exactly backwards for any family that reaches a two-digit minor.

    `isdecimal()`, not `isdigit()`: `isdigit()` is True for characters (e.g.
    the superscript `²`) that `int()` then refuses with a ValueError.
    `isdecimal()` is exactly the set `int()` accepts.
    """
    parts = []
    for token in str(model_id).split("-"):
        parts.append((1, int(token), "") if token.isdecimal() else (0, 0, token))
    return tuple(parts)


def _rank(model: dict, rungs: list[list[str]]) -> tuple:
    """Capability sort key: rung first, then newest, then version."""
    created = parse_ts(model.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
    return (rung_of(model["id"], rungs), created, _version_key(model["id"]))


def _clean_models(models_doc: dict, warn) -> list[dict]:
    """Model entries that are dicts with a well-formed, string `id`.
    Everything else named.

    The Models API is trusted; the FILE is not — it is written by another job
    and read off a public branch, and a `models` list holding a string or an
    entry with no id used to raise a TypeError three frames down.

    The id is shape-checked with `PREVIOUS_ARM_ID_RE`, the same shape
    `_clean_previous_arms` requires: an id this loose (or a bare type check
    alone) reaches `unranked`/`excluded` and from there render_summary's
    Markdown, which eval.yml prints to stdout — where GitHub parses `::`
    workflow commands — or reaches `catalogue_seen`, published verbatim to
    the public `eval-results` branch and read back as `previous`'s own
    `catalogue_seen` next run (`catalogue_seen` does not itself reach
    render_summary's Markdown). A hostile id is dropped the same way a
    bad-shaped `entry` is, and the warning names no value — only the count.
    """
    entries = (models_doc or {}).get("models")
    if not isinstance(entries, list):
        warn("models document has no `models` list; treating the catalogue as empty")
        return []
    clean = []
    skipped = 0
    malformed = 0
    for entry in entries:
        if not (isinstance(entry, dict) and isinstance(entry.get("id"), str)
                and entry["id"]):
            skipped += 1
        elif not PREVIOUS_ARM_ID_RE.match(entry["id"]):
            malformed += 1
        else:
            clean.append(entry)
    if skipped:
        warn(f"models document: skipped {skipped} entry/entries without a string `id`")
    if malformed:
        warn(f"models document: skipped {malformed} entry/entries with a "
             f"malformed model-id-shaped `id`")
    return clean


#: A week is 604800 seconds; no real account's turn rate gets within two
#: orders of magnitude of one turn a second, sustained for a week. Anything
#: above this in a single census cell is a bad value, not real usage — see
#: `_clean_counts`'s upper-bound check.
MAX_WEEKLY_TURNS = 10 ** 7


def _clean_counts(counts, warn) -> dict:
    """{model: {week: int}}, validated. Nothing that fails validation is counted.

    No offending VALUE is ever quoted back: the census is public, and an old
    census on the branch predates the key allowlist that keeps it that way.
    """
    if counts is None:
        return {}
    if not isinstance(counts, dict):
        warn("census `counts` is not an object; treating the census as empty")
        return {}
    cleaned: dict[str, dict[str, int]] = {}
    bad_rows = 0
    bad_cells = 0
    for model_id, by_week in counts.items():
        if not isinstance(model_id, str) or not isinstance(by_week, dict):
            bad_rows += 1
            continue
        for week, n in by_week.items():
            if not isinstance(week, str):
                bad_cells += 1
                continue
            # `bool` is an `int` SUBCLASS in Python — `int(True)` is `1`,
            # `int(False)` is `0` — so a census cell holding the JSON
            # literal `true`/`false` sailed through every check below and
            # silently became a real count instead of being rejected as
            # the wrong shape. Checked before `isinstance(n, int)` too:
            # that check alone would not otherwise catch it.
            if isinstance(n, bool):
                bad_cells += 1
                continue
            # An actual `int`, nothing coerced to one. `int(n)` used to
            # accept far more than a real census cell (a JSON number) ever
            # produces: `int(1.9)` silently truncates a float instead of
            # rejecting it; `int("5")` accepts a JSON STRING; `int("5_0")`
            # is `50` (Python's int() honors the digit-group underscore
            # numeric-literal syntax inside a string); `int("٥")` is `5`
            # (int() accepts non-ASCII Unicode decimal digits). None of
            # these is a value `json.load` ever hands back for a JSON
            # number — every one is a distinct, silent, wrong-typed cell
            # that used to become a real count.
            if not isinstance(n, int):
                bad_cells += 1
                continue
            value = n
            # A negative count is not a real turn tally — accepting it at
            # face value let it sum straight into usage_share's totals
            # (a `-99` cell once yielded a 'carries 10000.0%' reason, and a
            # cancelling +/- pair could zero a census's only ranked usage
            # while `_census_verdict` still read it as usable).
            if value < 0:
                bad_cells += 1
                continue
            # An upper bound, not just a lower one: `1e308` (a huge but
            # finite float) or a several-hundred-digit JSON integer both
            # pass `int()` cleanly — Python ints are arbitrary precision —
            # and used to ride straight into usage_share's arithmetic, where
            # multiplying a value that large by a float either silently
            # produces `inf` (published as "carries inf% of census usage")
            # or raises OverflowError converting it to a float at all. A
            # week cannot hold more turns than MAX_WEEKLY_TURNS; reject
            # anything above it as a bad cell, the same as a negative one.
            if value > MAX_WEEKLY_TURNS:
                bad_cells += 1
                continue
            cleaned.setdefault(model_id, {})[week] = value
    if bad_rows:
        warn(f"census `counts`: skipped {bad_rows} row(s) that are not "
             f"model -> {{week: count}}")
    if bad_cells:
        # "not a usable count", not "not a number": a negative value and one
        # above MAX_WEEKLY_TURNS both ARE numbers — they are rejected for
        # being out of range, a boolean for being the wrong type entirely,
        # and only a genuinely non-numeric/non-finite cell for failing to
        # parse as a number at all. One wording covers all four honestly.
        warn(f"census `counts`: skipped {bad_cells} weekly count(s) that are "
             f"not a usable count")
    return cleaned


def _census_relevance(count_keys):
    """A predicate: does the census name this id, under EITHER spelling?

    The one question both caps below order by, so they answer it the same
    way and one mutation cannot quietly change only one of them. Three
    routes, and each has its own regression floor (A3, #129 review round
    8): the census names the id outright; the census names a DATED
    spelling of it (`named_bases`); or the id is itself a dated spelling
    of something the census names.
    """
    named = set(count_keys)
    named_bases = set()
    for key in named:
        match = SNAPSHOT_SUFFIX.match(key)
        if match:
            named_bases.add(match.group("base"))

    def names(model_id: str) -> bool:
        if model_id in named or model_id in named_bases:
            return True
        match = SNAPSHOT_SUFFIX.match(model_id)
        return bool(match) and match.group("base") in named

    return names


#: N3 (#129 review round 6): the same cap `CATALOGUE_SEEN_CAP` applies to
#: `catalogue_seen`, sized the same way — see that constant's own comment.
PREVIOUS_ARMS_CAP = 500


def _clean_previous_arms(previous, warn, api_ids=(), count_keys=()) -> list[str]:
    """The previous roster's arm ids. A malformed entry is skipped, not fatal.

    Shape-checked with `PREVIOUS_ARM_ID_RE`, not just type-checked: a
    previous roster is a JSON file read off a public branch, and every id
    from it is interpolated verbatim into render_summary's Markdown, which
    eval.yml prints to stdout — where GitHub parses `::` workflow commands.
    An offender is dropped the same way a bad-shaped `entry` is, and the
    warning names no value — only the count.

    Dedup is a SET membership test, not `entry not in ids` over the
    growing output list — the latter is O(n^2) and measured at 5.4s for
    40,000 entries, 37s for 100,000, publishing a 2.7MB roster with no
    warning at all. It has no deterministic regression floor and is not
    getting one: its only symptom is wall-clock time, and a timing
    assertion is a flaky test, not a floor (N8, #129 review round 7). What
    actually BOUNDS the work here is the cap below — the dedup is a
    constant-factor courtesy on the way to it, keeping the scan linear
    rather than quadratic while the input is still unbounded. The accepted
    list is also capped at
    `PREVIOUS_ARMS_CAP`, and the warning names the dropped COUNT, never a
    dropped id.

    Past the cap, RELEVANCE decides who survives, not spelling (S3, #129
    review round 7). An id this run can actually say something about — one
    the Models API still lists (`api_ids`), or one the census names
    (`count_keys`, either spelling of a dated/undated pair) — is kept ahead
    of filler, and only then does the id order break ties. The plain
    `sorted(ids)[:PREVIOUS_ARMS_CAP]` this replaces had the same
    alphabetical-head shape S2 fixes for `catalogue_seen`, and the same
    consequence: a previous roster carrying 500 low-sorting filler ids
    beside ONE real departed arm reported 500 filler retirements and not
    the real one, so `retired_since_last` — the line render_summary leads
    with — silently lost the only retirement that happened. Both arguments
    default to empty, which reduces to the old spelling-only order for a
    caller with no context to give.
    """
    if previous is None:
        return []
    entries = previous.get("arms") if isinstance(previous, dict) else None
    if entries is None:
        return []
    if not isinstance(entries, list):
        warn("previous roster: `arms` is not a list; comparing against nothing")
        return []
    seen: set[str] = set()
    ids = []
    skipped = 0
    for entry in entries:
        if (isinstance(entry, dict) and isinstance(entry.get("id"), str)
                and entry["id"] and PREVIOUS_ARM_ID_RE.match(entry["id"])):
            if entry["id"] not in seen:
                seen.add(entry["id"])
                ids.append(entry["id"])
        else:
            skipped += 1
    if skipped:
        warn(f"previous roster: skipped {skipped} `arms` entry/entries that are "
             f"not an object with a well-formed model-id-shaped `id`")
    if len(ids) > PREVIOUS_ARMS_CAP:
        dropped = len(ids) - PREVIOUS_ARMS_CAP
        live = set(api_ids)
        names = _census_relevance(count_keys)

        def _relevant(model_id: str) -> bool:
            return model_id in live or names(model_id)

        # `not _relevant(...)` first: False sorts before True, so relevant
        # ids head the list and the id order only breaks ties inside each
        # group — deterministic either way.
        ids = sorted(ids, key=lambda i: (not _relevant(i), i))[:PREVIOUS_ARMS_CAP]
        warn(f"previous roster: dropped {dropped} `arms` entry/entries past "
             f"the {PREVIOUS_ARMS_CAP}-entry cap")
    return ids


def _as_date(moment: datetime) -> str:
    """A `catalogue_seen` date: UTC, zero-padded, re-readable by `parse_ts`.

    `strftime("%Y-%m-%d")` does neither of the last two on this platform
    (A2/F2, #129 review round 8). It renders an offset-aware timestamp's
    LOCAL date, so `2026-09-01T23:00:00-08:00` published `2026-09-01`, a
    day early, and `2026-09-02T01:00:00+05:00` published `2026-09-02`, a
    day late — the same fix `source.census_at` already had. And it does
    not zero-pad a year below 1000, so `0001-01-01` published as
    `1-01-01`, which `parse_ts` refuses: `_update_catalogue_seen` then
    read the entry as "seen today" (`parse_ts(last_seen) or now`), an
    entry two thousand years past the age window survived it, and 500
    such plants sorted as the newest history there is and evicted the
    real one. A date this harness writes and cannot read back is one
    that silently stops ageing.
    """
    return moment.astimezone(timezone.utc).date().isoformat()


#: What an unparseable `last_seen` sorts as inside `_update_catalogue_seen`'s
#: cap: the oldest moment there is, never `now`.
_LAST_SEEN_FLOOR = datetime.min.replace(tzinfo=timezone.utc)

#: `catalogue_seen`'s cap (N3, merged into S3's rewrite): a length past
#: which the O(1)-membership dedup below still leaves an unbounded, ever-
#: growing publish. This run's own live api ids are never evicted by it —
#: see `_update_catalogue_seen` — only accumulated HISTORY is trimmed.
CATALOGUE_SEEN_CAP = 500


def _clean_catalogue_seen(previous, warn, now: datetime) -> list[dict]:
    """The previous roster's `catalogue_seen` history, as `{"id",
    "last_seen"}` entries (S3, #129 review round 6). Accepts the bare
    string shape this field used to publish — on EVERY read, not for a
    bounded number of runs (N5, #129 review round 7: the docstring used to
    promise "one migration run", which nothing enforces and nothing needs
    to). What is actually true is that the shape is accepted on read and
    always REPUBLISHED in the `{id, last_seen}` shape, so after this
    harness's own first run the bare string can only ever come back from a
    producer this harness does not control — which is exactly the untrusted
    input the rest of this function is about. A bare string carries no age
    information at all, so it is rewritten
    with `last_seen` = today — seeing it in a previous roster is the
    only evidence there is, and treating it as "seen today" costs at
    most one extra `catalogue_seen_max_age_days` window before an id
    that stops being genuinely re-observed ages out on its own (see
    `_update_catalogue_seen`, which is what actually EVICTS an entry —
    this function only reads and shape-validates what came in). A
    `last_seen` in the future (a hand-edited or clock-skewed entry) is
    clamped to today rather than trusted, so a single future-dated plant
    cannot buy itself unlimited immunity from the age check.

    A malformed entry is skipped, not fatal — same treatment as
    `_clean_previous_arms`, and for the same reason: this is read off a
    public branch (`eval-results`), which the module docstring already
    calls untrusted, and every id from it ends up published again in
    this run's own `catalogue_seen` output.
    """
    if previous is None:
        return []
    entries = previous.get("catalogue_seen") if isinstance(previous, dict) else None
    if entries is None:
        return []
    if not isinstance(entries, list):
        warn("previous roster: `catalogue_seen` is not a list; starting empty")
        return []
    today = _as_date(now)
    by_id: dict[str, str] = {}
    migrated = 0
    skipped = 0
    for entry in entries:
        if isinstance(entry, str) and entry and PREVIOUS_ARM_ID_RE.match(entry):
            by_id[entry] = today
            migrated += 1
            continue
        if (isinstance(entry, dict) and isinstance(entry.get("id"), str)
                and entry["id"] and PREVIOUS_ARM_ID_RE.match(entry["id"])
                and isinstance(entry.get("last_seen"), str) and entry["last_seen"]):
            parsed = parse_ts(entry["last_seen"])
            if parsed is None:
                skipped += 1
                continue
            # The PARSED date, re-rendered — never the raw string (N1,
            # #129 review round 7). `parse_ts` strips its input before
            # comparing it against `now`, but the raw value used to be
            # stored here and republished verbatim, so a `\r\n` wrapped
            # around a date reached roster/latest.json on the public
            # branch as literal control characters. Same fix
            # `source.census_at` already had.
            by_id[entry["id"]] = today if parsed > now else _as_date(parsed)
            continue
        skipped += 1
    if migrated:
        warn(f"previous roster: migrated {migrated} `catalogue_seen` "
             f"entry/entries from the bare-string shape")
    if skipped:
        warn(f"previous roster: skipped {skipped} `catalogue_seen` entry/entries "
             f"that are not a well-formed {{id, last_seen}} object or a "
             f"model-id-shaped string")
    return [{"id": model_id, "last_seen": last_seen}
           for model_id, last_seen in by_id.items()]


def _update_catalogue_seen(api_ids, previous_entries: list[dict], now: datetime,
                           policy: dict, warn, count_keys=()) -> list[dict]:
    """This run's `catalogue_seen` history: refresh, evict, cap.

    Every id THIS run's Models API actually listed gets its `last_seen`
    refreshed to today — that is the only way an id's clock resets. Every
    other previously-seen id keeps its own `last_seen`, and is DROPPED
    once that is older than `policy["catalogue_seen_max_age_days"]` — the
    only way an id LEAVES this history, besides the cap below. A model id
    planted directly in `catalogue_seen` on `eval-results` (an untrusted
    branch, per the module docstring) that the Models API never actually
    returns has no way to get its `last_seen` refreshed, so it ages out
    on its own; reverting the plant on the branch is not even necessary.

    Ageing out ends a plant's future effect. It
    does not undo a retirement the plant already caused (N6, #129 review
    round 7): a model whose measured share the fabricated usage pushed
    under the exit bar is retired, and by the time the plant expires that
    model is no longer a previous arm at all — so the exit bar no longer
    applies to it, and a trickle of real usage (a dozen turns a week, say)
    never re-seats it. It comes back only by clearing the ENTRY bar, by
    being the newest in its tier, or by hand.

    The cap NEVER evicts one of this run's own live `api_ids` — only
    accumulated history beyond them — so `catalogue_seen` stays a
    superset of `api_ids`, the property `usage_share`'s docstring and
    `compute_roster`'s callers rely on. Past that, `count_keys` (this
    run's census keys, the same argument `_clean_previous_arms` takes)
    decides who survives, ahead of any date — see the invariant written
    over the sort below, and note that eviction there is PERMANENT for
    the same reason ageing out is not a repair.
    """
    today = _as_date(now)
    by_id = {e["id"]: e["last_seen"] for e in previous_entries}
    for model_id in api_ids:
        by_id[model_id] = today
    max_age = timedelta(days=policy["catalogue_seen_max_age_days"])
    survivors: dict[str, str] = {}
    aged_out = 0
    for model_id, last_seen in by_id.items():
        seen_at = parse_ts(last_seen) or now
        if now - seen_at > max_age:
            aged_out += 1
            continue
        survivors[model_id] = last_seen
    if aged_out:
        warn(f"catalogue_seen: dropped {aged_out} entry/entries older than "
             f"the {policy['catalogue_seen_max_age_days']}-day window")
    api_id_set = set(api_ids)
    live = sorted(i for i in survivors if i in api_id_set)
    # THE INVARIANT the cap's order has to satisfy (F1, #129 review round
    # 8): who survives is decided by data the previous roster does not
    # control — the live catalogue and the census — never by a field the
    # previous roster asserts about itself. An entry the census names
    # outlives any number of entries the census does not name, whatever
    # their dates or ids. Within entries the census does not name, order
    # is only a tie-break and a planter may win it, because those entries
    # move no share.
    #
    # Age alone does not satisfy it, and neither does spelling. Round 6
    # sorted by id, and `PREVIOUS_ARM_ID_RE` accepts a leading digit, so
    # 500 low-sorting ids evicted a real since-retired model by nothing
    # but its spelling. Round 7 sorted by `last_seen` — but the planter
    # writes `last_seen` too: a future date clamps to today and every bare
    # string migrates stamped today, so 498 entries dated today, or 500
    # bare strings, still evicted it. Either way its turns left the usage
    # denominator and an unrelated model was published as carrying 100.0%
    # of census usage where it really carried 9.09%.
    #
    # EVICTION IS PERMANENT. The next run's `previous.json` is this run's
    # output, so an id dropped here is gone from the history for good —
    # the same "ageing out is not a repair" property N6 wrote down for a
    # retirement (see this function's docstring). That is why the order
    # may not be something the input can dictate.
    #
    # Three stable sorts rather than one composite key, least significant
    # first: id ascending, then `last_seen` descending (leaving ids
    # ascending within one date), then census relevance (False sorts
    # first, so named entries head the list). An unparseable `last_seen`
    # sorts as the OLDEST moment there is, never as `now` (A2, round 8):
    # a value this module cannot read asserts nothing, and must not
    # outrank an entry that carries a real date. That branch is a FLOOR
    # rather than a live one — `_clean_catalogue_seen` re-renders every
    # date through `_as_date` before this runs, so everything reaching
    # here parses — which is exactly why it must not read as today: that
    # is the assumption `strftime`'s unpadded year quietly falsified.
    names = _census_relevance(count_keys)
    historical = sorted(i for i in survivors if i not in api_id_set)
    historical.sort(key=lambda i: parse_ts(survivors[i]) or _LAST_SEEN_FLOOR,
                    reverse=True)
    historical.sort(key=lambda i: not names(i))
    room = max(0, CATALOGUE_SEEN_CAP - len(live))
    kept = live + historical[:room]
    dropped = len(survivors) - len(kept)
    if dropped:
        warn(f"catalogue_seen: dropped {dropped} entry/entries past the "
             f"{CATALOGUE_SEEN_CAP}-entry cap")
    return [{"id": model_id, "last_seen": survivors[model_id]}
           for model_id in sorted(kept)]


def _in_window_totals(counts: dict, weeks: set[str], rungs: list[list[str]],
                      aliases: dict | None = None, api_ids=None,
                      previous_arms=None, catalogue_seen=None) -> tuple[int, int]:
    """(raw_total, ranked_total) of census usage over `weeks`.

    `ranked_total` mirrors `usage_share`'s own denominator — it excludes
    `other`, every id the tier ladder cannot place, and (when `api_ids`/
    `previous_arms`/`catalogue_seen` are given, as every call inside
    compute_roster does — see `_is_attributable`) every ranked-but-
    unattributable key such as a proxy alias that merely carries a family
    word without being a real catalogue model, a previous arm, or an id
    this harness's own history has observed. Computed once and handed to
    `_census_verdict`, so its "is there usage evidence" check agrees with
    the number every arm's share is actually divided by, rather than
    reading raw counts that can be nonzero while the ranked denominator is
    zero (a census entirely routed through Bedrock/Vertex/a proxy lands
    every count under `other`, or — the second route to the same gap — a
    proxy alias that happens to carry a family word).
    """
    aliases = aliases or {}
    api_ids_set = None if api_ids is None else set(api_ids)
    api_ids_folded = None if api_ids_set is None else _fold_set(api_ids_set, aliases)
    previous_arms_set = set(previous_arms) if previous_arms else set()
    previous_arms_folded = _fold_set(previous_arms_set, aliases)
    catalogue_seen_set = set(catalogue_seen) if catalogue_seen else set()
    raw_total = 0
    ranked_total = 0
    for candidate, by_week in (counts or {}).items():
        ranked = rung_of(candidate, rungs) is not None
        if ranked:
            folded = aliases.get(candidate, candidate)
            ranked = _is_attributable(candidate, folded, api_ids_set,
                                      api_ids_folded, previous_arms_set,
                                      previous_arms_folded, catalogue_seen_set)
        for week, n in (by_week or {}).items():
            if week in weeks:
                raw_total += n
                if ranked:
                    ranked_total += n
    return raw_total, ranked_total


#: `_census_verdict`'s machine-readable half. Reasons are for humans; this is
#: for callers deciding what else follows (e.g. whether `census_at` is
#: recorded), so they do not have to reconstruct it from a string prefix.
CENSUS_UNREADABLE = "unreadable"
CENSUS_ABSENT = "absent"
CENSUS_FUTURE = "future"
CENSUS_STALE = "stale"
CENSUS_EMPTY = "empty"
CENSUS_UNRANKED = "unranked"
CENSUS_FRESH = "fresh"

#: Verdicts whose census WAS published and current enough to be worth citing
#: as provenance, even though it is not usable evidence — see `CENSUS_EMPTY`
#: and `CENSUS_UNRANKED` below. `CENSUS_UNREADABLE` is deliberately absent:
#: a file that failed to parse has no `generated_at` to cite.
CENSUS_PUBLISHED_CODES = (CENSUS_EMPTY, CENSUS_UNRANKED, CENSUS_FRESH)


def _census_verdict(census_doc, raw_total: int, ranked_total: int, policy, now,
                    census_problem: str | None = None):
    """(usable, note, code) — is there usage evidence for the window, and why not.

    Eight ways to have none, and they are NOT the same fact: a file that is
    present but failed to parse (distinct from nothing being published at
    all — `read_json` already tells the two apart, but `main()` used to
    collapse them by discarding the problem and passing `census_doc=None`
    either way), nothing published, a timestamp in the future (clock skew or
    a hand edit — every week then falls outside the window while the age
    check reads as fresh), a census older than the freshness window, a
    census that is present and current and simply holds nothing for these
    weeks, a census that holds usage but none of it is usage this policy can
    rank (every count fell under `other`, an unranked id, or an id ranked
    but unattributable — a proxy alias, say, which the ladder DOES place but
    which names no real catalogue model or previous arm; see
    `_is_attributable`), a census whose ranked, attributable total is
    nonzero but still under `policy["min_ranked_turns"]` — almost the whole
    fleet routed through `other` with a handful of stray ranked turns is not
    evidence of anything, even though `ranked_total == 0` alone would not
    have caught it — and a census whose ranked total clears that ABSOLUTE
    floor yet is still a vanishing fraction of the raw window total: the
    absolute floor alone let `{other: 100000/wk, some-model: 20 turns
    total}` read as usable evidence over 800,020 raw turns, retiring a
    previous arm with no counted usage of its own at a literal 0.0%.
    `policy["min_ranked_share"]` is that RELATIVE guard. Each says so in its
    own words, because "fell back to newest per tier" without the cause is
    a roster nobody can debug.
    """
    if census_problem:
        # `read_json`'s message already names the file and the exception
        # class only — never file content — so it is safe to surface
        # verbatim as far down as an arm's own reason.
        return False, census_problem, CENSUS_UNREADABLE
    census_at = parse_ts((census_doc or {}).get("generated_at"))
    if census_doc is None or census_at is None:
        return False, "no fresh census (none published)", CENSUS_ABSENT
    if census_at > now:
        return False, ("no fresh census (its generated_at is in the future, so "
                       "every week of usage falls outside the window — clock "
                       "skew or a hand edit)"), CENSUS_FUTURE
    age = (now - census_at).days
    if now - census_at > timedelta(days=policy["census_max_age_days"]):
        return False, (f"no fresh census (last published {age} days ago, over the "
                       f"{policy['census_max_age_days']}-day window)"), CENSUS_STALE
    if raw_total == 0:
        return False, ("census published but empty over the window (no usage "
                       "recorded for any model in these weeks)"), CENSUS_EMPTY
    if ranked_total == 0:
        return False, ("census published but holds no usage this policy can "
                       "rank over the window (every count in these weeks is "
                       "`other`, an id the tier ladder cannot place, or an id "
                       "neither the Models API nor the previous roster "
                       "attributes)"), \
            CENSUS_UNRANKED
    if ranked_total < policy["min_ranked_turns"]:
        return False, (f"census published but holds only {ranked_total} "
                       f"rankable, attributable turn(s) over the window — "
                       f"under the {policy['min_ranked_turns']}-turn floor, "
                       f"too little to be evidence of anything"), \
            CENSUS_UNRANKED
    if ranked_total < policy["min_ranked_share"] * raw_total:
        bar = 100 * policy["min_ranked_share"]
        pct = 100 * ranked_total / raw_total
        return False, (f"census published but only {ranked_total} of "
                       f"{raw_total} raw turns over the window are rankable, "
                       f"attributable usage ({_format_share(pct, bar, under=True)}% "
                       f"— under the {bar:g}% relative floor), too little to "
                       f"be evidence of anything"), \
            CENSUS_UNRANKED
    return True, "", CENSUS_FRESH


def compute_roster(models_doc: dict, census_doc: dict | None, policy: dict,
                   previous: dict | None, now: datetime,
                   admin_doc: dict | None = None, warn=None,
                   census_problem: str | None = None,
                   previous_problem: str | None = None) -> dict:
    warn = warn or _stderr
    rungs = tier_rungs(policy)

    entries = _clean_models(models_doc, warn)
    api_ids = [m["id"] for m in entries]
    ranked = [m for m in entries if rung_of(m["id"], rungs) is not None]
    unranked = [{"id": m["id"],
                 "reason": ("no family word from the tier ladder appears in its "
                            "id, so it cannot be ranked and takes no roster seat")}
                for m in entries if rung_of(m["id"], rungs) is None]
    unranked_ids = {u["id"] for u in unranked}

    counts = _clean_counts((census_doc or {}).get("counts"), warn)

    # Computed before the alias maps below: USAGE attribution (B1, #129
    # review round 6) needs both a previous roster's arm ids and its
    # catalogue history to fold a previous arm published under a DATED id
    # that has since left the API, whose usage the census records under
    # the UNDATED alias — see the `aliases` comment just below.
    previous_arms = _clean_previous_arms(previous, warn, api_ids=api_ids,
                                        count_keys=counts.keys())

    # The union of every id the Models API has EVER listed across runs: this
    # run's api ids plus whatever the previous roster already accumulated,
    # refreshed/aged/capped by `_update_catalogue_seen` (S3, #129 review
    # round 6). Read back next run as `previous`'s own `catalogue_seen` —
    # see `_is_attributable`'s FIRST-RUN CAVEAT for what an empty history
    # means. `catalogue_seen_entries` is the PUBLISHED `{id, last_seen}`
    # shape; `catalogue_seen` stays a plain set of ids for every downstream
    # membership check (`_is_attributable`, `_fold_set`'s callers, etc.).
    catalogue_seen_entries = _update_catalogue_seen(
        api_ids, _clean_catalogue_seen(previous, warn, now), now, policy, warn,
        count_keys=counts.keys())
    catalogue_seen = {e["id"] for e in catalogue_seen_entries}

    # Two alias maps, deliberately. SEATING may only collapse a snapshot onto
    # an alias the catalogue actually offers — an alias that exists solely as
    # an old census key is not a model anyone can run, so `seat_aliases`
    # stays catalogue-only. USAGE is widened past that (see
    # `_usage_alias_map`): a departed previous arm, a `catalogue_seen`
    # history entry and a census key all fold over api ids, census keys,
    # previous arms AND catalogue_seen, because a previous arm published
    # under a dated id that has since left the API, whose usage the census
    # records under the undated alias, is in NEITHER `api_ids` NOR `counts`
    # — only its undated alias is (in `counts`) — and `alias_map` needs BOTH
    # spellings present in the ids it is given to create the fold at all.
    # Leaving previous_arms/catalogue_seen out of that call meant it never
    # saw the dated id, so `previous_arms_folded` downstream stayed
    # identical to `previous_arms` and never matched the undated candidate
    # — measured: 5000 real turns dropped from the denominator, inflating an
    # unrelated model's share from ~1.96% to a false ~97.1%. What the
    # widening may NOT do is re-target an id the Models API returns THIS
    # run: that is B1 of round 7, and `_usage_alias_map` is where the rule
    # lives. This is a SEPARATE mechanism from _is_attributable's
    # catalogue_seen check: that one credits a since-retired real id's own
    # usage even when neither of ITS spellings ever held (or holds) a seat.
    seat_aliases = alias_map(api_ids)
    snapshots = {m["id"]: seat_aliases[m["id"]]
                 for m in ranked if m["id"] in seat_aliases}

    available = [m for m in ranked if m["id"] not in snapshots]
    available.sort(key=lambda m: _rank(m, rungs))

    # Built AFTER `available` is ordered: rule (3) of `_usage_alias_map`
    # needs this run's own capability order to decide which live snapshot a
    # bare alias that is not itself in the catalogue names.
    aliases = _usage_alias_map(
        api_ids, list(counts) + previous_arms + list(catalogue_seen),
        seat_aliases, [m["id"] for m in available])

    enter_weeks = window_weeks(now, policy["arm_enter_window_weeks"])
    exit_weeks = window_weeks(now, policy["arm_exit_window_weeks"])
    window_union = set(enter_weeks) | set(exit_weeks)
    raw_total, ranked_total = _in_window_totals(
        counts, window_union, rungs, aliases=aliases,
        api_ids=api_ids, previous_arms=previous_arms,
        catalogue_seen=catalogue_seen)
    usable, stale_note, census_code = _census_verdict(
        census_doc, raw_total, ranked_total, policy, now,
        census_problem=census_problem)
    # The absolute/relative floor above is measured over the 8-week UNION,
    # which answers "is there fresh evidence at all". Seating and retiring
    # are separate questions, each measured over its OWN window: the 4-week
    # enter window is a strict subset of the union here, so a handful of
    # ranked turns can clear the union floor while the enter window itself
    # carries next to none — one lone turn there used to compute a 100.0%
    # entry share and seat a non-newest model on it (the ABSOLUTE floor,
    # applied per window). The RELATIVE floor (S1, #129 review round 6)
    # needs the same per-window treatment: an enter window dominated by
    # `other` can clear the union's relative floor on OTHER weeks' ranked
    # usage while carrying almost none of its own — measured: `other` at
    # 1,000,000/week for the enter window's weeks plus a real model
    # elsewhere in the union cleared the union's 100,025-of-4,100,025
    # relative floor while the enter window itself held 25 ranked turns
    # against 4,000,025 raw ones, computing a false 100.0% entry share.
    # Kept symmetric for the exit side even though, for this policy's
    # shipped numbers (arm_exit_window_weeks >= arm_enter_window_weeks),
    # the exit window IS the union and both `exit_usable` floors are
    # always identical to `usable`'s own — nothing guarantees that
    # relation stays true if the numbers ever change, and
    # TestIssue67Review6 exercises the exit-side branch below with a
    # test-only policy whose exit window is shorter than its enter one.
    enter_raw_total, enter_ranked_total = _in_window_totals(
        counts, set(enter_weeks), rungs, aliases=aliases,
        api_ids=api_ids, previous_arms=previous_arms,
        catalogue_seen=catalogue_seen)
    exit_raw_total, exit_ranked_total = _in_window_totals(
        counts, set(exit_weeks), rungs, aliases=aliases,
        api_ids=api_ids, previous_arms=previous_arms,
        catalogue_seen=catalogue_seen)
    enter_usable = (usable and enter_ranked_total >= policy["min_ranked_turns"]
                   and enter_ranked_total >= policy["min_ranked_share"] * enter_raw_total)
    exit_usable = (usable and exit_ranked_total >= policy["min_ranked_turns"]
                  and exit_ranked_total >= policy["min_ranked_share"] * exit_raw_total)
    # Provenance: the timestamp of the census this roster actually read. A
    # census that was published and simply held nothing usable for these
    # weeks HAS a timestamp worth recording — dropping it made "we read a
    # census and it said nothing" indistinguishable from "nobody published
    # one". A stale or future-dated census was not read, so it records
    # nothing. Branches on the verdict CODE, not on the reason string's
    # prefix — a human-facing sentence is not a stable thing to match on.
    # Published as the PARSED timestamp, re-rendered (N8, #129 review round
    # 6) — not the raw string: `parse_ts` strips it before ever comparing
    # it against `now`, but the raw value used to be published verbatim,
    # so a trailing newline or `\r` reached latest.json, summary.md, and
    # eval.yml's stdout as a literal control character. A published code
    # only ever follows a successful parse (see `_census_verdict`), so
    # this re-parse cannot fail here.
    census_at_parsed = (parse_ts((census_doc or {}).get("generated_at"))
                        if census_code in CENSUS_PUBLISHED_CODES else None)
    # `.astimezone(timezone.utc)` FIRST (N2, #129 review round 7):
    # `parse_ts` keeps whatever offset the census carried, and
    # `strftime("...Z")` on an offset-aware timestamp stamps a `Z` on the
    # LOCAL wall clock — a `+05:00` census published five hours early and
    # looking perfectly canonical, which is worse than looking wrong.
    census_at_published = (
        census_at_parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if census_at_parsed else None)

    newest_by_rung: dict[int, str] = {}
    for model in available:  # sorted weakest-first, oldest-first within a rung
        newest_by_rung[rung_of(model["id"], rungs)] = model["id"]

    # --- who is an arm, and why ------------------------------------------
    arms: list[dict] = []
    excluded: list[dict] = []
    for model in available:
        model_id = model["id"]
        rung = rung_of(model_id, rungs)
        label = rung_label(rungs, rung)
        raw_created = model.get("created_at")
        created = parse_ts(raw_created)
        age_days = (now - created).days if created else None
        is_newest = newest_by_rung.get(rung) == model_id
        old_enough = age_days is not None and age_days >= policy["cooling_off_days"]

        reason = None
        if enter_usable:
            share = usage_share(counts, model_id, enter_weeks, rungs, aliases,
                               api_ids=api_ids, previous_arms=previous_arms,
                               catalogue_seen=catalogue_seen)
            if share >= policy["arm_enter_usage_pct"]:
                reason = (f"carries {_format_share(share, policy['arm_enter_usage_pct'])}% "
                          f"of rankable census usage over the last "
                          f"{policy['arm_enter_window_weeks']} weeks "
                          f"(at or above the {policy['arm_enter_usage_pct']}% entry bar)")
        if reason is None and is_newest and old_enough:
            newest_words = (f"newest model in the {label} tier, {age_days} days old "
                            f"(past the {policy['cooling_off_days']}-day cooling-off)")
            reason = (newest_words if usable
                      else f"{stale_note}; fell back to newest per tier — {newest_words}")
        if reason is None and model_id in previous_arms:
            if not usable:
                # Staleness is not evidence of disuse. Retiring a previous arm
                # because nobody published a census retires it on NO evidence
                # — measured: an arm at 33% usage dropped when the census was
                # 21 days old. The only retirement a stale census supports is
                # a model that left the Models API, handled below.
                reason = (f"held over from the previous roster: {stale_note}, so "
                          f"there is no evidence to retire it")
            elif not exit_usable:
                # The census is fresh overall, but the EXIT window's own
                # ranked total is under one of the two floors — the same
                # "not enough evidence to act on" gap as the stale case
                # above, just scoped to this window rather than the whole
                # census. Names WHICH floor held, absolute checked first
                # (matching _census_verdict's own ordering).
                #
                # N5 (#129 review round 6): unreachable under
                # evals/roster-policy.yml's shipped numbers (see the
                # comment above `enter_raw_total`/`exit_raw_total`) — kept
                # rather than deleted, and made reachable and pinned by
                # TestIssue67Review6's two exit-side floor-note tests via
                # a test-only policy whose exit window is shorter than its
                # enter one, so this text is not dead code with no test
                # able to reach it.
                if exit_ranked_total < policy["min_ranked_turns"]:
                    floor_note = (f"an exit-window ranked, attributable total "
                                 f"of {exit_ranked_total} turn(s) over the "
                                 f"last {policy['arm_exit_window_weeks']} "
                                 f"weeks is under the "
                                 f"{policy['min_ranked_turns']}-turn floor, "
                                 f"too little to be evidence of anything")
                else:
                    pct = (100 * exit_ranked_total / exit_raw_total
                          if exit_raw_total else 0.0)
                    bar = 100 * policy["min_ranked_share"]
                    floor_note = (f"only {exit_ranked_total} of "
                                 f"{exit_raw_total} raw turns over the last "
                                 f"{policy['arm_exit_window_weeks']} weeks are "
                                 f"rankable, attributable usage "
                                 f"({_format_share(pct, bar, under=True)}% — under the "
                                 f"{bar:g}% relative floor for this window), "
                                 f"too little to be evidence of anything")
                reason = (f"held over from the previous roster: {floor_note}, so "
                          f"there is no evidence to retire it")
            else:
                held = usage_share(counts, model_id, exit_weeks, rungs, aliases,
                                  api_ids=api_ids, previous_arms=previous_arms,
                                  catalogue_seen=catalogue_seen)
                if held >= policy["arm_exit_usage_pct"]:
                    reason = (f"held over from the previous roster: still "
                              f"{_format_share(held, policy['arm_exit_usage_pct'])}% "
                              f"of rankable census usage over the last "
                              f"{policy['arm_exit_window_weeks']} weeks (at or above "
                              f"the {policy['arm_exit_usage_pct']}% exit bar)")
        if reason:
            arms.append({"id": model_id, "reason": reason})
        elif created is None:
            why = "absent" if not raw_created else "unparseable"
            excluded.append({"id": model_id, "reason": (
                f"excluded from the arm set: its created_at is {why}, so the "
                f"{policy['cooling_off_days']}-day cooling-off cannot be checked")})
        elif is_newest and not old_enough:
            excluded.append({"id": model_id, "reason": (
                f"excluded from the arm set: newest in the {label} tier but only "
                f"{age_days} days old, inside the {policy['cooling_off_days']}-day "
                f"cooling-off")})

    for snapshot_id in sorted(snapshots):
        excluded.append({"id": snapshot_id, "reason": (
            f"dated snapshot of `{snapshots[snapshot_id]}`; collapsed onto that "
            f"alias for ranking, seating and usage, so it takes no seat of its own")})

    arm_ids = {a["id"] for a in arms}

    # --- judge -------------------------------------------------------------
    # Preference order, and the last rung is not decorative: with no census the
    # arm set is "newest per tier", which on a catalogue holding one current
    # model per tier is EVERY available model — the state of the very first run,
    # before any census has been published. Emitting a null judge there would
    # ship a roster with a hole in it, so the fallback names the strongest model
    # available and says out loud that it is also an arm, leaving the caller to
    # decide rather than leaving it to find out. `is_arm` carries that in a
    # field as well as in words: run_eval.py refuses such a judge for an
    # unpinned fixture, and it cannot read prose.
    strongest_arm_rung = max((rung_of(a, rungs) for a in arm_ids), default=None)
    non_arms = [m for m in available if m["id"] not in arm_ids]
    above = ([m for m in non_arms if rung_of(m["id"], rungs) > strongest_arm_rung]
             if strongest_arm_rung is not None else [])

    if above:
        pick = above[-1]
        judge = {"id": pick["id"],
                 "reason": (f"most capable available model at least one tier above "
                            f"the strongest arm model "
                            f"({rung_label(rungs, rung_of(pick['id'], rungs))} "
                            f"over {rung_label(rungs, strongest_arm_rung)}), and "
                            f"not itself an arm")}
    elif non_arms:
        pick = non_arms[-1]
        arm_tier_words = (f" — nothing available sits above the strongest arm's "
                          f"{rung_label(rungs, strongest_arm_rung)} tier"
                          if strongest_arm_rung is not None else "")
        judge = {"id": pick["id"],
                 "reason": f"strongest available model that is not an arm{arm_tier_words}"}
    elif available:
        pick = available[-1]
        judge = {"id": pick["id"],
                 "reason": ("strongest available model — every available model is "
                            "currently an arm, so no non-arm judge exists; do not "
                            "run this model as the arm and the judge of the same run")}
    else:
        judge = {"id": None,
                 "reason": "the Models API returned no model this policy can rank"}
    judge["is_arm"] = judge["id"] in arm_ids

    # --- preflight ---------------------------------------------------------
    # Cheapest = the lowest tier the API still returns. Within it, prefer a
    # model that has cleared the cooling-off: a day-old cheapest-tier model
    # is exactly the kind an old or narrowly-scoped bearer may not yet be
    # entitled to invoke, and eval.yml's preflight step this feeds is FATAL
    # to the whole job — it used to canary on "newest in tier" with no
    # regard for age at all. Falls back to the newest regardless of age only
    # when nothing in the tier has cleared cooling-off yet: there being no
    # older model in the tier to prefer over it.
    cheapest = None
    cheapest_reason = None
    if available:
        lowest_rung = rung_of(available[0]["id"], rungs)
        rung_models = [m for m in available if rung_of(m["id"], rungs) == lowest_rung]
        label = rung_label(rungs, lowest_rung)
        cooled = []
        for m in rung_models:  # ascending order -> newest last
            created = parse_ts(m.get("created_at"))
            age_days = (now - created).days if created else None
            if age_days is not None and age_days >= policy["cooling_off_days"]:
                cooled.append(m)
        if cooled:
            cheapest = cooled[-1]
            cheapest_reason = (f"newest model in the {label} tier that is past the "
                               f"{policy['cooling_off_days']}-day cooling-off: the "
                               f"lowest tier the Models API still returns, and this "
                               f"is its cheapest safely-invocable pick")
        else:
            cheapest = rung_models[-1]
            cheapest_reason = (f"newest model in the {label} tier: the lowest tier "
                               f"the Models API still returns (still within the "
                               f"{policy['cooling_off_days']}-day cooling-off — "
                               f"nothing older in this tier has cleared it yet)")
    preflight = ({"id": cheapest["id"], "reason": cheapest_reason}
                if cheapest else {"id": None, "reason": "the Models API returned no "
                                                        "model this policy can rank"})

    # --- what moved --------------------------------------------------------
    added: list[dict] = []
    retired: list[dict] = []
    if previous is not None:
        added = [a for a in arms if a["id"] not in previous_arms]
        for model_id in previous_arms:
            if model_id in arm_ids:
                continue
            if model_id not in api_ids:
                why = "no longer returned by the Models API"
            elif model_id in unranked_ids:
                why = ("still returned by the Models API, but no family word from "
                       "the tier ladder appears in its id, so it can no longer be "
                       "ranked or seated")
            elif model_id in snapshots:
                why = (f"collapsed onto its undated alias `{snapshots[model_id]}`, "
                       f"which holds the seat")
            else:
                # Never `not usable` (nor `not exit_usable`) here: the arms
                # loop above gives every previous arm still in `available`
                # an unconditional "no evidence to retire it" reason in
                # both of those cases, which keeps it IN `arm_ids` — so a
                # previous arm reaching this `else` with `model_id not in
                # arm_ids` has always been genuinely measured against the
                # exit bar and found below it. (A prior revision carried a
                # dead `elif not usable:` branch here for exactly the case
                # this comment rules out; it could never execute.)
                held = usage_share(counts, model_id, exit_weeks, rungs, aliases,
                                  api_ids=api_ids, previous_arms=previous_arms,
                                  catalogue_seen=catalogue_seen)
                why = (f"below the {policy['arm_exit_usage_pct']}% exit bar for the last "
                       f"{policy['arm_exit_window_weeks']} weeks "
                       f"({_format_share(held, policy['arm_exit_usage_pct'], under=True)}% of "
                       f"rankable census usage)")
            retired.append({"id": model_id, "reason": why})

    # Three states, not two: `previous is not None` alone collapses "the
    # previous roster was there but unreadable" into the same false as
    # "there is no previous roster (first run)" — the exact gap that let the
    # published JSON and the rendered Markdown disagree about what happened,
    # since main() derived the Markdown's state from `previous_problem`
    # directly while the JSON only ever recorded the boolean. Publishing the
    # state itself means every caller reads the same fact.
    previous_state = ("unavailable" if previous_problem
                      else "compared" if previous is not None else "none")

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "models_api_at": (models_doc or {}).get("fetched_at"),
            "census_at": census_at_published,
            "admin_report_at": (admin_doc or {}).get("fetched_at") if admin_doc else None,
        },
        "arms": arms,
        "judge": judge,
        "preflight": preflight,
        "unranked": unranked,
        "excluded": excluded,
        "compared_to_previous": previous_state == "compared",
        "previous_state": previous_state,
        "retired_since_last": retired,
        "added_since_last": added,
        "catalogue_seen": catalogue_seen_entries,
    }


def render_summary(roster: dict, previous_state: str = "auto") -> str:
    """Markdown for $GITHUB_STEP_SUMMARY. A roster change leads.

    `previous_state` is "auto" (read the roster's own `previous_state`
    field — this is what every real caller does now that compute_roster
    fills it in, so the JSON and this Markdown cannot disagree) or an
    explicit override ("unavailable", "compared", "none") for exercising one
    state in isolation. The three cases are NOT interchangeable: printing
    "No change to the arm set since the last run" on a first run, or when
    the comparison never happened, is a claim about a comparison nobody made.
    """
    lines = ["### Model roster", ""]
    changed = roster["added_since_last"] or roster["retired_since_last"]
    if previous_state == "auto":
        previous_state = (roster.get("previous_state") or
                          ("compared" if roster.get("compared_to_previous")
                           else "none"))
    if previous_state == "unavailable":
        lines += ["**Roster inputs unavailable** — the previous roster could not "
                  "be read this run, so nothing was compared against it.", ""]
    elif changed:
        lines.append("**Roster changed since the last run.**")
        for entry in roster["added_since_last"]:
            lines.append(f"- added `{entry['id']}` — {entry['reason']}")
        for entry in roster["retired_since_last"]:
            lines.append(f"- retired `{entry['id']}` — {entry['reason']}")
        lines.append("")
    elif previous_state == "compared":
        lines += ["No change to the arm set since the last run.", ""]
    else:
        lines += ["First published roster here — no previous roster to compare "
                  "against.", ""]

    lines += ["| Role | Model | Why |", "| --- | --- | --- |"]
    for arm in roster["arms"]:
        lines.append(f"| arm | `{arm['id']}` | {arm['reason']} |")
    for role in ("judge", "preflight"):
        entry = roster[role]
        lines.append(f"| {role} | `{entry['id']}` | {entry['reason']} |")
    for role, entries in (("unranked", roster.get("unranked") or []),
                          ("excluded", roster.get("excluded") or [])):
        for entry in entries:
            lines.append(f"| {role} | `{entry['id']}` | {entry['reason']} |")
    if roster["judge"].get("is_arm"):
        lines += ["", "> **The judge is also an arm this run.** Do not run it as "
                      "the arm and the judge of the same eval."]
    source = roster["source"]
    lines += ["", f"Models API `{source['models_api_at']}` · census "
                  f"`{source['census_at'] or 'none'}` · admin report "
                  f"`{source['admin_report_at'] or 'none'}`", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", required=True, type=Path,
                        help="models document from scripts/refresh_models.py")
    parser.add_argument("--policy", type=Path,
                        default=Path(__file__).resolve().parent.parent / "evals" / "roster-policy.yml")
    parser.add_argument("--census", type=Path, default=None,
                        help="usage/latest.json from eval-results; optional")
    parser.add_argument("--admin-report", type=Path, default=None,
                        help="optional Admin API usage report; recorded as provenance")
    parser.add_argument("--previous", type=Path, default=None,
                        help="the last published roster/latest.json; optional")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    models_doc, problem = read_json(args.models)
    if models_doc is None:
        print(problem or f"no models document at {args.models}", file=sys.stderr)
        return 1

    policy = load_policy(args.policy)
    try:
        validate_policy(policy)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    census_doc, census_problem = read_json(args.census)
    if census_problem:
        _stderr(census_problem)
    previous_doc, previous_problem = read_json(args.previous)
    if previous_problem:
        _stderr(previous_problem)

    roster = compute_roster(
        models_doc=models_doc,
        census_doc=census_doc,
        policy=policy,
        previous=previous_doc,
        now=datetime.now(timezone.utc),
        admin_doc=load_json(args.admin_report),
        census_problem=census_problem,
        previous_problem=previous_problem,
    )

    if not roster["arms"]:
        # A roster with no arms is not a roster. It used to exit 0 and publish
        # an empty arm set — a run that silently evaluated nothing, which is
        # exactly the "went stale without anyone noticing" failure #67 exists
        # to remove. Nothing is written, so the last good roster stands.
        print("refusing to publish a roster with no arms: every ranked model is "
              "excluded (see the excluded/unranked reasons above)", file=sys.stderr)
        for entry in roster["excluded"] + roster["unranked"]:
            print(f"  {entry['id']}: {entry['reason']}", file=sys.stderr)
        return 3

    # Written via a temp file in the same directory and renamed: a partial
    # roster is worse than no roster, and the caller's "did the file appear?"
    # is the only signal the commit step has.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    staged = args.out.with_name(args.out.name + ".partial")
    with open(staged, "w", encoding="utf-8") as f:
        json.dump(roster, f, indent=2)
        f.write("\n")
    staged.replace(args.out)

    print(render_summary(roster))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
