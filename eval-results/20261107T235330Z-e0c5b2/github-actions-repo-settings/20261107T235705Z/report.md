# Eval report: github-actions-repo-settings

- Timestamp: 20261107T235705Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T235330Z-e0c5b2; started 2026-11-07T23:57:05Z, ended 2026-11-07T23:58:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.22, judge $0.06, guard $0.00; last agent call $0.09

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/9 | 7.7 (7.7 to 7.7, 1 judged) | 0.1318 / 0.1318 |
| without_skill | 1 | 0 | 3/9 | 7.7 (7.7 to 7.7, 1 judged) | 0.0881 / 0.0881 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1318 / 0.1318 | 0.0881 / 0.0881 | +0.0437 | +0.0437 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 21381 / 21381 | 18404 / 18404 | +2977 | +2977 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1623 / 1623 | 1429 / 1429 | +194 | +194 |
| cache_creation_input_tokens | 24930 / 24930 | 14239 / 14239 | +10691 | +10691 |
| cache_read_input_tokens | 158482 / 158482 | 168306 / 168306 | -9824 | -9824 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/1 | 0/1 |
| alpha-unmanaged-ruleset-facts | 0/1 | 0/1 |
| alpha-engine-does-not-delete | 0/1 | 0/1 |
| beta-overall-match | 0/1 | 0/1 |
| alpha-live-settings-read | 0/1 | 0/1 |
| beta-live-settings-read | 0/1 | 0/1 |
| no-write-attempted | 1/1 | 1/1 |
| config-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
