# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T184936Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T184755Z-c752f8; started 2026-11-07T18:49:36Z, ended 2026-11-07T19:02:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.61 to 0.62, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.23 over 6 call(s); agent $3.23, judge $0.00, guard $0.00; last agent call $0.48

## Fixture: nightly-snapshot (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/8 | skipped (objective-decided) | 0.5805 / 1.7414 |
| without_skill | 3 | 0 | 4/8 | skipped (objective-decided) | 0.4963 / 1.4888 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5805 / 0.5321 | 0.4963 / 0.4816 | +0.0842 | +0.0504 |
| num_turns | 11.3 / 10 | 8.7 / 9 | +2.7 | +1 |
| duration_ms | 122133.3 / 120228 | 128129 / 105972 | -5995.7 | +14256 |
| input_tokens | 22.7 / 20 | 18.7 / 18 | +4 | +2 |
| output_tokens | 7466.3 / 7441 | 7805.7 / 7054 | -339.3 | +387 |
| cache_creation_input_tokens | 29285 / 25111 | 25004.3 / 21734 | +4280.7 | +3377 |
| cache_read_input_tokens | 354395.3 / 315604 | 307609 / 296551 | +46786.3 | +19053 |
| tool_errors | 0.7 / 1 | 2 / 2 | -1.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| signing-on-runner | 1/3 | 0/3 |
| no-change-night | 1/3 | 0/3 |
| missing-tool-not-silent | 1/3 | 0/3 |
| new-data-still-committed | 1/3 | 0/3 |
| build-failure-still-fails | 3/3 | 3/3 |
| data-untouched | 3/3 | 3/3 |
