# Eval report: writing-adrs

- Timestamp: 20261026T145022Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145022Z-853e1c; started 2026-10-26T14:50:22Z, ended 2026-10-26T14:53:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.62 to 0.64, seven_day 0.79 to 0.79, from 7 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.1525 / 0.4575 |
| without_skill | 3 | 0 | 4.7/9 | skipped (objective-decided) | 0.1233 / 0.3698 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1525 / 0.1499 | 0.1233 / 0.1191 | +0.0292 | +0.0308 |
| num_turns | 6.7 / 7 | 4.7 / 4 | +2 | +3 |
| duration_ms | 26852.3 / 25978 | 22397 / 20460 | +4455.3 | +5518 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 2658 / 2517 | 2039.3 / 1817 | +618.7 | +700 |
| cache_creation_input_tokens | 28264 / 27982 | 22426 / 22340 | +5838 | +5642 |
| cache_read_input_tokens | 128419.7 / 128636 | 131583 / 119093 | -3163.3 | +9543 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 2/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
