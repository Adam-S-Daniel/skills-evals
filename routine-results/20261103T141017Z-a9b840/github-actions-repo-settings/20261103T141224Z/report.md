# Eval report: github-actions-repo-settings

- Timestamp: 20261103T141224Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T141017Z-a9b840; started 2026-11-03T14:12:24Z, ended 2026-11-03T14:14:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.47, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.00 over 4 call(s); agent $0.49, judge $1.51, guard $0.00; last agent call $0.20

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/9 | 7.7 (7.7 to 7.7, 1 judged) | 0.2901 / 0.2901 |
| without_skill | 1 | 0 | 5/9 | 3.3 (3.3 to 3.3, 1 judged) | 0.2002 / 0.2002 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2901 / 0.2901 | 0.2002 / 0.2002 | +0.0899 | +0.0899 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 34876 / 34876 | 30320 / 30320 | +4556 | +4556 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 2542 / 2542 | 2035 / 2035 | +507 | +507 |
| cache_creation_input_tokens | 25849 / 25849 | 15639 / 15639 | +10210 | +10210 |
| cache_read_input_tokens | 162302 / 162302 | 171653 / 171653 | -9351 | -9351 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/1 | 0/1 |
| alpha-unmanaged-ruleset-facts | 0/1 | 0/1 |
| alpha-engine-does-not-delete | 0/1 | 0/1 |
| beta-overall-match | 0/1 | 0/1 |
| alpha-live-settings-read | 1/1 | 1/1 |
| beta-live-settings-read | 1/1 | 1/1 |
| no-write-attempted | 1/1 | 1/1 |
| config-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
