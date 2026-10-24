# Eval report: writing-adrs

- Timestamp: 20261024T191527Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261024T191333Z-364116; started 2026-10-24T19:15:27Z, ended 2026-10-24T19:17:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.02 to 0.03, seven_day 0.34 to 0.35, from 7 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.1694 / 0.5081 |
| without_skill | 3 | 0 | 5/9 | skipped (objective-decided) | 0.1307 / 0.3920 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1694 / 0.1537 | 0.1307 / 0.1283 | +0.0387 | +0.0255 |
| num_turns | 6.3 / 6 | 6.3 / 6 | 0 | 0 |
| duration_ms | 23175.7 / 23532 | 23516.7 / 23021 | -341 | +511 |
| input_tokens | 8 / 8 | 11.3 / 10 | -3.3 | -2 |
| output_tokens | 2642.7 / 2591 | 2226 / 2225 | +416.7 | +366 |
| cache_creation_input_tokens | 32653.7 / 28158 | 22610 / 22609 | +10043.7 | +5549 |
| cache_read_input_tokens | 123024.3 / 127740 | 179445.3 / 155731 | -56421 | -27991 |
| tool_errors | 0.3 / 0 | 1.3 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
