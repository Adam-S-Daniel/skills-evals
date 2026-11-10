# Eval report: review-bash-ci-reliability

- Timestamp: 20261110T043145Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T042849Z-d5a0b0; started 2026-11-10T04:31:45Z, ended 2026-11-10T04:36:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.44 over 6 call(s); agent $1.18, judge $0.26, guard $0.00; last agent call $0.36

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/8 | 4.6 (4.5 to 4.8, 3 judged) | 0.3934 / 1.1803 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.3934 / 0.3638 |
| num_turns | 10 / 10 |
| duration_ms | 88293 / 91629 |
| input_tokens | 20 / 20 |
| output_tokens | 8081.3 / 8820 |
| cache_creation_input_tokens | 30350.7 / 21032 |
| cache_read_input_tokens | 399810.7 / 410881 |
| tool_errors | 0.7 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| signing-on-runner | 0/3 |
| no-change-night | 0/3 |
| missing-tool-not-silent | 0/3 |
| new-data-still-committed | 0/3 |
| build-failure-still-fails | 3/3 |
| data-untouched | 3/3 |
