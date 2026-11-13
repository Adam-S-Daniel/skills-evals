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
keeps: the keep test held its level at whatever pair it stopped; not a
provisional pooled keep, whose `rest_guard.keep_final` is false, since no
current-rest run can now confirm it) or
`no-benefit` (round 4's M1: a harm or no-benefit decided at its stopping
time is evidence at the gate's level, so it votes; the pause reads only a
pooled sample of the without arm and must not hide it), and is otherwise
`paused`, recording `class_before_pause`: parked, so it neither votes nor
stands beside it. A subject whose every counted cell
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
  * otherwise `retire`, and its `removal` is always `auto` (2026-11-13: the
    owner wants removals to happen without his intervention). `removal_reason`
    still describes the evidence (the dashboard shows it): every headroom cell
    `no-benefit`, only one cell with headroom, a cell that reached the run cap
    with no clear effect, or parked cells that did not vote. Whether the bot
    can open the removal pull request itself, or files an `agent-ready` issue
    for the fleet worker, is scripts/retire_skill.py's business, not the
    verdict's.

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
    rest's window is full.
  * THE POOLED KEEP is two tests, each at half the cell's keep alpha
    (Bonferroni, so the cell still keeps at its share of
    `benefit_confidence`), and the earlier crossing keeps: the pooled keep
    test over every pair, which counts only from the pair at which the
    current rest has `rest_guard_min_pairs` pairs (Adam, 2026-11-07: an
    older rest alone never keeps; such a cell stays `insufficient` and is
    fired), and a keep test over the current rest's pairs alone, so a cell
    that helps today keeps at its cap whatever the older rests showed.
    Each route's `keep_tests` p is doubled for the same reason. A cell with
    no older pair in its window (ONE REST, the pooled adversarial round
    4's M2) is classified exactly as a `current` cell: one keep route at
    the full keep alpha, and `rest_guard` null.
  * THE STALE KEEP (the pooled adversarial rounds 2 and 3): a keep the
    pooled test made is NOT final. If the removal (below) decides at any
    pair, before or after it, the cell is `no-benefit`; and at the current
    rest's cap it LAPSES, since no more pairs can test it: the cell ends on
    the current rest's own rules (no-clear-effect, or `insufficient` on one
    CLI version), as a `current` cell would, so an older rest alone never
    keeps. A keep the current-rest keep test made stays final when it
    crossed no later than the removal's stopping time, as under `current`.
    A provisional keep reports `rest_guard.keep_final` false and its reason
    says so; one that a removal overrode or that lapsed reports its route's
    `keep_tests` p as 1, and every class a lapsed cell ends in says it
    lapsed. scripts/plan_week.py fires it as an undecided cell until the
    current rest's own keep crosses or its window is full.

