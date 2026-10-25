# Eval report: writing-adrs

- Timestamp: 20261025T232304Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T232219Z-37b90c; started 2026-10-25T23:23:04Z, ended 2026-10-25T23:27:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.07 to 0.08, seven_day 0.49 to 0.49, from 6 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.3006 / 0.9018 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1849 / 0.5547 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3006 / 0.2346 | 0.1849 / 0.1726 | +0.1157 | +0.0620 |
| num_turns | 6.7 / 7 | 4 / 3 | +2.7 | +4 |
| duration_ms | 36957.3 / 36019 | 30990 / 28069 | +5967.3 | +7950 |
| input_tokens | 8 / 8 | 8 / 6 | 0 | +2 |
| output_tokens | 2714.3 / 2700 | 2259 / 2064 | +455.3 | +636 |
| cache_creation_input_tokens | 27249 / 18305 | 13873.3 / 13832 | +13375.7 | +4473 |
| cache_read_input_tokens | 140850 / 149877 | 142924 / 102771 | -2074 | +47106 |
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
