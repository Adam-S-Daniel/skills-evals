# Eval report: writing-adrs

- Timestamp: 20261026T140302Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140203Z-9f7bc6; started 2026-10-26T14:03:02Z, ended 2026-10-26T14:07:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.25 to 0.3, seven_day 0.71 to 0.71, from 10 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.2263 / 0.6789 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1855 / 0.5566 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2263 / 0.2224 | 0.1855 / 0.1827 | +0.0408 | +0.0397 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 35683 / 33938 | 33836.7 / 31920 | +1846.3 | +2018 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 2581.3 / 2428 | 2266.3 / 2226 | +315 | +202 |
| cache_creation_input_tokens | 18068.3 / 17998 | 13979.3 / 13761 | +4089 | +4237 |
| cache_read_input_tokens | 149892 / 148555 | 140980 / 140972 | +8912 | +7583 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
