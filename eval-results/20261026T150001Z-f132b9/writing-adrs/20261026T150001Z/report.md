# Eval report: writing-adrs

- Timestamp: 20261026T150001Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T150001Z-f132b9; started 2026-10-26T15:00:01Z, ended 2026-10-26T15:05:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.71 to 0.74, seven_day 0.81 to 0.81, from 8 snapshots

## Fixture: existing-convention (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 9.7 (9.5 to 10.0, 3 judged) | 0.2078 / 0.6235 |
| without_skill | 3 | 0 | 7/7 | 9.5 (9.5 to 9.5, 3 judged) | 0.2126 / 0.6377 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2078 / 0.2122 | 0.2126 / 0.2126 | -0.0047 | -0.0004 |
| num_turns | 5.7 / 6 | 6 / 6 | -0.3 | 0 |
| duration_ms | 32019.7 / 33404 | 39380.7 / 40178 | -7361 | -6774 |
| input_tokens | 7.3 / 8 | 12 / 12 | -4.7 | -4 |
| output_tokens | 2357.3 / 2425 | 2842 / 2812 | -484.7 | -387 |
| cache_creation_input_tokens | 16712.3 / 16769 | 13909.3 / 14006 | +2803 | +2763 |
| cache_read_input_tokens | 134160.7 / 146941 | 221360.7 / 220757 | -87200 | -73816 |
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
