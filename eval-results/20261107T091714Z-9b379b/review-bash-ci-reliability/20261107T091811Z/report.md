# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T091811Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T091714Z-9b379b; started 2026-11-07T09:18:11Z, ended 2026-11-07T09:20:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 6 call(s); agent $0.29, judge $0.13, guard $0.00; last agent call $0.09

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/8 | 4.8 (4.7 to 5.0, 3 judged) | 0.0951 / 0.2853 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0951 / 0.0922 |
| num_turns | 5.7 / 6 |
| duration_ms | 32419.7 / 32113 |
| input_tokens | 11.3 / 12 |
| output_tokens | 2877.3 / 2798 |
| cache_creation_input_tokens | 11500.7 / 11394 |
| cache_read_input_tokens | 202878.7 / 215949 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| signing-on-runner | 0/3 |
| no-change-night | 1/3 |
| missing-tool-not-silent | 1/3 |
| new-data-still-committed | 1/3 |
| build-failure-still-fails | 3/3 |
| data-untouched | 3/3 |
