# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T083217Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T083047Z-322455; started 2026-11-07T08:32:17Z, ended 2026-11-07T08:33:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1342 / 0.1342 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1041 / 0.1041 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1342 / 0.1342 | 0.1041 / 0.1041 | +0.0301 | +0.0301 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 19523 / 19523 | 33945 / 33945 | -14422 | -14422 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1980 / 1980 | 2740 / 2740 | -760 | -760 |
| cache_creation_input_tokens | 25468 / 25468 | 14044 / 14044 | +11424 | +11424 |
| cache_read_input_tokens | 125157 / 125157 | 205376 / 205376 | -80219 | -80219 |
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
