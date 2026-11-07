# Eval report: github-actions-repo-settings

- Timestamp: 20261107T235524Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T235330Z-e0c5b2; started 2026-11-07T23:55:24Z, ended 2026-11-07T23:57:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.78 over 4 call(s); agent $0.54, judge $0.24, guard $0.00; last agent call $0.19

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/9 | 8.7 (8.7 to 8.7, 1 judged) | 0.3490 / 0.3490 |
| without_skill | 1 | 0 | 4/9 | 6.7 (6.7 to 6.7, 1 judged) | 0.1910 / 0.1910 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3490 / 0.3490 | 0.1910 / 0.1910 | +0.1580 | +0.1580 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 31239 / 31239 | 31587 / 31587 | -348 | -348 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2656 / 2656 | 2072 / 2072 | +584 | +584 |
| cache_creation_input_tokens | 31778 / 31778 | 14400 / 14400 | +17378 | +17378 |
| cache_read_input_tokens | 207946 / 207946 | 171678 / 171678 | +36268 | +36268 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/1 | 1/1 |
| alpha-unmanaged-ruleset-facts | 0/1 | 0/1 |
| alpha-engine-does-not-delete | 0/1 | 0/1 |
| beta-overall-match | 0/1 | 0/1 |
| alpha-live-settings-read | 0/1 | 0/1 |
| beta-live-settings-read | 0/1 | 0/1 |
| no-write-attempted | 1/1 | 1/1 |
| config-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
