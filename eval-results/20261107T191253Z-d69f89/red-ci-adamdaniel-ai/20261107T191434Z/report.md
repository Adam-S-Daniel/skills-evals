# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T191434Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T191253Z-d69f89; started 2026-11-07T19:14:34Z, ended 2026-11-07T19:21:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.64, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.21 over 6 call(s); agent $2.21, judge $0.00, guard $0.00; last agent call $0.40

## Fixture: timeout-wall (n=3)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/3 | skipped (objective-decided) | 0.3750 / 1.1250 |
| without_skill | 3 | 0 | 2/3 | skipped (objective-decided) | 0.3606 / 1.0818 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3750 / 0.3129 | 0.3606 / 0.3684 | +0.0144 | -0.0556 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 78902.7 / 78109 | 65774 / 67948 | +13128.7 | +10161 |
| input_tokens | 20 / 20 | 14.7 / 14 | +5.3 | +6 |
| output_tokens | 4073 / 3834 | 3990.3 / 4005 | +82.7 | -171 |
| cache_creation_input_tokens | 24181.7 / 20798 | 19665 / 20111 | +4516.7 | +687 |
| cache_read_input_tokens | 303428.7 / 304130 | 264244 / 261147 | +39184.7 | +42983 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 3/3 | 0/3 |
| timeout-kept-on-a-work-job | 3/3 | 3/3 |
| readme-untouched | 3/3 | 3/3 |
