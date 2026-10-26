# Eval report: writing-adrs

- Timestamp: 20261026T111729Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T111631Z-d5c6ae; started 2026-10-26T11:17:29Z, ended 2026-10-26T11:20:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.17 to 0.17, seven_day 0.61 to 0.61, from 6 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1038 / 0.3115 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.0870 / 0.2609 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1038 / 0.1042 | 0.0870 / 0.0883 | +0.0169 | +0.0159 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 22831 / 22578 | 21012 / 20539 | +1819 | +2039 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 2434.7 / 2469 | 2184.3 / 2179 | +250.3 | +290 |
| cache_creation_input_tokens | 16137.3 / 16141 | 12723.3 / 12725 | +3414 | +3416 |
| cache_read_input_tokens | 147811.7 / 147802 | 140697 / 140638 | +7114.7 | +7164 |
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
