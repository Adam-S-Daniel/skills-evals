# Eval report: review-bash-ci-reliability

- Timestamp: 20261027T233740Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261027T233554Z-695948; started 2026-10-27T23:37:40Z, ended 2026-10-27T23:38:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.1 to 0.1, seven_day 0.2 to 0.2, from 4 snapshots

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.1849 / 0.1849 |
| without_skill | 1 | 0 | 7/7 | 9.8 (9.8 to 9.8, 1 judged) | 0.0826 / 0.0826 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1849 / 0.1849 | 0.0826 / 0.0826 | +0.1023 | +0.1023 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 19114 / 19114 | 25054 / 25054 | -5940 | -5940 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1613 / 1613 | 1682 / 1682 | -69 | -69 |
| cache_creation_input_tokens | 38521 / 38521 | 12307 / 12307 | +26214 | +26214 |
| cache_read_input_tokens | 146470 / 146470 | 165230 / 165230 | -18760 | -18760 |
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
