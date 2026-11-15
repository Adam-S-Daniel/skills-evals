# Automatic spend by category, 2026-11-15

Adam asked (Nov 15, 12:16 PM ET) for the forecast to break non-eval meter use
down by what runs on its own: creating new targets from transcripts,
centralizing targets and memories, the dashboard and Explorer, and every other
scheduled or event-fired job. [`scripts/automatic_spend.py`](../../scripts/automatic_spend.py)
now builds that inventory from sources, and
[`scripts/forecast_catch_up.py`](../../scripts/forecast_catch_up.py)
`--automatic-spend` folds it in. The categories are in
[`evals/automatic-spend.yml`](../../evals/automatic-spend.yml).

## Result

217 automatic jobs: 17 scheduled tasks, 189 workflows on a schedule or event
across the 16 fleet repos, and 11 BOXY scheduled tasks. Only 17 spend from the
subscription meter; 188 use GitHub Actions minutes alone, counted as $0.

| Category | Meter $/wk | Points/wk | Biggest jobs |
|---|---|---|---|
| Fleet maintenance | 74 | 10.4 | fleet worker 28 fires × $1.92; security triage 7 × $2.26; health audit |
| Dashboard and Explorer | 62 | 8.8 | dashboard refresh 14 × $4.45 (Explorer data and site freshness are Actions only) |
| Personal assistant tasks | 29 | 4.1 | another project's check-ins and briefs |
| Improving and re-checking targets | 23 | 3.3 | daily eval scope review 7 × $2.90; hook block review; prompt audit |
| Watching vendors and articles | 14 | 2.0 | changelog watcher 7 × $1.81 |
| Centralizing targets and memories | 4.5 | 0.6 | cloud memory curation 1 × $4.54; BOXY memory curation unmeasured |
| New targets from transcripts | 0 | 0 | the BOXY session miner runs no model; drafting a skill from a lesson runs inside the eval cap; public-gap drafting spends API dollars, unmeasured |
| **All automatic jobs** | **208** | **29.3** | |
| Interactive threads and local sessions | | 31.1 | the measured 60.4 points a week less the automatic 29.3 |
| **All non-eval use (measured)** | | **60.4** | |

Points use the forecast's mid rate, $7.09 a point (assumptions file).

## What it changes in the forecast

Non-eval use is now measured, not assumed:
`forecast_catch_up.py --meter-history` reads the account's weekly meter
readings, which are version-controlled privately at adam-agentskills-private
`persistent/usage-events:spend/meter-history.csv`. It measures over the whole
allowance week, from the Mon Nov 9 noon ET reset to Nov 15 at 12:39 PM ET. The
meter rose 94 points. Eval runs' calibrated points come off that rise, capped
at what the meter rose while evals ran: 42 points, against 49.5 calibrated.
That leaves **60.4 points a week** of non-eval use. This morning's forecast
assumed 105.

Use comes in bursts, so a part of the week can mislead. The eval-free stretch
from Nov 12 to Nov 15 alone gives 122.8 points a week. A first version of
this report used that figure. It was wrong: with 86% of the week gone and no
manual reset, the meter reads 94%, not the ~120% that rate would mean (Adam's
dashboard, 12:46 PM ET).

**Evals run first in the week** (Adam, 12:44 PM ET). The guard's fixed cap is
a floor (`allowance_guard.py` `room`), so from the reset evals fire until the
cap is spent. The 80% stop binds only on the other use that accrues
meanwhile. The forecast now models this with `eval_points_per_hour`, measured
from `routine-results`: the median over the two weeks that reached the cap is
0.88 points an hour, about 28 hours to spend the cap.

| | |
|---|---|
| Eval room | the full 25-point cap |
| Catch-up | **Jan 7, 2027** (Dec 30 to Jun 8), or **Dec 15** with the API credit |
| Keep-up | $119 a week, with 2 new fixtures a week |
| Your own work | 25 + 60.4 = 85 points a week, under the 100 limit (`owner_squeeze`) |

Run: [`forecast-2026-11-15-automatic.json`](forecast-2026-11-15-automatic.json),
`--set new_fixtures_per_week_open=2`.

## How the rates and costs are taken

- **Rate:** a task's own cron; for the fleet worker, its firing workflow's cron
  thinned to the 6-hour cadence (`FLEET_WORKER_EVERY_HOURS`); zero for a task
  that never fired; else ledger fires over 14 days.
