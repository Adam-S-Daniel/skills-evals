# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T051711Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051544Z-aaa1e2; started 2026-11-07T05:17:11Z, ended 2026-11-07T05:18:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1391 / 0.1391 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1277 / 0.1277 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1391 / 0.1391 | 0.1277 / 0.1277 | +0.0114 | +0.0114 |
| num_turns | 6 / 6 | 12 / 12 | -6 | -6 |
| duration_ms | 21781 / 21781 | 41297 / 41297 | -19516 | -19516 |
| input_tokens | 10 / 10 | 20 / 20 | -10 | -10 |
| output_tokens | 2278 / 2278 | 3277 / 3277 | -999 | -999 |
| cache_creation_input_tokens | 25945 / 25945 | 14822 / 14822 | +11123 | +11123 |
| cache_read_input_tokens | 125193 / 125193 | 355814 / 355814 | -230621 | -230621 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 1/1 |
| cmp-difference-recorded | 1/1 | 1/1 |
| crash-recorded | 1/1 | 0/1 |
| green-run-and-mismatch-unchanged | 1/1 | 1/1 |
| code-and-fixtures-untouched | 1/1 | 1/1 |
