# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T184011Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T183736Z-a30692; started 2026-11-04T18:40:11Z, ended 2026-11-04T18:41:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1873 / 0.1873 |
| without_skill | 1 | 0 | 7/8 | skipped (objective-decided) | 0.0920 / 0.0920 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1873 / 0.1873 | 0.0920 / 0.0920 | +0.0953 | +0.0953 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 48377 / 48377 | 31776 / 31776 | +16601 | +16601 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 2526 / 2526 | 2317 / 2317 | +209 | +209 |
| cache_creation_input_tokens | 34498 / 34498 | 13019 / 13019 | +21479 | +21479 |
| cache_read_input_tokens | 240075 / 240075 | 167360 / 167360 | +72715 | +72715 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
