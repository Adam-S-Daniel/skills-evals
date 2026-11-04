# Eval report: review-bash-ci-reliability

- Timestamp: 20261104T042933Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T042558Z-1216e7; started 2026-11-04T04:29:33Z, ended 2026-11-04T04:30:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.92 to 0.92, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.22, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.1320 / 0.1320 |
| without_skill | 1 | 0 | 7/7 | 9.2 (9.2 to 9.2, 1 judged) | 0.0914 / 0.0914 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1320 / 0.1320 | 0.0914 / 0.0914 | +0.0406 | +0.0406 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 18332 / 18332 | 21245 / 21245 | -2913 | -2913 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 1656 / 1656 | 2035 / 2035 | -379 | -379 |
| cache_creation_input_tokens | 24806 / 24806 | 12679 / 12679 | +12127 | +12127 |
| cache_read_input_tokens | 162023 / 162023 | 203187 / 203187 | -41164 | -41164 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 1/1 |
| unowned-template-not-fatal | 1/1 | 1/1 |
| clean-tree-still-passes | 1/1 | 1/1 |
| drift-and-missing-still-fail | 1/1 | 1/1 |
| config-data-untouched | 1/1 | 1/1 |
