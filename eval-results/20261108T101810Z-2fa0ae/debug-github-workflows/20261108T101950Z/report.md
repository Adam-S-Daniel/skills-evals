# Eval report: debug-github-workflows

- Timestamp: 20261108T101950Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T101810Z-2fa0ae; started 2026-11-08T10:19:50Z, ended 2026-11-08T10:21:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.75 to 0.75, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 2 call(s); agent $0.60, judge $0.00, guard $0.00; last agent call $0.27

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3368 / 0.3368 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2669 / 0.2669 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3368 / 0.3368 | 0.2669 / 0.2669 | +0.0699 | +0.0699 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 53801 / 53801 | 55363 / 55363 | -1562 | -1562 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3231 / 3231 | 3085 / 3085 | +146 | +146 |
| cache_creation_input_tokens | 27917 / 27917 | 19224 / 19224 | +8693 | +8693 |
| cache_read_input_tokens | 243946 / 243946 | 256535 / 256535 | -12589 | -12589 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
