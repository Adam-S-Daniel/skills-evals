# Eval report: debug-github-workflows

- Timestamp: 20261108T110315Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T110000Z-2f07fe; started 2026-11-08T11:03:15Z, ended 2026-11-08T11:04:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1249 / 0.1249 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0928 / 0.0928 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1249 / 0.1249 | 0.0928 / 0.0928 | +0.0320 | +0.0320 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 20046 / 20046 | 27214 / 27214 | -7168 | -7168 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1502 / 1502 | 1697 / 1697 | -195 | -195 |
| cache_creation_input_tokens | 23509 / 23509 | 13813 / 13813 | +9696 | +9696 |
| cache_read_input_tokens | 157755 / 157755 | 205863 / 205863 | -48108 | -48108 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 0/1 |
| feature-comparison-read | 1/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
