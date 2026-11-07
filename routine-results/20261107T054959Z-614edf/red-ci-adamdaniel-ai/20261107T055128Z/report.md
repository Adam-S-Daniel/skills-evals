# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T055128Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T054959Z-614edf; started 2026-11-07T05:51:28Z, ended 2026-11-07T05:52:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 4 call(s); agent $0.21, judge $0.05, guard $0.00; last agent call $0.08

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 3.0 (3.0 to 3.0, 1 judged) | 0.1245 / 0.1245 |
| without_skill | 1 | 0 | 2/3 | 3.5 (3.5 to 3.5, 1 judged) | 0.0817 / 0.0817 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1245 / 0.1245 | 0.0817 / 0.0817 | +0.0428 | +0.0428 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 15000 / 15000 | 13976 / 13976 | +1024 | +1024 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1004 / 1004 | 931 / 931 | +73 | +73 |
| cache_creation_input_tokens | 24431 / 24431 | 13685 / 13685 | +10746 | +10746 |
| cache_read_input_tokens | 166757 / 166757 | 176365 / 176365 | -9608 | -9608 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
