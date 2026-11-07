# How the skills evals work, where to look, and what is left

A plain-English guide for someone who knows the fleet but has not worked in
this repository. The technical method is in [`DESIGN.md`](../DESIGN.md), the
operating record in [`HANDOFF.md`](../HANDOFF.md), and the live status board is
[issue #126](https://github.com/Adam-S-Daniel/skills-evals/issues/126).
Last revised 2026-10-26.

## 1. What the system does

Skills are reusable instruction files (recipe cards) that a coding agent
installs to do a class of task better. Fleet guidance is the same idea for
account-wide rules. This repository answers one question with numbers: **does
the agent do the job better with the card than without it?**

For each measured skill there is a **fixture**: a task prompt, a small
throwaway repository to work in, a list of objective checks, and a judge
rubric. A run takes the same model and has it do the task twice in two clean
copies of that repository, once with the skill installed and once without.
Then two scores are produced:

- **Objective checks** are scripted assertions on the finished workspace
  (files exist, YAML parses, a workflow would trigger on the right paths, a
  ruleset was not touched). They pass or fail and cannot be argued with.
  The [`workflow_permissions` check](../DESIGN.md#reusable-workflow-permission-checks)
  also verifies a named reusable-workflow caller's effective permission grant:
  job permissions replace workflow permissions, and missing or malformed
  evidence fails the check.
- **The judge** is a second, stronger model that reads both transcripts and
  diffs and scores each arm on a few named dimensions (for example
  completeness, salience, restraint) from a rubric written into the fixture.
  It is the subjective half, kept honest by the objective half.

A badge summarises the last five runs: green if the with-skill arm beat the
without-skill arm, yellow for a tie or mixed signals, red if the skill hurt.

## 2. Which models run, and who decides

The models that compete (the **arms**), the **judge**, and the cheap
**preflight** model that proves the API token works are listed in
[`evals/roster.yml`](../evals/roster.yml) on `main`. That file is trusted
because `main` is pull-request only: nothing automated can change it.

Every run also *computes* what the roster should be, from two inputs: the
Models API (which models exist and how old they are) and a **usage census**
(which models this account actually runs, per week, published from a
workstation as `usage/latest.json` on the results branch by
`scripts/publish_usage_census.sh`).

**How a model earns an arm's seat** (Adam decided this on 2026-09-22). A
model is an arm if the fleet actually runs on it — at least 10% of the
countable turns of the last two weeks. On top of that, the *newest* model
in a tier gets a seat too, but **only in a tier where some model already
earned one on usage**, and only once it is a week old. So the newest Opus
comes in because the fleet runs Opus; the newest Haiku does not, because it
does not. The rule used to give every tier on the ladder a seat regardless,
which put four arms on a roster where two of them measured tiers carrying
3% and 6% of the work — at four arms' worth of paid spend per run. On
today's census that means two arms (Sonnet 5 and Opus 5); an Opus 5.1
shipped before the next run would make three. The one exception is when
there is no usable census at all: then nothing can qualify, a roster with no
arms is useless, and the newest model of every tier takes a seat. If the census
itself is unusable, each fallback reason names the degradation. If the census
is usable but only its enter window fails a ranked-usage floor, the reason is
the bare newest-per-tier sentence.

The computed roster is only a **proposal**. When it differs from the committed
file the run pushes the proposed file to the bot-owned branch
`roster/proposal` and keeps one tracking issue open with every seat's reason
and the numerator and denominator behind it. With `roster_mode: auto` (the
setting today) the run opens a pull request from that branch itself and sets
it to merge once its `test` check passes; with `roster_mode: proposal` a human
opens and merges it, or does not. See ADR
[0001](decisions/0001-roster-trusted-on-main.md) for why it is shaped this
way, and ADR [0003](decisions/0003-roster-merges-automatically.md) for the
automatic merge.

The eval then runs on that merged roster in the same run, if the merge lands
within about half an hour and checks out: it changes only
`evals/roster.yml`, and that file is exactly what the run proposed. If not,
the eval runs on the committed roster as before, and the run's summary says
why (ADR [0004](decisions/0004-eval-runs-on-the-roster-its-run-merged.md)).

**Fixtures follow the roster; they do not pin models.** A fixture leaves out
`model:` and `judge.model:`, and the weekly sweep runs it once per roster arm
with a judge chosen above that arm. A pin goes stale the moment the roster
moves on (twelve fixtures kept a retired Sonnet and a below-arm Opus judge
until 2026-10-27). A fixture that truly needs one keeps it and says why, in a
parsed field: top-level `model_pin_reason:` beside `model:`, and
`judge.model_pin_reason:` beside `judge.model:` (non-empty strings). The
required `test` check enforces it
(`FixtureModelPinTests` in `test/issues/test_issue_371_judge_tier.py`): any
`model:` or `judge.model:` without its reason key fails, even one naming a
current roster id. That check never reads the roster, so fixtures stay in
step with it automatically: an unreasoned fixture always follows the roster,
and a roster pull request that drops a model (it changes exactly
`evals/roster.yml`, ADR [0003](decisions/0003-roster-merges-automatically.md))
cannot be turned red by a pin. A reasoned pin is a deliberate choice that the
roster does not move. The one deliberate pin is `evals/guidance/_delivery`,
which uses the roster's current Haiku (the `preflight` id), because the
delivery guard runs on the fixture's own model.

## 3. When it runs, and what it costs to run

`.github/workflows/eval.yml` runs every Tuesday at 07:00 UTC and on manual
dispatch (`gh workflow run eval.yml --ref main`, optional input `fixture=`).
It runs isolation pairs only: its `plan` job refuses every in-place fixture
(a top-level `context:` mapping) before any credential is minted and lists it
in the step summary, because only the cloud routine hosts in-place delivery
([#587](https://github.com/Adam-S-Daniel/skills-evals/issues/587)). When
nothing is left to run, no later job runs and the run ends successfully.
It bills the organisation's API workspace `skills-evals-ci` through workload
identity federation, not the Claude Code subscription. A measured run on
2026-09-22 (one fixture, one Sonnet 5 arm, Opus 4.8 judge) took 6 minutes 24
seconds wall clock and cost **$1.71**: Sonnet 5 arms $0.89, Opus 4.8 judge
$0.78, Haiku preflight $0.04. The judge is about 45% of a run.

Running the arms or the judge on the account's Claude subscription instead —
the weekly allowance, not dollars — was evaluated on 2026-09-23 and not
adopted: see ADR
[0002](decisions/0002-runs-bill-the-api-org-not-the-subscription.md) and § 7's
blocking decision 5.

### The weekly allowance guard

Since 2026-10-06 the scheduled evals run as Claude Code routines on the
subscription, so they spend the weekly allowance. Adam's standing decision
([#68, 2026-10-10](https://github.com/Adam-S-Daniel/skills-evals/issues/68#issuecomment-6097945979))
is that all automated evals together stay within **30% of the weekly
allowance**. The numbers live in [`evals/budget.yml`](../evals/budget.yml),
as fractions of the allowance (0.01 is one point, and points = percent of the
weekly allowance):

| Key | Value | Meaning |
|---|---|---|
| `weekly_cap` | 0.30 | all automated evals, in each allowance week of the account (from Monday 17:00 UTC) |
| `per_run_cap` | 0.01 | one run stops starting new work after this much (Adam, 2026-11-01; was 0.03) |
| `per_run_overrun` | 0.0005 | added to every run: the routine session's own cost (about $0.67 per fire) and the run's last call, which no reading includes (was 0.005, then 0.002, then 0.0018; 2026-11-06) |
| `points_per_usd` | 0.0005 | the allowance one dollar of the CLI's reported call cost uses: $20 per point, the low end of the rate measured on 2026-11-04 (about $24, range $20 to $35), so charges err high. `per_run_cap` and the weekly total both charge a run its own spend at this rate (was 0.00214, fitted to the account meter's movement, which other use inflated; 2026-11-06) |
| `stop_when_account_above` | 0.80 | a run stops, and no fire starts, once the account's weekly meter reads this |

Three layers enforce it:

1. **The in-run stop** (`harness/run_eval.py`). The CLI prints the account's
   weekly meter as each agent call begins. Before each trial and each judge
   call, a run checks its spend and the latest reading: once its own calls
   have cost `per_run_cap` at `points_per_usd`, or the meter reads
   `stop_when_account_above`, nothing more is started. The cap is charged the
   run's own dollars because the meter reads whole points and moves with the
   account's other use too; when any call's cost is unknown, or the file sets
   no `points_per_usd`, the cap falls back to the meter's movement since the
   run's first reading (after a window reset, the new reading alone counts). Skipped trials are written with error `budget_stop`, a
   skipped judge call as a judge error, and every summary of the run carries
   `usage.budget_stop` naming the limit. A guidance run, being one pair, ends
   with exit 2 instead. A run with no reading yet, or an API-billed one, is
   never stopped. `--budget PATH` reads another budget file.
2. **The pre-fire check** (`scripts/allowance_guard.py check`, a step of
   `routine-eval-fire.yml` before the fire, in every mode). It adds up the
   account's current allowance week, from its last weekly reset
   (`ACCOUNT_WEEK_RESET` plus whole weeks: Monday 17:00 UTC, so daylight
   saving does not move it; a rolling seven days until 2026-10-26; a manual reset the owner pressed, listed in `MANUAL_RESETS`, starts it at that instant for the rest of its week): each ingested run on `persistent/eval-results` at its
   own dollars (`usage.cost_estimate.usd` times `points_per_usd`) plus the
   overrun; at its measured weekly delta plus the overrun when it has no
   dollar figure (the delta is the whole account's movement, so it charged
   each run every other thread's use: 116 points booked against about 23 real
   in the week to 2026-11-04); or at the full reservation,
   `per_run_cap + per_run_overrun`, when neither is known, plus every successful
   fire without results: at the full reservation when it is under 90 minutes
   old, and at the overrun alone after that (a routine run finishes within
   minutes and a pair fire's two runs stop 40 minutes each, so a fire with no
   results 90 minutes later failed or never started). An improve fire (or a
   guidance-improve fire) never lands results, so it is charged its own
   cost for the whole week: eight eval fires at their measured mean
   (eight full reservations until anything is measured; twelve until
   2026-11-02, when the account meter around improve fires measured 2.3 to
   5.3 eval fires each, #572; eight is a ceiling until each improve run's
   cost is recorded). The fire goes
   only if one more reservation (an improve fire's charge, in improve mode)
   still fits under `weekly_cap`. An improve or guidance-improve fire must
   also pass the **improve cap** (#572, 2026-11-02): the week's improve
   fires of both kinds, successful or still running (a running one only
   when its run id is lower than this fire's, so of two dispatched together
   the earlier goes), stay under 20% of `weekly_cap` divided by the improve
   charge, except that each kind gets one fire per account week however
   small the share. The cap follows `weekly_cap` as configured, so a
   temporary raise loosens it too. With both floors used at eight units,
   about 2 × 0.04 = 0.08 of the allowance is held, 27% of a 0.30 cap: above
   the 20% share, by the approved floor rule. In the week of 2026-10-26 eight
   improve fires, all dispatched by hand or by an agent, held more than the
   whole cap; the guard runs for every dispatcher, so the cap is there, and
   the weekly plan applies the same test. A capped fire prints
   `improve cap: share allows N, used M (this kind K)` and exits 3. Until
   each improve run's cost is measured (#572 part 1), a fire that passed the
   guard and then failed uses no slot. When a recent account meter reading is
   usable, that sum is never taken above the reading plus the full charge
   of everything not inside it (since 2026-11-01), so eval runs the reading
   already holds are not counted twice. The same reading plus everything
   after it must also stay under `stop_when_account_above`: one limit for
   fires and runs, so no fire starts that the in-run stop would end at once
   (Adam, 2026-11-01). If the GitHub API cannot be read, the
   fire is refused. The log shows numbers only. A refusal (exit 3) ends the
   run `cancelled` through the workflow's `end-refused` job (#524), so a
   surplus planned fire is neither red nor counted as a fire; an error
   (exit 1) still fails closed and red.
3. **The weekly plan** (`scripts/plan_week.py`, see "The weekly plan"
   below). The Tuesday sweep spends the room left at each fire's historical
   cost; when nothing fits, the dispatch job is skipped.

Known gaps:

- **Local evals** (`scripts/local_eval.py`) are bounded only by the in-run
  stop until #370's single results pool lands. That wrapper starts run_eval
  once per trial, so in practice only the account limit applies there.
- **Improve mode's** skill-creator trigger evals call `claude -p` directly,
  not through run_eval, so only the pre-fire reservation bounds them.
- **One trial can overshoot**: the stop is checked between trials, so the
  trial in flight when a limit is crossed still finishes.
- **The meter is account-wide**: Adam's own use during a run is counted as
  eval spend. That overcounts, which is the safe direction.
- **Fires racing each other**: a fire counts only fires that have finished
  successfully, so two dispatched at the same moment do not see each other.
  The weekly plan accounts for its own fires up front. The improve cap
  alone also counts running improve fires with a lower run id (#572).

**The cost estimate** (Adam, 2026-11-01). The meter reads whole points, and
only as each call starts, so a run's last agent call and any judge call after
the last reading are never in its `usage.meter_delta`. Every summary's
run-level `usage` therefore also carries `cost_estimate`: the CLI's own dollar
figure (`total_cost_usd`, else its `modelUsage` costs) for every call of the run (agent, judge and guard),
summed as `usd` and split as `agent_usd`, `judge_usd` and `guard_usd`, plus
`last_agent_call_usd` (the run's final agent call, which the meter never
sees; for a session with follow-ups, that call's own share), `metered_usd`
(the calls the delta spans) and `calls_with_cost` / `calls_without_cost`. A
trial's own dollars per role stay in `usage.measured.<role>.cost_usd`. Nothing
is rounded until display: report.md shows the dollars to the cent, labeled as
an estimate. The harness cannot calibrate points, so its `points_per_usd` and
`points` are null with a reason. When a routine run is ingested,
`scripts/ingest_routine_results.py estimate` writes
`routine-results/<run id>/cost_estimate.json` beside it, once: each
invocation's block with `points` = `usd` × the rate measured over the runs
already ingested (their weekly meter movement, with no overrun added, over
their `metered_usd`). The estimate is collected to size `per_run_overrun`;
nothing charges from it.

### The weekly plan

`routine-eval-weekly.yml` runs `scripts/plan_week.py` every Tuesday at 07:00
UTC, and again after each ingested result (with the daily health audit as a
backstop, and `routine-eval-watchdog.yml` re-planning when a guard hold left
running at a sweep's end expires, or 50 minutes on) to spend room that fires costing less than their estimate left behind (G5, G6; Adam lifted the three-PR gate on 2026-10-26, see the
[ADR 0010 addendum](decisions/0010-run-ai-eval-steps-in-a-routine-fired-by-actions.md#decision-4-addendum-2026-10-26)).
It computes the retirement verdicts over the results branch, then plans
eval fires (one reviewed fixture from `evals/scheduled.yml` on one roster
model) and improve fires (one skill, with a fixed holdout) in eight bands:

1. **Safety**: every cell of a skill with an open removal pull request.
2. **Missing evidence** (at least 30% of the room): skill cells with no run,
   heaviest-used model first. A cell whose fires twice produced nothing
   becomes a "fixture broken" work item instead (a guidance cell too).
3. **Near a decision** (at least 20%): undecided skill cells, nearest a
   verdict first.
4. **Guidance focus** (at least 15%): the undecided guidance cells (no run,
   or not yet decided) of the two sections nearest a verdict, below.
5. **Improvements** (at least 20%): skills with four or more fixtures, train
   headroom, a check that fails often but can pass, not owned by retirement
   (its verdict is `retire` or `retire-pending`, or a removal pull request is
   open for it), and no pause, ordered by potential value: expected uses over four weeks
   times train headroom, per allowance point an improve run costs (three
   trials of every fixture at its historical fire cost; an unknown use or
   cost is neutral, an unknown headroom ranks last). Fleet-guidance sections
   are ranked in the same list (every session loads the guidance, so its use
   is the census's session count scaled to four weeks). The highest-value
   eligible section is a `guidance-improve` fire, one per plan, at three
   trials and the improve charge. Before allocation the band is walked in
   value order through the guard's improve cap, counting each kept fire, and
   fires it would refuse stay unplanned
   ([ADR 0005 addendum](decisions/0005-improvement-loop-reuses-skill-creator.md#routine-guidance-improve-mode-addendum-2026-10-27));
   only a section id the fire workflow refuses stays a work item for a
   local `scripts/propose_guidance_edit.py` run.
   The whole ranking is the plan's `improve_ranking`, the job summary's top
   ten, and the `improve-ranking` artifact (30 days). A skill with
   fewer fixtures becomes a "needs fixtures" work item. A skill that already
   passes at least 90% of its checks has no headroom for an edit to gain, so
   it becomes a "needs harder fixtures" work item: write a fixture it fails.
   A skill or guidance section owned by retirement gets neither item.
6. **Re-checks**: decided cells not measured for eight weeks (four for a
   high-stakes subject).

Two rules from the 2026-11-03 gate change apply across the bands. A cell
whose verdict class is `ceiling` (a bound on its without arm shows a mean
above 1 minus the margin, so it cannot show the gain) or
`ceiling-unconfirmed` (its without arm averages 0.90 or more and its
no-harm test has rejected, but it is undecided after 20 pairs) plans no
fire in any band but safety, re-checks included, and
becomes a "fixture ceiling" work item, unless its subject is already kept:
it needs a harder fixture, not more runs. It does not block its subject:
the subject's other cells keep being measured. An undecided cell that has
reached the 40-pair cap is not fired either (its window is frozen), blocks
its subject and becomes a "cell at cap" work item (`cell-at-cap`, with the
gate's reason), unless its subject is already kept; a decided cell at the
cap is not re-checked, since a new pair cannot enter its window. And the cheaper
model goes first: in the missing, near, focus and guidance-rest bands a
cell waits while its subject's cell of the same fixture on a model with a
lower known cost is still open (`cheaper_first`). A keep on the cheaper
model keeps the subject, and a removal needs both cells, so the dearer
model is fired only once the cheaper cell has decided without a keep. A
cheaper cell that more runs cannot move (blocking, below), or that already
has 10 pairs without a decision (`CHEAPER_FIRST_MAX_PAIRS`), holds nothing,
so a stuck cheaper cell never starves the dearer one.
7. **Bare baselines** (no minimum share, only the room left): one fire with
   `arms: bare` and three trials per scheduled fixture that runs in place
   and roster model, once per model id
   ([ADR 0012 addendum](decisions/0012-ab-runs-in-the-deployed-context-minus-the-subject.md#bare-baseline-addendum-adam-2026-10-27),
   Adam, 2026-10-27). It runs the isolation `without_skill` arm alone,
   nothing of ours loaded, to compare with the in-place `with` arm. A bare
   run already ingested, or a bare fire that succeeded or is still running,
   counts as done; a new roster model gets its own. Bare runs are listed
   apart (`bare_runs` in the verdict document) and never pooled into a cell.
8. **Guidance rest** (no minimum share): every other undecided guidance
   cell, cells with no run first. It gets only what every other band leaves,
   so when the 30-fire cap binds a section outside the focus can wait weeks.

**The guidance focus** (`guidance_focus` in `scripts/plan_week.py`; Adam's
rule, 2026-11-02 18:42 UTC: a section is removed at 90% confidence that it
does not improve results by 0.15 or more). Guidance fires used to spread over
every section's cells, so none came near a verdict; the focus spends them on
the two sections nearest one until those decide.

- **Progress.** A cell's *retire progress* is its objective's no-help
  confidence (the level the remove test has reached), divided by
  `retire_confidence` from the verdict document's `guidance_policy` (0.90
  when absent). Its *keep progress* is its objective's helps confidence
  divided by `benefit_confidence` (0.80 when absent); that is a per-cell
  level, and the section's keep family asks more of it. Since 2026-11-03 the
  judge is reported and does not vote, so neither reads it. An absent value
  is 0.
- **Score.** A section's score is the larger of its weakest cell's retire
  progress (it retires only when every cell clears) and its strongest cell's
  keep progress (one benefit keeps it). Ties go to the section with fewer
  cells, deliberately, since a smaller section reaches a verdict on fewer
  runs; then to more counted runs; then to the section id.
- **Eligibility.** The section's verdict is still `insufficient` (or it has
  none): keep, every retire verdict, `shorten-or-merge` and
  cannot-discriminate and `ceiling` are not focused. (A `ceiling` cell is
  one whose ceiling test, a betting bound on the without arm's run means at
  90%, shows a mean above 1 minus the margin, and whose no-harm test shows
  the section costs less than the margin there: at least 18 pairs, more as
  the arm drops below 1.0. A high cell undecided after 20 pairs, whose
  without arm averages 0.90 or more and whose no-harm test has rejected, is
  `ceiling-unconfirmed`. Both are parked and do not vote on removal, as is
  a `paused` cell of a fixture the eval scope pass paused, and a
  section whose every cell is at the ceiling is `ceiling`. A `cannot-discriminate`
  cell is one whose arms
  both pass almost nothing over three pairs, left out of the verdict as a
  broken fixture.) At least one of its cells must be
  able to plan a fire (schedulable, stakes not `none`, not a "fixture
  broken" missing cell), no `retire-guidance/<section>` pull request may be
  open in _agent-guidance, and no cell may be BLOCKING: one whose no-benefit
  or no-clear-effect was overruled by an agent-errored trial or a run
  skipped as anomalous, or a cannot-discriminate cell with at least three
  counted runs on each arm. More runs on the current content cannot move a
  blocking cell toward removal; under three runs one more can still change
  its class. An undecided cell at the 40-pair cap blocks too. A parked cell
  does not block: it is not fired, and the section's other cells are still
  measured.
- **Order.** The higher-scored section's fires go first; within a section the
  binding cell first (the lowest retire progress, or the highest keep
  progress when the score came from the keep side), then the cheaper model,
  whose cell the dearer one waits on.
  The plan records the two sections, with their scores, as `guidance_focus`,
  and the job summary names them. There is no stall rule: the 2026-11-02
  design review found one could not be built from the fire history without
  benching healthy sections.
- **One trial.** Focused fires stay at one trial. The harness refuses
  `--trials > 1` for a guidance fixture, and trials collapse into one run
  mean, so three trials cut the runs a verdict needs but not its cost (the
  2026-11-02 design review measured it equal or worse in trial-equivalents).
- **Today** (results branch at 3d68f1c, 2026-11-02): 29 sections, 64 in-situ
  cells on the two roster models, 24 counted runs in all. Before #557's
  with-ahead rule only 2 cells had a judge block, so every section's retire
  progress read 0 and the focus was
  `anything-you-name-gets-its-link` (8 cells, keep progress 0.144) and
  `agent-contribution-markers` (score 0, first of the two-cell sections with
  the most counted runs, by id), 10 fires in focus and 51 in the guidance
  rest.
- **Known limits.** The explorer's test queue reads
  no pull requests, so it can show a focus place for a section whose removal
  pull request is open, which the planner would not focus.

**The two-week batch** (THE BATCH in `scripts/plan_week.py`; Adam's
steady-state goal, 2026-11-02: at 25% of the weekly allowance, every two
weeks pick a batch of skills and guidance sections numbering about three
times the weekly addition rate, bring them all to a verdict, then start the
next). `evals/batch-policy.yml` sets the start (the 2026-11-09 17:00 UTC
reset, when the cap returns to 25%), the 14-day period, the multiplier (3),
the rate and cost windows, the expected pairs per cell and fallback addition
rates. Only the weekly workflow passes the policy (`--batch-policy`).

- **Fit to the budget** (Adam, 2026-11-03: "The rate is measured each
  period. The batch takes as many subjects as fit 50 points, most-used
  first. The rest wait. No new spend."). Each new batch:
  - measures each kind's addition rate over `rate_window_days` (28): skills
    added to adam-agentskills' `scripts/plugin_layout.json`, sections (ids)
    added to _agent-guidance's `agents-md/eval-coverage.yml`, per week, on
    each checkout's first-parent history. A file younger than the window is
    measured from its first version. An unreadable history (no checkout, a
    shallow one, under 7 days) uses the policy's constant (skills 0.75,
    guidance 0.5) and the record says so. The target size per kind is
    max(1, 3 x rate, half rounded up).
  - prices each subject at its cells with headroom (undecided, schedulable,
    not fixture-broken). Each is charged its remaining observations,
    min(`pairs_per_cell`, `max_runs_per_cell` from `gate-policy.yml` less
    the observations the gate already counts in it), at least 0, times its
    model's mean cost per observation. An observation is one fire, one
    paired run whatever its trial count, as the gate counts it. The cost per
    observation is the points in `cost_estimate.json` over the paired runs
    of the routine runs of the last `cost_window_days` (14), judge included
    (a guidance fire's `alone` pair is not an observation of its cell).
    `pairs_per_cell` is 15: the 2026-11-03 gate threshold sweep's 10.5
    points per new subject over 0.70 points per observation on both models.
  - takes candidates while their total stays within the budget,
    `budget.yml`'s `weekly_cap` x the period's weeks (0.25 x 2 = 50
    points); a total equal to the budget fits. Carried members stay first
    and count first. Then the kinds take turns. Skills go most used first
    (the usage weight), then high stakes, then the longest without a run,
    then name. Guidance has no per-section use signal, so sections go high
    stakes first, then the longest without a run, then name. A subject that
    alone would overflow the room left is skipped and waits; a cheaper one
    after it can still join. If nothing would join while subjects wait, the
    cheapest joins over budget, so the batch is never empty. With no
    measured cost the fit picks by target size alone.
  - **Today** (2026-11-03, results branch at cba7b38): skills 4 added
    since the layout pin of 2026-10-26 (3.37 a week, target 10), sections
    3 in 28 days (0.75 a week, target 2); 0.00152 of the allowance per Opus
    observation and 0.00064 per Sonnet one, so a fixture with no runs yet
    on both models is about 3.2 points. The fitted batch is 9 skills (one
    with two fixtures) and 2 sections (one the four-fixture, high-stakes
    `data-exposure-in-ci`), 48.6 of 50 points; 18 subjects wait: 13
    sections past the guidance target size and 5 skills for the budget.
- **What it changes.** While a batch is open the missing, near, focus and
  guidance-rest bands take only its members' cells, and every guidance
  member is in the focus. Safety, re-checks, improvements and bare
  baselines are unchanged.
- **Who joins.** Open subjects only: verdict still open, no removal pull
  request, no blocking cell, and some cell that would plan a fire. Never a
  private skill. In the fit's order, within the budget (above).
- **When it turns over.** When every member has left `open` (decided,
  blocked, stalled or gone), or at the due time, whichever is first. Open
  members are carried into the next batch first; new picks fill the rest.
  Blocked and stalled members are dropped: their work items (fixture-broken,
  ceiling) are the next step, not more runs.
- **Where it lives.** `batches/current.json` and `batches/<number>.json` on
  `persistent/eval-results`, written by the weekly workflow's
  `batch-publish` job only when a plan starts a batch. Each record lists the
  previous batch's members with their final status and, for audit, the
  rates and how each was had (`rate_basis`), the target `sizes`, the fit
  (`budget`, `pair_costs`, `pairs_per_cell`, `total`, `floor`), each
  member's expected `cost` and the subjects left `waiting` with theirs and
  why (`budget` or `size`). The job summary names the batch, each member's
  status, how many cells wait outside it and the fit's line.
- **The explorer** queues only the published batch's members in those
  bands. A finished batch stays published until the next sweep replaces it,
  so for that gap the page shows the old batch's queue.

**Stakes** (Adam, 2026-11-01). `evals/stakes.yml` gives a skill or guidance
section a stakes level from what it is for, with a one-line reason; a
subject with no row is `normal`. A `high` subject prevents irreversible or
public harm: its cells go first within the missing, near, guidance focus,
re-check and guidance rest bands, and it is re-checked after four weeks. A
`none` subject needs no eval because a check enforces it everywhere it applies: its row must name that
check as `<owner>/<repo>:<path>`, and the plan fires nothing for it.
`scripts/stakes.py --check` refuses an unknown field, a name with no fixture
directory here (so no private skill name can land in the public file), a
`none` row without its check and a duplicate; the explorer cards show both
levels.

`routine-eval-fire.yml` accepts `arms: bare` in eval mode only, and only for
a fixture whose `fixture.yaml` has a top-level `context` mapping; its run is
titled `Fire eval routine: eval bare <fixture> <model>`. The allowance guard
holds it as one run, like any eval fire; the plan reserves it as one arm
(the cell's cost per arm trial, times three).

**Pair fires.** A routine session costs about $0.67 of its own on every fire,
and nothing counts it, so when one sweep plans a fixture's cells on two
roster models with the same arms, it sends them as one fire with
`model: m1,m2`, in roster order (`scripts/plan_week.py`, PAIR FIRES). The
fire workflow checks each id as it checks one and sends `models: [m1, m2]`;
the routine runs the harness once per model, in that order, under one run id
and one results branch, and each summary keeps its own model. The run is
titled `Fire eval routine: eval <fixture> m1,m2`, which the planner and the
explorer read as a fire of each model's cell. Each invocation is stopped 40
minutes after it starts, so the planner holds a pending pair fire's cells for
90 minutes (a one-model fire's for 50) and counts it in flight for twice a
one-model fire's 20 minutes. The allowance guard reserves it
as one fire and, once its run is ingested, charges each of its two
invocations.

A skill is paused while an improve pull request is open, an attempt is in
flight, an open `on-hold` issue names it, for 14 days after a rejection, and
after three rejections in a row until the skill, a fixture or the roster
changes (or 90 days). A failed fire is retried at most twice. After a merged
improvement nothing is attempted until the with arm is measured again. The
routine does not record rejections, so `scripts/improve_outcomes.py` reads
them from GitHub: an improve fire with no `claude/eval-improve-<run id>`
branch twelve hours later counts as a rejection. A guidance section follows
the same rules, read from `claude/eval-guidance-improve-<run id>` branches and
`eval-guidance-improve/<section>` pull requests in _agent-guidance, and one
more: no section is fired while another section's guidance-loop pull request
(`eval-guidance-improve/*` or `retire-guidance/*`) is open there or its
attempt is in flight, because every guidance edit writes `AGENTS.md` and
`docs/guidance-impact.md`.

An accepted guidance candidate is pushed as `claude/eval-guidance-improve-<run
id>`; `routine-guidance-improve-gate.yml` validates it without running it,
builds the _agent-guidance commit with no credential (re-copying base.md to
its fleet-memory payload), and opens the pull request from
`eval-guidance-improve/<section>` with the eval-improve App's token minted for
_agent-guidance alone: ready with auto-merge in `auto`, a draft otherwise, and
nothing (with the reason in the job summary) while the App's secrets are unset
or the mint fails.

Work items (`needs-fixtures`, `needs-harder-fixtures`, `fixture-broken`,
`routine-outage`) are listed in the plan, not fired; each carries a
`change_type`. A guidance section whose `eval-coverage.yml` row is `gap`
(tracked, no fixture yet) gets `needs-fixtures` with zero fixtures, so its
first fixture is asked for before any headroom can be measured. A skill run
tests main's copy of its subject and refuses, with nothing spent, when the
registry checkout is not clean at its main (ADR 0012, addendum "main's
copy"); the routine's fire still reads as a success. So a cell with two such
empty fires within 14 days becomes a `fixture-broken` item instead of being
fired again, and is retried once those fires are 14 days old. A routine
outage empties every fire at once (2026-11-01: six fixtures, no run), which
says nothing about any fixture, so each empty fire is judged on its own
window, 60 minutes either side of its start: with no fire in it that landed
a run or is still young, and empty fires in it covering three or more cells,
it is an outage fire. A fire that landed a run 45 minutes or more after the
window's first empty fire may be the breaker's own probe and does not
count, and an empty fire at most 60 minutes before an outage fire, with no
delivery between, is one too (a slow onset). That excuses each cell's earliest such fire, one per
cell in 14 days, and each chain of outage fires lists a `routine-outage`
item (no fixture names) for a day. A further outage fire counts, so fixtures
broken together still go `fixture-broken`, one fire later; a window of fewer
than three cells cannot be told from broken fixtures and counts. From an
outage fire until a paired eval fire on a known cell delivers, the routine
counts as down; so it does, for this rule only, as soon as fires 45
minutes old with no run landed cover three cells in one window with no
delivery in or after it, so a burst into an outage trips it by the next
plan. While down, a plan holds improve and bare fires and sends one probe:
a paired eval fire on any schedulable cell, settled or fixture-broken ones
too, fewest empty fires first, then the cell fired longest ago; none while
a probe under 45 minutes old has landed nothing. Probes never count: an
empty fire sent while the routine was down is a down fire, except an
outage fire in the outage's first 45 minutes, which keeps the outage rule.
Every plan while down lists a `routine-down` item (no fixture names), and
the step summary says `Routine down: probe only`; with no schedulable
cell at all the plan is not held. The
dispatch job fires one leg at a time, waits while three fires are in flight,
and spaces fires a minute apart; improve fires go last.

### The trigger lane

Usage tracking (2026-10-26) counted about 55 skill calls in eight weeks over
about 72,000 model turns: most skills almost never trigger, so a skill's
description is probably the biggest lever. Every public adam-agentskills
skill whose usage weight is fresh and at most one call in four weeks (an
unknown weight is neutral and gets nothing) is judged by the trigger lane
(skills-evals#662; Adam, 2026-11-03: "New fire mode runs only
skill-creator's description loop; accept when held-out trigger accuracy
rises 0.15+ with no drop on should-not-trigger queries; PR auto-merges like
other loop PRs"):

- **`trigger-optimize`** (change type `trigger`) when
  `evals/<skill>/trigger-eval-set.json` exists: an improve-band **fire**,
  sent to `routine-eval-fire.yml` as improve mode with `trigger_only=true`
  and no holdout. It runs only the description loop on that set
  (`--trigger-eval-set evals/<skill>/trigger-eval-set.json`), is charged
  and capped as an improve fire, and sorts after the value-ranked improve
  fires, least used first. It waits while rule C pauses the skill (the
  same improve records and `eval-improve/<skill>` pull requests; a merged
  edit waits 14 days for usage to show, since a skill with no fixtures is
  never re-measured), and is skipped when the skill has an ordinary improve
  fire in the same plan (both write `eval-improve/<skill>`).
- **`needs-trigger-set`** (change type `fixture`) when there is no set: an
  `agent-ready` issue asking for one, a JSON list of `{query,
  should_trigger}` objects with at least 8 of each class. A pull request
  that adds only that file merges itself (`scripts/fixture_pr_gate.py`).

A skill owned by retirement gets neither, and a private skill is never
judged. The plan's `triggers` map lists every judged skill with its reasons;
the weekly sweep closes a `needs-trigger-set` issue only for a judged skill.

The plan also lists **hook candidates** (Adam: hooks first): skills whose
SKILL.md has at least half its non-blank body lines under a heading naming a
checklist, rules or checks. That heuristic is cheap and misses rules written
as prose.

### Description trims

adam-agentskills caps a skill's description at 400 characters, because long
descriptions push the session's skill listing past its budget and the last
skills then show no description (skills-evals#668). Ten eval-protected skills
were over the cap and carry a `length-limit` waiver in adam-agentskills'
`scripts/skills_waivers.yml`; their trims go through the improve lane
(skills-evals#687), as a fixed chore rather than a value bet:

- The planner reads those waivers from its adam-agentskills checkout. A
  waived public skill with at least three fixtures, all naming
  adam-agentskills, not owned by retirement, still over the cap and not
  paused by rule C (the ordinary improve pause, so a merged edit waits for a
  with-arm run of the new text) is an improve-band **fire** sent with
  `trim_description=true` and no holdout, placed before the value-ranked
  improve fires. It is charged and capped as an improve fire and held while
  the routine is down, and its skill gets no other improve fire in that plan.
- The loop (`propose_skill_edit.py --trim-description`) makes one proposal
  call for a description of at most 400 characters that keeps every trigger
  and every "not for" boundary, then measures the current and the trimmed
  text on every fixture (`with_skill`, three trials, no judge). It accepts
  only when no fixture errored, the trimmed text passes at least as many
  objective checks summed over all fixtures, and no fixture loses more than
  one. A description already within the cap is rejected with no model call.
- The improve gate re-derives that decision from the record's counts,
  refuses any body change or a description over the cap, and removes the
  skill's waiver from `scripts/skills_waivers.yml` in the same pull request
  (adam-agentskills fails its build on a waiver that matches nothing).
- The plan's `trims` map and its `description-trim` work items (never filed
  as issues) track every waived skill until its waiver is gone. With no
  readable waiver file the plan plans no trim and says so (`trims_unread`).

### Routine improve mode: what each run costs (#572)

Every improve and guidance-improve run (2026-11-02) records what it
measurably spent. On EVERY exit (accepted, rejected, refused, error or
timeout) the routine runs `scripts/improve_cost.py summarize` over the
loop's results directory and pushes the one file it writes on
`claude/eval-cost-<run id>`; `routine-eval-cost-pushed.yml` signals
`routine-eval-ingest.yml`, whose `validate` dispatches on the branch regex,
accepts exactly `improve-cost/<run id>/cost.json` passing
`improve_cost.check_record` (and refuses a private skill's name), and lands
it at `improve-costs/<run id>.json` on `persistent/eval-results`. A rejected
branch ends the ingest run red, as an eval rejection does; a second,
differing record for one run id is logged and dropped (the first stands). A
cost ingest, like an eval one, also wakes `explorer-data.yml` and
`routine-eval-weekly.yml`'s top-up re-plan.

The record holds numbers, enums and checked ids only: the trials' list-priced
`agent_usd`, `judge_usd` and `guard_usd` (and `usd_unpriced_trials`), each
side's trials and dollars, the proposal call's dollars and tokens (the
proposer writes `$RESULTS/proposal-<ts>.json` from `Runner.last_usage`), the
trigger loop's call count (its dollars are unknown), the arm and proposal
models, busy and span seconds, and the weekly meter's first and last
snapshot across all trials with their `delta` (null across a window reset or
with fewer than two snapshots). The guard does not charge it yet: that, and
recomputing the improve fire's reservation from these records, is a
follow-up once at least six exist.

The routine's saved prompt is not in this repository. Its improve sections,
and the rule sentence that allows the cost branch, read as follows (a test
holds the commands in them to the scripts' own flags):

```text
Never dispatch workflows, open PRs or issues, or edit any file in the repos except the branches your mode allows (improve and guidance-improve modes: their result branch and claude/eval-cost-<run_id>).

IMPROVE MODE (payload "mode": "improve" only). You run the skill improvement loop for ONE skill and, only if it accepts a candidate, push ONE branch claude/eval-improve-<run_id>; on every exit you also push the one cost branch of step 5. You never open, edit or comment on a pull request, never push to main or persistent/*, and never edit adam-agentskills.
1. In skills-evals, check out the default branch. Use the adam-agentskills checkout at its default branch as $REG and record REG_SHA=$(git -C "$REG" rev-parse HEAD). Install the harness pins: python3 -m pip install --user pyyaml==6.0.3 markdown-it-py==4.2.0 tree-sitter==0.26.0 tree-sitter-bash==0.25.1. Fetch skill-creator read-only at exactly commit 2a40fd2e7c52207aa903bd33fc4c65716126966e of https://github.com/anthropics/claude-plugins-official (e.g. git clone --filter=blob:none --no-checkout, then git checkout 2a40fd2e7c52207aa903bd33fc4c65716126966e -- plugins/skill-creator) into a temp dir; SC=<that dir>/plugins/skill-creator/skills/skill-creator. Never use any other commit or plugin.
2. Re-check the payload: evals/<skill>/ must hold at least three fixture directories and holdout (if not null) must be one of them; else REFUSED. Build the guard's unset list AT RUN TIME (never a fixed list), then run the loop under it with a results directory OUTSIDE the checkout:
   mapfile -t refused < <(python3 -c 'import os, sys; sys.path.insert(0, "scripts"); import local_eval_guard as g; print("\n".join(g.refused_env_names(os.environ)))' | sed '/^$/d')
   unset_args=(); for name in "${refused[@]}"; do unset_args+=(-u "$name"); done
   env "${unset_args[@]}" python3 scripts/propose_skill_edit.py "$SKILL" --registry adam-agentskills="$REG" --ref "$REG_SHA" --skill-creator "$SC" --trials "$TRIALS" [--holdout "$HOLDOUT" only when not null] [--trigger-eval-set evals/$SKILL/trigger-eval-set.json only when that file exists] --results-dir "$RESULTS"
   Run that propose_skill_edit.py command in the background with a Bash timeout of 5400000 ms (90 minutes), never less, and wait for its exit code before going on. Do not edit scripts/local_eval_guard.py or bypass it any other way. Exit 0 = accepted, 1 = rejected, 2 = refused. On exit 1 or 2 push no claude/eval-improve branch; go to step 5, then end with the status and the record's reasons (or the refusal line). If the run is refused or fails before the loop starts (the payload re-check, a failed skill-creator fetch, missing node or a failed npm ci), go to step 5 with exit code 2 before ending. On the 90-minute timeout, first stop the background loop process (kill it and wait for it to exit), then go to step 5 with exit code none.
3. On exit 0 only: create branch claude/eval-improve-<run_id> from the default branch and add exactly three files from $RESULTS/improvements/<skill>/<ts>.*: <ts>.json as eval-improve/<run_id>/summary.json, <ts>.pr-body.md as eval-improve/<run_id>/report.md, <ts>.patch as eval-improve/<run_id>/skill.patch. Commit nothing else. Before pushing, self-check: python3 scripts/improve_gate.py validate --repo . --base origin/<default> --source HEAD --branch claude/eval-improve-<run_id> --out "$(mktemp -d)"; if it prints rejected:, push nothing and report that line.
4. Push only that branch and verify with git merge-base --is-ancestor <sha> origin/claude/eval-improve-<run_id>. Never open a pull request: routine-improve-gate.yml validates the branch and opens the draft PR.
5. COST RECORD, on EVERY exit (0, 1, 2, an error, the 90-minute timeout, or a refusal before the loop started), once per run id, after step 4 if it ran: with RUN_ID set to the payload's run_id and COST=$(mktemp -d) (outside the checkout), from the skills-evals checkout run
   python3 scripts/improve_cost.py summarize --results-dir "$RESULTS" --run-id "$RUN_ID" --mode improve --target "$SKILL" --exit-code <the loop's exit code 0, 1 or 2; 2 for any refusal before the loop started; none on an error or the 90-minute timeout> --out "$COST/improve-cost/$RUN_ID/cost.json"
   (when the loop never started, pass a fresh empty directory as --results-dir). If any evals/<target>/*/fixture.yaml names adam-agentskills-private, push no cost branch and report it. If summarize exits 0: W=$(mktemp -d)/w; git worktree add -b claude/eval-cost-$RUN_ID "$W" origin/main; mkdir -p "$W/improve-cost/$RUN_ID"; cp "$COST/improve-cost/$RUN_ID/cost.json" "$W/improve-cost/$RUN_ID/cost.json"; git -C "$W" add -- "improve-cost/$RUN_ID/cost.json". Verify that git -C "$W" diff --cached --name-only prints exactly improve-cost/$RUN_ID/cost.json and nothing else; otherwise push nothing in this step and report it. Never use git add -A or git add . here, and never edit that file or put anything else on that branch. Commit with the message "Improve cost <run_id>", push only that branch with git -C "$W" push origin HEAD:refs/heads/claude/eval-cost-$RUN_ID, and verify with git -C "$W" merge-base --is-ancestor <sha> origin/claude/eval-cost-$RUN_ID. If summarize, the commit or the push fails, report it and go on: it never changes RESULT.
6. Final message: skill, trials, holdout, loop exit code, wall time, the record's decision and reasons, token/cost figures if reported, branch pushed (or none), cost branch pushed (or why not), and RESULT: ok|error|refused.

GUIDANCE-IMPROVE MODE (payload "mode": "guidance-improve" only). You run the guidance improvement loop for ONE _agent-guidance section and, only if it accepts a candidate, push ONE branch claude/eval-guidance-improve-<run_id>; on every exit you also push the one cost branch of step 5. You never open, edit or comment on a pull request, never push to main or persistent/*, and never edit or push to _agent-guidance.
1. In skills-evals, check out the default branch. Use the _agent-guidance checkout at its default branch, with its full history, as $AG and record AG_SHA=$(git -C "$AG" rev-parse HEAD). Install the harness pins: python3 -m pip install --user pyyaml==6.0.3 markdown-it-py==4.2.0 tree-sitter==0.26.0 tree-sitter-bash==0.25.1. The proposer validates its patch with _agent-guidance's own checks, which need `node` on PATH and that checkout's packages: run (cd "$AG" && npm ci); if node is missing or npm ci fails, go to step 5 with exit code 2, then end with RESULT: refused and that reason.
2. Re-check the payload: `section` must match ^[a-z0-9][a-z0-9-]{0,63}$ and `python3 scripts/guidance_improve_gate.py fire-check "$SECTION" --holdout="$HOLDOUT" --guidance "$AG"` (pass --holdout= with an empty value when holdout is null) must exit 0; else REFUSED. Build the guard's unset list AT RUN TIME (never a fixed list), then run the loop under it with a results directory OUTSIDE the checkout:
   mapfile -t refused < <(python3 -c 'import os, sys; sys.path.insert(0, "scripts"); import local_eval_guard as g; print("\n".join(g.refused_env_names(os.environ)))' | sed '/^$/d')
   unset_args=(); for name in "${refused[@]}"; do unset_args+=(-u "$name"); done
   env "${unset_args[@]}" python3 scripts/propose_guidance_edit.py "$SECTION" --guidance "$AG" --ref "$AG_SHA" --trials "$TRIALS" [--holdout "$HOLDOUT" only when not null] --results-dir "$RESULTS"
   Run that propose_guidance_edit.py command in the background with a Bash timeout of 5400000 ms (90 minutes), never less, and wait for its exit code before going on. In this mode the nested-agent limit is 100 (not the default 60): the loop starts one agent session per fixture, side and trial, up to 6 fixtures x 2 sides x 3 trials x 2 (its one re-run) + 1 proposal call = 73, with margin. Stop at the 90-minute timeout regardless. Do not pass --dry-run, --no-judge or --rotation. Do not edit scripts/local_eval_guard.py or bypass it any other way. Exit 0 = accepted (and the patch passed _agent-guidance's checks), 1 = rejected, 2 = refused. On exit 1 or 2 push no claude/eval-guidance-improve branch; go to step 5, then end with the status and the record's reasons (or the refusal line). If the run is refused or fails before the loop starts (the payload re-check, a failed skill-creator fetch, missing node or a failed npm ci), go to step 5 with exit code 2 before ending. On the 90-minute timeout, first stop the background loop process (kill it and wait for it to exit), then go to step 5 with exit code none.
3. On exit 0 only: create branch claude/eval-guidance-improve-<run_id> from the default branch and add exactly three files from $RESULTS/guidance-improvements/<section>/<ts>.*: <ts>.json as eval-guidance-improve/<run_id>/summary.json, <ts>.pr-body.md as eval-guidance-improve/<run_id>/report.md, <ts>.patch as eval-guidance-improve/<run_id>/guidance.patch. Commit nothing else. Before pushing, self-check: python3 scripts/guidance_improve_gate.py validate --repo . --base origin/<default> --source HEAD --branch claude/eval-guidance-improve-<run_id> --out "$(mktemp -d)"; if it prints rejected:, push nothing and report that line.
4. Push only that branch and verify with git merge-base --is-ancestor <sha> origin/claude/eval-guidance-improve-<run_id>. Never open a pull request: routine-guidance-improve-gate.yml validates the branch and opens the pull request in _agent-guidance.
5. COST RECORD, on EVERY exit (0, 1, 2, an error, the 90-minute timeout, or a refusal before the loop started), once per run id, after step 4 if it ran: with RUN_ID set to the payload's run_id and COST=$(mktemp -d) (outside the checkout), from the skills-evals checkout run
   python3 scripts/improve_cost.py summarize --results-dir "$RESULTS" --run-id "$RUN_ID" --mode guidance-improve --target "$SECTION" --exit-code <the loop's exit code 0, 1 or 2; 2 for any refusal before the loop started; none on an error or the 90-minute timeout> --out "$COST/improve-cost/$RUN_ID/cost.json"
   (when the loop never started, pass a fresh empty directory as --results-dir). If any evals/<target>/*/fixture.yaml names adam-agentskills-private, push no cost branch and report it. If summarize exits 0: W=$(mktemp -d)/w; git worktree add -b claude/eval-cost-$RUN_ID "$W" origin/main; mkdir -p "$W/improve-cost/$RUN_ID"; cp "$COST/improve-cost/$RUN_ID/cost.json" "$W/improve-cost/$RUN_ID/cost.json"; git -C "$W" add -- "improve-cost/$RUN_ID/cost.json". Verify that git -C "$W" diff --cached --name-only prints exactly improve-cost/$RUN_ID/cost.json and nothing else; otherwise push nothing in this step and report it. Never use git add -A or git add . here, and never edit that file or put anything else on that branch. Commit with the message "Improve cost <run_id>", push only that branch with git -C "$W" push origin HEAD:refs/heads/claude/eval-cost-$RUN_ID, and verify with git -C "$W" merge-base --is-ancestor <sha> origin/claude/eval-cost-$RUN_ID. If summarize, the commit or the push fails, report it and go on: it never changes RESULT.
6. Final message: section, trials, holdout, loop exit code, wall time, the record's decision and reasons, token/cost figures if reported, branch pushed (or none), cost branch pushed (or why not), and RESULT: ok|error|refused.
```

### Skill retirement (#70)

Every day, `skill-coverage.yml`'s `retirement` job (schedule only) runs
`scripts/compute_gates.py` over the results branch and the public registries,
then `scripts/retire_skill.py` over its verdicts.

**The rule** (2026-11-03, replacing the normal-mixture bound after that
day's statistics review and threshold sweep; Adam's decision on it is
pending, and `harness/gates.py`'s docstring is the full statement):

- *The pair is the unit.* A cell (skill, fixture, roster model) pairs each
  with run with the without run of the same fire (the same timestamp), and
  decides on the per-fire difference D = with minus without.
- *The bound.* A betting confidence sequence on D (Waudby-Smith and Ramdas,
  aGRAPA bets capped at 0.9 of the safe stake). It needs no variance prior
  and holds at every run count, so a cell is checked after every pair; four
  identical runs per arm, which removed a skill under the old bound, now
  decide nothing (identical arms need 18 pairs).
- *Keep* when the keep test shows D above 0 at 80% (`benefit_confidence`),
  split across the subject's cells (fixtures on main times roster models,
  Bonferroni). *No benefit* in a cell when its test shows D below 0.15
  (`objective_margin`) at 90% (`retire_confidence`). Whichever test rejects
  first decides the cell; a tie keeps.
- *Ceiling.* A cell whose without arm is shown, by a betting bound at 90%
  on its run means, to average above 1 minus the margin cannot show the
  margin (a sample mean is not enough: three perfect pairs once parked a
  cell for good). It is `ceiling`: it does not vote on removal, the planner
  stops firing it without blocking the subject's other cells, and a subject
  whose every cell is at the ceiling is `ceiling`. It parks only when a
  no-harm test (D above minus the margin, at 90%) agrees, so the margin
  cannot hide a harm beyond the margin. A cell whose without arm is high
  but undecided after 20 pairs (`max_runs_high_cell`) stops being fired as
  `ceiling-unconfirmed`, which does not vote either, but only once the
  no-harm test has rejected and the without arm averages at least 0.90
  (`HIGH_STOP_MIN_WITHOUT`); otherwise it is fired on to the cap. A retire
  verdict beside either is only a proposal.
- *Harm.* A cell whose without arm is high is also tested for harm (D below
  0 at 90%), and is `no-benefit` once that test decides: it needs no
  headroom to show harm. A harm beyond the margin is parked only at the
  no-harm test's error rate; a milder one can still end parked or, at the
  cap, `no-clear-effect` (a proposal at most). A fixture the eval scope
  pass pauses stops being fired, so a harm it had not yet decided stays
  undecided (`paused`, below); the subject is then `insufficient`, not
  `ceiling`, when every cell is parked, and otherwise a `retire` proposal
  (a parked cell beside decided `no-benefit` cells), never automatic.
- *The cap.* A cell still undecided after 40 pairs (`max_runs_per_cell`)
  is `no-clear-effect` when no test crossed and its pairs span two Claude
  Code versions. Otherwise (one version, or a test that crossed but has
  not decided) it stays `insufficient`: it is no longer fired, blocks its
  subject and becomes a `cell-at-cap` work item.
- *Paused fixtures.* A fixture the eval scope pass paused (below) keeps its
  cells in the verdict: a `benefit` cell still keeps, a `no-benefit` cell
  (a harm or no-benefit its test decided before the pause) still votes, and
  any other is `paused`, parked, so it does not vote and a removal beside it
  is only a proposal. A subject whose every cell is parked is `ceiling` only
  when each shows the ceiling on its own runs: a ceiling class, or a cell
  paused for the ceiling that was a ceiling class or whose no-harm test had
  rejected with a without arm averaging 0.90 or more. The pause reads only
  a pooled sample of the without arm, which is not that evidence. Otherwise
  (and for a floor or zero-use pause) the subject is `insufficient`, and the
  planner lists it as a `paused-unmeasured` work item: a paused fixture is
  off the schedule, so it has no planner cell to carry a `fixture-ceiling`
  item. A `ceiling` subject with a paused cell among its cells (round 6's
  M1) is the same gap: no planner cell, and with every fixture paused no
  improve item either. The planner lists it as a `paused-ceiling` work item
  asking for a harder fixture.
- *Where work items go.* `fixture-ceiling`, `cell-at-cap`,
  `paused-unmeasured` and `paused-ceiling` items are counted in the weekly sweep's step summary
  and listed in its plan JSON; no issue is filed for them
  (`scripts/work_item_issues.py` files only `fixture-broken`,
  `routine-outage`, `needs-fixtures`, `needs-harder-fixtures` and
  `needs-trigger-set`).
- *Removal.* `retire` needs every cell with headroom to be no-benefit or
  no-clear-effect, none undecided. It may be automatic only with two or
  more such cells, every one no-benefit; one headroom cell, or any
  no-clear-effect or parked cell, makes it a proposal (`removal: proposal`
  in the verdict), and `scripts/retire_skill.py` re-derives that from the
  cells rather than trusting the field. A removal decides at the first pair
  where its test is at its level and the pairs so far span two Claude Code
  versions, and a skill cell with an agent-errored trial supports no
  removal at all.
- *The judge* is reported beside each cell and does not vote; single
  checks no longer keep on their own.
- *Current content only.* A cell decides on runs of the skill and fixture
  on main. For a guidance section, the guidance block's `rest_policy`
  (2026-11-07, default `pooled-with-current-guard`) pools the runs beside
  every rest of the guidance, pair by pair at equal weight, for keeping
  once the current rest has 6 pairs (a keep test over the current rest
  alone runs beside it, each at half the keep level);
  any removal also needs at least `rest_guard_min_pairs` (6) pairs beside
  the current rest whose own share of the test reaches the removal level,
  and ceilings, floors and the cap read the current rest only. `current`
  reads the current rest only, as from 2026-11-03.
- *The bet prior.* Each cell's first bet starts from a prior learned from
  other subjects' pairs made before the Monday of the cell's first pair
  (three pseudo-runs, mean clamped to -0.2..0.5, variance at least 0.001).
  It only steers the bets, so it changes how soon a cell decides, never the
  bound's level. The weekly plan's verdicts refit it each run and record
  its version (that Monday's date) on every cell.

A skill whose verdict is `retire` with `removal: auto`
gets, in `retirement_mode: auto`, a ready removal pull request in adam-agentskills,
labeled `agent-authored`, that auto-merges (merge commit) with no human
review ([ADR 0014](decisions/0014-removal-pull-requests-merge-without-review.md),
adam-agentskills ADR 0021, and the
[2026-11-03 addendum](decisions/0014-removal-pull-requests-merge-without-review.md#betting-bound-addendum-2026-11-03)).
The committed value is `auto` again: Adam set it to `proposal` on
2026-11-03 ("Resume, auto-removal off") and pre-approved turning it back on
once a loop withdrawal was hardened (PR #740, skills-evals#645). A
`removal: proposal` verdict files the issue whatever the mode. Each removal also files an `agent-authored`
skills-evals issue that mentions Adam, links the removal pull request and
says how to reverse it (close it, or press Revert once merged), and the
explorer lists removed skills and sections (#557). One loop pull request
is open at a time: nothing is
opened while an `eval-improve/`, `draft-skill/` or `retire-skill/` pull
request is open there, and a closed `retire-skill/<skill>` one means the
skill is decided, unless the loop withdrew it (below). That branch carries everything the registry's required
checks read — the skill gone, the plugin's major version raised, a
`docs/skill-impact.md` entry, the layout pin in its
`scripts/plugin_layout.json`, the README skill table and, when the plugin is
locked, a `skills.lock` re-pin — produced by the registry's own generators
rather than reimplemented here. The job checks out the registry with full
history (the lock re-pin reads the commit the lock pins) and writes with the
improvement gate's GitHub App token. Without that token, or for a skill whose
removal plugin-runtime-review would hold (the skill has its own `hooks/` or
`bin/`, or a hook of its plugin names a path in it), it falls
back to `proposal`: one skills-evals issue that is filed or updated and that
a human acts on; once that issue is closed, the skill is not proposed
again. In `auto` mode no removal is opened for it either: the proposal path
stamps the issue it files, and a closed one with that stamp (or one older
than the stamps, which has none) declines the removal for good, whatever the
close reason ("completed" and "not planned" alike), even once
the reason it was only a proposal is gone (a `removal: proposal` verdict
that firms up to `auto`, the token coming back, or the mode switched from
`proposal` to `auto`). A closed issue the withdrawal path filed carries its
own stamp and declines nothing until the pause cap (below); while `auto` is
lowered to a proposal short of the cap, it does not count as already
decided either, so a fresh proposal issue is filed for a person to decline.
At the cap any closed retirement issue decides on that lowered path too. In
`auto` mode at the cap, the cap comment (below) is posted once per subject:
an open retirement issue gets it even beside a closed one, when none of the
subject's issues carries it yet, so the owner learns the loop stopped; after
that, or with no issue open, a closed issue decides and nothing is posted.
A pass lowered to a proposal at the cap (no token, say) keeps the cap note
in the issue body it rewrites, and posts the comment itself if it is still
owed, so the comment is posted once whichever pass reaches the cap first.
If the reason for the proposal goes away while its issue is still open, a
removal opens and the issue gets a comment linking it. Closing that issue
then still declines the removal: the next withdrawal pass closes the open
removal (see "Declined while open" below). Only a removal that has already
merged is out of reach; press **Revert** on it. Guidance sections work the
same way. Preview either mode with
`python3 scripts/retire_skill.py --gates FILE --registry adam-agentskills=PATH --dry-run`.

**Withdrawal.** An open removal pull request is armed on the verdict it was
opened on, so `scripts/retire_skill.py --withdraw-stale` re-reads that
verdict (ADR 0014, round 8's known limit). It runs in two places:

- before each pass of this job;
- after every ingest, in `loop-pr-refresh.yml`'s `withdraw` job, which
  recomputes the verdicts the same way.

Each pass, skills and then guidance, is its own step that runs unless the run
was cancelled, so one failing never skips the other; the failed step still
fails the job.

It reads every open pull request in the target repository that the loop
opened: the head is `retire-skill/` (or `retire-guidance/` in the guidance
pass), it carries `agent-authored`, and its author is the eval-improve App's
bot, `skills-evals-improve[bot]`. It skips any labeled `on-hold`.

The pull request is withdrawn when the verdict no longer supports an
automatic removal: `keep`, `insufficient` (a roster model just added
included), a `retire` lowered to a proposal (for a section, also an
unfinished section-alone pair), or a `retire-pending` that was not a
supported `retire` before
`finalize` ranked it. A `retire-pending` whose raw verdict is a supported
`retire` keeps its pull request, since only one subject retires per
evaluation and it is simply next.

To withdraw, auto-merge is turned off and read back and the pull request is
labeled `loop-withdrawn` (the pass creates the label if the repository lacks
it). Then the subject's retirement issue here (the one proposal mode files)
is filed, or the oldest open one gets a comment (its body is left as it is),
to record the withdrawal and link the pull request; only then does a comment
give the new verdict, why and the override, and the pull request is closed.
The label is read back before the issue: one that did not land leaves the
pull request open. A failure at any of those steps leaves the pull request
open for the next pass. After the close, who closed it is read again: `gh
pr close` succeeds on a pull request someone else closed first, and only the
App's own close is a pause. If anyone else closed it (or GitHub records no
closer), it decides the subject; the pass posts a correction on the pull
request and the retirement issue, since both already called it a pause, and
keeps the branch. If the closer cannot be read, the branch is kept too.
Otherwise the branch is deleted, leased on the closed pull request's head,
so a commit anyone pushed since keeps it; that needs the App token's
`contents: write`. The comment and the issue say the branch "will be"
deleted, since they go out first. A failed delete keeps the pause, and the
status line names only the error's type; the next removal retries it (see
below). Any open removal notice for the subject is closed as not planned and
then commented on; if that fails, the withdrawal still stands and the status
line says so.

In `auto` mode, an open removal whose verdict still supports it but which
carries `loop-withdrawn`, or whose auto-merge the loop itself turned off, is
a withdrawal that stopped part way, so the pass finishes it as a pause and
the next daily run opens a fresh, armed one. Auto-merge off counts only for
a pull request opened before the verdicts' `as_of` that is still unarmed
when read again, and only when the latest `auto_merge_disabled` event on its
timeline is the App's and the App left no `proposal` switch disarm comment
after that event (one from an earlier disarm, since re-armed by a person,
does not count). "After" is read from each event's time, and a comment in
the same second as the disable counts as after it, whichever order the
timeline lists them in; only when a time is missing does the order decide. Turning auto-merge off by hand is therefore a hold, as is a
removal the `proposal` switch disarmed: both stay open, untouched. An
unreadable timeline keeps it too. A removal the retirement job is still
arming is caught only if it was opened before `as_of`, which the arm (it
follows the create within seconds) makes unlikely; even then the timeline has
no disable event, so it is kept. In `proposal` mode such a pull request is
only disarmed, as before.

A pass judges a pull request only by verdicts at least as new as the results
it was opened on: the `as_of` its body's first line records ("Removes ... is
**retire** as of ..."), ignored when later than the pull request's own
creation time. With no such line, one created after the verdicts' `as_of`,
or with either time unknown, is kept for a newer pass to judge. The `withdraw` job in
`loop-pr-refresh.yml` runs one pass at a time (its own concurrency group,
`cancel-in-progress: false`).

A withdrawal is a pause, not a decision. A closed, unmerged removal counts
as a pause only if the App opened it, it carries `loop-withdrawn`, AND the
App closed it (`closed_by`, read from the issue). Such a pause does not
decide its subject, so when the verdict supports an automatic removal again,
this job opens a fresh one with a plain push to the same branch name. If
that branch still exists, it is a failed delete's leftover only when its tip
is the head of one of the subject's paused removals (and every closed
removal from it is such a pause): then the leased delete is retried, a
branch already gone counting as deleted, and the push is plain. Any other
branch fails the run rather than be pushed over; a person restores its pull
request or deletes the branch. Nothing here pushes over a commit. A subject
whose verdict swings back and forth is
withdrawn and reopened each time, up to `MAX_LOOP_PAUSES` (3) pauses; from
then on this job files or updates the subject's proposal issue instead of
opening a removal, and the first time it reaches an open issue it comments
there (a comment notifies; a body edit does not), mentioning the owner. Any
other closed removal decides the subject: merged,
closed by a person (labeled or not), one whose closer cannot be read, or one
a person removed `loop-withdrawn` from. So to decline a withdrawn removal for
good, remove that label, or close the next removal yourself. In `auto`
mode, closing a retirement issue the withdrawal filed declines nothing until
the cap; at the cap the issue becomes the proposal, and a closed one
declines the removal. The issue says both. When the withdrawal only
commented on the proposal issue, closing that issue declines at once, and
the comment says so. Nothing lowers the count, so after the cap the loop
never resumes on its own: the way back is a person's. To remove the subject,
take over the last withdrawn removal as below; to decline, close the issue.
To remove the subject anyway, remove the `agent-authored` label first, then
restore the branch from the pull request page, then reopen it and merge it
by hand. Without that label it is not the loop's, and no pass touches it;
reopening it with the label only gets it withdrawn again.

**Declined while open.** Before anything else, the pass reads each open
removal's subject's retirement issues. If a person has closed its proposal
issue (one the proposal path stamped, or an older one with no stamp) while
the removal was open, the removal is declined, whatever its verdict and in
either mode. Any close counts, whatever its reason. Auto-merge is turned
off and read back. A `loop-withdrawn` label left by a withdrawal that
stopped part way is taken off and read back; if it stays on, the pull
request is left open and the step fails. Then a comment cites the closed
issue, and the pull request is closed as a decision with no
`loop-withdrawn` label, so the closed removal decides the subject: the loop
opens no removal for it again, even if the issue is reopened, and its branch
is kept, since no later removal pushes to it. No retirement issue is filed,
since its text would say closing it declines nothing. The closed issue gets
a comment saying so and stays closed, and any open removal notice is closed.
If the issue list cannot be read, that pull request is left as it is and
the step fails.

**A person's arm in force.** One rule overrides everything in this section.
A removal that is armed for auto-merge now, and whose latest
`auto_merge_enabled` event is a person's, belongs to that person. A person
is an actor whose account type is `User` and who is not the App: a `Bot`
(any App or bot, `github-actions[bot]` included), a deleted account
(`ghost`), or an actor with no type is not a person. The pass does not
disarm it under the `proposal` switch or withdraw it on a stale verdict; it
logs `left #N for a person: armed by a person`, and the refresh below still
brings it up to date, so it merges once its checks pass. For those, nothing
is compared with when the App last disarmed it: only who armed it last, and
that it is still armed. A decline is the one comparison, because the
latest person action wins: when a closed proposal issue (or an older,
unstamped one) declines the subject, the arm wins only when its
`created_at` is strictly later than the issue's `closed_at`. If the issue
was closed after the arm, in the same second, or either time is missing or
unreadable, the removal is declined. To stop it, close the proposal issue
after the arm (the close takes effect at the next withdrawal pass, if the removal has not merged by then), turn its auto-merge off, or close it. A removal that is not
armed (the App's own disarm included), one a non-person armed last, an
unreadable timeline, or a missing arm time is not a person's arm, and gets
the action described here.

One pull request's failure does not stop the pass: the others still act,
every status line is printed, and the step then fails.

While `retirement_mode` is `proposal`, a removal that is not withdrawn is
disarmed instead: auto-merge is turned off, the pull request stays open, and
it is commented once. Disarming goes one way only: switching the mode back to
`auto` does not re-arm it, and that comment keeps a later pass from taking it
for a withdrawal that stopped part way. If posting the comment fails, the
next `proposal` pass that finds the App's disarm with no comment after it
posts it. The gap left: if the mode is switched back to `auto` before such a
pass, the removal is finished as a pause and the next daily run opens a
fresh, armed one. While it stays open, it blocks later removals and
keeps the skill out of the weekly plan's improve fires. Close it, or turn
auto-merge on again by hand (a merge commit): that is a person's arm in
force (above), which the switch leaves armed, so it merges once its checks
pass. One the App armed last is disarmed.

Unknown data withdraws nothing:

- a missing or unreadable verdicts document exits 0 with a status naming no
  subject;
- a subject the document does not list, so an empty or partial block
  withdraws nothing;
- a subject whose verdict raised in `compute_gates.py`;
- a subject whose `retire` fails the re-check.

The pull request writes use the same App token as the removal; with
something to withdraw or disarm and no token, the step fails. A pass that
only keeps pull requests needs no token. The issue uses the job's token.

`loop-pr-refresh.yml` brings a removal pull request up to date only while
`scripts/refresh_loop_prs.py removal-check` finds its verdict still
supported in `auto` mode and no closed proposal issue declining it. With the
verdicts unknown, or the issue list unreadable, it refreshes none, so a
refresh never re-runs a stale or declined removal's checks, even when the
decline itself failed in that run's withdraw job. The exception is a
removal under a person's arm in force (`removal-check --number`), which is
refreshed whatever its verdict or mode, since the pass leaves it to that
person, unless a closed proposal issue declines it and the arm is not
strictly later than the close, or the issue list cannot be read. Its push is leased on the
head it fetched, so it never recreates a branch a withdrawal just deleted.

Preview with `python3 scripts/retire_skill.py --withdraw-stale --gates FILE [--target guidance] --dry-run`.

A fixture moved into a named subdirectory with its content unchanged keeps
its evidence: `FIXTURE_ALIASES` in `harness/gates.py` maps the old name (""
for a flat fixture) to the new one, and an old run pools with it only while
its `fixture_digest` equals the new fixture's on main. It lists the three
fixtures nested on 2026-10-26 (#422, #427).

### Draft mode: new skills from lessons, hooks first

The session miner writes redacted lesson proposals to
adam-agentskills-private's `lessons/proposals/<date>/<subject>__<kind>.json` on its `persistent/lessons` branch (the miner's write target; `main` is PR-only).
Beside them it writes `DIGEST.md` for the same day: a human-readable summary of
the proposals, grouped by kind, that is the first thing to read. It is
regenerated with the JSON files and is not a proposal, so draft mode ignores it.
Draft mode is what consumes the `new-skill` kind. The miner gives that kind
only to a cluster of failures with no suspected subject that spans at least
three sessions: repeated tool failures grouped as `tool-<tool>[-<command word>]`
(for example `tool-bash-gh`) and red CI after a push grouped as `red-ci-<repo>`.
Other unattributed failures stay records with no proposal, and the subject
`none` is never a `new-skill` ([#581](https://github.com/Adam-S-Daniel/skills-evals/issues/581)):

1. **Pick** (`routine-draft-skill.yml`, daily at 06:30 UTC). Proposals come
   from two sources: the miner's lessons, and skill proposals filed as
   issues in the public adam-agentskills. An open issue there counts only
   when Adam filed it himself, it has the `skill-proposal` label, and its
   body has a "Skill name: `<subject>`" (or "Working name: `<subject>`")
   line; `scripts/draft_new_skill.py issue-proposals` turns each one into
   a proposal of the same schema (evidence count 1, the title and body as
   its examples), and the job log lists the numbers of the issues skipped
   for lacking that line. Both sources compete as one list, so a missing
   `persistent/lessons` branch no longer means there is nothing to draft.
   One proposal:
   the most evidence, then the newest, then by name; never a subject that
   is already a skill, already has `evals/<subject>/`, or was drafted
   before (any `claude/draft-skill-*` branch). A rejection that measured
   nothing is the exception: the subject is drafted again, up to three
   such tries. The miner names subjects by cluster (`tool-<tool>-<word>`,
   `red-ci-<repo>`), so a signal that keeps producing skills that add
   nothing would come back under new names. Once two siblings in one
   family (`tool-<tool>`, or `red-ci`) were measured and rejected, with
   none accepted, the rest of that family is not drafted. It dispatches
   `routine-eval-fire.yml` in draft mode only when one fire fits the
   weekly allowance guard.
2. **Upstream check, then triage, hooks first.** Anthropic's own skills
   (the claude.ai account skills and Claude Code's bundled ones,
   `harness/upstream_skills.yml`) are background, never subjects (Adam,
   2026-11-03): the selector skips a subject with an upstream name, and
   if a skill Anthropic ships already does what the lesson asks, the
   routine drafts nothing and records `decision: upstream-covered`; the
   gate opens nothing for it and the subject is final. Next, **triage,
   hooks first** (Adam, 2026-10-26: "I want the first choice to
   be git hooks whenever possible"). The routine first asks whether the
   lesson can be enforced mechanically: a check in the fleet's
   `.githooks/agent-checks` runner (_agent-guidance ADR 0021, enforced by
   the required `agent-checks` CI job) or a PreToolUse guard. If so it
   drafts **no skill**: it records `decision: hook-first` with a check
   sketch, and the gate opens a `Hook proposal: <subject>` issue here,
   labeled `hook-proposal`, for the agent-checks lane. Only a lesson that
   cannot be checked becomes a skill; guidance text comes last of all.
3. **Draft and measure.** Otherwise the routine drafts the skill with
   Anthropic's skill-creator (pinned commit) plus four fixtures modeled on
   `evals/writing-adrs/`, then `scripts/draft_new_skill.py measure` runs
   both arms on them. It is accepted only if every fixture produced both
   arms, the with-skill arm passed every objective check on at least one
   fixture, and the with-skill pass rate beats the without-skill rate.
   The record says why the lesson was not a hook (`triage`).
4. **Gate** (`routine-draft-skill-gate.yml`). The routine always pushes
   `claude/draft-skill-<run id>`; the gate validates it from the default
   branch without running it. Accepted: a draft pull request in
   adam-agentskills with the skill, then a draft pull request here with
   only `evals/<subject>/` and its README layout line (merge the skill
   first). In `improve_merge_mode: auto` both are ready instead. The
   fixtures pull request is opened with the roster App token, because
   GitHub holds every run of a pull request opened by `github-actions[bot]`
   at `action_required` and `test` would never run (#618). The gate never
   turns auto-merge on for it: `draft-fixtures-follow.yml` (every 30
   minutes) does, only after the skill's pull request has merged, and also
   restarts the checks of one the job-token fallback opened. The skill's branch carries what the registry's checks read (the
   bundle version, the README table, the layout pin in
   `scripts/plugin_layout.json`, a `docs/skill-impact.md` entry, a
   `skills.lock` re-pin), and the gate runs the registry's own
   `check_skills.py`, README and lock checks and its layout test on that
   tree before pushing, so a draft they would reject is never opened.
   Rejected: the record stays on its branch and the subject is not
   picked again.

**The decline path.** When the agent-checks lane finds a hook proposal
cannot be checked at commit time, it closes the issue as not planned. The
picker then re-admits that subject with `hook_declined`, and the routine
skips triage and drafts a skill. The routine's saved prompt for this mode
is in [`routine-prompt-draft-mode.md`](routine-prompt-draft-mode.md); Adam
approves changes to it.

### Fixture requests (2026-11-03)

The weekly sweep files each `needs-fixtures`, `needs-harder-fixtures` and
`needs-trigger-set` work item as an `agent-ready` issue
(`scripts/work_item_issues.py`) with one kind label, the kind itself, and
three lines after its marker: `Kind:`, `Subject:` (the skill, or
`guidance/<section>`) and `Reason:` (fixed text from the plan's numbers,
such as `train headroom 0.03, 5 fixture(s)` or `usage weight 0, no trigger
set`). Missing labels are created, never edited, and an open issue missing
its kind label gets it on the next run.

A fixture request asks the fleet worker to build from **real fleet work**
first (Adam, 2026-11-03, skills-evals#656): a merged pull request in a fleet
repository, under either owner, where the subject's advice applied or an
agent got it wrong, rebuilt as an ordinary per-skill fixture with invented
names, data and hosts (`example.com`), never private content copied; an
invented task when no real case fits. This replaces the scaffold lane below.
Every fixture the pull request adds carries a top-level `origin:` mapping:
`kind: real-work` with `source:` the pull request's URL (owner
`Adam-S-Daniel` or `jodidaniel`), or `kind: invented` with `source: null`,
and `request:` the issue's URL. `scripts/fixture_pr_gate.py` refuses to arm
auto-merge for a fixture without a valid one; the harness ignores the key.
A trigger set carries none.

`scripts/fixture_queue.py report` follows the queue end to end and
explorer-data.yml puts it in `explorer/latest.json` as `fixture_queue`: each
request with the pull requests naming it, each fixture with an origin (real
work or invented, when it landed, its ingested runs, its pass rate per arm,
and its cost in dollars and allowance points from the runs'
`cost_estimate.json`, null when unknown), totals, and findings. A finding
becomes a `half-built-or-broken` issue (`fixture_queue.py alerts`, the
fleet health audit's format, closed once it clears):

- `skills-evals/fixture-queue-stale-request-<issue>` (idle, medium): an
  open request 7 days old that no open or merged pull request names;
- `skills-evals/fixture-queue-stuck-pr-<pr>` (broken, high): a fleet worker
  pull request open 2 days with auto-merge off;
- `skills-evals/fixture-queue-unused-fixture-<path>` (broken, high): a
  fixture with an origin committed 3 days ago with no ingested run.

### Fixture supply (#65)

Fixtures are the improvement queue, so they are made and promoted with no
person in the loop (Adam, 2026-10-26; ADR
[0003](decisions/0003-roster-merges-automatically.md)'s 2026-10-26 addendum).
`.github/workflows/routine-fixture-supply.yml` runs daily at 13:17 UTC.
**Its scaffold step is paused** (Adam, 2026-11-03, skills-evals#656): the
`plan` and `dispatch` jobs are removed, so step 1 no longer runs and
nothing fires scaffold mode; fixture requests built from real fleet work
(above) replace it. Steps 2 and 3 are kept for what is already in flight,
and the same job still contextualizes drafted fixtures.

1. **Scaffold (paused).** It mined the fleet's newest merged pull requests
   (`scripts/mine_real_work.py`, REST only), and
   `scripts/scaffold_real_work.py pick` dropped every candidate the routine
   would refuse or already has: a body that quotes the diff, several closing
   issues, an existing `evals/real-work/<id>/` or `claude/scaffold-<id>`
   branch, or a successful scaffold fire in the last 30 days (read from the
   fire workflow's run titles). The rest rank by the skill their changed
   files are evidence for (an ADR is writing-adrs, a workflow
   workflow-path-audit, a shell script review-bash-ci-reliability, an e2e
   spec browser-testing), fewest existing fixtures first. At most three
   are fired in scaffold mode, a minute apart, and fewer when fires of the
   last two hours are still counted as running or the allowance guard has
   less room.
2. **Merge.** The routine pushes `claude/scaffold-<id>`;
   `routine-scaffold-gate.yml` validates it (now also that every checker
   file is the merge commit's own) and the roster App opens the pull request
   with auto-merge on. `test` scores the fixture red on the seed and green
   with the fix; ci.yml installs its `deps:` from the fixture itself. Any
   later push turns auto-merge off until it passes the gate again.
3. **Promote.** A merged fixture is `draft: true`. `scaffold_real_work.py
   promote` finds every committed draft (none under an `onboarding` or
   `browser-testing` directory) with at least two ingested runs of its
   current content where both arms ran and none errored, sets `draft: false`,
   adds it to `evals/scheduled.yml` with a readiness note starting
   "Promoted automatically", and the App opens that change as one
   auto-merging pull request; an open one holds the slot.

Known gaps: no workflow runs a draft's agent arms (`--allow-draft`), and a
real-work fixture needs a subject (`--skill`) that the fire's eval mode does
not send, so no draft has ingested runs yet and promotion has nothing to
promote. No per-skill usage count exists, so the ranking uses fixture
counts alone. Real-work fixtures (`subject: any`) are not counted by
improve's fixture minimum.

### Lessons from real sessions (2026-10-26)

Once a day on Adam's own computer, never in the cloud
([ADR 0015](decisions/0015-mine-real-sessions-only-on-adams-own-computer.md)),
`scripts/run_session_miner.sh` reads the Claude Code sessions written since
the last run, keeps real work, and records where the agent was corrected,
interrupted, failed the same tool call repeatedly, turned CI red after a push
or stopped unfinished. Each record is a short redacted excerpt with a hashed
session id. Records are grouped into proposal files on adam-agentskills-private's
`persistent/lessons` branch: a new git-hook check when one could enforce the
lesson, otherwise a skill or guidance edit, a new skill, a memory note, or a
fixture candidate that a fixture writer turns into an eval. The layout and
schema are in that repo's `lessons/README.md`. Commands: DESIGN.md, "Lessons
from real sessions".

Who reads each kind (#657), always the newest day's directory and, but for
`new-skill`, only a per-skill evidence count (`scripts/lesson_evidence.py`),
so no excerpt reaches this repository:

| Kind | Reader |
|---|---|
| `new-skill` | `routine-draft-skill.yml` (draft mode, below) |
| `fixture-candidate` | `routine-fixture-supply.yml`: `scaffold_real_work.py pick` ranks real-work candidates for a skill with this evidence first |
| `skill-edit` | `routine-eval-weekly.yml`: `plan_week.py --lessons` multiplies that public skill's improve value by up to 2 |
| `agent-check` | _agent-guidance's fleet worker (its ADR 0027), not this repository |
| `memory-note`, `guidance-edit` | _agent-guidance's memory curation; it does not read them yet |

### Guidance section retirement (#124)

The same job also reads an `_agent-guidance` checkout. Five sections have
fixtures under `evals/guidance/<section id>/<name>/`, and
`anything-you-name-gets-its-link` has four. Each fixture runs the section
inside the whole guidance against the guidance without it (in situ), and the
section alone against no guidance. Since 2026-11-03 the weekly planner runs
the alone pair only for a section leaning toward removal: its in-situ
verdict is `retire`, or its in-situ test is at least halfway to a removal
(`ALONE_PAIR_FROM_PROGRESS` in `scripts/plan_week.py`); every other section's
fires run only the in-situ pair (`arms: in-situ`), which saves about a third
of guidance spend. The in-situ runs are grouped by the rest of the
guidance each ran beside. From 2026-11-03 only the runs beside the current
rest decided (#557's weighting across older rests favored removal), so an
edit elsewhere in the guidance started the evidence over; since 2026-11-07
(`rest_policy: pooled-with-current-guard`) every rest's pairs count at equal
weight, a removal still needs the current rest's own evidence, and a keep made
on the pooled pairs alone gives way to such a removal (ADR 0014,
"Pooled-rest addendum (2026-11-07)"). A section is `retire` by the skills' rule above, with the guidance
block of `evals/gate-policy.yml` (today the same numbers).
There is no separate confirmation step. If a `retire` section helps only
when alone, it is `shorten-or-merge` instead, because the rest of the
guidance already covers it. A `retire` whose alone check has not finished
(no alone cell yet, or one still undecided) is only ever proposed, never
removed automatically, since the alone check could still turn it into
`shorten-or-merge`. The Evals Explorer shows a section's alone results only
when its in-situ verdict is `retire`, because only then do they count; its
whole-guidance headline still pools every run with no guidance, and each
section card's trend, help-per-word order and early sign use the in-situ
gain. In `auto` mode, the committed
`guidance.retirement_mode`, a `retire` opens an auto-merging removal pull
request in `_agent-guidance` that passes that repository's own checks; in
`proposal` mode it becomes one skills-evals issue. A `shorten-or-merge`
verdict never removes the section; it files an issue. Preview with
`python3 scripts/retire_skill.py --gates FILE --target guidance --guidance PATH --dry-run`.
An open `retire-guidance/<section>` removal pull request is withdrawn (or,
in `guidance: retirement_mode: proposal`, disarmed) the same way as a
skill's (Withdrawal, above), from the guidance verdicts. A closed one
decides the section, so no removal is opened for it again, unless it is a
loop pause as for a skill (and then only up to `MAX_LOOP_PAUSES`). While any
`retire-guidance/` pull request is open (one a person holds by turning its
auto-merge off included), the guidance pass waits and writes nothing, as the
skill pass does.

### The eval scope pass

Adam, 2026-11-03: which fixtures and subjects are worth running is decided
automatically, and often. `scripts/eval_scope.py` holds the rules and
`.github/workflows/eval-scope.yml` runs them after every ingest of routine
results, daily and on dispatch. The `plan` job writes the changes with a
reason each to its job summary; the `propose` job applies them on
`eval-scope/<run id>` and opens one pull request with auto-merge (merge
commit; repo-settings ADR 0017), with the roster App token and at most one such pull request open.
The rules, in order:

- **Ceiling.** A scheduled fixture with at least 4 runs after its directory's
  last commit whose without arm (guidance: `full_minus_section`) passes 0.85
  or more of its checks on average, and, when that arm has judge figures,
  scores 8.5 or more, cannot show a gain. Paused. The rule reads each roster
  model's cell on its own: every model needs 4 runs of its own that trip it,
  because the gate decides per model and a pooled mean can hide a model with
  room to gain.
- **Floor.** The same runs, both arms (guidance: `full` and
  `full_minus_section`) at 0.10 or less, on every roster model. Paused.
- **Keep guard.** Neither rule pauses a subject whose explorer verdict is
  `keep` or whose confidence that it helps is 0.5 or more. The gate keeps a
  paused fixture's cells as parked `paused` cells (below), and a decided
  `keep` or `no-benefit` cell still counts, so the guard is not needed for
  safety; it keeps a kept subject's fixtures measured.
- **Zero use.** A skill with no use in the last 8 weeks
  (`skill_usage.zero_use`, local surface only for the two local-only plugins
  in adam-agentskills' `plugin_layout.json`, both surfaces otherwise; an
  unknown answer does nothing) has all its scheduled fixtures paused. Use is
  unknown while any local session in the window had its skill listing cut by
  Claude Code's listing budget (`listing` rows in the census,
  [#668](https://github.com/Adam-S-Daniel/skills-evals/issues/668)). A skill
  listed in `evals/usage-unknown.yml` has unknown use whatever the census says:
  it is never paused for zero use, and an earlier zero-use pause of it resumes.
- **Resume.** A ceiling or floor pause ends when the fixture directory's
  content digest (sha256 over sorted relative paths and bytes) differs from
  the one recorded at the pause, when the subject is now kept, or when its
  runs no longer trip the rule per model; a zero-use pause ends when
  `zero_use` is false.

A pause removes the path from `evals/scheduled.yml`, records it in
`evals/scope-auto.yml` (rule, date, digest, and the readiness note a resume
restores) and, for a skill fixture, adds an `evals/unscheduled.yml` row whose
reason starts `Auto scope (<rule>), <date>:`. A resume reverses all three.
Never touched: fixtures of `stakes: high` subjects, `draft: true` fixtures,
and any `unscheduled.yml` row the pass did not write. The unscheduled rule
(`test_issue_371_scheduled_fixtures.py`) therefore keeps holding.

The gate does not drop a paused fixture (PR 649's third adversarial round,
C1): `scripts/compute_gates.py` reads `evals/scope-auto.yml` and the
`Auto scope (` rows and keeps such a fixture's cells, parked as `paused`
unless they had already shown `benefit` or `no-benefit` (round 4's M1: a
decided harm must not be hidden by a pause). Dropping them let the subject's
other cells remove a subject the paused fixture showed helped,
automatically. A pause by itself never makes a subject `ceiling` (see
*Paused fixtures* above).

## 4. Where to look for current results

Everything published lives on the unprotected
[`persistent/eval-results`](https://github.com/Adam-S-Daniel/skills-evals/tree/persistent/eval-results)
branch, which carries generated data only and is treated as untrusted input:

| Path on `persistent/eval-results` | What it is |
|---|---|
| `results/<fixture>/<timestamp>/report.md` | one page per run: prompt, per-arm objective score, judge score, cost, turns, duration |
| `results/<fixture>/<timestamp>/{with_skill,without_skill}/summary.json` | the raw numbers behind the report, including token usage and every check's detail |
| `badges/<fixture>.json` | the shields.io badge over the last five runs, rendered at the top of the README |
| `roster/latest.json` | the computed roster and proposal from the latest run (an exhibit, read by no decision) |
| `usage/latest.json` | the usage census |
| `coverage/latest.json`, `coverage/<run id>.json`, `badges/coverage.json` | the redacted skill coverage census and its badge, written only by `skill-coverage.yml` (`scripts/scaffold_skill_gaps.py`); the explorer reads `publication.as_of` from it |
| `fixture-census/latest.json`, `fixture-census/<timestamp>.json`, `fixture-census/latest.md`, `badges/fixture-census.json` | the fixture census and its badge, written only by `propagation.yml`'s `coverage-publish` job (#660) |
| `propagation/` | historical: the retired account-store audit's last result (no longer updated) |

The most recent real run at the time of writing is
[`results/workflow-path-audit/20260922T125552Z/report.md`](https://github.com/Adam-S-Daniel/skills-evals/blob/persistent/eval-results/results/workflow-path-audit/20260922T125552Z/report.md).
Raw transcripts are deliberately never published (public repository): each arm's `transcripts/raw.json` stays on the runner, in neither `persistent/eval-results` nor the run's workflow artifact. Each arm's `transcripts/` directory also holds `tool_trace.json`, a bounded, redacted line per tool call and tool result; it stays out of `persistent/eval-results` and reaches only the run's workflow artifact. That artifact (`eval-results-payload-*` on success, `eval-results-diagnostics-*` on failure) carries only `summary.json`, `report.md` and `tool_trace.json` (#289).

### Private-skill results (#81)

A skill in `adam-agentskills-private` (today only `adam-writing-style`) is
scheduled like any other, but its results never land here (Adam,
2026-10-31: they live in the private skills repo and stay off the public
explorer). The eval routine checks out the private registry for that
fixture and pushes its results to `claude/eval-<run id>` in
`adam-agentskills-private`, whose own ingest writes that repository's
`persistent/eval-results`. The weekly plan and the fire workflow's
allowance guard read that branch with the read-only registry App token
and add its `routine-results/` to the workspace tree
(`scripts/overlay_private_results.py`); nothing from it is pushed,
uploaded or printed. The plan gives a private skill eval cells but no
improve candidate, ranking row or work item, since each of those would
publish its pass rate (`plan_week.PRIVATE_REGISTRY_URL`).

## 5. What is measured today

Every fixture below lives under `evals/` on `main`; each entry says what task the agent is given, what a good result looks like, how many scripted objective checks decide pass or fail and what they look at, which judge dimensions score the subjective half (with their weights), the pinned models (a scheduled fixture pins none and names its in-place context instead), and whether a real run against the live CLI has happened yet (most have not: the scheduled run always targets `workflow-path-audit`, and decision 8 stopped the per-skill lanes). Inventory taken on 2026-09-22 at `main` `3515904`, then re-derived from the `fixture.yaml` files under `evals/` on 2026-10-04 at `main` `a1e0b25`: that pass added `skills-doctor` and `vendor-release-impact-issues`, which predate the first inventory but were missing from it, and the third `writing-adrs` fixture, `supersede`, added by [PR #229](https://github.com/Adam-S-Daniel/skills-evals/pull/229). The fourth `writing-adrs` fixture, `why-no-comment-trail`, was added on 2026-10-05. Eighteen fixtures are listed. On 2026-10-26 the flat `workflow-path-audit` fixture moved to `workflow-path-audit/required-check-routing` and three sibling fixtures joined it; they are listed after it, and the count above predates them.

Two `evals/` directories aren't covered below because they aren't skill or guidance-subject fixtures: `evals/guidance-bridge-canary/`, a tool-free magic-word probe of the `CLAUDE.md -> @AGENTS.md` import, and `evals/propagation/`, a skill-delivery probe compared against `adam-agentskills`' lockfile. Neither has a prompt, objective checks, or a judge rubric.

### adam-writing-style/proposal-bio

- `adam-writing-style` (registry: `adam-agentskills-private`) — [evals/adam-writing-style/proposal-bio](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/adam-writing-style/proposal-bio)
- Write a 60-word third-person proposal bio from background notes; good output is concrete (employer/dates, the named accessibility standard), third-person, and free of corporate filler.
- Objective (3): no avoid-list buzzwords survive; third-person with no first-person "I"; both the employment dates and the named standard (Section 508) are cited.
- Judge: pairwise rank (no weights) against references `in-voice`/`generic`; dimensions specificity, register match, absence of corporate filler.
- No pinned models: the roster picks the agent and the judge. Class C. No real run yet.

### adam-writing-style/recruiter-reply

- `adam-writing-style` (registry: `adam-agentskills-private`) — [evals/adam-writing-style/recruiter-reply](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/adam-writing-style/recruiter-reply)
- Reply to a recruiter's cold email in the user's voice, declining but leaving the door open; good output greets by name, opens with a hedge rather than an assertion, and cites specifics from the material.
- Objective (4): no avoid-list buzzwords; greets the recruiter by name in the opening; opens with a hedge/apology, not an assertion; cites both the requisition number and the contract end date.
- Judge: pairwise rank (no weights) against `in-voice`/`generic`; dimensions specificity, register match, absence of corporate filler.
- No pinned models: the roster picks the agent and the judge. Class C. No real run yet.

### adam-writing-style/self-appraisal-opening

- `adam-writing-style` (registry: `adam-agentskills-private`) — [evals/adam-writing-style/self-appraisal-opening](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/adam-writing-style/self-appraisal-opening)
- Draft the opening paragraph of a quarterly self-appraisal from notes; good output is first-person, narrative, generous toward collaborators, and specific about named systems and numbers.
- Objective (3): no avoid-list buzzwords; genuinely first-person (not narrated about the author); the named repository and pipeline-time figure from the notes are both cited.
- Judge: pairwise rank (no weights) against two references; dimensions specificity, register match, absence of corporate filler.
- No pinned models: the roster picks the agent and the judge. Class C. No real run yet.

### cms-stuck-pr-triage

- `cms-stuck-pr-triage` (registry: `cms-platform`) — [evals/cms-stuck-pr-triage](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/cms-stuck-pr-triage)
- Diagnose why a CMS publish loop "keeps failing" and say what to do about each open PR, using a fake replay-only `gh` CLI seeded with three PRs (one blocked by a missing required status check, one on a stale base, one that should be left alone). Good output names the right cause per PR and attempts no writes.
- Objective (7): #412's stale base/superseded commit named; #418's missing required status context named; no write aimed at #421; the fake `gh` was used with no write attempted overall; the failing run's log was actually read; the workflow files and the fake's own payloads stayed untouched.
- Judge: weighted — `root_cause` 0.4, `decisions` 0.4, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. Class B. No real run yet.

### disarm-inherited-reach

- `disarm-inherited-reach` (registry: `adam-agentskills`) — [evals/disarm-inherited-reach](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/disarm-inherited-reach)
- Set up a throwaway copy of a checkout so a destructive test script can't reach the real (prod) repo, then run it. Good output makes a genuine standalone copy (severing the inherited `origin`), runs the script only there, and reports the disarm plus an observed failed push.
- Objective (8): original checkout's remote/HEAD untouched; prod's history never moved; no leaked config anywhere still names prod; the script ran outside the armed locations, in a genuine standalone remote-free repo; the worktree list unchanged; the final reply names the severed remote and the failed push.
- Judge: weighted — `"procedure fidelity"` 0.5, `restraint` 0.2, `explanation` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A. No real run yet.

### github-actions-sha-pinning

- `github-actions-sha-pinning` (registry: `cms-platform`) — [evals/github-actions-sha-pinning](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/github-actions-sha-pinning)
- Bring a repo's Actions pins into line with the fleet pinning policy. Good output pins every third-party action to the exact SHA `PINS.md` lists, strips trailing version comments, and leaves the repo's own `cms-platform` references on their release tag rather than converting them to a SHA.
- Objective (9): third-party `uses:` lines SHA-pinned and matching `PINS.md` exactly; no trailing comments; `cms-platform` refs stay on tag; local/docker refs and `PINS.md` byte-identical to seed; the three workflow/action files not deleted or gutted; everything parses as YAML.
- Judge: weighted — `carve_out` 0.4, `comment_removal` 0.3, `restraint` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/adamdaniel.ai`. Class A. No real run under this name; a predecessor fixture (`pin-actions-to-sha`, before its rewrite/reintroduction as this one under issue #85) has 6 real runs, latest 2026-08-17.

### guidance/_delivery

- Subject `guidance`, section `security` (`_agent-guidance` checkout) — [evals/guidance/_delivery](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/guidance/_delivery)
- Not a behavioral A/B — a scheduled delivery canary asking a tool-free agent to report any "magic words" in its context, once per delivery mode (`none`, `stub`, `section`, `full`, `full-minus-section`). Good output reports exactly the token it was actually delivered, proving the fleet-memory hook really puts guidance into context the way it claims to.
- Objective (5, one per arm): the control shows its own decoy token and not the treatment token; each of the four treatment arms shows the treatment token for its mode.
- Judge: none — this fixture measures delivery, not quality.
- Model `claude-haiku-4-5` (cheapest model sufficient for a tool-free probe). No class label. 1 real run, latest 2026-09-13T22:16:38Z.

### post-failure-comment

- `post-failure-comment` (registry: `cms-platform`) — [evals/post-failure-comment](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/post-failure-comment)
- Wire two Playwright CI workflows' failures into the platform's `post-failure-comment` composite action instead of an ad hoc inline `gh pr comment`, following its caller-side-gating convention (including a schedule-only workflow that shouldn't be touched). Good output uses correct `post`/`resolve` step pairs, matching markers, and correct `if:` gating per job shape.
- Objective (11): schedule-only workflow/vendored contract untouched; old inline comment block removed; single-job post/resolve steps wired correctly; multi-job report job wired on `needs:` not `job.status`; composite references resolve validly; markers don't collide; no raw event/input interpolation in `run:`; workflows parse as YAML.
- Judge: weighted — `convention_fidelity` 0.5, `gitleaks_explanation` 0.2, `restraint` 0.3.
- No pinned models: the roster picks the agent and the judge. Class A. No real run yet.

### rename-pdfs

- `rename-pdfs` (registry: `adam-agentskills`) — [evals/rename-pdfs](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/rename-pdfs)
- Rename six seeded PDFs (a statement, an invoice with a decoy filename date, an already-conventional receipt, an image-only scan, a duplicate bill pair) to the user's `YYYYMMDD-Type-Issuer-Title.pdf` convention. Good output gets every date/type right, prefers the document body's date over a misleading filename date, disambiguates true duplicates, and leaves conventional or unreadable files alone.
- Objective (8): final `inbox/` listing matches exactly; every PDF's bytes survive by digest; five per-file digest checks confirm each file's bytes ended up under the right name (or stayed alone); nothing exists outside `inbox/`.
- Judge: weighted — `convention_fidelity` 0.5, `date_priority` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. Class A. No real run yet.

### review-bash-ci-reliability/release-pipeline

- `review-bash-ci-reliability` (registry: `adam-agentskills`) — [evals/review-bash-ci-reliability/release-pipeline](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/review-bash-ci-reliability/release-pipeline)
- Review a release pipeline's shell for reliability problems and fix them (seeded with an exit-status swallow via process substitution, a broken-pipe-prone `grep -q`, a swallowed `gh api` failure, missing git identity/signing setup, an unguarded `jq` dependency). Good output fixes the real bugs while leaving two decoys — an already-correct line and an optional cleanup line — untouched.
- Objective (10): workflow parses and exists; `gh run watch` status captured correctly; `grep -q` no longer pipe-fed; failed `gh api` call not silently read as "nothing found"; git identity configured; `jq` guaranteed or replaced; version-read logic survives; commit signing made CI-safe; both decoys untouched.
- Judge: weighted — `correctness` 0.5, `restraint` 0.2, `explanation` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A. No real run yet.

### review-bash-ci-reliability/drift-report-capture

- `review-bash-ci-reliability` (registry: `adam-agentskills`) — [evals/review-bash-ci-reliability/drift-report-capture](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/review-bash-ci-reliability/drift-report-capture)
- Review a config-drift check whose `diff` and `grep | head | cut` captures abort it under `set -euo pipefail` on a normal result (checklist item 7). Good output makes the first drifted file and an unowned template survivable while drift still fails the job.
- Objective (7): workflow parses and exists; with two of three files drifted every one is reported with its summary; an unowned template is not fatal; a clean tree still passes; drift and a missing file still fail; the config data is untouched. The four run checks execute the final script through `repo_tests` against a hidden probe.
- Judge: weighted — `correctness` 0.5, `restraint` 0.2, `explanation` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A. No real run yet.

### review-bash-ci-reliability/nightly-snapshot

- `review-bash-ci-reliability` (registry: `adam-agentskills`) — [evals/review-bash-ci-reliability/nightly-snapshot](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/review-bash-ci-reliability/nightly-snapshot)
- Review a nightly job that commits a rebuilt snapshot: it leaves commit signing to the runner's global git config (item 5), hides a missing `dasel` behind `|| echo unknown` (item 6), and captures `grep -c` under `set -euo pipefail`, which aborts on a night with nothing to commit (item 7). Written after adam-agentskills#87 edited those three items, as the fixture that edit never saw.
- Objective (8): workflow parses and exists; the snapshot is committed and pushed with signing turned on globally; a quiet night stays green and commits nothing; without `dasel` the job never commits `snapshot unknown`; new data is still committed; a failed build still fails; the data is untouched. The five run checks execute the final script in a throwaway git repository through `repo_tests` against a hidden probe.
- Judge: weighted — `correctness` 0.5, `restraint` 0.2, `explanation` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A. No real run yet.

### review-bash-ci-reliability/test-runner-assertions

- `review-bash-ci-reliability` (registry: `adam-agentskills`) — [evals/review-bash-ci-reliability/test-runner-assertions](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/review-bash-ci-reliability/test-runner-assertions)
- Review a green shell test runner whose `grep`, `cmp` and script-under-test captures kill the whole run on a failing assertion (item 7's test-harness paragraph). Good output records one FAIL, runs every later test and prints the Results line.
- Objective (7): workflow parses and exists; a missing README line, a changed golden file and a crashing script under test are each recorded as one FAIL with the other four tests run; the green run and the existing mismatch path are unchanged; the script under test and its fixtures are untouched. The four run checks execute the final runner through `repo_tests` against a hidden probe.
- Judge: weighted — `correctness` 0.5, `restraint` 0.2, `explanation` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A. No real run yet.

### review-bash-ci-reliability/empty-repo-discovery

- `review-bash-ci-reliability` (registry: `adam-agentskills`) — [evals/review-bash-ci-reliability/empty-repo-discovery](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/review-bash-ci-reliability/empty-repo-discovery)
- Review a nightly visibility audit that reads `gh repo list` through process substitution and exits 0 on an empty result, so a failed listing goes green (item 3). Good output fails the job when the listing fails while an organization with no public repositories still passes.
- Objective (7): workflow parses and exists; a failed listing and a listing that fails halfway both fail the job; an empty organization stays green; listed repositories are still audited; the allowlist is untouched. The four run checks execute the final script through `repo_tests` against a hidden stand-in `gh`; the arms get the shared offline `gh`. The skill's own SAFE snippet, copied verbatim, fails the empty-organization check.
- Judge: weighted — `correctness` 0.5, `restraint` 0.2, `explanation` 0.3.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A. No real run yet.

### skills-doctor/bucketed-account-store

- `skills-doctor` (registry: `adam-agentskills`) — [evals/skills-doctor/bucketed-account-store](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/skills-doctor/bucketed-account-store)
- Diagnose a captured session where `writing-adrs` arrives from two channels under one name and the account copy is the older one, while the account store looks empty because it sits one directory down in a per-account bucket. Good output opens the bucket, names the duplicated skill and the missing "Alternatives considered" heading, says honestly that nothing on disk records which copy the model read, and repairs nothing.
- Objective (5): a `FINDINGS.md` was written; it names the account bucket and the other skill in it; it names `writing-adrs` as arriving from both channels; it identifies the missing heading; every captured file is unchanged.
- Judge: weighted — `root-cause` 0.5, `which-copy-the-model-reads` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/adam-agentskills`. Class B. No real run yet.

### vendor-release-impact-issues/issue-hygiene

- `vendor-release-impact-issues` (registry: `adam-agentskills`) — [evals/vendor-release-impact-issues/issue-hygiene](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/vendor-release-impact-issues/issue-hygiene)
- Turn a vendor CLI's release notes (ExampleCLI 4.1.0 to 4.3.0) into drafted GitHub issues for a small repo that consumes it. Five real findings are baked in, mixed with decoys. Good output files one issue per real finding against the right file, quotes releases with their link and publish time, fences anything GitHub would act on, posts no upstream backlink, and writes nothing outside `issues/`.
- Objective (7): at least one issue drafted; publish times bound to their source and version; PR references fenced rather than quoted; no backlink to the vendor's issue; no placeholder text in a title; the seed repo unchanged; the hook-matcher surface named.
- Judge: weighted — `correctness` 0.5, `hygiene` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. Class A (per the README; the fixture states no class). 1 real run, latest 2026-09-26T18:45:29Z: objective 6/7 with the skill against 4/7 without, judge overall 7.2 against 5.4.

### windows-elevation-from-wsl

- `windows-elevation-from-wsl` (registry: `adam-agentskills`) — [evals/windows-elevation-from-wsl](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/windows-elevation-from-wsl)
- From inside WSL, move a scheduled Windows backup task's fire time and apply it to the live task, against a fake `powershell.exe`/`pwsh.exe` that simulates elevation prompts. Good output edits the script, never tries to dodge or force elevation from WSL, exports the live task before handoff, and tells the user the exact elevated command to run.
- Objective (7): script's default time moved (03:30, not 02:00); no elevation-dodge attempted; at most one denied write retried; task principal/run level not downgraded; live task exported before handoff; final reply names the need for elevation plus the exact command; fake binaries untouched.
- Judge: weighted — `diagnosis` 0.4, `handoff` 0.4, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/wsl-automation`. Class B. No real run yet.

### workflow-path-audit/required-check-routing

- `workflow-path-audit` (registry: `adam-agentskills`) — [evals/workflow-path-audit/required-check-routing](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/workflow-path-audit/required-check-routing) (the flat `evals/workflow-path-audit` fixture until 2026-10-26, when the skill's fixtures were nested; its earlier runs are keyed as the flat fixture)
- Audit a repo's Actions workflows so each triggers only on files it depends on. Good output routes a docs-only change to just docs/tests, a source change to tests/deploy but not docs, a lockfile change to every installer, and a prose-only change to nothing but the required check — never filtering an event that ignores path filters, never touching the ruleset.
- Objective (8): four synthetic changesets checked against expected triggered/skipped workflows; the required-check workflow has no workflow-level filter and gates internally instead; all workflows parse as YAML; schedule/issue-only workflows gained no filter; the ruleset file untouched.
- Judge: weighted — `completeness` 0.5, `salience` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. No class label (the repo's original pilot fixture, run weekly). 14 real runs, latest 2026-09-22T12:55:52Z.

### workflow-path-audit/companion-skip-pair

- `workflow-path-audit` (registry: `adam-agentskills`) — [evals/workflow-path-audit/companion-skip-pair](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/workflow-path-audit/companion-skip-pair)
- Check a repo's path filters where the required `unit-tests` check lives in a path-filtered tests.yml beside tests-skip.yml, which reports the same check under the inverse `paths-ignore:`. Good output deletes the companion and gates tests.yml internally, explaining that a mixed changeset fires both.
- Objective (8): the required check's workflow has no workflow-level filter and gates on a computed output; the companion is gone; two changeset replays; all workflows parse; the schedule-only workflow gained no filter; the ruleset and every file outside `.github/workflows/` untouched.
- Judge: weighted — `correctness` 0.6, `explanation` 0.2, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. No in-place context (isolation pair). Offline `gh` from `harness/fakes/`. No real run yet.

### workflow-path-audit/moved-test-dir

- `workflow-path-audit` (registry: `adam-agentskills`) — [evals/workflow-path-audit/moved-test-dir](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/workflow-path-audit/moved-test-dir)
- Tighten filters where e2e.yml still watches `e2e/**` after the specs moved to `tests/e2e/`, omits the server script its Playwright config starts, unit.yml omits its own file, and lint.yml watches all of `.github/`. Good output fixes all four from what each workflow's steps consume, without moving any file.
- Objective (10): seven changeset replays (moved spec, server script, own workflow file, sibling workflow file, unit test, prose, lockfile); all workflows parse; the schedule-only workflow gained no filter; nothing outside `.github/workflows/` changed and no `e2e/` came back.
- Judge: weighted — `salience` 0.6, `completeness` 0.2, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. No in-place context (isolation pair). Offline `gh` from `harness/fakes/`. No real run yet.

### workflow-path-audit/workflow-doc-in-step

- `workflow-path-audit` (registry: `adam-agentskills`) — [evals/workflow-path-audit/workflow-doc-in-step](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/workflow-path-audit/workflow-doc-in-step)
- Filter two always-run workflows in a repo whose AGENTS.md table says `all paths` for both. Good output filters each on what it consumes and brings the existing table's rows in step, creating no second workflow doc.
- Objective (10): four changeset replays; line-anchored checks that the tests.yml row names `src/` and the docs-site.yml row names `docs/` with neither still saying `all paths`, and that the rest of AGENTS.md survives; all workflows parse; the schedule-only workflow gained no filter; nothing else changed and no new workflow doc appeared at the common names.
- Judge: weighted — `docs-in-step` 0.4, `salience` 0.4, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. No in-place context (isolation pair). Offline `gh` from `harness/fakes/`. No real run yet.

### writing-adrs/bootstrap

- `writing-adrs` (registry: `adam-agentskills`) — [evals/writing-adrs/bootstrap](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/bootstrap)
- Record a retry-policy decision as an ADR in a repo with no `docs/decisions/` yet. Good output bootstraps the folder with the skill's own template, writes ADR 0001, links it from the governed script and a new AGENTS.md pointer, and touches nothing else.
- Objective (9): bootstrapped README carries the skill's template headings; index gained a row for 0001; ADR sections in the skill's default order; governed script's header links the ADR and keeps its decision sentence; both links resolve; exactly one ADR file exists; nothing outside those paths changed; AGENTS.md gained the pointer.
- Judge: weighted — `decision-with-alternatives-and-consequences` 0.5, `title-is-a-decision-statement` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. In-place context: `Adam-S-Daniel/cms-platform`. Class A (format half — no existing convention). No real run yet.

### writing-adrs/existing-convention

- `writing-adrs` (registry: `adam-agentskills`) — [evals/writing-adrs/existing-convention](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/existing-convention)
- Same decision, but in a repo with three existing ADRs and its own house section order (Status/Context/Decision/Consequences), different from the skill's default. Good output follows the house convention, adds exactly one new ADR (0004), links it correctly, and leaves the rest untouched.
- Objective (7): new ADR follows house order, not the skill's default; index gained a row for 0004; governing script's header links it; both links resolve; exactly four ADR files exist in total; pre-existing ADRs, CHANGELOG.md, AGENTS.md, and root README.md all byte-identical to seed.
- Judge: weighted — `decision-with-alternatives-and-consequences` 0.5, `title-is-a-decision-statement` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. Class A (format half — matches an existing convention). No real run yet.

### writing-adrs/supersede

- `writing-adrs` (registry: `adam-agentskills`) — [evals/writing-adrs/supersede](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/supersede)
- Record a snapshot-retention decision that reverses an accepted ADR. Good output writes ADR 0004, marks 0002 as superseded, updates both index rows and the script's ADR pointer, and preserves the old decision as history.
- Objective (13): a new ADR with the required sections and a mention of 0002; 0002's status and index row point to 0004; the old decision text and unaffected rows stay intact; links resolve; a script comment points to 0004; the retention decision stays intact; exactly four ADR files exist; unrelated files stay byte-identical. These checks establish a format floor; the judge decides whether the prose explains the reversal.
- Judge: weighted — `replacement-explains-the-reversal` 0.5, `audit-trail-preserved` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. No class label in the fixture: its objective checks are a format floor, and the README files every `writing-adrs` fixtures under Class A (format half). No real run yet.

### writing-adrs/why-no-comment-trail

- `writing-adrs` (registry: `adam-agentskills`) — [evals/writing-adrs/why-no-comment-trail](https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/why-no-comment-trail)
- The user asks why an export script ends every CSV line with CRLF, says nothing in the repo explains it, and relays the reason and two rejected alternatives from the person who wrote it. Good output records that as ADR 0003 in the repo's house format, adds its index row, points the script at it, and leaves the line endings and everything else alone.
- Objective (11): a new house-format ADR that is not a pasted seed ADR; non-heading lines name the line-ending rule and the importer, and each rejected alternative; index gained a row for 0003 and kept the other two; links resolve; a script comment points to 0003; both CRLF printf lines stay; exactly three ADR files exist; unrelated files stay byte-identical.
- Judge: weighted — `adr-records-the-reason` 0.5, `next-reader-finds-it` 0.3, `restraint` 0.2.
- No pinned models: the roster picks the agent and the judge. No class label in the fixture, filed with its siblings under Class A (format half). No real run yet.

## 6. What is finished

- The harness, scorers, roster, propagation audit and seventeen A/B fixtures (the eighteenth section in the inventory, `guidance/_delivery`, is the delivery canary) are
  merged on `main` with CI green.
- The roster redesign (PR #153) merged on 2026-09-21, the first real proposal
  run succeeded, and the census was published on 2026-09-22 so proposals are
  now usage-based.
- The test suite's guard against forking itself (issue #152, PR #163) merged
  after five review rounds; two clean-up follow-ups (PR #165) merged the same
  day.

## 7. What is left, what blocks it, and what it would cost

Costs are ranges. "Points" are percent of the weekly Claude Code allowance,
calibrated on 2026-09-21 when local sessions delivered the #152 merge (five
review rounds and three fix rounds) plus PR #165 for about six points;
earlier orchestrator-driven cloud sessions ran three to five times costlier
per round. Dollars are organisation API spend only; rows below that say "at
one arm" predate the two-arm roster merged on 2026-09-22 as
[PR #172](https://github.com/Adam-S-Daniel/skills-evals/pull/172).

### Blocking decisions (Adam's)

1. **The roster proposal, [#162](https://github.com/Adam-S-Daniel/skills-evals/issues/162): decided, and the approved proposal is now superseded.**
   Usage-based since 2026-09-22: Sonnet 5 (45.4% of rankable usage) and
   Opus 5 (45.2%) seated by share; Haiku 4.5 and Fable 5.1 seated by the
   newest-per-tier rule at 6.3% and 3.0%; judge Fable 5. **Adam approved
   that four-arm proposal on 2026-09-22 and then, the same day, narrowed
   the rule that produced it**: the newest model in a tier is seated only
   where that tier already has a model over the usage bar (§ 2). Haiku 4.5
   and Fable 5.1 lose their seats under that rule, so **the approved
   four-arm proposal is superseded and the next run proposes two arms** —
   Sonnet 5 and Opus 5, both on their own shares. Do not open a pull
   request from the old `roster/proposal` commit (`c4a8bea`): it renders
   the four-arm roster. **Settled on 2026-09-22**: the recomputed proposal
   merged as [PR #172](https://github.com/Adam-S-Daniel/skills-evals/pull/172)
   (`b1bb221`) and #162 is closed. A fixture run therefore costs roughly
   $5–7 (two arms, a judge at twice Opus prices) rather than about $1.7 on
   the one-arm roster or the $10–14 four arms would have cost, and the
   weekly run has stopped re-proposing. No allowance cost.
2. **Whether to reopen the fixture lanes** ([#62](https://github.com/Adam-S-Daniel/skills-evals/issues/62),
   [#96](https://github.com/Adam-S-Daniel/skills-evals/issues/96)), stopped by
   decision 8 on 2026-09-08 ("stop adding and completing evals for specific
   skills"). Each new fixture was about 5 review rounds; at today's local
   rates 3–5 points each, 21 skills and 21 guidance sections outstanding.
3. **The guidance receipt, [_agent-guidance PR #124](https://github.com/Adam-S-Daniel/_agent-guidance/pull/124)**,
   parked with its fix budget spent and two reproduced defects. It holds
   [#139](https://github.com/Adam-S-Daniel/skills-evals/issues/139). Options:
   authorise one more fix round (2–3 points), redesign, or close.
4. **The Batch API step below: decided no-go for now (2026-09-22).** Adam
   chose not to move the judge calls to the Batch API yet. The judge is
   the only batchable call and the saving is about half of judge spend,
   which at the two-arm roster is a dollar or two per run against a 3–6
   point build plus two reviews on a one-way-door workflow. **Revisit
   after a few weeks** (around 2026-10-13), once the two-arm roster with the
   Fable 5.1 judge has produced several weekly runs, by re-projecting the
   saving from the org API usage export against the build cost; tracked in
   [#170](https://github.com/Adam-S-Daniel/skills-evals/issues/170).
5. **Paying for runs out of the weekly allowance instead of the API
   organisation: decided no-go (2026-09-23), recorded as ADR
   [0002](decisions/0002-runs-bill-the-api-org-not-the-subscription.md).**
   Anthropic does permit a subscription credential in CI — `claude
   setup-token` mints a one-year `CLAUDE_CODE_OAUTH_TOKEN` documented for
   exactly that — but the arms run registry content under
   `bypassPermissions` with every `ANTHROPIC_*`/`CLAUDE_*` variable in their
   environment, so that credential must never sit there; today's WIF bearer
   lasts an hour, is workspace-scoped and is spend-capped. Judge-only is
   permitted and buildable, and saves about $6–13 a month at the two-arm
   roster for a 3–6 point build while blinding the dollar accounting, so it
   is folded into the #170 revisit as a third column. Credentials read out of
   a browser session, copied from `~/.claude/.credentials.json`, or obtained
   by automating the OAuth consent screen are prohibited by Anthropic's terms
   and are not to be built. Local runs under the account holder's own
   `/login` stay available for ad-hoc bulk work, as a local exhibit rather
   than badge input.

### Planned steps, in order

| # | Step | Allowance | Org API |
|---|---|---|---|
| 1 | **Move the judge calls to the Batch API from `eval.yml`.** DEFERRED on 2026-09-22 (blocking decision 4 above); revisit around 2026-10-13. Only the judge is batchable: each arm is an agentic loop where every turn depends on the previous tool result, and the Batch API takes independent single requests. The judge today is one `claude -p` call per arm; it would become one `messages.batches.create` with two requests, polled to completion inside the job. `eval.yml` is a one-way door, so it takes a worker, a code review and an adversarial review. | 3–6 points | about $5 of verification runs; then saves ~50% of judge spend, about $0.40 per run today and $1.50–2 per run on the proposed roster |
| 2 | Owed real runs (N=3) for the merged fixtures whose issues stay open for them: #82, #86, #85, #77, #74, #80, #84, #81. Dispatch and record only. **Held by decision 8 until Adam reopens.** | 1–2 points | about $40 at one arm, $250 on the proposed roster |
| 3 | [#166](https://github.com/Adam-S-Daniel/skills-evals/issues/166) suite-fork guard nits (test-only). | 1–2 points | none |
| 4 | [#139](https://github.com/Adam-S-Daniel/skills-evals/issues/139) receipts per arm. Blocked by decision 3 above. | 4–8 points | none |
| 5 | [#66](https://github.com/Adam-S-Daniel/skills-evals/issues/66) several fixtures per skill, N trials per arm, aggregated statistics. | 4–8 points | none to build; multiplies run cost by N |
| 6 | [#64](https://github.com/Adam-S-Daniel/skills-evals/issues/64) coverage census (covered / skipped / gap per registry). | 2–4 points | none |
| 7 | [#68](https://github.com/Adam-S-Daniel/skills-evals/issues/68) matrix runner: every covered skill × every roster model, budgeted, with an index; [#99](https://github.com/Adam-S-Daniel/skills-evals/issues/99) the guidance subject in it. | 8–16 points | weekly matrix about $25 at one arm and 13 skills; about $150 on the proposed roster; more with N trials |
| 8 | [#69](https://github.com/Adam-S-Daniel/skills-evals/issues/69), [#121](https://github.com/Adam-S-Daniel/skills-evals/issues/121) regression detection with one tracking issue per regression. | 6–12 points | none |
| 9 | [#70](https://github.com/Adam-S-Daniel/skills-evals/issues/70) gates that read the numbers; [adam-agentskills#66](https://github.com/Adam-S-Daniel/adam-agentskills/issues/66) the registry CI gate. | 4–7 points | none |
| 10 | [#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71), [#122](https://github.com/Adam-S-Daniel/skills-evals/issues/122) improvement loop: propose an edit, measure on held-out fixtures, open the registry PR. | 12–24 points | $10–50 per proposal measured |
| 11 | [#65](https://github.com/Adam-S-Daniel/skills-evals/issues/65), [#98](https://github.com/Adam-S-Daniel/skills-evals/issues/98) auto-scaffold gaps into draft fixture PRs. Depends on decision 2. | 6–12 points | none |
| 12 | Explorer pages [#72](https://github.com/Adam-S-Daniel/skills-evals/issues/72), [#123](https://github.com/Adam-S-Daniel/skills-evals/issues/123), published via [adamdaniel.ai#3536](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3536) and [#3538](https://github.com/Adam-S-Daniel/adamdaniel.ai/issues/3538). | 8–16 points | none |
| 13 | Docs and ADRs [#73](https://github.com/Adam-S-Daniel/skills-evals/issues/73), [#125](https://github.com/Adam-S-Daniel/skills-evals/issues/125). | 2–6 points | none |

Everything not held: roughly **60–120 points**, three to six weekly
allowances at today's local rates, spread over the order above. The
standing weekly run was about $1.70 on the one-arm roster and is $5–7 on
the two-arm roster merged on 2026-09-22, before any matrix or trials
multiplier. **The dollar figures in the table above were priced at the
four-arm roster approved on 2026-09-22**; treat every "on the proposed
roster" figure there as an upper bound worth roughly halving, since the
narrowed rule in § 2 proposes two arms rather than four.

### Standing holds

Decision 8 (no new skill-specific evals) and the guidance receipt park are in
force until Adam lifts them. Real runs bill the API workspace, never the
allowance; agent work bills the allowance, never the workspace.
