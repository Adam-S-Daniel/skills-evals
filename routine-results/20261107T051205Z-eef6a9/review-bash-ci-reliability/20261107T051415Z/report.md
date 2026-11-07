# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T051415Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051205Z-eef6a9; started 2026-11-07T05:14:15Z, ended 2026-11-07T05:15:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.34, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.25, judge $0.07, guard $0.00; last agent call $0.10

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1514 / 0.1514 |
| without_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.0968 / 0.0968 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1514 / 0.1514 | 0.0968 / 0.0968 | +0.0546 | +0.0546 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 26836 / 26836 | 26618 / 26618 | +218 | +218 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 2366 / 2366 | 2378 / 2378 | -12 | -12 |
| cache_creation_input_tokens | 26796 / 26796 | 13151 / 13151 | +13645 | +13645 |
| cache_read_input_tokens | 205241 / 205241 | 203769 / 203769 | +1472 | +1472 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 1/1 |
| unowned-template-not-fatal | 1/1 | 1/1 |
| clean-tree-still-passes | 1/1 | 1/1 |
| drift-and-missing-still-fail | 1/1 | 1/1 |
| config-data-untouched | 1/1 | 1/1 |
