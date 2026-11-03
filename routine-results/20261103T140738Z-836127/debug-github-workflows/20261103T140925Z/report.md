# Eval report: debug-github-workflows

- Timestamp: 20261103T140925Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T140738Z-836127; started 2026-11-03T14:09:25Z, ended 2026-11-03T14:10:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.46, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.57 over 2 call(s); agent $0.57, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3414 / 0.3414 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.2264 / 0.2264 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3414 / 0.3414 | 0.2264 / 0.2264 | +0.1149 | +0.1149 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 37781 / 37781 | 36960 / 36960 | +821 | +821 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3185 / 3185 | 2702 / 2702 | +483 | +483 |
| cache_creation_input_tokens | 28561 / 28561 | 16269 / 16269 | +12292 | +12292 |
| cache_read_input_tokens | 245585 / 245585 | 210983 / 210983 | +34602 | +34602 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
