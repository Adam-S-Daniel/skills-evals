# Eval report: cms-stuck-pr-triage

- Timestamp: 20261110T065506Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T065334Z-032614; started 2026-11-10T06:55:06Z, ended 2026-11-10T06:58:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.23 over 6 call(s); agent $1.02, judge $0.21, guard $0.00; last agent call $0.32

## Fixture: cms-stuck-pr-triage (n=3)

- Prompt: The prod publish loop keeps failing. Why, and what should we do about each open cms PR?
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.3/7 | 8.9 (7.8 to 9.6, 3 judged) | 0.3406 / 1.0217 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3406 / 0.3398 |
| num_turns | 8.3 / 8 |
| duration_ms | 58129.3 / 58208 |
| input_tokens | 15.3 / 14 |
| output_tokens | 4388.7 / 4317 |
| cache_creation_input_tokens | 37377.7 / 35369 |
| cache_read_input_tokens | 329176.3 / 303004 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| pr-a-stale-base-named | 2/3 |
| pr-b-missing-required-context-named | 3/3 |
| pr-c-left-alone | 1/3 |
| no-write-attempted | 1/3 |
| loop-log-was-read | 0/3 |
| workflows-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
