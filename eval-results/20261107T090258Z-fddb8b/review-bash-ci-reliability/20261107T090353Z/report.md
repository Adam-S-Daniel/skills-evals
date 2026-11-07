# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T090353Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T090258Z-fddb8b; started 2026-11-07T09:03:53Z, ended 2026-11-07T09:05:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.39 over 6 call(s); agent $0.26, judge $0.13, guard $0.00; last agent call $0.09

## Fixture: drift-report-capture (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7/7 | 7.8 (7.6 to 7.9, 3 judged) | 0.0860 / 0.2580 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0860 / 0.0871 |
| num_turns | 4.7 / 5 |
| duration_ms | 23975.7 / 27655 |
| input_tokens | 9.3 / 10 |
| output_tokens | 2512 / 2492 |
| cache_creation_input_tokens | 11106.3 / 11115 |
| cache_read_input_tokens | 164375.7 / 177008 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflow-yaml-parses | 3/3 |
| workflow-file-present | 3/3 |
| every-drifted-file-reported | 3/3 |
| unowned-template-not-fatal | 3/3 |
| clean-tree-still-passes | 3/3 |
| drift-and-missing-still-fail | 3/3 |
| config-data-untouched | 3/3 |
