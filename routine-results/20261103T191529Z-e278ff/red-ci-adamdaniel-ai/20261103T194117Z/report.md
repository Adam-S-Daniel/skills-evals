# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T194117Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T191529Z-e278ff; started 2026-11-03T19:41:17Z, ended 2026-11-03T19:42:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | skipped (objective-decided) | 0.1307 / 0.1307 |
| without_skill | 1 | 0 | 1/3 | skipped (objective-decided) | 0.0859 / 0.0859 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1307 / 0.1307 | 0.0859 / 0.0859 | +0.0448 | +0.0448 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 25971 / 25971 | 13766 / 13766 | +12205 | +12205 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1415 / 1415 | 1267 / 1267 | +148 | +148 |
| cache_creation_input_tokens | 24955 / 24955 | 13900 / 13900 | +11055 | +11055 |
| cache_read_input_tokens | 167307 / 167307 | 176382 / 176382 | -9075 | -9075 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 0/1 |
