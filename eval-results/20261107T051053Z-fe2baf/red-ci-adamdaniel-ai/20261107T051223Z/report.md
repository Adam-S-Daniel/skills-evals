# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T051223Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051053Z-fe2baf; started 2026-11-07T05:12:23Z, ended 2026-11-07T05:13:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 4 call(s); agent $0.21, judge $0.05, guard $0.00; last agent call $0.08

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 1/3 | 3.0 (3.0 to 3.0, 1 judged) | 0.1306 / 0.1306 |
| without_skill | 1 | 0 | 2/3 | 3.5 (3.5 to 3.5, 1 judged) | 0.0838 / 0.0838 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1306 / 0.1306 | 0.0838 / 0.0838 | +0.0467 | +0.0467 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 16238 / 16238 | 23393 / 23393 | -7155 | -7155 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1423 / 1423 | 1102 / 1102 | +321 | +321 |
| cache_creation_input_tokens | 24897 / 24897 | 13777 / 13777 | +11120 | +11120 |
| cache_read_input_tokens | 167242 / 167242 | 176653 / 176653 | -9411 | -9411 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 0/1 | 1/1 |
