# Eval report: platform-release-and-bump

- Timestamp: 20261107T154904Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T154711Z-34bb2f; started 2026-11-07T15:49:04Z, ended 2026-11-07T15:57:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.51, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.00 over 6 call(s); agent $3.00, judge $0.00, guard $0.00; last agent call $0.45

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8.3/10 | skipped (objective-decided) | 0.5535 / 1.6604 |
| without_skill | 3 | 0 | 8/10 | skipped (objective-decided) | 0.4468 / 1.3403 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5535 / 0.5917 | 0.4468 / 0.4532 | +0.1067 | +0.1385 |
| num_turns | 13.3 / 13 | 11.7 / 12 | +1.7 | +1 |
| duration_ms | 84058.7 / 66411 | 72544.3 / 76111 | +11514.3 | -9700 |
| input_tokens | 25.3 / 26 | 22 / 22 | +3.3 | +4 |
| output_tokens | 5619.3 / 5159 | 4872.7 / 4914 | +746.7 | +245 |
| cache_creation_input_tokens | 40965.3 / 42646 | 30947 / 30390 | +10018.3 | +12256 |
| cache_read_input_tokens | 552653.7 / 548463 | 508188 / 524720 | +44465.7 | +23743 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| canonical-verifier | 1/3 | 0/3 |
| refs-on-release | 2/3 | 3/3 |
| resolved-revision | 3/3 | 3/3 |
| added-caller | 3/3 | 3/3 |
| retired-caller | 1/3 | 0/3 |
| gem-files-present | 3/3 | 3/3 |
| no-pin-comments | 3/3 | 3/3 |
| no-gh-write | 3/3 | 3/3 |
| verifier-digest | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
