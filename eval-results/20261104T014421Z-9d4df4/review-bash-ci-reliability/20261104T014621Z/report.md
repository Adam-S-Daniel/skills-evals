# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T014621Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T014421Z-9d4df4; started 2026-11-04T01:46:21Z, ended 2026-11-04T01:47:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1369 / 0.1369 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.0949 / 0.0949 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1369 / 0.1369 | 0.0949 / 0.0949 | +0.0419 | +0.0419 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 20586 / 20586 | 24372 / 24372 | -3786 | -3786 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2071 / 2071 | 2072 / 2072 | -1 | -1 |
| cache_creation_input_tokens | 25892 / 25892 | 13460 / 13460 | +12432 | +12432 |
| cache_read_input_tokens | 125551 / 125551 | 203192 / 203192 | -77641 | -77641 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 1/1 |
| cmp-difference-recorded | 1/1 | 1/1 |
| crash-recorded | 1/1 | 0/1 |
| green-run-and-mismatch-unchanged | 1/1 | 1/1 |
| code-and-fixtures-untouched | 1/1 | 1/1 |
