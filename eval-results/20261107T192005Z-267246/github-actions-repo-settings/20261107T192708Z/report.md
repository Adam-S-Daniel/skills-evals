# Eval report: github-actions-repo-settings

- Timestamp: 20261107T192708Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T192005Z-267246; started 2026-11-07T19:27:08Z, ended 2026-11-07T19:30:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.87 over 12 call(s); agent $0.66, judge $0.21, guard $0.00; last agent call $0.09

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/9 | 7.7 (7.7 to 7.7, 3 judged) | 0.1080 / 0.3239 |
| without_skill | 3 | 0 | 4/9 | 7.1 (5.7 to 8.0, 3 judged) | 0.1116 / 0.3347 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1080 / 0.0980 | 0.1116 / 0.0979 | -0.0036 | +0.0001 |
| num_turns | 5 / 5 | 6.3 / 6 | -1.3 | -1 |
| duration_ms | 24349 / 25096 | 29617 / 27853 | -5268 | -2757 |
| input_tokens | 10 / 10 | 12.7 / 12 | -2.7 | -2 |
| output_tokens | 1782 / 1856 | 1936 / 1974 | -154 | -118 |
| cache_creation_input_tokens | 18332.3 / 15466 | 17562.7 / 15012 | +769.7 | +454 |
| cache_read_input_tokens | 167973.7 / 170726 | 219431 / 207829 | -51457.3 | -37103 |
| tool_errors | 0 / 0 | 0.7 / 0 | -0.7 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 1/3 | 1/3 |
| beta-live-settings-read | 1/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
