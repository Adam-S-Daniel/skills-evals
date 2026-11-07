# Eval report: review-bash-ci-reliability

- Timestamp: 20261107T121023Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T120839Z-85c7bb; started 2026-11-07T12:10:23Z, ended 2026-11-07T12:12:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.56 over 8 call(s); agent $0.41, judge $0.15, guard $0.00; last agent call $0.09

## Fixture: drift-report-capture (n=2)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | 8.6 (8.6 to 8.6, 2 judged) | 0.1178 / 0.2356 |
| without_skill | 2 | 0 | 7/7 | 8.4 (8.2 to 8.7, 2 judged) | 0.0857 / 0.1715 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1178 / 0.1178 | 0.0857 / 0.0857 | +0.0321 | +0.0321 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 23703 / 23703 | 22060 / 22060 | +1643 | +1643 |
| input_tokens | 13 / 13 | 10 / 10 | +3 | +3 |
| output_tokens | 1838 / 1838 | 1859 / 1859 | -21 | -21 |
| cache_creation_input_tokens | 20152 / 20152 | 12620 / 12620 | +7532 | +7532 |
| cache_read_input_tokens | 187912.5 / 187912.5 | 166367.5 / 166367.5 | +21545 | +21545 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 2/2 | 2/2 |
| workflow-file-present | 2/2 | 2/2 |
| every-drifted-file-reported | 2/2 | 2/2 |
| unowned-template-not-fatal | 2/2 | 2/2 |
| clean-tree-still-passes | 2/2 | 2/2 |
| drift-and-missing-still-fail | 2/2 | 2/2 |
| config-data-untouched | 2/2 | 2/2 |
