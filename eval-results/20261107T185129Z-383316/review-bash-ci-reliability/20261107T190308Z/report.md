# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T190308Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T185129Z-383316; started 2026-11-07T19:03:08Z, ended 2026-11-07T19:06:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.63, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 6 call(s); agent $0.67, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: test-runner-assertions (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1128 / 0.3383 |
| without_skill | 3 | 0 | 6.3/7 | skipped (objective-decided) | 0.1091 / 0.3274 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1128 / 0.1022 | 0.1091 / 0.1170 | +0.0036 | -0.0148 |
| num_turns | 6 / 6 | 7 / 6 | -1 | 0 |
| duration_ms | 23849 / 24384 | 35309.3 / 37798 | -11460.3 | -13414 |
| input_tokens | 10.7 / 10 | 12.7 / 12 | -2 | -2 |
| output_tokens | 2198 / 2094 | 2893.3 / 3182 | -695.3 | -1088 |
| cache_creation_input_tokens | 19076.7 / 15953 | 14558.3 / 14950 | +4518.3 | +1003 |
| cache_read_input_tokens | 144569.3 / 135780 | 219553.7 / 205679 | -74984.3 | -69899 |
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
