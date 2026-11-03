# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T142821Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T142625Z-4d8fde; started 2026-11-03T14:28:21Z, ended 2026-11-03T14:29:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.47, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1397 / 0.1397 |
| without_skill | 1 | 0 | 4/8 | skipped (objective-decided) | 0.1103 / 0.1103 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1397 / 0.1397 | 0.1103 / 0.1103 | +0.0294 | +0.0294 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 36337 / 36337 | 47383 / 47383 | -11046 | -11046 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2161 / 2161 | 3043 / 3043 | -882 | -882 |
| cache_creation_input_tokens | 25469 / 25469 | 14776 / 14776 | +10693 | +10693 |
| cache_read_input_tokens | 162185 / 162185 | 207649 / 207649 | -45464 | -45464 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| signing-on-runner | 1/1 | 0/1 |
| no-change-night | 1/1 | 0/1 |
| missing-tool-not-silent | 1/1 | 0/1 |
| new-data-still-committed | 1/1 | 0/1 |
| build-failure-still-fails | 1/1 | 1/1 |
| data-untouched | 1/1 | 1/1 |