THE CURRENT-REST GUARD (pooled only). Every path toward removal reads the
current rest:

  * a `no-benefit` decision by the remove test (rule 7) decides at the
    first pair n where, of pairs 1..n, at least `rest_guard_min_pairs` are
    beside the current rest, those span `min_cli_versions`, and the current
    rest's REMOVAL EVIDENCE (`remove_evidence`) is at
    log(1 / (1 - retire_confidence)). The evidence is the MEAN of two
    wealths: the current rest's SHARE of the pooled test's log wealth (the
    log gains of its own pairs, betting what the pooled test bet) and the
    wealth of the current rest's own remove test (its own bets over its own
    pairs, as under `current`). Both bets are predictable (each is fixed by
    the pairs before it), so each is a nonnegative supermartingale under
    "the section still helps by the margin beside the current rest",
    whatever the older rests showed; so is their mean, and Ville's
    inequality holds a false removal against TODAY's rest at
    1 - retire_confidence. The pooled wealth's own level is not required
    (the pooled adversarial round 3's m5: it added nothing to the level, and
    older gains can hold it down for good), so one rule serves a removal
    with or without a pooled keep before it. This is the non-contradiction
    condition made strict: the current rest's own evidence decides the
    removal, and older rests only size the share's bets. The remove test
    counts as CROSSED (rule 7's `remove_at`) at the evidence's first
    crossing; a crossed test whose floor or CLI versions are not yet met
    keeps the cell `insufficient` (to its cap, where a single CLI version
    leaves it so, as under `current`);
  * a `no-benefit` decision by the harm test (rule 4) decides the same
    way on its own HARM EVIDENCE (`harm_evidence`, the mean of its current
    share and the current rest's own harm test; the pooled adversarial
    round 4's M3: older gains held the pooled harm bets near zero, so a
    section harming today was never removed), and counts as crossed
    (`harm_at`) at that evidence's first crossing. A crossing the older
    rests made alone is never one (round 1's blocker: it had held a cell
    `insufficient` at its cap for good); a test that never crossed lets the
    cell fall through to the current rest's ceiling, high-cell and cap
    rules. The objective block's `remove_at` and `rest_guard`'s `pooled_*`
    fields report the pooled crossings for display;
  * the ceiling, no-harm and high-cell rules (rules 4 to 6), which park a
    cell and so can turn a keep in waiting into a proposed removal, and the
    floor (rule 2), which sets a cell aside, read the current rest's pairs
    only, as under `current`;
  * `no-clear-effect` (rule 8) needs the current rest's window full and its
    pairs spanning `min_cli_versions`.

`rest_guard_min_pairs` (6) is a floor under the evidence, which cannot
reach its level in under three pairs: a removal never rests on one burst of
fires beside a rest that just changed. Each cell reports `current_rest_pairs`
(its window's pairs beside the current rest, which the cap counts), `rests`
and `rest_guard` (`usable_current_rest_pairs`, those with a run mean on both
arms, which the guard counts; the levels the current rest's shares reached;
the pooled and current-rest keep crossings; `keep_final`; the current rest's
own remove test's and the removal evidence's crossings, `current_remove_at`
and `remove_evidence_at`; and `remove_evidence_confidence`, the level the
evidence reached, which the planner and the explorer read for the cell's
no-help level; `harm_evidence_at` and `harm_evidence_confidence`, the same
for the harm evidence; and `current_objective`, the current rest's own
`sequence_block`, which the explorer charts). `no_help_confidence`, `harm_confidence`,
`remove_share_at` and `harm_share_at` still report the shares alone.

CURRENT LOG WEALTH (reporting only). The levels and p-values above read a
test's PEAK wealth, but a test rejects only when its running wealth crosses,
and betting wealth can fall after a peak. So each `sequence_block` also
reports `keep_log_wealth` and `no_help_log_wealth`, the keep and remove
tests' last log wealth; each `keep_tests` entry its route's as `log_wealth`
(on its p's scale: less log 2 for a doubled pooled route, None where its p
is pinned to 1); and `rest_guard` its removal evidence's as
`remove_evidence_log_wealth`. No decision reads them; scripts/plan_week.py's
`pairs_to_verdict` projects from them.

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
#: Why a run with too few scored or agent-errored trials does not count.
FEW_TRIALS_REASON = f"fewer than {MIN_TRIALS_PER_RUN} scored or errored trials"
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


def last_wealth(wealth: list) -> float:
    """A test's CURRENT log wealth: its last value, 0 before any pair.
    Reporting only (the planner's projection starts here): `reached` and
    `ville_p` read the peak, but a test rejects only when its running wealth
    crosses (`first_crossing`), and betting wealth can fall after a peak."""
    return wealth[-1] if wealth else 0.0


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
            # The tests' current (last) log wealth, beside the peak-based
            # levels above: reporting only, no decision reads them.
            "keep_log_wealth": last_wealth(keep), "no_help_log_wealth": last_wealth(remove),
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
        skip = FEW_TRIALS_REASON
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

    def done(cls, reason, at=None):
        # `decided_at` (RUN UTILITY): the usable pair at which the class
        # was decided, None for a class that has not decided.
        return {**out, "class": cls, "reason": reason, "decided_at": at}

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
    if rest is not None and all(usable_current):
        # ONE REST (the pooled adversarial round 4's M2): with no older
        # USABLE pair in the window (the round 5 review's m2: an older pair
        # with no run mean adds nothing), pooling has nothing to add, and
        # two keep routes would split the keep alpha over the same test. The
        # cell is classified exactly as a `current` cell (`rest_guard` stays
        # null, every keep is final).
        rest = None
    ds = differences(usable)
    if not ds:
        return done("insufficient", "no run with objective checks on an arm")
    # Pooled, the keep is two tests, the pooled one and one over the current
    # rest alone, each at half the cell's keep alpha (Bonferroni), so the
    # cell still keeps at its share of `benefit_confidence`.
    route_alpha = keep_alpha if rest is None else keep_alpha / 2
    objective = sequence_block(ds, margin, route_alpha, remove_alpha, bet_prior)
    out["objective"] = objective
    out["keep_tests"] = [{"route": "objective", "p": objective["keep_p"],
                          "log_wealth": objective["keep_log_wealth"]}]
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
    # Where each current-rest usable pair falls among the usable pairs
    # (1-based): the ceiling and no-harm tests count current-rest pairs.
    current_places = [i + 1 for i, c in enumerate(usable_current) if c]

    def place(n):
        """Usable pair of the n-th (1-based) current-rest usable pair."""
        return current_places[n - 1]

    def count_reached(need):
        """The usable pair (1-based) by which the current rest's window
        holds `need` pairs: where a cap or the high-cell stop is reached."""
        seen = used = 0
        for (w, o), c in zip(window, is_current):
            used += w["numbers"]["run_mean"] is not None and o["numbers"]["run_mean"] is not None
            seen += c
            if seen >= need:
                return used
        return len(usable)

    withouts = [o["numbers"]["run_mean"] for _, o in current_usable]
    current_ds = differences(current_usable)
    without_mean = _mean(withouts) if withouts else None
    floor = 1 - margin
    ceiling_at = first_crossing(ceiling_wealth(withouts, floor), remove_alpha) \
        if floor > 0 and withouts else None
    high = without_mean is not None and without_mean > floor

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

    def per_pair(current_wealth):
        """A log wealth over the current rest's pairs alone, read at every
        usable pair (it stands still across an older rest's pairs)."""
        spread, seen = [], 0
        for c in usable_current:
            seen += c
            spread.append(current_wealth[seen - 1] if seen else 0.0)
        return spread

    def mean_of(a, b):
        """The log of the mean of two wealths given as logs."""
        top = max(a, b)
        return top + math.log1p(math.exp(min(a, b) - top)) - math.log(2)

    def decided_at(wealth, evidence=None):
        """The STOPPING TIME of a removal-side test (round 2's C1): the first
        pair n at which its running wealth is at 1/remove_alpha AND the
        pairs so far span `min_cli_versions`. The event {decided_at is not
        None} lies inside {the wealth ever reaches 1/alpha}, which Ville's
        inequality bounds by alpha under H0, so the level holds. The wealth
        must be at the threshold at n itself: a pair that knocks it under
        (a late D = +1 on a new version) does not decide.

        Pooled (`rest`), the test decides on THE CURRENT-REST GUARD instead:
        at n, at least `min_pairs` of pairs 1..n are beside the current
        rest, those span `min_cli_versions`, and the current rest's
        `evidence` (the mean of the test's current share and the current
        rest's own test, `remove_evidence` or `harm_evidence`) is at
        1/remove_alpha. That evidence is a test martingale for H0 on the
        current rest alone, whatever the older rests showed, so a removal
        keeps its level against TODAY's rest; the pooled wealth's own level
        is not required (rounds 3's m5 and 4's M3: it added nothing to the
        level, and older gains could hold it down for good)."""
        need = policy["min_cli_versions"]
        if rest is None:
            return next((i + 1 for i, w in enumerate(wealth)
                         if w >= threshold and len(versions(i + 1)) >= need), None)
        seen = 0
        for i in range(len(wealth)):
            seen += usable_current[i]
            if evidence[i] >= threshold and seen >= rest["min_pairs"] \
                    and len(versions(i + 1, current_only=True)) >= need:
                return i + 1
        return None

    def awaiting(crossed, what):
        """A test that crossed but has not decided: more pairs on a second
        CLI version (pooled: more pairs beside the current rest) can still
        decide it, up to the cap."""
        if rest is not None:
            found = versions(len(usable), current_only=True)
            crossing = ("the current rest's removal evidence reached its level"
                        if what == "no benefit" else
                        "the current rest's harm evidence reached its level")
            return done("insufficient", f"{what} on the numbers (at pair {crossed} "
                        f"{crossing}), but the current-rest guard has not held at one pair: it "
                        f"needs at least {rest['min_pairs']} pairs beside the current rest "
                        f"({len(current_usable)} so far) spanning "
                        f"{policy['min_cli_versions']} CLI versions ({len(found)} so far), "
                        "with it still at its level")
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
                    "effect, which can only propose a removal", count_reached(cap))

    keep_at, remove_at = objective["keep_at"], objective["remove_at"]
    harm_pooled = harm_wealth(ds, bet_prior)
    remove_pooled = remove_wealth(ds, margin, bet_prior)
    harm_at = first_crossing(harm_pooled, remove_alpha)
    if rest is None:
        harm_decided = decided_at(harm_pooled)
        remove_decided = decided_at(remove_pooled)
    else:
        # THE CURRENT-REST EVIDENCE for a removal: the mean of two test
        # martingales for H0 "helps by the margin beside today's rest", the
        # current rest's share of the pooled remove test and the current
        # rest's own remove test (its own bets, as under `current`). A mean
        # of two is one, so the guard keeps its level; the own test lets a
        # section that stopped helping be removed even when gains beside an
        # older rest starved the pooled bets (the pooled adversarial round 2).
        # The removal decides on this evidence, the pair floor and the CLI
        # versions alone (round 3's m5): the pooled wealth added nothing to
        # the level, and one rule now serves a removal with or without a
        # pooled keep before it.
        remove_evidence = [mean_of(a, b) for a, b in zip(
            current_share(remove_pooled),
            per_pair(remove_wealth(current_ds, margin, bet_prior)))]
        remove_decided = decided_at(remove_pooled, remove_evidence)
        # The harm test likewise (round 4's M3): older gains held the pooled
        # harm test's bets near zero, so a section harming today was never
        # removed. Its evidence is the mean of its current share and the
        # current rest's own harm test, and it decides on that evidence with
        # the pair floor and the CLI versions.
        harm_evidence = [mean_of(a, b) for a, b in zip(
            current_share(harm_pooled), per_pair(harm_wealth(current_ds, bet_prior)))]
        harm_decided = decided_at(harm_pooled, harm_evidence)
    # Round 2's M1: no harm beyond the margin (H0: E[D] <= -margin), at the
    # remove level. A ceiling cell parks only when this rejects too; pooled,
    # it reads the current rest, as the ceiling test does.
    noharm_at = first_crossing(keep_wealth(current_ds, bet_prior, -margin), remove_alpha) \
        if current_ds else None
    if rest is not None:
        remove_share, harm_share = current_share(remove_pooled), current_share(harm_pooled)
        # Where each current-rest pair falls among the usable pairs (1-based).
        places = [i + 1 for i, c in enumerate(usable_current) if c]

        # Each test's crossing reads the same current-rest evidence as its
        # stopping time, or a crossing could wait for a decision that cannot
        # come; one older rests made alone is never a crossing (the pooled
        # adversarial round 1's blocker).
        remove_at = first_crossing(remove_evidence, remove_alpha)
        harm_at = first_crossing(harm_evidence, remove_alpha)
        # THE KEEP, pooled (round 1's blocker and Adam's 2026-11-07 rule): the
        # pooled keep counts only from the pair at which the current rest has
        # `min_pairs` pairs, so an older rest alone never keeps; a keep test
        # over the current rest alone (its first pair's bet neutral or the
        # learned prior's, like a `current` cell) lets a cell that helps today
        # keep at its cap. Each runs at half the keep alpha; the earlier wins.
        pooled_keep = objective["keep_at"]
        floor_at = places[rest["min_pairs"] - 1] if len(places) >= rest["min_pairs"] else None
        pooled_keep = max(pooled_keep, floor_at) \
            if pooled_keep is not None and floor_at is not None else None
        current_keep_wealth = keep_wealth(current_ds, bet_prior)
        current_keep = first_crossing(current_keep_wealth, route_alpha)
        current_keep = places[current_keep - 1] if current_keep is not None else None
        keep_at = min([k for k in (pooled_keep, current_keep) if k is not None],
                      default=None)
        # Each route's p is doubled (Bonferroni), so `1 - m x min p` still
        # reads the cell's keep level; the pooled one counts only from the
        # current-rest pair floor.
        # Each route's `log_wealth` is its current log wealth on its p's
        # scale (less log 2 for the doubled p), None where its p is pinned
        # to 1 as no keep evidence; reporting only.
        out["keep_tests"] = [
            {"route": "objective", "p": min(1.0, 2 * objective["keep_p"])
             if floor_at is not None else 1.0,
             "log_wealth": objective["keep_log_wealth"] - math.log(2)
             if floor_at is not None else None},
            {"route": "objective-current-rest",
             "p": min(1.0, 2 * ville_p(current_keep_wealth)),
             "log_wealth": last_wealth(current_keep_wealth) - math.log(2)}]
        out["rest_guard"] = {
            "min_pairs": rest["min_pairs"], "usable_current_rest_pairs": len(current_usable),
            "met_pairs": len(current_usable) >= rest["min_pairs"],
            # The levels the current rest's shares reached (Ville's 1 - 1/W).
            "no_help_confidence": reached(remove_share),
            "harm_confidence": reached(harm_share),
            "remove_share_at": first_crossing(remove_share, remove_alpha),
            "harm_share_at": first_crossing(harm_share, remove_alpha),
            "pooled_remove_at": objective["remove_at"],
            "pooled_harm_at": first_crossing(harm_pooled, remove_alpha),
            "pooled_keep_at": objective["keep_at"], "current_keep_at": current_keep,
            # The current rest's own figures (the round 4 review's minor 3:
            # scripts/explorer_data.py charts these, not the pooled block),
            # its keep bound at the current route's alpha; None with no
            # usable current-rest pair. Its pairs count the current rest's.
            "current_objective": sequence_block(current_ds, margin, route_alpha,
                                                remove_alpha, bet_prior)
            if current_ds else None,
            # The round 2 fields: the current rest's own remove test's and the
            # removal evidence's (the mean of the two) first crossings.
            "current_remove_at": first_crossing(
                per_pair(remove_wealth(current_ds, margin, bet_prior)), remove_alpha),
            "remove_evidence_at": remove_at,
            # The level the removal evidence reached (Ville's 1 - 1/W), what
            # the planner's retire progress and the explorer read.
            "remove_evidence_confidence": reached(remove_evidence),
            # Its current (last) log wealth, reporting only (`last_wealth`).
            "remove_evidence_log_wealth": last_wealth(remove_evidence),
            # Round 4's M3: the harm evidence's crossing and level.
            "harm_evidence_at": harm_at,
            "harm_evidence_confidence": reached(harm_evidence)}
    out.update(headroom=ceiling_at is None, without_mean=without_mean,
               ceiling_at=ceiling_at, harm_at=harm_at, harm_decided_at=harm_decided,
               remove_decided_at=remove_decided, noharm_at=noharm_at)
    capped = held_current >= cap
    # Round 3's M3: the keep is compared with the removal's STOPPING TIME,
    # not its first crossing. A remove crossing that never decided (one CLI
    # version) must not outrank a keep reached later; the keep's own
    # crossing bounds its error either way.
    if rest is not None:
        # THE STALE KEEP (the pooled adversarial rounds 2 to 4): a keep the
        # pooled test made is NOT final. If the remove test decides on the
        # current rest's evidence (with the pair floor and the CLI versions),
        # no-benefit wins over it, since that decision holds its level
        # against today's rest whatever came before. (The harm test's null,
        # E[D] >= 0, is harder to reject than the remove test's, so a harm
        # decision comes no sooner in practice; round 4's mutation check
        # found reading it here changed nothing.) A keep the current-rest test made alone stays final,
        # ordered against the removal's stopping time as a `current` cell's
        # keep is.
        final = current_keep is not None and (remove_decided is None
                                             or current_keep <= remove_decided)
        standing = [current_keep] if final else []
        removed = remove_decided is not None
        # Round 3's M1: a provisional keep does not stand at the current
        # rest's cap either. No more pairs can test it there, so the cell
        # ends on the current rest's own rules, as a `current` cell would:
        # an older rest alone never keeps.
        lapsed = pooled_keep is not None and not removed and capped
        if pooled_keep is not None and not removed and not capped:
            standing.append(pooled_keep)
        elif pooled_keep is not None:
            # Round 4's m(a): a pooled keep that a removal overrode or that
            # lapsed is no keep evidence, so its route reports p = 1.
            out["keep_tests"][0].update(p=1.0, log_wealth=None)
        keep_at = min(standing, default=None)
        out["rest_guard"]["keep_final"] = final
        keeps = keep_at is not None
        provisional = "" if final else (
            " (a pooled keep, not final: a removal on the current rest's evidence "
            "overrides it, and it lapses at the current rest's cap, unless the current "
            "rest's own keep test rejects first)")
        if lapsed:
            # Round 4's m(d): every class a lapsed cell ends in says so.
            plain_done = done

            def done(cls, reason, at=None):
                return plain_done(cls, f"{reason}; the pooled keep at pair {pooled_keep} "
                                  "lapsed at the current rest's cap, which no more pairs "
                                  "can test (an older rest alone never keeps)", at)
    else:
        keeps = keep_at is not None and (remove_decided is None or keep_at <= remove_decided)
        provisional = ""
    if keeps:
        return done("benefit", f"the keep test rejected at pair {keep_at}: confident at "
                    f"{policy['benefit_confidence']:.0%} across the subject's {family} "
                    f"cell(s) that the gain is above 0{provisional}", keep_at)
    if (ceiling_at is not None or high) and harm_at is not None:
        # Round 1's M1: a cell at the ceiling can still show HARM, which
        # needs no headroom, so it is never hidden as `ceiling`.
        if harm_decided is None:
            return awaiting(harm_at, "harm")
        return done(
            "no-benefit", f"the harm test decided at pair {harm_decided} (crossed at "
            f"{harm_at}): confident at {policy['retire_confidence']:.0%} that the "
            "subject lowers results here, which needs no headroom to show", harm_decided)
    if ceiling_at is not None and noharm_at is not None:
        return done("ceiling", f"the ceiling test rejected at pair {ceiling_at} and the "
                    f"no-harm test at pair {noharm_at}: confident at "
                    f"{policy['retire_confidence']:.0%} that the without arm's mean is "
                    f"above 1 - {margin} and the subject costs less than {margin} here, "
                    "so this task leaves no room to show the margin; the cell does not "
                    "vote on removal and needs a harder fixture",
                    max(place(ceiling_at), place(noharm_at)))
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
                        "being fired, does not vote on removal and needs a harder fixture",
                        max(count_reached(policy["max_runs_high_cell"]), place(noharm_at)))
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
        over = "" if rest is None or pooled_keep is None else (
            f", beside today's rest whatever older rests showed; the pooled keep test's "
            f"crossing at pair {pooled_keep} does not stand against it (a pooled keep is "
            "not final)")
        return done(
            "no-benefit", f"the remove test decided at pair {remove_decided} (crossed at "
            f"{remove_at}): confident at {policy['retire_confidence']:.0%} that the gain "
            f"is under {margin}{over}", remove_decided)
    if capped:
        return capped_class()
    return done("insufficient", "neither test has rejected yet")


