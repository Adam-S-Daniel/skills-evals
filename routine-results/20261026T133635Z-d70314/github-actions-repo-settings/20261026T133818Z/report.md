# Eval report: github-actions-repo-settings

- Timestamp: 20261026T133818Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T133635Z-d70314; started 2026-10-26T13:38:18Z, ended 2026-10-26T13:40:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.1 to 0.11, seven_day 0.68 to 0.68, from 7 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/9 | skipped (objective-decided) | 0.1030 / 0.3091 |
| without_skill | 3 | 0 | 3.3/9 | skipped (objective-decided) | 0.0853 / 0.2560 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1030 / 0.0907 | 0.0853 / 0.0844 | +0.0177 | +0.0064 |
| num_turns | 5 / 5 | 4.3 / 4 | +0.7 | +1 |
| duration_ms | 26229.3 / 25956 | 22196.7 / 21547 | +4032.7 | +4409 |
| input_tokens | 10 / 10 | 8.7 / 8 | +1.3 | +2 |
| output_tokens | 1608.3 / 1683 | 1641.7 / 1664 | -33.3 | +19 |
| cache_creation_input_tokens | 17623.7 / 14254 | 13672.3 / 13645 | +3951.3 | +609 |
| cache_read_input_tokens | 164481.7 / 166926 | 142129.3 / 130218 | +22352.3 | +36708 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 1/3 | 0/3 |
| beta-live-settings-read | 1/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
