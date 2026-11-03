# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T233638Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T233501Z-4c9fe3; started 2026-11-03T23:36:38Z, ended 2026-11-03T23:37:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.23, judge $0.16, guard $0.00; last agent call $0.10

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.1312 / 0.1312 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.0973 / 0.0973 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1312 / 0.1312 | 0.0973 / 0.0973 | +0.0339 | +0.0339 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 20561 / 20561 | 28431 / 28431 | -7870 | -7870 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1826 / 1826 | 2338 / 2338 | -512 | -512 |
| cache_creation_input_tokens | 25091 / 25091 | 13384 / 13384 | +11707 | +11707 |
| cache_read_input_tokens | 125381 / 125381 | 203421 / 203421 | -78040 | -78040 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 1/1 |
| unowned-template-not-fatal | 1/1 | 1/1 |
| clean-tree-still-passes | 1/1 | 1/1 |
| drift-and-missing-still-fail | 1/1 | 1/1 |
| config-data-untouched | 1/1 | 1/1 |
