# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T174728Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T172958Z-8867c5; started 2026-11-03T17:47:28Z, ended 2026-11-03T17:51:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.62, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.11 over 2 call(s); agent $1.11, judge $0.00, guard $0.00; last agent call $0.56

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.5533 / 0.5533 |
| without_skill | 1 | 0 | 3/7 | skipped (objective-decided) | 0.5608 / 0.5608 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5533 / 0.5533 | 0.5608 / 0.5608 | -0.0075 | -0.0075 |
| num_turns | 11 / 11 | 11 / 11 | 0 | 0 |
| duration_ms | 131523 / 131523 | 119574 / 119574 | +11949 | +11949 |
| input_tokens | 22 / 22 | 22 / 22 | 0 | 0 |
| output_tokens | 8727 / 8727 | 7258 / 7258 | +1469 | +1469 |
| cache_creation_input_tokens | 37175 / 37175 | 23556 / 23556 | +13619 | +13619 |
| cache_read_input_tokens | 347737 / 347737 | 380749 / 380749 | -33012 | -33012 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 0/1 | 0/1 |
| unowned-template-not-fatal | 0/1 | 0/1 |
| clean-tree-still-passes | 1/1 | 0/1 |
| drift-and-missing-still-fail | 1/1 | 0/1 |
| config-data-untouched | 1/1 | 1/1 |
