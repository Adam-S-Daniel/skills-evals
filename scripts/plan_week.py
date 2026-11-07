#!/usr/bin/env python3
"""Plan the week's routine fires: which cells to measure and which skills to
improve, by priority band, inside the weekly allowance (G5, G6).

    plan_week.py plan --results-tree DIR --as-of TIME [--registry NAME=PATH ...]
                      [--guidance DIR] [--evidence FILE] [--lessons DIR]
                      [--max-fires 30] [--out FILE]
    plan_week.py validate-fire        (the matrix leg's env; exit 0 or 1; a stale leg exits 0
                                       with fire=false)
    plan_week.py wait-slot [--max-wait SECONDS] [--sweep-started TIME]
    plan_week.py watchdog --mode wait|check [--max-wait SECONDS]

The rules are the thresholds design's (eval-loop thresholds, version 2,
2026-10-25), A (eligibility), C (stopping) and D (bands); B (acceptance)
stays in scripts/propose_skill_edit.py.

WHAT IS MEASURED. Eval fires are cells, (fixture, roster arm model), of the
reviewed fixtures in evals/scheduled.yml only (ADR 0008): every fire is one
routine-eval-fire.yml dispatch in eval mode with that `model` (or with a
fixture's two model cells at once, PAIR FIRES), both arms
(for a guidance cell not leaning toward removal, its in-situ pair alone:
THE ALONE PAIR, at FOCUS_VERDICTS), one trial. A cell's evidence is scripts/compute_gates.py's verdict document,
computed here over the results tree, so the cells are pooled exactly as the
retirement verdict pools them.

GUIDANCE FIXTURES (#124). A scheduled `evals/guidance/<section>/<name>`
fixture (`subject: guidance`) is a cell like any other, fired in eval mode
on its path, but it names a section, not a skill: its evidence is the
section's in-situ cells in the verdict document's `guidance` half
(results/guidance/<section>/..., classified by arm `mode`), and its cell
carries `section` and an empty `skill`. Skill-only logic skips it: the
removal-PR safety band, skill improve eligibility and skill usage weight.
The section's expected extent needs `--guidance`, an _agent-guidance
checkout; without one every guidance cell that has runs stays insufficient
and there are no guidance improve candidates. A guidance section is an
improve CANDIDATE (see IMPROVE ELIGIBILITY), ranked with the skills, and an
eligible one is a `guidance-improve` fire (routine-eval-fire.yml's
guidance-improve mode, ADR 0005's routine guidance improve mode addendum).

THE BANDS (rule D), in order:

  1. safety: every cell of a skill with an open removal pull request in
     adam-agentskills (`retire-skill/<skill>`), no cap, counted first. The
     doc's second safety item, a touch check of an open registry pull
     request's head, is not planned: routine arms run only the registries'
     default branches (ADR 0010 decision 1).
  2. missing evidence, at least 30%: cells with no run on their model,
     cheaper model first, then heaviest model usage (usage/latest.json on the results branch;
     equal weights without it).
  3. near a decision, at least 20%: insufficient cells, fewest runs first,
     then the cheaper model (every run can decide a cell: harness/gates.py
     checks a confidence sequence after each one).
  Bands 2 and 3 skip every cell of a skill or guidance section whose
  verdict is already `keep` (one confident benefit decides it; band 6
  re-checks it), and order the cheaper model first within a tie (Adam,
  2026-10-31: Sonnet first, Opus only while that has not settled it).
  They hold skill cells only: an undecided guidance cell (class missing or
  insufficient) goes to band 4 or band 8.
  4. guidance focus, at least 15% (`guidance_focus`; Adam's rule,
     2026-11-02 18:42 UTC: remove a section at 90% confidence it does not
     improve results by 0.15 or more): the undecided cells of the
     GUIDANCE_FOCUS_SECTIONS (2) eligible sections nearest a verdict.
       progress: a cell's retire progress is its objective's no-help
         confidence (the level its remove test reached) over
         `retire_confidence` (the verdict document's `guidance_policy`,
         else DEFAULT_RETIRE_CONFIDENCE); its keep progress is its
         objective's helps confidence over `benefit_confidence`. The judge
         does not vote (harness/gates.py, 2026-11-03). An absent value is
         0.
       score: max(min over the section's cells of retire progress, max
         over them of keep progress), since it retires only when every
         cell clears and keeps on one; ties by fewer cells (a smaller
         section is nearer a verdict for the same runs, deliberately), more
         counted runs, then section id.
       eligible: its verdict is open (`insufficient` or none: keep, every
         retire verdict, shorten-or-merge, ceiling and cannot-discriminate
         are not), some cell would plan a fire (schedulable, stakes not
         `none`, not fixture-broken), no removal pull request is open in
         _agent-guidance, and no cell is BLOCKING: its no-benefit or
         no-clear-effect was overruled by an errored trial or an anomalous
         skip, or it is cannot-discriminate with BLOCKING_MIN_RUNS (3)
         counted runs on each arm. More runs on the current content cannot
         move a blocking cell toward removal, nor an `insufficient` cell at
         `max_runs_per_cell` pairs (gates' `at_cap`). A ceiling or
         ceiling-unconfirmed cell does not block: it is not fired, and the
         section's other cells still are.
     Within it the higher-scored section goes first, then its binding
     cell: the lowest retire progress, or, when the section's score came
     from the keep side, the highest keep progress; then the cheaper
     model. The plan records the sections as
     `guidance_focus`. There is no stall rule: a section that never gets
     closer holds its slot until its verdict or content changes.
  EMPTY FIRES (#559). A cell bound for band 2, 3, 4, 6 or 8 with
  BROKEN_AFTER_FIRES (2) empty fires becomes a `fixture-broken` work item
  and enters no band. An empty fire is a successful non-bare eval fire for
  the cell that started after the cell's newest run of any role or digest
  on its model (gates' `newest_on_model`; any fire when it has none), at
  least FIRE_RESULT_WINDOW (2 hours) ago, within RETRY_AFTER (14 days, so a
  broken cell is retried once its fires age out) and not before
  EMPTY_FIRES_SINCE (fires under the delivery before main's copy say
  nothing). OUTAGES (2026-11-01: six fixtures fired, none produced
  anything). Each fire is classified once: young (under FIRE_RESULT_WINDOW
  old), delivered (a run of the cell is stamped within FIRE_RESULT_WINDOW
  of its start, gates' `run_stamps_on_model`) or empty, so a later retry
  never changes an old fire's state. Each empty fire is judged on its own
  window, OUTAGE_GAP (60 minutes) either side of its start, over every
  classified fire of every cell (#583: a window centered on the fire, so
  its verdict depends only on fires near it, not on where a chain began).
  One with no delivered and no young fire in its window, and empty fires
  there covering at least OUTAGE_CELLS (3) distinct cells, is an outage
  fire (a delivered fire PROBE_WAIT or more after the window's first empty
  one may be the breaker's own probe and does not count; an empty fire at
  most OUTAGE_GAP before an outage fire, no delivery between, is one too,
  for a slow onset): a cell's earliest, at most OUTAGE_EXCUSES (1) within
  RETRY_AFTER, is excused (`outage_fires`), and any further one counts, so
  fixtures broken together still go fixture-broken, one fire later. One
  with a young fire in its window is undecided and counts nothing yet. A window
  narrower than three cells cannot be told from broken fixtures, so it
  counts: that is the ambiguity left. Each chain of outage fires (each at
  most OUTAGE_GAP after the last) starting in the last 24 hours is a
  `routine-outage` work item (no fixture names). A refused run counts: the
  fire workflow succeeds once the fire API accepts, so fixture-broken means
  "no run after two fires", whatever the cause. A cell whose verdict
  document lacks `newest_on_model` or `run_stamps_on_model` counts none and
  joins no window (fail safe). Safety cells are exempt. Every band, safety included, skips a cell with a
  PENDING fire: one younger than its `pending_window` (the routine's
  40-minute eval stop per model plus 10 minutes), successful or still
  running, with no run on the cell since it started; past that the fire cannot deliver, so the
  cell is planned again, a lost fire re-fired within the hour. THE CIRCUIT BREAKER
  (#583): the routine is down from the start of an outage fire until a
  paired eval fire on a known cell delivers (or, for the breaker only,
  once fires PROBE_WAIT, 45 minutes, old with no run, plus empty fires,
  cover OUTAGE_CELLS cells in one window with no delivery in it or after
  it). While down a plan holds improve and bare fires and sends at most
  one fire, a probe: a paired eval fire on any schedulable cell (settled
  and fixture-broken ones too), fewest empty fires first, then the oldest
  last fire, then band order; none while a probe younger than PROBE_WAIT
  has landed nothing. Probes never count: an empty fire that started
  while the routine was down is a down fire (`down_fires`), not an empty
  one, unless it is an outage fire in the outage's first PROBE_WAIT,
  which keeps the outage rule. Every plan while down lists a
  `routine-down` work item (no fixture names). With no schedulable eval
  cell at all the plan is not held.
  5. improvements, at least 20%: improve fires for eligible skills and
     guidance-improve fires for eligible guidance sections, highest
     potential value first: value = use x headroom / cost, ties by name;
     a skill's times its skill-edit lesson boost (SKILL-EDIT LESSONS).
       use: a skill's usage weight (harness/skill_usage.py, `skill_weights`:
         invocations over 4 weeks); a guidance section's is the census's
         transcript sessions scanned scaled to 28 days by its window
         (`skill_usage.session_rate`), since every session loads the
         guidance. Unknown (no, stale or unreadable census) is neutral, the
         median known skill weight, never zero; a known 0 stays 0.
       headroom: 1 - the pooled with-arm pass rate over the train fixtures
         (a guidance section's: its in-situ `full` arm). Unknown headroom
         gives no value, ranked last, never a guessed 0.
       cost: allowance points, IMPROVE_TRIALS x the sum over the subject's
         fixtures of that fixture's mean `fire_cost` across its cells with a
         known cost. With none known, the median of the known estimates
         across candidates, else the improve charge (neutral, like use).
     Each ranking row records whether use and cost were known.
     IMPROVE CAP (#572, 2026-11-02): before allocation the band is walked
     in allocate's own order, and an item goes only when
     `allowance_guard.improve_cap` allows it with the earlier kept items
     counted, exactly the test the guard applies to each fire (Adam's 0.20
     share of weekly_cap for the account week, at least one fire of each
     kind). Cut items count as unplanned. The share above is of one sweep's
     room; this one is of the whole week's cap, and binds every dispatcher.
  6. re-checks: decided cells whose newest run is over 8 weeks old (4
     weeks for a high-stakes subject).
  STAKES (evals/stakes.yml, scripts/stakes.py; Adam, 2026-11-01): within
  bands 2, 3, 4, 6 and 8 a high-stakes subject's cells go first, before
  the band's own order; a `none` subject (a named check enforces it) plans
  no eval fire at all. Every other subject is `normal`.
  7. bare baselines (ADR 0012, bare baseline addendum; Adam, 2026-10-27:
     "one time per model per version of model"): one fire with `arms:
     bare`, `BARE_TRIALS` trials, per (scheduled fixture that runs in place,
     roster model) that has never had one, heaviest model first, with no
     minimum share, so only room the other bands leave. Done means a bare
     run ingested for that cell (the verdict document's `bare_runs`) or a
     bare fire for it that succeeded or is still running (its run title);
     a refused or failed fire is not done. A new roster model id gets its
     own; nothing is repeated on a clock.
  8. guidance rest: every other undecided guidance cell, with no minimum
     share, so only room every other band leaves, in band 3's order
     (fewest runs, so missing cells first, then the cheaper model). When
     the 30-fire cap binds, a section outside the focus can wait weeks.

THE BATCH (Adam's steady-state goal, 2026-11-02 18:57 UTC: at 25% of the
weekly allowance, every two weeks pick a batch of skills and guidance
sections numbering about three times the historical weekly addition rate,
bring them all to a verdict, then start a new batch). Only with
`--batch-policy` (evals/batch-policy.yml; the weekly workflow passes it),
and only from the policy's `start`. `batch_state` decides it each plan:
  members (Adam's 2026-11-03 decision, fit the batch to the budget): a
    target size per kind (skill, guidance section) of max(1, multiplier x
    the weekly addition rate measured when the batch starts, half rounded
    up; `batch_rates`, the policy's constant when a history is unreadable),
    filled within the budget, `weekly_cap` x the period's weeks
    (`fit_batch`). Candidates are the subjects with a schedulable cell,
    never a private skill, whose status is open (`batch_subjects`: verdict
    open, no removal pull request, no blocking cell, some cell would plan a
    fire). Carried members first; then the kinds take turns, skills ranked
    most used first, then high stakes, guidance sections (no per-section
    use) high stakes first; then the longest without a run (never run
    first), then name. Each cell with headroom is charged its remaining
    observations, min(`pairs_per_cell`, the gate's `max_runs_per_cell` -
    the observations it has), at its model's measured cost per observation
    (`pair_costs`: points per paired run); a subject that alone would
    overflow the room left waits, and a cheaper one after it can still join.
    Never empty while a subject waits.
  lifetime: a batch stays until every member has left `open` (decided,
    blocked, stalled or gone) or it is due (`period_days` after its start),
    whichever is first. Then the next one starts at once: the old batch's
    open members carried first, keeping their `joined` number, then new
    picks to fill each kind. Nothing to carry and nothing to pick keeps the
    old record.
  effect: bands 2, 3, 4 and 8 (BATCH_BANDS) take only member cells; the
    guidance focus is every guidance member, not the top
    GUIDANCE_FOCUS_SECTIONS. Safety, re-checks, improvements and bare
    baselines are unchanged.
  record: BATCH_RECORD (batches/current.json) on the results branch, read
    with the results tree. A plan that starts a batch writes it to
    `--batch-out` and sets `batch_started=true`; the weekly workflow's
    batch-publish job commits it there and as batches/<number>.json. The
    record carries the previous batch's members with their final status,
    and for audit the rates and their basis, the target sizes, the fit
    (budget, costs, total), each member's expected cost and the subjects
    left waiting. A malformed record stops the plan (fail closed). The plan's `batch`
    adds each member's status now and `outside`, the cells the batch held
    back.

Each band first gets its minimum share of the room left after safety;
what is left then goes to the bands in order. Within a band ties break on
cost, cheapest first, and the plan stops at `--max-fires`. A fire is
reserved at its historical cost: its cell's mean agent `cost_usd` per run
(summed over both arms) converted to allowance points by the ratio the
measured routine runs show (points per dollar), between `per_run_overrun`
and one full reservation; one full reservation when either is unknown. A
bare fire runs ONE arm, so it is reserved at its cell's mean agent cost per
arm trial times `BARE_TRIALS`, clamped the same way. An
improve or guidance-improve fire is reserved at
`allowance_guard.improve_charge`. The room is
`allowance_guard.room`. The per-fire guard still checks every fire at its
full reservation before it spends anything; this plan only orders them.

IMPROVE ELIGIBILITY (rule A), per skill with fixtures under evals/<skill>/:

  1. at least `MIN_IMPROVE_FIXTURES` (4) fixtures, all naming
     adam-agentskills (the one registry the routine checks out); the first
     by name is the fixed holdout, passed as `holdout` so the proposer never
     sees it. Fewer fixtures with train headroom is a `needs-fixtures` work
     item instead, ranked by headroom, unless retirement owns the skill
     (rule 4).
  2. train headroom: 1 - the pooled with-arm pass rate over the other
     fixtures is at least `MIN_GAIN` (propose_skill_edit's default gain). A
     skill below it (one that already passes at least 90% of its checks) can
     not be improved by an edit, so it becomes a `needs-harder-fixtures` work
     item instead: the next step is a fixture it fails. Retiring skills and
     skills outside adam-agentskills get none.
  3. a target: some train check fails in at least 25% of at least 6 scored
     with-arm trials, at least twice, and has passed at least once in some
     arm. Infrastructure trials are not evidence (gates.trial_record).
  4. not owned by retirement (`retirement_owner`): owned means its verdict
     is `retire` or `retire-pending`, or a `retire-skill/<skill>` pull
     request is open in adam-agentskills. An owned skill gets no
     `needs-fixtures` or `needs-harder-fixtures` item either.
  5. not paused (rule C, `pause`): no open improve pull request
     (`eval-improve/<skill>` in adam-agentskills), no attempt in flight, no
     open issue or pull request labeled `on-hold` whose title names the
     skill, no cooldown. Outcomes come from scripts/improve_outcomes.py.

  The same ranking covers every guidance section with fixtures (not
  `_delivery`, the canary), found by scripts/propose_guidance_edit.py's own
  listing (fixtures declaring the `full` ablation arm). A section is
  eligible with at least `MIN_IMPROVE_FIXTURES` such fixtures (the last in
  name order is the holdout, as the proposer picks it), train headroom of at
  least `MIN_GAIN` over its pooled in-situ `full` arm runs, and a guidance
  not owned by retirement (`retirement_owner` with `subject="guidance"`: a
  guidance verdict, the verdict document's `guidance` half, of `retire` or
  `retire-pending`, or an open `retire-guidance/<section>` pull request in
  _agent-guidance; an owned section gets no fixture work item either), an
  `eval-coverage.yml` row that is not `skipped` (the
  proposer refuses one), and not paused: `pause` keyed by section over the
  guidance-improve outcomes (scripts/improve_outcomes.py, mode
  `guidance-improve`) and the `eval-guidance-improve/<section>` pull
  requests in _agent-guidance, plus the guidance lane (`guidance_lane`): no
  guidance-loop pull request (`eval-guidance-improve/*`,
  `retire-guidance/*`) open there and no guidance-improve attempt in flight,
  since every guidance edit writes AGENTS.md and docs/guidance-impact.md and
  a second would conflict. Its content change, for the three-rejection stop,
  is the _agent-guidance history of its row's file. It has no target rule
  (the proposer proposes before it measures). An eligible section is an
  improve-band fire, `mode: guidance-improve`, its `section`, the proposer's
  holdout as `holdout` (the fixture key, guidance/<section>/<name>), reserved
  at the improve charge; at most ONE per plan, the highest value (the lane
  rule again). The work item `guidance-improve` (change type
  `guidance-edit`, routed to a local run of the proposer) remains only for
  an eligible section whose id the fire workflow's `section` pattern
  (^[a-z0-9][a-z0-9-]{0,63}$) refuses. One with fewer fixtures and headroom
  gets `needs-fixtures`, one without headroom `needs-harder-fixtures`, each
  carrying its `section`. A section whose eval-coverage.yml row is `gap`
  (tracked, no fixture yet; `guidance_gaps`) and that retirement does not
  own gets `needs-fixtures` with zero fixtures and unknown headroom, so its
  first fixture is asked for too.

STOPPING (rule C): a rejection (every no-branch outcome, conservatively, and
an accepted candidate whose pull request closed unmerged) starts a 14-day
cooldown; three in a row stop the skill until its content (the registry
checkout's git history for its directory), a fixture (this repository's
history under evals/<skill>/) or the roster (evals/roster.yml) changes after
the third, or 90 days pass. A failed fire job is infrastructure: it is
retried at most twice, then the skill waits 14 days. After a merged
improvement nothing is attempted until a with-arm run of the new content
lands (the gates pool only runs of the content on main).

WORK ITEMS are not fires: `needs-fixtures`, `needs-harder-fixtures`,
`fixture-ceiling` and `fixture-broken` (change type `fixture`), `cell-at-cap`
(change type None: an undecided cell whose pairs reached the cap, with its
gates reason; none for a kept subject), `paused-unmeasured` (change type
`fixture`: a subject the gate marked `unmeasured`, every cell parked and a
scope-paused one showing no ceiling on its own runs; `unmeasured_items`),
`paused-ceiling` (change type `fixture`: a `ceiling` subject with a scope-paused
cell, which has no planner cell to ask for the harder fixture;
`paused_ceiling_items`),
`routine-outage` and `routine-down` (change type None: the routine failed,
not a subject; see EMPTY FIRES),
`guidance-improve` (change type `guidance-edit`; only for a section id the
fire workflow refuses, see above). Every item carries `change_type`:
`skill-edit` for an improve fire or a description trim (`description-trim`,
DESCRIPTION TRIMS), `guidance-edit` for a guidance-improve fire, `fixture`,
`trigger` for a trigger-only improve fire (THE TRIGGER LANE), or None for
`routine-outage` and
`routine-down`. `fixture-ceiling`, `cell-at-cap`, `paused-unmeasured` and `paused-ceiling` are
routed SUMMARY_ROUTE: the step summary counts them and the plan JSON lists
them, but scripts/work_item_issues.py files no issue for them (round 4's
m1). Lesson proposals of kind `agent-check` are not planned
here: _agent-guidance's fleet worker reads them (its ADR 0027), so a
second reader would file each twice (#657).

SKILL-EDIT LESSONS (#657). `--lessons DIR` is adam-agentskills-private's
`lessons/proposals/` from `persistent/lessons`, read by
scripts/lesson_evidence.py: the newest day's `skill-edit` proposals whose
subject is `skill:<name>`, as `{name: evidence_count}`. A public skill's
improve candidate with such evidence has its value multiplied by
1 + min(count, SKILL_EDIT_BOOST_CAP) / SKILL_EDIT_BOOST_CAP, so real-session
evidence can at most double it; it never makes an ineligible skill eligible
and never gives an unknown value one. The ranking row carries the count as
`lesson_evidence`. A private skill gets no candidate, so no count of it is
published.

THE TRIGGER LANE (usage tracking, 2026-10-26: about 55 skill calls in 8
weeks over about 72,000 model turns, so most skills almost never trigger).
Every public adam-agentskills skill whose usage weight is fresh (known) and
at most `TRIGGER_MAX_WEIGHT` is judged here (skills-evals#662; Adam,
2026-11-03: "New fire mode runs only skill-creator's description loop").
With a reviewed evals/<skill>/trigger-eval-set.json it is a `trigger-optimize`
FIRE: an improve-mode fire with `trigger_only` true (change type `trigger`,
no holdout, charged and capped as an improve fire), which runs only the
description loop on that set and is accepted on a held-out gain of 0.15 with
no drop on the should-not-trigger queries. It goes in the improve band after
the value-ranked improve fires, least used first, and only when nothing
pauses the skill (rule C over the same improve records and
`eval-improve/<skill>` pull requests, with a merged edit waiting COOLDOWN for
usage to show, since a skill with no fixtures is never re-measured) and the
skill has no ordinary improve fire in the plan (both would write
`eval-improve/<skill>`). Without a set it is a `needs-trigger-set` work item
(change type `fixture`, routed to an agent-ready issue) to write one. A skill
owned by retirement gets neither, and a private skill is never judged. The
plan's `triggers` maps every judged skill to {eligible, reasons, weight};
the weekly workflow closes a needs-trigger-set issue only for a judged skill.
Skills whose SKILL.md is mostly checklist or rules
sections (`hook_candidate`) are listed as `hook_candidates` and in the
summary, since a git hook may serve them better.

DESCRIPTION TRIMS (skills-evals#687). adam-agentskills caps a description at
TRIM_MAX_CHARS (400) characters, and an eval-protected skill over the cap
carries a `length-limit` waiver in that checkout's `scripts/skills_waivers.yml`
until the improve lane trims it. Every waived skill that is not private is
tracked in the plan's `trims` map ({eligible, reasons, chars, planned}) and as
a `description-trim` work item (change type `skill-edit`) whose `route` is
"fire" when this plan fires it, else why not; the weekly workflow files no
issue for it. One is eligible when it has at least TRIM_MIN_FIXTURES fixtures,
all naming adam-agentskills (the trim is measured on them), is not owned by
retirement, its description is still over the cap, and its rule C pause (the
same as an ordinary improve fire's, including a merged edit waiting for a
with-arm run of the new text) is None. It is then an improve-band fire with
`trim_description` true (change type `skill-edit`, no holdout, charged and
capped as an improve fire), placed BEFORE the value-ranked improve fires: a
fixed chore, not a value bet. It is still subject to the improve cap and the
outage hold, and a skill with a trim fire gets no ordinary or trigger-only
improve fire in the same plan (all write `eval-improve/<skill>`). A missing or
unreadable waiver file plans no trim, and `trims_unread` says why. Once a trim
merges, its pull request has removed the waiver, so the skill drops off.

OUTPUT. `--out` gets the whole plan as JSON, including `improve_ranking`
(every candidate, skill or guidance section, by value, highest first and
unknown last, with its use, headroom, cost, whether use and cost were known,
and eligibility), `guidance` (a per-section status like `skills`) and
`guidance_focus` (the focused sections with their scores, band 4); each
fire entry carries its `value` (null for an eval fire; the matrix legs do
not). `--ranking-out` gets the ranking alone (public-safe: skill names and
section ids), which the weekly workflow uploads as the `improve-ranking`
artifact. $GITHUB_OUTPUT gets `matrix=`
(the fires, improve and guidance-improve fires last so a long improve run
never holds up the evals behind it; every leg carries `section`, empty but
for a guidance-improve leg, `trigger_only`, the string "true" for a
trigger-only improve leg and "false" otherwise, and `trim_description`, the
same for a description trim) and `count=`. The log and job summary carry numbers and
public skill names only.

PAIR FIRES. A routine session costs about $0.67 of its own on every fire,
counted nowhere, so one fire runs a fixture on two models when it can
(`pair_fires`, after the allocation): two chosen eval fires on one fixture
with the same `arms` (so the same trials) on two roster models become ONE
leg whose `model` is "m1,m2", in roster order (ctx["roster_models"]; a
hand-built ctx without it pairs nothing). Its `cost` is the two cells'
sum, its `band` the earlier cell's, and its `cells` lists each model with
its own band and cost. A lone cell, an improve or guidance-improve fire,
a probe and the refresh fire stay single legs. `--max-fires` caps cells,
so pairing only ever shortens the matrix, and wait-slot still counts
fires. The fire workflow sends the pair as `models: [m1, m2]`; the
routine runs run_eval once per model, in that order, into one run id. Each
run gets its own 40 minutes, so a pending pair fire holds its cells for
`routine_deadlines.deadline("eval", 2)`, 90 minutes, and counts in flight
for twice EVAL_FLIGHT (`fire_models`). Its
run title, `... <fixture> m1,m2`, holds a cell of each model: every
reader here expands it per model (`improve_outcomes.title_models`), so a
pending pair fire holds both cells and its two runs are judged each on
its own model. `validate-fire` checks each model as it checks one, and
the pair as the fire workflow does (two distinct ids, each matching
PAIR_MODEL_RE).

FIRE CHECK. `guidance-headroom SECTION` is routine-eval-fire.yml's check
before a guidance-improve fire: the same rule A headroom over the same
pooled in-situ `full` runs (`guidance_contexts`), so a fire dispatched by
hand cannot start what the plan would never pick. Exit 1 when the train
headroom is known and under `MIN_GAIN` (the section already passes at least
90% of its checks; it needs harder fixtures), 0 otherwise. Unknown headroom
passes: the guidance proposer measures before it decides, and the rule is
about sections already at the ceiling. Unlike the skill proposer it has no
early stop after a baseline (it interleaves baseline and candidate), so
without this check such a fire spends its whole run before rejecting
(2026-10-28: "anything-you-name-gets-its-link" at 72/72, run
20261028T213124Z-65c174). The log names the section and the numbers only.

EVIDENCE. `--evidence FILE` reads the GitHub evidence from a recorded JSON
file ({fire_runs, improve_branches, registry_prs, on_hold}, and optionally
guidance_branches, guidance_prs and guidance_on_hold, empty when absent);
without it the evidence is fetched with GH_TOKEN (scripts/improve_outcomes.py's
reader), _agent-guidance's pull requests and on-hold issues included.
Every read failure stops the plan (fail closed); the message is fixed text
and a status code.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import urllib.parse

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT / "harness"))

import allowance_guard as guard  # noqa: E402
import improve_outcomes as outcomes_mod  # noqa: E402
import lesson_evidence  # noqa: E402
import plan_scheduled_evals as schedule  # noqa: E402
import routine_deadlines  # noqa: E402
import stakes as stakes_mod  # noqa: E402

REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
#: A skill here is private (Adam, 2026-10-31): its results come from the
#: private repository's own results branch and stay out of every public
#: output, so it gets cells (fires) but no improve candidate, ranking row,
#: status or work item, each of which would publish its pass rate.
PRIVATE_REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills-private"
REGISTRY_REPO = "Adam-S-Daniel/adam-agentskills"
SELF_REPO = "Adam-S-Daniel/skills-evals"
GUIDANCE_REPO = "Adam-S-Daniel/_agent-guidance"
#: Guidance-loop heads in _agent-guidance: improvements (this plan's fires,
#: scripts/guidance_improve_gate.py) and removals (scripts/retire_skill.py).
GUIDANCE_IMPROVE_PREFIX = "eval-guidance-improve/"
GUIDANCE_REMOVAL_PREFIX = "retire-guidance/"
#: The fire modes that run the improvement loop (held IMPROVE_FLIGHT).
IMPROVE_MODES = ("improve", "guidance-improve")
MIN_IMPROVE_FIXTURES = 4
MIN_GAIN = 0.10
TARGET_FAIL_RATE = 0.25
TARGET_MIN_TRIALS = 6
TARGET_MIN_FAILS = 2
COOLDOWN = timedelta(days=14)
STOP_AFTER_REJECTIONS = 3
STOP_FOR = timedelta(days=90)
INFRA_RETRIES = 2
RECHECK_AFTER = timedelta(weeks=8)
#: A decided high-stakes subject is re-checked this soon (evals/stakes.yml).
RECHECK_AFTER_HIGH = timedelta(weeks=4)
BROKEN_AFTER_FIRES = 2
#: A successful eval fire this old with no run on its cell produced nothing.
FIRE_RESULT_WINDOW = timedelta(hours=2)
#: How long a one-model fire with no run yet holds its cell (`pending`): the
#: routine's own eval-mode stop plus a margin (scripts/routine_deadlines.py),
#: after which the fire cannot deliver, so the cell is planned again. The
#: stop is per model, so a pair fire holds for `pending_window` of two. Adam,
#: 2026-11-03: a lost fire must not wait FIRE_RESULT_WINDOW, two hours, for
#: someone to notice it. The fire itself is still classified only at
#: FIRE_RESULT_WINDOW, so the outage windows and PROBE_WAIT keep their
#: meaning, and only two empty fires make the cell fixture-broken.
PENDING_WINDOW = routine_deadlines.deadline("eval")
#: Only empty fires this recent count, so a fixture-broken cell is retried
#: once its fires age out instead of staying broken for good (#559).
RETRY_AFTER = timedelta(days=14)
#: Empty fires before this are not counted. Runs test main's copy of a skill
#: from #559 on, which adds refusals (registry_checkout_dirty, ...) and
#: clears others, so fires made under the old delivery say nothing about
#: whether the cell can produce a run now; the first sweep after the change
#: judges only fires made under it.
EMPTY_FIRES_SINCE = datetime(2026, 11, 3, tzinfo=timezone.utc)
#: An empty fire is judged on the fires that started within this of its
#: start, on either side (#583): a window centered on the fire itself, so
#: its verdict depends only on fires near it, never on where a chain of
#: fires began. Outage fires at most this far apart are one reported outage.
#: explorer_data's FIRE_SWEEP_GAP is this constant and its sweeps come from
#: fire_sweeps too, over the fires without results.
OUTAGE_GAP = timedelta(minutes=60)
#: An empty fire whose window holds no delivered or young fire, and whose
#: window's empty fires span at least this many distinct (fixture, model)
#: cells, is a routine outage's, not a broken fixture's: one bad cell or two
#: cannot explain it, and counting it would bench healthy cells for
#: RETRY_AFTER. A narrower window cannot be told from broken fixtures, so it
#: counts.
OUTAGE_CELLS = 3
#: Outage fires excused per cell within RETRY_AFTER, its earliest. The
#: backstop: a fixture empty in sweep after sweep still reaches
#: BROKEN_AFTER_FIRES, one fire later, even when every sweep looks like an
#: outage because several broken fixtures fail together.
OUTAGE_EXCUSES = 1
#: A `routine-outage` work item is listed for an outage whose first fire is this recent.
OUTAGE_REPORT_WINDOW = timedelta(hours=24)
#: While the routine is down (#583), a probe this young with no landed run
#: holds the next probe, and a fire this old with none counts toward the
#: provisional trip. An eval run lands in 4 to 12 minutes; FIRE_RESULT_WINDOW
#: still decides whether a fire was empty.
PROBE_WAIT = timedelta(minutes=45)
SHARES = (("missing", 0.30), ("near", 0.20), ("focus", 0.15), ("improve", 0.20))
BANDS = ("safety", "missing", "near", "focus", "improve", "recheck", "bare", "guidance-rest")
#: The guidance focus (module docstring, band 4; Adam's rule, 2026-11-02
#: 18:42 UTC: remove a section at 90% confidence it does not improve results
#: by 0.15 or more). Every section had a missing cell and runs were spread
#: over all of them, so none came near a verdict; the focus spends guidance
#: fires on the sections nearest one. Fires stay at one trial: the harness
#: refuses `--trials > 1` for a guidance fixture, and trials collapse into
#: one run mean, so three cost as much per verdict (2026-11-02 design
#: review).
GUIDANCE_FOCUS_SECTIONS = 2
#: The decision levels a cell's progress is normalized by when the verdict
#: document carries no `guidance_policy` (evals/gate-policy.yml's).
DEFAULT_RETIRE_CONFIDENCE = 0.90
DEFAULT_BENEFIT_CONFIDENCE = 0.80
#: The verdicts more runs on the current content may still change: every
#: other section verdict (keep, retire, retire-pending, retire-unconfirmed,
#: shorten-or-merge, ceiling, cannot-discriminate) is decided or blocked.
FOCUS_VERDICTS = (None, "insufficient")
#: THE ALONE PAIR (owner, 2026-11-03): a guidance eval fire runs the
#: section-alone pair (section vs none) beside the in-situ pair (`arms:
#: both`) only for a section leaning toward removal (`leans_to_removal`);
#: every other guidance fire is `arms: in-situ`. The alone pair is about 37%
#: of guidance agent spend and is read in one place, harness/gates.py
#: `guidance_verdict`, which turns an in-situ `retire` into
#: `shorten-or-merge` when an alone cell shows benefit. A section leans toward
#: removal when its in-situ verdict is `retire`, or when its retire progress
#: (the lowest over its cells, as `guidance_focus` scores it) is at least
#: this share of the retire level: the alone pair needs runs of its own
#: before a retire lands (the gate makes a retire whose alone pair is
#: unfinished a proposal, never an automatic removal), and from halfway the
#: remaining in-situ runs leave it time to collect them.
ALONE_PAIR_FROM_PROGRESS = 0.5
#: A cell more runs on the current content cannot move toward removal: one
#: whose no-benefit or no-clear-effect was overruled by an agent-errored
#: trial or a run skipped as anomalous (gates.classify_cell's reason), or a
#: cannot-discriminate cell with at least this many counted runs on each
#: arm (under it one more run can still change the class), or an
#: `insufficient` cell at `max_runs_per_cell` pairs (`at_cap`, round 2's C1).
#: A parked cell (PARKED_CLASSES) is not blocking (round 1's M2): it only
#: does not vote, and the subject's other cells must stay measured.
BLOCKING_REASON = "no-benefit on the numbers, but the cell has"
BLOCKING_REASONS = (BLOCKING_REASON, "no-clear-effect on the numbers, but the cell has")
BLOCKING_CLASSES = ("cannot-discriminate",)
BLOCKING_MIN_RUNS = 3
#: The cell classes that are parked, not fired: harness/gates.py's
#: PARKED_CLASSES, copied because this module imports gates only lazily (its
#: lighter subcommands run where pyyaml is not installed);
#: test_issue_gate_round3.py pins the two equal.
PARKED_CLASSES = ("ceiling", "ceiling-unconfirmed", "paused")
#: The route of a work item listed only in the sweep's step summary (its
#: kind and count, `summary_lines`) and the plan JSON: `fixture-ceiling`,
#: `cell-at-cap`, `paused-unmeasured` and `paused-ceiling` (round 4's m1 and M1, round 6's M1). scripts/work_item_issues.py files issues
#: for its KINDS only, so routing these to `issue` promised one that never came.
SUMMARY_ROUTE = "summary"
IMPROVE_TRIALS = 3
#: Where an eligible guidance section's improvement runs when the fire
#: workflow's `section` pattern refuses its id.
GUIDANCE_IMPROVE_ROUTE = ("local run: scripts/propose_guidance_edit.py (the fire "
                          "workflow's section pattern refuses this id)")
#: A guidance fixture key, relative to evals/ (the proposer's listing).
GUIDANCE_FIXTURE_RE = re.compile(r"guidance/[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
                                 r"(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127})?")
#: The window `use` is counted over: skill_usage.weight's four weeks.
USE_WINDOW_DAYS = 28
#: Trials of a bare fire's one arm (routine-eval-weekly.yml sends them).
BARE_TRIALS = 3
#: An eval leg's one model id: the fire workflow's own shape check.
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
#: PAIR FIRES: each id of a pair fire, the routine payload contract's
#: pattern, which routine-eval-fire.yml checks too before it fires a pair.
PAIR_MODEL_RE = re.compile(r"claude-[a-z0-9][a-z0-9.-]{0,62}")
#: wait-slot: at most this many fires in flight, each counted in flight this
#: long per model after it started, polled once a minute. 10 and 10 minutes
#: for the allowance week ending 2026-11-09 17:00 UTC only (Adam,
#: 2026-11-07: run enough in parallel to use the week's remaining allowance):
#: at 6 and 20 minutes the first slim sweep found every slot held by fires
#: that had finished in about 5 minutes, which capped it near 9 fires an
#: hour. A routine eval run takes p50 3.5 and p90 17 minutes per model
#: (471 runs). Restore 3 and 20 minutes with evals/budget.yml's restore after
#: that reset.
MAX_IN_FLIGHT = 10
EVAL_FLIGHT = timedelta(minutes=10)
IMPROVE_FLIGHT = timedelta(hours=3)
POLL_SECONDS = 60
#: wait-slot: the whole sweep's dispatch legs share this much waiting, counted
#: from the plan (--sweep-started). The legs run one at a time, so 25 minutes
#: of waiting per leg kept the 2026-11-02 22:50 UTC sweep running until 04:30
#: and held every ingest's re-plan queued behind it. A leg past the budget
#: checks once and, while the cap is still full, skips its fire; the next
#: re-plan (after an ingest or the watchdog) plans that cell again, since an
#: undispatched cell has no fire run.
SWEEP_MAX_WAIT = 1500
#: watchdog (routine-eval-watchdog.yml): re-plan this long after the last
#: sweep when nothing else has started one, and this long after a fire's
#: hold ends, so the guard's own clock is past it. A fire that never pushes
#: results wakes no ingest, so without this nothing re-plans when its hold
#: frees the room (2026-11-01: a 15:55 UTC fire stalled the evals 16:11 to
#: 18:33 UTC). `check` mode, the schedule's, uses the newest finished
#: sweep's end as the anchor and never sleeps.
WATCHDOG_IDLE = timedelta(minutes=50)
WATCHDOG_MARGIN = timedelta(minutes=2)
WATCHDOG_MAX_WAIT = 3300
WEEKLY_WORKFLOW = "routine-eval-weekly.yml"
WATCHDOG_WORKFLOW = "routine-eval-watchdog.yml"
#: A skill-edit lesson's boost reaches its full x2 at this evidence count
#: (#657; module docstring, SKILL-EDIT LESSONS).
SKILL_EDIT_BOOST_CAP = 3
#: The trigger lane: a skill whose fresh usage weight (invocations over
#: skill_usage.weight's four weeks) is at most this rarely triggers at all.
TRIGGER_MAX_WEIGHT = 1
TRIGGER_SET = "trigger-eval-set.json"
#: DESCRIPTION TRIMS (skills-evals#687): the cap a trim meets
#: (propose_skill_edit.TRIM_MAX_CHARS), the fixtures it is measured on at
#: least (propose_skill_edit.MIN_FIXTURES; a test holds both equal), and the
#: registry's waiver file and class that mark a skill still to trim.
TRIM_MAX_CHARS = 400
TRIM_MIN_FIXTURES = 3
WAIVERS_FILE = "scripts/skills_waivers.yml"
LENGTH_WAIVER_CLASS = "length-limit"
#: Why no trim is planned when the waiver file cannot be read. Fixed text.
TRIMS_UNREAD = ("the adam-agentskills checkout's scripts/skills_waivers.yml is "
                "missing or unreadable, so no description trim is planned")
#: A hook candidate: at least this share of its SKILL.md body's non-blank
#: lines sits under a heading naming a checklist, rules or checks.
HOOK_RULE_SHARE = 0.5
HOOK_HEADING_RE = re.compile(r"\b(?:checklist|rules|checks)\b", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"(#{1,6})\s+(.*)")
STAMP = "%Y%m%dT%H%M%SZ"
# THE BATCH (module docstring): its policy, and its record on the results
# branch (written by routine-eval-weekly.yml's batch-publish job).
BATCH_KINDS = ("skill", "guidance")
BATCH_RECORD = "batches/current.json"
BATCH_SUBJECT_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
# The bands a batch restricts to its members; safety, recheck, improve and
# bare are not.
BATCH_BANDS = ("missing", "near", "focus", "guidance-rest")
BATCH_POLICY_KEYS = frozenset({"start", "period_days", "multiplier", "rates", "rate_window_days",
                               "pairs_per_cell", "cost_window_days"})
#: The files whose history is each kind's addition rate (`addition_histories`).
BATCH_SKILL_HISTORY = "scripts/plugin_layout.json"
BATCH_GUIDANCE_HISTORY = "agents-md/eval-coverage.yml"
#: A history shorter than this is no rate: the policy's constant is used.
BATCH_MIN_RATE_SPAN = timedelta(days=7)
#: Float slack on the budget test, so a sum of costs equal to the budget fits.
BATCH_BUDGET_SLACK = 1e-9


#: The PlanError for a malformed evals/unscheduled.yml or evals/scope-auto.yml
#: (compute_gates raises ValueError for either; round 4's m4).
SCHEDULE_FILES_MALFORMED = "evals/unscheduled.yml or evals/scope-auto.yml is malformed"


class PlanError(Exception):
    """The plan could not be made. Fixed text, never evidence content."""


class PlanStale(PlanError):
    """The plan went stale between the plan job and a dispatch leg: a fixture
    it named was unscheduled or held after planning (the eval-scope pass
    merged a pause). Refusing to fire is right, but it is a hold, not a
    failure: the leg skips and the next re-plan drops the cell."""


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp_time(stamp) -> datetime | None:
    try:
        return datetime.strptime(stamp, STAMP).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def fire_models(title: dict | None) -> int:
    """How many run_eval commands a fire of this parsed run title runs, one
    after the other: two for a pair fire (PAIR FIRES), else one."""
    return max(1, len(outcomes_mod.title_models(title)))


def pending_window(title: dict | None) -> timedelta:
    """How long an eval fire of this run title with no run yet holds its
    cells: PENDING_WINDOW for one model, the routine's per-model stop twice
    over plus the margin for a pair fire."""
    return routine_deadlines.deadline("eval", fire_models(title))


# ---------------------------------------------------------------------------
# Rule C: is a skill paused?

def pause(skill: str, records: list, prs: list, on_hold: list, now: datetime,
          changed_at: datetime | None, remeasured_after, key: str = "skill") -> str | None:
    """Why `skill` may not be attempted now, or None. `records` are
    improve_outcomes records, `prs` {skill, state, created_at, closed_at,
    merged_at} of `eval-improve/<skill>` pull requests, `on_hold` the titles
    of open `on-hold` issues and pull requests, `changed_at` the newest
    change to its content, fixtures or the roster, and `remeasured_after` a
    function of a time: whether a with-arm run of the skill landed after
    it. A guidance section passes `key="section"`: its records and its
    `eval-guidance-improve/<section>` pull requests carry `section`."""
    mine = [r for r in records if r[key] == skill]
    own_prs = sorted((p for p in prs if p[key] == skill),
                     key=lambda p: p["created_at"] or "")
    if any(p["state"] == "open" for p in own_prs):
        return "an improve pull request is open"
    token = re.compile(rf"(?<![A-Za-z0-9._-]){re.escape(skill)}(?![A-Za-z0-9._-])")
    if any(isinstance(t, str) and token.search(t) for t in on_hold):
        return "an open on-hold issue or pull request names it"
    if any(r["outcome"] == "pending" for r in mine):
        return "an attempt is in flight"
    failed = 0
    for record in reversed(mine):
        if record["outcome"] != "fire-failed":
            break
        failed += 1
    if failed > INFRA_RETRIES:
        last = outcomes_mod.parse_time(mine[-1]["at"])
        if now - last < COOLDOWN:
            return f"its fire failed {failed} times in a row; retrying after a cooldown"
    # Measured outcomes, in order: a rejection, or an acceptance and what its
    # pull request became.
    measured = []
    for record in mine:
        at = outcomes_mod.parse_time(record["at"])
        if record["outcome"] == "rejected":
            measured.append(("rejected", at))
        elif record["outcome"] == "accepted":
            pr = next((p for p in own_prs if outcomes_mod.parse_time(p["created_at"])
                       and outcomes_mod.parse_time(p["created_at"]) >= at), None)
            if pr is None:
                measured.append(("awaiting-pr", at))
            elif pr["merged_at"]:
                measured.append(("merged", outcomes_mod.parse_time(pr["merged_at"])))
            else:
                measured.append(("rejected", outcomes_mod.parse_time(pr["closed_at"]) or at))
    if not measured:
        return None
    kind, at = measured[-1]
    if kind == "awaiting-pr":
        return "an accepted candidate has no registry pull request yet"
    if kind == "merged":
        if not remeasured_after(at):
            return "an improvement merged; waiting for the with arm to be re-measured"
        return None
    streak = 0
    for kind, _ in reversed(measured):
        if kind != "rejected":
            break
        streak += 1
    if streak >= STOP_AFTER_REJECTIONS:
        if not (changed_at and changed_at > at) and now - at < STOP_FOR:
            return (f"{streak} rejections in a row; stopped until its content, a "
                    "fixture or the roster changes, or 90 days pass")
        return None
    if now - at < COOLDOWN:
        return "cooling down after a rejection"
    return None


def guidance_lane(section: str, records: list, prs: list, removals: list) -> str | None:
    """Why no guidance-improve fire may go for `section` because of ANOTHER
    section, or None: every guidance edit writes AGENTS.md and
    docs/guidance-impact.md in _agent-guidance, so a second open pull
    request would conflict once the first merged (the gate opens nothing
    while one is open). `records` are guidance-improve outcome records, `prs`
    the `eval-guidance-improve/<section>` pull requests, `removals` the
    sections with an open `retire-guidance/` pull request."""
    if any(p["state"] == "open" and p["section"] != section for p in prs) \
            or any(r != section for r in removals):
        return "another guidance-loop pull request is open in _agent-guidance"
    if any(r["outcome"] == "pending" and r["section"] != section for r in records):
        return "another guidance-improve attempt is in flight"
    if section in removals:
        return "a removal pull request for it is open in _agent-guidance"
    return None


# ---------------------------------------------------------------------------
# Rule A's evidence: train headroom and targets, from pooled with-arm trials.

def train_evidence(cells: dict, train: list) -> dict:
    """{pass_rate, headroom, with_trials, targets} over the train fixtures'
    cells. `cells` is gates.pool_cells' output: {(fixture, model): {"with":
    runs, "without": runs}}, each run with `trials` (gates.trial_record) and
    `timestamp`."""
    passed = total = 0
    by_check: dict = {}
    with_trials = 0
    for (fixture, _model), pool in cells.items():
        if fixture not in train:
            continue
        for role in ("with", "without"):
            for run in pool[role]:
                for trial in run["trials"]:
                    if not trial.get("scored") or trial.get("infrastructure") \
                            or not trial.get("checks"):
                        continue
                    for check, ok in trial["checks"].items():
                        entry = by_check.setdefault((fixture, check),
                                                    {"n": 0, "fails": 0, "passed_any": False})
                        entry["passed_any"] |= bool(ok)
                        if role == "with":
                            entry["n"] += 1
                            entry["fails"] += 0 if ok else 1
                    if role == "with":
                        with_trials += 1
                        passed += sum(1 for ok in trial["checks"].values() if ok)
                        total += len(trial["checks"])
    rate = passed / total if total else None
    targets = sorted(f"{fixture or '-'}:{check}" for (fixture, check), e in by_check.items()
                     if e["n"] >= TARGET_MIN_TRIALS and e["fails"] >= TARGET_MIN_FAILS
                     and e["fails"] / e["n"] >= TARGET_FAIL_RATE and e["passed_any"])
    return {"pass_rate": rate, "headroom": None if rate is None else 1 - rate,
            "with_trials": with_trials, "targets": targets}


def with_run_after(cells: dict, moment: datetime) -> bool:
    """Whether any pooled with-arm run of these cells is stamped after `moment`."""
    return any((_stamp_time(run["timestamp"]) or moment) > moment
               for pool in cells.values() for run in pool["with"])


# ---------------------------------------------------------------------------
# Rule D: the bands.

def fire_cost(cell: dict, ctx: dict) -> float:
    """A cell's fire at its historical cost (module docstring)."""
    reserve, ratio = ctx["reservation"], ctx.get("points_per_usd")
    usd = cell.get("usd_per_fire")
    if not ratio or usd is None:
        return reserve
    return min(reserve, max(ctx["overrun"], usd * ratio))


