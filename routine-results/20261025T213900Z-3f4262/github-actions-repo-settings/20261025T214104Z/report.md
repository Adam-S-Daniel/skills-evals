# Eval report: github-actions-repo-settings

- Timestamp: 20261025T214104Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T213900Z-3f4262; started 2026-10-25T21:41:04Z, ended 2026-10-25T21:45:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.19 to 0.21, seven_day 0.46 to 0.46, from 8 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/9 | skipped (objective-decided) | 0.3290 / 0.9870 |
| without_skill | 3 | 0 | 3.3/9 | skipped (objective-decided) | 0.1962 / 0.5887 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3290 / 0.3044 | 0.1962 / 0.1947 | +0.1328 | +0.1096 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 45028.7 / 46664 | 33167.3 / 32055 | +11861.3 | +14609 |
| input_tokens | 13.3 / 14 | 10 / 10 | +3.3 | +4 |
| output_tokens | 2898.3 / 2793 | 2273.7 / 2276 | +624.7 | +517 |
| cache_creation_input_tokens | 27693.7 / 25278 | 14636 / 14493 | +13057.7 | +10785 |
| cache_read_input_tokens | 247161 / 251357 | 168119.7 / 168106 | +79041.3 | +83251 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 1/3 | 0/3 |
| alpha-live-settings-read | 0/3 | 0/3 |
| beta-live-settings-read | 3/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
