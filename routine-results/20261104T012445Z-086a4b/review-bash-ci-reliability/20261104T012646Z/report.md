# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T012646Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T012445Z-086a4b; started 2026-11-04T01:26:46Z, ended 2026-11-04T01:27:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1459 / 0.1459 |
| without_skill | 1 | 0 | 7/8 | skipped (objective-decided) | 0.0911 / 0.0911 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1459 / 0.1459 | 0.0911 / 0.0911 | +0.0548 | +0.0548 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 31025 / 31025 | 29618 / 29618 | +1407 | +1407 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2365 / 2365 | 2295 / 2295 | +70 | +70 |
| cache_creation_input_tokens | 26414 / 26414 | 12840 / 12840 | +13574 | +13574 |
| cache_read_input_tokens | 165615 / 165615 | 167446 / 167446 | -1831 | -1831 |
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
