# Eval report: github-actions-repo-settings

- Timestamp: 20261026T130129Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T125953Z-cef9c8; started 2026-10-26T13:01:29Z, ended 2026-10-26T13:04:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0 to 0.01, seven_day 0.66 to 0.66, from 7 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.0948 / 0.2844 |
| without_skill | 3 | 0 | 3.3/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.0860 / 0.2580 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0948 / 0.0829 | 0.0860 / 0.0875 | +0.0088 | -0.0046 |
| num_turns | 4.3 / 4 | 4.7 / 5 | -0.3 | -1 |
| duration_ms | 19815.3 / 18284 | 22948.3 / 22611 | -3133 | -4327 |
| input_tokens | 8.7 / 8 | 9.3 / 10 | -0.7 | -2 |
| output_tokens | 1448.7 / 1449 | 1598.7 / 1638 | -150 | -189 |
| cache_creation_input_tokens | 16616 / 13830 | 13637.3 / 13586 | +2978.7 | +244 |
| cache_read_input_tokens | 138397 / 130951 | 154469.7 / 166647 | -16072.7 | -35696 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 0/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 0/3 | 1/3 |
| beta-live-settings-read | 0/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
