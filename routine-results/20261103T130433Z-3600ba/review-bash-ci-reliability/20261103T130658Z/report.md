# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T130658Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T130433Z-3600ba; started 2026-11-03T13:06:58Z, ended 2026-11-03T13:08:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.24, judge $0.16, guard $0.00; last agent call $0.10

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1400 / 0.1400 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1005 / 0.1005 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1400 / 0.1400 | 0.1005 / 0.1005 | +0.0396 | +0.0396 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 31645 / 31645 | 39314 / 39314 | -7669 | -7669 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2294 / 2294 | 2241 / 2241 | +53 | +53 |
| cache_creation_input_tokens | 26142 / 26142 | 14375 / 14375 | +11767 | +11767 |
| cache_read_input_tokens | 125134 / 125134 | 205557 / 205557 | -80423 | -80423 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 1/1 |
| cmp-difference-recorded | 1/1 | 1/1 |
| crash-recorded | 1/1 | 1/1 |
| green-run-and-mismatch-unchanged | 1/1 | 1/1 |
| code-and-fixtures-untouched | 1/1 | 1/1 |