def bare_cost(cell: dict | None, ctx: dict) -> float:
    """A bare fire's reservation: one arm, BARE_TRIALS trials, at its cell's
    mean agent cost per arm trial (module docstring)."""
    reserve, ratio = ctx["reservation"], ctx.get("points_per_usd")
    usd = (cell or {}).get("usd_per_arm_trial")
    if not ratio or usd is None:
        return reserve
    return min(reserve, max(ctx["overrun"], usd * BARE_TRIALS * ratio))


def bare_items(ctx: dict) -> list:
    """Band 7's fires: one per ctx["bare"] entry, {fixture, model, skill},
    the in-place cells with no bare run yet."""
    weights = ctx["model_weights"]
    cells = {(c["fixture"], c["model"]): c for c in ctx["cells"]}
    items = []
    for entry in ctx.get("bare", []):
        weight = weights.get(entry["model"], 0.0)
        items.append({"mode": "eval", "arms": "bare", "fixture": entry["fixture"],
                      "model": entry["model"], "skill": entry["skill"], "holdout": "",
                      "cost": bare_cost(cells.get((entry["fixture"], entry["model"])), ctx),
                      "change_type": None, "weight": weight, "band": "bare",
                      "order": (-weight,)})
    return items


def model_costs(cells: list) -> dict:
    """Each roster model's median agent cost per arm trial over the cells
    that know one; a model with none known is absent (ordered last)."""
    known: dict = {}
    for cell in cells:
        if cell.get("usd_per_arm_trial") is not None:
            known.setdefault(cell["model"], []).append(cell["usd_per_arm_trial"])
    return {m: statistics.median(v) for m, v in known.items()}


