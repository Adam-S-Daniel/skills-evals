# Eval report: writing-adrs

- Timestamp: 20261026T140305Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140200Z-570427; started 2026-10-26T14:03:05Z, ended 2026-10-26T14:06:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.25 to 0.29, seven_day 0.71 to 0.71, from 9 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1006 / 0.3017 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.0872 / 0.2615 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1006 / 0.1006 | 0.0872 / 0.0880 | +0.0134 | +0.0126 |
| num_turns | 8 / 9 | 5 / 4 | +3 | +5 |
| duration_ms | 24701.3 / 25592 | 28810.3 / 28851 | -4109 | -3259 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 2105 / 2158 | 2109.7 / 1956 | -4.7 | +202 |
| cache_creation_input_tokens | 16148.3 / 16021 | 12965.7 / 12768 | +3182.7 | +3253 |
| cache_read_input_tokens | 147673 / 147803 | 140692 / 140740 | +6981 | +7063 |
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
