# Eval report: github-actions-repo-settings

- Timestamp: 20261026T121243Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T121116Z-e42fa6; started 2026-10-26T12:12:43Z, ended 2026-10-26T12:15:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.24 to 0.25, seven_day 0.62 to 0.62, from 7 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/9 | skipped (objective-decided) | 0.0984 / 0.2952 |
| without_skill | 3 | 0 | 3/9 | skipped (objective-decided) | 0.0898 / 0.2694 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0984 / 0.0874 | 0.0898 / 0.0896 | +0.0086 | -0.0022 |
| num_turns | 4.7 / 5 | 6 / 6 | -1.3 | -1 |
| duration_ms | 20733.7 / 20658 | 26446 / 22544 | -5712.3 | -1886 |
| input_tokens | 9.3 / 10 | 11.3 / 12 | -2 | -2 |
| output_tokens | 1529.3 / 1515 | 1760.7 / 1810 | -231.3 | -295 |
| cache_creation_input_tokens | 16973.7 / 14001 | 13297 / 13399 | +3676.7 | +602 |
| cache_read_input_tokens | 151783.3 / 165852 | 189706 / 200003 | -37922.7 | -34151 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 0/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 1/3 | 0/3 |
| beta-live-settings-read | 1/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
