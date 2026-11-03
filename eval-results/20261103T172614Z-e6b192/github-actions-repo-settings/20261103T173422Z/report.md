# Eval report: github-actions-repo-settings

- Timestamp: 20261103T173422Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T172614Z-e6b192; started 2026-11-03T17:34:22Z, ended 2026-11-03T17:35:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.61, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.22, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/9 | 8.0 (8.0 to 8.0, 1 judged) | 0.1380 / 0.1380 |
| without_skill | 1 | 0 | 3/9 | 7.7 (7.7 to 7.7, 1 judged) | 0.0810 / 0.0810 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1380 / 0.1380 | 0.0810 / 0.0810 | +0.0570 | +0.0570 |
| num_turns | 5 / 5 | 4 / 4 | +1 | +1 |
| duration_ms | 28892 / 28892 | 30119 / 30119 | -1227 | -1227 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2026 / 2026 | 1672 / 1672 | +354 | +354 |
| cache_creation_input_tokens | 25416 / 25416 | 12797 / 12797 | +12619 | +12619 |
| cache_read_input_tokens | 160401 / 160401 | 130906 / 130906 | +29495 | +29495 |
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
