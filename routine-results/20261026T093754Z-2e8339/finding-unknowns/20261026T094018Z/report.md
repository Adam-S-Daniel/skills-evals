# Eval report: finding-unknowns

- Timestamp: 20261026T094018Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T093754Z-2e8339; started 2026-10-26T09:40:18Z, ended 2026-10-26T09:45:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.07 to 0.07, seven_day 0.58 to 0.58, from 6 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/4 | - | 0.2439 / 0.7316 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.1901 / 0.5704 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2439 / 0.2219 | 0.1901 / 0.1819 | +0.0538 | +0.0400 |
| num_turns | 8 / 8 | 6.3 / 6 | +1.7 | +2 |
| duration_ms | 44528 / 43316 | 46867 / 45163 | -2339 | -1847 |
| input_tokens | 12 / 12 | 12.7 / 12 | -0.7 | 0 |
| output_tokens | 2760 / 2892 | 2647.3 / 2465 | +112.7 | +427 |
| cache_creation_input_tokens | 18502.7 / 15169 | 11942.7 / 11675 | +6560 | +3494 |
| cache_read_input_tokens | 203064.7 / 205497 | 207967.3 / 195987 | -4902.7 | +9510 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 3/3 | 2/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
