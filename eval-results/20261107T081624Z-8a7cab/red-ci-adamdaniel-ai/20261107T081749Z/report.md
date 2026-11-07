# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T081749Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T081624Z-8a7cab; started 2026-11-07T08:17:49Z, ended 2026-11-07T08:18:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | skipped (objective-decided) | 0.1309 / 0.1309 |
| without_skill | 1 | 0 | 1/3 | skipped (objective-decided) | 0.0856 / 0.0856 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1309 / 0.1309 | 0.0856 / 0.0856 | +0.0453 | +0.0453 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 18746 / 18746 | 15140 / 15140 | +3606 | +3606 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1081 / 1081 | 1192 / 1192 | -111 | -111 |
| cache_creation_input_tokens | 24871 / 24871 | 14005 / 14005 | +10866 | +10866 |
| cache_read_input_tokens | 205999 / 205999 | 176804 / 176804 | +29195 | +29195 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 0/1 |
