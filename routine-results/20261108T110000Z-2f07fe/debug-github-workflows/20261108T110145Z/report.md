# Eval report: debug-github-workflows

- Timestamp: 20261108T110145Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T110000Z-2f07fe; started 2026-11-08T11:01:45Z, ended 2026-11-08T11:03:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.59 over 2 call(s); agent $0.59, judge $0.00, guard $0.00; last agent call $0.24

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.3576 / 0.3576 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.2364 / 0.2364 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3576 / 0.3576 | 0.2364 / 0.2364 | +0.1212 | +0.1212 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 47452 / 47452 | 37600 / 37600 | +9852 | +9852 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 2786 / 2786 | 2779 / 2779 | +7 | +7 |
| cache_creation_input_tokens | 31269 / 31269 | 17229 / 17229 | +14040 | +14040 |
| cache_read_input_tokens | 258198 / 258198 | 214702 / 214702 | +43496 | +43496 |
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
