# Eval report: finding-unknowns

- Timestamp: 20261026T114144Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T114005Z-b0b7dc; started 2026-10-26T11:41:44Z, ended 2026-10-26T11:45:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.19 to 0.19, seven_day 0.61 to 0.61, from 6 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/4 | - | 0.1170 / 0.3510 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.0844 / 0.2533 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1170 / 0.1029 | 0.0844 / 0.0831 | +0.0326 | +0.0199 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 42215.3 / 42143 | 30573 / 34084 | +11642.3 | +8059 |
| input_tokens | 14.7 / 14 | 14 / 14 | +0.7 | 0 |
| output_tokens | 2141.7 / 2182 | 1677.7 / 1651 | +464 | +531 |
| cache_creation_input_tokens | 17564 / 13595 | 11165.7 / 11213 | +6398.3 | +2382 |
| cache_read_input_tokens | 252827.7 / 241631 | 229671.3 / 227314 | +23156.3 | +14317 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 2/3 | 2/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
