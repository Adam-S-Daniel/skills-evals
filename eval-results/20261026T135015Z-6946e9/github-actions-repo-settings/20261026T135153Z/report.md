# Eval report: github-actions-repo-settings

- Timestamp: 20261026T135153Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135015Z-6946e9; started 2026-10-26T13:51:53Z, ended 2026-10-26T13:57:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.14 to 0.2, seven_day 0.69 to 0.7, from 9 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.3174 / 0.9521 |
| without_skill | 3 | 0 | 3.7/9 | 8.9 (8.7 to 9.0, 3 judged) | 0.1945 / 0.5834 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3174 / 0.2901 | 0.1945 / 0.1934 | +0.1229 | +0.0967 |
| num_turns | 7.3 / 8 | 4.7 / 5 | +2.7 | +3 |
| duration_ms | 47391.3 / 47588 | 30552 / 30005 | +16839.3 | +17583 |
| input_tokens | 13.3 / 14 | 9.3 / 10 | +4 | +4 |
| output_tokens | 2991.7 / 2806 | 2283 / 2170 | +708.7 | +636 |
| cache_creation_input_tokens | 26049.7 / 22592 | 14701.7 / 14529 | +11348 | +8063 |
| cache_read_input_tokens | 245338.7 / 255842 | 155705 / 168455 | +89633.7 | +87387 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 1/3 |
| alpha-live-settings-read | 0/3 | 0/3 |
| beta-live-settings-read | 2/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
