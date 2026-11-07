# Eval report: github-actions-repo-settings

- Timestamp: 20261107T045955Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T045823Z-f243da; started 2026-11-07T04:59:55Z, ended 2026-11-07T05:01:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 4 call(s); agent $0.22, judge $0.07, guard $0.00; last agent call $0.10

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/9 | 7.7 (7.7 to 7.7, 1 judged) | 0.1243 / 0.1243 |
| without_skill | 1 | 0 | 5/9 | 8.7 (8.7 to 8.7, 1 judged) | 0.0999 / 0.0999 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1243 / 0.1243 | 0.0999 / 0.0999 | +0.0244 | +0.0244 |
| num_turns | 4 / 4 | 6 / 6 | -2 | -2 |
| duration_ms | 17528 / 17528 | 32895 / 32895 | -15367 | -15367 |
| input_tokens | 8 / 8 | 12 / 12 | -4 | -4 |
| output_tokens | 1192 / 1192 | 1964 / 1964 | -772 | -772 |
| cache_creation_input_tokens | 25021 / 25021 | 14834 / 14834 | +10187 | +10187 |
| cache_read_input_tokens | 122958 / 122958 | 209036 / 209036 | -86078 | -86078 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/1 | 0/1 |
| alpha-unmanaged-ruleset-facts | 0/1 | 0/1 |
| alpha-engine-does-not-delete | 0/1 | 0/1 |
| beta-overall-match | 0/1 | 0/1 |
| alpha-live-settings-read | 0/1 | 1/1 |
| beta-live-settings-read | 0/1 | 1/1 |
| no-write-attempted | 1/1 | 1/1 |
| config-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
