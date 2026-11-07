# Eval report: platform-release-and-bump

- Timestamp: 20261107T113416Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T113242Z-2e55d8; started 2026-11-07T11:34:16Z, ended 2026-11-07T11:37:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.77 over 4 call(s); agent $0.77, judge $0.00, guard $0.00; last agent call $0.18

## Fixture: platform-release-and-bump (n=2)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 10/10 | skipped (objective-decided) | 0.2249 / 0.4498 |
| without_skill | 2 | 0 | 8.5/10 | skipped (objective-decided) | 0.1579 / 0.3158 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2249 / 0.2249 | 0.1579 / 0.1579 | +0.0670 | +0.0670 |
| num_turns | 13 / 13 | 8.5 / 8.5 | +4.5 | +4.5 |
| duration_ms | 48066.5 / 48066.5 | 38827.5 / 38827.5 | +9239 | +9239 |
| input_tokens | 24 / 24 | 17 / 17 | +7 | +7 |
| output_tokens | 3823.5 / 3823.5 | 2936.5 / 2936.5 | +887 | +887 |
| cache_creation_input_tokens | 34014.5 / 34014.5 | 23409.5 / 23409.5 | +10605 | +10605 |
| cache_read_input_tokens | 505604.5 / 505604.5 | 348605 / 348605 | +156999.5 | +156999.5 |
| tool_errors | 0.5 / 0.5 | 0.5 / 0.5 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| canonical-verifier | 2/2 | 1/2 |
| refs-on-release | 2/2 | 2/2 |
| resolved-revision | 2/2 | 2/2 |
| added-caller | 2/2 | 1/2 |
| retired-caller | 2/2 | 1/2 |
| gem-files-present | 2/2 | 2/2 |
| no-pin-comments | 2/2 | 2/2 |
| no-gh-write | 2/2 | 2/2 |
| verifier-digest | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
