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
