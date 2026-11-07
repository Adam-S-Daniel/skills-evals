# Eval report: github-actions-repo-settings

- Timestamp: 20261107T132850Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T132749Z-646417; started 2026-11-07T13:28:50Z, ended 2026-11-07T13:31:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.56, judge $0.35, guard $0.00; last agent call $0.18

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/9 | 7.4 (6.6 to 8.0, 3 judged) | 0.1878 / 0.5635 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1878 / 0.1858 |
| num_turns | 5.3 / 5 |
| duration_ms | 32481 / 30994 |
| input_tokens | 10.7 / 10 |
| output_tokens | 2159.3 / 2133 |
| cache_creation_input_tokens | 13204.3 / 13062 |
| cache_read_input_tokens | 194820.3 / 182356 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| alpha-sha-drift | 2/3 |
| alpha-unmanaged-ruleset-facts | 0/3 |
| alpha-engine-does-not-delete | 0/3 |
| beta-overall-match | 1/3 |
| alpha-live-settings-read | 0/3 |
| beta-live-settings-read | 0/3 |
| no-write-attempted | 3/3 |
| config-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
