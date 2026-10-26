# Eval report: writing-adrs

- Timestamp: 20261026T134126Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T134029Z-338e46; started 2026-10-26T13:41:26Z, ended 2026-10-26T13:44:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.68 to 0.68, from 7 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1051 / 0.3152 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.0886 / 0.2658 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1051 / 0.1054 | 0.0886 / 0.0864 | +0.0165 | +0.0190 |
| num_turns | 10 / 10 | 8.3 / 8 | +1.7 | +2 |
| duration_ms | 24698.3 / 23506 | 22450.7 / 21685 | +2247.7 | +1821 |
| input_tokens | 8 / 8 | 8.7 / 8 | -0.7 | 0 |
| output_tokens | 2425.7 / 2367 | 2208 / 2113 | +217.7 | +254 |
| cache_creation_input_tokens | 16469 / 16484 | 12742.3 / 12758 | +3726.7 | +3726 |
| cache_read_input_tokens | 148025.7 / 147935 | 154141 / 140626 | -6115.3 | +7309 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| new-adr-0004-is-a-house-format-entry | 3/3 | 3/3 |
| new-adr-0004-names-0002 | 3/3 | 3/3 |
| adr-0002-status-says-superseded-by-0004 | 3/3 | 3/3 |
| adr-0002-keeps-what-it-recorded | 3/3 | 3/3 |
| index-gained-a-row-for-0004 | 3/3 | 3/3 |
| index-row-for-0002-says-superseded-by-0004 | 3/3 | 3/3 |
| index-rows-for-0001-and-0003-kept | 3/3 | 3/3 |
| decision-log-links-resolve | 3/3 | 3/3 |
| script-comment-points-at-0004 | 3/3 | 3/3 |
| script-adr-pointers-resolve | 3/3 | 3/3 |
| script-still-keeps-the-newest-14 | 3/3 | 3/3 |
| exactly-one-new-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
