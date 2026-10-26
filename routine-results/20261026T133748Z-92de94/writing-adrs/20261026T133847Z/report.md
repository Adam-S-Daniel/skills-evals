# Eval report: writing-adrs

- Timestamp: 20261026T133847Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T133748Z-92de94; started 2026-10-26T13:38:47Z, ended 2026-10-26T13:43:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.1 to 0.11, seven_day 0.68 to 0.68, from 7 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 9.7 (9.5 to 10.0, 3 judged) | 0.2113 / 0.6340 |
| without_skill | 3 | 0 | 7/7 | 9.0 (9.0 to 9.0, 3 judged) | 0.1637 / 0.4910 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2113 / 0.1997 | 0.1637 / 0.1663 | +0.0476 | +0.0334 |
| num_turns | 6.3 / 7 | 3.7 / 4 | +2.7 | +3 |
| duration_ms | 32550.7 / 30672 | 24599 / 23446 | +7951.7 | +7226 |
| input_tokens | 8 / 8 | 7.3 / 8 | +0.7 | 0 |
| output_tokens | 2379.7 / 2064 | 1823.7 / 1719 | +556 | +345 |
| cache_creation_input_tokens | 16723 / 16142 | 12666.7 / 12958 | +4056.3 | +3184 |
| cache_read_input_tokens | 148930 / 147667 | 128562.7 / 140645 | +20367.3 | +7022 |
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
