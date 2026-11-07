# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T134637Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T134532Z-42eb2b; started 2026-11-07T13:46:37Z, ended 2026-11-07T13:48:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 6 call(s); agent $0.43, judge $0.25, guard $0.00; last agent call $0.15

## Fixture: timeout-wall (n=3)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 2/3 | 4.0 (3.5 to 4.5, 3 judged) | 0.1444 / 0.4333 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1444 / 0.1452 |
| num_turns | 4.7 / 5 |
| duration_ms | 27811.7 / 27520 |
| input_tokens | 9.3 / 10 |
| output_tokens | 1596.3 / 1677 |
| cache_creation_input_tokens | 9960.7 / 9923 |
| cache_read_input_tokens | 163932 / 176601 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| wall-off-the-required-job | 0/3 |
| timeout-kept-on-a-work-job | 3/3 |
| readme-untouched | 3/3 |
