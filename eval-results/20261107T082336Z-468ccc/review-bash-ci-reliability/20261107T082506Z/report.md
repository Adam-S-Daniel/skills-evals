# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T082506Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T082336Z-468ccc; started 2026-11-07T08:25:06Z, ended 2026-11-07T08:26:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.25, judge $0.08, guard $0.00; last agent call $0.11

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/8 | 8.5 (8.5 to 8.5, 1 judged) | 0.1420 / 0.1420 |
| without_skill | 1 | 0 | 7/8 | 4.9 (4.9 to 4.9, 1 judged) | 0.1079 / 0.1079 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1420 / 0.1420 | 0.1079 / 0.1079 | +0.0342 | +0.0342 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 34342 / 34342 | 38537 / 38537 | -4195 | -4195 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 2294 / 2294 | 2873 / 2873 | -579 | -579 |
| cache_creation_input_tokens | 25662 / 25662 | 13741 / 13741 | +11921 | +11921 |
| cache_read_input_tokens | 164212 / 164212 | 241497 / 241497 | -77285 | -77285 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| signing-on-runner | 0/1 | 0/1 |
| no-change-night | 0/1 | 1/1 |
| missing-tool-not-silent | 0/1 | 1/1 |
| new-data-still-committed | 0/1 | 1/1 |
| build-failure-still-fails | 1/1 | 1/1 |
| data-untouched | 1/1 | 1/1 |
