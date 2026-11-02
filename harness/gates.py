#!/usr/bin/env python3
"""The skill retirement verdict (#70, part 1): cells, their classes, and the
verdict over them. Thresholds live in `evals/gate-policy.yml`.

Guidance sections (#124) get the same verdict over their ablation pair
(`guidance_verdict`, at the end of this module): the rules below apply with
"skill" read as "section".

POOLED EVIDENCE (Adam, 2026-10-25), replacing #70's four weekly sweeps.

  * A CELL is (skill, fixture, current roster arm model), for every fixture
    of the skill ON MAIN (scripts/compute_gates.py enumerates them from the
    evals directory) and every arm model of the roster it is given
    (`--roster`). A cell with no run is `missing`; runs of a fixture no
    longer on main, or of a model no longer on the roster, are not read: the
    roster follows current use (Adam, 2026-10-25), so a superseded model
    leaves at once and no evidence is asked of it. A fixture moved to a
    new name with its content unchanged keeps its runs (`FIXTURE_ALIASES`,
    digest-checked by `pooled_fixture`). The arm
    model is the REQUESTED one: `cross_model.model`, which
    harness/run_eval.py writes from the arm's own `--model`
    (`_write_summary`'s `agent_model`) and `run_eval._arm_model` reads back;
    never `models_used`, which includes subagent models.
  * THE UNIT IS THE RUN. Trials within one run are near-identical, so each
    arm of each run is reduced to its mean trial pass rate (and mean judge
    figure), and every interval is over those run means. A run counts for an
    arm only with at least `MIN_TRIALS_PER_RUN` (1, round 5: the weekly
    sweep fires one trial per run) scored trials in that arm.
  * THE ARMS ARE TWO INDEPENDENT SAMPLES of ONE comparison, pooled
    (`pool_cells`, the one function that decides which runs a cell holds)
    against the content ON MAIN, never the newest run's:
      - with arm: the skill's `tested_digest` as the registry checkout gives
        it and the fixture's `fixture_digest` as the evals directory gives it
        (both computed by compute_gates with the functions run_eval uses);
      - without arm: the same fixture digest. It does not hold the subject,
        so it pools across `tested_digest` changes.
    Their arm contexts (`arm_context.skills_digest` and `guidance_digest`)
    are chosen JOINTLY (`_joint_context`, round 5, B6): only a with group
    and a without group sharing a pair key, the same non-subject skills
    (`arm_context.others_digest`) and frozen guidance
    (`context.guidance.digest`), can form the cell, and of those pairs the
    one with the most runs in its smaller arm, on roster models, is chosen;
    a tie on that count goes to the pair with the newer newest run, and
    only a full tie, or no such pair, chooses none and the cell is
    `insufficient`. So
    a without arm from older guidance cannot be pooled against a with arm
    from newer guidance. The arm context cannot be computed from main (it
    is the frozen context a run deployed), so the pair with the most runs
    chooses it, and an honest context change counts once its pair
    outnumbers the old one.
    Any key unknown (no registry given, the skill not found in one, the
    fixture not tracked in Git) makes the cell `insufficient`; there is no
    pool-everything fallback.
  * WHICH RUNS COUNT. Every validated run, whatever its billing, runner or
    location (#370); the verdict records each used run's `run` block and
    links its report. Validation is scripts/compute_gates.py's: a summary of
    the wrong shape skips its run with a reason (`MalformedSummary`), never a
    crash.
  * FIXTURE CLASS. No fixture carries a machine-readable class; DESIGN.md
    ("Four instruments, one harness") says a Class C fixture "says so in its
    `judge:` block: `mode: pairwise`". So a fixture is JUDGE-CARRIED (Class
    C) when its `judge.mode` is pairwise (`run_eval._judge_is_pairwise`) or
    it has no objective checks; when the fixture file is not available, when
    any trial's judge result is pairwise. compute_gates sets
    `judge_carried` on each run.

THE NUMBERS. A trial's pass rate is its checks passed over checks scored; its
judge figure is `overall` of an absolute result and `dimensions_mean` of a
pairwise one, a number from 0 to 10 (a skipped or failed judge result has
none). A trial with a FAILED check whose detail starts with the scorer's
own marker (`INFRASTRUCTURE_DETAIL_PREFIX`), or whose error type is one
(`INFRASTRUCTURE_ERRORS`), is an infrastructure error and is left out;
run_eval still scores it as it does today, the reclassification is made
here. Any other errored trial (an agent failure, a timeout, a budget stop)
is the agent's: it scores 0 on every check of the cell and has no judge
figure, since dropping it, or its run, would compare only the trials that
went well. A cell with any such trial can never be `no-benefit` (at most
`insufficient`; it can still show `benefit`), so errors can only help keep.
An arm of a run COUNTS when it has `MIN_TRIALS_PER_RUN` scored or
agent-errored trials and no scored trial without check results on a fixture
that has checks (`NO_CHECKS_REASON`, which also keeps the cell from
`no-benefit`); each cell records, under `skipped`, why its other runs did
not count. An arm's run mean is the mean of those trials' pass rates. Its
run judge figure is the mean of its trials' judge figures, and exists only
when every one of those trials has a figure. A cell's judge figures are
usable when no counted run judged conditionally (`judge_conditional` true:
run_eval skips the judge when the with arm is already ahead on the
objective, so conditional scores alone are a sample biased toward no
benefit), or when every counted run of both arms has its figure, so no
judge call was skipped and nothing was selected out. A delta is mean(with run means) - mean(without
run means).

THE BOUNDS (`confidence_sequence`; Adam, 2026-10-31: decide on confidence
alone, with no minimum run count and no fixed looks). A two-sided
normal-mixture confidence sequence (Robbins) over the delta of run means: it
holds at every run count at once, so a cell is checked after every run
without the repeated looks inflating its error rate. Its standard error uses
each arm's MODERATED variance (`moderated_variance`): `prior_strength`
pseudo-runs at the prior, the run-to-run variance measured across every
evaluation of the same kind (`run_priors`: every skill's runs, or every
guidance section's, grouped by skill, fixture, model, arm and content, and
pooled by `pooled_variance`), plus the cell's own n - 1 at its own sample
variance. So one run on each arm can decide a large enough difference, and a
cell's own spread takes over as its runs grow. The objective, judge and
per-check figures each have their own prior. The normal-mixture boundary
treats the moderated variance as known, so its anytime guarantee is
approximate, and it is two-sided, so using one end of it is conservative.
Levels: benefit uses the `benefit_confidence` sequence's lower end; no-benefit
the `retire_confidence` sequence's upper end; a check the
`check_confidence` sequence's lower end, Holm-corrected across the
fixture's checks (`confident_checks`).

A CELL'S CLASS (`_classify`), first match wins:

  1. `insufficient`: an arm has no counted run.
  2. `cannot-discriminate`: some check fails in every scored trial of BOTH
     arms, or both arms' pooled pass rate <= `floor_fraction`.
  3. `benefit`: the objective delta's lower bound > 0; or some check
     confidently better with the skill (Holm); or, when the objective shows
     no confident gain, the judge delta's lower bound > 0. A judge-carried
     fixture keeps on any of the three too: its judge decides, but its
     objective checks are evidence of benefit. The judge figure is usable
     with one judged run on each arm (see THE NUMBERS for conditional runs).
  4. `ceiling`: both arms' pooled pass rate >= `ceiling_fraction`; for a
     judge-carried fixture, both arms' mean judge figure >= `judge_ceiling`.
  5. `no-benefit`: the objective delta's `retire_confidence` upper bound <
     `objective_margin`, and the judge delta's < `judge_margin`; the judge
     figure must be usable, since rule 3 only reached it when the objective
     showed no confident gain. A judge-carried fixture needs the judge's
     bound, and the objective's too whenever it has objective checks;
     without checks, the judge's alone. A removal also needs the counted
     runs to show `min_cli_versions` `harness.version`s; with fewer it is
     `insufficient`.
  6. `insufficient`: the evidence is not tight yet.

`classify_cell` classifies a cell over all its counted runs, ordered by
(timestamp, path). Nothing is carried from an earlier evaluation, and since
every run is within the current pooling key, new content starts over.
scripts/compute_gates.py reads no run stamped after its `--as-of`, so an
evaluation can be repeated as of a time. A run is named by `run_key`,
`<path>#<fixture>#<role>`.

THE VERDICT (`retirement`), over every fixture on main x every current roster
arm model: any `benefit` -> `keep`; any `insufficient` or missing cell, or no
fixture on main -> `insufficient`; any `cannot-discriminate` ->
`cannot-discriminate`; any `ceiling` -> `ceiling`; `retire` only when there is at least one cell and
every cell is `no-benefit` (no roster model means no cell, never a
retirement); anything else `insufficient`. scripts/compute_gates.py then lets
one skill retire per evaluation. A standing retirement's stickiness, and
holding the one slot while a removal pull request is open, are part 2's: it
reads the open pull requests from GitHub rather than trusting an earlier
gates file.

IN-SITU GUIDANCE CELLS (#557; Adam's D5, 2026-11-02, via #546): compared
WITHIN runs that share the same rest-of-guidance digest, then combined,
instead of keeping one same-rest group (`_joint_context`). `pool_cells`
with `strata` groups a cell's current-content runs by `pair_key`;
`classify_strata` drops a stratum without a counted run on each arm and runs
`_classify` over the rest with each delta a precision-weighted
`stratified_estimate` and the counts pooled. The cell's priors are its own
(`cell_priors`, 20 degrees of freedom before a measured value replaces the
0.25 fallback; scripts/simulate_stratified_pooling.py). The pooled bounds
decide, with no separate confirmation beside the rest on main (Adam,
2026-11-02: remove at 90% confidence that the section does not improve
results by 0.15 or more, the guidance block of evals/gate-policy.yml).
Skills and the alone pair are pooled exactly as before.

KNOWN LIMITS, left for a later part:

  * Holm's m counts every check the fixture has, including checks constant
    in both arms that can never be confident, so the per-check keep is
    harder than it needs to be (Tarone's method would leave them out).
  * Scorer and harness changes are not part of the pooling key: runs scored
    before and after a scorer fix pool together.
  * A run's `tested_digest` is main's copy of the skill when the run fired
    (skills-evals#559; ADR 0012, addendum "main's copy"), and the gate
    compares it with main's copy when the gates run. A skill edit in between
    stops both arms pooling until a new with run lands (insufficient, never
    a wrong retire); runs made before #559 tested the deployed copy and pool
    only where it equals main's. Real-work fixtures
    (evals/real-work/, `subject: any`) are not a skill's fixtures on main,
    so their runs are not read.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import yaml

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "evals" / "gate-policy.yml"
#: Where a report path in the results tree is published.
RESULTS_BLOB = ("https://github.com/Adam-S-Daniel/skills-evals/blob/"
                "persistent/eval-results/")
MODES = ("auto", "proposal")
#: Scored trials an arm of one run needs to count (#70's 3).
MIN_TRIALS_PER_RUN = 1
#: Trial error types that are the harness's, not the agent's.
INFRASTRUCTURE_ERRORS = ("scorer_unavailable", "scorer_sandbox_unavailable",
                         # A guidance arm whose delivery was not proved
                         # (harness/run_eval.py `_guard_error`, and a hook
                         # that never wrote its block): INCONCLUSIVE, never
                         # the agent's failure.
                         "delivery_failed", "guard_error", "guard_miss",
                         "guard_contaminated",
                         # Its own session's receipt disagreed (#139).
                         "delivery_unproven", "receipt_contaminated")
#: The start of a FAILED check's detail that names a scorer failure rather
#: than anything the agent did: harness/scorers/commands.py's
#: `ScorerSandboxUnavailable` message, `scorer_sandbox_unavailable exit=<n>`,
#: which command_succeeds and repo_tests return as the check's detail. Only
#: the start counts: an agent's own text elsewhere in a detail cannot make
#: its trial an infrastructure error. (A missing bash parser,
#: `parser_unavailable`, already errors the trial in run_eval as
#: `scorer_unavailable`.)
INFRASTRUCTURE_DETAIL_PREFIX = "scorer_sandbox_unavailable exit="
#: Why a run with a scored trial that has no check result does not count.
NO_CHECKS_REASON = "a trial without objective checks on a fixture that has them"
#: Fixtures moved from the flat `evals/<skill>/` into a named subdirectory
#: with their content unchanged (#422, #427): {(skill, old name, "" for
#: flat): new name}. A run recorded under the old name pools with the new
#: one only while its `fixture_digest` equals the new fixture's digest on
#: main (`pooled_fixture`), so an alias never joins different content.
FIXTURE_ALIASES = {
    ("review-bash-ci-reliability", ""): "release-pipeline",
    ("vendor-release-impact-issues", ""): "issue-hygiene",
    ("workflow-path-audit", ""): "required-check-routing",
}


class GatePolicyError(ValueError):
    """The gate policy is missing, unreadable or breaks a rule."""


def _number(low, high, *, low_open=False, high_open=False):
    def check(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value):
            return False
        above = value > low if low_open else value >= low
        below = value < high if high_open else value <= high
        return above and below
    return check


def _count(low):
    return lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= low


_LEVEL = ("a number above 0.5 and below 1",
          _number(0.5, 1, low_open=True, high_open=True))
#: Each scalar key, its rule in words, and the rule.
SKILL_KEYS = {
    "objective_margin": ("a number from 0 to 1", _number(0, 1)),
    "judge_margin": ("a number from 0 to 10", _number(0, 10)),
    "benefit_confidence": _LEVEL,
    "retire_confidence": _LEVEL,
    "check_confidence": _LEVEL,
    "min_cli_versions": ("an integer of at least 1", _count(1)),
    "prior_strength": ("a number above 0", _number(0, math.inf, low_open=True,
                                                   high_open=True)),
    "ceiling_fraction": ("a number above 0 and at most 1",
                         _number(0, 1, low_open=True)),
    "judge_ceiling": ("a number above 0 and at most 10",
                      _number(0, 10, low_open=True)),
    "floor_fraction": ("a number from 0 and below 1", _number(0, 1, high_open=True)),
}


def parse_gate_policy(text: str) -> dict:
    """{"skills": {...}, "guidance": {...} or None} from `text`, or
    GatePolicyError naming the key. `guidance:` (skills-evals#124) is
    optional and has the same keys and rules as `skills:`, kept apart so the
    two can diverge; without it no guidance verdict is computed.

    A missing or invalid `retirement_mode` is `proposal`, the mode that
    removes nothing on its own."""
    try:
        document = yaml.safe_load(text)
    except (yaml.YAMLError, ValueError):
        # PyYAML raises a bare ValueError for a date-shaped scalar that is
        # not a date (2026-13-05).
        raise GatePolicyError("gate policy is not valid YAML") from None
    if not isinstance(document, dict) or "skills" not in document \
            or not set(document) <= {"skills", "guidance"}:
        raise GatePolicyError("gate policy must be a mapping with the key skills "
                              "and optionally guidance")
    return {"skills": _policy_block(document["skills"], "skills"),
            "guidance": (_policy_block(document["guidance"], "guidance")
                         if "guidance" in document else None)}


def _policy_block(block, name: str) -> dict:
    """One block of thresholds (`skills:` or `guidance:`), checked."""
    if not isinstance(block, dict):
        raise GatePolicyError(f"gate policy {name} must be a mapping")
    unknown = sorted(set(block) - set(SKILL_KEYS) - {"retirement_mode"})
    if unknown:
        raise GatePolicyError(f"gate policy {name} has unknown keys {unknown}")
    out = {}
    for key, (words, valid) in SKILL_KEYS.items():
        if key not in block:
            raise GatePolicyError(f"gate policy {name} is missing {key}")
        if not valid(block[key]):
            raise GatePolicyError(f"gate policy {name}.{key} must be {words}")
        out[key] = block[key]
    mode = block.get("retirement_mode")
    out["retirement_mode"] = mode if mode in MODES else "proposal"
    return out


def load_gate_policy(path: Path | None = None) -> dict:
    """`parse_gate_policy` of the file at `path` (default evals/gate-policy.yml)."""
    path = Path(path) if path is not None else DEFAULT_POLICY
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise GatePolicyError(f"gate policy {path.name} could not be read") from None
    return parse_gate_policy(text)


# ---------------------------------------------------------------------------
# Statistics.

def _is_number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _mean(values) -> float:
    return math.fsum(values) / len(values)


def _finite_sum(values) -> float | None:
    """`math.fsum` of `values`, or None when one is None or the sum is not a
    finite number (two costs of 1e308 overflow)."""
    if any(v is None for v in values):
        return None
    try:
        total = math.fsum(values)
    except OverflowError:
        return None
    return total if math.isfinite(total) else None


def _constant(values) -> bool:
    return min(values) == max(values)


def _variance(values: list) -> float:
    if len(values) < 2 or _constant(values):
        return 0.0  # exactly, not the rounding residue of the mean
    mean = _mean(values)
    return math.fsum((v - mean) ** 2 for v in values) / (len(values) - 1)


#: The prior variance when no group has two runs to measure one: a run-mean
#: standard deviation of 0.25, wider than any group measured on 2026-10-31.
FALLBACK_PRIOR_VARIANCE = 0.0625
#: The least prior variance, so a history of identical runs cannot make the
#: prior claim certainty (a run-mean standard deviation of 0.01).
MIN_PRIOR_VARIANCE = 1e-4
#: The prior guard of an in-situ guidance cell (#546, #557, `cell_priors`):
#: the least degrees of freedom a measured prior needs, and the fallback
#: below them, the largest variance of a figure from 0 to 1. In
#: scripts/simulate_stratified_pooling.py a prior measured on a few runs
#: broke both error targets and these met them; the prior is measured per
#: cell because one pooled from other, lower-variance cells did not.
GUIDANCE_PRIOR_MIN_DF = 20
GUIDANCE_FALLBACK_PRIOR_VARIANCE = 0.25


def pooled_variance(groups: list, min_df: int = 1,
                    fallback: float = FALLBACK_PRIOR_VARIANCE) -> float:
    """The pooled run-to-run variance over `groups` (each a list of run
    figures of one model, fixture, arm and content): the sum of squared
    deviations over the summed degrees of freedom, from every group with two
    or more runs. `fallback` (default `FALLBACK_PRIOR_VARIANCE`) when none
    has or they hold fewer than `min_df` degrees of freedom (#546: a prior
    measured on a few runs can be far too small), and never under
    `MIN_PRIOR_VARIANCE`."""
    df = sum(len(g) - 1 for g in groups if len(g) >= 2)
    if not df or df < min_df:
        return fallback
    ss = math.fsum(_variance(g) * (len(g) - 1) for g in groups if len(g) >= 2)
    return max(ss / df, MIN_PRIOR_VARIANCE)


def moderated_variance(values: list, prior: float, strength: float) -> float:
    """An arm's run-to-run variance, shrunk toward the prior: `strength`
    pseudo-degrees of freedom at `prior` plus the arm's own n - 1 at its
    sample variance. One run gives the prior; many runs give their own
    spread."""
    own = len(values) - 1
    return (strength * prior + own * _variance(values)) / (strength + own)


def confidence_sequence(a: list, b: list, level: float, prior: float,
                        strength: float) -> tuple[float, float]:
    """(lower, upper) of mean(a) - mean(b), two-sided at `level` and valid
    at every run count however often it is checked: the normal-mixture
    boundary (Robbins), |d - delta| <= sqrt((I + r) log((I + r) / (r alpha^2))) / I,
    with I = 1/se^2 the information so far and r = 1/prior the information
    of one run on each arm. The standard error comes from each arm's
    `moderated_variance`, so a spread measured across all evaluations stands
    in for the few runs a cell has. Needs a run on each arm."""
    if not a or not b:
        raise ValueError("a confidence sequence needs a run on each arm")
    se2 = (moderated_variance(a, prior, strength) / len(a)
           + moderated_variance(b, prior, strength) / len(b))
    delta = _mean(a) - _mean(b)
    info, rho, alpha = 1 / se2, 1 / prior, 1 - level
    half = math.sqrt((info + rho) * math.log((info + rho) / (rho * alpha * alpha))) / info
    return delta - half, delta + half


def confidence_reached(a: list, b: list, prior: float, strength: float,
                       distance: float) -> float:
    """The highest level at which `confidence_sequence(a, b, level, ...)`
    still clears a bound `distance` away from mean(a) - mean(b): solving
    half(alpha) = distance for alpha, alpha = sqrt((I + r) / r) *
    exp(-distance^2 I^2 / (2 (I + r))), and the level is 1 - alpha. With
    `distance` = delta it is the confidence that the delta is above 0; with
    `distance` = margin - delta, that it is under the margin. 0 when the
    point estimate is already on the wrong side. Needs a run on each arm."""
    if not a or not b:
        raise ValueError("a confidence sequence needs a run on each arm")
    if distance <= 0:
        return 0.0
    se2 = (moderated_variance(a, prior, strength) / len(a)
           + moderated_variance(b, prior, strength) / len(b))
    info, rho = 1 / se2, 1 / prior
    alpha = math.sqrt((info + rho) / rho) * math.exp(
        -distance * distance * info * info / (2 * (info + rho)))
    return max(0.0, 1 - alpha)


def confidence_reached_info(info: float, prior: float, distance: float) -> float:
    """`confidence_reached` from an information I directly (#557): the
    level at which a sequence with information `info` still clears a bound
    `distance` away. For a `stratified_estimate`."""
    if distance <= 0:
        return 0.0
    rho = 1 / prior
    alpha = math.sqrt((info + rho) / rho) * math.exp(
        -distance * distance * info * info / (2 * (info + rho)))
    return max(0.0, 1 - alpha)


def keep_p(delta: float, info: float, prior: float) -> float:
    """The two-sided alpha at which a sequence with estimate `delta` and
    information `info` has its lower end at 0 (`confidence_reached_info`
    inverted): 1 when `delta` <= 0. A keep test's p-value (#557 follow-up)."""
    if delta <= 0:
        return 1.0
    rho = 1 / prior
    return min(1.0, math.sqrt((info + rho) / rho) * math.exp(
        -delta * delta * info * info / (2 * (info + rho))))


def _stratum(a: list, b: list, prior: float, strength: float) -> tuple[float, float]:
    """(mean(a) - mean(b), its information 1/se^2) from each arm's
    `moderated_variance`."""
    se2 = (moderated_variance(a, prior, strength) / len(a)
           + moderated_variance(b, prior, strength) / len(b))
    return _mean(a) - _mean(b), 1 / se2


def stratified_estimate(strata: list, prior: float, strength: float) -> tuple[float, float]:
    """(d, I): the precision-weighted delta over `strata`, a list of (a, b)
    run-figure lists sharing one rest-of-guidance digest each (#546), and its
    information. Each stratum's weight P_s is its own 1/se^2, so Z = sum
    P_s d_s, I = sum P_s and d = Z / I. Every stratum needs a run on each
    arm. P_s is re-estimated at each look, so the boundary fed this (d, I)
    is approximately anytime-valid, in the same sense as a single cell's."""
    if not strata:
        raise ValueError("a stratified estimate needs a stratum")
    parts = [_stratum(a, b, prior, strength) for a, b in strata]
    info = math.fsum(p for _, p in parts)
    return math.fsum(p * d for d, p in parts) / info, info


def _half_width(info: float, prior: float, alpha: float) -> float:
    rho = 1 / prior
    return math.sqrt((info + rho) * math.log((info + rho) / (rho * alpha * alpha))) / info


def stratified_sequence(strata: list, level: float, prior: float,
                        strength: float) -> tuple[float, float]:
    """`confidence_sequence` over `stratified_estimate`'s (d, I). One stratum
    is exactly `confidence_sequence` of its two arms."""
    if len(strata) == 1:
        return confidence_sequence(*strata[0], level, prior, strength)
    delta, info = stratified_estimate(strata, prior, strength)
    half = _half_width(info, prior, 1 - level)
    return delta - half, delta + half


def confident_checks(with_rates: dict, without_rates: dict, level: float,
                     priors: dict, strength: float) -> list:
    """Check keys whose with-minus-without delta of per-run pass rates has a
    lower bound above 0, Holm-corrected across every check in both arms:
    ordered by the delta over its standard error, the k-th (from 0) is
    tested at two-sided level 1 - (1 - level) / (m - k) and the procedure
    stops at the first that fails. `priors` maps a check to its prior
    variance."""
    keys = sorted(set(with_rates) & set(without_rates))
    alpha, m = 1 - level, len(keys)
    ranked = []
    for key in keys:
        a, b = with_rates[key], without_rates[key]
        if not a or not b:
            continue
        prior = priors.get(key, FALLBACK_PRIOR_VARIANCE)
        se = math.sqrt(moderated_variance(a, prior, strength) / len(a)
                       + moderated_variance(b, prior, strength) / len(b))
        ranked.append((-(_mean(a) - _mean(b)) / se, key))
    confident = []
    for k, (_, key) in enumerate(sorted(ranked)):
        prior = priors.get(key, FALLBACK_PRIOR_VARIANCE)
        if confidence_sequence(with_rates[key], without_rates[key],
                               1 - alpha / (m - k), prior, strength)[0] <= 0:
            break
        confident.append(key)
    return confident


def stratified_confident_checks(strata: list, level: float, priors: dict,
                                strength: float) -> list:
    """`confident_checks` over strata (#546): `strata` is a list of
    (with_rates, without_rates) per rest-of-guidance stratum. A check's
    figure is `stratified_estimate` over the strata where it has a run on
    each arm; Holm's m counts every check in both arms of any stratum, as
    `confident_checks` counts them. One stratum is exactly
    `confident_checks`."""
    if len(strata) == 1:
        return confident_checks(*strata[0], level, priors, strength)
    keys = sorted({k for w, o in strata for k in set(w) & set(o)})
    alpha, m = 1 - level, len(keys)
    per_key, ranked = {}, []
    for key in keys:
        parts = [(w[key], o[key]) for w, o in strata
                 if key in w and key in o and w[key] and o[key]]
        if not parts:
            continue
        per_key[key] = parts
        prior = priors.get(key, FALLBACK_PRIOR_VARIANCE)
        delta, info = stratified_estimate(parts, prior, strength)
        ranked.append((-delta * math.sqrt(info), key))
    confident = []
    for k, (_, key) in enumerate(sorted(ranked)):
        prior = priors.get(key, FALLBACK_PRIOR_VARIANCE)
        if stratified_sequence(per_key[key], 1 - alpha / (m - k), prior,
                               strength)[0] <= 0:
            break
        confident.append(key)
    return confident


# ---------------------------------------------------------------------------
# Trials and runs.

class MalformedSummary(ValueError):
    """A trial summary that is not the shape run_eval writes: its run is
    skipped, never scored around and never a crash."""


def check_key(check_id) -> str:
    """A check id as a string key: a fixture may write any YAML value as one."""
    return json.dumps(check_id, sort_keys=True)


#: The reason run_eval records when it skips a pair's judge because the with
#: arm is strictly ahead on the objective (harness/run_eval.py
#: `JUDGE_SKIPPED`).
JUDGE_SKIP_WITH_AHEAD = "objective-decided"


def trial_record(summary: dict) -> dict:
    """What a cell needs from one trial summary, or MalformedSummary. A
    cost that is not a finite number from 0 up is unknown."""
    agent = summary.get("agent")
    if agent is not None and not isinstance(agent, dict):
        raise MalformedSummary("agent is not a mapping")
    cost = agent.get("cost_usd") if isinstance(agent, dict) else None
    out = {"cost_usd": cost if _is_number(cost) and cost >= 0 else None}
    checks = summary.get("objective_checks")
    if checks is None:
        checks = []
    if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
        raise MalformedSummary("objective_checks is not a list of mappings")
    error = summary.get("error")
    infra = any(c.get("passed") is False and isinstance(c.get("detail"), str)
                and c["detail"].startswith(INFRASTRUCTURE_DETAIL_PREFIX)
                for c in checks) or (isinstance(error, dict)
                                     and error.get("type") in INFRASTRUCTURE_ERRORS)
    if infra:
        return {**out, "scored": False, "infrastructure": True, "errored": False}
    if error:
        # The agent's failure (a timeout, a budget stop): it scores 0 on
        # every check and has no judge figure (`run_numbers`).
        return {**out, "scored": False, "infrastructure": False, "errored": True,
                "checks": {}, "judge": None, "pairwise": False}
    if not all(isinstance(c.get("passed"), bool) for c in checks):
        raise MalformedSummary("a check's passed is not true or false")
    judge = summary.get("judge")
    if judge is not None and not isinstance(judge, dict):
        raise MalformedSummary("judge is not a mapping")
    pairwise = isinstance(judge, dict) and judge.get("mode") == "pairwise"
    figure = None
    if isinstance(judge, dict) and "error" not in judge \
            and judge.get("status") != "skipped":
        figure = judge.get("dimensions_mean") if pairwise else judge.get("overall")
        if figure is not None and not (_is_number(figure) and 0 <= figure <= 10):
            raise MalformedSummary("judge figure is not a number from 0 to 10")
    record = {**out, "scored": True, "infrastructure": False, "errored": False,
              "checks": {check_key(c.get("id")): c["passed"] for c in checks},
              "judge": figure, "pairwise": pairwise}
    if isinstance(judge, dict) and judge.get("status") == "skipped" \
            and judge.get("reason") == JUDGE_SKIP_WITH_AHEAD:
        # run_eval's conditional judge skipped this pair because its with arm
        # was strictly ahead on the objective (#557 reads it; nothing else).
        record["judge_skipped_with_ahead"] = True
    return record


def run_numbers(trials: list, judge_unconditional: bool, check_ids=(),
                has_checks: bool = False) -> dict:
    """One arm of one run, reduced: whether it counts (`skip_reason` None:
    `MIN_TRIALS_PER_RUN` scored or agent-errored trials, and no scored trial
    without check results when the fixture has checks, `has_checks`), its
    run mean, its run judge figure (when every one of those trials has one;
    `judge_conditional` records whether the call was conditional, which
    `_classify` weighs) and whether those figures differ, its
    per-check pass rates and its pooled counts. An agent-errored trial scores
    0 on every check of `check_ids` (the cell's checks) and has no judge
    figure; an infrastructure error is left out."""
    check_ids = sorted(check_ids)
    errored = [t for t in trials if t.get("errored")]
    scored = [t for t in trials if t.get("scored")] + [
        {**t, "checks": {k: False for k in check_ids}} for t in errored]
    if (has_checks or check_ids) and any(not t["checks"] for t in scored
                                         if not t.get("errored")):
        skip = NO_CHECKS_REASON
    elif len(scored) < MIN_TRIALS_PER_RUN:
        skip = f"fewer than {MIN_TRIALS_PER_RUN} scored or errored trials"
    else:
        skip = None
    rates = [sum(t["checks"].values()) / len(t["checks"]) for t in scored if t["checks"]]
    figures = [t["judge"] for t in scored]
    judged = len(scored) >= MIN_TRIALS_PER_RUN and None not in figures
    per_check: dict = {}
    for t in scored:
        for key, passed in t["checks"].items():
            per_check.setdefault(key, []).append(passed)
    costs = [t["cost_usd"] for t in trials if t.get("cost_usd") is not None]
    cost = _finite_sum(costs)
    return {"scored_trials": len(scored), "errored_trials": len(errored),
            "counted": skip is None, "skip_reason": skip,
            "judge_conditional": not judge_unconditional,
            "run_mean": _mean(rates) if rates else None,
            "judge_mean": _mean(figures) if judged else None,
            "judge_spread": bool(judged and not _constant(figures)),
            "judge_figures": figures if judged else None,
            "check_rates": {k: sum(v) / len(v) for k, v in per_check.items()},
            "check_passed": {k: sum(v) for k, v in per_check.items()},
            "check_n": {k: len(v) for k, v in per_check.items()},
            "passed": sum(sum(t["checks"].values()) for t in scored),
            "total": sum(len(t["checks"]) for t in scored),
            "cost_usd": cost,
            "cost_unknown_trials": (len(trials) - len(costs)) if cost is not None
            else len(trials)}


def _numbers(run: dict) -> dict:
    return run.setdefault("numbers", run_numbers(run["trials"],
                                                 run.get("judge_conditional") is False))


def prime(runs: list) -> None:
    """Reduce every run of one cell (`run_numbers`) against the cell's own
    checks: the check ids any scored trial of either arm reports, and
    whether the fixture has checks at all (a run's `fixture_checks`, which
    compute_gates reads from fixture.yaml, or any check result)."""
    check_ids = {k for r in runs for t in r["trials"] if t.get("scored")
                 for k in t["checks"]}
    has_checks = bool(check_ids) or any(r.get("fixture_checks") for r in runs)
    for run in runs:
        run["numbers"] = run_numbers(run["trials"], run.get("judge_conditional") is False,
                                     check_ids, has_checks)


# ---------------------------------------------------------------------------
# Cells.

def _arm_summary(runs: list) -> dict:
    passed = sum(r["numbers"]["passed"] for r in runs)
    total = sum(r["numbers"]["total"] for r in runs)
    means = [r["numbers"]["run_mean"] for r in runs if r["numbers"]["run_mean"] is not None]
    judged = [r["numbers"]["judge_mean"] for r in runs
              if r["numbers"]["judge_mean"] is not None]
    return {"runs": len(runs),
            "scored_trials": sum(r["numbers"]["scored_trials"] for r in runs),
            "checks_passed": passed, "checks_scored": total,
            "pass_rate": passed / total if total else None,
            "run_means": means, "mean_of_run_means": _mean(means) if means else None,
            "judge_runs": len(judged), "judge_run_means": judged,
            "judge_conditional_runs": sum(r["numbers"]["judge_conditional"] for r in runs),
            "judge_figure": _mean(judged) if judged else None}


def _pooled(runs: list, field: str) -> dict:
    out: dict = {}
    for run in runs:
        for key, value in run["numbers"][field].items():
            out[key] = out.get(key, 0) + value
    return out


def run_priors(runs: list) -> dict:
    """The prior variances, measured across every run given (all skills or
    all guidance sections of one evaluation): runs grouped by skill,
    fixture, model, role, guidance pair and content (fixture digest, and the
    tested digest for a with arm), and each figure's run-to-run variance
    pooled over the groups (`pooled_variance`). {"objective", "judge",
    "check"}: the run mean, the run judge figure, and a check's per-run pass
    rate (pooled over every check)."""
    groups: dict = {}
    for run in runs:
        numbers = run_numbers(run["trials"], run.get("judge_conditional") is False)
        if not numbers["counted"]:
            continue
        key = (run["skill"], run["fixture"], run["model"], run["role"], run.get("pair"),
               run["fixture_digest"], run["tested_digest"] if run["role"] == "with" else None)
        group = groups.setdefault(key, {"objective": [], "judge": [], "check": {}})
        if numbers["run_mean"] is not None:
            group["objective"].append(numbers["run_mean"])
        if numbers["judge_mean"] is not None:
            group["judge"].append(numbers["judge_mean"])
        for check, rate in numbers["check_rates"].items():
            group["check"].setdefault(check, []).append(rate)
    judge = pooled_variance([g["judge"] for g in groups.values()])
    return {"objective": pooled_variance([g["objective"] for g in groups.values()]),
            # The judge scale is 0 to 10: its fallback scales with it.
            "judge": judge * 100 if judge == FALLBACK_PRIOR_VARIANCE else judge,
            "check": pooled_variance([v for g in groups.values()
                                      for v in g["check"].values()])}


def _judge_usable(arms: dict) -> bool:
    """Whether two arm summaries' judge figures can be used (see the comment
    in `_classify`)."""
    conditional = any(arms[a]["judge_conditional_runs"] for a in arms)
    complete = all(arms[a]["judge_runs"] == arms[a]["runs"] for a in arms)
    return bool(arms["with"]["judge_run_means"] and arms["without"]["judge_run_means"]) \
        and (complete or not conditional)


def _classify(with_runs: list, without_runs: list, policy: dict,
              judge_carried: bool, priors: dict, strata: list | None = None) -> dict:
    """Rules 1 to 6 of the module docstring, over counted runs. With
    `strata` (#557: a list of (with runs, without runs), one per
    rest-of-guidance stratum, whose union is the two arms), the counts
    (rules 2 and 4) stay pooled over the arms, the deltas and the per-check
    keep are `stratified_estimate`s over the strata, and the judge is
    usable only when it is usable in EVERY stratum (a skipped conditional
    call is a sample biased toward no benefit, so dropping that stratum's
    judge would be too)."""
    arms = {"with": _arm_summary(with_runs), "without": _arm_summary(without_runs)}
    cli = sorted({v for r in with_runs + without_runs for v in r["cli_versions"]})
    out = {**arms, "cli_versions": cli, "objective": None, "judge": None,
           "confident_checks": [], "priors": priors, "keep_tests": []}

    def done(cls, reason):
        return {**out, "class": cls, "reason": reason}

    least = min(arms["with"]["runs"], arms["without"]["runs"])
    if least < 1:
        return done("insufficient", "an arm has no counted run")

    with_n, with_passed = _pooled(with_runs, "check_n"), _pooled(with_runs, "check_passed")
    without_n = _pooled(without_runs, "check_n")
    without_passed = _pooled(without_runs, "check_passed")
    for key in sorted(set(with_n) & set(without_n)):
        if not with_passed[key] and not without_passed[key]:
            return done("cannot-discriminate", f"check {key} fails in every "
                        "scored trial of both arms")
    rates = [arms[a]["pass_rate"] for a in arms]
    if all(r is not None and r <= policy["floor_fraction"] for r in rates):
        return done("cannot-discriminate", "both arms' pass rate at or below "
                    f"{policy['floor_fraction']}")

    strength = policy["prior_strength"]
    objective_ceiling = all(r is not None and r >= policy["ceiling_fraction"]
                            for r in rates)
    wj, oj = arms["with"]["judge_run_means"], arms["without"]["judge_run_means"]
    # A conditional judge call is skipped when its pair's objective already
    # favors the with arm, so conditional figures are a sample biased toward
    # no benefit: unless every counted run of BOTH arms has its figure, in
    # which case none was skipped and nothing was selected out (2026-10-31).
    if strata is None:
        judge_ok = _judge_usable(arms)
    else:
        judge_ok = bool(wj and oj) and all(
            _judge_usable({"with": _arm_summary(w), "without": _arm_summary(o)})
            for w, o in strata)
    judge_ceiling = judge_ok and all(arms[a]["judge_figure"] >= policy["judge_ceiling"]
                                     for a in arms)
    wm, om = arms["with"]["run_means"], arms["without"]["run_means"]
    objective_ok = bool(wm and om)

    def figures(runs, field):
        return [r["numbers"][field] for r in runs if r["numbers"][field] is not None]

    def delta(a, b, prior, margin, field="run_mean"):
        parts = None if strata is None else [
            (figures(w, field), figures(o, field)) for w, o in strata]
        parts = parts and [(x, y) for x, y in parts if x and y]
        if parts and len(parts) > 1:
            d, info = stratified_estimate(parts, prior, strength)
            return {"delta": d, "strata": len(parts),
                    "benefit_lower": stratified_sequence(
                        parts, policy["benefit_confidence"], prior, strength)[0],
                    "retire_upper": stratified_sequence(
                        parts, policy["retire_confidence"], prior, strength)[1],
                    "helps_confidence": confidence_reached_info(info, prior, d),
                    "no_help_confidence": confidence_reached_info(info, prior,
                                                                  margin - d)}
        if parts:
            a, b = parts[0]
        d = _mean(a) - _mean(b)
        return {"delta": d,
                "benefit_lower": confidence_sequence(
                    a, b, policy["benefit_confidence"], prior, strength)[0],
                "retire_upper": confidence_sequence(
                    a, b, policy["retire_confidence"], prior, strength)[1],
                # The levels the two bounds reach, for display (the explorer
                # page): confident above 0, and confident under the margin.
                "helps_confidence": confidence_reached(a, b, prior, strength, d),
                "no_help_confidence": confidence_reached(a, b, prior, strength,
                                                         margin - d)}

    def objective_benefit():
        """The objective delta and the per-check keep (Holm): the reason the
        objective shows benefit, or None."""
        out["objective"] = delta(wm, om, priors["objective"], policy["objective_margin"])
        if out["objective"]["benefit_lower"] > 0:
            return "objective delta's lower bound is above 0"
        def by_check(runs):
            return {k: [r["numbers"]["check_rates"][k] for r in runs
                        if k in r["numbers"]["check_rates"]]
                    for k in {k for r in runs for k in r["numbers"]["check_rates"]}}
        check_priors = {k: priors["check"] for k in set(with_n) & set(without_n)}
        if strata is None:
            out["confident_checks"] = confident_checks(
                by_check(with_runs), by_check(without_runs), policy["check_confidence"],
                check_priors, strength)
        else:
            out["confident_checks"] = stratified_confident_checks(
                [(by_check(w), by_check(o)) for w, o in strata],
                policy["check_confidence"], check_priors, strength)
        if out["confident_checks"]:
            return "a check is confidently better with the skill"
        return None

    def no_benefit(cls_reason):
        """`no-benefit`, unless the runs span too few CLI versions to remove."""
        if len(cli) < policy["min_cli_versions"]:
            return done("insufficient", f"no benefit on the numbers, but {len(cli)} "
                        f"CLI version(s), under the {policy['min_cli_versions']} "
                        "a removal needs")
        return done("no-benefit", cls_reason)

    def with_ahead_skips_only():
        """Every counted run of both arms either has its judge figure, or has
        none only because every scored trial records a with-ahead skip."""
        for run in with_runs + without_runs:
            if run["numbers"]["judge_mean"] is not None:
                continue
            judged = [t for t in run["trials"] if t.get("scored") or t.get("errored")]
            if not judged or not all(t.get("judge_skipped_with_ahead") for t in judged):
                return False
        return True

    def route(a_lists, prior):
        """(d, I) of one route: stratified over the strata that have a figure
        on each arm, else the two pooled arms."""
        parts = [(x, y) for x, y in a_lists if x and y]
        if len(parts) > 1:
            return stratified_estimate(parts, prior, strength)
        return _stratum(*parts[0], prior, strength)

    def lists(field):
        if strata is None:
            return [(figures(with_runs, field), figures(without_runs, field))]
        return [(figures(w, field), figures(o, field)) for w, o in strata]

    def check_lists():
        def by_check(runs):
            return {k: [r["numbers"]["check_rates"][k] for r in runs
                        if k in r["numbers"]["check_rates"]]
                    for k in {k for r in runs for k in r["numbers"]["check_rates"]}}
        pairs = ([(with_runs, without_runs)] if strata is None else strata)
        return [(by_check(w), by_check(o)) for w, o in pairs]

    # The keep tests (#557 follow-up): one p-value per route that can return
    # `benefit` here, for `retirement`'s per-subject family. Computed for
    # every such route whatever the cell's class, and never setting
    # out["judge"], so a route the class did not need is still tested.
    tests = []
    if objective_ok:
        tests.append({"route": "objective",
                      "p": keep_p(*route(lists("run_mean"), priors["objective"]),
                                  priors["objective"])})
    per_check = check_lists()
    keys = sorted({k for w, o in per_check for k in set(w) & set(o)})
    ranked = []
    for key in keys:
        parts = [(w[key], o[key]) for w, o in per_check if key in w and key in o]
        if any(x and y for x, y in parts):
            d, info = route(parts, priors["check"])
            ranked.append((-d * math.sqrt(info), key, d, info))
    if ranked:
        _, _, d, info = min(ranked)
        tests.append({"route": "checks",
                      "p": min(1.0, len(keys) * keep_p(d, info, priors["check"]))})
    judge_route = (judge_ok or (not judge_carried and strata is not None
                                and with_ahead_skips_only())) and bool(wj and oj)
    if judge_route:
        tests.append({"route": "judge",
                      "p": keep_p(*route(lists("judge_mean"), priors["judge"]),
                                  priors["judge"])})
    out["keep_tests"] = tests

    judge_words = ("the judge figure needs a judged run on each arm, and every "
                   "counted run judged when any judge call was conditional")
    if judge_carried:
        # Decided on the judge, but a judge-carried fixture with objective
        # checks keeps on them too, and is no-benefit only when they are.
        reason = objective_benefit() if objective_ok else None
        if reason:
            return done("benefit", reason)
        if not judge_ok:
            return done("insufficient", judge_words)
        out["judge"] = delta(wj, oj, priors["judge"], policy["judge_margin"],
                             "judge_mean")
        if out["judge"]["benefit_lower"] > 0:
            return done("benefit", "judge delta's lower bound is above 0")
        if judge_ceiling:
            return done("ceiling", "both arms' judge figure at or above "
                        f"{policy['judge_ceiling']}")
        if out["judge"]["retire_upper"] >= policy["judge_margin"]:
            return done("insufficient", "the interval is not tight enough yet")
        if objective_ok and out["objective"]["retire_upper"] >= policy["objective_margin"]:
            return done("insufficient", "the objective interval is not tight enough yet")
        return no_benefit("the deltas' upper bounds are under their margins")

    if not objective_ok:
        return done("insufficient", "no run with objective checks on an arm")
    reason = objective_benefit()
    if reason:
        return done("benefit", reason)
    if judge_ok:
        out["judge"] = delta(wj, oj, priors["judge"], policy["judge_margin"],
                             "judge_mean")
        if out["judge"]["benefit_lower"] > 0:
            return done("benefit", "judge delta's lower bound is above 0")
    if objective_ceiling:
        return done("ceiling", "both arms' pass rate at or above "
                    f"{policy['ceiling_fraction']}")
    if not judge_ok and strata is not None and with_ahead_skips_only():
        # In-situ guidance (#557, T3's review): every missing judge figure is
        # a conditional skip made because the with arm was strictly ahead on
        # the objective, so no figure was lost for any other reason and the
        # objective alone decides a removal. The judged runs left are a
        # sample biased toward no benefit, so they may still keep, never
        # remove.
        if wj and oj:
            judged = delta(wj, oj, priors["judge"], policy["judge_margin"], "judge_mean")
            if judged["benefit_lower"] > 0:
                out["judge"] = judged
                return done("benefit", "judge delta's lower bound is above 0, on the "
                            "runs the conditional judge was called for")
        if objective_ceiling:
            return done("ceiling", "both arms' pass rate at or above "
                        f"{policy['ceiling_fraction']}")
        if out["objective"]["retire_upper"] < policy["objective_margin"]:
            return no_benefit("the objective delta's upper bound is under its margin, and "
                              "every skipped judge call was skipped because the with arm "
                              "was ahead")
        return done("insufficient", "the interval is not tight enough yet")
    if not judge_ok:
        return done("insufficient", "the objective interval is not tight enough "
                    f"yet, and the judge is needed to remove: {judge_words}")
    if out["objective"]["retire_upper"] < policy["objective_margin"] \
            and out["judge"]["retire_upper"] < policy["judge_margin"]:
        return no_benefit("every delta's upper bound is under its margin")
    return done("insufficient", "the interval is not tight enough yet")


def run_key(run: dict) -> str:
    """A run's name in `runs_used`:
    `<path>#<fixture>#<role>`, since one `<timestamp>` holds every fixture."""
    return f"{run['path']}#{run['fixture'] or ''}#{run['role']}"


def classify_cell(with_runs: list, without_runs: list, policy: dict,
                  judge_carried: bool, priors: dict) -> dict:
    """A cell's class over all its counted runs (module docstring)."""
    prime(with_runs + without_runs)
    counted, skipped = [], {}
    for runs in (with_runs, without_runs):
        keep = []
        for run in sorted(runs, key=_order):
            reason = run["numbers"]["skip_reason"]
            if reason is None:
                keep.append(run)
            else:
                skipped[reason] = skipped.get(reason, 0) + 1
        counted.append(keep)
    full = _classify(*counted, policy, judge_carried, priors)
    cls, reason = full["class"], full["reason"]
    errored = sum(r["numbers"]["errored_trials"] for r in with_runs + without_runs)
    if cls == "no-benefit" and (errored or NO_CHECKS_REASON in skipped):
        # An agent's errors can only help keep: dropping or scoring around
        # them would compare only the trials that went well.
        cls, reason = "insufficient", (f"{cls} on the numbers, but the cell has "
                                       f"{errored} agent-errored trial(s) or a run "
                                       "skipped as anomalous, so it cannot retire")
    return {**full, "class": cls, "reason": reason, "judge_carried": judge_carried,
            "skipped": skipped}


#: A skill cell's prior guard (#557 follow-up), softer than guidance's:
#: 10 degrees of freedom before a measured value replaces the fallback, and
#: fallbacks just above the measured mid-range spread (objective 0.0063,
#: judge 0.76; checks keep guidance's 0.25, they only keep). Chosen by
#: simulation against the integrator's two bars: false removals at a true
#: judge gain of 1.5 at or under 4% (3.4%, against 4.8% on the pooled
#: prior) and the high cohort (4 skills + 3 sections) within the 50-point
#: budget (0.96x); the full guidance guard cost 1.18x.
SKILL_PRIOR_GUARD = {"min_df": 10, "objective": 0.01, "judge": 1.0, "check": 0.25}
GUIDANCE_PRIOR_GUARD = {"min_df": GUIDANCE_PRIOR_MIN_DF,
                        "objective": GUIDANCE_FALLBACK_PRIOR_VARIANCE,
                        "judge": GUIDANCE_FALLBACK_PRIOR_VARIANCE * 100,
                        "check": GUIDANCE_FALLBACK_PRIOR_VARIANCE}


def cell_priors(runs: list, guard: dict | None = None) -> dict:
    """The prior variances of ONE in-situ guidance cell (#557), measured over
    its own runs only: a prior pooled across cells is anti-conservative when
    other cells sit near the ceiling. Groups are (role, rest of guidance,
    fixture digest, and the tested digest for a with arm), over counted
    runs as `run_priors` counts them, each figure pooled with
    `GUIDANCE_PRIOR_MIN_DF` degrees of freedom needed before the measured
    value replaces `GUIDANCE_FALLBACK_PRIOR_VARIANCE` (x100 for the judge's
    0-to-10 scale, applied exactly when the fallback is). `guard` replaces
    those (`SKILL_PRIOR_GUARD` for a skill cell)."""
    guard = guard or GUIDANCE_PRIOR_GUARD
    groups: dict = {}
    for run in runs:
        numbers = run_numbers(run["trials"], run.get("judge_conditional") is False)
        if not numbers["counted"]:
            continue
        key = (run["role"], run.get("pair_key"), run["fixture_digest"],
               run["tested_digest"] if run["role"] == "with" else None)
        group = groups.setdefault(key, {"objective": [], "judge": [], "check": {}})
        if numbers["run_mean"] is not None:
            group["objective"].append(numbers["run_mean"])
        if numbers["judge_mean"] is not None:
            group["judge"].append(numbers["judge_mean"])
        for check, rate in numbers["check_rates"].items():
            group["check"].setdefault(check, []).append(rate)

    def guarded(lists, figure):
        df = sum(len(v) - 1 for v in lists if len(v) >= 2)
        if df < guard["min_df"]:
            return guard[figure]
        return pooled_variance(lists)

    return {"objective": guarded([g["objective"] for g in groups.values()], "objective"),
            "judge": guarded([g["judge"] for g in groups.values()], "judge"),
            "check": guarded([v for g in groups.values() for v in g["check"].values()],
                             "check")}


def classify_strata(strata: dict, policy: dict, judge_carried: bool) -> dict:
    """An in-situ guidance cell's class over its rest-of-guidance strata
    (#557). `strata` maps a rest digest to {"with": runs, "without": runs}.

    A stratum is USED when it has a counted run on each arm. The class is
    `_classify` over the used strata (counts pooled, deltas stratified),
    with `cell_priors` over the used strata's runs. A run skipped as
    anomalous ANYWHERE in the cell's current-content runs, used or not,
    keeps it from `no-benefit`, as in `classify_cell`; an agent-errored
    trial scores 0 on every check of its arm and does not block.
    There is no separate confirmation beside the rest on main (Adam,
    2026-11-02): the pooled bounds decide."""
    every = [r for s in strata.values() for role in ("with", "without") for r in s[role]]
    prime(every)
    counted, skipped = {}, {}
    for rest, arms in strata.items():
        counted[rest] = {}
        for role in ("with", "without"):
            keep = []
            for run in sorted(arms[role], key=_order):
                reason = run["numbers"]["skip_reason"]
                if reason is None:
                    keep.append(run)
                else:
                    skipped[reason] = skipped.get(reason, 0) + 1
            counted[rest][role] = keep
    used = sorted(rest for rest, arms in counted.items() if arms["with"] and arms["without"])
    used_runs = [r for rest in used for role in ("with", "without") for r in strata[rest][role]]
    # Re-prime the used runs alone, so a check seen only in a dropped
    # stratum is not part of the cell's checks.
    prime(used_runs)
    pairs = [(counted[rest]["with"], counted[rest]["without"]) for rest in used]
    with_runs = sorted((r for w, _ in pairs for r in w), key=_order)
    without_runs = sorted((r for _, o in pairs for r in o), key=_order)
    full = _classify(with_runs, without_runs, policy, judge_carried, cell_priors(used_runs),
                     strata=pairs or None)
    cls, reason = full["class"], full["reason"]
    # An agent-errored trial already scores 0 on every check of its arm
    # (`run_numbers`), so it counts as a bad result, never as one left out;
    # unlike `classify_cell` it does not also block removal, which at the
    # run counts a guidance verdict needs would block a cell for good
    # (#557, T3's planner review). A run skipped as anomalous still does.
    if cls == "no-benefit" and NO_CHECKS_REASON in skipped:
        cls, reason = "insufficient", (f"{cls} on the numbers, but the cell has a run "
                                       "skipped as anomalous, so it cannot retire")
    return {**full, "class": cls, "reason": reason, "judge_carried": judge_carried,
            "skipped": skipped, "strata": used, "used_runs": used_runs,
            "errored_trials": sum(r["numbers"]["errored_trials"] for r in every)}


# ---------------------------------------------------------------------------
# Pooling and the verdict.

def _order(run: dict) -> tuple:
    """A run's place: its timestamp, then its path."""
    return run["timestamp"], run["path"]


def _joint_context(with_runs: list, without_runs: list, models: list):
    """(with context, without context, pair key) chosen JOINTLY (round 5,
    B6), or (None, None, None). Runs on a roster model are grouped by (arm context digest,
    `pair_key`): the pair key is what both arms of one comparison must share,
    the non-subject skills (`arm_context.others_digest`) and the frozen
    guidance (`context.guidance.digest`). A candidate is a with group and a
    without group of one pair key, scored by its smaller arm's run count; the
    best candidate is the cell's; a tie on that count goes to the candidate
    with the newer newest run (Adam, 2026-11-01: an equal tie had dropped a
    cell back to insufficient), and only a full tie, or no candidate, chooses
    none. No
    single run's self-report chooses either (round 4), and the two arms can
    no longer be pooled from different guidance or skill sets."""
    def groups(runs):
        counts: dict = {}
        for run in runs:
            if run["model"] in models and run["arm_context_digest"] and run.get("pair_key"):
                key = (run["arm_context_digest"], run["pair_key"])
                n, newest = counts.get(key, (0, ""))
                counts[key] = (n + 1, max(newest, run["timestamp"]))
        return counts
    candidates = sorted(((min(n_with, n_without), max(new_with, new_without),
                          with_ctx, without_ctx, pair)
                         for (with_ctx, pair), (n_with, new_with) in groups(with_runs).items()
                         for (without_ctx, other), (n_without, new_without)
                         in groups(without_runs).items()
                         if pair == other), reverse=True)
    if not candidates or (len(candidates) > 1 and candidates[0][:2] == candidates[1][:2]):
        return None, None, None
    return candidates[0][2:]


def pooled_fixture(run: dict, skill: str, expected: dict) -> str:
    """The fixture on main a run of `skill` counts for: its own name ("" for
    flat), or its `FIXTURE_ALIASES` target when the old name is no longer on
    main and the run's fixture digest equals the target's there."""
    name = run["fixture"] or ""
    target = FIXTURE_ALIASES.get((skill, name))
    if target is None or name in expected or target not in expected:
        return name
    digest = expected[target].get("fixture_digest")
    return target if digest is not None and run["fixture_digest"] == digest else name


def pool_cells(runs: list, skill: str, models: list, expected: dict,
               strata: bool = False) -> dict:
    """Which arm runs each (fixture, model) cell of `skill` holds, each arm
    pooled by its own key against the content on main (module docstring).
    `expected` maps each fixture on main ("" for a flat one) to its
    {"fixture_digest", "tested_digest"}, either None when unknown. A run's
    fixture is `pooled_fixture`'s. The one place runs are grouped; swap it
    to change the window.

    `newest_on_model` is the newest timestamp of ANY run of the cell's
    fixture on its model, whatever its role or digests (None with no run).
    It is output only and decides nothing here: the planner counts a fire
    that landed a run, pooled or not, as a fire that produced something,
    so a stale-digest run is not mistaken for an empty fire.

    `strata` (#557, in-situ guidance only): no `_joint_context`; each cell
    holds every current-content run on its model, grouped by `pair_key`
    (the rest of the guidance the run ran beside) under `strata`, and its
    own key {tested_digest, fixture_digest}."""
    if strata:
        return _pool_strata(runs, skill, models, expected)
    own = [r for r in runs if r["skill"] == skill]
    cells = {}
    for fixture, main in sorted(expected.items()):
        mine = [r for r in own if pooled_fixture(r, skill, expected) == fixture]
        tested, fdig = main.get("tested_digest"), main.get("fixture_digest")
        current_with = [r for r in mine if r["role"] == "with" and tested is not None
                        and r["tested_digest"] == tested and fdig is not None
                        and r["fixture_digest"] == fdig]
        current_without = [r for r in mine if r["role"] == "without" and fdig is not None
                           and r["fixture_digest"] == fdig]
        with_context, without_context, pair = _joint_context(current_with, current_without,
                                                             models)
        key = {"tested_digest": tested, "fixture_digest": fdig,
               "with_context": with_context, "without_context": without_context}
        for model in models:
            stamps = [r["timestamp"] for r in mine if r["model"] == model]
            cells[(fixture, model)] = {
                "key": key, "on_model": len(stamps),
                "newest_on_model": max(stamps) if stamps else None,
                "with": [r for r in current_with if r["model"] == model
                         and r["arm_context_digest"] == with_context
                         and r.get("pair_key") == pair],
                "without": [r for r in current_without if r["model"] == model
                            and r["arm_context_digest"] == without_context
                            and r.get("pair_key") == pair]}
    return cells


def _pool_strata(runs: list, skill: str, models: list, expected: dict) -> dict:
    own = [r for r in runs if r["skill"] == skill]
    cells = {}
    for fixture, main in sorted(expected.items()):
        mine = [r for r in own if pooled_fixture(r, skill, expected) == fixture]
        tested, fdig = main.get("tested_digest"), main.get("fixture_digest")
        for model in models:
            groups: dict = {}
            for run in mine:
                if run["model"] != model or not run.get("pair_key") or fdig is None \
                        or run["fixture_digest"] != fdig:
                    continue
                if run["role"] == "with" and (tested is None or run["tested_digest"] != tested):
                    continue
                groups.setdefault(run["pair_key"], {"with": [], "without": []})[
                    run["role"]].append(run)
            stamps = [r["timestamp"] for r in mine if r["model"] == model]
            cells[(fixture, model)] = {
                "key": {"tested_digest": tested, "fixture_digest": fdig},
                "on_model": len(stamps),
                "newest_on_model": max(stamps) if stamps else None,
                "strata": groups,
                "with": [r for g in groups.values() for r in g["with"]],
                "without": [r for g in groups.values() for r in g["without"]]}
    return cells


def _link(path: str) -> dict:
    return {"path": path, "url": RESULTS_BLOB + path}


def _run_entry(run: dict) -> dict:
    numbers = _numbers(run)
    return {"path": run["path"], "timestamp": run["timestamp"],
            "report": _link(run["report"]), "run": run["run"],
            "counted": numbers["counted"], "scored_trials": numbers["scored_trials"],
            "run_mean": numbers["run_mean"], "judge_mean": numbers["judge_mean"],
            "cost_usd": numbers["cost_usd"]}


def retirement(index: dict, models: list, skill: str, policy: dict,
               expected: dict, priors: dict | None = None, strata: bool = False,
               family: bool = True) -> dict:
    """The verdict for `skill` over every fixture on main (`expected`, see
    `pool_cells`) x roster model cell. `priors`, when given, applies to every
    cell; by default each cell measures its own (`cell_priors` with
    `SKILL_PRIOR_GUARD`; #557 follow-up).

    `strata` (#557, in-situ guidance): cells are pooled by rest of guidance
    and classified by `classify_strata` (which measures its own per-cell
    priors; `priors` is not used); a cell's `runs` and `runs_used` are its
    used strata's runs.

    `family` (#557 follow-up; default on): the 85% keep is applied per
    SUBJECT, not per cell. Every cell's keep tests (`_classify`) form one
    family of FIXED size m = fixtures on main x roster models x 3 routes
    (objective, checks, judge), known before any run; a subject keeps only
    when some `benefit` cell has a test with p <= (1 - benefit_confidence)
    / m (Holm's first step, which is all "any keep" needs). Otherwise every
    `benefit` cell is `insufficient`, so the planner keeps measuring it. A
    union over anytime-valid sequences with plug-in variances: as
    approximate as one cell's bound. The verdict records `keep_family` (m)
    and `keep_alpha`. The alone pair passes `family=False`."""
    cells, used = [], set()
    for (fixture, model), pool in sorted(pool_cells(index.get("runs", []), skill,
                                                    models, expected, strata).items()):
        arms = {"with": pool["with"], "without": pool["without"]}
        runs = arms["with"] + arms["without"]
        prime(runs)
        if not strata:
            used.update(run_key(r) for r in runs)
        missing = sorted(k for k, v in pool["key"].items() if v is None)
        if not pool["on_model"]:
            cell = {"class": "missing", "reason": "no run on this model"}
        elif missing:
            cell = {"class": "insufficient",
                    "reason": f"pooling key incomplete: {', '.join(missing)}"}
        elif strata:
            carried = any(r["judge_carried"] for r in runs)
            cell = classify_strata(pool["strata"], policy, carried)
            mine = cell.pop("used_runs")
            arms = {role: [r for r in mine if r["role"] == role] for role in arms}
            runs = arms["with"] + arms["without"]
            pool = {**pool, "key": {**pool["key"], "strata": cell.pop("strata")}}
        else:
            carried = any(r["judge_carried"] for r in runs)
            # A skill cell's priors are its own (#557 follow-up): the pooled
            # cross-skill prior sat below the measured spread. `priors`, when
            # given (the alone pair's, a test's), applies to every cell.
            cell = classify_cell(arms["with"], arms["without"], policy, carried,
                                 priors if priors is not None
                                 else cell_priors(runs, SKILL_PRIOR_GUARD))
        if strata:
            used.update(run_key(r) for r in runs)
        cells.append({"fixture": fixture or None, "model": model, "key": pool["key"],
                      "newest_on_model": pool["newest_on_model"], **cell,
                      "cost_usd": _finite_sum([r["numbers"]["cost_usd"] for r in runs]),
                      "cost_unknown_trials": sum(r["numbers"]["cost_unknown_trials"]
                                                 for r in runs),
                      "runs": {role: [_run_entry(r) for r in sorted(arms[role], key=_order)]
                               for role in arms}})
    if family and expected:
        m = len(expected) * max(1, len(models)) * 3
        alpha = 1 - policy["benefit_confidence"]
        passing = any(c["class"] == "benefit" and any(t["p"] <= alpha / m
                                                       for t in c.get("keep_tests", []))
                      for c in cells)
        if not passing:
            for c in cells:
                if c["class"] == "benefit":
                    c["cell_reason"] = c["reason"]
                    c["class"], c["reason"] = "insufficient", (
                        f"benefit in this cell alone ({c['reason']}), not across the "
                        f"subject's {m} keep tests at {policy['benefit_confidence']:.0%} "
                        "each (Holm)")
    classes = {c["class"] for c in cells}
    if not expected:
        verdict, reason = "insufficient", "no fixture on main"
    elif "benefit" in classes:
        verdict, reason = "keep", "a cell shows benefit"
    elif classes & {"insufficient", "missing"}:
        verdict, reason = "insufficient", "a cell is insufficient or missing"
    elif "cannot-discriminate" in classes:
        verdict, reason = "cannot-discriminate", "a cell cannot discriminate"
    elif "ceiling" in classes:
        verdict, reason = "ceiling", "a cell is at the ceiling"
    elif cells and classes == {"no-benefit"}:
        verdict, reason = "retire", "every cell shows no benefit"
    else:
        # No cell (no roster model) or a class this verdict does not know:
        # never a retirement without evidence.
        verdict, reason = "insufficient", "no cell shows no benefit"
    out = {"verdict": verdict, "reason": reason, "cells": cells,
           "runs_used": sorted(used)}
    if family and expected:
        out.update(keep_family=len(expected) * max(1, len(models)) * 3,
                   keep_alpha=1 - policy["benefit_confidence"])
    return out


# ---------------------------------------------------------------------------
# Guidance sections (skills-evals#124).

#: Each of a section's two comparisons, and the role of an arm in it by its
#: delivery mode. `in_situ` is the ablation, the whole guidance with and
#: without the section, and decides removal; `alone` is the section against
#: no guidance, and only says whether the section teaches the behavior.
GUIDANCE_PAIRS = {"in_situ": {"full": "with", "full-minus-section": "without"},
                  "alone": {"section": "with", "none": "without"}}


def guidance_verdict(index: dict, models: list, section: str, policy: dict,
                     expected: dict) -> dict:
    """The verdict for one guidance section: `retirement` over its in-situ
    cells (every run of `index` whose `pair` is `in_situ`), and over its
    alone cells for contrast. `expected` is as for `pool_cells`, with the
    section's own extent digest as `tested_digest`, and a run's `pair_key`
    and arm context are the digest of the rest of the guidance it ran
    beside, so the two arms of a cell always ran beside the same rest.

    THE TWIST: a section whose in-situ verdict is `retire` while some alone
    cell shows `benefit` teaches the behavior, but the rest of the guidance
    already covers it. Its verdict is `shorten-or-merge`, never a removal.
    Every other in-situ verdict stands as it is.

    The in-situ cells are pooled by rest of guidance (#557, `retirement`
    with `strata`). The alone cells pool as before."""
    runs = index.get("runs", [])
    priors = run_priors(runs)
    out = {pair: retirement({"runs": [r for r in runs if r.get("pair") == pair]},
                            models, section, policy, expected, priors,
                            strata=pair == "in_situ", family=pair == "in_situ")
           for pair in GUIDANCE_PAIRS}
    in_situ, alone = out["in_situ"], out["alone"]
    verdict, reason = in_situ["verdict"], in_situ["reason"]
    if verdict == "retire" and any(c["class"] == "benefit" for c in alone["cells"]):
        verdict, reason = ("shorten-or-merge", "no marginal benefit inside the whole "
                           "guidance, but a cell shows benefit alone (section vs "
                           "none): the rest of the guidance covers it")
    return {"verdict": verdict, "reason": reason, "in_situ_verdict": in_situ["verdict"],
            "cells": in_situ["cells"],
            "alone": {"verdict": alone["verdict"], "reason": alone["reason"],
                      "cells": alone["cells"]},
            "runs_used": sorted(set(in_situ["runs_used"]) | set(alone["runs_used"])),
            **{k: in_situ[k] for k in ("keep_family", "keep_alpha") if k in in_situ}}
