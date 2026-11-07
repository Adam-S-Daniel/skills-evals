# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T121349Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T121211Z-8ef987; started 2026-11-07T12:13:49Z, ended 2026-11-07T12:16:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 4 call(s); agent $0.47, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: nightly-snapshot (n=2)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 6/8 | skipped (objective-decided) | 0.1359 / 0.2718 |
| without_skill | 2 | 0 | 5.5/8 | skipped (objective-decided) | 0.0984 / 0.1969 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1359 / 0.1359 | 0.0984 / 0.0984 | +0.0375 | +0.0375 |
| num_turns | 8.5 / 8.5 | 5.5 / 5.5 | +3 | +3 |
| duration_ms | 36126.5 / 36126.5 | 33085.5 / 33085.5 | +3041 | +3041 |
| input_tokens | 17 / 17 | 11 / 11 | +6 | +6 |
| output_tokens | 2552 / 2552 | 2634 / 2634 | -82 | -82 |
| cache_creation_input_tokens | 20924.5 / 20924.5 | 13351 / 13351 | +7573.5 | +7573.5 |
| cache_read_input_tokens | 266513.5 / 266513.5 | 186811.5 / 186811.5 | +79702 | +79702 |
| tool_errors | 1 / 1 | 0.5 / 0.5 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 2/2 | 2/2 |
| workflow-file-present | 2/2 | 2/2 |
| signing-on-runner | 1/2 | 0/2 |
| no-change-night | 1/2 | 1/2 |
| missing-tool-not-silent | 1/2 | 1/2 |
| new-data-still-committed | 1/2 | 1/2 |
| build-failure-still-fails | 2/2 | 2/2 |
| data-untouched | 2/2 | 2/2 |
