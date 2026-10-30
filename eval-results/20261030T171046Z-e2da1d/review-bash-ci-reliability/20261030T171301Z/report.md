# Eval report: review-bash-ci-reliability

- Timestamp: 20261030T171301Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261030T171046Z-e2da1d; started 2026-10-30T17:13:01Z, ended 2026-10-30T17:17:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.09 to 0.1, seven_day 0.65 to 0.65, from 12 snapshots

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.314 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/8 | 5.0 (4.7 to 5.2, 3 judged) | 0.1323 / 0.3968 |
| without_skill | 3 | 0 | 6/8 | 5.1 (4.9 to 5.4, 3 judged) | 0.1043 / 0.3130 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1323 / 0.0987 | 0.1043 / 0.0918 | +0.0279 | +0.0069 |
| num_turns | 6.7 / 7 | 5.7 / 6 | +1 | +1 |
| duration_ms | 30528.3 / 30332 | 38132.3 / 37489 | -7604 | -7157 |
| input_tokens | 11.3 / 12 | 11.3 / 12 | 0 | 0 |
| output_tokens | 2510.3 / 2253 | 2377 / 2463 | +133.3 | -210 |
| cache_creation_input_tokens | 23019.3 / 15014 | 15413 / 12526 | +7606.3 | +2488 |
| cache_read_input_tokens | 150538 / 147449 | 188859.3 / 200586 | -38321.3 | -53137 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| signing-on-runner | 0/3 | 0/3 |
| no-change-night | 1/3 | 2/3 |
| missing-tool-not-silent | 1/3 | 2/3 |
| new-data-still-committed | 1/3 | 2/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| data-untouched | 3/3 | 3/3 |
