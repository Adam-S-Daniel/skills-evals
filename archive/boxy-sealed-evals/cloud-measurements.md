# Cloud-side measurements and the decision to park (2026-11-04 to 2026-11-06)

Measured from the cloud project thread that captained the BOXY lane. The BOXY
measurements are in [README.md](README.md). The options review that preceded
the build is [runner-options-review-2026-11-04.md](runner-options-review-2026-11-04.md).

## Weekly meter economics

- About **$24 of API-equivalent spend per 1% of the weekly meter** (range $20
  to $35). Measured account-wide from tick to tick: 11-03 12:35 to 11-04 04:31
  UTC, 51.5 points for $1,221 ($23.7 per point); interactive use alone, $22.6.
- The meter reads whole points, so any one reading can be off by up to 1 point.
- Burn on 2026-11-04: about 3.3 points an hour with evals running, and about
  2.3 an hour with evals off. Interactive threads, not evals, were most of it.
  One captain thread on Opus at Extra effort with a large context cost $45 of
  the $67 that all project threads spent in one two-hour window.

## The eval budget guard over-charges runs

- `scripts/allowance_guard.py` charged each ingested run the account-wide meter
  movement during that run, plus an overrun allowance. Overlapping runs were
  each charged the same movement, and so was every other thread's use.
- In the week to 2026-11-04 it booked 116 points against about 23 points of
  real eval spend: about five times too much.
- `evals/budget.yml` `points_per_usd` (0.00214) is about five times the
  measured rate. The ingest's calibration (0.0028 per dollar) is about seven
  times too high, for the same reason.

## What one eval costs, by where it runs

The cloud routine's own session (reading the instructions, installing, running,
committing and pushing) is not counted in any summary. It was measured from 12
routine sessions with `get_session`:

- **$0.665 per fire** on average (median $0.651, range $0.627 to $0.738), on
  Sonnet 5.5. A least-squares fit reproduces every session's cost exactly at
  $2 per million input tokens, $0.10 per million cache reads, $4 per million
  one-hour cache writes and $10 per million output tokens.
- **75% of it is the first call**, which writes about 94,000 tokens of startup
  context that no other fire has cached (only about 30,000 tokens are shared).
  Startup holds 99 tools (51 of them MCP), 79 skills, the fleet guidance and
  every attached repository's CLAUDE.md and AGENTS.md. The 31 KB instructions
  file adds about 13,500 tokens.
- A fire takes 10 to 13 model calls. About 8 of 10 are mechanical.

Per fixture and model (arms plus judge about $0.55):

| Where it runs | Per run | A full sweep (114 runs) |
|---|---|---|
| Cloud routine as it was | about $1.22 | about 5.8 points |
| Slimmer cloud routine | about $0.95 | not measured |
| Slimmer routine, both models per fire | about $0.80 | about 3.8 points |
| BOXY sealed container | about $0.55 | about 2.6 points |

## Decision (Adam, 2026-11-06 6:07 PM ET)

Park the BOXY lane here, implement the slimmer cloud routine and both models per
fire, and resume evals in the cloud to use the rest of the week's budget.
Against the slimmer cloud routine, BOXY would have saved about 1.2 points per
full sweep. It still needed the T8 and T9 work, a request queue, a scheduled
runner on BOXY, a GitHub App and two ADR changes. Its real runs also needed
Adam to start them, because the agent's safety checks block token-using
commands.
