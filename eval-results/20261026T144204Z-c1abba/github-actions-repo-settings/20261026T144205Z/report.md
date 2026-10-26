# Eval report: github-actions-repo-settings

- Timestamp: 20261026T144205Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144204Z-c1abba; started 2026-10-26T14:42:05Z, ended 2026-10-26T14:45:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.55 to 0.58, seven_day 0.78 to 0.78, from 6 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/9 | skipped (objective-decided) | 0.1047 / 0.3141 |
| without_skill | 3 | 0 | 3/9 | skipped (objective-decided) | 0.0959 / 0.2876 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1047 / 0.0929 | 0.0959 / 0.0965 | +0.0088 | -0.0036 |
| num_turns | 5 / 5 | 5.3 / 5 | -0.3 | 0 |
| duration_ms | 33142.3 / 33303 | 32672.7 / 29357 | +469.7 | +3946 |
| input_tokens | 9.3 / 10 | 10 / 10 | -0.7 | 0 |
| output_tokens | 1875.3 / 1961 | 1786.7 / 1666 | +88.7 | +295 |
| cache_creation_input_tokens | 17666.3 / 14104 | 15279 / 15546 | +2387.3 | -1442 |
| cache_read_input_tokens | 152692.3 / 158516 | 168633.3 / 169386 | -15941 | -10870 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 0/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 2/3 | 0/3 |
| beta-live-settings-read | 2/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
