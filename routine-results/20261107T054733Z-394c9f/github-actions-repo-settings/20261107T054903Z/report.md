# Eval report: github-actions-repo-settings

- Timestamp: 20261107T054903Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T054733Z-394c9f; started 2026-11-07T05:49:03Z, ended 2026-11-07T05:49:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1354 / 0.1354 |
| without_skill | 1 | 0 | 3/9 | skipped (objective-decided) | 0.1024 / 0.1024 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1354 / 0.1354 | 0.1024 / 0.1024 | +0.0329 | +0.0329 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 22016 / 22016 | 22110 / 22110 | -94 | -94 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1771 / 1771 | 2263 / 2263 | -492 | -492 |
| cache_creation_input_tokens | 25372 / 25372 | 15677 / 15677 | +9695 | +9695 |
| cache_read_input_tokens | 161339 / 161339 | 170754 / 170754 | -9415 | -9415 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/1 | 0/1 |
| alpha-unmanaged-ruleset-facts | 0/1 | 0/1 |
| alpha-engine-does-not-delete | 0/1 | 0/1 |
| beta-overall-match | 0/1 | 0/1 |
| alpha-live-settings-read | 1/1 | 0/1 |
| beta-live-settings-read | 1/1 | 0/1 |
| no-write-attempted | 1/1 | 1/1 |
| config-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
