# Eval report: finding-unknowns

- Timestamp: 20261026T132506Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T132337Z-39a490; started 2026-10-26T13:25:06Z, ended 2026-10-26T13:29:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.06 to 0.08, seven_day 0.67 to 0.67, from 8 snapshots

## Fixture: finding-unknowns (n=3)

- Prompt: Before you start on TASK.md, work out what you don't know and resolve what you can.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/4 | - | 0.2507 / 0.7521 |
| without_skill | 3 | 0 | 3.7/4 | - | 0.1937 / 0.5811 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2507 / 0.2378 | 0.1937 / 0.1919 | +0.0570 | +0.0459 |
| num_turns | 8 / 8 | 6.7 / 7 | +1.3 | +1 |
| duration_ms | 44448 / 42876 | 42675 / 43603 | +1773 | -727 |
| input_tokens | 12 / 12 | 13.3 / 14 | -1.3 | -2 |
| output_tokens | 3125.3 / 3087 | 2704 / 2756 | +421.3 | +331 |
| cache_creation_input_tokens | 18444.7 / 15281 | 11945.7 / 11774 | +6499 | +3507 |
| cache_read_input_tokens | 202918.7 / 204997 | 220036.7 / 231720 | -17118 | -26723 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| cites-export-module | 3/3 | 2/3 |
| cites-acceptance-test | 2/3 | 3/3 |
| cites-design-decision | 3/3 | 3/3 |
| source-unchanged | 3/3 | 3/3 |
