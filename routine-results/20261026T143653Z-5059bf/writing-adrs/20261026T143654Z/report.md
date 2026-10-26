# Eval report: writing-adrs

- Timestamp: 20261026T143654Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143653Z-5059bf; started 2026-10-26T14:36:54Z, ended 2026-10-26T14:42:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.52 to 0.54, seven_day 0.77 to 0.77, from 7 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.2369 / 0.7107 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1871 / 0.5612 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2369 / 0.2306 | 0.1871 / 0.1862 | +0.0498 | +0.0444 |
| num_turns | 7 / 7 | 3.7 / 4 | +3.3 | +3 |
| duration_ms | 39034.3 / 36418 | 31358.7 / 30892 | +7675.7 | +5526 |
| input_tokens | 8.7 / 8 | 7.3 / 8 | +1.3 | 0 |
| output_tokens | 2744 / 2609 | 2347 / 2246 | +397 | +363 |
| cache_creation_input_tokens | 18650 / 18550 | 14299.3 / 14322 | +4350.7 | +4228 |
| cache_read_input_tokens | 163207.7 / 149299 | 127823 / 139918 | +35384.7 | +9381 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

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
