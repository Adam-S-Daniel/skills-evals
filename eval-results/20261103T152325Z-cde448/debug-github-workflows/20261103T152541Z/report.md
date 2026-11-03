# Eval report: debug-github-workflows

- Timestamp: 20261103T152541Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T152325Z-cde448; started 2026-11-03T15:25:41Z, ended 2026-11-03T15:26:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.51, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 2 call(s); agent $0.20, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1163 / 0.1163 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0870 / 0.0870 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1163 / 0.1163 | 0.0870 / 0.0870 | +0.0292 | +0.0292 |
| num_turns | 4 / 4 | 6 / 6 | -2 | -2 |
| duration_ms | 20543 / 20543 | 18783 / 18783 | +1760 | +1760 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 1290 / 1290 | 1594 / 1594 | -304 | -304 |
| cache_creation_input_tokens | 22830 / 22830 | 13592 / 13592 | +9238 | +9238 |
| cache_read_input_tokens | 120559 / 120559 | 167168 / 167168 | -46609 | -46609 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 1/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
