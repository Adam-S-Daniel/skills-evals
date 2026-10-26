# Eval report: finding-unknowns

- Timestamp: 20261026T104420Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T104313Z-cbfaf9; started 2026-10-26T10:44:20Z, ended 2026-10-26T10:47:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.12 to 0.12, seven_day 0.59 to 0.6, from 7 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/4 | - | 0.1218 / 0.3654 |
| without_skill | 3 | 0 | 3/4 | - | 0.0890 / 0.2671 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1218 / 0.1188 | 0.0890 / 0.0892 | +0.0328 | +0.0296 |
| num_turns | 10.7 / 11 | 7.7 / 8 | +3 | +3 |
| duration_ms | 35831.3 / 39161 | 31268 / 31884 | +4563.3 | +7277 |
| input_tokens | 16 / 16 | 14.7 / 16 | +1.3 | 0 |
| output_tokens | 2527.3 / 2476 | 2107.7 / 2110 | +419.7 | +366 |
| cache_creation_input_tokens | 17223.7 / 15433 | 10993.3 / 10827 | +6230.3 | +4606 |
| cache_read_input_tokens | 276074.3 / 287552 | 239655 / 261715 | +36419.3 | +25837 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 2/3 | 1/3 |
| cites-acceptance-test | 3/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 2/3 |
