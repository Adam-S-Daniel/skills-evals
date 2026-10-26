# Eval report: github-actions-repo-settings

- Timestamp: 20261026T143440Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143439Z-702244; started 2026-10-26T14:34:40Z, ended 2026-10-26T14:37:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.5 to 0.53, seven_day 0.76 to 0.77, from 10 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/9 | skipped (objective-decided) | 0.1041 / 0.3122 |
| without_skill | 3 | 0 | 3.7/9 | skipped (objective-decided) | 0.0918 / 0.2754 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1041 / 0.0891 | 0.0918 / 0.0913 | +0.0122 | -0.0022 |
| num_turns | 4.7 / 5 | 5.3 / 5 | -0.7 | 0 |
| duration_ms | 26664.3 / 27303 | 26889 / 28539 | -224.7 | -1236 |
| input_tokens | 8.7 / 8 | 10 / 10 | -1.3 | -2 |
| output_tokens | 1757.3 / 1727 | 1773 / 1764 | -15.7 | -37 |
| cache_creation_input_tokens | 18101.3 / 14668 | 14311.3 / 14098 | +3790 | +570 |
| cache_read_input_tokens | 140660.3 / 131459 | 168182.7 / 168022 | -27522.3 | -36563 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 0/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 2/3 | 1/3 |
| beta-live-settings-read | 2/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
