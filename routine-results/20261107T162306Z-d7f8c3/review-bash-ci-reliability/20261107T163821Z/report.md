# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T163821Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T162306Z-d7f8c3; started 2026-11-07T16:38:21Z, ended 2026-11-07T16:42:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.55, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 6 call(s); agent $0.63, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.1153 / 0.3459 |
| without_skill | 3 | 0 | 5/8 | skipped (objective-decided) | 0.0962 / 0.2887 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1153 / 0.1076 | 0.0962 / 0.0983 | +0.0191 | +0.0093 |
| num_turns | 7 / 7 | 5.3 / 5 | +1.7 | +2 |
| duration_ms | 32108 / 33461 | 48666.7 / 50878 | -16558.7 | -17417 |
| input_tokens | 12 / 12 | 10.7 / 10 | +1.3 | +2 |
| output_tokens | 2284.3 / 2182 | 2584.3 / 2569 | -300 | -387 |
| cache_creation_input_tokens | 18830.3 / 16000 | 13097.7 / 13132 | +5732.7 | +2868 |
| cache_read_input_tokens | 171178.7 / 175355 | 179682.3 / 167323 | -8503.7 | +8032 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| signing-on-runner | 2/3 | 0/3 |
| no-change-night | 2/3 | 1/3 |
| missing-tool-not-silent | 2/3 | 1/3 |
| new-data-still-committed | 2/3 | 1/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| data-untouched | 3/3 | 3/3 |
