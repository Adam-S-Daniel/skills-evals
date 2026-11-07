# Eval report: cms-stuck-pr-triage

- Timestamp: 20261107T160036Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T155045Z-7deeb2; started 2026-11-07T16:00:36Z, ended 2026-11-07T16:07:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.52 to 0.52, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.85 over 12 call(s); agent $1.51, judge $0.34, guard $0.00; last agent call $0.25

## Fixture: cms-stuck-pr-triage (n=3)

- Prompt: The prod publish loop keeps failing. Why, and what should we do about each open cms PR?
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | 6.1 (5.4 to 7.2, 3 judged) | 0.2540 / 0.7620 |
| without_skill | 3 | 0 | 6.3/7 | 9.2 (9.2 to 9.2, 3 judged) | 0.2490 / 0.7470 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2540 / 0.2618 | 0.2490 / 0.2522 | +0.0050 | +0.0096 |
| num_turns | 11 / 12 | 12.7 / 12 | -1.7 | 0 |
| duration_ms | 59407.7 / 63045 | 59764.7 / 57425 | -357 | +5620 |
| input_tokens | 22 / 24 | 18 / 16 | +4 | +8 |
| output_tokens | 4950.3 / 4781 | 4600.7 / 4709 | +349.7 | +72 |
| cache_creation_input_tokens | 39286.7 / 36617 | 41387.3 / 43810 | -2100.7 | -7193 |
| cache_read_input_tokens | 473208.7 / 537925 | 374072.7 / 342638 | +99136 | +195287 |
| tool_errors | 0.3 / 0 | 1 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-a-stale-base-named | 3/3 | 3/3 |
| pr-b-missing-required-context-named | 2/3 | 3/3 |
| pr-c-left-alone | 3/3 | 3/3 |
| no-write-attempted | 3/3 | 3/3 |
| loop-log-was-read | 0/3 | 1/3 |
| workflows-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
