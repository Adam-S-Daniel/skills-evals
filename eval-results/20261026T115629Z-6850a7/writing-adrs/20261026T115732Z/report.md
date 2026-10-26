# Eval report: writing-adrs

- Timestamp: 20261026T115732Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T115629Z-6850a7; started 2026-10-26T11:57:32Z, ended 2026-10-26T11:59:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.2 to 0.2, seven_day 0.61 to 0.61, from 6 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1051 / 0.3153 |
| without_skill | 3 | 0 | 6/7 | skipped (objective-decided) | 0.0709 / 0.2127 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1051 / 0.1035 | 0.0709 / 0.0711 | +0.0342 | +0.0324 |
| num_turns | 9.3 / 9 | 4 / 4 | +5.3 | +5 |
| duration_ms | 23358.3 / 24557 | 16396.3 / 16026 | +6962 | +8531 |
| input_tokens | 10.7 / 10 | 8 / 8 | +2.7 | +2 |
| output_tokens | 2254.7 / 2263 | 1309.7 / 1319 | +945 | +944 |
| cache_creation_input_tokens | 15510.3 / 15495 | 10926.7 / 10949 | +4583.7 | +4546 |
| cache_read_input_tokens | 203735 / 189736 | 139492 / 139514 | +64243 | +50222 |
| tool_errors | 1.3 / 1 | 0 / 0 | +1.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 0/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
