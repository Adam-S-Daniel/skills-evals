# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T174546Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T173313Z-10451d; started 2026-11-03T17:45:46Z, ended 2026-11-03T17:47:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.62, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1401 / 0.1401 |
| without_skill | 1 | 0 | 7/8 | skipped (objective-decided) | 0.0853 / 0.0853 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1401 / 0.1401 | 0.0853 / 0.0853 | +0.0548 | +0.0548 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 29514 / 29514 | 34402 / 34402 | -4888 | -4888 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2240 / 2240 | 2182 / 2182 | +58 | +58 |
| cache_creation_input_tokens | 25331 / 25331 | 12616 / 12616 | +12715 | +12715 |
| cache_read_input_tokens | 163408 / 163408 | 130064 / 130064 | +33344 | +33344 |
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
