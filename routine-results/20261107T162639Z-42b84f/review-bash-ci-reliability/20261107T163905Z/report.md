# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T163905Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T162639Z-42b84f; started 2026-11-07T16:39:05Z, ended 2026-11-07T16:42:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.55, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 6 call(s); agent $0.63, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: test-runner-assertions (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1090 / 0.3269 |
| without_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.1015 / 0.3044 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1090 / 0.0983 | 0.1015 / 0.1056 | +0.0075 | -0.0074 |
| num_turns | 6 / 6 | 6.7 / 7 | -0.7 | -1 |
| duration_ms | 20104.7 / 20275 | 47484.7 / 44005 | -27380 | -23730 |
| input_tokens | 10 / 10 | 13.3 / 14 | -3.3 | -4 |
| output_tokens | 1976 / 1934 | 2308.7 / 2389 | -332.7 | -455 |
| cache_creation_input_tokens | 18987.3 / 15641 | 13820.7 / 13849 | +5166.7 | +1792 |
| cache_read_input_tokens | 132286.7 / 135527 | 230613.3 / 241699 | -98326.7 | -106172 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| grep-miss-recorded | 3/3 | 3/3 |
| cmp-difference-recorded | 3/3 | 3/3 |
| crash-recorded | 3/3 | 1/3 |
| green-run-and-mismatch-unchanged | 3/3 | 3/3 |
| code-and-fixtures-untouched | 3/3 | 3/3 |
