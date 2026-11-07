# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T190225Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T184755Z-c752f8; started 2026-11-07T19:02:25Z, ended 2026-11-07T19:05:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.62, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 6 call(s); agent $0.63, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.1138 / 0.3414 |
| without_skill | 3 | 0 | 5.7/8 | skipped (objective-decided) | 0.0977 / 0.2930 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1138 / 0.1049 | 0.0977 / 0.1008 | +0.0161 | +0.0041 |
| num_turns | 6.7 / 7 | 5.7 / 6 | +1 | +1 |
| duration_ms | 27464.7 / 22838 | 29724 / 30975 | -2259.3 | -8137 |
| input_tokens | 11.3 / 12 | 11.3 / 12 | 0 | 0 |
| output_tokens | 2278 / 2189 | 2583.7 / 2625 | -305.7 | -436 |
| cache_creation_input_tokens | 18795.3 / 15569 | 13139.7 / 13486 | +5655.7 | +2083 |
| cache_read_input_tokens | 158125 / 174192 | 192637.7 / 205548 | -34512.7 | -31356 |
| tool_errors | 0.3 / 0 | 1 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| signing-on-runner | 3/3 | 0/3 |
| no-change-night | 3/3 | 2/3 |
| missing-tool-not-silent | 3/3 | 1/3 |
| new-data-still-committed | 3/3 | 2/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| data-untouched | 3/3 | 3/3 |
