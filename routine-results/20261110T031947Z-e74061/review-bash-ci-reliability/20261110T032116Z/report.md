# Eval report: review-bash-ci-reliability

- Timestamp: 20261110T032116Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T031947Z-e74061; started 2026-11-10T03:21:16Z, ended 2026-11-10T03:24:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 6 call(s); agent $0.76, judge $0.25, guard $0.00; last agent call $0.16

## Fixture: drift-report-capture (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/7 | 8.0 (7.7 to 8.2, 3 judged) | 0.2537 / 0.7610 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2537 / 0.2040 |
| num_turns | 7.7 / 7 |
| duration_ms | 46639.3 / 44823 |
| input_tokens | 13.3 / 12 |
| output_tokens | 4280.3 / 4265 |
| cache_creation_input_tokens | 23982 / 14808 |
| cache_read_input_tokens | 240492 / 223102 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| every-drifted-file-reported | 3/3 |
| unowned-template-not-fatal | 3/3 |
| clean-tree-still-passes | 3/3 |
| drift-and-missing-still-fail | 3/3 |
| config-data-untouched | 3/3 |
