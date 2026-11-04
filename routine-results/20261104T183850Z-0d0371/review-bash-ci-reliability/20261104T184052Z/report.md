# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T184052Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T183850Z-0d0371; started 2026-11-04T18:40:52Z, ended 2026-11-04T18:42:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.26, judge $0.16, guard $0.00; last agent call $0.11

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1425 / 0.1425 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1145 / 0.1145 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1425 / 0.1425 | 0.1145 / 0.1145 | +0.0280 | +0.0280 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 19244 / 19244 | 27166 / 27166 | -7922 | -7922 |
| input_tokens | 10 / 10 | 14 / 14 | -4 | -4 |
| output_tokens | 2496 / 2496 | 3253 / 3253 | -757 | -757 |
| cache_creation_input_tokens | 26254 / 26254 | 14470 / 14470 | +11784 | +11784 |
| cache_read_input_tokens | 125184 / 125184 | 240769 / 240769 | -115585 | -115585 |
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