def run_key(run: dict) -> str:
    """A run's name in `runs_used`:
    `<path>#<fixture>#<role>`, since one `<timestamp>` holds every fixture."""
    return f"{run['path']}#{run['fixture'] or ''}#{run['role']}"


def _cell_pairs(with_runs: list, without_runs: list, rest: dict | None) -> tuple:
    """(skipped, pairs, unpaired, rest_info) of one primed cell: the count of
    runs not counted by their skip reason, the cell's pairs in order, every
    counted run left without a partner, and `_classify`'s `rest` (None, or
    `rest` with each pair's `pair_key`). `classify_cell` and `cell_discards`
    both read it, so the runs a cell decides on and the runs it reports
    discarded come from one place."""
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
    return skipped, pairs, unpaired, rest_info


# ---------------------------------------------------------------------------
# Discarded runs (Adam, 2026-11-07).
#
# Every recorded arm run of a subject either counts toward its current
# verdict or is DISCARDED for one reason, a stable slug the explorer and the
# dashboard key on. A run counts when it sits in a pair inside its cell's
# window (`_classify`: the first `max_runs_per_cell` pairs, per rest when
# pooled) with a run mean on both arms, in a cell the verdict reads (not
# `cannot-discriminate`). The first reason that applies, in this order, is
# the run's:
#
#   Read by scripts/compute_gates.py `build_index`, before any cell:
#     invalid_run          the arm run does not validate (`skipped` names how)
#     after_as_of          stamped after the evaluation's --as-of
#     duplicate            a copy of an arm run already read (DUPLICATES)
#     bare_run             a bare isolation without arm (BARE RUNS), reported
#                          apart and never pooled
#     verdict_raised       the subject's verdict raised, so none of its runs
#                          was read
#   Pooling (`pool_cells`, `pool_discard`):
#     fixture_off_main     its fixture is not one of the subject's fixtures on
#                          main (removed, renamed, draft or unscheduled)
#     model_off_roster     its arm model is not on the current roster
#     content_unknown      main's content key is unknown (no registry or
#                          guidance checkout copy, no rest digest): the cell
#                          is `insufficient` on an incomplete key
#     fixture_changed      its fixture digest is not the fixture's on main
#     subject_changed      a with arm whose tested digest is not the skill's
#                          (or the section extent's) on main
#     context_unknown      it records no arm context or pair key
#     hooked_run           in-situ guidance: it ran with a fleet hook set,
#                          which main's key does not have
#     rest_changed         in-situ guidance under `rest_policy: current`: it
#                          ran beside an older rest of the guidance
#     context_unmatched    its arm context or pair key is not the one the
#                          cell chose jointly (`_joint_context`)
#   Inside a cell (`cell_discards`):
#     no_check_results     a scored trial without check results on a fixture
#                          that has checks (NO_CHECKS_REASON)
#     no_scored_trials     fewer than MIN_TRIALS_PER_RUN scored or
#                          agent-errored trials (every trial an
#                          infrastructure error; FEW_TRIALS_REASON)
#     unpaired             no counted partner arm of its fire (within one rest
#                          when pooled)
#     over_cap             its pair falls after the cell's window
#                          (`max_runs_per_cell` pairs, per rest when pooled)
#     no_objective_score   its pair lacks a run mean on an arm (judge-only)
#     cannot_discriminate  its cell is `cannot-discriminate`, which the
#                          verdict leaves out
#
# Not a discard: an agent-errored or infrastructure-errored TRIAL inside a
# counted run, a judge figure the verdict does not read, `min_cli_versions`
# (it delays a decision, it drops no run), a parked or scope-paused cell (it
# still counts), and the one-retirement-per-evaluation rule.
#
# A run's cost is the sum of its trials' `agent.cost_usd` (what each cell's
# `cost_usd` sums); a run with any trial lacking one adds to `cost_unknown`,
# and its known trials still add to `cost_usd`, which is then a floor.

