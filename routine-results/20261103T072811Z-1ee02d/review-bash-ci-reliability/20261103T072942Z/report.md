# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T072942Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T072811Z-1ee02d; started 2026-11-03T07:29:42Z, ended 2026-11-03T07:30:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.22, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1308 / 0.1308 |
| without_skill | 1 | 0 | 7/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.0928 / 0.0928 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1308 / 0.1308 | 0.0928 / 0.0928 | +0.0380 | +0.0380 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 18008 / 18008 | 27209 / 27209 | -9201 | -9201 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1736 / 1736 | 2106 / 2106 | -370 | -370 |
| cache_creation_input_tokens | 25221 / 25221 | 12855 / 12855 | +12366 | +12366 |
| cache_read_input_tokens | 125301 / 125301 | 202856 / 202856 | -77555 | -77555 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 1/1 |
| unowned-template-not-fatal | 1/1 | 1/1 |
| clean-tree-still-passes | 1/1 | 1/1 |
| drift-and-missing-still-fail | 1/1 | 1/1 |
| config-data-untouched | 1/1 | 1/1 |
