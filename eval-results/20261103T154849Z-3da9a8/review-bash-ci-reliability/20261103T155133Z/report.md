# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T155133Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T154849Z-3da9a8; started 2026-11-03T15:51:33Z, ended 2026-11-03T15:52:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.54, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 4 call(s); agent $0.23, judge $0.16, guard $0.00; last agent call $0.09

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1362 / 0.1362 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0936 / 0.0936 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1362 / 0.1362 | 0.0936 / 0.0936 | +0.0426 | +0.0426 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 17384 / 17384 | 19863 / 19863 | -2479 | -2479 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1929 / 1929 | 2284 / 2284 | -355 | -355 |
| cache_creation_input_tokens | 26061 / 26061 | 13494 / 13494 | +12567 | +12567 |
| cache_read_input_tokens | 125989 / 125989 | 167338 / 167338 | -41349 | -41349 |
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
