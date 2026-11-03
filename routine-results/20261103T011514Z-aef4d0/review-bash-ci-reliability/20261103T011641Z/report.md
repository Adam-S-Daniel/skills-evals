# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T011641Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T011514Z-aef4d0; started 2026-11-03T01:16:41Z, ended 2026-11-03T01:18:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.28 to 0.28, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 4 call(s); agent $0.26, judge $0.17, guard $0.00; last agent call $0.11

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1471 / 0.1471 |
| without_skill | 1 | 0 | 7/7 | 8.1 (8.1 to 8.1, 1 judged) | 0.1116 / 0.1116 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1471 / 0.1471 | 0.1116 / 0.1116 | +0.0354 | +0.0354 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 23852 / 23852 | 32215 / 32215 | -8363 | -8363 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2268 / 2268 | 2801 / 2801 | -533 | -533 |
| cache_creation_input_tokens | 27028 / 27028 | 15677 / 15677 | +11351 | +11351 |
| cache_read_input_tokens | 162430 / 162430 | 208977 / 208977 | -46547 | -46547 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 1/1 |
| cmp-difference-recorded | 1/1 | 1/1 |
| crash-recorded | 1/1 | 1/1 |
| green-run-and-mismatch-unchanged | 1/1 | 1/1 |
| code-and-fixtures-untouched | 1/1 | 1/1 |
