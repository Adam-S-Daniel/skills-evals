# Eval report: writing-adrs

- Timestamp: 20261025T020744Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T020641Z-674ad6; started 2026-10-25T02:07:44Z, ended 2026-10-25T02:13:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.1 to 0.11, seven_day 0.37 to 0.38, from 8 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.3974 / 1.1921 |
| without_skill | 3 | 0 | 3.7/9 | skipped (objective-decided) | 0.2932 / 0.8796 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3974 / 0.4042 | 0.2932 / 0.2931 | +0.1042 | +0.1112 |
| num_turns | 10 / 10 | 6 / 6 | +4 | +4 |
| duration_ms | 63435.3 / 60960 | 44064.7 / 43844 | +19370.7 | +17116 |
| input_tokens | 16.7 / 16 | 11.3 / 12 | +5.3 | +4 |
| output_tokens | 4562.7 / 4897 | 3161.3 / 3223 | +1401.3 | +1674 |
| cache_creation_input_tokens | 30698.7 / 30990 | 24195.3 / 24166 | +6503.3 | +6824 |
| cache_read_input_tokens | 302223.3 / 291561 | 181786.7 / 192699 | +120436.7 | +98862 |
| tool_errors | 0.7 / 0 | 0.7 / 1 | 0 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 1/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 1/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
