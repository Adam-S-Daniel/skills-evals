# Eval report: writing-adrs

- Timestamp: 20261026T130458Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T130313Z-5a5ec5; started 2026-10-26T13:04:58Z, ended 2026-10-26T13:07:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.01 to 0.02, seven_day 0.66 to 0.66, from 7 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.1522 / 0.4566 |
| without_skill | 3 | 0 | 5/9 | skipped (objective-decided) | 0.1256 / 0.3769 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1522 / 0.1528 | 0.1256 / 0.1241 | +0.0266 | +0.0287 |
| num_turns | 6.3 / 6 | 5.3 / 5 | +1 | +1 |
| duration_ms | 30316 / 30553 | 19606.7 / 17842 | +10709.3 | +12711 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 2774 / 2859 | 2187.7 / 2061 | +586.3 | +798 |
| cache_creation_input_tokens | 27907.3 / 27849 | 22633 / 22834 | +5274.3 | +5015 |
| cache_read_input_tokens | 128005.3 / 127656 | 131961.3 / 121160 | -3956 | +6496 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

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
