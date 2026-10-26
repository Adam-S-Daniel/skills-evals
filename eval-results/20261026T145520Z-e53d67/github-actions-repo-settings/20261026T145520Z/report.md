# Eval report: github-actions-repo-settings

- Timestamp: 20261026T145520Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145520Z-e53d67; started 2026-10-26T14:55:20Z, ended 2026-10-26T14:59:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.67 to 0.69, seven_day 0.8 to 0.8, from 6 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.3/9 | 8.7 (8.0 to 9.0, 3 judged) | 0.1068 / 0.3203 |
| without_skill | 3 | 0 | 4.3/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.0912 / 0.2735 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1068 / 0.1009 | 0.0912 / 0.0900 | +0.0156 | +0.0109 |
| num_turns | 4.7 / 5 | 4.7 / 5 | 0 | 0 |
| duration_ms | 21362 / 22769 | 22370.7 / 20555 | -1008.7 | +2214 |
| input_tokens | 9.3 / 10 | 9.3 / 10 | 0 | 0 |
| output_tokens | 1833 / 1847 | 1832 / 1712 | +1 | +135 |
| cache_creation_input_tokens | 18268 / 15847 | 14298.7 / 14008 | +3969.3 | +1839 |
| cache_read_input_tokens | 153338.7 / 158225 | 156460.7 / 167925 | -3122 | -9700 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 0/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 1/3 | 2/3 |
| beta-live-settings-read | 0/3 | 2/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
