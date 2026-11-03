# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T093512Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T093314Z-c802e1; started 2026-11-03T09:35:12Z, ended 2026-11-03T09:40:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.65 over 4 call(s); agent $1.17, judge $0.48, guard $0.00; last agent call $0.47

## Fixture: nightly-snapshot (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/8 | 8.6 (8.6 to 8.6, 1 judged) | 0.6995 / 0.6995 |
| without_skill | 1 | 0 | 4/8 | 4.7 (4.7 to 4.7, 1 judged) | 0.4735 / 0.4735 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6995 / 0.6995 | 0.4735 / 0.4735 | +0.2260 | +0.2260 |
| num_turns | 12 / 12 | 7 / 7 | +5 | +5 |
| duration_ms | 169782 / 169782 | 112986 / 112986 | +56796 | +56796 |
| input_tokens | 26 / 26 | 16 / 16 | +10 | +10 |
| output_tokens | 9952 / 9952 | 6424 / 6424 | +3528 | +3528 |
| cache_creation_input_tokens | 38271 / 38271 | 21939 / 21939 | +16332 | +16332 |
| cache_read_input_tokens | 441836 / 441836 | 252443 / 252443 | +189393 | +189393 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| signing-on-runner | 0/1 | 0/1 |
| no-change-night | 0/1 | 0/1 |
| missing-tool-not-silent | 0/1 | 0/1 |
| new-data-still-committed | 0/1 | 0/1 |
| build-failure-still-fails | 1/1 | 1/1 |
| data-untouched | 1/1 | 1/1 |
