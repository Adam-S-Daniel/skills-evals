# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T162818Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T162639Z-42b84f; started 2026-11-07T16:28:18Z, ended 2026-11-07T16:39:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.55, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.84 over 6 call(s); agent $2.84, judge $0.00, guard $0.00; last agent call $0.49

## Fixture: test-runner-assertions (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/7 | skipped (objective-decided) | 0.5217 / 1.5650 |
| without_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.4266 / 1.2799 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5217 / 0.6150 | 0.4266 / 0.4060 | +0.0950 | +0.2091 |
| num_turns | 10 / 10 | 6.7 / 7 | +3.3 | +3 |
| duration_ms | 104860.3 / 114566 | 105766 / 102242 | -905.7 | +12324 |
| input_tokens | 21.3 / 20 | 15.3 / 16 | +6 | +4 |
| output_tokens | 5876.3 / 6386 | 6733.3 / 7242 | -857 | -856 |
| cache_creation_input_tokens | 27857.7 / 28237 | 21490 / 22266 | +6367.7 | +5971 |
| cache_read_input_tokens | 350344.3 / 361776 | 243841.7 / 259480 | +106502.7 | +102296 |
| tool_errors | 1.3 / 1 | 0.3 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| grep-miss-recorded | 3/3 | 3/3 |
| cmp-difference-recorded | 3/3 | 3/3 |
| crash-recorded | 3/3 | 3/3 |
| green-run-and-mismatch-unchanged | 3/3 | 3/3 |
| code-and-fixtures-untouched | 2/3 | 1/3 |
