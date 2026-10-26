# Eval report: github-actions-repo-settings

- Timestamp: 20261026T101559Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T101508Z-24c7a7; started 2026-10-26T10:15:59Z, ended 2026-10-26T10:20:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.1 to 0.1, seven_day 0.59 to 0.59, from 6 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.3358 / 1.0073 |
| without_skill | 3 | 0 | 4.7/9 | 8.8 (8.3 to 9.0, 3 judged) | 0.2084 / 0.6251 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3358 / 0.3149 | 0.2084 / 0.2019 | +0.1274 | +0.1130 |
| num_turns | 8 / 8 | 5.3 / 5 | +2.7 | +3 |
| duration_ms | 44525 / 43534 | 35012.3 / 33643 | +9512.7 | +9891 |
| input_tokens | 14 / 14 | 10.7 / 10 | +3.3 | +4 |
| output_tokens | 3322 / 3435 | 2581.3 / 2610 | +740.7 | +825 |
| cache_creation_input_tokens | 27209 / 24123 | 15043.7 / 14499 | +12165.3 | +9624 |
| cache_read_input_tokens | 257936.7 / 260842 | 181809 / 168368 | +76127.7 | +92474 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 1/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 2/3 |
| alpha-live-settings-read | 0/3 | 1/3 |
| beta-live-settings-read | 1/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
