# Eval report: platform-release-and-bump

- Timestamp: 20261107T200449Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T200304Z-03749f; started 2026-11-07T20:04:49Z, ended 2026-11-07T20:13:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.67, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.12 over 6 call(s); agent $3.12, judge $0.00, guard $0.00; last agent call $0.42

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/10 | skipped (objective-decided) | 0.5681 / 1.7043 |
| without_skill | 3 | 0 | 7.7/10 | skipped (objective-decided) | 0.4703 / 1.4109 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5681 / 0.5721 | 0.4703 / 0.4356 | +0.0978 | +0.1365 |
| num_turns | 13.3 / 13 | 10.7 / 11 | +2.7 | +2 |
| duration_ms | 76894.3 / 84946 | 84276.3 / 82687 | -7382 | +2259 |
| input_tokens | 26 / 26 | 22 / 22 | +4 | +4 |
| output_tokens | 5672.3 / 5859 | 5554 / 4944 | +118.3 | +915 |
| cache_creation_input_tokens | 41861.3 / 40749 | 32089.3 / 29642 | +9772 | +11107 |
| cache_read_input_tokens | 598229.3 / 604994 | 483728.7 / 497729 | +114500.7 | +107265 |
| tool_errors | 1 / 1 | 0.3 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| canonical-verifier | 0/3 | 0/3 |
| refs-on-release | 3/3 | 3/3 |
| resolved-revision | 3/3 | 3/3 |
| added-caller | 3/3 | 2/3 |
| retired-caller | 0/3 | 0/3 |
| gem-files-present | 3/3 | 3/3 |
| no-pin-comments | 3/3 | 3/3 |
| no-gh-write | 3/3 | 3/3 |
| verifier-digest | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
