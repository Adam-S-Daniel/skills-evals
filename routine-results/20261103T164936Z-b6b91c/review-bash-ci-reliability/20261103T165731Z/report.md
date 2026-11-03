# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T165731Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T164936Z-b6b91c; started 2026-11-03T16:57:31Z, ended 2026-11-03T17:01:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 2 call(s); agent $0.99, judge $0.00, guard $0.00; last agent call $0.53

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.4670 / 0.4670 |
| without_skill | 1 | 0 | 3/7 | skipped (objective-decided) | 0.5264 / 0.5264 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4670 / 0.4670 | 0.5264 / 0.5264 | -0.0594 | -0.0594 |
| num_turns | 11 / 11 | 11 / 11 | 0 | 0 |
| duration_ms | 89727 / 89727 | 148322 / 148322 | -58595 | -58595 |
| input_tokens | 20 / 20 | 28 / 28 | -8 | -8 |
| output_tokens | 5914 / 5914 | 10145 / 10145 | -4231 | -4231 |
| cache_creation_input_tokens | 34132 / 34132 | 27938 / 27938 | +6194 | +6194 |
| cache_read_input_tokens | 339129 / 339129 | 443052 / 443052 | -103923 | -103923 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 0/1 |
| cmp-difference-recorded | 1/1 | 0/1 |
| crash-recorded | 1/1 | 0/1 |
| green-run-and-mismatch-unchanged | 1/1 | 0/1 |
| code-and-fixtures-untouched | 1/1 | 1/1 |
