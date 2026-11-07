# Eval report: cms-stuck-pr-triage

- Timestamp: 20261107T113748Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T113618Z-ce21a6; started 2026-11-07T11:37:48Z, ended 2026-11-07T11:41:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.05 over 4 call(s); agent $1.05, judge $0.00, guard $0.00; last agent call $0.26

## Fixture: cms-stuck-pr-triage (n=2)

- Prompt: The prod publish loop keeps failing. Why, and what should we do about each open cms PR?
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.2659 / 0.5319 |
| without_skill | 2 | 0 | 6.5/7 | skipped (objective-decided) | 0.2610 / 0.5220 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2659 / 0.2659 | 0.2610 / 0.2610 | +0.0049 | +0.0049 |
| num_turns | 11.5 / 11.5 | 11 / 11 | +0.5 | +0.5 |
| duration_ms | 47294.5 / 47294.5 | 48939.5 / 48939.5 | -1645 | -1645 |
| input_tokens | 20 / 20 | 19 / 19 | +1 | +1 |
| output_tokens | 4087.5 / 4087.5 | 4385 / 4385 | -297.5 | -297.5 |
| cache_creation_input_tokens | 45210 / 45210 | 43917.5 / 43917.5 | +1292.5 | +1292.5 |
| cache_read_input_tokens | 441916.5 / 441916.5 | 414458 / 414458 | +27458.5 | +27458.5 |
| tool_errors | 1 / 1 | 0.5 / 0.5 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-a-stale-base-named | 2/2 | 2/2 |
| pr-b-missing-required-context-named | 2/2 | 2/2 |
| pr-c-left-alone | 2/2 | 2/2 |
| no-write-attempted | 2/2 | 2/2 |
| loop-log-was-read | 2/2 | 1/2 |
| workflows-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
