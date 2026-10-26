# Eval report: github-actions-repo-settings

- Timestamp: 20261026T095037Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T094904Z-484023; started 2026-10-26T09:50:37Z, ended 2026-10-26T09:55:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.08 to 0.09, seven_day 0.59 to 0.59, from 7 snapshots

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.3324 / 0.9971 |
| without_skill | 3 | 0 | 5/9 | 9.0 (9.0 to 9.0, 3 judged) | 0.2208 / 0.6624 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3324 / 0.3110 | 0.2208 / 0.2280 | +0.1116 | +0.0829 |
| num_turns | 8 / 8 | 5.7 / 6 | +2.3 | +2 |
| duration_ms | 45348.7 / 44462 | 40506.3 / 38799 | +4842.3 | +5663 |
| input_tokens | 14 / 14 | 11.3 / 12 | +2.7 | +2 |
| output_tokens | 2936 / 2947 | 2749 / 2780 | +187 | +167 |
| cache_creation_input_tokens | 27665.7 / 24882 | 15848.7 / 16357 | +11817 | +8525 |
| cache_read_input_tokens | 261386 / 262300 | 194993 / 207670 | +66393 | +54630 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 1/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 1/3 |
| alpha-live-settings-read | 0/3 | 2/3 |
| beta-live-settings-read | 2/3 | 2/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