DISCARD_REASONS = (
    "invalid_run", "after_as_of", "duplicate", "bare_run", "verdict_raised",
    "fixture_off_main", "model_off_roster", "content_unknown", "fixture_changed",
    "subject_changed", "context_unknown", "hooked_run", "rest_changed",
    "context_unmatched", "no_check_results", "no_scored_trials", "unpaired",
    "over_cap", "no_objective_score", "cannot_discriminate")
#: The run skip reasons of `run_numbers`, by slug.
SKIP_REASON_SLUGS = {NO_CHECKS_REASON: "no_check_results",
                     FEW_TRIALS_REASON: "no_scored_trials"}


def run_cost(trials: list) -> tuple:
    """(dollars, cost unknown) of one arm run from its trial records (or
    any mappings with `cost_usd`): the sum of the known costs, and whether
    any trial, or the sum, is not a finite number from 0 up."""
    costs = [t.get("cost_usd") for t in trials if isinstance(t, dict)]
    known = [c for c in costs if _is_number(c) and c >= 0]
    total = _finite_sum(known)
    if total is None:
        return 0.0, True
    return total, not trials or len(known) < len(trials)


def discard_entry(run: dict, reason: str) -> tuple:
    """(reason, dollars, cost unknown) for one discarded validated run."""
    if reason not in DISCARD_REASONS:
        raise ValueError(f"unknown discard reason {reason!r}")
    return (reason, *run_cost(run.get("trials") or []))


