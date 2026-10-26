# Eval report: writing-adrs

- Timestamp: 20261026T111730Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T111631Z-c7490d; started 2026-10-26T11:17:30Z, ended 2026-10-26T11:22:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.17 to 0.17, seven_day 0.61 to 0.61, from 6 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 9.6 (9.5 to 9.8, 3 judged) | 0.2170 / 0.6510 |
| without_skill | 3 | 0 | 7/7 | 9.0 (8.8 to 9.3, 3 judged) | 0.1827 / 0.5480 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2170 / 0.2175 | 0.1827 / 0.1798 | +0.0343 | +0.0377 |
| num_turns | 6.7 / 7 | 4.7 / 4 | +2 | +3 |
| duration_ms | 34856 / 36321 | 32804 / 32119 | +2052 | +4202 |
| input_tokens | 8.7 / 8 | 9.3 / 8 | -0.7 | 0 |
| output_tokens | 2434.3 / 2492 | 2098.3 / 2114 | +336 | +378 |
| cache_creation_input_tokens | 16977.7 / 17022 | 13361.7 / 13597 | +3616 | +3425 |
| cache_read_input_tokens | 161680.7 / 148469 | 168283 / 142894 | -6602.3 | +5575 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| adr-0004-house-format-sections-in-order | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
