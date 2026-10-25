# Eval report: finding-unknowns

- Timestamp: 20261025T215238Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T215120Z-f6bba8; started 2026-10-25T21:52:38Z, ended 2026-10-25T21:57:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.22 to 0.24, seven_day 0.46 to 0.47, from 8 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/4 | - | 0.2432 / 0.7295 |
| without_skill | 3 | 0 | 4/4 | - | 0.1846 / 0.5539 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2432 / 0.2181 | 0.1846 / 0.1880 | +0.0585 | +0.0301 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 47303.3 / 49190 | 45080.7 / 46998 | +2222.7 | +2192 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2732.3 / 2706 | 2591.3 / 2817 | +141 | -111 |
| cache_creation_input_tokens | 18462.7 / 14901 | 11685.7 / 11605 | +6777 | +3296 |
| cache_read_input_tokens | 203806 / 205413 | 196329 / 196072 | +7477 | +9341 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 3/3 | 3/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
