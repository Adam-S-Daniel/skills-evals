# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T120642Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T120504Z-c6c38f; started 2026-11-07T12:06:42Z, ended 2026-11-07T12:07:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.38, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: timeout-wall (n=2)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 2/3 | skipped (objective-decided) | 0.1061 / 0.2121 |
| without_skill | 2 | 0 | 1.5/3 | skipped (objective-decided) | 0.0849 / 0.1698 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1061 / 0.1061 | 0.0849 / 0.0849 | +0.0211 | +0.0211 |
| num_turns | 5.5 / 5.5 | 5.5 / 5.5 | 0 | 0 |
| duration_ms | 16027.5 / 16027.5 | 15284.5 / 15284.5 | +743 | +743 |
| input_tokens | 10 / 10 | 11 / 11 | -1 | -1 |
| output_tokens | 1170 / 1170 | 998.5 / 998.5 | +171.5 | +171.5 |
| cache_creation_input_tokens | 19285.5 / 19285.5 | 13833.5 / 13833.5 | +5452 | +5452 |
| cache_read_input_tokens | 171898 / 171898 | 195748 / 195748 | -23850 | -23850 |
| tool_errors | 0.5 / 0.5 | 1 / 1 | -0.5 | -0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/2 | 0/2 |
| timeout-kept-on-a-work-job | 2/2 | 2/2 |
| readme-untouched | 2/2 | 1/2 |
