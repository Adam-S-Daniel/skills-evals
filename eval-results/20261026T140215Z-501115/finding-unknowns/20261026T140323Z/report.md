# Eval report: finding-unknowns

- Timestamp: 20261026T140323Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140215Z-501115; started 2026-10-26T14:03:23Z, ended 2026-10-26T14:07:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.25 to 0.31, seven_day 0.71 to 0.72, from 12 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/4 | - | 0.1181 / 0.3544 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.0905 / 0.2716 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1181 / 0.1172 | 0.0905 / 0.0900 | +0.0276 | +0.0272 |
| num_turns | 10.3 / 10 | 8.7 / 9 | +1.7 | +1 |
| duration_ms | 51759.3 / 61849 | 30043.7 / 31366 | +21715.7 | +30483 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 2154.3 / 2137 | 2042.3 / 1968 | +112 | +169 |
| cache_creation_input_tokens | 17247.7 / 15233 | 10950.3 / 11025 | +6297.3 | +4208 |
| cache_read_input_tokens | 275653.7 / 273595 | 262685.3 / 262145 | +12968.3 | +11450 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 2/3 | 2/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
