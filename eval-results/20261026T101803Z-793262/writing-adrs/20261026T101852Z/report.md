# Eval report: writing-adrs

- Timestamp: 20261026T101852Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T101803Z-793262; started 2026-10-26T10:18:52Z, ended 2026-10-26T10:21:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.1 to 0.1, seven_day 0.59 to 0.59, from 6 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1053 / 0.3160 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.0731 / 0.2194 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1053 / 0.1041 | 0.0731 / 0.0711 | +0.0322 | +0.0330 |
| num_turns | 8.7 / 9 | 4.7 / 4 | +4 | +5 |
| duration_ms | 27353.3 / 28250 | 20906.3 / 20132 | +6447 | +8118 |
| input_tokens | 10.7 / 10 | 8.7 / 8 | +2 | +2 |
| output_tokens | 2171 / 2293 | 1362.3 / 1322 | +808.7 | +971 |
| cache_creation_input_tokens | 15743.7 / 15503 | 11030.7 / 10939 | +4713 | +4564 |
| cache_read_input_tokens | 204939.7 / 190025 | 152460.3 / 139495 | +52479.3 | +50530 |
| tool_errors | 1 / 1 | 0.3 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 0/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
