# Eval report: platform-release-and-bump

- Timestamp: 20261107T155710Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T154711Z-34bb2f; started 2026-11-07T15:57:10Z, ended 2026-11-07T16:02:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.52, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.09 over 6 call(s); agent $1.09, judge $0.00, guard $0.00; last agent call $0.18

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/10 | skipped (objective-decided) | 0.2029 / 0.6087 |
| without_skill | 3 | 0 | 9.3/10 | skipped (objective-decided) | 0.1590 / 0.4769 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2029 / 0.1905 | 0.1590 / 0.1487 | +0.0439 | +0.0418 |
| num_turns | 11.7 / 12 | 9.7 / 10 | +2 | +2 |
| duration_ms | 50255.7 / 52597 | 48931.7 / 44028 | +1324 | +8569 |
| input_tokens | 21.3 / 22 | 18.7 / 18 | +2.7 | +4 |
| output_tokens | 3298 / 3361 | 2853.3 / 2727 | +444.7 | +634 |
| cache_creation_input_tokens | 31499 / 28882 | 22971.7 / 22764 | +8527.3 | +6118 |
| cache_read_input_tokens | 438972 / 449429 | 385223.3 / 357996 | +53748.7 | +91433 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| canonical-verifier | 3/3 | 2/3 |
| refs-on-release | 3/3 | 3/3 |
| resolved-revision | 3/3 | 3/3 |
| added-caller | 3/3 | 3/3 |
| retired-caller | 3/3 | 2/3 |
| gem-files-present | 3/3 | 3/3 |
| no-pin-comments | 3/3 | 3/3 |
| no-gh-write | 3/3 | 3/3 |
| verifier-digest | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
