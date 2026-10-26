# Eval report: writing-adrs

- Timestamp: 20261026T102232Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T102139Z-2fb740; started 2026-10-26T10:22:32Z, ended 2026-10-26T10:26:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.1 to 0.11, seven_day 0.59 to 0.59, from 7 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.2822 / 0.8465 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1870 / 0.5609 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2822 / 0.2125 | 0.1870 / 0.1869 | +0.0952 | +0.0255 |
| num_turns | 5.3 / 5 | 3.7 / 4 | +1.7 | +1 |
| duration_ms | 32758 / 32566 | 35578.7 / 30946 | -2820.7 | +1620 |
| input_tokens | 6 / 6 | 7.3 / 8 | -1.3 | -2 |
| output_tokens | 2390.3 / 2445 | 2347.7 / 2175 | +42.7 | +270 |
| cache_creation_input_tokens | 26840.3 / 17672 | 14276.3 / 14383 | +12564 | +3289 |
| cache_read_input_tokens | 97493.7 / 106695 | 128286.7 / 141018 | -30793 | -34323 |
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