def discard_summary(entries) -> dict:
    """{"total", "cost_usd", "cost_unknown", "by_reason": {slug: {"runs",
    "cost_usd", "cost_unknown"}}} of (reason, dollars, unknown) entries, at
    full precision (`math.fsum`; None only if the sum overflows)."""
    entries = list(entries)

    def block(rows):
        return {"cost_usd": _finite_sum([d for _, d, _ in rows]),
                "cost_unknown": sum(1 for *_, u in rows if u)}
    by_reason = {}
    for slug in sorted({e[0] for e in entries}):
        rows = [e for e in entries if e[0] == slug]
        by_reason[slug] = {"runs": len(rows), **block(rows)}
    return {"total": len(entries), **block(entries), "by_reason": by_reason}


def merge_discards(*summaries) -> dict:
    """One `discard_summary` of several (None skipped): counts add, dollars
    add by `math.fsum`."""
    rows: dict = {}
    for summary in summaries:
        for slug, row in ((summary or {}).get("by_reason") or {}).items():
            rows.setdefault(slug, []).append(row)
    by_reason = {slug: {"runs": sum(r["runs"] for r in got),
                        "cost_usd": _finite_sum([r["cost_usd"] for r in got]),
                        "cost_unknown": sum(r["cost_unknown"] for r in got)}
                 for slug, got in sorted(rows.items())}
    return {"total": sum(r["runs"] for r in by_reason.values()),
            "cost_usd": _finite_sum([r["cost_usd"] for r in by_reason.values()]),
            "cost_unknown": sum(r["cost_unknown"] for r in by_reason.values()),
            "by_reason": by_reason}


def _cell_split(with_runs: list, without_runs: list, policy: dict, cls: str,
                rest: dict | None) -> tuple:
    """(discards, usable) of one classified cell: (run, reason) for every
    run that does not count (DISCARDED RUNS, "Inside a cell"), and the
    window's pairs with a run mean on both arms, in `_classify`'s order
    (empty for a `cannot-discriminate` cell), whose 1-based places are the
    ones `decided_at` names."""
    prime(with_runs + without_runs)
    _skipped, pairs, unpaired, rest_info = _cell_pairs(with_runs, without_runs, rest)
    cap = policy["max_runs_per_cell"]
    if rest_info is None:
        window = pairs[:cap]
    else:
        window, _ = _rest_window(pairs, rest_info["keys"], rest_info["current"], cap)
    in_window = {id(r) for pair in window for r in pair}
    usable = [(w, o) for w, o in window
              if w["numbers"]["run_mean"] is not None and o["numbers"]["run_mean"] is not None]
    scored = {id(r) for pair in usable for r in pair}
    lone = {id(r) for r in unpaired}
    out = []
    for run in sorted(with_runs + without_runs, key=_order):
        reason = run["numbers"]["skip_reason"]
        if reason is not None:
            out.append((run, SKIP_REASON_SLUGS.get(reason, "no_scored_trials")))
        elif id(run) in lone:
            out.append((run, "unpaired"))
        elif id(run) not in in_window:
            out.append((run, "over_cap"))
        elif id(run) not in scored:
            out.append((run, "no_objective_score"))
        elif cls == "cannot-discriminate":
            out.append((run, "cannot_discriminate"))
    return out, ([] if cls == "cannot-discriminate" else usable)


def cell_discards(with_runs: list, without_runs: list, policy: dict, cls: str,
                  rest: dict | None = None) -> list:
    """(run, reason) for every run of one classified cell that does not
    count toward the verdict (DISCARDED RUNS, "Inside a cell"), read from
    `_cell_pairs` and `_classify`'s own window. `cls` is the cell's class;
    `rest` is `classify_cell`'s."""
    return _cell_split(with_runs, without_runs, policy, cls, rest)[0]


