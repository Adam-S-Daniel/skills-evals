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
| Interactive threads and local sessions | | 75.7 | the measured 105 points a week less the automatic 29.3 |

Points use the forecast's mid rate, $7.09 a point (assumptions file).

## What it changes in the forecast

Nothing in the totals yet: non-eval use stays the measured ~105 points a week,
now split into 29.3 automatic and 75.7 interactive
([`forecast-2026-11-15-automatic.json`](forecast-2026-11-15-automatic.json),
`--set new_fixtures_per_week_open=2 --set interactive_points_per_week=75.7`).
With the 80% account stop, evals get no meter room above about 51 points a
week of interactive use. At 25.7 interactive points (55 total) catch-up lands
Jan 7, 2027, or Dec 15 with the API credit.

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

- **Interactive use is a remainder,** not a measurement: 105 minus the
  automatic total. BOXY's meter history (the seven_day readings) is still a
  local CSV; once it is version-controlled next to the fire ledger, the script
  can take the total from it instead of an assumption.
- **The ledger sees only each task's last run,** so fires between dashboard
  refreshes are lost; rates come from crons, so this affects cost samples only.
- **The centralization audit** listed on the dashboard
  no longer exists (`get_trigger` 404); its row should come off.
