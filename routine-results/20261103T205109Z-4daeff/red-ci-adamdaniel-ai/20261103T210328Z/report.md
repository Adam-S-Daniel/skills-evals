# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T210328Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T205109Z-4daeff; started 2026-11-03T21:03:28Z, ended 2026-11-03T21:04:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/3 | skipped (objective-decided) | 0.1426 / 0.1426 |
| without_skill | 1 | 0 | 2/3 | skipped (objective-decided) | 0.0869 / 0.0869 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1426 / 0.1426 | 0.0869 / 0.0869 | +0.0557 | +0.0557 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 29127 / 29127 | 34590 / 34590 | -5463 | -5463 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1748 / 1748 | 1350 / 1350 | +398 | +398 |
| cache_creation_input_tokens | 26106 / 26106 | 13938 / 13938 | +12168 | +12168 |
| cache_read_input_tokens | 207101 / 207101 | 176743 / 176743 | +30358 | +30358 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 1/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
