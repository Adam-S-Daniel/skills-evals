# Eval report: debug-github-workflows

- Timestamp: 20261108T183507Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T183154Z-4113c5; started 2026-11-08T18:35:07Z, ended 2026-11-08T18:36:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 2 call(s); agent $0.53, judge $0.00, guard $0.00; last agent call $0.20

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3355 / 0.3355 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1974 / 0.1974 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3355 / 0.3355 | 0.1974 / 0.1974 | +0.1381 | +0.1381 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 57279 / 57279 | 47521 / 47521 | +9758 | +9758 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 3302 / 3302 | 2948 / 2948 | +354 | +354 |
| cache_creation_input_tokens | 43053 / 43053 | 17460 / 17460 | +25593 | +25593 |
| cache_read_input_tokens | 270639 / 270639 | 255585 / 255585 | +15054 | +15054 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 1/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
