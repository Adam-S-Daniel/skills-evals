# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T082125Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T081958Z-0ed9a8; started 2026-11-07T08:21:25Z, ended 2026-11-07T08:22:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.23, judge $0.09, guard $0.00; last agent call $0.09

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1442 / 0.1442 |
| without_skill | 1 | 0 | 7/7 | 7.6 (7.6 to 7.6, 1 judged) | 0.0899 / 0.0899 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1442 / 0.1442 | 0.0899 / 0.0899 | +0.0543 | +0.0543 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 23564 / 23564 | 24946 / 24946 | -1382 | -1382 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2466 / 2466 | 1952 / 1952 | +514 | +514 |
| cache_creation_input_tokens | 25759 / 25759 | 12550 / 12550 | +13209 | +13209 |
| cache_read_input_tokens | 165034 / 165034 | 201623 / 201623 | -36589 | -36589 |
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
