# Eval report: writing-adrs

- Timestamp: 20261026T120256Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T120137Z-e760c4; started 2026-10-26T12:02:56Z, ended 2026-10-26T12:06:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.21 to 0.22, seven_day 0.61 to 0.62, from 8 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1009 / 0.3027 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.0875 / 0.2626 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1009 / 0.0997 | 0.0875 / 0.0883 | +0.0134 | +0.0114 |
| num_turns | 8.3 / 9 | 6.7 / 8 | +1.7 | +1 |
| duration_ms | 28475.7 / 27086 | 22697.3 / 22617 | +5778.3 | +4469 |
| input_tokens | 8.7 / 8 | 8 / 8 | +0.7 | 0 |
| output_tokens | 2095.3 / 2126 | 2069.3 / 2201 | +26 | -75 |
| cache_creation_input_tokens | 15896.7 / 15888 | 13149 / 13167 | +2747.7 | +2721 |
| cache_read_input_tokens | 162097.3 / 147755 | 140883.3 / 140801 | +21214 | +6954 |
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
