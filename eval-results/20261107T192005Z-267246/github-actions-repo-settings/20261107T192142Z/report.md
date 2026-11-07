# Eval report: github-actions-repo-settings

- Timestamp: 20261107T192142Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T192005Z-267246; started 2026-11-07T19:21:42Z, ended 2026-11-07T19:27:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.20 over 12 call(s); agent $1.46, judge $0.73, guard $0.00; last agent call $0.19

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/9 | 7.1 (6.3 to 7.7, 3 judged) | 0.2776 / 0.8329 |
| without_skill | 3 | 0 | 4/9 | 7.9 (7.7 to 8.0, 3 judged) | 0.2098 / 0.6294 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2776 / 0.2811 | 0.2098 / 0.1982 | +0.0678 | +0.0829 |
| num_turns | 6.3 / 6 | 5.3 / 5 | +1 | +1 |
| duration_ms | 37369.3 / 35374 | 30949.3 / 31565 | +6420 | +3809 |
| input_tokens | 12 / 12 | 10.7 / 10 | +1.3 | +2 |
| output_tokens | 2708.7 / 2697 | 2501 / 2292 | +207.7 | +405 |
| cache_creation_input_tokens | 22976.3 / 22311 | 15361.7 / 14769 | +7614.7 | +7542 |
| cache_read_input_tokens | 198043.3 / 214571 | 184212.7 / 171200 | +13830.7 | +43371 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 0/3 | 1/3 |
| beta-live-settings-read | 0/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
