# Eval report: writing-adrs

- Timestamp: 20261026T132551Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T132448Z-652426; started 2026-10-26T13:25:51Z, ended 2026-10-26T13:28:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.07 to 0.07, seven_day 0.67 to 0.67, from 6 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.0984 / 0.2953 |
| without_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.0762 / 0.2286 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0984 / 0.1015 | 0.0762 / 0.0762 | +0.0223 | +0.0254 |
| num_turns | 8 / 9 | 5.7 / 5 | +2.3 | +4 |
| duration_ms | 22215.7 / 22439 | 17473 / 17460 | +4742.7 | +4979 |
| input_tokens | 9.3 / 10 | 8.7 / 8 | +0.7 | +2 |
| output_tokens | 1953.3 / 2053 | 1544.7 / 1639 | +408.7 | +414 |
| cache_creation_input_tokens | 15307.3 / 15427 | 11328.3 / 11417 | +3979 | +4010 |
| cache_read_input_tokens | 175377 / 189191 | 152855.3 / 139540 | +22521.7 | +49651 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 1/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
