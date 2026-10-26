# Eval report: finding-unknowns

- Timestamp: 20261026T124928Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T124811Z-b00461; started 2026-10-26T12:49:28Z, ended 2026-10-26T12:52:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.4 to 0.42, seven_day 0.65 to 0.66, from 8 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/4 | - | 0.1243 / 0.3728 |
| without_skill | 3 | 0 | 2.3/4 | - | 0.0950 / 0.2851 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1243 / 0.1173 | 0.0950 / 0.0831 | +0.0292 | +0.0342 |
| num_turns | 10.7 / 11 | 8.7 / 7 | +2 | +4 |
| duration_ms | 31261.3 / 29587 | 30939.3 / 28589 | +322 | +998 |
| input_tokens | 16.7 / 18 | 16 / 14 | +0.7 | +4 |
| output_tokens | 2404.7 / 2488 | 2242.7 / 1839 | +162 | +649 |
| cache_creation_input_tokens | 17801.3 / 14651 | 11535.7 / 11363 | +6265.7 | +3288 |
| cache_read_input_tokens | 289963.7 / 306766 | 264445 / 225853 | +25518.7 | +80913 |
| tool_errors | 0 / 0 | 0.7 / 0 | -0.7 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 3/3 | 0/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 2/3 |
| source-unchanged | 3/3 | 2/3 |
