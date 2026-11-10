# Eval report: review-bash-ci-reliability

- Timestamp: 20261110T065045Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T064909Z-751739; started 2026-11-10T06:50:45Z, ended 2026-11-10T06:54:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.03 over 6 call(s); agent $0.79, judge $0.24, guard $0.00; last agent call $0.18

## Fixture: test-runner-assertions (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6.3/7 | 8.3 (7.8 to 9.4, 3 judged) | 0.2638 / 0.7915 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2638 / 0.2404 |
| num_turns | 7 / 7 |
| duration_ms | 54228.7 / 55540 |
| input_tokens | 14 / 14 |
| output_tokens | 4457.7 / 4486 |
| cache_creation_input_tokens | 24724 / 16415 |
| cache_read_input_tokens | 255058 / 266813 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| grep-miss-recorded | 3/3 |
| cmp-difference-recorded | 3/3 |
| crash-recorded | 3/3 |
| green-run-and-mismatch-unchanged | 3/3 |
| code-and-fixtures-untouched | 1/3 |
