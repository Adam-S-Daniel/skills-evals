# Eval report: platform-release-and-bump

- Timestamp: 20261107T132142Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T132040Z-b53b8e; started 2026-11-07T13:21:42Z, ended 2026-11-07T13:24:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.68 over 6 call(s); agent $0.43, judge $0.25, guard $0.00; last agent call $0.14

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.7/10 | 6.0 (5.2 to 7.5, 3 judged) | 0.1437 / 0.4310 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1437 / 0.1374 |
| num_turns | 9.3 / 10 |
| duration_ms | 48144 / 52474 |
| input_tokens | 17.3 / 18 |
| output_tokens | 3049.3 / 2674 |
| cache_creation_input_tokens | 19611.3 / 17576 |
| cache_read_input_tokens | 346999.3 / 371368 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| canonical-verifier | 1/3 |
| refs-on-release | 3/3 |
| resolved-revision | 3/3 |
| added-caller | 1/3 |
| retired-caller | 1/3 |
| gem-files-present | 3/3 |
| no-pin-comments | 3/3 |
| no-gh-write | 3/3 |
| verifier-digest | 3/3 |
| instrument-unchanged | 2/3 |
