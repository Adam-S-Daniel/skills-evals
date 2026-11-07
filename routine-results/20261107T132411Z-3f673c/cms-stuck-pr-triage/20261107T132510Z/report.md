# Eval report: cms-stuck-pr-triage

- Timestamp: 20261107T132510Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T132411Z-3f673c; started 2026-11-07T13:25:10Z, ended 2026-11-07T13:27:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 6 call(s); agent $0.55, judge $0.15, guard $0.00; last agent call $0.21

## Fixture: cms-stuck-pr-triage (n=3)

- Prompt: The prod publish loop keeps failing. Why, and what should we do about each open cms PR?
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/7 | 9.1 (8.8 to 9.2, 3 judged) | 0.1845 / 0.5535 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1845 / 0.1840 |
| num_turns | 11 / 10 |
| duration_ms | 45073.7 / 46509 |
| input_tokens | 15.3 / 14 |
| output_tokens | 3981.7 / 4123 |
| cache_creation_input_tokens | 27912.7 / 28580 |
| cache_read_input_tokens | 329908.7 / 284058 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| pr-a-stale-base-named | 3/3 |
| pr-b-missing-required-context-named | 3/3 |
| pr-c-left-alone | 3/3 |
| no-write-attempted | 3/3 |
| loop-log-was-read | 3/3 |
| workflows-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
