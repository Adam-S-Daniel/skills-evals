# Eval report: writing-adrs

- Timestamp: 20261026T145310Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145309Z-10cac2; started 2026-10-26T14:53:10Z, ended 2026-10-26T14:58:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.64 to 0.68, seven_day 0.79 to 0.8, from 10 snapshots

## Fixture: supersede (n=3)

- Prompt: Record the snapshot-retention decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.2083 / 0.6250 |
| without_skill | 3 | 0 | 13/13 | 10.0 (10.0 to 10.0, 3 judged) | 0.1989 / 0.5966 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2083 / 0.2089 | 0.1989 / 0.2024 | +0.0095 | +0.0065 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 30628.7 / 29614 | 35510 / 35428 | -4881.3 | -5814 |
| input_tokens | 6 / 6 | 9.3 / 10 | -3.3 | -4 |
| output_tokens | 2382.3 / 2382 | 2523.3 / 2516 | -141 | -134 |
| cache_creation_input_tokens | 17418.3 / 17385 | 14359 / 14784 | +3059.3 | +2601 |
| cache_read_input_tokens | 106021 / 106030 | 166824.7 / 176049 | -60803.7 | -70019 |
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
