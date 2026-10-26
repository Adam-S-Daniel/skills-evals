# Eval report: finding-unknowns

- Timestamp: 20261026T122314Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T122158Z-d01d58; started 2026-10-26T12:23:14Z, ended 2026-10-26T12:28:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.29 to 0.31, seven_day 0.63 to 0.64, from 8 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/4 | - | 0.2470 / 0.7409 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.1845 / 0.5536 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2470 / 0.2257 | 0.1845 / 0.1837 | +0.0625 | +0.0421 |
| num_turns | 8 / 8 | 6.3 / 6 | +1.7 | +2 |
| duration_ms | 46796.7 / 44974 | 45646 / 48853 | +1150.7 | -3879 |
| input_tokens | 12 / 12 | 12.7 / 12 | -0.7 | 0 |
| output_tokens | 2888.3 / 2870 | 2378.7 / 2463 | +509.7 | +407 |
| cache_creation_input_tokens | 18557.7 / 15166 | 11898.7 / 11958 | +6659 | +3208 |
| cache_read_input_tokens | 203523.7 / 205245 | 208559.7 / 197103 | -5036 | +8142 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 2/3 | 2/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
