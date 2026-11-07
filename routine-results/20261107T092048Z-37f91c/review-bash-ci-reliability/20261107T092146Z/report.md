# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T092146Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T092048Z-37f91c; started 2026-11-07T09:21:46Z, ended 2026-11-07T09:23:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 6 call(s); agent $0.27, judge $0.11, guard $0.00; last agent call $0.09

## Fixture: test-runner-assertions (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 6.3/7 | 6.4 (5.3 to 8.3, 3 judged) | 0.0884 / 0.2652 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0884 / 0.0884 |
| num_turns | 5.7 / 6 |
| duration_ms | 32642 / 34507 |
| input_tokens | 11.3 / 12 |
| output_tokens | 2156.7 / 1979 |
| cache_creation_input_tokens | 11607 / 11754 |
| cache_read_input_tokens | 203864.7 / 216098 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| grep-miss-recorded | 3/3 |
| cmp-difference-recorded | 3/3 |
| crash-recorded | 1/3 |
| green-run-and-mismatch-unchanged | 3/3 |
| code-and-fixtures-untouched | 3/3 |
