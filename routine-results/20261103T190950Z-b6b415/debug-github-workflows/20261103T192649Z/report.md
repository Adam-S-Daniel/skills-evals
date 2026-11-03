# Eval report: debug-github-workflows

- Timestamp: 20261103T192649Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T190950Z-b6b415; started 2026-11-03T19:26:49Z, ended 2026-11-03T19:27:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 2 call(s); agent $0.20, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.1162 / 0.1162 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0838 / 0.0838 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1162 / 0.1162 | 0.0838 / 0.0838 | +0.0324 | +0.0324 |
| num_turns | 4 / 4 | 5 / 5 | -1 | -1 |
| duration_ms | 17723 / 17723 | 21323 / 21323 | -3600 | -3600 |
| input_tokens | 8 / 8 | 8 / 8 | 0 | 0 |
| output_tokens | 1221 / 1221 | 1574 / 1574 | -353 | -353 |
| cache_creation_input_tokens | 22968 / 22968 | 13748 / 13748 | +9220 | +9220 |
| cache_read_input_tokens | 120848 / 120848 | 130819 / 130819 | -9971 | -9971 |
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
