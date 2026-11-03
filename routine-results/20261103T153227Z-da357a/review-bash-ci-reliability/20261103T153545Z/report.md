# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T153545Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T153227Z-da357a; started 2026-11-03T15:35:45Z, ended 2026-11-03T15:37:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.52 to 0.52, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 4 call(s); agent $0.21, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.4 (8.4 to 8.4, 1 judged) | 0.1300 / 0.1300 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0843 / 0.0843 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1300 / 0.1300 | 0.0843 / 0.0843 | +0.0457 | +0.0457 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 19150 / 19150 | 40201 / 40201 | -21051 | -21051 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1751 / 1751 | 1828 / 1828 | -77 | -77 |
| cache_creation_input_tokens | 25000 / 25000 | 12342 / 12342 | +12658 | +12658 |
| cache_read_input_tokens | 125045 / 125045 | 166209 / 166209 | -41164 | -41164 |
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
