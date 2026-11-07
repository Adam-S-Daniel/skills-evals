# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T085642Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T085547Z-5571ca; started 2026-11-07T08:56:42Z, ended 2026-11-07T08:57:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 6 call(s); agent $0.19, judge $0.07, guard $0.00; last agent call $0.06

## Fixture: timeout-wall (n=3)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 2/3 | 3.5 (3.5 to 3.5, 3 judged) | 0.0625 / 0.1874 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0625 / 0.0624 |
| num_turns | 5 / 5 |
| duration_ms | 13051.3 / 12714 |
| input_tokens | 10 / 10 |
| output_tokens | 915.3 / 960 |
| cache_creation_input_tokens | 8947.3 / 8770 |
| cache_read_input_tokens | 175079 / 175265 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| wall-off-the-required-job | 0/3 |
| timeout-kept-on-a-work-job | 3/3 |
| readme-untouched | 3/3 |
