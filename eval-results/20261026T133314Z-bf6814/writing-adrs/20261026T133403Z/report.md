# Eval report: writing-adrs

- Timestamp: 20261026T133403Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T133314Z-bf6814; started 2026-10-26T13:34:03Z, ended 2026-10-26T13:38:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.09 to 0.1, seven_day 0.68 to 0.68, from 6 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.2188 / 0.6564 |
| without_skill | 3 | 0 | 13/13 | 9.2 (7.7 to 10.0, 3 judged) | 0.1942 / 0.5827 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2188 / 0.2098 | 0.1942 / 0.2003 | +0.0246 | +0.0095 |
| num_turns | 5.7 / 5 | 4.3 / 4 | +1.3 | +1 |
| duration_ms | 32382 / 29277 | 32136.3 / 31591 | +245.7 | -2314 |
| input_tokens | 7.3 / 6 | 8.7 / 8 | -1.3 | -2 |
| output_tokens | 2446 / 2290 | 2386.3 / 2435 | +59.7 | -145 |
| cache_creation_input_tokens | 17819.3 / 17807 | 14402.7 / 14352 | +3416.7 | +3455 |
| cache_read_input_tokens | 135891.7 / 106793 | 155648.7 / 143692 | -19757 | -36899 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

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
