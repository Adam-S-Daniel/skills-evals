# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T222021Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T220907Z-18b2a2; started 2026-11-03T22:20:21Z, ended 2026-11-03T22:22:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.77, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.26, judge $0.16, guard $0.00; last agent call $0.11

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1513 / 0.1513 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1105 / 0.1105 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1513 / 0.1513 | 0.1105 / 0.1105 | +0.0408 | +0.0408 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 33161 / 33161 | 45321 / 45321 | -12160 | -12160 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 2679 / 2679 | 2780 / 2780 | -101 | -101 |
| cache_creation_input_tokens | 26974 / 26974 | 14615 / 14615 | +12359 | +12359 |
| cache_read_input_tokens | 166342 / 166342 | 242342 / 242342 | -76000 | -76000 |
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
