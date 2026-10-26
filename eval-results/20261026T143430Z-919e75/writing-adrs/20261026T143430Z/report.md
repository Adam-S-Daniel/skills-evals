# Eval report: writing-adrs

- Timestamp: 20261026T143430Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143430Z-919e75; started 2026-10-26T14:34:30Z, ended 2026-10-26T14:39:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.5 to 0.53, seven_day 0.76 to 0.77, from 9 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.3035 / 0.9104 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1938 / 0.5814 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3035 / 0.2660 | 0.1938 / 0.1980 | +0.1097 | +0.0680 |
| num_turns | 6 / 6 | 4.3 / 4 | +1.7 | +2 |
| duration_ms | 37999 / 37547 | 34589 / 33725 | +3410 | +3822 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 2813.7 / 2532 | 2490.7 / 2616 | +323 | -84 |
| cache_creation_input_tokens | 27348.7 / 19280 | 14477 / 14679 | +12871.7 | +4601 |
| cache_read_input_tokens | 141225.7 / 119965 | 140049.3 / 140255 | +1176.3 | -20290 |
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
