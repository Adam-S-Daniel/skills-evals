# Eval report: finding-unknowns

- Timestamp: 20261026T145524Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145523Z-6dc188; started 2026-10-26T14:55:24Z, ended 2026-10-26T15:00:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.67 to 0.71, seven_day 0.8 to 0.81, from 8 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/4 | - | 0.2437 / 0.7312 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.1796 / 0.5388 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2437 / 0.2263 | 0.1796 / 0.1818 | +0.0641 | +0.0445 |
| num_turns | 8 / 8 | 5.7 / 6 | +2.3 | +2 |
| duration_ms | 45417.3 / 39995 | 43486 / 44048 | +1931.3 | -4053 |
| input_tokens | 12 / 12 | 11.3 / 12 | +0.7 | 0 |
| output_tokens | 2887.7 / 2985 | 2642 / 2613 | +245.7 | +372 |
| cache_creation_input_tokens | 18176 / 15602 | 11260 / 11319 | +6916 | +4283 |
| cache_read_input_tokens | 202541 / 207371 | 183106 / 194493 | +19435 | +12878 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 3/3 | 3/3 |
| cites-acceptance-test | 3/3 | 2/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
