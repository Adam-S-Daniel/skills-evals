# Eval report: writing-adrs

- Timestamp: 20261026T135330Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135201Z-8320a9; started 2026-10-26T13:53:30Z, ended 2026-10-26T13:56:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.16 to 0.2, seven_day 0.69 to 0.7, from 9 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.1639 / 0.4917 |
| without_skill | 3 | 0 | 4/9 | skipped (objective-decided) | 0.1205 / 0.3616 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1639 / 0.1617 | 0.1205 / 0.1180 | +0.0434 | +0.0437 |
| num_turns | 7.3 / 7 | 4.3 / 4 | +3 | +3 |
| duration_ms | 28969 / 26788 | 28603 / 23925 | +366 | +2863 |
| input_tokens | 8.7 / 8 | 8.7 / 8 | 0 | 0 |
| output_tokens | 3385.3 / 3294 | 1772 / 1703 | +1613.3 | +1591 |
| cache_creation_input_tokens | 28937.7 / 28967 | 22400 / 22256 | +6537.7 | +6711 |
| cache_read_input_tokens | 142725.3 / 129015 | 131841 / 119243 | +10884.3 | +9772 |
| tool_errors | 0.3 / 0 | 1 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 1/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 2/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