- **Cost per fire:** the median over the routine fire ledger, now
  version-controlled privately at adam-agentskills-private
  `persistent/usage-events:spend/routine-fires.jsonl` (it names private tasks
  and session ids). 24 fires, Nov 9 to 15, topped up from `get_session` for
  this run.
- **Unmeasured (6 jobs, add nothing):** BOXY memory curation (runs `claude -p`
  on BOXY), the lockfile weekly check (a persistent session, no per-fire
  cost), two media-discovery workflows and the public-gap drafter (Anthropic
  API dollars, not meter), and one twice-a-year personal task.

## Gaps

- **Interactive use is a remainder:** the measured total less the automatic
  jobs. Any automatic job priced too low shows up as interactive use.
- **The meter history has gaps:** none from Nov 11, 3:24 AM to Nov 12,
  1:31 PM ET, or from 7:39 AM to 12:39 PM ET on Nov 15 (the collector's login
  expired). A rise across a gap still counts. The first gap spans the end of
  the eval runs, so "rise while evals ran" includes about 15 hours of other
  use, which makes 60.4 a slight undercount.
- **This week's evals ran past the cap** (42 points) before the guard's rate
  fix (#958). Next week's should stop at 25.
- **The ledger sees only each task's last run,** so fires between dashboard
  refreshes are lost; rates come from crons, so this affects cost samples only.
- **The centralization audit** listed on the dashboard
  no longer exists (`get_trigger` 404); its row should come off.

## Loop membership and current-model costs (1:30 PM ET)

Adam asked (1:06 PM ET) for a consistent mark on every job saying whether it
is part of the continuous improvement system, with security alert triage, the
fleet health audit and the "work locally" feature watch outside it. He also
asked that costs come only from fires on each task's current model.

- **The mark:** each category in
  [`evals/automatic-spend.yml`](../../evals/automatic-spend.yml) has
  `in_loop`. `outside_loop` and `inside_loop` override it for single jobs,
  and `other_in_loop` covers the jobs no category matches. Every job in the
  output carries `in_loop`, and the totals split meter spend by it.
- **Current model:** the model that served the task's newest fire since its
  last edit; with no fire since, its set model. A set model the fires
  ignore is flagged `model_mismatch`.

| Job | Model | Fires costed | Points/wk |
|---|---|---|---|
| Dashboard refresh | Opus | 1 | 8.8 |
| Fleet worker | Sonnet | 6 | 7.6 |
| Daily eval scope review | Opus | 3 | 2.9 |
| Agent changelog watcher | Sonnet | 3 (1 Fable fire dropped) | 1.8 |
| Git hook block review | Opus (page says Sonnet) | 1 | 0.3 |
| Prompt-audit sweep | Sonnet | 1 | 0.1 |
| Memory curation | Sonnet, no fire yet (1 Opus fire dropped) | 0 | unmeasured |
| **In the loop** | | | **21.5** |
| Outside: security triage 2.2, work-locally watch 0.2, health audit (unmeasured, Opus fire dropped), personal 4.1 | | | **6.6** |

Run: `automatic_spend.py` with a second `--triggers` dump that adds each
task's `model` and `updated_at` (list_triggers, 1:15 PM ET).

## The loop's jobs inside the 25% (1:20 PM ET)

Adam (1:10 PM ET): every automated part of the continuous improvement system
fits in the 25%. `forecast_catch_up.py` now takes the in-loop jobs' points
off the eval cap (`loop_jobs_in_cap`, on by default;
`--set loop_jobs_in_cap=0` turns it off).

| In-loop jobs (points/wk) | Eval room | Catch-up, cap only | With API credit |
|---|---|---|---|
| 21.5 (today) | 3.5 | never | never |
| 13.3 | 11.7 | never | Sep 2027 |
| 8 | 17 | 2034 | Jan 19, 2027 |
| 4 | 21 | Feb 26, 2027 | Dec 26, 2026 |

Keep-up alone costs $119 a week (2 new fixtures a week), about 17 points.
Run: [`forecast-2026-11-15-loop-in-cap.json`](forecast-2026-11-15-loop-in-cap.json);
the other rows set `loop_meter_usd_per_week` by hand to show trims.
