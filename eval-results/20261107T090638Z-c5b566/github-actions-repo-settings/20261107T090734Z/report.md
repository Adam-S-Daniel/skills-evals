# Eval report: github-actions-repo-settings

- Timestamp: 20261107T090734Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T090638Z-c5b566; started 2026-11-07T09:07:34Z, ended 2026-11-07T09:09:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 6 call(s); agent $0.26, judge $0.11, guard $0.00; last agent call $0.09

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.3/9 | 7.5 (7.0 to 7.7, 3 judged) | 0.0871 / 0.2614 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0871 / 0.0874 |
| num_turns | 5.7 / 5 |
| duration_ms | 25358 / 23252 |
| input_tokens | 10 / 10 |
| output_tokens | 1859.7 / 1944 |
| cache_creation_input_tokens | 12635.7 / 12899 |
| cache_read_input_tokens | 179786.3 / 180220 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| alpha-sha-drift | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 |
| alpha-engine-does-not-delete | 0/3 |
| beta-overall-match | 0/3 |
| alpha-live-settings-read | 0/3 |
| beta-live-settings-read | 0/3 |
| no-write-attempted | 3/3 |
| config-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
