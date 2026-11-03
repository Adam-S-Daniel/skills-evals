# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T084452Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T084314Z-246e24; started 2026-11-03T08:44:52Z, ended 2026-11-03T08:47:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 2 call(s); agent $0.81, judge $0.00, guard $0.00; last agent call $0.44

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3716 / 0.3716 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.4424 / 0.4424 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3716 / 0.3716 | 0.4424 / 0.4424 | -0.0708 | -0.0708 |
| num_turns | 10 / 10 | 6 / 6 | +4 | +4 |
| duration_ms | 48566 / 48566 | 89228 / 89228 | -40662 | -40662 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 3902 / 3902 | 5810 / 5810 | -1908 | -1908 |
| cache_creation_input_tokens | 29386 / 29386 | 21379 / 21379 | +8007 | +8007 |
| cache_read_input_tokens | 291924 / 291924 | 213383 / 213383 | +78541 | +78541 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 1/1 |
| cmp-difference-recorded | 1/1 | 1/1 |
| crash-recorded | 1/1 | 1/1 |
| green-run-and-mismatch-unchanged | 1/1 | 1/1 |
| code-and-fixtures-untouched | 1/1 | 0/1 |
