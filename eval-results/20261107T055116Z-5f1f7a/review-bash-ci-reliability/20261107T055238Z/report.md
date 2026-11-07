# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T055238Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T055116Z-5f1f7a; started 2026-11-07T05:52:38Z, ended 2026-11-07T05:53:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.21, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1288 / 0.1288 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0796 / 0.0796 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1288 / 0.1288 | 0.0796 / 0.0796 | +0.0493 | +0.0493 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 19725 / 19725 | 21294 / 21294 | -1569 | -1569 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1723 / 1723 | 1466 / 1466 | +257 | +257 |
| cache_creation_input_tokens | 24777 / 24777 | 12073 / 12073 | +12704 | +12704 |
| cache_read_input_tokens | 124694 / 124694 | 165813 / 165813 | -41119 | -41119 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 1/1 |
| unowned-template-not-fatal | 1/1 | 1/1 |
| clean-tree-still-passes | 1/1 | 1/1 |
| drift-and-missing-still-fail | 1/1 | 1/1 |
| config-data-untouched | 1/1 | 1/1 |
