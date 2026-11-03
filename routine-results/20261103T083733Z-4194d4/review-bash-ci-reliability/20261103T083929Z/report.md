# Eval report: review-bash-ci-reliability

- Timestamp: 20261103T083929Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T083733Z-4194d4; started 2026-11-03T08:39:29Z, ended 2026-11-03T08:43:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.10 over 2 call(s); agent $1.10, judge $0.00, guard $0.00; last agent call $0.47

## Fixture: drift-report-capture (n=1)

- Prompt: Review the shell in this repo's CI for reliability problems and fix what you find.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.6242 / 0.6242 |
| without_skill | 1 | 0 | 3/7 | skipped (objective-decided) | 0.4744 / 0.4744 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6242 / 0.6242 | 0.4744 / 0.4744 | +0.1497 | +0.1497 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 111149 / 111149 | 93112 / 93112 | +18037 | +18037 |
| input_tokens | 14 / 14 | 18 / 18 | -4 | -4 |
| output_tokens | 6876 / 6876 | 6434 / 6434 | +442 | +442 |
| cache_creation_input_tokens | 35841 / 35841 | 21494 / 21494 | +14347 | +14347 |
| cache_read_input_tokens | 171106 / 171106 | 295508 / 295508 | -124402 | -124402 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflow-yaml-parses | 1/1 | 1/1 |
| workflow-file-present | 1/1 | 1/1 |
| every-drifted-file-reported | 1/1 | 0/1 |
| unowned-template-not-fatal | 1/1 | 0/1 |
| clean-tree-still-passes | 1/1 | 0/1 |
| drift-and-missing-still-fail | 1/1 | 0/1 |
| config-data-untouched | 1/1 | 1/1 |
