# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T051449Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T051318Z-ab9157; started 2026-11-07T05:14:49Z, ended 2026-11-07T05:15:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 4 call(s); agent $0.22, judge $0.07, guard $0.00; last agent call $0.08

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/8 | 8.7 (8.7 to 8.7, 1 judged) | 0.1368 / 0.1368 |
| without_skill | 1 | 0 | 7/8 | 4.9 (4.9 to 4.9, 1 judged) | 0.0827 / 0.0827 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1368 / 0.1368 | 0.0827 / 0.0827 | +0.0541 | +0.0541 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 19279 / 19279 | 20478 / 20478 | -1199 | -1199 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2065 / 2065 | 2061 / 2061 | +4 | +4 |
| cache_creation_input_tokens | 24955 / 24955 | 12280 / 12280 | +12675 | +12675 |
| cache_read_input_tokens | 163141 / 163141 | 129902 / 129902 | +33239 | +33239 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| signing-on-runner | 0/1 | 0/1 |
| no-change-night | 0/1 | 1/1 |
| missing-tool-not-silent | 0/1 | 1/1 |
| new-data-still-committed | 0/1 | 1/1 |
| build-failure-still-fails | 1/1 | 1/1 |
| data-untouched | 1/1 | 1/1 |
