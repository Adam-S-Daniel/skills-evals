# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T055354Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T055230Z-ba3d00; started 2026-11-07T05:53:54Z, ended 2026-11-07T05:55:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.35, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1447 / 0.1447 |
| without_skill | 1 | 0 | 7/8 | skipped (objective-decided) | 0.1007 / 0.1007 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1447 / 0.1447 | 0.1007 / 0.1007 | +0.0439 | +0.0439 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 31624 / 31624 | 31083 / 31083 | +541 | +541 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2460 / 2460 | 3004 / 3004 | -544 | -544 |
| cache_creation_input_tokens | 25888 / 25888 | 13516 / 13516 | +12372 | +12372 |
| cache_read_input_tokens | 165023 / 165023 | 166092 / 166092 | -1069 | -1069 |
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
