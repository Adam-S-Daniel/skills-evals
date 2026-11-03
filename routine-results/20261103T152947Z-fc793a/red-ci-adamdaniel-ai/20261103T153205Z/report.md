# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T153205Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T152947Z-fc793a; started 2026-11-03T15:32:05Z, ended 2026-11-03T15:33:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.52, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.22, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 4.5 (4.5 to 4.5, 1 judged) | 0.1309 / 0.1309 |
| without_skill | 1 | 0 | 2/3 | 4.5 (4.5 to 4.5, 1 judged) | 0.0884 / 0.0884 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1309 / 0.1309 | 0.0884 / 0.0884 | +0.0425 | +0.0425 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 26103 / 26103 | 24628 / 24628 | +1475 | +1475 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1464 / 1464 | 1472 / 1472 | -8 | -8 |
| cache_creation_input_tokens | 24872 / 24872 | 13993 / 13993 | +10879 | +10879 |
| cache_read_input_tokens | 167096 / 167096 | 176662 / 176662 | -9566 | -9566 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
