# Eval report: github-actions-repo-settings

- Timestamp: 20261107T115918Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T115747Z-8968fd; started 2026-11-07T11:59:18Z, ended 2026-11-07T12:02:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.61 over 8 call(s); agent $0.47, judge $0.14, guard $0.00; last agent call $0.10

## Fixture: drift-diagnosis (n=2)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 3/9 | 7.8 (7.7 to 8.0, 2 judged) | 0.1384 / 0.2768 |
| without_skill | 2 | 0 | 3/9 | 7.7 (7.4 to 8.0, 2 judged) | 0.0958 / 0.1915 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1384 / 0.1384 | 0.0958 / 0.0958 | +0.0426 | +0.0426 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 30704.5 / 30704.5 | 31192 / 31192 | -487.5 | -487.5 |
| input_tokens | 13 / 13 | 12 / 12 | +1 | +1 |
| output_tokens | 1940.5 / 1940.5 | 1908 / 1908 | +32.5 | +32.5 |
| cache_creation_input_tokens | 24307.5 / 24307.5 | 14035.5 / 14035.5 | +10272 | +10272 |
| cache_read_input_tokens | 217233.5 / 217233.5 | 205279 / 205279 | +11954.5 | +11954.5 |
| tool_errors | 1.5 / 1.5 | 0.5 / 0.5 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/2 | 0/2 |
| alpha-unmanaged-ruleset-facts | 0/2 | 0/2 |
| alpha-engine-does-not-delete | 0/2 | 0/2 |
| beta-overall-match | 0/2 | 0/2 |
| alpha-live-settings-read | 0/2 | 0/2 |
| beta-live-settings-read | 0/2 | 0/2 |
| no-write-attempted | 2/2 | 2/2 |
| config-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
