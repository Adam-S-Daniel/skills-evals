# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T190716Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T185506Z-4b6968; started 2026-11-07T19:07:16Z, ended 2026-11-07T19:11:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.63, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.88 over 12 call(s); agent $0.65, judge $0.23, guard $0.00; last agent call $0.10

## Fixture: drift-report-capture (n=3)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | 8.4 (8.1 to 9.0, 3 judged) | 0.1157 / 0.3471 |
| without_skill | 3 | 0 | 7/7 | 8.1 (7.6 to 8.6, 3 judged) | 0.1003 / 0.3009 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1157 / 0.1094 | 0.1003 / 0.1020 | +0.0154 | +0.0073 |
| num_turns | 8.3 / 9 | 5.7 / 6 | +2.7 | +3 |
| duration_ms | 24560.3 / 27277 | 29234.3 / 30827 | -4674 | -3550 |
| input_tokens | 14.7 / 16 | 11.3 / 12 | +3.3 | +4 |
| output_tokens | 2012.7 / 2300 | 2831.3 / 2850 | -818.7 | -550 |
| cache_creation_input_tokens | 18355 / 15348 | 13221.3 / 13314 | +5133.7 | +2034 |
| cache_read_input_tokens | 221084.3 / 242279 | 190673 / 202579 | +30411.3 | +39700 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 3/3 | 3/3 |
| workflow-file-present | 3/3 | 3/3 |
| every-drifted-file-reported | 3/3 | 3/3 |
| unowned-template-not-fatal | 3/3 | 3/3 |
| clean-tree-still-passes | 3/3 | 3/3 |
| drift-and-missing-still-fail | 3/3 | 3/3 |
| config-data-untouched | 3/3 | 3/3 |
