# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T162929Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T161555Z-52546b; started 2026-11-07T16:29:29Z, ended 2026-11-07T16:33:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.54, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 12 call(s); agent $0.59, judge $0.24, guard $0.00; last agent call $0.08

## Fixture: drift-report-capture (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 8.3 (7.8 to 8.6, 3 judged) | 0.1095 / 0.3285 |
| without_skill | 3 | 0 | 7/7 | 8.5 (8.4 to 8.6, 3 judged) | 0.0859 / 0.2578 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1095 / 0.0972 | 0.0859 / 0.0865 | +0.0236 | +0.0108 |
| num_turns | 7 / 7 | 4.7 / 5 | +2.3 | +2 |
| duration_ms | 28626 / 28405 | 30002.3 / 28778 | -1376.3 | -373 |
| input_tokens | 12.7 / 12 | 9.3 / 10 | +3.3 | +2 |
| output_tokens | 1774.7 / 1726 | 2003.3 / 1988 | -228.7 | -262 |
| cache_creation_input_tokens | 18344 / 14923 | 12597 / 12460 | +5747 | +2463 |
| cache_read_input_tokens | 183503.3 / 174684 | 154826 / 167146 | +28677.3 | +7538 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| every-drifted-file-reported | 3/3 | 3/3 |
| unowned-template-not-fatal | 3/3 | 3/3 |
| clean-tree-still-passes | 3/3 | 3/3 |
| drift-and-missing-still-fail | 3/3 | 3/3 |
| config-data-untouched | 3/3 | 3/3 |
