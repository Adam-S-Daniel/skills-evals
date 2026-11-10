# Eval report: platform-release-and-bump

- Timestamp: 20261110T113735Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T113606Z-3e6df9; started 2026-11-10T11:37:35Z, ended 2026-11-10T11:40:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.21 to 0.21, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.25 over 6 call(s); agent $0.87, judge $0.38, guard $0.00; last agent call $0.21

## Fixture: platform-release-and-bump (n=3)

- Prompt: Bump this consumer to platform v0.1.104.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.3/10 | 5.2 (5.1 to 5.3, 3 judged) | 0.2900 / 0.8699 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2900 / 0.2551 |
| num_turns | 7.7 / 8 |
| duration_ms | 40166.3 / 42821 |
| input_tokens | 15.3 / 16 |
| output_tokens | 2847 / 2926 |
| cache_creation_input_tokens | 34040.7 / 25830 |
| cache_read_input_tokens | 313811.7 / 321017 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| canonical-verifier | 0/3 |
| refs-on-release | 3/3 |
| resolved-revision | 3/3 |
| added-caller | 1/3 |
| retired-caller | 0/3 |
| gem-files-present | 3/3 |
| no-pin-comments | 3/3 |
| no-gh-write | 3/3 |
| verifier-digest | 3/3 |
| instrument-unchanged | 3/3 |
