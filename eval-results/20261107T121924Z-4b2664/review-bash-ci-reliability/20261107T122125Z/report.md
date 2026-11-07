# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T122125Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T121924Z-4b2664; started 2026-11-07T12:21:25Z, ended 2026-11-07T12:23:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.42, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: test-runner-assertions (n=2)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.1182 / 0.2364 |
| without_skill | 2 | 0 | 6/7 | skipped (objective-decided) | 0.0904 / 0.1808 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1182 / 0.1182 | 0.0904 / 0.0904 | +0.0278 | +0.0278 |
| num_turns | 6.5 / 6.5 | 5 / 5 | +1.5 | +1.5 |
| duration_ms | 24875.5 / 24875.5 | 24820 / 24820 | +55.5 | +55.5 |
| input_tokens | 11 / 11 | 10 / 10 | +1 | +1 |
| output_tokens | 2082 / 2082 | 2075 / 2075 | +7 | +7 |
| cache_creation_input_tokens | 20580 / 20580 | 13218.5 / 13218.5 | +7361.5 | +7361.5 |
| cache_read_input_tokens | 150271.5 / 150271.5 | 167432.5 / 167432.5 | -17161 | -17161 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 2/2 | 2/2 |
| workflow-file-present | 2/2 | 2/2 |
| grep-miss-recorded | 2/2 | 2/2 |
| cmp-difference-recorded | 2/2 | 2/2 |
| crash-recorded | 2/2 | 0/2 |
| green-run-and-mismatch-unchanged | 2/2 | 2/2 |
| code-and-fixtures-untouched | 2/2 | 2/2 |
