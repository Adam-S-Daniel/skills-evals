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
  * THE ARMS ARE POOLED by their own keys (`pool_cells`, the one function
    that decides which runs a cell holds) against the content ON MAIN, never
    the newest run's:
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
  * THE PAIR IS THE UNIT OF A DECISION (2026-11-03, replacing two
    independent samples; `pair_runs`). One fire on one model runs both arms
    and stamps them with one `--timestamp`, so a with run and a without run
    of the same cell with the same timestamp are one PAIR, and its paired
    difference is D = with run mean - without run mean, in [-1, 1]. Both
    runs must count and have a run mean. A run with no partner (its fire's
    other arm was not validated, did not count or is not in the cell's
    pooling key) is UNPAIRED: listed under `unpaired`, never in a bound.
    Should two runs of one role share a timestamp, the first by path pairs.
    Pairs are ordered by (timestamp, with run's path), and only the first
    `max_runs_per_cell` decide.
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
went well. A SKILL cell with any such trial can never be `no-benefit` or
`no-clear-effect` (at most `insufficient`; it can still show `benefit`), so
errors can only help keep and never support a removal, even a proposed one
(the 2026-11-03 adversarial review's m4).
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
judge call was skipped and nothing was selected out; only then is a judge
figure reported. A delta is the mean of the pairs' differences.

THE BOUNDS (2026-11-03, replacing the normal-mixture sequence over
moderated variances, which the statistics review of that day found invalid
at the run counts where it decided: four identical runs per arm removed a
skill). A BETTING confidence sequence (Waudby-Smith and Ramdas, "Estimating
means of bounded random variables by betting", hedged capital with aGRAPA
bets) over a cell's paired differences D. It needs no variance prior and
assumes nothing about the data except that D lies in [-1, 1]. Each decision
is a one-sided test martingale, the wealth of a bettor who stakes a fraction
lambda_t of it on each new pair:

  keep    H0: E[D] <= 0,       W = prod(1 + lambda_t D_t),
          lambda_t in [0, BET_CAP];
  remove  H0: E[D] >= margin,  W = prod(1 + lambda_t (margin - D_t)),
          lambda_t in [0, BET_CAP / (1 - margin)].

lambda_t is aGRAPA's mu / (var + mu^2) over the payoffs BEFORE pair t (and
the bet prior's pseudo-runs, `bet_prior`), capped at BET_CAP (0.9) of the
largest stake that cannot lose everything. Under H0 each W is a nonnegative
supermartingale, so by Ville's inequality P(W ever reaches 1/alpha) <= alpha
however often it is looked at and whatever the bets were: a cell is checked
after every pair. A test REJECTS at the first pair whose wealth reaches its
threshold:

  keep    alpha = (1 - benefit_confidence) / m, where m is the subject's
          keep family (`retirement`: fixtures on main x roster models, fixed
          before any run; Bonferroni, so the subject keeps at
          `benefit_confidence` overall);
  remove  alpha = 1 - retire_confidence, per cell.

Three more one-sided tests run at the remove level, on the same betting
machinery (`log_wealth`):

  ceiling H0: E[without] <= 1 - margin (`ceiling_wealth`): the payoff of a
          pair is its without run mean less that floor. Rejecting shows
          the without arm cannot fall the margin below a perfect with
          arm, so the cell has no headroom. A without arm at 1.0 rejects
          at pair 18; at 0.95, pair 25; at 0.90 it does not inside a
          40-pair cap.
  harm    H0: E[D] >= 0 (`harm_wealth`, the remove test with margin 0):
          rejecting shows the skill makes the cell worse. It needs no
          headroom, so a high cell stays fired while it may still show
          one (rule 6); a harm milder than the margin can still end a
          cell `ceiling-unconfirmed` or, at the cap, `no-clear-effect`.
  no-harm H0: E[D] <= -margin (`keep_wealth` at -margin): rejecting shows
          the subject costs less than the margin here. A ceiling parks a
          cell only with it (the round 2 review's M1: at a perfect without
          arm the ceiling test rejects at pair 18, before a harm of up to
          about 0.17 could show). Equal arms reject it with the ceiling.

A REMOVAL DECIDES AT A STOPPING TIME (round 2's C1). The remove and harm
tests decide (`remove_decided_at`, `harm_decided_at`) at the first pair n
whose running wealth is at 1/alpha AND whose pairs 1..n span
`min_cli_versions` `harness.version`s. That event lies inside "the wealth
ever reaches 1/alpha", which Ville bounds by alpha under H0, so the level
holds. The wealth must be at its level at n itself, so a late pair that
knocks it down (a D = +1 on the new version) does not decide; but a
crossing reached inside one Claude Code release is no longer stuck there
for good, as it was when versions were read only up to the first crossing.
`remove_at` and `harm_at` stay each test's first crossing, reported.

When both tests reject, the one that decided first wins (a tie keeps): the
keep test's first crossing against the remove test's stopping time
(round 3's M3). Against the remove test's first crossing, a crossing that
never decided (one CLI version) outranked a keep reached afterwards for
good, and the cell sat undecided at the cap.
`helps_confidence` and `no_help_confidence` are 1 - 1 / (the largest wealth
so far) of the two tests, the levels they reached; `benefit_lower` and
`retire_upper` are the sequence's ends at the keep and remove levels, found
by bisection over the tested value (`betting_bound`), for display only.
The judge does not vote (2026-11-03): its figure is reported with the same
statistics on (with - without) / 10, and no class reads it. Nor do single
checks (the review's M1: a per-check keep route held its error rate only
under its plug-in variance): the objective run mean decides.

A CELL'S CLASS (`_classify`), over its paired runs, first match wins:

  1. `insufficient`: no pair (an arm has no counted run, or no fire has both).
  2. `cannot-discriminate`: both arms' pooled pass rate <= `floor_fraction`
     with FLOOR_MIN_RUNS pairs (the fixture looks broken); with fewer,
     `insufficient`.
  3. `benefit`: the keep test rejected first.
  4. HARM, where the ceiling test rejected or the without arm's mean is
     above 1 - `objective_margin`, and the harm test crossed: `no-benefit`
     once it decides (above), `insufficient` until then.
  5. `ceiling`: the ceiling test and the no-harm test both rejected (round
     1's C1: a bound, not a sample mean over a fixed pair count; round 2's
     M1: never over a harm the margin could hide). The subject has no room
     to show the margin on this task, so the cell does not vote on
     removal; the planner stops firing it but keeps measuring the
     subject's other cells.
  6. A without arm above 1 - margin on the sample or the bound, not yet
     parked: `ceiling-unconfirmed` (round 2's M2, a budget rule) from
     `max_runs_high_cell` pairs on, once the no-harm test has rejected and
     the without arm averages at least HIGH_STOP_MIN_WITHOUT (0.90; round
     3's M2: without either, a stop on the sample mean hid a harm of 0.15
     two times in three and parked a third of the helpful cells whose true
     without arm was 0.82). The planner stops firing it, it does not vote,
     and a retire verdict beside it is a proposal. Otherwise `insufficient`
     until the cap, where rule 8 decides it. The remove test does not
     decide such a cell.
  7. NO BENEFIT, where the remove test crossed first: `no-benefit` once it
     decides (above), `insufficient` until then.
  8. `no-clear-effect`: `max_runs_per_cell` pairs, neither test crossed,
     and the pairs span `min_cli_versions` (with fewer, `insufficient`).
     Never an automatic removal: the verdict can only propose one.
  9. `insufficient`: neither test has rejected yet.

Every cell records `at_cap` (its pairs reached `max_runs_per_cell`): its
window is then frozen, so the planner fires an `insufficient` one no more,
counts it as blocking and lists it as a `cell-at-cap` work item (round 3's
M3). A cell ends there undecided when its pairs span one CLI version, or
when a test crossed but has not decided on two; only new content (or a
person) moves it.

`classify_cell` classifies a cell over all its counted runs, ordered by
(timestamp, path). Nothing is carried from an earlier evaluation, and since
every run is within the current pooling key, new content starts over.
scripts/compute_gates.py reads no run stamped after its `--as-of`, so an
evaluation can be repeated as of a time. A run is named by `run_key`,
`<path>#<fixture>#<role>`.

THE VERDICT (`retirement`), over every fixture on main x every current roster
arm model. A `cannot-discriminate` cell is left out (a broken fixture says
nothing about the subject), and a `ceiling`, `ceiling-unconfirmed` or
`paused` cell (PARKED_CLASSES) does not vote on removal.

A fixture the eval scope pass paused (scripts/eval_scope.py; `expected`
marks it `scope_paused` with the pause's rule, from compute_gates) stays in
the verdict (round 3's C1: dropping its cells let the subject's other cells
remove a subject it helped, automatically). Each of its cells keeps its
class when that is `benefit` (a keep it earned before the pause still
keeps: the keep test held its level at whatever pair it stopped) or
`no-benefit` (round 4's M1: a harm or no-benefit decided at its stopping
time is evidence at the gate's level, so it votes; the pause reads only a
pooled sample of the without arm and must not hide it), and is otherwise
`paused`, recording `class_before_pause`: parked, so it neither votes nor
lets a removal beside it be automatic. A subject whose every counted cell
is parked is `ceiling` only when each cell shows the ceiling on its own runs
(`_shows_ceiling`: a ceiling class, or a ceiling pause of a cell that was a
ceiling class, or whose no-harm test had rejected with a without arm
averaging at least HIGH_STOP_MIN_WITHOUT), and `insufficient` otherwise,
marked `unmeasured` so scripts/plan_week.py lists a `paused-unmeasured` work
item (a floor or zero-use pause measures nothing, and a pooled sample is not
a bound).
A `ceiling` subject with a paused cell among them is marked `paused_ceiling`,
for a `paused-ceiling` work item that asks for a harder fixture: a paused
fixture has no planner cell to carry a `fixture-ceiling` one.
HEADROOM cells are the `no-benefit` and `no-clear-effect` ones. First match:

  * no fixture on main -> `insufficient`;
  * any `benefit` -> `keep`;
  * any `insufficient` or missing cell -> `insufficient`;
  * every cell broken -> `cannot-discriminate`;
  * no headroom cell (every counted cell parked) -> `ceiling` when every
    one shows it on its own runs (above): the subject needs a fixture with
    headroom, not more runs, and is never removed for it; otherwise
    `insufficient`;
  * otherwise `retire`, with `removal`:
      - `auto` when there are at least AUTO_MIN_HEADROOM_CELLS (2) headroom
        cells and every one is `no-benefit`: two cells with independent run
        noise make the per-cell 10% about 1% realized;
        No parked cell may stand beside them (the review's C1): a cell
        that did not vote leaves the subject's case incomplete;
      - `proposal` otherwise (one headroom cell only, a cell that hit the
        cap with no clear effect, or a parked cell): a human decides,
        whatever
        `retirement_mode` says (scripts/retire_skill.py lowers auto to a
        proposal, and re-derives auto from the cells rather than trusting
        the field).

No roster model means no cell, never a retirement. scripts/compute_gates.py
then lets one skill retire per evaluation. A standing retirement's
stickiness, and holding the one slot while a removal pull request is open,
are part 2's: it reads the open pull requests from GitHub rather than
trusting an earlier gates file.

IN-SITU GUIDANCE CELLS (#557). The guidance block's `rest_policy` chooses
how a cell reads the runs beside the rest of the guidance (the guidance
without the section; a run's `pair_key`), and `expected`'s `rest_digest`
(computed by compute_gates from the `--guidance` checkout) names the rest
on main, the CURRENT rest. With no `rest_digest` the cell is `insufficient`
under either policy. An agent-errored trial scores 0 and does not block a
guidance cell's removal; a run skipped as anomalous does, as for a skill.

  * `current` (2026-11-03, the review's C3): a cell holds only the runs
    beside the current rest, so every pair compares the section against
    today's rest; runs beside an older rest are ignored. One edit elsewhere
    in base.md then starts every cell over (on 2026-11-04 one edit
    discarded 494 of 498 in-situ arms).
  * `pooled-with-current-guard` (Adam, 2026-11-07, the default; ADR 0014,
    "Pooled-rest addendum (2026-11-07)"): a cell holds the runs beside
    EVERY rest, under the same key otherwise (the with arm's tested
    digest, the fixture digest, the model, and no fleet hook set). Runs
    pair only within one rest (`classify_cell`), and the pairs of every
    rest form ONE betting sequence in time order, each pair at equal weight
    (the inverse-variance weighting across strata the 2026-11-03 review
    removed gave the constant, at-ceiling strata the most weight; equal
    weight gives none more). Each rest's window holds its first
    `max_runs_per_cell` pairs (`_rest_window`, a predictable selection, so
    the tests keep their level), and the cell is `at_cap` when the current
    rest's window is full. The keep test reads every pair: an older rest's
    benefit can keep a section, the safe error.

THE CURRENT-REST GUARD (pooled only). Every path toward removal reads the
current rest:

  * a `no-benefit` decision, by the remove test (rule 7) or the harm test
    (rule 4), decides only at a pair n where the pooled test is at its level
    AND, of pairs 1..n, at least `rest_guard_min_pairs` are beside the
    current rest, those span `min_cli_versions`, and the current rest's
    SHARE of the test's log wealth (the log gains of its own pairs, betting
    what the pooled test bet) is at log(1 / (1 - retire_confidence)) on its
    own. The bets are predictable (each is fixed by the pairs before it), so
    the share is a nonnegative supermartingale under "the section still
    helps by the margin beside the current rest", whatever the older rests
    showed, and Ville's inequality holds a false removal against TODAY's
    rest at 1 - retire_confidence. This is the non-contradiction condition
    made strict: the current rest's own evidence must decide the removal,
    and older rests only size its bets. A share that falls (the current rest
    shows the gain the older ones did not) can never decide. Otherwise the
    cell stays `insufficient` and the planner fires it beside the current
    rest;
  * the ceiling, no-harm and high-cell rules (rules 4 to 6), which park a
    cell and so can turn a keep in waiting into a proposed removal, and the
    floor (rule 2), which sets a cell aside, read the current rest's pairs
    only, as under `current`;
  * `no-clear-effect` (rule 8) needs the current rest's window full and its
    pairs spanning `min_cli_versions`.

`rest_guard_min_pairs` (6) is a floor under the share test, which cannot
reach its level in under three pairs: a removal never rests on one burst of
fires beside a rest that just changed. Each cell reports `current_rest_pairs`,
`rests` and `rest_guard` (the levels the current rest's shares reached).

THE BET PRIOR (`bet_prior`). Each test's running estimate starts from
pseudo-runs: by default NEUTRAL_BET_PRIOR (mean 0, variance 0.25, one run),
so the first bet is 0. compute_gates may pass a LEARNED prior per cell
(`fit_bet_prior`): the paired differences of OTHER subjects of the same
kind, stamped before the Monday (UTC) of the cell's first pair, clamped
(mean -0.2 to 0.5, variance at least 0.001, PRIOR_PSEUDO_RUNS (3)
pseudo-runs, however many differences it was fit on). It only sizes
the bets: since it is fixed before the cell's first pair, Ville's bound
holds whatever it is, and a wild fit can only slow or speed decisions. The
prior's version (that Monday) is recorded on the cell. It is refit from the
results on every evaluation, so the weekly plan job, which computes the
verdicts before it plans, refits it each run; nothing persists it.

KNOWN LIMITS, left for a later part:

  * A fixture with no objective checks (judge-only) can no longer decide:
    with the judge not voting, its cells stay `insufficient`. No skill or
    guidance fixture on main is judge-only today (the four Class C ones are
    pairwise but also have objective checks).

  * Runs share a CLI version, a model snapshot and an upstream state when
    they land in one burst, and both models share one fixture, so cells
    are less independent than the auto-removal rule's two-cell argument
    assumes (the review's M5). `min_cli_versions` is a weak guard.
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
from datetime import datetime, timedelta
from pathlib import Path

import yaml

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "evals" / "gate-policy.yml"
#: Where a report path in the results tree is published.
RESULTS_BLOB = ("https://github.com/Adam-S-Daniel/skills-evals/blob/"
                "persistent/eval-results/")
MODES = ("auto", "proposal")
#: Scored trials an arm of one run needs to count (#70's 3).
MIN_TRIALS_PER_RUN = 1
#: Counted runs on each arm before a cell where both arms pass at most
#: `floor_fraction` is set aside as `cannot-discriminate` (a fixture that
#: looks broken); under it the cell is `insufficient`, so the planner fires
#: it again rather than parking it on one unlucky run.
FLOOR_MIN_RUNS = 3
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
#: Each scalar key, its rule in words, and the rule. The objective margin is
#: below 1 so the removal test has a stake to make (BET_CAP / (1 - margin)).
SKILL_KEYS = {
    "objective_margin": ("a number from 0 and below 1", _number(0, 1, high_open=True)),
    "judge_margin": ("a number from 0 to 10", _number(0, 10)),
    "benefit_confidence": _LEVEL,
    "retire_confidence": _LEVEL,
    "min_cli_versions": ("an integer of at least 1", _count(1)),
    "max_runs_per_cell": ("an integer of at least 1", _count(1)),
    "max_runs_high_cell": ("an integer of at least 1, at most max_runs_per_cell",
                           _count(1)),
    "floor_fraction": ("a number from 0 and below 1", _number(0, 1, high_open=True)),
}


#: How an in-situ guidance cell reads runs beside older rests of the
#: guidance (module docstring, IN-SITU GUIDANCE CELLS): `current` reads only
#: the runs beside the rest on main (the rule of 2026-11-03);
#: `pooled-with-current-guard` (Adam, 2026-11-07) pools every rest, pair by
#: pair at equal weight, and guards every removal-direction decision with the
#: current rest's own evidence.
REST_POLICIES = ("current", "pooled-with-current-guard")
#: The `rest_policy` of a guidance block that names none, and of a policy
#: given in code without one.
DEFAULT_REST_POLICY = "pooled-with-current-guard"
#: The `rest_guard_min_pairs` of a guidance block that names none: the
#: least pairs beside the current rest a removal-direction decision needs.
DEFAULT_REST_GUARD_MIN_PAIRS = 6
#: The keys only the guidance block takes, each optional with its default.
GUIDANCE_ONLY_KEYS = ("rest_policy", "rest_guard_min_pairs")


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
            "guidance": (_policy_block(document["guidance"], "guidance", guidance=True)
                         if "guidance" in document else None)}


def _policy_block(block, name: str, guidance: bool = False) -> dict:
    """One block of thresholds (`skills:` or `guidance:`), checked. Only the
    guidance block takes GUIDANCE_ONLY_KEYS (a skill has no rest of the
    guidance): `rest_policy`, one of REST_POLICIES (default
    DEFAULT_REST_POLICY), and `rest_guard_min_pairs`, an integer from 1 to
    `max_runs_per_cell` (default DEFAULT_REST_GUARD_MIN_PAIRS). An unknown
    `rest_policy` fails: unlike `retirement_mode`, no value of it is safe to
    fall back to silently."""
    if not isinstance(block, dict):
        raise GatePolicyError(f"gate policy {name} must be a mapping")
    allowed = set(SKILL_KEYS) | {"retirement_mode"} | (
        set(GUIDANCE_ONLY_KEYS) if guidance else set())
    unknown = sorted(set(block) - allowed)
    if unknown:
        raise GatePolicyError(f"gate policy {name} has unknown keys {unknown}")
    out = {}
    for key, (words, valid) in SKILL_KEYS.items():
        if key not in block:
            raise GatePolicyError(f"gate policy {name} is missing {key}")
        if not valid(block[key]):
            raise GatePolicyError(f"gate policy {name}.{key} must be {words}")
        out[key] = block[key]
    if out["max_runs_high_cell"] > out["max_runs_per_cell"]:
        raise GatePolicyError(f"gate policy {name}.max_runs_high_cell must be "
                              f"{SKILL_KEYS['max_runs_high_cell'][0]}")
    mode = block.get("retirement_mode")
    out["retirement_mode"] = mode if mode in MODES else "proposal"
    if guidance:
        rest_policy = block.get("rest_policy", DEFAULT_REST_POLICY)
        if not isinstance(rest_policy, str) or rest_policy not in REST_POLICIES:
            raise GatePolicyError(f"gate policy {name}.rest_policy must be one of "
                                  f"{', '.join(REST_POLICIES)}, not {rest_policy!r}")
        guard = block.get("rest_guard_min_pairs", DEFAULT_REST_GUARD_MIN_PAIRS)
        if not _count(1)(guard) or guard > out["max_runs_per_cell"]:
            raise GatePolicyError(f"gate policy {name}.rest_guard_min_pairs must be an "
                                  "integer of at least 1, at most max_runs_per_cell")
        out.update(rest_policy=rest_policy, rest_guard_min_pairs=guard)
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
# Statistics: the betting confidence sequence (module docstring, THE BOUNDS).

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


#: The share of the largest safe stake a bet may take (the threshold sweep's
#: c = 0.9): a bet of 1 / (the payoff's worst loss) could lose everything on
#: one pair, so every bet stays at most BET_CAP of it.
BET_CAP = 0.9
#: The bet prior with no learned one: (mean, variance, pseudo-runs) of a
#: test's payoff before its first pair. A mean of 0 makes the first bet 0.
NEUTRAL_BET_PRIOR = (0.0, 0.25, 1.0)
#: The least variance a bet's running estimate uses, so a run of identical
#: payoffs cannot divide by zero (the sweep's 1e-6).
MIN_BET_VARIANCE = 1e-6
#: A learned bet prior's clamps (`fit_bet_prior`): its mean, least variance
#: and pseudo-runs. A wild fit can then only mis-size bets.
PRIOR_MEAN_RANGE = (-0.2, 0.5)
PRIOR_MIN_VARIANCE = 0.001
PRIOR_PSEUDO_RUNS = 3.0
#: Cells with two or more pairs a learned prior needs; with fewer, the
#: neutral prior.
PRIOR_MIN_CELLS = 3
#: Bisection steps for a display bound (`betting_bound`): 2^-30 of the range.
BOUND_STEPS = 30


def log_wealth(payoffs: list, worst: float, prior: tuple = NEUTRAL_BET_PRIOR) -> list:
    """The running log wealth of one one-sided betting test (aGRAPA, capped):
    after each payoff y_t, log prod(1 + lambda_s y_s) over s <= t. `worst`
    (> 0) is the largest loss a payoff can carry (every y_t >= -worst), so
    lambda_t lies in [0, BET_CAP / worst]. lambda_t = mu / (var + mu^2) of the
    payoffs before t, started from `prior` = (mean, variance, pseudo-runs);
    it never sees y_t, so under H0 (E[y_t | past] <= 0) the wealth is a
    nonnegative supermartingale and Ville's inequality bounds the chance it
    ever reaches 1/alpha by alpha, whatever the prior."""
    if not worst > 0:
        raise ValueError("a betting test needs a payoff bounded below")
    mean0, var0, n0 = prior
    total, square, n = mean0 * n0, (var0 + mean0 * mean0) * n0, n0
    cap = BET_CAP / worst
    out, wealth = [], 0.0
    for y in payoffs:
        mu = total / n if n else 0.0
        var = max(square / n - mu * mu, MIN_BET_VARIANCE) if n else 0.25
        bet = min(max(mu / (var + mu * mu), 0.0), cap)
        wealth += math.log1p(bet * y)
        out.append(wealth)
        total, square, n = total + y, square + y * y, n + 1
    return out


def _test_prior(bet_prior: dict | None, shift: float, sign: int) -> tuple:
    """The (mean, variance, pseudo-runs) of a test's payoff sign * (D - shift)
    from a learned prior on D, or NEUTRAL_BET_PRIOR."""
    if not bet_prior:
        return NEUTRAL_BET_PRIOR
    return (sign * (bet_prior["mean"] - shift), bet_prior["variance"], bet_prior["n"])


def keep_wealth(ds: list, bet_prior: dict | None = None, at: float = 0.0) -> list:
    """The keep test's running log wealth against H0: E[D] <= `at`."""
    return log_wealth([d - at for d in ds], 1 + at, _test_prior(bet_prior, at, 1))


def remove_wealth(ds: list, margin: float, bet_prior: dict | None = None) -> list:
    """The remove test's running log wealth against H0: E[D] >= `margin`."""
    return log_wealth([margin - d for d in ds], 1 - margin,
                      _test_prior(bet_prior, margin, -1))


def ceiling_wealth(withouts: list, floor: float) -> list:
    """The ceiling test's running log wealth against H0: E[without run mean]
    <= `floor` (1 - margin): payoffs o - floor, at least -floor, on neutral
    bets. Rejecting says, at its level, that the task leaves the subject no
    room to show the margin."""
    return log_wealth([o - floor for o in withouts], floor)


def harm_wealth(ds: list, bet_prior: dict | None = None) -> list:
    """The harm test's running log wealth against H0: E[D] >= 0 (payoffs -D):
    rejecting says the subject lowers results, which needs no headroom."""
    return remove_wealth(ds, 0.0, bet_prior)


def first_crossing(wealth: list, alpha: float) -> int | None:
    """The 1-based pair at which `wealth` (log) first reaches 1/alpha, or None."""
    threshold = -math.log(alpha)
    return next((i + 1 for i, w in enumerate(wealth) if w >= threshold), None)


def reached(wealth: list) -> float:
    """The level a test reached so far: 1 - 1 / its largest wealth (Ville's
    p-value is 1 / sup wealth), 0 before any pair or below a wealth of 1."""
    best = max(wealth, default=0.0)
    return max(0.0, 1 - math.exp(-best)) if best > 0 else 0.0


def ville_p(wealth: list) -> float:
    """Ville's p-value of a test so far: min(1, 1 / its largest wealth)."""
    return min(1.0, math.exp(-max(wealth, default=0.0)))


def betting_bound(ds: list, alpha: float, side: str, bet_prior: dict | None = None) -> float:
    """One end of the betting confidence sequence at one-sided level 1 -
    `alpha`, for display: `lower`, the largest a whose keep-type test of
    E[D] <= a has rejected; `upper`, the smallest b whose remove-type test of
    E[D] >= b has rejected. Found by bisection over (-1, 1), which assumes
    the rejection is monotone in the tested value; it is for display, and
    no decision reads it (decisions run the tests at 0 and at the margin)."""
    edge = 1 - 1e-9

    def rejects(value):
        wealth = (keep_wealth(ds, bet_prior, value) if side == "lower"
                  else remove_wealth(ds, value, bet_prior))
        return first_crossing(wealth, alpha) is not None

    if side == "lower":
        if not rejects(-edge):
            return -1.0
        lo, hi = -edge, edge
        if rejects(hi):
            return 1.0
        for _ in range(BOUND_STEPS):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if rejects(mid) else (lo, mid)
        return lo
    if not rejects(edge):
        return 1.0
    lo, hi = -edge, edge
    if rejects(lo):
        return -1.0
    for _ in range(BOUND_STEPS):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if rejects(mid) else (mid, hi)
    return hi


def sequence_block(ds: list, margin: float, keep_alpha: float, remove_alpha: float,
                   bet_prior: dict | None = None, scale: float = 1.0) -> dict:
    """One figure's statistics over paired differences `ds` (in [-1, 1]):
    the keep and remove tests, where each first rejected (`keep_at`,
    `remove_at`, 1-based pairs, or None), the levels they reached, and the
    display bounds. `scale` multiplies the reported delta and bounds back to
    the figure's own scale (10 for the judge)."""
    keep, remove = keep_wealth(ds, bet_prior), remove_wealth(ds, margin, bet_prior)
    return {"delta": _mean(ds) * scale, "pairs": len(ds),
            "keep_at": first_crossing(keep, keep_alpha),
            "remove_at": first_crossing(remove, remove_alpha),
            "helps_confidence": reached(keep), "no_help_confidence": reached(remove),
            "keep_p": ville_p(keep),
            "benefit_lower": betting_bound(ds, keep_alpha, "lower", bet_prior) * scale,
            "retire_upper": betting_bound(ds, remove_alpha, "upper", bet_prior) * scale}


def fit_bet_prior(cells: list, margin: float, version: str | None = None) -> dict | None:
    """A learned bet prior (module docstring, THE BET PRIOR) from `cells`, a
    list of {"ds": paired differences, "without_mean": the without arm's mean
    run mean}: the mean of every pair's D and the mean within-cell variance
    over cells with two or more pairs, clamped, at PRIOR_PSEUDO_RUNS
    pseudo-runs. A cell without headroom (without mean above 1 - `margin`)
    is left out, as the threshold sweep fitted it. None with fewer than
    PRIOR_MIN_CELLS cells of two or more pairs."""
    usable = [c["ds"] for c in cells
              if c["ds"] and c["without_mean"] is not None
              and c["without_mean"] <= 1 - margin]
    spread = [_variance(ds) for ds in usable if len(ds) >= 2]
    if len(spread) < PRIOR_MIN_CELLS:
        return None
    mean = _mean([d for ds in usable for d in ds])
    return {"mean": min(max(mean, PRIOR_MEAN_RANGE[0]), PRIOR_MEAN_RANGE[1]),
            "variance": max(_mean(spread), PRIOR_MIN_VARIANCE),
            "n": PRIOR_PSEUDO_RUNS,
            "cells": len(spread), "version": version}


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

#: Headroom cells, every one `no-benefit`, a subject needs before its
#: removal may be automatic (module docstring, THE VERDICT).
AUTO_MIN_HEADROOM_CELLS = 2
#: The least without-arm mean at which a high cell may stop at
#: `max_runs_high_cell` pairs as `ceiling-unconfirmed` (round 3's M2).
HIGH_STOP_MIN_WITHOUT = 0.90


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


def _judge_usable(arms: dict) -> bool:
    """Whether two arm summaries' judge figures can be reported: no counted
    run judged conditionally, or every one of both arms has its figure (a
    skipped conditional call is a sample biased toward no benefit)."""
    conditional = any(arms[a]["judge_conditional_runs"] for a in arms)
    complete = all(arms[a]["judge_runs"] == arms[a]["runs"] for a in arms)
    return bool(arms["with"]["judge_run_means"] and arms["without"]["judge_run_means"]) \
        and (complete or not conditional)


def pair_runs(with_runs: list, without_runs: list) -> tuple:
    """(pairs, unpaired) of one cell's counted runs (module docstring, THE
    PAIR IS THE UNIT): a with run and a without run with the same timestamp
    are one pair; of two runs of one role with one timestamp the first by
    (timestamp, path) pairs. Pairs are ordered by (timestamp, the with run's
    path); `unpaired` is every other run given."""
    def first(runs):
        out = {}
        for run in sorted(runs, key=_order):
            out.setdefault(run["timestamp"], run)
        return out
    w, o = first(with_runs), first(without_runs)
    pairs = sorted(((w[t], o[t]) for t in set(w) & set(o)), key=lambda p: _order(p[0]))
    paired = {id(r) for pair in pairs for r in pair}
    return pairs, [r for r in with_runs + without_runs if id(r) not in paired]


def differences(pairs: list, field: str = "run_mean", scale: float = 1.0) -> list:
    """The pairs' differences (with - without) / `scale` of `field`, over the
    pairs where both runs have it."""
    out = []
    for w, o in pairs:
        a, b = w["numbers"][field], o["numbers"][field]
        if a is not None and b is not None:
            out.append((a - b) / scale)
    return out


def _rest_window(pairs: list, keys: list, current, cap: int) -> tuple:
    """(window, is_current) of a pooled in-situ cell (IN-SITU GUIDANCE CELLS):
    the first `cap` pairs of EACH rest, in the cells' order, and whether each
    is beside the `current` rest. Whether a pair enters depends only on the
    pairs before it, so the window is a predictable selection and every
    betting test over it keeps its level; each rest's window is frozen at its
    cap, as a whole cell's is under `current`."""
    seen: dict = {}
    window, is_current = [], []
    for pair, key in zip(pairs, keys):
        if seen.get(key, 0) < cap:
            seen[key] = seen.get(key, 0) + 1
            window.append(pair)
            is_current.append(key == current)
    return window, is_current


def _classify(pairs: list, policy: dict, family: int = 1,
              bet_prior: dict | None = None, rest: dict | None = None) -> dict:
    """Rules 1 to 8 of the module docstring (A CELL'S CLASS), over a cell's
    `pairs` in order: the first `max_runs_per_cell` decide, and a removal's
    CLI versions are read over the pairs that entered it. `family` is the
    subject's keep family m.

    `rest` (an in-situ guidance cell under `pooled-with-current-guard`):
    {"keys": each pair's rest (`pair_key`), "current": the rest on main,
    "min_pairs": `rest_guard_min_pairs`}. The keep, remove and harm tests
    then bet over every rest's pairs (`_rest_window`), each pair at equal
    weight, while everything that parks a cell, sets it aside, caps it or
    lets a removal decide reads the current rest (module docstring, IN-SITU
    GUIDANCE CELLS, THE CURRENT-REST GUARD). None is the rule for skills and
    for `current`: every pair is beside the current content."""
    cap = policy["max_runs_per_cell"]
    if rest is None:
        window = pairs[:cap]
        is_current = [True] * len(window)
        held_current = len(pairs)
    else:
        window, is_current = _rest_window(pairs, rest["keys"], rest["current"], cap)
        held_current = sum(is_current)
    current_window = [p for p, c in zip(window, is_current) if c]
    arms = {"with": _arm_summary([w for w, _ in window]),
            "without": _arm_summary([o for _, o in window])}
    current_arms = arms if rest is None else {
        "with": _arm_summary([w for w, _ in current_window]),
        "without": _arm_summary([o for _, o in current_window])}
    cli = sorted({v for pair in window for r in pair for v in r["cli_versions"]})
    margin = policy["objective_margin"]
    keep_alpha = (1 - policy["benefit_confidence"]) / family
    remove_alpha = 1 - policy["retire_confidence"]
    out = {**arms, "cli_versions": cli, "pairs": len(pairs), "pairs_used": len(window),
           # Round 2's C1: the window is frozen, so more fires change nothing.
           # Pooled, each rest's window is, so the cell is at its cap when
           # the CURRENT rest's is: more fires beside it change nothing.
           "at_cap": held_current >= cap,
           "objective": None, "judge": None, "keep_tests": [], "keep_family": family,
           "bet_prior": bet_prior, "headroom": None, "without_mean": None}
    if rest is not None:
        out.update(rest_policy="pooled-with-current-guard",
                   current_rest_pairs=len(current_window),
                   rests=len(set(rest["keys"])), rest_guard=None)

    def done(cls, reason):
        return {**out, "class": cls, "reason": reason}

    if not window:
        return done("insufficient", "no pair: an arm has no counted run, or no fire "
                    "has both arms counted")
    # The floor sets a cell aside, which lets the subject's other cells
    # remove it, so pooled it reads the current rest alone.
    rates = [current_arms[a]["pass_rate"] for a in current_arms]
    if all(r is not None and r <= policy["floor_fraction"] for r in rates):
        if len(current_window) >= FLOOR_MIN_RUNS:
            return done("cannot-discriminate", "both arms' pass rate at or below "
                        f"{policy['floor_fraction']} over {len(current_window)} pairs: "
                        "the fixture looks broken")
        return done("insufficient", "both arms' pass rate at or below "
                    f"{policy['floor_fraction']}; {FLOOR_MIN_RUNS} pairs decide whether "
                    "the fixture is broken")
    usable, usable_current = [], []
    for (w, o), c in zip(window, is_current):
        if w["numbers"]["run_mean"] is not None and o["numbers"]["run_mean"] is not None:
            usable.append((w, o))
            usable_current.append(c)
    ds = differences(usable)
    if not ds:
        return done("insufficient", "no run with objective checks on an arm")
    objective = sequence_block(ds, margin, keep_alpha, remove_alpha, bet_prior)
    out["objective"] = objective
    out["keep_tests"] = [{"route": "objective", "p": objective["keep_p"]}]
    # The judge is reported, never decides (2026-11-03): a removal it had to
    # agree to was blocked for good wherever its call was skipped (the
    # review's M2), and its keep route was a second family member.
    if _judge_usable(arms):
        jd = differences(window, "judge_mean", 10.0)
        if jd:
            out["judge"] = {**sequence_block(jd, policy["judge_margin"] / 10, keep_alpha,
                                             remove_alpha, None, scale=10.0),
                            "votes": False}
    # The ceiling, no-harm and high-cell rules park a cell (a parked cell
    # does not vote, so it can turn a keep in waiting into a proposed
    # removal) and read the without arm's level, which is what a change of
    # rest moves, so pooled they read the current rest alone: pooling never
    # parks a cell the current rest would not.
    current_usable = [p for p, c in zip(usable, usable_current) if c]
    withouts = [o["numbers"]["run_mean"] for _, o in current_usable]
    current_ds = differences(current_usable)
    without_mean = _mean(withouts) if withouts else None
    floor = 1 - margin
    ceiling_at = first_crossing(ceiling_wealth(withouts, floor), remove_alpha) \
        if floor > 0 and withouts else None
    harm_at = first_crossing(harm_wealth(ds, bet_prior), remove_alpha)
    high = without_mean is not None and without_mean > floor
    out.update(headroom=ceiling_at is None, without_mean=without_mean,
               ceiling_at=ceiling_at, harm_at=harm_at)

    def versions(n, current_only=False):
        """The CLI versions of the first `n` usable pairs (with
        `current_only`, of those beside the current rest)."""
        return sorted({v for pair, c in zip(usable[:n], usable_current[:n])
                       if c or not current_only for r in pair for v in r["cli_versions"]})

    threshold = -math.log(remove_alpha)

    def current_share(wealth):
        """The current rest's share of a pooled test's running log wealth:
        after pair n, the sum of the log gains of the pairs up to n beside
        the current rest, betting what the pooled test bet."""
        out_share, total, previous = [], 0.0, 0.0
        for w, c in zip(wealth, usable_current):
            if c:
                total += w - previous
            previous = w
            out_share.append(total)
        return out_share

    def decided_at(wealth):
        """The STOPPING TIME of a removal-side test (round 2's C1): the first
        pair n at which its running wealth is at 1/remove_alpha AND the
        pairs so far span `min_cli_versions`. The event {decided_at is not
        None} lies inside {the wealth ever reaches 1/alpha}, which Ville's
        inequality bounds by alpha under H0, so the level holds. The wealth
        must be at the threshold at n itself: a pair that knocks it under
        (a late D = +1 on a new version) does not decide.

        Pooled (`rest`), THE CURRENT-REST GUARD also holds at n: at least
        `min_pairs` of pairs 1..n are beside the current rest, those span
        `min_cli_versions`, and the current rest's share of the wealth
        (`current_share`) is itself at 1/remove_alpha. That share is a test
        martingale for H0 on the current rest alone, whatever the older
        rests showed, so a removal keeps its level against TODAY's rest."""
        need = policy["min_cli_versions"]
        if rest is None:
            return next((i + 1 for i, w in enumerate(wealth)
                         if w >= threshold and len(versions(i + 1)) >= need), None)
        share = current_share(wealth)
        seen = 0
        for i, w in enumerate(wealth):
            seen += usable_current[i]
            if w >= threshold and share[i] >= threshold and seen >= rest["min_pairs"] \
                    and len(versions(i + 1, current_only=True)) >= need:
                return i + 1
        return None

    def awaiting(crossed, what):
        """A test that crossed but has not decided: more pairs on a second
        CLI version (pooled: more pairs beside the current rest) can still
        decide it, up to the cap."""
        if rest is not None:
            found = versions(len(usable), current_only=True)
            return done("insufficient", f"{what} on the numbers (the pooled test crossed "
                        f"at pair {crossed}), but the current-rest guard is not met: "
                        f"{len(current_usable)} pair(s) beside the current rest (at least "
                        f"{rest['min_pairs']} needed), spanning {len(found)} CLI "
                        f"version(s) of {policy['min_cli_versions']}, and the current "
                        "rest's share of the test must reach its level on its own")
        found = versions(len(usable))
        return done("insufficient", f"{what} on the numbers (the test crossed at pair "
                    f"{crossed}), but it has not been at its level on pairs spanning "
                    f"{policy['min_cli_versions']} CLI versions ({len(found)} so far)")

    def capped_class():
        """Rule 8: the cap reached with no test deciding (pooled: the
        current rest's cap, on the current rest's CLI versions)."""
        found = versions(len(usable), current_only=rest is not None)
        if len(found) < policy["min_cli_versions"]:
            return done("insufficient", f"no clear effect on the numbers, but {len(found)} "
                        f"CLI version(s) in the pairs, under the "
                        f"{policy['min_cli_versions']} a removal needs")
        return done("no-clear-effect", f"{cap} pairs and neither test rejected: no clear "
                    "effect, which can only propose a removal")

    keep_at, remove_at = objective["keep_at"], objective["remove_at"]
    harm_pooled = harm_wealth(ds, bet_prior)
    remove_pooled = remove_wealth(ds, margin, bet_prior)
    harm_decided = decided_at(harm_pooled)
    remove_decided = decided_at(remove_pooled)
    # Round 2's M1: no harm beyond the margin (H0: E[D] <= -margin), at the
    # remove level. A ceiling cell parks only when this rejects too; pooled,
    # it reads the current rest, as the ceiling test does.
    noharm_at = first_crossing(keep_wealth(current_ds, bet_prior, -margin), remove_alpha) \
        if current_ds else None
    out.update(harm_decided_at=harm_decided, remove_decided_at=remove_decided,
               noharm_at=noharm_at)
    if rest is not None:
        remove_share, harm_share = current_share(remove_pooled), current_share(harm_pooled)
        out["rest_guard"] = {
            "min_pairs": rest["min_pairs"], "current_rest_pairs": len(current_usable),
            "met_pairs": len(current_usable) >= rest["min_pairs"],
            # The levels the current rest's shares reached (Ville's 1 - 1/W).
            "no_help_confidence": reached(remove_share),
            "harm_confidence": reached(harm_share),
            "remove_share_at": first_crossing(remove_share, remove_alpha),
            "harm_share_at": first_crossing(harm_share, remove_alpha)}
    capped = held_current >= cap
    # Round 3's M3: the keep is compared with the removal's STOPPING TIME,
    # not its first crossing. A remove crossing that never decided (one CLI
    # version) must not outrank a keep reached later; the keep's own
    # crossing bounds its error either way.
    if keep_at is not None and (remove_decided is None or keep_at <= remove_decided):
        return done("benefit", f"the keep test rejected at pair {keep_at}: confident at "
                    f"{policy['benefit_confidence']:.0%} across the subject's {family} "
                    "cell(s) that the gain is above 0")
    if (ceiling_at is not None or high) and harm_at is not None:
        # Round 1's M1: a cell at the ceiling can still show HARM, which
        # needs no headroom, so it is never hidden as `ceiling`.
        if harm_decided is None:
            return awaiting(harm_at, "harm")
        return done(
            "no-benefit", f"the harm test decided at pair {harm_decided} (crossed at "
            f"{harm_at}): confident at {policy['retire_confidence']:.0%} that the "
            "subject lowers results here, which needs no headroom to show")
    if ceiling_at is not None and noharm_at is not None:
        return done("ceiling", f"the ceiling test rejected at pair {ceiling_at} and the "
                    f"no-harm test at pair {noharm_at}: confident at "
                    f"{policy['retire_confidence']:.0%} that the without arm's mean is "
                    f"above 1 - {margin} and the subject costs less than {margin} here, "
                    "so this task leaves no room to show the margin; the cell does not "
                    "vote on removal and needs a harder fixture")
    if high or ceiling_at is not None:
        # High on the sample, or on the bound without the no-harm test:
        # neither park the cell nor let it vote. Round 2's M2: after
        # `max_runs_high_cell` pairs it stops being fired, but only once the
        # no-harm test has rejected (round 3's M2: a sample-mean stop hid a
        # harm of 0.15 two times in three) and the without arm is at least
        # HIGH_STOP_MIN_WITHOUT (round 3's M2: a stop at 0.85 parked a third
        # of the cells whose true without arm was 0.82).
        if len(current_window) >= policy["max_runs_high_cell"] and noharm_at is not None \
                and without_mean >= HIGH_STOP_MIN_WITHOUT:
            return done("ceiling-unconfirmed", f"{len(current_window)} pairs, the without arm "
                        f"averaging {without_mean:.3f}, and the no-harm test rejected at "
                        f"pair {noharm_at}, but the ceiling test has not: the cell stops "
                        "being fired, does not vote on removal and needs a harder fixture")
        if not capped:
            return done("insufficient", f"the without arm averages {without_mean:.3f}, "
                        f"above 1 - {margin}, but the ceiling and no-harm tests have not "
                        "both rejected: more pairs decide whether the cell has headroom")
        # At the cap, a high cell the stop did not take ends on the cap
        # rule: the remove test does not decide it (it cannot show the margin).
        return capped_class()
    if remove_at is not None:
        if remove_decided is None:
            return awaiting(remove_at, "no benefit")
        return done(
            "no-benefit", f"the remove test decided at pair {remove_decided} (crossed at "
            f"{remove_at}): confident at {policy['retire_confidence']:.0%} that the gain "
            f"is under {margin}")
    if capped:
        return capped_class()
    return done("insufficient", "neither test has rejected yet")


def run_key(run: dict) -> str:
    """A run's name in `runs_used`:
    `<path>#<fixture>#<role>`, since one `<timestamp>` holds every fixture."""
    return f"{run['path']}#{run['fixture'] or ''}#{run['role']}"


def classify_cell(with_runs: list, without_runs: list, policy: dict,
                  judge_carried: bool = False, family: int = 1, bet_prior=None,
                  errored_blocks: bool = True, rest: dict | None = None) -> dict:
    """A cell's class over all its counted runs (module docstring), paired
    by `pair_runs`. `bet_prior` is a learned prior, None (neutral), or a
    function of the cell's first pair's timestamp returning either.
    `errored_blocks` (skills; not in-situ guidance) keeps a cell with an
    agent-errored trial from `no-benefit` and `no-clear-effect`, so it never
    leads to a removal, automatic or proposed (the review's m4).

    `rest` (an in-situ guidance cell under `pooled-with-current-guard`):
    {"current": the rest on main, "min_pairs": `rest_guard_min_pairs`}. Runs
    pair only within one rest (one `pair_key`), never across two, and the
    pairs of every rest are ordered together for `_classify`."""
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
    if rest is None:
        pairs, unpaired = pair_runs(*counted)
        rest_info = None
    else:
        pairs, unpaired = [], []
        for key in sorted({r.get("pair_key") for r in counted[0] + counted[1]}, key=str):
            some, lone = pair_runs([r for r in counted[0] if r.get("pair_key") == key],
                                   [r for r in counted[1] if r.get("pair_key") == key])
            pairs += some
            unpaired += lone
        pairs.sort(key=lambda p: _order(p[0]))
        rest_info = {**rest, "keys": [w.get("pair_key") for w, _ in pairs]}
    if callable(bet_prior):
        bet_prior = bet_prior(pairs[0][0]["timestamp"]) if pairs else None
    full = _classify(pairs, policy, family, bet_prior, rest_info)
    cls, reason = full["class"], full["reason"]
    errored = sum(r["numbers"]["errored_trials"] for r in with_runs + without_runs)
    if cls in ("no-benefit", "no-clear-effect") \
            and ((errored and errored_blocks) or NO_CHECKS_REASON in skipped):
        # An agent's errors can only help keep: dropping or scoring around
        # them would compare only the trials that went well.
        cls, reason = "insufficient", (f"{cls} on the numbers, but the cell has "
                                       f"{errored} agent-errored trial(s) or a run "
                                       "skipped as anomalous, so it cannot retire")
    return {**full, "class": cls, "reason": reason, "judge_carried": judge_carried,
            "skipped": skipped, "unpaired": len(unpaired), "errored_trials": errored}


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
               strata: bool = False, rest_policy: str = DEFAULT_REST_POLICY) -> dict:
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
    `run_stamps_on_model` is every such timestamp, sorted, also output only:
    the planner asks whether a run landed inside a given fire's window,
    which the newest stamp alone cannot answer once a later run lands.

    `strata` (#557, in-situ guidance only): no `_joint_context`; each cell
    holds the current-content runs on its model made beside the rest of the
    guidance on main (`pair_key` equal to `expected`'s `rest_digest`; the
    module docstring, IN-SITU GUIDANCE CELLS), under `strata` too, and its
    own key {tested_digest, fixture_digest, rest_digest}: an unknown rest
    makes the key incomplete. With `rest_policy` `pooled-with-current-guard`
    (the module docstring, IN-SITU GUIDANCE CELLS) the cell holds the runs
    beside EVERY rest instead, under the same key otherwise: the with arm's
    tested digest, the fixture digest, the model, and no fleet hook set (a
    hooked run's `pair_key` carries its hook set, so it never equaled the
    rest on main either). Each rest is a stratum, and `rest_digest` still
    names the current one, which the guard reads."""
    if rest_policy not in REST_POLICIES:
        raise ValueError(f"unknown rest_policy {rest_policy!r}")
    if strata:
        return _pool_strata(runs, skill, models, expected,
                            pooled=rest_policy != "current")
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
            stamps = sorted(r["timestamp"] for r in mine if r["model"] == model)
            cells[(fixture, model)] = {
                "key": key, "on_model": len(stamps),
                "newest_on_model": stamps[-1] if stamps else None,
                "run_stamps_on_model": stamps,
                "with": [r for r in current_with if r["model"] == model
                         and r["arm_context_digest"] == with_context
                         and r.get("pair_key") == pair],
                "without": [r for r in current_without if r["model"] == model
                            and r["arm_context_digest"] == without_context
                            and r.get("pair_key") == pair]}
    return cells


def _pool_strata(runs: list, skill: str, models: list, expected: dict,
                 pooled: bool = False) -> dict:
    own = [r for r in runs if r["skill"] == skill]
    cells = {}
    for fixture, main in sorted(expected.items()):
        mine = [r for r in own if pooled_fixture(r, skill, expected) == fixture]
        tested, fdig = main.get("tested_digest"), main.get("fixture_digest")
        rest = main.get("rest_digest")
        for model in models:
            groups: dict = {}
            for run in mine:
                if run["model"] != model or not run.get("pair_key") or fdig is None \
                        or run["fixture_digest"] != fdig or rest is None:
                    continue
                if pooled:
                    # Any rest, but the hook part of the key as on main: none.
                    if run.get("fleet_hooks_digest") is not None:
                        continue
                elif run["pair_key"] != rest:
                    continue
                if run["role"] == "with" and (tested is None or run["tested_digest"] != tested):
                    continue
                groups.setdefault(run["pair_key"], {"with": [], "without": []})[
                    run["role"]].append(run)
            stamps = [r["timestamp"] for r in mine if r["model"] == model]
            cells[(fixture, model)] = {
                "key": {"tested_digest": tested, "fixture_digest": fdig, "rest_digest": rest},
                "on_model": len(stamps),
                "newest_on_model": max(stamps) if stamps else None,
                "run_stamps_on_model": sorted(stamps),
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
               expected: dict, bet_prior=None, strata: bool = False,
               family: bool = True) -> dict:
    """The verdict for `skill` over every fixture on main (`expected`, see
    `pool_cells`) x roster model cell (module docstring, THE VERDICT).
    `bet_prior` is None (neutral bets), a learned prior for every cell, or a
    function of a cell's first pair's timestamp (`prior_from_history`).

    `strata` (#557, in-situ guidance): cells hold the runs beside the rest
    of the guidance on main, or beside every rest under the policy's
    `rest_policy` `pooled-with-current-guard` (`pool_cells`; each cell is
    then classified with THE CURRENT-REST GUARD), and an agent-errored trial
    does not block a removal.

    `family` (default on): the keep is applied per SUBJECT. Every cell's
    keep test runs at (1 - benefit_confidence) / m, m = fixtures on main x
    roster models, known before any run (Bonferroni), so the subject keeps
    at `benefit_confidence` overall. The verdict records `keep_family` (m)
    and `keep_alpha`. The alone pair passes `family=False` (m = 1)."""
    m = len(expected) * max(1, len(models)) if family and expected else 1
    rest_policy = policy.get("rest_policy", DEFAULT_REST_POLICY) if strata else "current"
    pooled = rest_policy != "current"
    cells, used = [], set()
    for (fixture, model), pool in sorted(pool_cells(index.get("runs", []), skill,
                                                    models, expected, strata,
                                                    rest_policy).items()):
        arms = {"with": pool["with"], "without": pool["without"]}
        runs = arms["with"] + arms["without"]
        prime(runs)
        used.update(run_key(r) for r in runs)
        missing = sorted(k for k, v in pool["key"].items() if v is None)
        if not pool["on_model"]:
            cell = {"class": "missing", "reason": "no run on this model"}
        elif missing:
            cell = {"class": "insufficient",
                    "reason": f"pooling key incomplete: {', '.join(missing)}"}
        else:
            carried = any(r["judge_carried"] for r in runs)
            guard = {"current": pool["key"]["rest_digest"],
                     "min_pairs": policy.get("rest_guard_min_pairs",
                                             DEFAULT_REST_GUARD_MIN_PAIRS)} if pooled else None
            cell = classify_cell(arms["with"], arms["without"], policy, carried, m,
                                 bet_prior, errored_blocks=not strata, rest=guard)
        paused = (expected.get(fixture) or {}).get("scope_paused")
        if paused and cell["class"] not in PAUSE_KEEPS_CLASS:
            # Round 3's C1: the eval scope pass stopped firing this fixture.
            # Dropping its cells let the others remove a subject it helped,
            # so they stay, parked: a keep they earned before the pause
            # still keeps, a decided `no-benefit` still votes (round 4's
            # M1: the pause reads only the pooled without arm, so parking
            # it hid a decided harm of any size), and anything else neither
            # votes nor frees an automatic removal.
            cell = {**cell, "class": "paused", "class_before_pause": cell["class"],
                    "reason": f"paused by the eval scope pass ({paused}) and no longer "
                              f"fired; before the pause it was {cell['class']}: "
                              f"{cell['reason']}"}
        if paused:
            cell = {**cell, "scope_paused": paused}
        cells.append({"fixture": fixture or None, "model": model, "key": pool["key"],
                      "newest_on_model": pool["newest_on_model"],
                      "run_stamps_on_model": pool["run_stamps_on_model"], **cell,
                      "cost_usd": _finite_sum([r["numbers"]["cost_usd"] for r in runs]),
                      "cost_unknown_trials": sum(r["numbers"]["cost_unknown_trials"]
                                                 for r in runs),
                      "runs": {role: [_run_entry(r) for r in sorted(arms[role], key=_order)]
                               for role in arms}})
    out = {"cells": cells, "runs_used": sorted(used)}
    out.update(_verdict(cells, bool(expected)))
    if family and expected:
        out.update(keep_family=m, keep_alpha=1 - policy["benefit_confidence"])
    return out


#: Cells that do not vote on removal: `ceiling` (shown by the bounds) and
#: `ceiling-unconfirmed` (high at `max_runs_high_cell` pairs, round 2's M2),
#: whose without arm leaves no room, and `paused` (a fixture the eval scope
#: pass stopped firing, round 3's C1), which will get no more runs. A
#: retire verdict beside any of them is a proposal. scripts/plan_week.py
#: keeps a literal copy (it imports gates lazily); a test pins the two.
PARKED_CLASSES = frozenset({"ceiling", "ceiling-unconfirmed", "paused"})
#: The parked classes that say the without arm leaves no room.
CEILING_CLASSES = frozenset({"ceiling", "ceiling-unconfirmed"})
#: The classes a scope-paused fixture's cell keeps (round 4's M1): each was
#: decided at the gate's own level before the pause froze its window.
PAUSE_KEEPS_CLASS = frozenset({"benefit", "no-benefit"})


def _shows_ceiling(cell: dict) -> bool:
    """Whether a parked cell's own runs say its without arm leaves no room
    (round 4's M1): a ceiling class, or a cell the eval scope pass paused at
    the ceiling whose class before the pause was a ceiling class, or whose
    no-harm test had rejected with a without arm averaging at least
    HIGH_STOP_MIN_WITHOUT. The pause itself reads only a pooled sample of
    the without arm, which is not evidence enough to call a subject
    `ceiling`, and a floor or zero-use pause measures nothing."""
    if cell["class"] in CEILING_CLASSES:
        return True
    if cell["class"] != "paused" or cell.get("scope_paused") != "ceiling":
        return False
    if cell.get("harm_at") is not None:
        return False
    if cell.get("class_before_pause") in CEILING_CLASSES:
        return True
    without = cell.get("without_mean")
    return cell.get("noharm_at") is not None and without is not None \
        and without >= HIGH_STOP_MIN_WITHOUT


def _verdict(cells: list, any_fixture: bool) -> dict:
    """{verdict, reason} and, for `retire`, {removal, removal_reason}, over
    classified cells (module docstring, THE VERDICT)."""
    counted = [c for c in cells if c["class"] != "cannot-discriminate"]
    classes = {c["class"] for c in counted}
    headroom = [c for c in counted if c["class"] in ("no-benefit", "no-clear-effect")]
    if not any_fixture:
        return {"verdict": "insufficient", "reason": "no fixture on main"}
    if "benefit" in classes:
        return {"verdict": "keep", "reason": "a cell shows benefit"}
    if classes & {"insufficient", "missing"}:
        return {"verdict": "insufficient", "reason": "a cell is insufficient or missing"}
    if cells and not counted:
        return {"verdict": "cannot-discriminate", "reason": "every cell's fixture looks "
                "broken: both arms pass almost nothing"}
    if classes <= PARKED_CLASSES and classes:
        if all(_shows_ceiling(c) for c in counted):
            out = {"verdict": "ceiling", "reason": "every cell's without arm is at the "
                   "ceiling: the subject needs a fixture with headroom, not more runs"}
            if any(c["class"] == "paused" for c in counted):
                # Round 6's M1: a scope-paused fixture is off the schedule, so
                # it has no planner cell and no `fixture-ceiling` item.
                # scripts/plan_week.py lists the subject as a `paused-ceiling`
                # work item asking for the harder fixture.
                out["paused_ceiling"] = True
            return out
        # `unmeasured`: scripts/plan_week.py lists the subject as a
        # `paused-unmeasured` work item, since a paused fixture has no
        # planner cell to carry one.
        return {"verdict": "insufficient", "unmeasured": True, "reason": "every cell is "
                "parked, and a cell the eval scope pass paused does not show a ceiling on "
                "its own runs (or was paused for a floor or no use): no fixture is "
                "measuring the subject"}
    if not headroom or not classes <= PARKED_CLASSES | {"no-benefit", "no-clear-effect"}:
        # No cell (no roster model) or a class this verdict does not know:
        # never a retirement without evidence.
        return {"verdict": "insufficient", "reason": "no cell shows no benefit"}
    clear = all(c["class"] == "no-benefit" for c in headroom)
    parked = " (cells parked or with a broken fixture do not vote)" \
        if len(headroom) < len(cells) else ""
    ceilings = sum(c["class"] in PARKED_CLASSES for c in counted)
    if clear and ceilings:
        # The review's C1: a parked cell is evidence that did not vote, so a
        # removal beside one is for a person to make.
        return {"verdict": "retire", "removal": "proposal",
                "reason": f"every cell with headroom shows no benefit{parked}",
                "removal_reason": f"{ceilings} parked cell(s) (at the ceiling, or paused "
                                  "by the eval scope pass) did not vote"}
    if clear and len(headroom) >= AUTO_MIN_HEADROOM_CELLS:
        return {"verdict": "retire", "removal": "auto",
                "reason": f"every cell with headroom shows no benefit{parked}",
                "removal_reason": f"{len(headroom)} cells with headroom, every one "
                                  "no-benefit"}
    if clear:
        why = (f"only {len(headroom)} cell with headroom; an automatic removal needs "
               f"{AUTO_MIN_HEADROOM_CELLS}")
        reason = f"the one cell with headroom shows no benefit{parked}"
    else:
        why = "a cell reached the run cap with no clear effect"
        reason = f"no cell with headroom shows benefit, and one has no clear effect{parked}"
    return {"verdict": "retire", "removal": "proposal", "reason": reason,
            "removal_reason": why}


def _monday(stamp: str) -> str | None:
    """The `YYYYMMDDT000000Z` stamp of the Monday (UTC) of `stamp`'s week."""
    try:
        moment = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ")
    except (TypeError, ValueError):
        return None
    return (moment - timedelta(days=moment.weekday())).strftime("%Y%m%dT000000Z")


def paired_history(runs: list) -> list:
    """Every pair in `runs` (an index's runs of one kind), for learning a bet
    prior: {"subject", "cell", "timestamp", "d", "without"} per pair, a with
    and a without run of one (subject, fixture, model, guidance pair) with
    one timestamp, both counted with a run mean, the first by path. The
    cell groups a pair by its content as recorded (fixture digest, tested
    digest, pair key, and the fleet hook digest, so a variance is measured
    within one hook set as #605 asked of the old priors), not by main's, so
    the history known before a time does not depend on later edits."""
    arms: dict = {}
    for run in sorted(runs, key=_order):
        numbers = run_numbers(run["trials"], run.get("judge_conditional") is False)
        if not numbers["counted"] or numbers["run_mean"] is None:
            continue
        key = (run["skill"], run["fixture"], run["model"], run.get("pair"), run["timestamp"])
        arms.setdefault(key, {}).setdefault(run["role"], (run, numbers["run_mean"]))
    out = []
    for key, roles in sorted(arms.items(), key=lambda item: tuple(map(str, item[0]))):
        if "with" in roles and "without" in roles:
            w, mean_w = roles["with"]
            o, mean_o = roles["without"]
            out.append({"subject": key[0], "timestamp": key[4], "d": mean_w - mean_o,
                        "without": mean_o,
                        "cell": (key[0], key[1], key[2], key[3], w["fixture_digest"],
                                 w["tested_digest"], w.get("pair_key"),
                                 w.get("fleet_hooks_digest"))})
    return out


def prior_from_history(history: list, subject: str, margin: float):
    """The function `retirement` calls with a cell's first pair's timestamp:
    `fit_bet_prior` over the pairs of OTHER subjects in `history` stamped
    before that week's Monday (UTC), versioned by that Monday's date. Fixed
    before the cell's first pair, so the betting bound stays valid."""
    cache: dict = {}

    def prior(first: str):
        monday = _monday(first)
        if monday is None:
            return None
        if monday not in cache:
            cells: dict = {}
            for pair in history:
                if pair["subject"] != subject and pair["timestamp"] < monday:
                    cells.setdefault(pair["cell"], []).append(pair)
            cache[monday] = fit_bet_prior(
                [{"ds": [p["d"] for p in ps], "without_mean": _mean([p["without"] for p in ps])}
                 for ps in cells.values()], margin,
                f"{monday[:4]}-{monday[4:6]}-{monday[6:8]}")
        return cache[monday]
    return prior


# ---------------------------------------------------------------------------
# Guidance sections (skills-evals#124).

#: Each of a section's two comparisons, and the role of an arm in it by its
#: delivery mode. `in_situ` is the ablation, the whole guidance with and
#: without the section, and decides removal; `alone` is the section against
#: no guidance, and only says whether the section teaches the behavior.
GUIDANCE_PAIRS = {"in_situ": {"full": "with", "full-minus-section": "without"},
                  "alone": {"section": "with", "none": "without"}}
#: An alone cell of these classes has not decided whether the section helps
#: on its own: no run, a test that has not rejected, a fixture that cannot
#: tell, or one the eval scope pass paused.
ALONE_UNDECIDED_CLASSES = frozenset({"missing", "insufficient", "cannot-discriminate",
                                     "paused"})
ALONE_UNFINISHED_REASON = ("the section-alone check has not finished: an alone cell "
                           "(section vs none) has not decided, so it could still show "
                           "benefit and turn this into shorten-or-merge")


def alone_unfinished(alone_cells) -> bool:
    """Whether the section-alone pair is unfinished: no alone cell, or one
    whose class is in ALONE_UNDECIDED_CLASSES. Since 2026-11-03 the planner
    fires the alone pair only for a section leaning toward removal, so it
    may have few or no runs when the in-situ test reaches `retire`."""
    cells = [c for c in alone_cells or [] if isinstance(c, dict)]
    return not cells or any(c.get("class") in ALONE_UNDECIDED_CLASSES for c in cells)


def guidance_verdict(index: dict, models: list, section: str, policy: dict,
                     expected: dict, bet_prior=None) -> dict:
    """The verdict for one guidance section: `retirement` over its in-situ
    cells (every run of `index` whose `pair` is `in_situ`), and over its
    alone cells for contrast. `expected` is as for `pool_cells`, with the
    section's own extent digest as `tested_digest` and the rest of the
    guidance on main as `rest_digest`; a run's `pair_key` and arm context
    are the digest of the rest of the guidance it ran beside, so the two
    arms of a pair always ran beside the same rest. `bet_prior` applies to
    the in-situ cells; the alone cells bet neutrally.

    THE TWIST: a section whose in-situ verdict is `retire` while some alone
    cell shows `benefit` teaches the behavior, but the rest of the guidance
    already covers it. Its verdict is `shorten-or-merge`, never a removal.
    Every other in-situ verdict stands as it is.

    THE UNFINISHED ALONE PAIR (2026-11-03): the alone pair runs only for a
    section leaning toward removal (scripts/plan_week.py, THE ALONE PAIR),
    so a `retire` whose alone pair is unfinished (`alone_unfinished`) could
    still turn into shorten-or-merge. Its `removal` is then `proposal`,
    never `auto`, with ALONE_UNFINISHED_REASON.

    The in-situ cells hold only runs beside the rest on main (`retirement`
    with `strata`). The alone cells pool as before."""
    runs = index.get("runs", [])
    out = {pair: retirement({"runs": [r for r in runs if r.get("pair") == pair]},
                            models, section, policy, expected,
                            bet_prior if pair == "in_situ" else None,
                            strata=pair == "in_situ", family=pair == "in_situ")
           for pair in GUIDANCE_PAIRS}
    in_situ, alone = out["in_situ"], out["alone"]
    verdict, reason = in_situ["verdict"], in_situ["reason"]
    extra = {k: in_situ[k] for k in ("removal", "removal_reason", "unmeasured",
                                         "paused_ceiling")
             if k in in_situ}
    if verdict == "retire" and any(c["class"] == "benefit" for c in alone["cells"]):
        verdict, reason = ("shorten-or-merge", "no marginal benefit inside the whole "
                           "guidance, but a cell shows benefit alone (section vs "
                           "none): the rest of the guidance covers it")
        extra = {}
    elif verdict == "retire" and extra.get("removal") == "auto" \
            and alone_unfinished(alone["cells"]):
        extra = {**extra, "removal": "proposal", "removal_reason": ALONE_UNFINISHED_REASON}
    return {"verdict": verdict, "reason": reason, "in_situ_verdict": in_situ["verdict"],
            **extra, "cells": in_situ["cells"],
            "alone": {"verdict": alone["verdict"], "reason": alone["reason"],
                      "cells": alone["cells"]},
            "runs_used": sorted(set(in_situ["runs_used"]) | set(alone["runs_used"])),
            **{k: in_situ[k] for k in ("keep_family", "keep_alpha") if k in in_situ}}
