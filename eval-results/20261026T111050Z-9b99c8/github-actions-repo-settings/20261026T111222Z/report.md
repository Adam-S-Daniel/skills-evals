# Eval report: github-actions-repo-settings

- Timestamp: 20261026T111222Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T111050Z-9b99c8; started 2026-10-26T11:12:22Z, ended 2026-10-26T11:14:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.16 to 0.16, seven_day 0.6 to 0.6, from 6 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/9 | skipped (objective-decided) | 0.1054 / 0.3162 |
| without_skill | 3 | 0 | 3.3/9 | skipped (objective-decided) | 0.0852 / 0.2555 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1054 / 0.0935 | 0.0852 / 0.0861 | +0.0203 | +0.0074 |
| num_turns | 5.3 / 5 | 5 / 5 | +0.3 | 0 |
| duration_ms | 20731.3 / 20507 | 18681 / 17533 | +2050.3 | +2974 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1846.3 / 1918 | 1603.7 / 1570 | +242.7 | +348 |
| cache_creation_input_tokens | 17605.3 / 14342 | 13144.3 / 13590 | +4461 | +752 |
| cache_read_input_tokens | 165053 / 168399 | 165190.7 / 167056 | -137.7 | +1343 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 2/3 | 0/3 |
| beta-live-settings-read | 2/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