# ---------------------------------------------------------------------------
# Run utility (Adam, 2026-11-07: "what runs provided no utility vs helped
# determine the disposition of the target for some period of time").
#
# Every arm run of a subject read by scripts/compute_gates.py gets ONE class
# (UTILITY_CLASSES), and, when its current verdict does not count it, the
# DISCARDED RUNS reason slug, so the ledger's reasons always add up to
# `discarded_runs`:
#
#   decisive             counted in a current cell that has DECIDED (any
#                        class but insufficient, missing and
#                        cannot-discriminate), in a pair at or before the
#                        cell's decision point `decided_at`.
#   after_decision       counted (or, superseded, would have been) in a pair
#                        after its cell's decision point: no utility.
#   building             counted in a current cell that has not decided.
#   decisive_superseded  not counted today because the content or roster
#                        changed (STRANDING_REASONS), but its OLD cell
#                        version decided, and its pair is at or before that
#                        decision point: it decided a past disposition.
#   stranded             not counted today for a STRANDING_REASONS change,
#                        usable in its old cell version, which never decided.
#   discarded            never usable: every other reason, and a superseded
#                        run that its old cell version did not count either.
#
# THE DECISION POINT (`_classify`'s `decided_at`, 1-based over the cell's
# usable pairs, those in the window with a run mean on both arms): for
# `benefit` the keep test's crossing that stands (`keep_at`), but for a
# pooled keep the pair at which it became final (the current rest's own
# keep, `rest_guard.current_keep_at`, when later): a provisional pooled keep
# (`keep_final` false) has none yet, so its runs are `building`; for `no-benefit`
# the remove or harm test's stopping time (`remove_decided_at`,
# `harm_decided_at`); for `ceiling` the later of the ceiling and no-harm
# crossings; for `ceiling-unconfirmed` the later of the no-harm crossing and
# the pair at which the current rest's window reached `max_runs_high_cell`
# (the without-arm mean it also reads is over every pair, not a stopping
# time, so that rule is the most defensible point); for `no-clear-effect`
# the pair at which the current rest's window reached the cap. An
# insufficient cell has none (its runs are `building`), including one at its
# cap, and so has a cell whose decided class the agent-errored rule turned
# back to insufficient. A cell parked by the eval scope pass keeps its
# decision point, except a provisional pooled keep, which is undecided.
#
# CELL VERSIONS. A decision belongs to a cell VERSION: the cell (pooled
# fixture, model) and the content it tested (fixture digest, the with arm's
# tested digest, and the pair key: the other skills and the guidance, or the
# rest of the guidance). A run dropped today as `fixture_off_main`,
# `model_off_roster`, `fixture_changed`, `subject_changed`, `rest_changed` or
# `context_unmatched` was valid when it ran and was invalidated by a later
# change, so it is regrouped with the other such runs of its version (and
# the without partners those leave `unpaired` in a current cell) and that
# group is classified alone by `classify_cell`, with the subject's keep
# family and prior. A without arm records no tested digest, so it takes
# its with partner's (same run directory, fixture and model); one with no
# such partner is grouped with a None digest and stays unpaired there, so
# it is `discarded`. An old version is classified with `rest` None, as
# `rest_policy: current` would (one rest per version, which can only make
# fewer old decisions, so more runs read `stranded`, never fewer).
#
# Each subject also lists `decisions`: per cell version, its first and last
# run day, its class, and the day of the pair at its decision point.

UTILITY_CLASSES = ("decisive", "decisive_superseded", "after_decision", "building",
                   "stranded", "discarded")
#: The DISCARDED RUNS reasons that mean "valid when it ran, invalidated by a
#: later change": a run dropped for one is regrouped by its old cell version.
STRANDING_REASONS = frozenset({"fixture_off_main", "model_off_roster", "fixture_changed",
                               "subject_changed", "rest_changed", "context_unmatched"})
#: Classes that say a cell has not decided.
UNDECIDED_CLASSES = frozenset({"missing", "insufficient", "cannot-discriminate"})


def run_day(timestamp) -> str | None:
    """The UTC day, YYYY-MM-DD, of a results timestamp (YYYYMMDDTHHMMSSZ)."""
    if isinstance(timestamp, str) and len(timestamp) >= 8 and timestamp[:8].isdigit():
        return f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    return None


def utility_entry(run: dict, cls: str, reason: str | None = None, cost=None) -> tuple:
    """(day, model, class, reason, dollars, cost unknown) of one arm run.
    `cost` is (dollars, unknown) when the run has no trial records."""
    if cls not in UTILITY_CLASSES:
        raise ValueError(f"unknown utility class {cls!r}")
    if reason is not None and reason not in DISCARD_REASONS:
        raise ValueError(f"unknown discard reason {reason!r}")
    dollars, unknown = cost if cost is not None else run_cost(run.get("trials") or [])
    model = run.get("model")
    return (run_day(run.get("timestamp")), model if isinstance(model, str) else None,
            cls, reason, dollars, unknown)


def utility_rows(entries) -> list:
    """The ledger: `utility_entry` entries summed per (day, model, class,
    reason) as {"date", "model", "class", "reason", "runs", "cost_usd",
    "cost_unknown"}, dollars by `math.fsum` at full precision."""
    groups: dict = {}
    for day, model, cls, reason, dollars, unknown in entries:
        groups.setdefault((day, model, cls, reason), []).append((dollars, unknown))
    return [{"date": day, "model": model, "class": cls, "reason": reason,
             "runs": len(got), "cost_usd": _finite_sum([d for d, _ in got]),
             "cost_unknown": sum(1 for _, u in got if u)}
            for (day, model, cls, reason), got in sorted(
                groups.items(), key=lambda kv: tuple(x or "" for x in kv[0]))]


def merge_utility(*ledgers) -> list:
    """One ledger of several (None skipped): rows of one key add."""
    groups: dict = {}
    for ledger in ledgers:
        for row in ledger or []:
            key = (row["date"], row["model"], row["class"], row["reason"])
            groups.setdefault(key, []).append(row)
    return [{"date": k[0], "model": k[1], "class": k[2], "reason": k[3],
             "runs": sum(r["runs"] for r in got),
             "cost_usd": _finite_sum([r["cost_usd"] for r in got]),
             "cost_unknown": sum(r["cost_unknown"] for r in got)}
            for k, got in sorted(groups.items(), key=lambda kv: tuple(x or "" for x in kv[0]))]


def cell_utility(with_runs: list, without_runs: list, policy: dict, cell: dict,
                 rest: dict | None = None) -> tuple:
    """((run, class, reason) for every run of one classified current cell,
    the day of its decision point or None): RUN UTILITY's classes."""
    discards, usable = _cell_split(with_runs, without_runs, policy, cell["class"], rest)
    at = None if cell["class"] in UNDECIDED_CLASSES else cell.get("decided_at")
    guard = cell.get("rest_guard")
    if cell["class"] == "benefit" and isinstance(guard, dict) and at is not None:
        # A pooled keep is not final until the current rest's own keep test
        # rejects (THE STALE KEEP): until then its runs are building, and
        # its decision point is where it became final, not the earlier
        # pooled crossing. Reporting only: the class is the gate's.
        final_at = guard.get("current_keep_at")
        if guard.get("keep_final") is False:
            at = None
        elif isinstance(final_at, int) and not isinstance(final_at, bool) and final_at > at:
            at = final_at
    out = [(r, "discarded", why) for r, why in discards]
    for i, pair in enumerate(usable, 1):
        cls = "building" if at is None else "decisive" if i <= at else "after_decision"
        out += [(r, cls, None) for r in pair]
    day = run_day(usable[at - 1][0]["timestamp"]) if at and at <= len(usable) else None
    return out, day


