# Eval report: github-actions-repo-settings

- Timestamp: 20261103T153137Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T152845Z-33512a; started 2026-11-03T15:31:37Z, ended 2026-11-03T15:33:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.51, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1365 / 0.1365 |
| without_skill | 1 | 0 | 3/9 | skipped (objective-decided) | 0.0949 / 0.0949 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1365 / 0.1365 | 0.0949 / 0.0949 | +0.0416 | +0.0416 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 46666 / 46666 | 26153 / 26153 | +20513 | +20513 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1691 / 1691 | 1933 / 1933 | -242 | -242 |
| cache_creation_input_tokens | 25829 / 25829 | 14612 / 14612 | +11217 | +11217 |
| cache_read_input_tokens | 162328 / 162328 | 170605 / 170605 | -8277 | -8277 |
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
