# Eval report: finding-unknowns

- Timestamp: 20261026T134808Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T134627Z-3b5a49; started 2026-10-26T13:48:08Z, ended 2026-10-26T13:52:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.13 to 0.15, seven_day 0.68 to 0.69, from 9 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/4 | - | 0.1171 / 0.3513 |
| without_skill | 3 | 0 | 3.3/4 | - | 0.0883 / 0.2649 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1171 / 0.1000 | 0.0883 / 0.0885 | +0.0288 | +0.0116 |
| num_turns | 10 / 9 | 7.7 / 8 | +2.3 | +1 |
| duration_ms | 49604.7 / 49759 | 28561.3 / 30283 | +21043.3 | +19476 |
| input_tokens | 14.7 / 14 | 15.3 / 16 | -0.7 | -2 |
| output_tokens | 2365.3 / 2405 | 1812.7 / 1840 | +552.7 | +565 |
| cache_creation_input_tokens | 17069 / 13181 | 11211.7 / 11058 | +5857.3 | +2123 |
| cache_read_input_tokens | 251344.7 / 241698 | 252854.7 / 261418 | -1510 | -19720 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 2/3 | 1/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