def recheck_after(cell: dict) -> timedelta:
    """How long after its newest run a decided cell is re-checked: sooner
    for a high-stakes subject (evals/stakes.yml)."""
    return RECHECK_AFTER_HIGH if cell.get("stakes") == "high" else RECHECK_AFTER


def section_retire_progress(ctx: dict, section: str) -> float:
    """A guidance section's retire progress: the lowest `retire_progress`
    over its cells in ctx["cells"] (every cell, held ones too, as
    `guidance_focus` scores it), at the policy's retire level; 0 when it
    has no cell."""
    policy = ctx.get("guidance_policy") or {}
    level = policy.get("retire_confidence") or DEFAULT_RETIRE_CONFIDENCE
    progress = [retire_progress(c, level) for c in ctx["cells"] if c.get("section") == section]
    return min(progress, default=0.0)


def leans_to_removal(cell: dict, ctx: dict) -> bool:
    """Whether `cell`'s guidance section leans toward removal (THE ALONE
    PAIR): its in-situ verdict is `retire` (a `retire` or `shorten-or-merge`
    section verdict), or its retire progress is at least
    ALONE_PAIR_FROM_PROGRESS."""
    in_situ = cell.get("in_situ_verdict")
    if in_situ == "retire" or cell.get("verdict") in ("retire", "shorten-or-merge"):
        return True
    return section_retire_progress(ctx, cell["section"]) >= ALONE_PAIR_FROM_PROGRESS


def fire_arms(cell: dict, ctx: dict) -> str:
    """The `arms` of an eval fire on `cell`: `both` for a skill cell and for
    a guidance section leaning toward removal, `in-situ` for any other
    guidance cell (THE ALONE PAIR)."""
    if not cell.get("section"):
        return "both"
    return "both" if leans_to_removal(cell, ctx) else "in-situ"


#: The `arms` of a paired eval fire: both of a skill's arms, both guidance
#: pairs, or a guidance fixture's in-situ pair alone (THE ALONE PAIR). A
#: bare fire runs one arm and is not one.
PAIRED_ARMS = ("both", "in-situ")


def eval_item(cell: dict, ctx: dict) -> dict:
    """A paired eval fire on `cell`, without its band: what `eval_items`
    puts in a band and `probe_items` probes with. Its arms are `fire_arms`:
    both, or a guidance cell's in-situ pair alone."""
    return {"mode": "eval", "arms": fire_arms(cell, ctx), "fixture": cell["fixture"],
            "model": cell["model"],
            "skill": cell["skill"], "holdout": "", "cost": fire_cost(cell, ctx),
            "change_type": None, "weight": ctx["model_weights"].get(cell["model"], 0.0)}


def _level(block, field: str) -> float:
    """A confidence block's `field`, 0 when the block or value is absent."""
    value = block.get(field) if isinstance(block, dict) else None
    return float(value) if isinstance(value, (int, float)) \
        and not isinstance(value, bool) else 0.0


def retire_progress(cell: dict, level: float) -> float:
    """How near a guidance cell is to no-benefit, as a share of the decision
    level: its objective's no-help confidence (the remove test's level so
    far). The judge does not vote (harness/gates.py, 2026-11-03), so it is
    not read. An absent value is 0."""
    return _level(cell.get("objective"), "no_help_confidence") / level


def keep_progress(cell: dict, level: float) -> float:
    """How near a guidance cell is to benefit, as a share of the decision
    level: its objective's helps confidence (the keep test's level so far,
    per cell; the subject's keep family asks more of it)."""
    return _level(cell.get("objective"), "helps_confidence") / level


def _produces_item(cell: dict) -> bool:
    """Whether `eval_items` would plan a fire for this undecided cell: it
    is schedulable, its subject is not stakes `none`, and its fires have
    not come back empty (a fixture-broken item). A `pending` cell still
    counts: its fire may yet land a run, and dropping its section from the
    focus for one sweep would hand the slot to another."""
    return cell.get("schedulable", True) and cell.get("stakes", "normal") != "none" \
        and cell["class"] in ("missing", "insufficient") \
        and cell.get("empty_fires", 0) < BROKEN_AFTER_FIRES


def _blocking(cell: dict) -> bool:
    """A cell more runs on the current content cannot move: BLOCKING_REASON,
    a BLOCKING_CLASSES cell with BLOCKING_MIN_RUNS, or an undecided cell
    whose pairs reached `max_runs_per_cell` (gates' `at_cap`, round 2's C1:
    its window is frozen)."""
    return str(cell.get("reason") or "").startswith(BLOCKING_REASONS) \
        or (cell.get("at_cap") is True and cell["class"] == "insufficient") \
        or (cell["class"] in BLOCKING_CLASSES
            and (cell.get("with_counted") or 0) >= BLOCKING_MIN_RUNS
            and (cell.get("without_counted") or 0) >= BLOCKING_MIN_RUNS)


def guidance_focus(ctx: dict) -> tuple:
    """([{section, score}], {section: progress}) for the guidance focus,
    from the eval cells alone (module docstring, band 4). A section's score
    is max(min over its cells of retire progress, max over its cells of
    keep progress): it retires only when every cell clears, and keeps on
    one. Eligible: its verdict is still open (FOCUS_VERDICTS), some cell
    would plan a fire (`_produces_item`), no removal pull request is open
    for it (ctx["guidance_removal_prs"]) and no cell is blocking (every
    cell, held ones too). The top GUIDANCE_FOCUS_SECTIONS by score, then
    fewer cells (a smaller section is nearer a verdict for the same runs,
    deliberately), then more counted runs, then section id. `progress` maps
    each focused section to its place in that order, the side its score
    came from ("keep" or "retire") and the levels used."""
    policy = ctx.get("guidance_policy") or {}
    retire_level = policy.get("retire_confidence") or DEFAULT_RETIRE_CONFIDENCE
    benefit_level = policy.get("benefit_confidence") or DEFAULT_BENEFIT_CONFIDENCE
    removals = set(ctx.get("guidance_removal_prs") or ())
    members = batch_members(ctx)
    sections: dict = {}
    for cell in ctx["cells"]:
        if cell.get("section") and (members is None
                                    or ("guidance", cell["section"]) in members):
            sections.setdefault(cell["section"], []).append(cell)
    ranked = []
    for section, cells in sections.items():
        if section in removals or any(c.get("verdict") not in FOCUS_VERDICTS for c in cells) \
                or not any(_produces_item(c) for c in cells) or any(_blocking(c) for c in cells):
            continue
        retire = min(retire_progress(c, retire_level) for c in cells)
        keep = max(keep_progress(c, benefit_level) for c in cells)
        runs = sum((c.get("with_counted") or 0) + (c.get("without_counted") or 0) for c in cells)
        ranked.append((-max(retire, keep), len(cells), -runs, section, keep > retire))
    ranked.sort()
    # With a batch open its guidance members are the focus, however many.
    chosen = ranked if members is not None else ranked[:GUIDANCE_FOCUS_SECTIONS]
    return ([{"section": r[3], "score": -r[0]} for r in chosen],
            {r[3]: {"position": place, "side": "keep" if r[4] else "retire",
                    "retire_level": retire_level, "benefit_level": benefit_level}
             for place, r in enumerate(chosen)})


def _guidance_band(cell: dict, focused: dict, near_order: tuple) -> tuple:
    """(band, order) for an undecided guidance cell's fire: `focus` for a
    focused section, the higher-scored section first, then by the cell's
    own progress on the side the section's score came from (the binding
    cell first: lowest retire progress, or highest keep progress), then the
    cheaper model. Sections go first because the two sides' progress do not
    compare: a keep-side cell's would sort before every retire-side cell.
    `guidance-rest` for any other section, in the near band's order
    (`near_order`: fewest runs, then the cheaper model), so a missing cell
    leads. High stakes first in both."""
    rank, _least, price = near_order[:3]
    focus = focused.get(cell["section"])
    if focus is None:
        return "guidance-rest", near_order
    if focus["side"] == "keep":
        progress = -keep_progress(cell, focus["benefit_level"])
    else:
        progress = retire_progress(cell, focus["retire_level"])
    return "focus", (rank, focus["position"], progress, price)


# ---------------------------------------------------------------------------
# The two-week batch (module docstring, THE BATCH).

def load_batch_policy(path: Path) -> dict | None:
    """evals/batch-policy.yml, validated, or None when the file is absent:
    {start, period, multiplier, rates: {kind: per week}, rate_window,
    pairs_per_cell, cost_window}. `rates` are the fallback constants, used
    for a kind whose addition history is unreadable (`batch_rates`). Any
    other shape is a PlanError (fixed text)."""
    import yaml  # noqa: PLC0415
    if not path.exists():
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PlanError("the batch policy is unreadable") from exc
    bad = PlanError("the batch policy is malformed")
    if not isinstance(doc, dict) or set(doc) != BATCH_POLICY_KEYS:
        raise bad
    start = outcomes_mod.parse_time(doc["start"])
    period, multiplier, rates = doc["period_days"], doc["multiplier"], doc["rates"]
    windows = (doc["rate_window_days"], doc["cost_window_days"])
    pairs = doc["pairs_per_cell"]
    numbers = [multiplier, pairs, *(rates.values() if isinstance(rates, dict) else ())]

    def whole_days(value, low, high):
        return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high

    if start is None or not whole_days(period, 1, 60) \
            or not whole_days(windows[0], BATCH_MIN_RATE_SPAN.days, 365) \
            or not whole_days(windows[1], 1, 365) or not isinstance(rates, dict) \
            or set(rates) != set(BATCH_KINDS) \
            or any(not isinstance(n, (int, float)) or isinstance(n, bool)
                   or not math.isfinite(n) or n < 0 for n in numbers) \
            or multiplier <= 0 or pairs <= 0:
        raise bad
    return {"start": start, "period": timedelta(days=period), "multiplier": float(multiplier),
            "rates": {kind: float(rates[kind]) for kind in BATCH_KINDS},
            "rate_window": timedelta(days=windows[0]), "pairs_per_cell": float(pairs),
            "cost_window": timedelta(days=windows[1])}


def batch_sizes(policy: dict, rates: dict | None = None) -> dict:
    """Members per kind, the batch's target size: max(1, multiplier x weekly
    rate, half rounded up). `rates` are the measured ones (`batch_rates`);
    without them, the policy's constants."""
    rates = policy["rates"] if rates is None else rates
    return {kind: max(1, math.floor(policy["multiplier"] * rates[kind] + 0.5))
            for kind in BATCH_KINDS}


# ---------------------------------------------------------------------------
# The batch's measured inputs (Adam's 2026-11-03 decision, "Fit the batch to
# the budget": the rate is measured each period, and the batch takes as many
# subjects as fit the period's budget, most-used first).