def _version(entries: list) -> dict:
    """A decisions row's dates: the first and last run day of `entries`."""
    days = sorted(run_day(r["timestamp"]) or "" for r in entries)
    return {"from": days[0] or None, "to": days[-1] or None}


def supersede(ledger: list, skill: str, expected: dict, policy: dict, family: int,
              bet_prior, errored_blocks: bool) -> list:
    """RUN UTILITY, CELL VERSIONS, in place on `ledger` ([run, class,
    reason] lists): every run dropped for a STRANDING_REASONS change, and
    the without partners those leave unpaired, regrouped by old cell version
    and classified alone. Returns (the old versions' `decisions` rows, the
    ids of the runs moved to an old version)."""
    def partner_key(run):
        return (run["path"], run["fixture"] or "", run["model"])
    dropped = [row for row in ledger if row[2] in STRANDING_REASONS]
    if not dropped:
        return [], set()
    lone = {(partner_key(row[0]), row[0]["role"]): row for row in ledger
            if row[2] == "unpaired"}
    with_digest = {partner_key(row[0]): row[0].get("tested_digest")
                   for row in dropped if row[0]["role"] == "with"}
    groups: dict = {}
    for row in dropped:
        run = row[0]
        key = (pooled_fixture(run, skill, expected) or "", run["model"], run["fixture_digest"],
               with_digest.get(partner_key(run)), run.get("pair_key"))
        members = groups.setdefault(key, {})
        members[id(run)] = row
        other = lone.get((partner_key(run), "without" if run["role"] == "with" else "with"))
        if other is not None:
            members[id(other[0])] = other
    decisions, moved = [], set()
    for key, members in sorted(groups.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        rows = list(members.values())
        moved.update(members)
        with_runs = [r[0] for r in rows if r[0]["role"] == "with"]
        without_runs = [r[0] for r in rows if r[0]["role"] == "without"]
        cell = classify_cell(with_runs, without_runs, policy,
                             any(r.get("judge_carried") for r, *_ in rows), family,
                             bet_prior, errored_blocks=errored_blocks)
        result, day = cell_utility(with_runs, without_runs, policy, cell)
        old = {"decisive": "decisive_superseded", "building": "stranded"}
        by_id = {id(r): cls for r, cls, _ in result}
        for row in rows:
            row[1] = old.get(by_id[id(row[0])], by_id[id(row[0])])
        decisions.append({"fixture": key[0] or None, "model": key[1], "current": False,
                          **_version([r[0] for r in rows]), "class": cell["class"],
                          "decided": day if cell["class"] not in UNDECIDED_CLASSES else None})
    return decisions, moved


def pool_discard(run: dict, skill: str, models: list, expected: dict, strata: bool,
                 rest_policy: str) -> str:
    """Why `pool_cells` left `run` (a run of `skill`) out of every cell:
    the first DISCARDED RUNS pooling reason that applies."""
    fixture = pooled_fixture(run, skill, expected)
    if fixture not in expected:
        return "fixture_off_main"
    if run["model"] not in models:
        return "model_off_roster"
    main = expected[fixture]
    tested, fdig = main.get("tested_digest"), main.get("fixture_digest")
    if fdig is None or tested is None or (strata and main.get("rest_digest") is None):
        return "content_unknown"
    if run["fixture_digest"] != fdig:
        return "fixture_changed"
    if run["role"] == "with" and run["tested_digest"] != tested:
        return "subject_changed"
    if not run.get("pair_key") or (not strata and not run.get("arm_context_digest")):
        return "context_unknown"
    if strata:
        if run.get("fleet_hooks_digest") is not None:
            return "hooked_run"
        if rest_policy == "current" and run["pair_key"] != main["rest_digest"]:
            return "rest_changed"
    return "context_unmatched"


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
    skipped, pairs, unpaired, rest_info = _cell_pairs(with_runs, without_runs, rest)
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
        full = {**full, "decided_at": None}
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
    cells, used, ledger, pooled_ids, decisions = [], set(), [], set(), []
    all_runs = index.get("runs", [])
    for (fixture, model), pool in sorted(pool_cells(all_runs, skill,
                                                    models, expected, strata,
                                                    rest_policy).items()):
        arms = {"with": pool["with"], "without": pool["without"]}
        runs = arms["with"] + arms["without"]
        prime(runs)
        used.update(run_key(r) for r in runs)
        pooled_ids.update(id(r) for r in runs)
        missing = sorted(k for k, v in pool["key"].items() if v is None)
        decision = None
        if not pool["on_model"]:
            cell = {"class": "missing", "reason": "no run on this model"}
        elif missing:
            cell = {"class": "insufficient",
                    "reason": f"pooling key incomplete: {', '.join(missing)}"}
            ledger += [[r, "discarded", "content_unknown"] for r in runs]
        else:
            carried = any(r["judge_carried"] for r in runs)
            guard = {"current": pool["key"]["rest_digest"],
                     "min_pairs": policy.get("rest_guard_min_pairs",
                                             DEFAULT_REST_GUARD_MIN_PAIRS)} if pooled else None
            cell = classify_cell(arms["with"], arms["without"], policy, carried, m,
                                 bet_prior, errored_blocks=not strata, rest=guard)
            cell_rows, decided_day = cell_utility(arms["with"], arms["without"], policy,
                                                  cell, guard)
            ledger += [list(row) for row in cell_rows]
            if runs:
                decision = {"fixture": fixture or None, "model": model, "current": True,
                            **_version(runs), "class": cell["class"], "decided": decided_day,
                            "_runs": runs}
                decisions.append(decision)
        paused = (expected.get(fixture) or {}).get("scope_paused")
        provisional = cell["class"] == "benefit" and \
            (cell.get("rest_guard") or {}).get("keep_final") is False
        if paused and (cell["class"] not in PAUSE_KEEPS_CLASS or provisional):
            # Round 3's C1: the eval scope pass stopped firing this fixture.
            # Dropping its cells let the others remove a subject it helped,
            # so they stay, parked: a keep they earned before the pause
            # still keeps, a decided `no-benefit` still votes (round 4's
            # M1: the pause reads only the pooled without arm, so parking
            # it hid a decided harm of any size), and anything else neither
            # votes nor frees an automatic removal. A provisional pooled keep
            # (`keep_final` False) is undecided too (the round 4 review): a
            # paused fixture gets no current-rest runs to confirm it.
            if provisional:
                # The round 5 review's m1: a parked provisional keep is no
                # keep evidence, so its pooled route reports p = 1, as an
                # overridden or lapsed one does.
                cell = {**cell, "keep_tests": [
                    {**t, "p": 1.0, "log_wealth": None}
                    if t.get("route") == "objective" else t
                    for t in cell["keep_tests"]]}
            if provisional:
                # RUN UTILITY: a parked provisional keep has not decided.
                ids = {id(r) for r in runs}
                for row in ledger:
                    if row[1] in ("decisive", "after_decision") and id(row[0]) in ids:
                        row[1] = "building"
                if decision:
                    decision["decided"] = None
            if decision:
                decision["class"] = "paused"
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
    ledger += [[r, "discarded", pool_discard(r, skill, models, expected, strata, rest_policy)]
               for r in sorted(all_runs, key=_order)
               if r["skill"] == skill and id(r) not in pooled_ids]
    # RUN UTILITY, CELL VERSIONS: runs a later change dropped, by old version.
    old, moved = supersede(ledger, skill, expected, policy, m, bet_prior,
                           errored_blocks=not strata)
    for decision in decisions:
        # A current version's days are its own runs', not those of an old
        # version that a change left unpaired in its pool.
        own = [r for r in decision.pop("_runs") if id(r) not in moved]
        if own:
            decision.update(_version(own))
    decisions += old
    # DISCARDED RUNS: every run of the subject given that does not count;
    # RUN UTILITY: every run of it, by class, from the same ledger.
    out = {"cells": cells, "runs_used": sorted(used),
           "discarded_runs": discard_summary(discard_entry(r, why)
                                             for r, _, why in ledger if why),
           "run_utility": utility_rows(utility_entry(r, cls, why) for r, cls, why in ledger),
           "decisions": sorted(decisions, key=lambda d: (d["fixture"] or "", d["model"],
                                                         d["from"] or "", d["current"]))}
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
    # A pooled in-situ cell reads the harm the current rest shows on its own
    # (its harm evidence), as its ceiling and no-harm tests do.
    guard = cell.get("rest_guard")
    harm = guard.get("harm_evidence_at") if isinstance(guard, dict) else cell.get("harm_at")
    if harm is not None:
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
    if any(c.get("scope_paused") == "removed" for c in cells):
        # The eval scope pass paused the fixture because the skill is gone
        # from its registry: there is nothing left to keep or remove, and no
        # work item may ask for a fixture for it. The explorer shows it as
        # removed (scripts/explorer_data.py mark_removed / removed_skills).
        return {"verdict": "insufficient", "removed": True, "reason": "the skill no "
                "longer exists in its registry, so its fixtures are paused and it is "
                "not judged"}
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
    if any(c["class"] == "paused" and c.get("scope_paused") == "zero-use" for c in counted):
        # A fixture the eval scope pass paused for no recorded use never
        # voted: with every retire automatic (2026-11-13), the cells that did
        # vote must not remove a never-used skill beside it. It stays
        # `insufficient` until those fixtures run again (the skill is used);
        # an unused skill leaves through harness/removal_policy.py instead.
        # A ceiling or floor pause keeps the parked-cell behavior below.
        return {"verdict": "insufficient", "reason": "a fixture paused for no recorded use "
                "of the skill has not voted, so the other cells do not remove it"}
    if not headroom or not classes <= PARKED_CLASSES | {"no-benefit", "no-clear-effect"}:
        # No cell (no roster model) or a class this verdict does not know:
        # never a retirement without evidence.
        return {"verdict": "insufficient", "reason": "no cell shows no benefit"}
    clear = all(c["class"] == "no-benefit" for c in headroom)
    parked = " (cells parked or with a broken fixture do not vote)" \
        if len(headroom) < len(cells) else ""
    ceilings = sum(c["class"] in PARKED_CLASSES for c in counted)
    # Every retire is `auto` (2026-11-13); `removal_reason` keeps the evidence.
    if clear and ceilings:
        why = f"{ceilings} parked cell(s) (at the ceiling, or paused by the eval " \
              "scope pass) did not vote"
        reason = f"every cell with headroom shows no benefit{parked}"
    elif clear and len(headroom) >= 2:
        why = f"{len(headroom)} cells with headroom, every one no-benefit"
        reason = f"every cell with headroom shows no benefit{parked}"
    elif clear:
        why = f"only {len(headroom)} cell with headroom"
        reason = f"the one cell with headroom shows no benefit{parked}"
    else:
        why = "a cell reached the run cap with no clear effect"
        reason = f"no cell with headroom shows benefit, and one has no clear effect{parked}"
    return {"verdict": "retire", "removal": "auto", "reason": reason,
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
    still turn into shorten-or-merge. Its verdict is then `insufficient`
    with ALONE_UNFINISHED_REASON (2026-11-13: neither a removal nor an owner
    proposal; the scheduler runs the alone arm), and `in_situ_verdict` stays
    `retire`.

    The in-situ cells are `retirement` with `strata`: by the policy's
    `rest_policy`, the runs beside the rest on main only (`current`), or
    beside every rest with THE CURRENT-REST GUARD (`pooled-with-current-guard`;
    module docstring, IN-SITU GUIDANCE CELLS). The alone cells pool as
    before."""
    runs = index.get("runs", [])
    out = {pair: retirement({"runs": [r for r in runs if r.get("pair") == pair]},
                            models, section, policy, expected,
                            bet_prior if pair == "in_situ" else None,
                            strata=pair == "in_situ", family=pair == "in_situ")
           for pair in GUIDANCE_PAIRS}
    in_situ, alone = out["in_situ"], out["alone"]
    verdict, reason = in_situ["verdict"], in_situ["reason"]
    extra = {k: in_situ[k] for k in ("removal", "removal_reason", "unmeasured", "removed",
                                         "paused_ceiling")
             if k in in_situ}
    if verdict == "retire" and any(c["class"] == "benefit" for c in alone["cells"]):
        verdict, reason = ("shorten-or-merge", "no marginal benefit inside the whole "
                           "guidance, but a cell shows benefit alone (section vs "
                           "none): the rest of the guidance covers it")
        extra = {}
    elif verdict == "retire" and alone_unfinished(alone["cells"]):
        # Not a removal and not a proposal for a person: the evidence is
        # incomplete. `in_situ_verdict` stays `retire`, so the planner still
        # fires the alone pair (scripts/plan_week.py `leans_to_removal`).
        verdict, reason = "insufficient", ALONE_UNFINISHED_REASON
        extra = {}
    return {"verdict": verdict, "reason": reason, "in_situ_verdict": in_situ["verdict"],
            **extra, "cells": in_situ["cells"],
            "alone": {"verdict": alone["verdict"], "reason": alone["reason"],
                      "cells": alone["cells"]},
            "runs_used": sorted(set(in_situ["runs_used"]) | set(alone["runs_used"])),
            "discarded_runs": merge_discards(in_situ.get("discarded_runs"),
                                             alone.get("discarded_runs")),
            "run_utility": merge_utility(in_situ.get("run_utility"), alone.get("run_utility")),
            "decisions": [{**d, "pair": pair} for pair in GUIDANCE_PAIRS
                          for d in out[pair].get("decisions", [])],
            **{k: in_situ[k] for k in ("keep_family", "keep_alpha") if k in in_situ}}
