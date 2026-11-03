# Eval report: github-actions-repo-settings

- Timestamp: 20261103T194649Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T193007Z-8d2ec8; started 2026-11-03T19:46:49Z, ended 2026-11-03T19:48:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.69, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 4 call(s); agent $0.55, judge $0.45, guard $0.00; last agent call $0.19

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/9 | 8.0 (8.0 to 8.0, 1 judged) | 0.3523 / 0.3523 |
| without_skill | 1 | 0 | 4/9 | 7.7 (7.7 to 7.7, 1 judged) | 0.1950 / 0.1950 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3523 / 0.3523 | 0.1950 / 0.1950 | +0.1573 | +0.1573 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 39956 / 39956 | 30387 / 30387 | +9569 | +9569 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2836 / 2836 | 2089 / 2089 | +747 | +747 |
| cache_creation_input_tokens | 31737 / 31737 | 14847 / 14847 | +16890 | +16890 |
| cache_read_input_tokens | 207934 / 207934 | 171841 / 171841 | +36093 | +36093 |
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