def _git_out(root: Path, *args: str) -> str:
    """`git <args>` in `root`, its stdout; OSError or CalledProcessError
    when git cannot answer."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout


def history_versions(root: Path, path: str, parse) -> list:
    """[(commit time, names)] of every commit touching `path` in the checkout
    at `root`, oldest first, `names` being `parse(text)` of the file at that
    commit (an empty set where the commit deleted it). Raises PlanError when
    the history cannot be read: no checkout, a shallow one (its oldest commit
    would read as the file's first version), no commit of the file, or a
    version `parse` refuses."""
    unreadable = PlanError(f"the history of {path} is unreadable")
    try:
        if not (root / ".git").exists() \
                or _git_out(root, "rev-parse", "--is-shallow-repository").strip() != "false":
            raise unreadable
        # First parent: main's own versions, at the time each one landed.
        log = _git_out(root, "log", "--first-parent", "--format=%H %cI", "HEAD", "--", path)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise unreadable from exc
    versions = []
    for line in reversed(log.splitlines()):
        sha, _, stamp = line.partition(" ")
        when = outcomes_mod.parse_time(stamp)
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or when is None:
            raise unreadable
        try:
            text = _git_out(root, "show", f"{sha}:{path}")
        except subprocess.CalledProcessError:
            versions.append((when, frozenset()))  # deleted at this commit
            continue
        except OSError as exc:
            raise unreadable from exc
        try:
            versions.append((when, frozenset(parse(text))))
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            raise unreadable from exc
    if not versions:
        raise unreadable
    return sorted(versions, key=lambda version: version[0])


def layout_skills(text: str) -> set:
    """The skills adam-agentskills' scripts/plugin_layout.json lists, across
    its plugins (the ADR 0013 layout pin)."""
    doc = json.loads(text)
    out = set()
    for body in doc["plugins"].values():
        out.update(str(skill) for skill in body["skills"])
    return out


def guidance_gaps(guidance_dir: Path | None) -> list:
    """The ids of _agent-guidance's agents-md/eval-coverage.yml rows that are
    not `skipped` and have no fixture directory yet (`gap`), not `_`-prefixed:
    the sections the improve lane cannot see, since guidance_contexts lists
    only sections with fixtures. [] without a checkout or a readable file."""
    import yaml  # noqa: PLC0415
    if guidance_dir is None:
        return []
    path = Path(guidance_dir) / BATCH_GUIDANCE_HISTORY
    try:
        if path.is_symlink() or not path.is_file():
            return []
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(doc, list):
        return []
    return sorted(str(row["id"]) for row in doc
                  if isinstance(row, dict) and row.get("status") == "gap"
                  and isinstance(row.get("id"), str) and not row["id"].startswith("_"))


def coverage_sections(text: str) -> set:
    """The section ids of _agent-guidance's agents-md/eval-coverage.yml: one
    row per `##` heading of base.md and per file under agents-md/sections/,
    keyed by an id that never changes when a heading is reworded."""
    import yaml  # noqa: PLC0415
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError("not YAML") from exc
    return {str(row["id"]) for row in doc}


def addition_rate(versions: list, now: datetime, window: timedelta) -> dict | None:
    """Subjects added per week over the trailing `window` from `versions`
    ([(time, names)], oldest first): the names at `now` (the newest version
    at or before it) not in the baseline, the newest version at or before
    the window's start, over the weeks between. A file younger than the
    window is measured from its first version, over its own age, so a bulk
    import is that baseline, never a burst of additions. Names removed in
    the window are not subtracted: the batch sizes for what arrives. None
    when no version is at or before `now` or the span is under
    BATCH_MIN_RATE_SPAN (too short to be a rate)."""
    seen = [(t, names) for t, names in versions if t <= now]
    if not seen:
        return None
    start = now - window
    before = [(t, names) for t, names in seen if t <= start]
    since, base = (start, before[-1][1]) if before else seen[0]
    span = now - since
    if span < BATCH_MIN_RATE_SPAN:
        return None
    added = len(seen[-1][1] - base)
    weeks = span / timedelta(weeks=1)
    return {"rate": added / weeks, "added": added, "weeks": weeks, "since": _iso(since)}


def batch_rates(policy: dict, histories: dict, now: datetime) -> dict:
    """{kind: {rate, source, ...}}: each kind's measured addition rate
    (`addition_rate` over `histories[kind]`, the versions or a PlanError's
    text when unreadable), or the policy's constant with `source: policy`
    and the reason when it cannot be measured."""
    out = {}
    for kind in BATCH_KINDS:
        versions = histories.get(kind)
        measured = addition_rate(versions, now, policy["rate_window"]) \
            if isinstance(versions, list) else None
        if measured is not None:
            out[kind] = {**measured, "source": "measured"}
            continue
        reason = versions if isinstance(versions, str) else (
            "no history given" if versions is None
            else "the history is shorter than the shortest rate span")
        out[kind] = {"rate": policy["rates"][kind], "source": "policy", "reason": reason}
    return out


def addition_histories(registries: dict, guidance: Path | None) -> dict:
    """{kind: versions or the reason they are unreadable} for `batch_rates`:
    adam-agentskills' scripts/plugin_layout.json (skills) and
    _agent-guidance's agents-md/eval-coverage.yml (guidance sections), from
    the full-history checkouts the weekly workflow makes."""
    sources = {"skill": ((registries.get("adam-agentskills") or {}).get("path"),
                         BATCH_SKILL_HISTORY, layout_skills),
               "guidance": (guidance, BATCH_GUIDANCE_HISTORY, coverage_sections)}
    out = {}
    for kind, (root, path, parse) in sources.items():
        if not root:
            out[kind] = f"no checkout holds {path}"
            continue
        try:
            out[kind] = history_versions(Path(root), path, parse)
        except PlanError as exc:
            out[kind] = str(exc)
    return out


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and value >= 0


def _invocation_usd(directory: Path) -> float | None:
    """The dollars of the run_eval invocation that wrote one run directory
    (`routine-results/<run id>/<key>/<timestamp>`): each distinct run-level
    `usage` block's `cost_estimate.usd`, summed as ingest's `estimate` sums
    them; None when a summary there is unreadable or lacks one."""
    if directory.is_symlink() or not directory.is_dir():
        return None
    blocks = {}
    for path in guard._summary_paths(directory):
        summary = guard._load_summary(path)
        usage = summary.get("usage") if isinstance(summary, dict) else None
        estimate = usage.get("cost_estimate") if isinstance(usage, dict) else None
        usd = estimate.get("usd") if isinstance(estimate, dict) else None
        if not _number(usd):
            return None
        level = {key: value for key, value in usage.items() if key != "measured"}
        blocks[json.dumps(level, sort_keys=True)] = float(usd)
    return sum(blocks.values()) if blocks else None


def model_shares(tree: Path, dir_models: dict, doc: dict) -> dict | None:
    """PAIR FIRES: {model: its share of a routine run's points} for a run
    holding more than one model, or None when that cannot be told. Each run
    directory (one run_eval invocation) must hold one model, and its share
    is its dollars (`_invocation_usd`) over the estimate's `usd`, which the
    directories' dollars must add up to: the estimate's points are those
    dollars times one rate, so the split is exact."""
    total = doc.get("usd")
    if not _number(total) or total <= 0:
        return None
    usd: dict = {}
    for path, models in sorted(dir_models.items()):
        spent = _invocation_usd(tree / path)
        if len(models) != 1 or spent is None:
            return None
        (model,) = models
        usd[model] = usd.get(model, 0.0) + spent
    if not math.isclose(sum(usd.values()), total, rel_tol=1e-9, abs_tol=1e-12):
        return None
    return {model: value / total for model, value in usd.items()}


def pair_costs(records: list, tree: Path, now: datetime, window: timedelta) -> dict:
    """{roster model: mean allowance fraction per observation}: over the
    routine runs of the last `window` whose cost_estimate.json carries
    `points` and whose validated paired records (`records`,
    compute_gates.build_index's `runs` and `guidance_runs`, any content
    digest) are all on one model, their points over their observations. An
    observation is what the gate counts toward `max_runs_per_cell`: one
    paired run (a with run and a without run at one path), whatever its
    trial count, so a 3-trial run costs its own measured points. A guidance
    fire's `alone` pair is read for contrast, not counted in its cell, so
    only its `in_situ` pair is an observation. Judge and guard calls are in a
    run's points, so they are in the mean. A model with no such run is
    absent. A pair fire's run (PAIR FIRES) holds two models, one per run
    directory: its points are split by `model_shares`, and each model gets
    its share over its own directories' observations; a run that cannot be
    split (one directory holding two models, say) is left out."""
    runs: dict = {}
    for record in records:
        parts = str(record.get("path", "")).split("/")
        if parts[0] != guard.DEST_ROOT or len(parts) < 2:
            continue
        entry = runs.setdefault(parts[1], {"models": set(), "roles": {}, "dirs": {},
                                           "newest": None})
        entry["models"].add(record.get("model"))
        entry["dirs"].setdefault(record["path"], set()).add(record.get("model"))
        if record.get("pair") in (None, "in_situ"):
            entry["roles"].setdefault(record["path"], set()).add(record.get("role"))
        at = _stamp_time(record.get("timestamp"))
        if at is not None and (entry["newest"] is None or at > entry["newest"]):
            entry["newest"] = at
    points: dict = {}
    observations: dict = {}
    for run_id, entry in sorted(runs.items()):
        paired = {path: 1 for path, roles in entry["roles"].items()
                  if {"with", "without"} <= roles}
        count = sum(paired.values())
        if None in entry["models"] or count <= 0 \
                or entry["newest"] is None or not now - window <= entry["newest"] <= now:
            continue
        try:
            doc = json.loads((tree / guard.DEST_ROOT / run_id / "cost_estimate.json")
                             .read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, RecursionError):
            continue
        cost = doc.get("points") if isinstance(doc, dict) else None
        if not _number(cost):
            continue
        if len(entry["models"]) == 1:
            shares = {next(iter(entry["models"])): 1.0}
        else:
            shares = model_shares(tree, entry["dirs"], doc)
            if shares is None:
                continue
        for model, share in sorted(shares.items()):
            seen = sum(paired.get(path, 0) for path, models in entry["dirs"].items()
                       if model in models)
            if seen <= 0:
                continue
            points[model] = points.get(model, 0.0) + cost * share
            observations[model] = observations.get(model, 0) + seen
    return {model: points[model] / observations[model] for model in points}


def subject_cost(cells: list, costs: dict, pairs_per_cell: float,
                 cap: int | None = None) -> float | None:
    """A subject's expected cost to a verdict, in allowance fractions: over
    its cells with headroom (`_produces_item`: undecided, schedulable, not
    fixture-broken), each cell's model's measured mean cost per observation
    (the dearest measured model for one with none) times the observations
    it still needs: min(`pairs_per_cell`, `cap` - the gate's own count of
    its observations, `pairs`), at least 0. `cap` is the gate policy's
    `max_runs_per_cell` (None: no cap). None when no model's cost is
    measured."""
    if not costs:
        return None
    dearest = max(costs.values())
    total = 0.0
    for cell in cells:
        if not _produces_item(cell):
            continue
        remaining = pairs_per_cell
        if cap is not None:
            done = cell.get("pairs")
            done = done if isinstance(done, int) and not isinstance(done, bool) else 0
            remaining = min(remaining, cap - done)
        total += costs.get(cell["model"], dearest) * max(0.0, remaining)
    return total


def gate_cap(ctx: dict, kind: str) -> int | None:
    """`max_runs_per_cell` from evals/gate-policy.yml, as the verdict
    document carries it: its `guidance` block for a section (the `skills`
    block when the document has none), its `skills` block for a skill. None
    when absent."""
    block = (ctx.get("guidance_policy") if kind == "guidance" else None) or ctx.get("policy")
    cap = block.get("max_runs_per_cell") if isinstance(block, dict) else None
    return cap if isinstance(cap, int) and not isinstance(cap, bool) else None


def read_batch(tree: Path) -> dict | None:
    """The open batch's record from the results tree (BATCH_RECORD), or None
    when there is none. A record of any other shape is a PlanError: it is
    this planner's own output, so a bad one means something wrote over it."""
    path = tree / BATCH_RECORD
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise PlanError("the batch record is unreadable") from exc
    bad = PlanError("the batch record is malformed")
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise bad
    number, members = doc.get("number"), doc.get("members")
    if not isinstance(number, int) or isinstance(number, bool) or number < 1 \
            or not isinstance(members, list) \
            or outcomes_mod.parse_time(doc.get("started_at")) is None \
            or outcomes_mod.parse_time(doc.get("due_at")) is None:
        raise bad
    for member in members:
        if not isinstance(member, dict) or member.get("kind") not in BATCH_KINDS \
                or not isinstance(member.get("subject"), str) \
                or not BATCH_SUBJECT_RE.fullmatch(member["subject"]) \
                or not isinstance(member.get("joined"), int) \
                or isinstance(member.get("joined"), bool) \
                or not 1 <= member["joined"] <= number:
            raise bad
    return doc


def batch_subjects(ctx: dict) -> dict:
    """{(kind, subject): {status, rank, newest}} for every subject with a
    schedulable eval cell. Private skills are never listed (the record is
    public). Status, first match:
      decided  its verdict is closed (anything but FOCUS_VERDICTS) or a
               removal pull request is open for it;
      blocked  some cell is blocking (`_blocking`): more runs on the current
               content cannot move it;
      stalled  no cell would plan a fire (`_produces_item`: fixture-broken,
               every cell held or stakes `none`);
      open     otherwise.
    `rank` is 0 for a high-stakes subject, else 1; `newest` its newest run
    on any cell (None for never run)."""
    private = set(ctx.get("private_skills") or ())
    removal_skills = set(ctx.get("removal_prs") or ())
    removal_sections = set(ctx.get("guidance_removal_prs") or ())
    grouped: dict = {}
    for cell in ctx["cells"]:
        key = ("guidance", cell["section"]) if cell.get("section") else ("skill", cell["skill"])
        grouped.setdefault(key, []).append(cell)
    subjects = {}
    for (kind, name), cells in grouped.items():
        live = [c for c in cells if c.get("schedulable", True)]
        if not live or (kind == "skill" and name in private) \
                or not BATCH_SUBJECT_RE.fullmatch(name or ""):
            continue
        removal = name in (removal_sections if kind == "guidance" else removal_skills)
        if removal or any(c.get("verdict") not in FOCUS_VERDICTS for c in cells):
            status = "decided"
        elif any(_blocking(c) for c in cells):
            status = "blocked"
        elif not any(_produces_item(c) for c in live):
            status = "stalled"
        else:
            status = "open"
        stamps = [t for t in (_stamp_time(c.get("newest")) for c in cells) if t is not None]
        subjects[(kind, name)] = {
            "status": status, "newest": max(stamps) if stamps else None,
            "rank": 0 if any(c.get("stakes") == "high" for c in cells) else 1}
    return subjects


def batch_state(ctx: dict, now: datetime) -> dict | None:
    """The batch this plan works on, or None before the policy's start (or
    without a policy). Pure. Returns {record, started, status}: `record` is
    what BATCH_RECORD holds, `started` whether this plan began it (so the
    weekly workflow publishes it), `status` each member's status now.

    The previous record stays while some member is open and it is not yet
    due. Otherwise a new batch starts: the previous batch's open members
    first, in their order, keeping their `joined`; then `fit_batch` adds open
    subjects not already in it, up to each kind's target size
    (`batch_sizes` of ctx["batch_rates"], the measured addition rates) and
    within the batch budget (ctx["batch_budget"]). Decided, blocked, stalled
    and gone members are not carried: each ended on its own work item or
    verdict. When there is nothing to start (no carry and no pick) the
    previous record stays, so a finished batch with no candidates is not
    renumbered on every sweep."""
    policy = ctx.get("batch_policy")
    if not policy or now < policy["start"]:
        return None
    subjects = batch_subjects(ctx)
    previous = ctx.get("previous_batch")

    def status_of(member):
        return subjects.get((member["kind"], member["subject"]), {}).get("status", "gone")

    def described(record, started):
        return {"record": record, "started": started,
                "status": [{"kind": m["kind"], "subject": m["subject"], "status": status_of(m)}
                           for m in record["members"]]}

    old = previous["members"] if previous else []
    carry = [m for m in old if status_of(m) == "open"]
    if previous and carry and now < outcomes_mod.parse_time(previous["due_at"]):
        return described(previous, False)
    rates = ctx.get("batch_rates") or {
        kind: {"rate": policy["rates"][kind], "source": "policy",
               "reason": "no measured rate given"} for kind in BATCH_KINDS}
    sizes = batch_sizes(policy, {kind: rates[kind]["rate"] for kind in BATCH_KINDS})
    number = previous["number"] + 1 if previous else 1
    fit = fit_batch(ctx, subjects, carry, sizes, number)
    if previous and not carry and not fit["picks"]:
        return described(previous, False)
    record = {"schema_version": 1, "number": number, "started_at": _iso(now),
              "due_at": _iso(now + policy["period"]), "sizes": sizes,
              "multiplier": policy["multiplier"],
              "rates": {kind: rates[kind]["rate"] for kind in BATCH_KINDS},
              # Audit (Adam's 2026-11-03 decision): how each rate was had,
              # the budget and costs the fit used, and who waits.
              "rate_basis": rates, "fit": fit["fit"],
              "members": fit["carried"] + fit["picks"], "waiting": fit["waiting"],
              "previous": None if not previous else {
                  "number": previous["number"],
                  "members": [{"kind": m["kind"], "subject": m["subject"],
                               "status": status_of(m)} for m in old]}}
    return described(record, True)


def fit_batch(ctx: dict, subjects: dict, carry: list, sizes: dict, number: int) -> dict:
    """Fit a new batch to its budget (Adam's 2026-11-03 decision: "The batch
    takes as many subjects as fit 50 points, most-used first. The rest
    wait."). Pure. Returns {carried, picks, waiting, fit}.

    Carried members stay whatever they cost, and their cost counts first.
    The candidates, open subjects not carried, are ranked per kind. Skills:
    most used first (the usage weight, `neutral_weights` of
    ctx["skill_weights"]), then high stakes, then the longest without a run
    (never run first), then name. Guidance has no per-section use, so its
    sections rank high stakes first, then the longest without a run, then
    name. The kinds take turns, so neither kind's list starves the other. A
    candidate joins while its kind is under its target size and its expected
    cost (`subject_cost`, the remaining observations of its cells with
    headroom up to the gate's `max_runs_per_cell`) fits the room the budget
    has left (equal fits); one that
    alone would overflow the room is skipped, so a cheaper later one can
    still join. When no cost is measured (no ctx["batch_pair_costs"]) or no
    budget is known, the fit picks by target size alone and says so. When
    nothing at all would join while subjects wait, the cheapest candidate
    joins anyway (`floor`), so the batch is never empty while work waits."""
    policy = ctx["batch_policy"]
    budget = ctx.get("batch_budget")
    costs = ctx.get("batch_pair_costs") or {}
    pairs = policy.get("pairs_per_cell")
    by_subject: dict = {}
    for cell in ctx["cells"]:
        key = ("guidance", cell["section"]) if cell.get("section") else ("skill", cell["skill"])
        by_subject.setdefault(key, []).append(cell)
    priced = bool(costs) and budget is not None and pairs is not None

    def cost_of(kind, name):
        return subject_cost(by_subject.get((kind, name), []), costs, pairs,
                            gate_cap(ctx, kind)) if priced else None

    carried = [{"kind": m["kind"], "subject": m["subject"], "joined": m["joined"],
                "cost": cost_of(m["kind"], m["subject"])} for m in carry]
    spent = sum(m["cost"] or 0.0 for m in carried)
    taken = {(m["kind"], m["subject"]) for m in carry}
    open_skills = [name for (k, name), info in subjects.items()
                   if k == "skill" and info["status"] == "open"]
    weights = neutral_weights({**{name: None for name in open_skills},
                               **(ctx.get("skill_weights") or {})})
    floor_time = datetime.min.replace(tzinfo=timezone.utc)
    ranked = {}
    for kind in BATCH_KINDS:
        # Skills: most used first, then stakes. Guidance has no per-section
        # use, so stakes stay first there.
        ranked[kind] = [name for _w, _r, _n, name in sorted(
            (-(weights.get(name, 0.0) if kind == "skill" else 0.0), info["rank"],
             info["newest"] or floor_time, name)
            for (k, name), info in subjects.items()
            if k == kind and info["status"] == "open" and (k, name) not in taken)]
    room = {kind: sizes[kind] - sum(1 for m in carry if m["kind"] == kind)
            for kind in BATCH_KINDS}
    turns = [(kind, name) for i in range(max((len(v) for v in ranked.values()), default=0))
             for kind in BATCH_KINDS if i < len(ranked[kind]) for name in [ranked[kind][i]]]
    picks, waiting = [], []
    for kind, name in turns:
        cost = cost_of(kind, name)
        if room[kind] <= 0:
            waiting.append({"kind": kind, "subject": name, "cost": cost, "reason": "size"})
        elif priced and spent + cost > budget + BATCH_BUDGET_SLACK:
            waiting.append({"kind": kind, "subject": name, "cost": cost, "reason": "budget"})
        else:
            picks.append({"kind": kind, "subject": name, "joined": number, "cost": cost})
            spent += cost or 0.0
            room[kind] -= 1
    floor = False
    if not carried and not picks and waiting:
        # Never empty while subjects wait: the cheapest joins, over budget.
        cheapest = min(waiting, key=lambda w: (w["cost"] if w["cost"] is not None else 0.0))
        waiting.remove(cheapest)
        picks.append({"kind": cheapest["kind"], "subject": cheapest["subject"],
                      "joined": number, "cost": cheapest["cost"]})
        spent += cheapest["cost"] or 0.0
        floor = True
    # The record lists each kind's picks together, skills first, in the
    # order they joined.
    picks.sort(key=lambda m: BATCH_KINDS.index(m["kind"]))
    fit = {"budget": budget, "pairs_per_cell": pairs, "pair_costs": costs,
           "priced": priced, "total": spent if priced else None, "floor": floor}
    if not priced:
        fit["reason"] = ("no budget known" if budget is None
                         else "no cost per pair measured for any roster model")
    return {"carried": carried, "picks": picks, "waiting": waiting, "fit": fit}


def batch_members(ctx: dict) -> set | None:
    """{(kind, subject)} of the batch `build_plan` put in ctx["batch"], or
    None when no batch is active (every subject is measured as before)."""
    batch = ctx.get("batch")
    if not batch:
        return None
    return {(m["kind"], m["subject"]) for m in batch["record"]["members"]}


def eval_items(ctx: dict, now: datetime) -> tuple:
    """(fires by band, work items) for the eval cells. A subject (skill or
    guidance section) already kept plans no missing or near fire: one
    confident benefit keeps it, so more runs cannot change the verdict
    until its re-check. Within a band the cheaper model goes first (Adam,
    2026-10-31: Sonnet first, Opus only while the cheaper runs have not
    settled it), then the heavier-used model. An undecided guidance cell
    enters neither missing nor near: `focus` for a section of
    `guidance_focus`, `guidance-rest` otherwise (`_guidance_band`).

    A `ceiling` or `ceiling-unconfirmed` cell (harness/gates.py) plans no
    fire in any band but safety, re-checks included: it is a
    `fixture-ceiling` work item (none when its subject is kept), since only a
    harder fixture can let it vote. An `insufficient` cell whose pairs
    reached `max_runs_per_cell` (`at_cap`) plans no fire either: its window
    is frozen. It is a `cell-at-cap` work item carrying its gates reason
    (round 3's M3: it was a silent dead end; it is a step summary
    count, not an issue), and a decided cell at the cap is not re-checked
    (round 3's m5).

    CHEAPER MODEL FIRST (2026-11-03, the threshold sweep's adaptive
    allocation): in the missing, near, focus and guidance-rest bands a cell
    plans no fire while its subject's cell of the same fixture on a cheaper
    model (`model_costs`) is still open (`cheaper_first`). A keep there keeps
    the subject, and a removal needs both cells, so only the cost changes.

    A cell bound for the missing, near, recheck, focus or guidance-rest
    band with at least BROKEN_AFTER_FIRES `empty_fires` is a
    `fixture-broken` work item instead and enters no band: a refusal that keeps recurring (an upstream
    edit can cause one at any time) would otherwise re-fire it on every
    sweep. A safety cell is exempt, since a removal pull request must keep
    its evidence slot. A `pending` cell, whose last fire may still land a
    run, plans no fire in any band, safety included. Each of ctx["outages"]
    (a chain of outage fires) whose first start is within
    OUTAGE_REPORT_WINDOW is a `routine-outage` work item; its `sweep_start`
    is the chain's first start. While the routine is down
    (ctx["routine_down"], the time it went down), a `routine-down` item,
    `since` that time, is listed first on every plan, and `build_plan` sends
    at most one probe (`probe_items`) instead of these fires."""
    costs = model_costs(ctx["cells"])
    removal = {s for s in ctx["removal_prs"]}
    _focus, focused = guidance_focus(ctx)
    held = cheaper_first(ctx["cells"], costs)
    members = batch_members(ctx)
    bands = {band: [] for band in BANDS}
    work = []
    for cell in ctx["cells"]:
        if not cell.get("schedulable", True):
            continue  # an isolation, null-pin or private cell enters no band, safety included
        stakes = cell.get("stakes", "normal")
        if stakes == "none":
            continue  # a check enforces it; evals/stakes.yml names the check
        # High stakes go first in every band but safety.
        rank = 0 if stakes == "high" else 1
        item = eval_item(cell, ctx)
        price = costs.get(cell["model"], math.inf)
        least = min(cell["with_runs"], cell["without_runs"])
        newest = _stamp_time(cell["newest"])
        kept = cell.get("verdict") == "keep"
        due = newest is not None and now - newest >= recheck_after(cell)
        if not cell.get("section") and cell["skill"] in removal:
            band, order = "safety", ()
        elif cell["class"] in PARKED_CLASSES:
            # Parked (harness/gates.py PARKED_CLASSES): its without arm leaves
            # no room to show the margin, so no fire, re-checks included, can
            # move it. It needs a harder fixture, unless its subject is
            # already kept (round 2's m6: then nothing is asked of it).
            if not kept:
                parked = {"kind": "fixture-ceiling", "change_type": "fixture",
                          "skill": cell["skill"], "fixture": cell["fixture"],
                          "model": cell["model"], "route": SUMMARY_ROUTE}
                if cell.get("section"):
                    parked["section"] = cell["section"]
                work.append(parked)
            band, order = None, None
        elif cell.get("at_cap") is True and cell["class"] == "insufficient":
            # Round 2's C1: `max_runs_per_cell` pairs freeze the window, so
            # another fire cannot change the class. It is blocking instead,
            # and round 3's M3: a work item says so, since only new content
            # (or a person) can move it.
            if not kept:
                capped = {"kind": "cell-at-cap", "change_type": None,
                          "skill": cell["skill"], "fixture": cell["fixture"],
                          "model": cell["model"], "route": SUMMARY_ROUTE,
                          "reason": cell.get("reason")}
                if cell.get("section"):
                    capped["section"] = cell["section"]
                work.append(capped)
            band, order = None, None
        elif cell.get("at_cap") is True and cell["class"] != "missing":
            # Round 3's m5: a decided cell at the cap is not re-checked; a
            # new pair cannot enter its frozen window.
            band, order = None, None
        elif kept and cell["class"] in ("missing", "insufficient"):
            # More runs cannot change a keep, but its re-check still comes
            # due, or a kept subject with an unsettled cell would never be
            # tested again.
            band, order = ("recheck", (rank, newest.timestamp())) if due else (None, None)
        elif cell["class"] == "missing":
            band, order = (_guidance_band(cell, focused, (rank, least, price, -item["weight"]))
                           if cell.get("section") else ("missing", (rank, price, -item["weight"])))
        elif cell["class"] == "insufficient" and cell.get("section"):
            band, order = _guidance_band(cell, focused, (rank, least, price, -item["weight"]))
        elif cell["class"] == "insufficient":
            band, order = "near", (rank, least, price, -item["weight"])
        elif due:
            band, order = "recheck", (rank, newest.timestamp())
        else:
            band, order = None, None
        if band is None:
            continue
        subject = ("guidance", cell["section"]) if cell.get("section") \
            else ("skill", cell["skill"])
        if members is not None and band in BATCH_BANDS and subject not in members:
            continue  # THE BATCH: measured once its subject joins one
        if band in CHEAPER_FIRST_BANDS and id(cell) in held:
            continue  # its cheaper model's cell of the same fixture goes first
        if band != "safety" and cell.get("empty_fires", 0) >= BROKEN_AFTER_FIRES:
            broken = {"kind": "fixture-broken", "change_type": "fixture",
                      "skill": cell["skill"], "fixture": cell["fixture"],
                      "model": cell["model"], "route": "issue"}
            if cell.get("section"):
                broken["section"] = cell["section"]
            work.append(broken)
        elif not cell.get("pending"):
            bands[band].append({**item, "band": band, "order": order})
    # No fixture names: an outage is the routine's, not any fixture's, and
    # the step summary counts work items by kind.
    outages = [{"kind": "routine-outage", "change_type": None, "route": "issue",
                "sweep_start": _iso(outage["start"]), "fires": outage["fires"]}
               for outage in ctx.get("outages", [])
               if now - outage["start"] <= OUTAGE_REPORT_WINDOW]
    down = ctx.get("routine_down")
    if down:
        # Every plan while down, not only for OUTAGE_REPORT_WINDOW: an outage
        # can outlast its routine-outage item.
        outages.insert(0, {"kind": "routine-down", "change_type": None, "route": "issue",
                           "since": _iso(down)})
    return bands, outages + work + list(ctx.get("unmeasured") or [])


def unmeasured_items(gates_doc: dict, private: frozenset = frozenset()) -> list:
    """Round 4's M1: one `paused-unmeasured` work item (change type
    `fixture`, SUMMARY_ROUTE) per skill or guidance section whose verdict
    the gate marked `unmeasured`: every cell parked, and a fixture the eval
    scope pass paused shows no ceiling on its own runs. A paused fixture is
    off evals/scheduled.yml, so it has no planner cell and no
    `fixture-ceiling` item; without this the subject would sit
    `insufficient` with nothing asking for a resumed or harder fixture. A
    private skill gets none (the plan names only public subjects)."""
    out = []
    for half in ("skills", "guidance"):
        for name, verdict in sorted((gates_doc.get(half) or {}).items()):
            if not isinstance(verdict, dict) or verdict.get("unmeasured") is not True \
                    or (half == "skills" and name in private):
                continue
            item = {"kind": "paused-unmeasured", "change_type": "fixture",
                    "skill": name if half == "skills" else "", "route": SUMMARY_ROUTE,
                    "fixtures": sorted({c.get("fixture") or "" for c in verdict.get("cells", [])
                                        if c.get("class") == "paused"})}
            if half == "guidance":
                item["section"] = name
            out.append(item)
    return out


def paused_ceiling_items(gates_doc: dict, private: frozenset = frozenset()) -> list:
    """Round 6's M1: one `paused-ceiling` work item (change type `fixture`,
    SUMMARY_ROUTE) per skill or guidance section whose verdict is `ceiling`
    with a scope-paused cell among its cells (`paused_ceiling`). A paused
    fixture is off evals/scheduled.yml, so it has no planner cell and no
    `fixture-ceiling` item, and a skill whose fixtures are all paused is not
    in `skill_contexts` either; without this the subject would sit at
    `ceiling` with nothing asking for the harder fixture the verdict says it
    needs. A private skill gets none."""
    out = []
    for half in ("skills", "guidance"):
        for name, verdict in sorted((gates_doc.get(half) or {}).items()):
            if not isinstance(verdict, dict) or verdict.get("paused_ceiling") is not True \
                    or (half == "skills" and name in private):
                continue
            item = {"kind": "paused-ceiling", "change_type": "fixture",
                    "skill": name if half == "skills" else "", "route": SUMMARY_ROUTE,
                    "fixtures": sorted({c.get("fixture") or "" for c in verdict.get("cells", [])
                                        if c.get("class") == "paused"})}
            if half == "guidance":
                item["section"] = name
            out.append(item)
    return out


#: The bands where a cell waits for its cheaper model's cell (`eval_items`).
CHEAPER_FIRST_BANDS = ("missing", "near", "focus", "guidance-rest")
#: Pairs after which an undecided cheaper cell no longer holds its dearer
#: sibling (the review's M3): it may never decide, and the dearer model may
#: still show a keep.
CHEAPER_FIRST_MAX_PAIRS = 10


def cheaper_first(cells: list, costs: dict) -> set:
    """The `id()`s of the cells that wait (`eval_items`, CHEAPER MODEL
    FIRST): an open cell (missing or insufficient) whose subject has a cell
    of the same fixture on a model with a lower known cost (`costs`) that
    would still be fired (`_produces_item`: open, schedulable, not stakes
    `none`, its fires not coming back empty), is not BLOCKING (`_blocking`:
    more runs cannot move it) and has fewer than CHEAPER_FIRST_MAX_PAIRS
    pairs (gates' `pairs`). A cheaper cell that is decided in any other way
    (ceiling, no-clear-effect, cannot-discriminate, no-benefit) is not open,
    so it holds nothing either. With no cost known for either model,
    neither waits."""
    def subject(cell):
        return ("guidance", cell["section"]) if cell.get("section") else ("skill", cell["skill"])
    open_classes = ("missing", "insufficient")
    by_fixture: dict = {}
    for cell in cells:
        by_fixture.setdefault((subject(cell), cell["fixture"]), []).append(cell)
    held = set()
    for group in by_fixture.values():
        for cell in group:
            price = costs.get(cell["model"], math.inf)
            if cell["class"] in open_classes and any(
                    _produces_item(other) and not _blocking(other)
                    and (other.get("pairs") or 0) < CHEAPER_FIRST_MAX_PAIRS
                    and costs.get(other["model"], math.inf) < price
                    for other in group if other is not cell):
                held.add(id(cell))
    return held


def neutral_weights(raw: dict) -> dict:
    """Each skill's usage weight, an unknown one (None) given the median of
    the known positive weights, or 1.0 when there is none: neutral, never
    zero. A known 0 (a fresh census that never saw the skill) stays 0."""
    known = sorted(w for w in raw.values() if w is not None and w > 0)
    neutral = known[len(known) // 2] if known else 1.0
    return {skill: neutral if w is None else w for skill, w in raw.items()}


def lesson_boost(count: int) -> float:
    """The improve value multiplier for `count` skill-edit lessons: 1 with
    none, 2 at SKILL_EDIT_BOOST_CAP or more (module docstring)."""
    return 1 + min(max(count, 0), SKILL_EDIT_BOOST_CAP) / SKILL_EDIT_BOOST_CAP


def value_of(use, headroom, cost) -> float | None:
    """The potential value of an improvement: expected uses over the usage
    window times train headroom, per allowance point spent. None when any
    factor is unknown (headroom) or the cost is not positive: never a guess
    of 0."""
    if use is None or headroom is None or cost is None or cost <= 0:
        return None
    return use * headroom / cost


def cost_estimate(ctx: dict, subject: str, name: str) -> float | None:
    """What an improve run on a subject costs, in allowance points:
    IMPROVE_TRIALS times the sum over its fixtures of that fixture's mean
    `fire_cost` across its cells with a known cost. A fixture with no known
    cell adds nothing. None when no fixture has a known cost (or the
    points-per-dollar ratio is unknown)."""
    if not ctx.get("points_per_usd"):
        return None
    per_fixture: dict = {}
    for c in ctx.get("cells", []):
        mine = c.get("section") == name if subject == "guidance" \
            else not c.get("section") and c["skill"] == name
        if mine and c.get("usd_per_fire") is not None:
            per_fixture.setdefault(c["fixture"], []).append(fire_cost(c, ctx))
    if not per_fixture:
        return None
    return IMPROVE_TRIALS * sum(sum(v) / len(v) for v in per_fixture.values())


def retirement_owner(ctx: dict, name: str, skill: dict | None = None,
                     subject: str = "skill") -> str | None:
    """Why retirement owns skill `name`, or None. One rule for every lane that
    edits a skill or asks for work on it: the gates document's verdict
    (ctx["gate_verdicts"], which keeps a skill whose fixtures are all
    scope-paused) when gather supplied it, else `skill["verdict"]`; `retire`
    and `retire-pending` own it, and so does an open `retire-skill/<skill>`
    pull request (ctx["removal_prs"]), whatever the verdict now reads.

    With `subject="guidance"`, `name` is a guidance section and the same rule
    reads its verdict from `skill` (the section's ctx["guidance"] entry) and
    its open `retire-guidance/<section>` pull requests from
    ctx["guidance_removal_prs"]."""
    if subject == "guidance":
        verdict = (skill or (ctx.get("guidance") or {}).get(name, {})).get("verdict")
        removals = ctx.get("guidance_removal_prs")
    else:
        verdicts = ctx.get("gate_verdicts")
        verdict = (verdicts.get(name) if verdicts is not None
                   else (skill or ctx["skills"].get(name, {})).get("verdict"))
        removals = ctx.get("removal_prs")
    if verdict in ("retire", "retire-pending"):
        return f"owned by retirement ({verdict})"
    if name in (removals or ()):
        return "owned by retirement (open removal PR)"
    return None


def improve_items(ctx: dict, now: datetime) -> tuple:
    """(improve fires, work items, per-skill status, per-section guidance
    status, improve ranking). Candidates, skills and guidance sections, are
    ranked by value = use x headroom / cost (module docstring, THE BANDS
    item 5); improve fires and guidance work items follow that order, and
    needs-fixtures and needs-harder-fixtures items stay ordered by skill
    usage weight, heaviest first (`neutral_weights` of ctx["skill_weights"]),
    then train headroom."""
    raw = ctx.get("skill_weights") or {}
    weights = neutral_weights({name: raw.get(name) for name in ctx["skills"]})
    # The neutral use of anything unknown: the median `neutral_weights` gives
    # an unknown skill, from the skills alone.
    neutral = neutral_weights({**{n: raw.get(n) for n in ctx["skills"]}, "": None})[""]
    fires, work, status = [], [], {}
    candidates = []
    lessons = ctx.get("skill_edit_lessons") or {}
    for name, skill in sorted(ctx["skills"].items()):
        evidence = skill["evidence"]
        headroom = evidence["headroom"]
        reasons = []
        owner = retirement_owner(ctx, name, skill)
        if not skill["registry_ok"]:
            reasons.append("its fixtures do not all name adam-agentskills")
        if headroom is None or headroom < MIN_GAIN:
            reasons.append("no train headroom")
            if headroom is not None and skill["registry_ok"] and owner is None:
                work.append({"kind": "needs-harder-fixtures", "change_type": "fixture",
                             "skill": name, "fixtures": skill["fixtures"],
                             "headroom": headroom, "route": "issue"})
        if skill["fixtures"] < MIN_IMPROVE_FIXTURES:
            if not reasons and owner is None:
                work.append({"kind": "needs-fixtures", "change_type": "fixture",
                             "skill": name, "fixtures": skill["fixtures"],
                             "headroom": headroom, "route": "issue"})
            reasons.append(f"{skill['fixtures']} fixture(s), under {MIN_IMPROVE_FIXTURES}")
        if not evidence["targets"]:
            reasons.append("no failing check to target")
        if owner:
            reasons.append(owner)
        if not reasons and skill["pause"]:
            reasons.append(skill["pause"])
        status[name] = {"eligible": not reasons, "reasons": reasons, "headroom": headroom,
                        "fixtures": skill["fixtures"], "targets": len(evidence["targets"])}
        candidates.append({"subject": "skill", "name": name, "use": weights.get(name, neutral),
                           "use_known": raw.get(name) is not None, "headroom": headroom,
                           "cost": cost_estimate(ctx, "skill", name),
                           "eligible": not reasons, "reasons": reasons,
                           "fixtures": skill["fixtures"], "holdout": skill["holdout"],
                           "lessons": lessons.get(name, 0)})
    guidance_use = ctx.get("guidance_use")
    gstatus, gitems = {}, []
    for section, info in sorted((ctx.get("guidance") or {}).items()):
        headroom = info["evidence"]["headroom"]
        reasons = []
        if headroom is None or headroom < MIN_GAIN:
            reasons.append("no train headroom")
        if info["fixtures"] < MIN_IMPROVE_FIXTURES:
            reasons.append(f"{info['fixtures']} fixture(s), under {MIN_IMPROVE_FIXTURES}")
        owner = retirement_owner(ctx, section, info, subject="guidance")
        if owner:
            reasons.append(owner)
        if info.get("row_ok") is False:
            reasons.append("its eval-coverage.yml row is skipped or missing")
        if not reasons and info.get("pause"):
            reasons.append(info["pause"])
        gstatus[section] = {"eligible": not reasons, "reasons": reasons, "headroom": headroom,
                            "fixtures": info["fixtures"]}
        candidates.append({"subject": "guidance", "name": section,
                           "use": neutral if guidance_use is None else guidance_use,
                           "use_known": guidance_use is not None, "headroom": headroom,
                           "cost": cost_estimate(ctx, "guidance", section),
                           "eligible": not reasons, "reasons": reasons})
        gitems.append((section, info, headroom, reasons, owner))
    known = sorted(c["cost"] for c in candidates if c["cost"] is not None)
    fallback = (known[len(known) // 2] if len(known) % 2
                else (known[len(known) // 2 - 1] + known[len(known) // 2]) / 2) \
        if known else ctx["improve_charge"]
    ranking = []
    for c in candidates:
        cost = fallback if c["cost"] is None else c["cost"]
        base = value_of(c["use"], c["headroom"], cost)
        row = {"subject": c["subject"], "name": c["name"],
               "value": base, "use": c["use"],
               "use_known": c["use_known"], "headroom": c["headroom"], "cost": cost,
               "cost_known": c["cost"] is not None, "eligible": c["eligible"],
               "reasons": c["reasons"]}
        if c["subject"] == "skill":
            row["lesson_evidence"] = c["lessons"]
            if base is not None:
                row["value"] = base * lesson_boost(c["lessons"])
        ranking.append(row)
    ranking.sort(key=lambda r: (r["value"] is None, -(r["value"] or 0.0), r["name"]))
    value = {(r["subject"], r["name"]): r["value"] for r in ranking}
    for c in candidates:
        if c["subject"] == "skill" and c["eligible"]:
            v = value[("skill", c["name"])]
            fires.append({"mode": "improve", "arms": "", "fixture": "", "model": "",
                          "skill": c["name"], "holdout": c["holdout"],
                          "cost": ctx["improve_charge"], "change_type": "skill-edit",
                          "band": "improve", "value": v,
                          "order": (v is None, -(v or 0.0), c["name"])})
    work.sort(key=lambda w: (-weights.get(w["skill"], 1.0), -(w["headroom"] or 0.0), w["skill"]))
    # An eligible section is a guidance-improve fire, at most one per plan
    # (`guidance_lane`: a second open guidance edit would conflict), the
    # highest value first; a work item only when the fire workflow's section
    # pattern refuses its id.
    guidance_work, fired = [], None
    for section, info, headroom, reasons, owner in sorted(
            gitems, key=lambda g: (value[("guidance", g[0])] is None,
                                   -(value[("guidance", g[0])] or 0.0), g[0])):
        v = value[("guidance", section)]
        if not reasons and not outcomes_mod.SECTION_RE.fullmatch(section):
            guidance_work.append({
                "kind": "guidance-improve", "change_type": "guidance-edit",
                "section": section, "fixtures": info["fixtures"], "headroom": headroom,
                "value": v, "route": GUIDANCE_IMPROVE_ROUTE})
        elif not reasons and fired is not None:
            gstatus[section]["deferred"] = (f"one guidance-improve fire per plan; "
                                            f"{fired} ranks higher")
        elif not reasons:
            fired = section
            fires.append({"mode": "guidance-improve", "arms": "", "fixture": "", "model": "",
                          "skill": "", "section": section,
                          "holdout": info.get("holdout_fixture", ""),
                          "cost": ctx["improve_charge"], "change_type": "guidance-edit",
                          "band": "improve", "value": v,
                          "order": (v is None, -(v or 0.0), section)})
        elif headroom is not None and owner is None \
                and (headroom < MIN_GAIN or info["fixtures"] < MIN_IMPROVE_FIXTURES):
            # A section retirement owns (`retirement_owner`) gets no fixture
            # work. A paused section, or one whose manifest row is skipped,
            # still does when it lacks fixtures or headroom (as on the skill
            # side); whether it should is an open policy question.
            kind = "needs-harder-fixtures" if headroom < MIN_GAIN else "needs-fixtures"
            guidance_work.append({
                "kind": kind, "change_type": "fixture", "skill": "", "section": section,
                "fixtures": info["fixtures"], "headroom": headroom, "value": v,
                "route": "issue"})
    # A tracked section with no fixture at all (`guidance_gaps`: its manifest
    # row is not skipped) never reaches ctx["guidance"], so nothing above
    # asks for its first fixture; ask here, unless retirement owns it.
    for section in sorted(set(ctx.get("guidance_gaps") or ()) - set(ctx.get("guidance") or {})):
        if not outcomes_mod.SECTION_RE.fullmatch(section) \
                or retirement_owner(ctx, section, {}, subject="guidance"):
            continue
        gstatus[section] = {"eligible": False, "reasons": ["no fixtures yet"],
                            "headroom": None, "fixtures": 0}
        guidance_work.append({
            "kind": "needs-fixtures", "change_type": "fixture", "skill": "",
            "section": section, "fixtures": 0, "headroom": None, "value": None,
            "route": "issue"})
    guidance_work.sort(key=lambda w: (w["value"] is None, -(w["value"] or 0.0), w["section"]))
    return fires, work + guidance_work, status, gstatus, ranking


def hook_candidate(text: str) -> bool:
    """Whether a SKILL.md is mostly mechanical rules, so a git hook may
    serve better than a skill (Adam, 2026-10-26: hooks first). A cheap
    heuristic: at least HOOK_RULE_SHARE of the body's non-blank lines
    (frontmatter left out, fenced code counted) sit under a heading whose
    text has the word checklist, rules or checks, down to the next heading
    of the same or a higher level."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        ends = [i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"]
        lines = lines[ends[0] + 1:] if ends else lines
    total = under = 0
    fence, level = False, None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fence = not fence
        heading = None if fence else MARKDOWN_HEADING_RE.fullmatch(stripped)
        if heading:
            depth = len(heading.group(1))
            if level is not None and depth <= level:
                level = None
            if level is None and HOOK_HEADING_RE.search(heading.group(2)):
                level = depth
            continue
        if stripped:
            total += 1
            under += level is not None
    return bool(total) and under / total >= HOOK_RULE_SHARE


def gate_verdicts(gates_doc: dict) -> dict:
    """{skill: gate verdict} read from the gates document itself. Round 7's
    M1: `skill_contexts` drops a skill whose fixtures are all scope-paused,
    but the gate keeps those cells (`keep_paused`), so only the document
    knows such a skill is `retire`."""
    return {name: v.get("verdict") for name, v in (gates_doc.get("skills") or {}).items()
            if isinstance(v, dict)}


def trigger_items(ctx: dict, improve_skills=frozenset(), trim_skills=frozenset()) -> tuple:
    """(trigger fires, work items, hook candidates, per-skill status) for
    the trigger lane (module docstring, THE TRIGGER LANE; skills-evals#662).

    A skill of ctx["triggers"] (every adam-agentskills skill) is judged when
    its usage weight is known, so fresh, and it is not private (a private
    skill's name stays out of every public output, and its weight is never
    known anyway). A judged skill at most TRIGGER_MAX_WEIGHT and not owned
    by retirement gets an improve-band fire with `trigger_only` when
    evals/<skill>/trigger-eval-set.json exists, its own rule C pause
    (ctx["triggers"][skill]["pause"], absent read as None) is None and it is
    not in `improve_skills`, the skills with an ordinary improve fire in
    this plan, nor in `trim_skills`, those with a description trim (each
    would write `eval-improve/<skill>`); with no set it gets
    a `needs-trigger-set` work item instead. Any other judged skill gets
    neither, and its reasons are in the status. An unknown weight is neutral:
    nothing, and no status, so the weekly workflow never closes that
    skill's needs-trigger-set issue on a plan that could not see it.

    Fires sort after every value-ranked improve fire (`order` starts as an
    unknown-value improve fire's does, then infinity outranks any `-value`),
    least used first, then by name."""
    weights = ctx.get("skill_weights") or {}
    private = set(ctx.get("private_skills") or ())
    fires, work, status = [], [], {}
    for name, info in sorted(ctx.get("triggers", {}).items()):
        weight = weights.get(name)
        if weight is None or name in private:
            continue
        reasons = []
        if weight > TRIGGER_MAX_WEIGHT:
            reasons.append(f"used more than {TRIGGER_MAX_WEIGHT} time(s) in four weeks")
        # The gates document's verdict, not skill_contexts': that drops a
        # skill whose fixtures are all scope-paused, which the gate keeps.
        owner = retirement_owner(ctx, name)
        if owner:
            reasons.append(owner)
        path = f"evals/{name}/{TRIGGER_SET}"
        if not reasons and not info["trigger_set"]:
            work.append({"kind": "needs-trigger-set", "change_type": "fixture",
                         "route": "issue", "skill": name, "weight": weight,
                         "trigger_set": path, "hook_candidate": info["hook_candidate"]})
            reasons.append("no reviewed trigger set yet")
        if not reasons and info.get("pause"):
            reasons.append(info["pause"])
        if not reasons and name in improve_skills:
            reasons.append("an ordinary improve fire is planned for it")
        if not reasons and name in trim_skills:
            reasons.append("a description trim is planned for it")
        status[name] = {"eligible": not reasons, "reasons": reasons, "weight": weight}
        if not reasons:
            fires.append({"mode": "improve", "trigger_only": True, "arms": "", "fixture": "",
                          "model": "", "skill": name, "holdout": "",
                          "cost": ctx["improve_charge"], "change_type": "trigger",
                          "band": "improve", "value": None,
                          "order": (True, math.inf, weight, name)})
    work.sort(key=lambda w: (w["weight"], w["skill"]))
    hooks = sorted(name for name, info in ctx.get("triggers", {}).items()
                   if info["hook_candidate"] and name not in private)
    return fires, work, hooks, status


def trim_items(ctx: dict) -> tuple:
    """(trim fires, per-skill status, why none could be read or None) for
    DESCRIPTION TRIMS (module docstring; skills-evals#687).

    ctx["trims"] is {skill: {"chars"}} for every length-limit waiver of the
    adam-agentskills checkout (`trim_contexts`), or None (or absent) when
    the waiver file could not be read: no trim, and the plan says so. A
    private skill is skipped, so its name reaches no output. Every other
    waived skill gets a status; it is eligible when ctx["skills"] has it
    (public, with fixtures) with at least TRIM_MIN_FIXTURES fixtures all
    naming adam-agentskills, it is not owned by retirement, its description
    is not already within TRIM_MAX_CHARS (an unknown length does not block:
    the loop rejects a short one with no model call), its rule C pause
    (ctx["skills"][skill]["pause"], the ordinary improve fire's) is None,
    and no other waived skill of its plugin is `busy` (`trim_busy`) or has
    a trim planned earlier in this walk: one trim per plugin at a time.

    Fires sort before every value-ranked improve fire (`order` starts as a
    known-value fire's does, then minus infinity outranks any `-value`), by
    name."""
    trims = ctx.get("trims")
    if trims is None:
        return [], {}, TRIMS_UNREAD
    private = set(ctx.get("private_skills") or ())
    busy = {info.get("plugin") for info in trims.values() if info.get("busy")}
    busy.discard(None)
    fires, status = [], {}
    for name, info in sorted(trims.items()):
        if name in private:
            continue
        chars = info.get("chars")
        skill = ctx["skills"].get(name)
        reasons = []
        if skill is None:
            reasons.append("no public fixtures under evals/ to measure a trim on")
        else:
            if not skill["registry_ok"]:
                reasons.append("its fixtures do not all name adam-agentskills")
            if skill["fixtures"] < TRIM_MIN_FIXTURES:
                reasons.append(f"{skill['fixtures']} fixture(s), under {TRIM_MIN_FIXTURES}")
            owner = retirement_owner(ctx, name, skill)
            if owner:
                reasons.append(owner)
        if isinstance(chars, int) and chars <= TRIM_MAX_CHARS:
            reasons.append("already within the cap")
        if not reasons and skill["pause"]:
            reasons.append(skill["pause"])
        plugin = info.get("plugin")
        if not reasons and plugin in busy:
            reasons.append(f"another trim or improve attempt in plugin {plugin} is open or planned")
        status[name] = {"eligible": not reasons, "reasons": reasons, "chars": chars,
                        "planned": False}
        if not reasons:
            if plugin is not None:
                busy.add(plugin)
            fires.append({"mode": "improve", "trim_description": True, "arms": "",
                          "fixture": "", "model": "", "skill": name, "holdout": "",
                          "cost": ctx["improve_charge"], "change_type": "skill-edit",
                          "band": "improve", "value": None,
                          "order": (False, -math.inf, name)})
    return fires, status, None


def trim_work(status: dict, chosen: list, capped: list) -> list:
    """One `description-trim` work item per skill of `status` (trim_items),
    in name order, routed "fire" when `chosen` (this plan's fires) holds its
    trim and otherwise why not, and `status[skill]["planned"]` set in place.
    Not issue-routed: the plan's `trims` map is the record until every
    waived skill is trimmed or rejected."""
    fired = {i["skill"] for i in chosen if i.get("trim_description")}
    cut = {i["skill"] for i in capped if i.get("trim_description")}
    work = []
    for name, info in sorted(status.items()):
        if name in fired:
            route = "fire"
        elif info["reasons"]:
            route = info["reasons"][0]
        elif name in cut:
            route = "the improve cap is reached"
        else:
            route = "not planned this sweep (no room, or the routine is down)"
        info["planned"] = name in fired
        work.append({"kind": "description-trim", "change_type": "skill-edit",
                     "skill": name, "chars": info["chars"], "route": route})
    return work


def allocate(bands: dict, room: float, max_fires: int) -> list:
    """The fires that fit `room` points: safety first, then each band up to
    its minimum share of what is left, then the rest in band order."""
    for band in bands.values():
        band.sort(key=lambda i: (*i["order"], i["cost"], i["fixture"], i["model"], i["skill"]))
    chosen = []

    def take(item):
        chosen.append(item)
        bands[item["band"]].remove(item)

    for item in list(bands["safety"]):
        if len(chosen) < max_fires:
            take(item)
    left = room - sum(i["cost"] for i in chosen)
    after_safety = max(0.0, left)
    for band, share in SHARES:
        allowance = share * after_safety
        for item in list(bands[band]):
            if len(chosen) >= max_fires:
                break
            if item["cost"] <= allowance + guard.EPSILON and item["cost"] <= left + guard.EPSILON:
                take(item)
                allowance -= item["cost"]
                left -= item["cost"]
    for band in BANDS[1:]:
        for item in list(bands[band]):
            if len(chosen) >= max_fires:
                break
            if item["cost"] <= left + guard.EPSILON:
                take(item)
                left -= item["cost"]
    return chosen


def improve_capped(items: list, improve_state: dict | None) -> tuple:
    """(kept, cut) of the improve band's `items` under the improve cap
    (#572): walked in allocate's own order with a copy of the guard's counts,
    each item kept only when `allowance_guard.improve_cap` allows it with the
    earlier kept items counted, the test the guard applies to each fire in
    turn. With no `improve_state` (a hand-built ctx, the explorer) there is
    no cap."""
    if improve_state is None:
        return list(items), []
    state = {**improve_state,
             "improve_by_kind": dict(improve_state.get("improve_by_kind") or {})}
    kept, cut = [], []
    for item in sorted(items, key=lambda i: (*i["order"], i["cost"], i["fixture"],
                                             i["model"], i["skill"])):
        if guard.improve_cap(state, item["mode"]):
            state["improve_by_kind"][item["mode"]] = \
                state["improve_by_kind"].get(item["mode"], 0) + 1
            kept.append(item)
        else:
            cut.append(item)
    return kept, cut


def probe_blocked(ctx: dict, now: datetime) -> bool:
    """Whether a probe younger than PROBE_WAIT with no landed run yet holds
    the next one (#583): a cell's `pending_since` is its newest such fire.
    An older one no longer blocks: an eval run takes 4 to 12 minutes, so a
    probe that has landed nothing by then is very likely empty, and waiting
    out FIRE_RESULT_WINDOW would halve the probe rate for nothing."""
    return any(c.get("pending_since") is not None and now - c["pending_since"] < PROBE_WAIT
               for c in ctx.get("cells", []))


def probe_items(bands: dict, ctx: dict) -> list | None:
    """While the routine is down (#583), the candidate probes, best first,
    or None when there is no schedulable eval cell at all. A probe is a
    paired eval fire (`eval_item`), the only kind that can deliver and so
    end the outage, on ANY schedulable cell, in a band or not (settled and
    fixture-broken cells too; `stakes: none` never fires), minus cells with
    a pending fire. Ranked by fewest `empty_fires`, then the oldest
    `last_fire` (any fire on the cell, all history; never fired first), then
    band order (allocate's order within a band; cells in no band last).
    Probes never count (`down_fires`), so the ranking spreads the load and
    keeps a broken fixture from holding the head of the queue."""
    cells = [c for c in ctx.get("cells", [])
             if c.get("schedulable", True) and c.get("stakes", "normal") != "none"]
    if not cells:
        return None
    placed = {(i["fixture"], i["model"]): (index, i) for index, band in enumerate(BANDS)
              for i in bands[band] if i["mode"] == "eval" and i["arms"] in PAIRED_ARMS}
    floor = datetime.min.replace(tzinfo=timezone.utc)
    ranked = []
    for cell in cells:
        if cell.get("pending"):
            continue
        index, banded = placed.get((cell["fixture"], cell["model"]), (len(BANDS), None))
        item = banded or {**eval_item(cell, ctx), "band": "probe", "order": ()}
        ranked.append(((cell.get("empty_fires", 0), cell.get("last_fire") or floor, index,
                        item["order"], item["cost"], item["fixture"], item["model"],
                        item["skill"]), item))
    ranked.sort(key=lambda pair: pair[0])
    return [item for _, item in ranked]


def pair_fires(chosen: list, roster: list | None) -> list:
    """PAIR FIRES: `chosen` with each two eval fires that share a fixture and
    `arms` on two distinct models of `roster` made one fire, placed where
    the first of them was. Its `model` is "m1,m2" in roster order, its
    `cost` their sum, its `band` and `order` the first's, and its `cells`
    each model's band and cost. A group of more than two pairs its first
    two by roster order and leaves the rest single; any other fire, and
    every fire when `roster` is None, is kept as it is."""
    if not roster:
        return list(chosen)
    rank = {model: index for index, model in enumerate(roster)}
    groups: dict = {}  # (fixture, arms) -> positions in `chosen`, in order
    for position, item in enumerate(chosen):
        if item["mode"] == "eval" and item["model"] in rank \
                and PAIR_MODEL_RE.fullmatch(item["model"]):
            groups.setdefault((item["fixture"], item["arms"]), []).append(position)
    out = list(chosen)
    for positions in groups.values():
        pair = sorted(positions, key=lambda p: rank[chosen[p]["model"]])[:2]
        if len(pair) < 2 or chosen[pair[0]]["model"] == chosen[pair[1]]["model"]:
            continue
        cells = [chosen[p] for p in pair]
        first = min(pair)
        out[first] = {**chosen[first], "model": ",".join(c["model"] for c in cells),
                      "cost": sum(c["cost"] for c in cells),
                      "cells": [{"model": c["model"], "band": c["band"], "cost": c["cost"]}
                                for c in cells]}
        out[max(pair)] = None
    return [item for item in out if item is not None]


def build_plan(ctx: dict, now: datetime, max_fires: int = 30) -> dict:
    """The plan for `ctx` (see `gather`), as of `now`. Pure. While
    ctx["routine_down"] (#583) it holds improve and bare fires and plans at
    most one probe (`probe_items`): the first candidate that fits the room,
    else, with the guard's refresh, one that fits a reservation; none while
    `probe_blocked`. With no schedulable eval cell at all it plans normally
    (`probe_only` False)."""
    batch = batch_state(ctx, now)
    outside = 0
    if batch is not None:
        unbatched, _work = eval_items(ctx, now)
        ctx = {**ctx, "batch": batch}
    bands, work = eval_items(ctx, now)
    if batch is not None:
        # Cells a sweep without the batch would have queued in its bands.
        outside = sum(len(unbatched[b]) - len(bands[b]) for b in BATCH_BANDS)
    improve, needs, status, guidance_status, ranking = improve_items(ctx, now)
    # DESCRIPTION TRIMS: a skill with a trim fire gets no ordinary or
    # trigger-only improve fire (each writes `eval-improve/<skill>`).
    trim_fires, trim_status, trims_unread = trim_items(ctx)
    trim_skills = {i["skill"] for i in trim_fires}
    for name in trim_skills & {i["skill"] for i in improve if i["mode"] == "improve"}:
        status[name]["deferred"] = "a description trim is planned for it"
    improve = [i for i in improve if not (i["mode"] == "improve" and i["skill"] in trim_skills)]
    # Trigger-only and trim fires join the improve band before the cap, so
    # they count against it exactly as the guard counts them (improve mode).
    trigger_fires, triggers, hooks, trigger_status = trigger_items(
        ctx, {i["skill"] for i in improve if i["mode"] == "improve"}, trim_skills)
    improve_state = ctx.get("improve_state")
    improve, capped = improve_capped(trim_fires + improve + trigger_fires, improve_state)
    bands["improve"].extend(improve)
    bands["bare"].extend(bare_items(ctx))
    down = bool(ctx.get("routine_down"))
    probes = probe_items(bands, ctx) if down else None
    # With no schedulable eval cell at all there is nothing to probe with,
    # and holding the queue would idle it until a delivery that cannot
    # come: plan normally (`probe_only` False says so).
    probe_only = probes is not None
    if probe_only:
        # The circuit breaker (#583): one probe, or nothing while a younger
        # one may still land. Improve, guidance-improve and bare fires run
        # through the same routine (routine-eval-fire.yml), so an outage
        # empties them too; they wait in `unplanned` with everything else.
        chosen = []
        if not probe_blocked(ctx, now):
            limit = ctx["room"]
            fits = [i for i in probes if i["cost"] <= limit + guard.EPSILON]
            if not fits and ctx.get("refresh"):
                # The guard's refresh fire, below: at most one reservation.
                fits = [i for i in probes if i["cost"] <= ctx["reservation"] + guard.EPSILON]
            chosen = fits[:1]
        for item in chosen:
            if item in bands.get(item["band"], []):
                bands[item["band"]].remove(item)
    else:
        chosen = allocate(bands, ctx["room"], max_fires)
    if not probe_only and not chosen and ctx.get("refresh"):
        # The guard's one refresh fire (allowance_guard.refresh): only an
        # ingested eval run brings a newer account reading, and without one
        # the stale holds refuse every fire until the weekly reset (2026-11-01,
        # the loop sat idle from 06:26 to 10:30 UTC with room left). The first
        # eval fire in band order, at most one reservation.
        evals = {band: [i for i in items if i["mode"] == "eval"]
                 for band, items in bands.items()}
        chosen = allocate(evals, ctx["reservation"], 1)
        for item in chosen:
            bands[item["band"]].remove(item)
    # Improve fires last: a long improve run in flight never holds up evals.
    chosen.sort(key=lambda i: i["mode"] in IMPROVE_MODES)
    # PAIR FIRES: one fire for a fixture's two model cells.
    legs = pair_fires(chosen, ctx.get("roster_models"))
    fires = [{"slot": slot, "band": i["band"], "mode": i["mode"], "arms": i["arms"],
              "fixture": i["fixture"],
              # Per fixture, never per model: a pair's two cells share it.
              "eval_key": i["fixture"][len("evals/"):] if i["fixture"] else "",
              "model": i["model"], "skill": i["skill"], "section": i.get("section") or "",
              "holdout": i["holdout"],
              # A string, as the matrix carries it into the leg's env.
              "trigger_only": "true" if i.get("trigger_only") else "false",
              "trim_description": "true" if i.get("trim_description") else "false",
              "change_type": i["change_type"] or "measure", "cost": i["cost"],
              "value": i.get("value"),
              **({"cells": i["cells"]} if "cells" in i else {})}
             for slot, i in enumerate(legs)]
    return {"schema_version": 1, "generated_at": _iso(now), "room": ctx["room"],
            "reservation": ctx["reservation"], "improve_charge": ctx["improve_charge"],
            # The circuit breaker's state, for the step summary (#583):
            # down, and whether the plan held everything but one probe.
            "routine_down": down, "probe_only": probe_only,
            "points_per_usd": ctx.get("points_per_usd"), "fires": fires,
            "unplanned": {band: len(items) + (len(capped) if band == "improve" else 0)
                          for band, items in bands.items()},
            # Whether one more fire of each kind passed the improve cap
            # before this plan (#572); None without a cap.
            "improve_allowed": None if improve_state is None else
            {mode: guard.improve_cap(improve_state, mode) for mode in IMPROVE_MODES},
            "guidance_focus": guidance_focus(ctx)[0],
            # THE BATCH: None before the policy's start; `started` tells the
            # weekly workflow to publish `record` to BATCH_RECORD.
            "batch": None if batch is None else {**batch, "outside": outside},
            # Trims first (a fixed chore), then trigger items just before
            # improve's.
            "work": trim_work(trim_status, chosen, capped) + triggers + needs + work,
            "skills": status, "guidance": guidance_status, "improve_ranking": ranking,
            # THE TRIGGER LANE: every judged skill, the only ones whose
            # needs-trigger-set issue the weekly workflow may close.
            "triggers": trigger_status,
            # DESCRIPTION TRIMS: every waived public skill, until each is
            # trimmed (its waiver removed) or rejected.
            "trims": trim_status, "trims_unread": trims_unread,
            "hook_candidates": hooks, "real_work": ctx.get("real_work", []),
            # An eval leg sends no skill and no section, and only a
            # guidance-improve leg a section: the fire workflow refuses them
            # in any other mode.
            "matrix": {"include": [{**{k: f[k] for k in ("slot", "band", "mode", "arms",
                                                         "fixture", "eval_key", "model",
                                                         "holdout", "trigger_only",
                                                         "trim_description")},
                                    "skill": f["skill"] if f["mode"] == "improve" else "",
                                    "section": f["section"] if f["mode"] == "guidance-improve"
                                    else ""}
                                   for f in fires]}}


# ---------------------------------------------------------------------------
# Gathering the context. Everything below reads files, git or GitHub.

def _git_time(cwd: Path, *paths: str) -> datetime | None:
    """The newest commit time touching `paths` in the checkout at `cwd`."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", *paths], cwd=cwd,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return outcomes_mod.parse_time(out)


def _registry_time(registries: dict, skill: str) -> datetime | None:
    """The newest commit to the skill's directory in the adam-agentskills
    checkout, or None without one."""
    entry = registries.get("adam-agentskills")
    if not entry:
        return None
    root = Path(entry["path"])
    dirs = sorted(str(d.relative_to(root)) for d in root.glob(f"plugins/*/skills/{skill}")
                  if d.is_dir())
    return _git_time(root, *dirs) if dirs else None


def model_weights(tree: Path, models: list) -> dict:
    """Each roster model's share of the census counts (usage/latest.json:
    {model: {iso week: count}}), equal shares without a usable census."""
    try:
        doc = json.loads((tree / "usage" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        doc = None
    counts = {}
    for model in models:
        weeks = doc.get(model) if isinstance(doc, dict) else None
        counts[model] = sum(v for v in weeks.values() if isinstance(v, int)
                            and not isinstance(v, bool) and v > 0) \
            if isinstance(weeks, dict) else 0
    total = sum(counts.values())
    if not total:
        return {model: 1 / len(models) for model in models} if models else {}
    return {model: count / total for model, count in counts.items()}


def points_per_usd(tree: Path, gates_doc: dict, limits: dict) -> float | None:
    """Measured allowance points per agent dollar over the ingested routine
    runs that have both a measured delta and a known cost."""
    usd: dict = {}
    for verdict in gates_doc["skills"].values():
        for cell in verdict.get("cells", []):
            for runs in cell.get("runs", {}).values():
                for run in runs:
                    parts = str(run.get("path", "")).split("/")
                    if parts[0] == guard.DEST_ROOT and len(parts) > 1 \
                            and isinstance(run.get("cost_usd"), (int, float)):
                        usd[parts[1]] = usd.get(parts[1], 0.0) + run["cost_usd"]
    points = spent = 0.0
    for run_id, dollars in sorted(usd.items()):
        cost = guard.measured_cost(tree / guard.DEST_ROOT / run_id, limits)
        if cost is not None and dollars > 0:
            points += cost
            spent += dollars
    return points / spent if spent and points else None


def _fixture_subject(evals_dir: Path, fixture: str) -> tuple:
    """("skill", skill name) for a skill fixture, or ("guidance", section id)
    for a guidance-section fixture, `evals/guidance/<section>/<name>` with
    `subject: guidance` and that `section:` (compute_gates.expected_guidance)."""
    import yaml
    doc = yaml.safe_load((evals_dir.parent / fixture / "fixture.yaml").read_text(encoding="utf-8"))
    doc = doc if isinstance(doc, dict) else {}
    parts = fixture.split("/")
    if doc.get("subject") == "guidance":
        section = doc.get("section")
        if len(parts) != 4 or parts[1] != "guidance" or not isinstance(section, str) \
                or parts[2] != section or section.startswith("_"):
            raise PlanError("a scheduled guidance fixture is not under its section")
        return "guidance", section
    if doc.get("subject") == "any":
        return "any", None  # a real-work row: no skill cell, the skill planner skips it
    skill = doc.get("skill")
    if not isinstance(skill, str):
        raise PlanError("a scheduled fixture names no skill")
    return "skill", skill


HOLD_PRIVATE = "private, paused"
HOLD_GIT = "git too old for fleet hooks"
#: Where ingested routine runs land on the results branch (ADR 0010
#: decision 2; ingest_routine_results.DEST_ROOT).
ROUTINE_RESULTS = "routine-results"
_STAMP_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z")


def routine_git_version(results_tree: Path) -> str | None:
    """`harness.git_version` of the newest ingested routine summary that
    records one (a non-empty string), by the summary's `timestamp`, or None
    when none does. This is the Git the routine's arms run (#535), which the
    planner's own host does not show: the plan runs on an Actions runner."""
    import compute_gates  # noqa: PLC0415
    root = Path(results_tree) / ROUTINE_RESULTS
    newest = None
    if root.is_dir():
        for path in root.rglob("summary.json"):
            doc = compute_gates._read(path)
            if not isinstance(doc, dict) or not isinstance(doc.get("harness"), dict):
                continue
            version, stamp = doc["harness"].get("git_version"), doc.get("timestamp")
            if not (isinstance(version, str) and version and isinstance(stamp, str)
                    and _STAMP_RE.fullmatch(stamp)):
                continue
            if newest is None or (stamp, str(path)) > newest[:2]:
                newest = (stamp, str(path), version)
    return newest[2] if newest else None


def fixture_hold_reason(directory: Path, routine_git: str | None = None, *,
                        check_git: bool = True) -> str | None:
    """Why the planner refuses to schedule the fixture in `directory`, or
    None when it may be. Adam, 2026-11-02: an isolation pair never pools
    (harness/gates.py pool_cells needs a tested digest and an arm context), so
    a skill fixture with no `context:` mapping ("no context") or a null
    `guidance_revision` pin ("null pin") is held, and a private-registry
    fixture ("private, paused") waits for a private context. A guidance or
    real-work fixture runs in situ and needs no context.

    A fixture that opts into the fleet hooks (`fleet_hooks:` present and not
    false; ADR 0012, fleet hooks addendum, #535) is held ("git too old for
    fleet hooks") unless `routine_git`, the routine's Git as its newest
    ingested summary records it (`routine_git_version`), is Git 2.54 or
    later, which config-based hooks need (run_eval.git_supports_fleet_hooks).
    No recorded version holds. The harness refuses such a run too
    (`git_too_old_for_fleet_hooks`), but only after the fire is spent, and
    two empty fires make the cell fixture-broken. `check_git=False` skips
    this hold, for a caller that has no results tree (`validate_fire`)."""
    import yaml  # noqa: PLC0415
    try:
        doc = yaml.safe_load((directory / "fixture.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        doc = None
    doc = doc if isinstance(doc, dict) else {}
    if doc.get("registry") == PRIVATE_REGISTRY_URL:
        return HOLD_PRIVATE
    if check_git and doc.get("fleet_hooks", False) is not False:
        import run_eval  # noqa: PLC0415
        if not run_eval.git_supports_fleet_hooks(routine_git):
            return HOLD_GIT
    if doc.get("subject") in ("guidance", "any"):
        return None
    if not isinstance(doc.get("context"), dict):
        return "no context"
    if doc["context"].get("guidance_revision") is None:
        return "null pin"
    return None


def real_work_rows(evals_dir: Path) -> list:
    """The scheduled `subject: any` fixtures: real-work rows the skill planner
    does not plan."""
    committed = schedule.committed_fixtures(evals_dir.parent)
    scheduled = schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    return [f for f in scheduled if _fixture_subject(evals_dir, f)[0] == "any"
            and fixture_hold_reason(evals_dir.parent / f) != HOLD_PRIVATE]


def fire_sweeps(starts, gap: timedelta = OUTAGE_GAP) -> list:
    """Group fire start times into sweeps: sorted, and a start at most `gap`
    (inclusive) after the previous start joins its sweep, else opens a new
    one, however long the chain runs. The planner chains its outage fires
    into reported outages with it, explorer_data (#573) its fires without
    results."""
    sweeps: list = []
    for start in sorted(starts):
        if sweeps and start - sweeps[-1][-1] <= gap:
            sweeps[-1].append(start)
        else:
            sweeps.append([start])
    return sweeps


def _landed_runs(cell: dict | None) -> list | None:
    """The start-of-run times of every run of the cell on its model, any role
    or digest (gates' `run_stamps_on_model`), or None when unknown: the key
    is absent (a verdict document from before it), not a list, or holds an
    unreadable stamp. A cell the verdict document does not list has none."""
    if cell is None:
        return []
    raw = cell.get("run_stamps_on_model")
    if not isinstance(raw, list):
        return None
    times = [_stamp_time(stamp) for stamp in raw]
    return None if None in times else times


def eval_cells(evals_dir: Path, gates_doc: dict, fire_runs: list, now: datetime,
               routine_git: str | None = None) -> list:
    """The cells of `eval_cells_and_outages`."""
    return eval_cells_and_outages(evals_dir, gates_doc, fire_runs, now, routine_git)[0]


def judge_empty_fires(fires: list, since: datetime) -> list:
    """The outage verdict of each of `fires`, (start, state, cell index)
    tuples with state young, delivered or empty, in the same order: None for
    a fire that is not empty or started before `since` (its window may reach
    past the fires gathered), else one of
      * "undecided": a young fire started inside its window, so the window
        may yet hold a delivered one; it counts neither way until then;
      * "outage": no delivered fire inside its window that started before
        the window's first empty fire start + PROBE_WAIT (a later one may be
        the breaker's own probe), and the window's empty fires cover at
        least OUTAGE_CELLS distinct cells; or a counted fire at most
        OUTAGE_GAP before an outage fire with no delivered fire started
        between the two (a chain absorbs its leading empties, slow onset);
      * "counted": anything else, a delivered fire beside it or a window
        narrower than OUTAGE_CELLS cells.
    The window is [start - OUTAGE_GAP, start + OUTAGE_GAP], inclusive, so a
    verdict depends only on fires near the fire (#583): it cannot move when
    a fire hours away ages out or its cell leaves the plan. Every empty fire
    is at least FIRE_RESULT_WINDOW old, longer than OUTAGE_GAP, so every
    fire that will ever start inside its window already has."""
    verdicts = []
    for start, state, _ in fires:
        if state != "empty" or start < since:
            verdicts.append(None)
            continue
        near = [(t, other, index) for t, other, index in fires if abs(t - start) <= OUTAGE_GAP]
        states = {other for _, other, _ in near}
        first = min(t for t, other, _ in near if other == "empty")
        if "young" in states:
            verdicts.append("undecided")
        elif not any(other == "delivered" and t < first + PROBE_WAIT for t, other, _ in near) \
                and len({index for _, other, index in near if other == "empty"}) >= OUTAGE_CELLS:
            verdicts.append("outage")
        else:
            verdicts.append("counted")
    first_pass = list(verdicts)
    for i, (start, _, _) in enumerate(fires):
        if verdicts[i] == "counted" and any(
                v == "outage" and start < t <= start + OUTAGE_GAP
                and not any(s == "delivered" and start <= d <= t for d, s, _ in fires)
                for (t, _, _), v in zip(fires, first_pass)):
            verdicts[i] = "outage"
    return verdicts


def eval_cells_and_outages(evals_dir: Path, gates_doc: dict, fire_runs: list,
                           now: datetime, routine_git: str | None = None) -> tuple:
    """(cells, outages, routine down). One cell per scheduled fixture x
    roster model, with its gates class, run counts, newest run, mean cost
    per run, `empty_fires`, `outage_fires`, `down_fires`, `pending`,
    `pending_since`, `last_fire`, and
    `schedulable` with its `hold_reason` (fixture_hold_reason, given
    `routine_git`, the routine's recorded Git). A held cell
    stays in the list for the cost statistics; `eval_items` plans none of
    it. A `subject: any` row makes no cell (`real_work_rows` lists it). Each
    outage is {"start", "fires"}: a maximal chain of outage fires, each at
    most OUTAGE_GAP after the one before, its first start and how many
    outage fires it holds. Routine down is when the routine went down, or
    None while it is up (ROUTINE DOWN below).

    A cell is UNKNOWN when its gates cell lacks `newest_on_model` or
    `run_stamps_on_model` (a verdict document from before them) or either
    holds an unreadable stamp. It counts 0 for every fire count, fails safe,
    never fixture-broken on a guess, and its fires take no part in any
    window. A cell the verdict document does not list has no run at all: it
    is known, with no bound.

    FIRE STATES. Every successful non-bare eval fire on a known cell that
    started at or after EMPTY_FIRES_SINCE and within RETRY_AFTER +
    OUTAGE_GAP, and every successful or still running one younger than
    FIRE_RESULT_WINDOW, is exactly one of: young (younger than
    FIRE_RESULT_WINDOW), delivered (the cell has a run stamped inside
    [start, start + FIRE_RESULT_WINDOW]) or empty. The state never changes
    once the fire is old enough: a later retry's run falls outside an
    earlier fire's window. The fires gathered reach OUTAGE_GAP past
    RETRY_AFTER so that every candidate's window is whole.

    OUTAGES (#583). Each empty fire within RETRY_AFTER is judged on its own
    window of OUTAGE_GAP either side of its start, over every classified
    fire of every known cell (`judge_empty_fires`): undecided while a young
    fire is in it, an OUTAGE fire when no delivered fire is in it and its
    empty fires cover at least OUTAGE_CELLS distinct cells (a routine
    outage empties every fire at once and says nothing about any one
    fixture), else counted. A window narrower than OUTAGE_CELLS cells cannot
    be told from broken fixtures, so it counts, unless the routine was down
    (`down_fires`).

    DOWN SPANS (#583, `down_intervals`): the routine was down from the start
    of each outage fire, as judged now, until the start of the next
    delivered paired eval fire on a known cell (a young fire that has landed
    its run included). Probes sent while down never count: an empty fire
    that started inside a down span is a DOWN fire (`is_down_fire`) when it
    is not an outage fire, or is one at least PROBE_WAIT after the span
    opened. Without this a lone probe, a one-cell window, always counted,
    which benched healthy cells across back-to-back outages (the same two
    head-of-band cells drew the empty probes on 2026-10-31 and 2026-11-01).

      * `empty_fires`: the cell's candidates, empty fires that started after
        gates' `newest_on_model` (no bound when it is None: no run on its
        model) and within RETRY_AFTER, that are counted: not down fires,
        and not outage fires, or outage fires past the cell's
        OUTAGE_EXCUSES. The bound is the
        newest run of ANY role or digest on that model, not the pooled
        newest: a fire that landed a run that does not pool still produced
        something.
      * `outage_fires`: the candidates excused as outage fires, at most
        OUTAGE_EXCUSES per cell, its earliest. The backstop: a cell empty in
        outage after outage still reaches BROKEN_AFTER_FIRES, one fire
        later, so broken fixtures that fail together are not retried
        forever. An undecided candidate is in no count until it is decided.
      * `down_fires`: the candidates that are down fires, in neither count
        above.
      * `pending`: a successful or still running non-bare eval fire that
        started after the bound and less than its `pending_window` ago
        (PENDING_WINDOW, longer for a pair fire), so its run may still
        land. On an unknown cell any such fire is pending: holding a cell
        for at most that window is cheaper than a second fire. Past it the
        routine has stopped, so the cell is planned again.
      * `pending_since`: the start of the newest fire started after the
        bound and less than FIRE_RESULT_WINDOW ago, else None; one younger
        than PROBE_WAIT holds the next probe (`probe_blocked`).
      * `last_fire`: the start of the cell's newest successful or running
        eval fire of any arms and age, else None, for the probe order.

    ROUTINE DOWN (the circuit breaker, #583): the last down span is still
    open, so routine down is its opening; or else, provisionally and for
    the breaker only, `provisional_trip`'s window of fires PROBE_WAIT old
    with nothing landed, so a burst into an outage trips the breaker in
    under an hour instead of FIRE_RESULT_WINDOW. An empty probe does not
    end it: only a delivery does, and `build_plan` fires one probe at a
    time until one does.

    A refused run counts as empty: routine-eval-fire.yml concludes `success`
    once the fire API accepts, so fixture-broken means "no run after n
    fires", whatever the cause."""
    committed = schedule.committed_fixtures(evals_dir.parent)
    scheduled = schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    finished: dict = {}
    young: dict = {}
    held: dict = {}  # (cell, start): how long that young fire holds the cell
    latest: dict = {}  # each cell's newest successful or running fire, any arms, any age
    for run in fire_runs:
        title = outcomes_mod.parse_title(run.get("display_title"))
        started = outcomes_mod.parse_time(run.get("run_started_at") or run.get("created_at"))
        if not (title and title["mode"] == "eval" and title["model"] and started):
            continue
        running = run.get("status") not in (None, "completed")
        # A pair fire (PAIR FIRES) is a fire of each of its two cells: each
        # is young, pending, delivered or empty on its own model's runs.
        for model in outcomes_mod.title_models(title):
            key = (title["target"], model)
            if running or run.get("conclusion") == "success":
                latest[key] = max(latest.get(key, started), started)
            # A bare fire runs one arm, never the cell's pair: neither empty nor pending.
            if title["bare"]:
                continue
            if now - started < FIRE_RESULT_WINDOW:
                if running or run.get("conclusion") == "success":
                    young.setdefault(key, []).append(started)
                    held[key, started] = max(held.get((key, started), PENDING_WINDOW),
                                             pending_window(title))
            elif run.get("conclusion") == "success" \
                    and now - started <= RETRY_AFTER + OUTAGE_GAP \
                    and started >= EMPTY_FIRES_SINCE:
                finished.setdefault(key, []).append(started)
    table = stakes_mod.load(evals_dir / "stakes.yml", evals_dir)
    cells = []
    fires: list = []  # (start, state, cell index) of every classified fire
    early: list = []  # young fires that have already landed a run
    stale: list = []  # (start, cell index): young fires PROBE_WAIT old with no run yet
    candidates: list = []  # per cell, its candidates' starts, earliest first
    all_landed: list = []  # per cell x model visited, its landed run times
    for fixture in scheduled:
        subject, ident = _fixture_subject(evals_dir, fixture)
        if subject == "any":
            continue  # a real-work row is not a skill cell
        hold = fixture_hold_reason(evals_dir.parent / fixture, routine_git)
        parts = fixture.split("/")
        if subject == "guidance":
            # Pooled by section (results/guidance/<id>/...), in-situ cells.
            skill, section, name = "", ident, parts[3]
            verdict = (gates_doc.get("guidance") or {}).get(section, {})
        else:
            skill, section = ident, None
            name = parts[2] if len(parts) == 3 else None
            verdict = gates_doc["skills"].get(skill, {})
        for model in gates_doc["roster_models"]:
            cell = next((c for c in verdict.get("cells", [])
                         if c.get("fixture") == name and c.get("model") == model), None)
            runs = cell.get("runs", {}) if cell else {}
            entries = [r for role in ("with", "without") for r in runs.get(role, [])]
            stamps = sorted({r["timestamp"] for r in entries})
            cost = cell.get("cost_usd") if cell else None
            arm_trials = sum(r.get("scored_trials") or 0 for r in entries)
            newest = stamps[-1] if stamps else None
            cls = cell["class"] if cell else "missing"
            raw = cell.get("newest_on_model") if cell else None
            bound = _stamp_time(raw)
            landed = _landed_runs(cell)
            all_landed.append(landed or [])
            # An unreadable stamp is as unknown as an absent key.
            known = landed is not None and (cell is None or (
                "newest_on_model" in cell and (raw is None or bound is not None)))
            waiting = [t for t in young.get((fixture, model), [])
                       if not known or bound is None or t > bound]
            mine: list = []
            if known:
                index = len(cells)
                for t in young.get((fixture, model), []):
                    fires.append((t, "young", index))
                    if any(r >= t for r in landed):
                        early.append(t)  # its run is in: the routine delivered
                    elif now - t >= PROBE_WAIT:
                        stale.append((t, index))
                for t in finished.get((fixture, model), []):
                    if any(t <= r <= t + FIRE_RESULT_WINDOW for r in landed):
                        fires.append((t, "delivered", index))
                        continue
                    fires.append((t, "empty", index))
                    if (bound is None or t > bound) and now - t <= RETRY_AFTER:
                        mine.append(t)
            candidates.append(sorted(mine))
            cells.append({
                "skill": skill, "section": section, "fixture": fixture, "model": model,
                "class": cls, "verdict": verdict.get("verdict"),
                # A guidance section's in-situ verdict, before the alone
                # pair's shorten-or-merge twist (`leans_to_removal`).
                "in_situ_verdict": verdict.get("in_situ_verdict"),
                # Gates' pair count and reason (`cheaper_first`, `_blocking`).
                "pairs": (cell or {}).get("pairs"), "reason": (cell or {}).get("reason"),
                "at_cap": (cell or {}).get("at_cap") is True,
                "schedulable": hold is None, "hold_reason": hold,
                "stakes": stakes_mod.level_of(table, subject, ident),
                "with_runs": len(runs.get("with", [])),
                "without_runs": len(runs.get("without", [])), "newest": newest,
                "usd_per_fire": cost / len(stamps) if cost is not None and stamps else None,
                "usd_per_arm_trial": cost / arm_trials if cost is not None and arm_trials
                else None,
                "empty_fires": 0, "outage_fires": 0, "down_fires": 0,
                "pending": bool(waiting),  # settled below, once every run is known
                "waiting": waiting,
                "pending_since": max(waiting, default=None),
                "last_fire": latest.get((fixture, model))})
            if section is not None:
                # What the guidance focus reads (`guidance_focus`): the
                # cell's confidence blocks, its reason and its COUNTED runs
                # per arm (the arm summaries' `runs`; `with_runs` above
                # counts every pooled run, skipped ones included).
                arms = {role: (cell or {}).get(role) for role in ("with", "without")}
                cells[-1].update({
                    "objective": (cell or {}).get("objective"),
                    "judge": (cell or {}).get("judge"),
                    "judge_carried": bool((cell or {}).get("judge_carried")),
                    "reason": (cell or {}).get("reason"),
                    **{f"{role}_counted": (arm.get("runs") or 0) if isinstance(arm, dict) else 0
                       for role, arm in arms.items()}})
    # A fire past its pending window is lost when the routine has delivered a run
    # of any cell since it started: the routine is up, so this fire alone
    # failed, and its cell is planned again now. With no delivery since,
    # the routine may be down, so the cell keeps holding for
    # FIRE_RESULT_WINDOW, as before: re-firing every cell into an outage
    # would only spend fires and count healthy cells broken.
    landed_any = [r for cell_landed in all_landed for r in cell_landed]
    for cell in cells:
        waiting = cell.pop("waiting")
        key = (cell["fixture"], cell["model"])
        cell["pending"] = any(now - t < held[key, t]
                              or not any(r > t for r in landed_any)
                              for t in waiting)
    # Second pass, once every fire is classified: judge each empty fire on
    # its own window, reconstruct when the routine was down, then count each
    # cell's candidates by their verdicts.
    verdicts = judge_empty_fires(fires, now - RETRY_AFTER)
    verdict_of = {(t, index): v for (t, _, index), v in zip(fires, verdicts)}
    outage_starts = sorted(t for (t, _, _), v in zip(fires, verdicts) if v == "outage")
    delivered = sorted([t for t, state, _ in fires if state == "delivered"] + early)
    spans = down_intervals(outage_starts, delivered)
    for index, (out, times) in enumerate(zip(cells, candidates)):
        for t in times:  # earliest first, so the excuse goes to the earliest
            verdict = verdict_of[(t, index)]
            if verdict == "undecided":
                continue
            if is_down_fire(t, verdict, spans):
                out["down_fires"] += 1
            elif verdict == "outage" and out["outage_fires"] < OUTAGE_EXCUSES:
                out["outage_fires"] += 1
            else:
                out["empty_fires"] += 1
    outages = [{"start": chain[0], "fires": len(chain)}
               for chain in fire_sweeps(outage_starts, OUTAGE_GAP)]
    if spans and spans[-1][1] is None:
        down = spans[-1][0]
    else:
        down = provisional_trip([(t, i) for t, state, i in fires if state == "empty"] + stale,
                                delivered)
    return cells, outages, down


def down_intervals(outage_starts: list, delivered: list) -> list:
    """When the routine was down (#583), as [opened, ended] pairs, earliest
    first, from sorted outage-fire and delivered-fire starts: down from the
    start of each outage fire (as judged now) until the start of the next
    delivered paired eval fire on a known cell, None while none has; spans
    that overlap merge, keeping the earliest opening."""
    spans: list = []
    for start in outage_starts:
        end = next((d for d in delivered if d > start), None)
        if spans and spans[-1][1] == end:
            continue  # the same span: it opened at an earlier outage fire
        spans.append([start, end])
    return spans


def is_down_fire(start: datetime, verdict: str, spans: list) -> bool:
    """Whether an empty fire, judged `verdict`, was sent while the routine
    was down (#583), so it says nothing about its cell and counts neither
    toward `empty_fires` nor against OUTAGE_EXCUSES: it started inside a
    down span and is not an outage fire, or is one that started at least
    PROBE_WAIT after the span opened. The breaker cannot trip sooner than
    PROBE_WAIT after the outage's first fire, so a fire that late is a
    probe (or a fire the breaker held back from), and probes 45 to 60
    minutes apart make outage windows of their own. An outage fire inside
    the first PROBE_WAIT keeps the outage rule, excused once and then
    counted: the backstop for fixtures that break together."""
    for opened, ended in spans:
        if opened <= start and (ended is None or start < ended):
            return verdict != "outage" or start - opened >= PROBE_WAIT
    return False


def provisional_trip(stale: list, delivered: list) -> datetime | None:
    """The breaker's early trip (#583), for the breaker only (it changes no
    count): `stale` holds (start, cell index) of every empty fire and every
    young fire at least PROBE_WAIT old with no landed run. The routine is
    down when some such fire's window, OUTAGE_GAP either side of its start,
    holds stale fires on at least OUTAGE_CELLS cells and no delivered or
    landed fire (`delivered`, starts), and is newer than every delivered
    fire: the earliest such window's first stale start, else None. Without
    it a burst into an outage runs FIRE_RESULT_WINDOW before any of its
    fires is judged; with it the breaker trips about PROBE_WAIT after the
    burst. A healthy sweep's runs land within minutes, so its fires are
    never stale."""
    newest = max(delivered, default=None)
    for start, _ in sorted(stale):
        low, high = start - OUTAGE_GAP, start + OUTAGE_GAP
        if newest is not None and newest >= low:
            continue  # a delivered fire inside the window or after it
        near = [(t, index) for t, index in stale if low <= t <= high]
        if len({index for _, index in near}) >= OUTAGE_CELLS:
            return min(t for t, _ in near)
    return None


def bare_cells(evals_dir: Path, gates_doc: dict, fire_runs: list) -> list:
    """{fixture, model, skill} for each (scheduled skill fixture that runs in
    place, roster model) with no bare run yet (module docstring, band 7):
    none in the verdict document's `bare_runs` and no bare fire for it that
    succeeded or is still running. A guidance fixture has none: its arms are
    its own."""
    committed = schedule.committed_fixtures(evals_dir.parent)
    scheduled = schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    done = {(run.get("skill"), run.get("fixture"), run.get("model"))
            for run in gates_doc.get("bare_runs", []) if isinstance(run, dict)}
    fired = set()
    for run in fire_runs:
        title = outcomes_mod.parse_title(run.get("display_title")) \
            if isinstance(run, dict) else None
        if title and title["bare"] and title["model"] \
                and (run.get("conclusion") == "success"
                     or run.get("status") not in (None, "completed")):
            # A bare pair fire (PAIR FIRES) covers both of its models.
            fired.update((title["target"], model) for model in outcomes_mod.title_models(title))
    out = []
    for fixture in scheduled:
        subject, skill = _fixture_subject(evals_dir, fixture)
        if subject != "skill" or not schedule.declares_context(evals_dir.parent / fixture):
            continue
        parts = fixture.split("/")
        name = parts[2] if len(parts) == 3 else None
        for model in gates_doc["roster_models"]:
            if (skill, name, model) not in done and (fixture, model) not in fired:
                out.append({"fixture": fixture, "model": model, "skill": skill})
    return out


def skill_contexts(evals_dir: Path, tree: Path, as_of: str, registries: dict,
                   gates_doc: dict, records: list, prs: list, on_hold: list,
                   now: datetime) -> dict:
    """Per skill with fixtures under evals/: what rule A and C need."""
    import compute_gates
    import gates
    import yaml
    index = compute_gates.build_index(tree, evals_dir, as_of)
    models = gates_doc["roster_models"]
    roster_changed = _git_time(evals_dir.parent, "evals/roster.yml")
    out = {}
    for directory in sorted(p for p in evals_dir.iterdir() if p.is_dir()):
        if directory.name == "guidance":
            # Guidance sections, not a skill: no improve loop, no usage weight.
            continue
        try:
            expected = compute_gates.expected_content(evals_dir, directory.name, registries)
        except ValueError:
            raise PlanError(SCHEDULE_FILES_MALFORMED) from None
        if not expected:
            continue
        urls, names = set(), sorted(expected)
        for name in names:
            try:
                doc = yaml.safe_load((directory / name / "fixture.yaml").read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, yaml.YAMLError):
                doc = None
            urls.add(doc.get("registry") if isinstance(doc, dict) else None)
            if not isinstance(doc, dict) or doc.get("skill") != directory.name:
                urls.add(None)
        if PRIVATE_REGISTRY_URL in urls:
            continue
        skill = directory.name
        cells = gates.pool_cells(index["runs"], skill, models, expected)
        holdout = names[0] if len(names) >= MIN_IMPROVE_FIXTURES else ""
        train = [n for n in names if n != holdout]
        changes = [t for t in (roster_changed,
                               _git_time(evals_dir.parent, f"evals/{skill}"),
                               _registry_time(registries, skill)) if t]
        out[skill] = {
            "fixtures": len(names), "holdout": holdout,
            "registry_ok": urls == {REGISTRY_URL},
            "verdict": gates_doc["skills"].get(skill, {}).get("verdict", "insufficient"),
            "evidence": train_evidence(cells, train),
            "pause": pause(skill, records, prs, on_hold, now,
                           max(changes) if changes else None,
                           lambda moment, cells=cells: with_run_after(cells, moment))}
    return out


def guidance_contexts(evals_dir: Path, tree: Path, as_of: str, gates_doc: dict,
                      guidance_dir: Path | None, records: list = (), prs: list = (),
                      removals: list = (), on_hold: list = (),
                      now: datetime | None = None) -> dict:
    """Per guidance section with fixtures that declare the `full` ablation
    arm (scripts/propose_guidance_edit.py's own listing): what improve
    eligibility needs, {fixtures, holdout, holdout_fixture, verdict,
    evidence, row_ok, pause}. The holdout is the last fixture in name order,
    as the proposer picks it, and only when there are MIN_IMPROVE_FIXTURES:
    `holdout` its directory name (the cells' key), `holdout_fixture` its key
    relative to evals/ (what the fire sends). The evidence is
    `train_evidence` over the other fixtures' pooled in-situ `full` arm
    runs; `row_ok` whether the proposer's `load_row` accepts the section's
    manifest row; `pause` rule C (`pause` keyed by section, then
    `guidance_lane`) over the guidance-improve `records`, the
    `eval-guidance-improve/` `prs` and the open `removals`. {} without
    `guidance_dir` (a section's extent, hence its cells, needs the
    checkout)."""
    root = evals_dir / "guidance"
    if guidance_dir is None or not root.is_dir() or root.is_symlink():
        return {}
    import compute_gates
    import gates
    import propose_guidance_edit as proposer
    index = compute_gates.build_index(tree, evals_dir, as_of)
    runs = [r for r in index["guidance_runs"] if r.get("pair") == "in_situ"]
    now = now or datetime.now(timezone.utc)
    roster_changed = _git_time(evals_dir.parent, "evals/roster.yml")
    out = {}
    for directory in sorted(p for p in root.iterdir()
                            if p.is_dir() and not p.is_symlink() and not p.name.startswith("_")):
        section = directory.name
        try:
            found = proposer.fixture_layout_discover(evals_dir, section)
        except proposer.Refusal:
            raise PlanError("a guidance fixture is unreadable") from None
        if not found:
            continue
        names = [Path(f).name for f in found]
        enough = len(names) >= MIN_IMPROVE_FIXTURES
        holdout = names[-1] if enough else ""
        # Pooled as the gate pools in-situ cells: the current-content runs
        # beside the rest of the guidance on main (2026-11-03; older rests
        # are ignored), so the improve evidence counts the same runs the
        # section's verdict does.
        try:
            expected = compute_gates.expected_guidance(evals_dir, section, guidance_dir)
        except ValueError:
            # Round 4's m4: expected_guidance reads the scope pauses, and a
            # malformed file must fail the plan with a plain reason, as the
            # skill path does, never a traceback or an opaque error.
            raise PlanError(SCHEDULE_FILES_MALFORMED) from None
        cells = gates.pool_cells(runs, section, gates_doc["roster_models"], expected,
                                 strata=True)
        try:
            row = proposer.load_row(guidance_dir, section)
        except proposer.Refusal:
            row = None
        changes = [t for t in (roster_changed,
                               _git_time(evals_dir.parent, f"evals/guidance/{section}"),
                               _git_time(guidance_dir, row["file"]) if row else None) if t]
        out[section] = {
            "fixtures": len(found), "holdout": holdout,
            "holdout_fixture": found[-1] if enough else "",
            "verdict": (gates_doc.get("guidance") or {}).get(section, {}).get(
                "verdict", "insufficient"),
            "evidence": train_evidence(cells, [n for n in names if n != holdout]),
            "row_ok": row is not None,
            "pause": pause(section, list(records), list(prs), list(on_hold), now,
                           max(changes) if changes else None,
                           lambda moment, cells=cells: with_run_after(cells, moment),
                           key="section")
            or guidance_lane(section, list(records), list(prs), list(removals))}
    return out


def fetch_evidence(token: str, now: datetime) -> dict:
    """The GitHub evidence, read live (fail closed)."""
    get = outcomes_mod.github_get
    since = now - STOP_FOR - timedelta(days=30)
    fire_runs = outcomes_mod.fetch_fire_runs(SELF_REPO, token, since)
    branches = outcomes_mod.fetch_improve_branches(SELF_REPO, token)
    guidance_branches = outcomes_mod.fetch_improve_branches(SELF_REPO, token,
                                                            mode="guidance-improve")

    def pulls_of(repo: str) -> list:
        pulls = []
        for page in range(1, outcomes_mod.MAX_PAGES + 1):
            rows = get(f"/repos/{repo}/pulls?state=all&per_page=100&page={page}", token)
            if not isinstance(rows, list):
                raise outcomes_mod.EvidenceError("the pulls API answered without a list")
            pulls.extend(rows)
            if len(rows) < 100:
                break
        return pulls

    def on_hold_of(repo: str) -> list:
        rows = get(f"/repos/{repo}/issues?state=open&labels=on-hold&per_page=100", token)
        if not isinstance(rows, list):
            raise outcomes_mod.EvidenceError("the issues API answered without a list")
        return [r.get("title") for r in rows if isinstance(r, dict)]
    own = on_hold_of(SELF_REPO)
    return {"fire_runs": fire_runs, "improve_branches": branches,
            "registry_prs": pulls_of(REGISTRY_REPO),
            "on_hold": own + on_hold_of(REGISTRY_REPO),
            "guidance_branches": guidance_branches,
            "guidance_prs": pulls_of(GUIDANCE_REPO),
            "guidance_on_hold": own + on_hold_of(GUIDANCE_REPO)}


def registry_prs(rows: list) -> tuple:
    """(improve PRs as {skill, state, created_at, closed_at, merged_at},
    skills with an open removal PR) from the pulls API's rows."""
    improve, removal = [], set()
    for row in rows:
        head = (row.get("head") or {}).get("ref") if isinstance(row, dict) else None
        if not isinstance(head, str):
            continue
        for prefix in ("eval-improve/", "retire-skill/"):
            skill = head[len(prefix):] if head.startswith(prefix) else None
            if skill is None or not outcomes_mod.SKILL_RE.fullmatch(skill):
                continue
            if prefix == "retire-skill/":
                if row.get("state") == "open":
                    removal.add(skill)
            else:
                improve.append({"skill": skill, "state": row.get("state"),
                                "created_at": row.get("created_at"),
                                "closed_at": row.get("closed_at"),
                                "merged_at": row.get("merged_at")})
    return improve, sorted(removal)


def guidance_prs(rows: list) -> tuple:
    """(guidance improve PRs as {section, state, created_at, closed_at,
    merged_at}, sections with an open removal PR) from _agent-guidance's
    pulls API rows: `eval-guidance-improve/<section>` and
    `retire-guidance/<section>` heads."""
    improve, removal = [], set()
    for row in rows:
        head = (row.get("head") or {}).get("ref") if isinstance(row, dict) else None
        if not isinstance(head, str):
            continue
        for prefix in (GUIDANCE_IMPROVE_PREFIX, GUIDANCE_REMOVAL_PREFIX):
            section = head[len(prefix):] if head.startswith(prefix) else None
            if section is None or not outcomes_mod.SECTION_RE.fullmatch(section):
                continue
            if prefix == GUIDANCE_REMOVAL_PREFIX:
                if row.get("state") == "open":
                    removal.add(section)
            else:
                improve.append({"section": section, "state": row.get("state"),
                                "created_at": row.get("created_at"),
                                "closed_at": row.get("closed_at"),
                                "merged_at": row.get("merged_at")})
    return improve, sorted(removal)


def private_skills(evals_dir: Path) -> frozenset:
    """The skills with a fixture in the private registry (`registry:` is
    PRIVATE_REGISTRY_URL). The public census never counts them, so their
    usage weight is unknown, not 0."""
    import yaml  # noqa: PLC0415
    out = set()
    for path in sorted(evals_dir.rglob("fixture.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if (isinstance(doc, dict) and isinstance(doc.get("skill"), str)
                and doc.get("registry") == PRIVATE_REGISTRY_URL):
            out.add(doc["skill"])
    return frozenset(out)


def skill_weights(tree: Path, skills: list, now: datetime,
                  private: frozenset = frozenset()) -> dict:
    """{skill: weight or None} from harness/skill_usage.py (skills-evals#420)
    over usage/weekly-local.json on the results branch: invocations over the
    last four weeks, 0 for a fresh census that never saw the skill, None
    when unknown (stale or absent). A skill in `private` is always None: the
    public census counts it under `other`, so a 0 would be false. Until that
    module is on main every weight is unknown, which `neutral_weights` makes
    neutral."""
    try:
        import skill_usage  # noqa: PLC0415 - optional until #420 merges
    except ImportError:
        return {skill: None for skill in skills}
    try:
        doc = skill_usage.load(tree / "usage" / "weekly-local.json")
    except (OSError, ValueError):
        doc = None
    out = {}
    for skill in skills:
        if skill in private:
            out[skill] = None
            continue
        try:
            value = skill_usage.weight(doc, skill, now) if doc is not None else None
        except (TypeError, ValueError, KeyError):
            value = None
        out[skill] = value if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and value >= 0 else None
    return out


def guidance_use(tree: Path, now: datetime) -> float | None:
    """The expected uses of every guidance section over USE_WINDOW_DAYS: all
    of it loads in every session, so the census's transcript sessions
    scanned, scaled to that window (skill_usage.session_rate). None when
    unknown (stale, absent or unreadable census), which the ranking makes
    neutral."""
    try:
        import skill_usage  # noqa: PLC0415 - optional, as in skill_weights
        value = skill_usage.session_rate(skill_usage.load(tree / "usage" / "weekly-local.json"),
                                         now, USE_WINDOW_DAYS)
    except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) \
        and value >= 0 else None


def trigger_contexts(evals_dir: Path, registries: dict) -> dict:
    """{skill: {"trigger_set", "hook_candidate"}} for every skill of the
    adam-agentskills checkout (`plugins/*/skills/<skill>/SKILL.md`, the one
    registry the routine improves); {} without one."""
    entry = registries.get("adam-agentskills")
    if not entry:
        return {}
    out = {}
    for path in sorted(Path(entry["path"]).glob("plugins/*/skills/*/SKILL.md")):
        name = path.parent.name
        if not outcomes_mod.SKILL_RE.fullmatch(name) or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        found = evals_dir / name / TRIGGER_SET
        out[name] = {"trigger_set": found.is_file() and not found.is_symlink(),
                     "hook_candidate": hook_candidate(text)}
    return out


def trigger_pauses(triggers: dict, evals_dir: Path, registries: dict, records: list,
                   prs: list, on_hold: list, now: datetime) -> None:
    """Set each trigger-lane skill's rule C `pause` in `triggers` (from
    `trigger_contexts`), in place: a trigger-only fire is an improve attempt
    of its skill (improve_outcomes), so the same records, `eval-improve/`
    pull requests and on-hold titles pause it, and its content changes as
    `skill_contexts` reads them (the registry, evals/<skill>, the roster).
    A merged edit is "re-measured" once COOLDOWN has passed: a skill with no
    fixtures gets no with-arm run, so usage, not a run, is what shows the
    new description worked. A skill with no trigger set fires nothing, so
    it is not read (None)."""
    roster_changed = _git_time(evals_dir.parent, "evals/roster.yml")
    for name, info in triggers.items():
        if not info["trigger_set"]:
            info["pause"] = None
            continue
        changes = [t for t in (roster_changed, _git_time(evals_dir.parent, f"evals/{name}"),
                               _registry_time(registries, name)) if t]
        info["pause"] = pause(name, records, prs, on_hold, now,
                              max(changes) if changes else None,
                              lambda at: now - at >= COOLDOWN)


def trim_contexts(registries: dict) -> dict | None:
    """{skill: {"chars"}} for every `length-limit` waiver of the
    adam-agentskills checkout's WAIVERS_FILE that names adam-agentskills and
    one `plugins/<plugin>/skills/<skill>/SKILL.md`, `chars` being that
    SKILL.md's parsed description length (None when unreadable), or None
    without a checkout or a readable file (DESCRIPTION TRIMS)."""
    import improve_gate  # noqa: PLC0415 - its registry path pattern
    import yaml  # noqa: PLC0415
    entry = registries.get("adam-agentskills")
    if not entry:
        return None
    root = Path(entry["path"])
    path = root / WAIVERS_FILE
    try:
        if path.is_symlink() or not path.is_file():
            return None
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    waivers = doc.get("waivers") if isinstance(doc, dict) else None
    if not isinstance(waivers, list):
        return None
    out = {}
    for waiver in waivers:
        if not isinstance(waiver, dict) or waiver.get("klass") != LENGTH_WAIVER_CLASS \
                or waiver.get("registry") != "adam-agentskills" \
                or not isinstance(waiver.get("path"), str):
            continue
        match = improve_gate.SKILL_MD_RE.fullmatch(waiver["path"])
        if not match or ".." in waiver["path"].split("/"):
            continue
        chars = None
        skill_md = root / waiver["path"]
        try:
            if not skill_md.is_symlink():
                text = skill_md.read_text(encoding="utf-8")
                front = yaml.safe_load(text[4:text.index("\n---\n", 3)]) \
                    if text.startswith("---\n") else None
                if isinstance(front, dict) and isinstance(front.get("description"), str):
                    chars = len(front["description"])
        except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError):
            chars = None
        out[match.group("skill")] = {"chars": chars, "plugin": match.group("plugin")}
    return out


def trim_busy(trims: dict | None, records: list, prs: list) -> dict | None:
    """Mark each waived skill of `trims` (from `trim_contexts`) `busy`, in
    place, when an improve attempt of it is in flight (a `pending`
    improve_outcomes record) or its `eval-improve/<skill>` pull request is
    open. `trim_items` plans no trim in a plugin with a busy waived skill:
    two trims of one plugin edit neighboring waiver lines and bump the same
    plugin manifest, so their pull requests would conflict."""
    if trims is None:
        return None
    for name, info in trims.items():
        info["busy"] = any(r["skill"] == name and r["outcome"] == "pending" for r in records) \
            or any(p["skill"] == name and p["state"] == "open" for p in prs)
    return trims


def gather(args, now: datetime) -> dict:
    import compute_gates
    evals_dir = args.evals_dir
    registries = compute_gates.flag_registries(args.registry)
    limits = guard.budget_file.load_budget(args.budget)
    gates_doc = compute_gates.compute(args.results_tree, evals_dir / "roster.yml",
                                      evals_dir / "gate-policy.yml", evals_dir,
                                      compute_gates.parse_as_of(args.as_of), registries,
                                      args.guidance)
    if args.evidence is not None:
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    else:
        evidence = fetch_evidence(os.environ.get("GH_TOKEN", ""), now)
    records = outcomes_mod.outcomes(evidence["fire_runs"], evidence["improve_branches"], now)
    prs, removal = registry_prs(evidence["registry_prs"])
    grecords = outcomes_mod.outcomes(evidence["fire_runs"],
                                     evidence.get("guidance_branches", []), now,
                                     mode="guidance-improve")
    gprs, gremoval = guidance_prs(evidence.get("guidance_prs", []))
    since = guard.window_start(now)
    # No own run: every not-completed improve fire counts (#572).
    by_kind, in_flight = guard.improve_kind_counts(evidence["fire_runs"], now, since)
    state = guard.account(args.results_tree, limits, now,
                          _fire_pair(evidence["fire_runs"], now, since),
                          guard.improve_counts(evidence["fire_runs"], now, since),
                          since,
                          improve_started=guard.improve_starts(evidence["fire_runs"], now, since),
                          eval_started=guard.eval_fire_starts(evidence["fire_runs"], now, since),
                          improve_by_kind=by_kind, improve_in_flight=in_flight)
    print(guard.describe(state))
    skills = skill_contexts(evals_dir, args.results_tree,
                            compute_gates.parse_as_of(args.as_of), registries,
                            gates_doc, records, prs, evidence["on_hold"], now)
    triggers = trigger_contexts(evals_dir, registries)
    trigger_pauses(triggers, evals_dir, registries, records, prs, evidence["on_hold"], now)
    cells, outages, down = eval_cells_and_outages(evals_dir, gates_doc, evidence["fire_runs"],
                                                  now, routine_git_version(args.results_tree))
    held = sum(1 for c in cells if c["hold_reason"] == HOLD_PRIVATE)
    if held:
        print(f"{held} private cells held")  # a count only: no name in the log
    return {"policy": gates_doc["policy"], "reservation": state["reservation"],
            "overrun": limits["per_run_overrun"], "improve_charge": state["improve_charge"],
            "room": guard.room(state),
            # What allowance_guard.improve_cap reads, for build_plan's walk.
            "improve_state": {key: state[key] for key in (
                "cap", "improve_charge", "improve_by_kind", "improve_in_flight")},
            # One eval fire may go only to bring a newer reading.
            "refresh": guard.fits(state) < 1 and guard.refresh(state),
            "points_per_usd": points_per_usd(args.results_tree, gates_doc, limits),
            "model_weights": model_weights(args.results_tree, gates_doc["roster_models"]),
            # PAIR FIRES: a pair's models, in this order.
            "roster_models": list(gates_doc["roster_models"]),
            "removal_prs": removal,
            "gate_verdicts": gate_verdicts(gates_doc),
            # The guidance focus's inputs (`guidance_focus`): its decision
            # levels, a separate top-level key of the verdict document, and
            # the sections whose removal pull request is open.
            "guidance_policy": gates_doc.get("guidance_policy"),
            "guidance_removal_prs": gremoval,
            "cells": cells, "outages": outages, "routine_down": down,
            "unmeasured": unmeasured_items(gates_doc, private_skills(evals_dir))
            + paused_ceiling_items(gates_doc, private_skills(evals_dir)),
            "real_work": real_work_rows(evals_dir),
            "bare": bare_cells(evals_dir, gates_doc, evidence["fire_runs"]),
            "skills": skills,
            "guidance": guidance_contexts(evals_dir, args.results_tree,
                                          compute_gates.parse_as_of(args.as_of), gates_doc,
                                          args.guidance, grecords, gprs, gremoval,
                                          evidence.get("guidance_on_hold", []), now),
            "guidance_gaps": guidance_gaps(args.guidance),
            "guidance_use": guidance_use(args.results_tree, now),
            "triggers": triggers,
            "trims": trim_busy(trim_contexts(registries), records, prs),
            "skill_weights": skill_weights(args.results_tree, sorted(set(skills) | set(triggers)),
                                           now, private_skills(evals_dir)),
            "skill_edit_lessons": lesson_evidence.skill_evidence(args.lessons, "skill-edit"),
            # THE BATCH: only with --batch-policy (the weekly workflow's).
            **batch_inputs(args, registries, limits, now),
            "private_skills": private_skills(evals_dir)}


def batch_inputs(args, registries: dict, limits: dict, now: datetime) -> dict:
    """THE BATCH's ctx keys: the policy and the previous record, and what a
    new batch is sized and fitted with (Adam's 2026-11-03 decision): the
    measured addition rates, the period's budget (`weekly_cap` x the
    period's weeks) and each roster model's measured cost per pair. All None
    without --batch-policy."""
    policy = load_batch_policy(args.batch_policy) if args.batch_policy is not None else None
    if policy is None:
        return {"batch_policy": None, "previous_batch": None, "batch_rates": None,
                "batch_budget": None, "batch_pair_costs": None}
    import compute_gates  # noqa: PLC0415
    rates = batch_rates(policy, addition_histories(registries, args.guidance), now)
    # Every validated paired run, any content digest: a pair's cost does not
    # depend on which version of the subject it measured.
    index = compute_gates.build_index(args.results_tree, args.evals_dir,
                                      compute_gates.parse_as_of(args.as_of))
    for kind, basis in rates.items():
        if basis["source"] == "policy":
            # A fixed text and a kind only: the reason names no subject.
            print(f"batch: the {kind} addition rate is the policy's constant")
    return {"batch_policy": policy, "previous_batch": read_batch(args.results_tree),
            "batch_rates": rates,
            "batch_budget": limits["weekly_cap"] * (policy["period"] / timedelta(weeks=1)),
            "batch_pair_costs": pair_costs(index["runs"] + index["guidance_runs"],
                                           args.results_tree, now, policy["cost_window"])}


def _fire_pair(runs: list, now: datetime, since: datetime | None = None) -> tuple:
    """(successful fires since `since`, default the last week; in the guard's
    hold) from the rows."""
    times = [outcomes_mod.parse_time(r.get("run_started_at") or r.get("created_at"))
             for r in runs if isinstance(r, dict) and r.get("conclusion") == "success"]
    times = [t for t in times if t is not None]
    since = since or now - guard.WINDOW
    return (sum(1 for t in times if t >= since),
            sum(1 for t in times if t >= now - guard.PENDING_FULL_HOLD))


def summary_lines(plan: dict) -> list:
    """Public-safe lines: counts, bands, public skill and fixture names."""
    lines = [f"### Weekly plan: {len(plan['fires'])} fire(s), room "
             f"{plan['room'] * 100:.1f} points", ""]
    for fire in plan["fires"]:
        target = fire["fixture"] or (f"{fire['skill'] or fire.get('section', '')} "
                                     f"(holdout {fire['holdout']})")
        if fire.get("trigger_only") == "true":
            target = f"{fire['skill']} (trigger only)"
        if fire.get("trim_description") == "true":
            target = f"{fire['skill']} (description trim)"
        mode = fire["mode"] + (" bare" if fire.get("arms") == "bare" else "")
        lines.append(f"- {fire['band']}: {mode} {target} {fire['model']}".rstrip()
                     + f", {fire['cost'] * 100:.2f} points")
    kinds: dict = {}
    for item in plan["work"]:
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
    lines.append("")
    if plan.get("real_work"):
        lines.append("Real-work row, not planned by the skill planner: "
                     + ", ".join(plan["real_work"]))
    lines.append("Work items: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
                                   or "none"))
    if plan.get("routine_down") and plan.get("probe_only", True):
        # Why a sweep with room fires one fire or none (#583).
        lines.append("Routine down: probe only (until a paired eval fire on a known "
                     "cell delivers)")
    elif plan.get("routine_down"):
        lines.append("Routine down: no schedulable eval cell to probe, planned normally")
    eligible = sorted(s for s, v in plan["skills"].items() if v["eligible"])
    lines.append("Improve-eligible skills: " + (", ".join(eligible) or "none"))
    # THE TRIGGER LANE: public skill names only (a private skill is never judged).
    trigger_ok = sorted(s for s, v in (plan.get("triggers") or {}).items() if v["eligible"])
    lines.append("Trigger-only eligible skills: " + (", ".join(trigger_ok) or "none"))
    # DESCRIPTION TRIMS: public adam-agentskills skill names only.
    if plan.get("trims_unread"):
        lines.append("Description trims: " + plan["trims_unread"])
    else:
        trims = plan.get("trims") or {}
        lines.append("Description trims: " + (", ".join(
            f"{s} ({'planned' if v['planned'] else 'eligible' if v['eligible'] else v['reasons'][0]})"
            for s, v in sorted(trims.items())) or "none waived"))
    batch = plan.get("batch")
    if batch:
        record = batch["record"]
        members = ", ".join(f"{s['subject']} ({s['status']})" for s in batch["status"])
        lines.append(f"Batch {record['number']}{' (started now)' if batch['started'] else ''}"
                     f", due {record['due_at']}: {members or 'no members'}; "
                     f"{batch['outside']} cell(s) outside it wait")
        fit = record.get("fit")
        if fit:  # a record from before the fit has none
            rates = ", ".join(f"{kind} {record['rates'][kind]:.2f}/week "
                              f"({record['rate_basis'][kind]['source']})"
                              for kind in BATCH_KINDS)
            spend = (f"{fit['total'] * 100:.1f} of {fit['budget'] * 100:.1f} points"
                     if fit["priced"] else f"not priced: {fit['reason']}")
            lines.append(f"Batch fit: rates {rates}; target sizes "
                         + ", ".join(f"{k} {v}" for k, v in record["sizes"].items())
                         + f"; {spend}; {len(record['waiting'])} subject(s) wait"
                         + (" (floor: the cheapest joined over budget)" if fit["floor"] else ""))
    lines.append("Guidance focus: " + (", ".join(
        f"{f['section']} ({f['score']:.3f})" for f in plan.get("guidance_focus", []))
        or "none"))
    lines.append("Hook candidates (mostly checklist or rules sections): "
                 + (", ".join(plan.get("hook_candidates", [])) or "none"))
    lines += ["", "Improve ranking (value = use × headroom ÷ cost)", ""]
    ranking = plan.get("improve_ranking", [])[:10]
    for row in ranking:
        value = "unknown" if row["value"] is None else f"{row['value']:.3g}"
        headroom = "unknown" if row["headroom"] is None else f"{row['headroom']:.2f}"
        end = ", eligible" if row["eligible"] else f": {row['reasons'][0]}"
        lines.append(f"- {row['subject']} {row['name']}: value {value} (use {row['use']:.1f}, "
                     f"headroom {headroom}, cost {row['cost'] * 100:.2f} points){end}")
    if not ranking:
        lines.append("- none")
    return lines


# ---------------------------------------------------------------------------
# The dispatch legs.

def validate_fire(env: dict, root: Path = REPO_ROOT) -> None:
    """Refuse a matrix leg that is not a fire this repository would plan:
    eval mode on a scheduled, committed fixture and a roster arm, or a pair
    of two distinct roster arms "m1,m2" (PAIR FIRES), its arms
    both, in-situ on a guidance fixture (THE ALONE PAIR), or bare on a
    fixture that runs in place; improve mode on a skill
    improve_gate.py fire-check accepts, with a holdout and no arms, or, with
    TRIGGER_ONLY "true" (THE TRIGGER LANE), with no holdout and the check's
    trigger-only rules (a committed trigger set of enough queries);
    guidance-improve mode on a section guidance_improve_gate.py fire-check
    accepts, with its holdout fixture key and no arms. Only a
    guidance-improve leg carries a section, and only an improve leg
    TRIGGER_ONLY "true" or TRIM_DESCRIPTION "true" (DESCRIPTION TRIMS: no
    holdout, and the check's `trim` rules), never both; absent or empty
    reads as "false"."""
    import guidance_improve_gate
    import improve_gate
    import roster_arm
    mode = env.get("MODE", "")
    fixture, key, model = env.get("FIXTURE", ""), env.get("EVAL_KEY", ""), env.get("MODEL", "")
    skill, holdout = env.get("SKILL", ""), env.get("HOLDOUT", "")
    section = env.get("SECTION", "")
    arms = env.get("ARMS", "")
    trigger_only = env.get("TRIGGER_ONLY", "")
    if trigger_only not in ("true", "false", ""):
        raise PlanError("the leg's trigger_only is not true or false")
    trigger_only = trigger_only == "true"
    trim = env.get("TRIM_DESCRIPTION", "")
    if trim not in ("true", "false", ""):
        raise PlanError("the leg's trim_description is not true or false")
    trim = trim == "true"
    if trim and mode != "improve":
        raise PlanError("only an improve leg may be a description trim")
    if trim and trigger_only:
        raise PlanError("a leg is a description trim or trigger-only, never both")
    if section and mode != "guidance-improve":
        raise PlanError("only a guidance-improve leg carries a section")
    if trigger_only and mode != "improve":
        raise PlanError("only an improve leg may be trigger-only")
    if mode == "eval":
        committed = schedule.committed_fixtures(root)
        scheduled = schedule.scheduled_fixtures(root / "evals" / "scheduled.yml", committed)
        if fixture in committed and fixture not in scheduled:
            raise PlanStale("the eval leg's fixture was unscheduled after the plan")
        # PAIR FIRES: "m1,m2" is two distinct ids, each in the payload
        # contract's pattern, and each checked below as a lone model is.
        models = model.split(",")
        pair_ok = len(models) == 1 or (len(models) == 2 and models[0] != models[1]
                                       and all(PAIR_MODEL_RE.fullmatch(m) for m in models))
        if fixture not in scheduled or schedule.validate_fixture(fixture, committed) != key \
                or skill or holdout or arms not in (*PAIRED_ARMS, "bare") or not pair_ok \
                or not all(MODEL_RE.fullmatch(m)
                           and roster_arm.is_arm(m, root / "evals" / "roster.yml")
                           for m in models):
            raise PlanError("the eval leg is not a scheduled fixture on a roster arm")
        if arms == "bare" and not schedule.declares_context(root / fixture):
            raise PlanError("the bare leg's fixture does not run in place")
        if arms == "in-situ" and _fixture_subject(root / "evals", fixture)[0] != "guidance":
            raise PlanError("the in-situ leg's fixture is not a guidance fixture")
        # The fire has no results tree to read the routine's Git from; the
        # plan held the fixture on it, and the harness refuses an old Git.
        if arms in PAIRED_ARMS \
                and fixture_hold_reason(root / fixture, check_git=False) is not None:
            raise PlanStale("the eval leg's fixture is held, not schedulable")
    elif mode == "improve" and trim:
        if fixture or key or model or arms or holdout \
                or not outcomes_mod.SKILL_RE.fullmatch(skill):
            raise PlanError("the description trim leg is malformed")
        try:
            improve_gate.fire_check(skill, "", trim=True)
        except improve_gate.Rejected:
            raise PlanError("the description trim leg is refused by the fire check") from None
    elif mode == "improve" and trigger_only:
        if fixture or key or model or arms or holdout \
                or not outcomes_mod.SKILL_RE.fullmatch(skill):
            raise PlanError("the trigger-only improve leg is malformed")
        try:
            improve_gate.fire_check(skill, "", trigger_only=True)
        except improve_gate.Rejected:
            raise PlanError("the trigger-only improve leg is refused by the fire check") from None
    elif mode == "improve":
        if fixture or key or model or arms or not outcomes_mod.SKILL_RE.fullmatch(skill) \
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", holdout):
            raise PlanError("the improve leg is malformed")
        try:
            improve_gate.fire_check(skill, holdout)
        except improve_gate.Rejected:
            raise PlanError("the improve leg is refused by the fixture check") from None
    elif mode == "guidance-improve":
        if fixture or key or model or arms or skill \
                or not outcomes_mod.SECTION_RE.fullmatch(section) \
                or not GUIDANCE_FIXTURE_RE.fullmatch(holdout):
            raise PlanError("the guidance-improve leg is malformed")
        try:
            guidance_improve_gate.fire_check(section, holdout, evals_dir=root / "evals")
        except guidance_improve_gate.Rejected:
            raise PlanError("the guidance-improve leg is refused by the fixture check") from None
    else:
        raise PlanError("the leg's mode is not eval, improve or guidance-improve")


def in_flight(runs: list, now: datetime) -> int:
    """Fire runs still running, or started within their mode's flight time.
    A pair fire (PAIR FIRES) is one run, so it counts once: the cap counts
    fires, not cells. It runs its models one after the other, so it is in
    flight for EVAL_FLIGHT per model."""
    count = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        started = outcomes_mod.parse_time(run.get("run_started_at") or run.get("created_at"))
        if run.get("status") not in (None, "completed"):
            count += 1
            continue
        if started is None or run.get("conclusion") != "success":
            continue
        title = outcomes_mod.parse_title(run.get("display_title"))
        flight = (IMPROVE_FLIGHT if title and title["mode"] in IMPROVE_MODES
                  else EVAL_FLIGHT * fire_models(title))
        if now - started < flight:
            count += 1
    return count


def wait_slot(fetch, max_wait: int, clock=lambda: datetime.now(timezone.utc),
              sleep=time.sleep, sweep_started: datetime | None = None) -> bool:
    """Poll until fewer than MAX_IN_FLIGHT fires are in flight; False after
    `max_wait` seconds, or once SWEEP_MAX_WAIT has passed since
    `sweep_started` (always one check). `fetch(since)` returns the fire runs."""
    if sweep_started is not None:
        left = SWEEP_MAX_WAIT - (clock() - sweep_started).total_seconds()
        max_wait = max(0, min(max_wait, int(left)))
    waited = 0
    while True:
        now = clock()
        if in_flight(fetch(now - IMPROVE_FLIGHT), now) < MAX_IN_FLIGHT:
            return True
        if waited + POLL_SECONDS > max_wait:
            return False
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def watchdog_due(anchor: datetime, fire_runs: list) -> datetime:
    """When to re-plan after a sweep at `anchor`: WATCHDOG_IDLE after it, or
    earlier, WATCHDOG_MARGIN after the first guard hold (a successful fire's
    PENDING_FULL_HOLD) that was still running at `anchor` ends."""
    due = anchor + WATCHDOG_IDLE
    for run in fire_runs:
        if not isinstance(run, dict) or run.get("conclusion") != "success":
            continue
        started = outcomes_mod.parse_time(run.get("run_started_at") or run.get("created_at"))
        if started is None:
            continue
        ends = started + guard.PENDING_FULL_HOLD
        if ends > anchor:
            due = min(due, ends + WATCHDOG_MARGIN)
    return due


def watchdog_decide(sweeps: list, fire_runs: list, now: datetime,
                    anchor: datetime | None = None) -> tuple:
    """("dispatch" | "wait" | "stand-down", due or None).

    With `anchor` (wait mode, armed at a sweep's end): any sweep created after
    it stands this watchdog down, since that sweep arms its own. Without
    (check mode): any sweep not finished stands it down, and the anchor is the
    newest finished sweep's end; no sweep at all is due now."""
    rows = [r for r in sweeps if isinstance(r, dict)]
    if anchor is not None:
        for run in rows:
            created = outcomes_mod.parse_time(run.get("created_at"))
            if created is None or created > anchor:
                return "stand-down", None
    else:
        if any(r.get("status") != "completed" for r in rows):
            return "stand-down", None
        ends = [outcomes_mod.parse_time(r.get("updated_at")) for r in rows]
        ends = [t for t in ends if t is not None]
        if not ends:
            return "dispatch", now
        anchor = max(ends)
    due = watchdog_due(anchor, fire_runs)
    return ("dispatch" if now >= due else "wait"), due


def fetch_runs(workflow: str, token: str, query: dict, get=outcomes_mod.github_get) -> list:
    """One page (newest first, 100) of `workflow`'s runs matching `query`."""
    doc = get(f"/repos/{SELF_REPO}/actions/workflows/{workflow}/runs?"
              + urllib.parse.urlencode({**query, "per_page": "100"}), token)
    found = doc.get("workflow_runs") if isinstance(doc, dict) else None
    if not isinstance(found, list):
        raise outcomes_mod.EvidenceError("the workflow runs API answered without a run list")
    return found


def watchdog(mode: str, fetch_sweeps, fetch_fires, timers_alive, max_wait: int,
             clock=lambda: datetime.now(timezone.utc), sleep=time.sleep) -> tuple:
    """Run the watchdog: (dispatch?, reason). `wait` mode anchors at its own
    start and sleeps until due (at most `max_wait` seconds in all); `check`
    mode decides once and stands down while a wait-mode watchdog is alive.
    `fetch_sweeps(since)` and `fetch_fires(since)` return runs created at or
    after `since`; `timers_alive()` is whether a wait-mode run is in
    progress."""
    start = clock()
    if mode == "check":
        if timers_alive():
            return False, "a waiting watchdog is armed"
        anchor = None
        sweeps = fetch_sweeps(start - timedelta(days=1))
    else:
        anchor = start
    while True:
        now = clock()
        if anchor is not None:
            sweeps = fetch_sweeps(anchor)
        since = (anchor or now) - guard.PENDING_FULL_HOLD - WATCHDOG_IDLE
        action, due = watchdog_decide(sweeps, fetch_fires(since), now, anchor)
        if action == "stand-down":
            return False, "a newer sweep is queued or running"
        if action == "dispatch":
            return True, f"re-plan due {_iso(due)}"
        if mode == "check":
            return False, f"next re-plan due {_iso(due)}"
        left = max_wait - (now - start).total_seconds()
        if left <= 0:
            return False, f"waited {max_wait}s; re-plan due {_iso(due)}"
        sleep(max(1, min((due - now).total_seconds(), left)))


def guidance_headroom(section: str, tree: Path, evals_dir: Path, guidance_dir: Path,
                      as_of: str) -> tuple:
    """(ok, message) for the fire check (module docstring, FIRE CHECK)."""
    import compute_gates
    gates_doc = compute_gates.compute(tree, evals_dir / "roster.yml",
                                      evals_dir / "gate-policy.yml", evals_dir,
                                      compute_gates.parse_as_of(as_of), {}, guidance_dir)
    info = guidance_contexts(evals_dir, tree, compute_gates.parse_as_of(as_of), gates_doc,
                             guidance_dir).get(section)
    headroom = info["evidence"]["headroom"] if info else None
    if headroom is None:
        return True, f"section {section}: train headroom unknown; the proposer measures it"
    if headroom < MIN_GAIN:
        return False, (f"section {section}: train headroom {headroom:.3f} is under the "
                       f"minimum gain {MIN_GAIN:g}; it needs harder fixtures, not an "
                       "improve run")
    return True, f"section {section}: train headroom {headroom:.3f}"


def _utcnow() -> datetime:
    """The plan's `now` (a seam for the plan command's tests)."""
    return datetime.now(timezone.utc)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--results-tree", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--registry", action="append", metavar="NAME=PATH")
    p.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    p.add_argument("--guidance", type=Path, default=None,
                   help="an _agent-guidance checkout: the guidance sections' content")
    p.add_argument("--budget", type=Path, default=None)
    p.add_argument("--evidence", type=Path, default=None)
    p.add_argument("--lessons", type=Path, default=None,
                   help="adam-agentskills-private lessons/proposals/ (skill-edit lessons)")
    p.add_argument("--max-fires", type=int, default=30)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--ranking-out", type=Path, default=None,
                   help="the improve ranking alone (public-safe), as JSON")
    p.add_argument("--batch-policy", type=Path, default=None,
                   help="evals/batch-policy.yml: plan within the two-week batch")
    p.add_argument("--batch-out", type=Path, default=None,
                   help="the batch record, written only when this plan started it")
    sub.add_parser("validate-fire")
    p = sub.add_parser("guidance-headroom")
    p.add_argument("section")
    p.add_argument("--results-tree", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--guidance", type=Path, required=True)
    p.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    p = sub.add_parser("wait-slot")
    p.add_argument("--max-wait", type=int, default=1500)
    p.add_argument("--sweep-started", default=None)
    p = sub.add_parser("watchdog")
    p.add_argument("--mode", choices=("wait", "check"), required=True)
    p.add_argument("--max-wait", type=int, default=WATCHDOG_MAX_WAIT)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-fire":
            fire = True
            try:
                validate_fire(dict(os.environ))
            except PlanStale as exc:
                # A stale plan is a hold, like a full cap: skip, stay green.
                print(f"::notice::{exc}; this leg is skipped and the next re-plan drops it")
                fire = False
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                    out.write(f"fire={'true' if fire else 'false'}\n")
            return 0
        if args.command == "guidance-headroom":
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.section):
                raise PlanError("the section id is malformed")
            ok, message = guidance_headroom(args.section, args.results_tree, args.evals_dir,
                                            args.guidance, args.as_of)
            print(message if ok else f"::error::{message}")
            return 0 if ok else 1
        if args.command == "wait-slot":
            token = os.environ.get("GH_TOKEN", "")
            started = None
            if args.sweep_started:
                started = outcomes_mod.parse_time(args.sweep_started)
                if started is None:
                    raise PlanError("--sweep-started is not a time")
            ok = wait_slot(lambda since: outcomes_mod.fetch_fire_runs(SELF_REPO, token, since),
                           args.max_wait, sweep_started=started)
            # A full cap is a hold, not a failure: the leg skips its fire and
            # the next re-plan picks the cell up again.
            if not ok:
                print(f"::notice::{MAX_IN_FLIGHT} or more fires stayed in flight; "
                      "this fire is held for the next re-plan")
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                    out.write(f"open={'true' if ok else 'false'}\n")
            return 0
        if args.command == "watchdog":
            token = os.environ.get("GH_TOKEN", "")
            stamp = lambda moment: ">=" + moment.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
            go, reason = watchdog(
                args.mode,
                lambda since: fetch_runs(WEEKLY_WORKFLOW, token, {"created": stamp(since)}),
                lambda since: outcomes_mod.fetch_fire_runs(SELF_REPO, token, since),
                lambda: bool(fetch_runs(WATCHDOG_WORKFLOW, token,
                                        {"event": "workflow_dispatch",
                                         "status": "in_progress"})),
                args.max_wait)
            print(f"watchdog: {reason}")
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                    out.write(f"dispatch={'true' if go else 'false'}\n")
            return 0
        if not 1 <= args.max_fires <= 30:
            raise PlanError("the fire cap must be 1 to 30")
        now = _utcnow()
        plan = build_plan(gather(args, now), now, args.max_fires)
    except (PlanError, outcomes_mod.EvidenceError, guard.GuardError,
            guard.budget_file.BudgetError) as exc:
        print(f"::error::weekly plan: {exc}")
        return 1
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError):
        # Never echo evidence content or exception bodies into the public log.
        print("::error::weekly plan: the plan could not be made")
        return 1
    lines = summary_lines(plan)
    print("\n".join(lines))
    if args.out is not None:
        args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.ranking_out is not None:
        args.ranking_out.write_text(json.dumps(
            {"schema_version": 1, "generated_at": plan["generated_at"],
             "improve_ranking": plan["improve_ranking"]}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    started = bool(plan["batch"] and plan["batch"]["started"])
    if args.batch_out is not None and started:
        args.batch_out.write_text(json.dumps(plan["batch"]["record"], indent=2, sort_keys=True)
                                  + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("matrix=" + json.dumps(plan["matrix"], separators=(",", ":")) + "\n")
            out.write(f"count={len(plan['fires'])}\n")
            out.write(f"batch_started={'true' if started else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
