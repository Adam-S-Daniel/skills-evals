# Eval report: platform-release-and-bump

- Timestamp: 20261025T214214Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T213956Z-344c13; started 2026-10-25T21:42:14Z, ended 2026-10-25T21:51:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.2 to 0.22, seven_day 0.46 to 0.46, from 7 snapshots

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/10 | skipped (objective-decided) | 0.5878 / 1.7634 |
| without_skill | 3 | 0 | 7.7/10 | skipped (objective-decided) | 0.5439 / 1.6316 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5878 / 0.5427 | 0.5439 / 0.5450 | +0.0439 | -0.0023 |
| num_turns | 12.3 / 12 | 11.3 / 11 | +1 | +1 |
| duration_ms | 92134.3 / 78021 | 88091 / 89462 | +4043.3 | -11441 |
| input_tokens | 20.7 / 20 | 22 / 22 | -1.3 | -2 |
| output_tokens | 5517.3 / 4809 | 5640.7 / 5614 | -123.3 | -805 |
| cache_creation_input_tokens | 46162 / 42992 | 39989.3 / 40651 | +6172.7 | +2341 |
| cache_read_input_tokens | 525755.3 / 519320 | 542580.3 / 537063 | -16825 | -17743 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

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
