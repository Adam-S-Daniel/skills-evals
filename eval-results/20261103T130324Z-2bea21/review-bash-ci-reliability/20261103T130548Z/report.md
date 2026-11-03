# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T130548Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T130324Z-2bea21; started 2026-11-03T13:05:48Z, ended 2026-11-03T13:06:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1374 / 0.1374 |
| without_skill | 1 | 0 | 7/8 | skipped (objective-decided) | 0.0858 / 0.0858 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1374 / 0.1374 | 0.0858 / 0.0858 | +0.0517 | +0.0517 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 23550 / 23550 | 29245 / 29245 | -5695 | -5695 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2205 / 2205 | 2224 / 2224 | -19 | -19 |
| cache_creation_input_tokens | 25702 / 25702 | 12619 / 12619 | +13083 | +13083 |
| cache_read_input_tokens | 125431 / 125431 | 130341 / 130341 | -4910 | -4910 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| signing-on-runner | 1/1 | 0/1 |
| no-change-night | 1/1 | 1/1 |
| missing-tool-not-silent | 1/1 | 1/1 |
| new-data-still-committed | 1/1 | 1/1 |
| build-failure-still-fails | 1/1 | 1/1 |
| data-untouched | 1/1 | 1/1 |
