# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T232304Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T232029Z-04ea38; started 2026-11-03T23:23:04Z, ended 2026-11-03T23:24:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.22, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: timeout-wall (n=1)

- Prompt: Our `test` check sometimes goes `cancelled` after about ten minutes and the PR can never merge. Fix the workflow so a slow run cannot leave the required check cancelled.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 4.0 (4.0 to 4.0, 1 judged) | 0.1294 / 0.1294 |
| without_skill | 1 | 0 | 2/3 | 4.0 (4.0 to 4.0, 1 judged) | 0.0897 / 0.0897 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1294 / 0.1294 | 0.0897 / 0.0897 | +0.0397 | +0.0397 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 17093 / 17093 | 16740 / 16740 | +353 | +353 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1334 / 1334 | 1549 / 1549 | -215 | -215 |
| cache_creation_input_tokens | 24825 / 24825 | 14121 / 14121 | +10704 | +10704 |
| cache_read_input_tokens | 167437 / 167437 | 176949 / 176949 | -9512 | -9512 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| wall-off-the-required-job | 0/1 | 0/1 |
| timeout-kept-on-a-work-job | 1/1 | 1/1 |
| readme-untouched | 1/1 | 1/1 |
