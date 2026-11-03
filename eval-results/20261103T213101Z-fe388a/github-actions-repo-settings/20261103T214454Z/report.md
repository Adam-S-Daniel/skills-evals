# Eval report: github-actions-repo-settings

- Timestamp: 20261103T214454Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T213101Z-fe388a; started 2026-11-03T21:44:54Z, ended 2026-11-03T21:47:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 4 call(s); agent $0.56, judge $0.45, guard $0.00; last agent call $0.22

## Fixture: drift-diagnosis (n=1)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/9 | 7.3 (7.3 to 7.3, 1 judged) | 0.3464 / 0.3464 |
| without_skill | 1 | 0 | 5/9 | 8.0 (8.0 to 8.0, 1 judged) | 0.2157 / 0.2157 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3464 / 0.3464 | 0.2157 / 0.2157 | +0.1307 | +0.1307 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 39755 / 39755 | 45693 / 45693 | -5938 | -5938 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2569 / 2569 | 2558 / 2558 | +11 | +11 |
| cache_creation_input_tokens | 31672 / 31672 | 16262 / 16262 | +15410 | +15410 |
| cache_read_input_tokens | 208012 / 208012 | 172029 / 172029 | +35983 | +35983 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 1/1 | 0/1 |
| alpha-unmanaged-ruleset-facts | 0/1 | 0/1 |
| alpha-engine-does-not-delete | 0/1 | 0/1 |
| beta-overall-match | 0/1 | 0/1 |
| alpha-live-settings-read | 0/1 | 1/1 |
| beta-live-settings-read | 0/1 | 1/1 |
| no-write-attempted | 1/1 | 1/1 |
| config-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
