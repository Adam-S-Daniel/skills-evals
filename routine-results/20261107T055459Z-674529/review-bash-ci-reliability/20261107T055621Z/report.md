# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T055621Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T055459Z-674529; started 2026-11-07T05:56:21Z, ended 2026-11-07T05:57:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.26, judge $0.09, guard $0.00; last agent call $0.12

## Fixture: test-runner-assertions (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1381 / 0.1381 |
| without_skill | 1 | 0 | 7/7 | 8.3 (8.3 to 8.3, 1 judged) | 0.1224 / 0.1224 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1381 / 0.1381 | 0.1224 / 0.1224 | +0.0157 | +0.0157 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 23333 / 23333 | 38749 / 38749 | -15416 | -15416 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2246 / 2246 | 4103 / 4103 | -1857 | -1857 |
| cache_creation_input_tokens | 25772 / 25772 | 15207 / 15207 | +10565 | +10565 |
| cache_read_input_tokens | 124940 / 124940 | 204732 / 204732 | -79792 | -79792 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| grep-miss-recorded | 1/1 | 1/1 |
| cmp-difference-recorded | 1/1 | 1/1 |
| crash-recorded | 1/1 | 1/1 |
| green-run-and-mismatch-unchanged | 1/1 | 1/1 |
| code-and-fixtures-untouched | 1/1 | 1/1 |
