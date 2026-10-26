# Eval report: writing-adrs

- Timestamp: 20261026T060201Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T060035Z-9e285d; started 2026-10-26T06:02:01Z, ended 2026-10-26T06:04:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.56 to 0.56, from 7 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.7/9 | skipped (objective-decided) | 0.1779 / 0.5338 |
| without_skill | 3 | 0 | 4.3/9 | skipped (objective-decided) | 0.1222 / 0.3665 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1779 / 0.1658 | 0.1222 / 0.1243 | +0.0558 | +0.0415 |
| num_turns | 6.7 / 7 | 5.3 / 6 | +1.3 | +1 |
| duration_ms | 27707 / 27199 | 21425.3 / 21259 | +6281.7 | +5940 |
| input_tokens | 8 / 8 | 9.3 / 10 | -1.3 | -2 |
| output_tokens | 3264.3 / 3355 | 1904.3 / 1921 | +1360 | +1434 |
| cache_creation_input_tokens | 33234 / 29122 | 22195.7 / 22364 | +11038.3 | +6758 |
| cache_read_input_tokens | 123499 / 127759 | 143320.7 / 155521 | -19821.7 | -27762 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 2/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 2/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 2/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
