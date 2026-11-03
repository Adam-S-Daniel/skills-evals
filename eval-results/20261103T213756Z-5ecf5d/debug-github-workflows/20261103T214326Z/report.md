# Eval report: debug-github-workflows

- Timestamp: 20261103T214326Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261103T213756Z-5ecf5d; started 2026-11-03T21:43:26Z, ended 2026-11-03T21:45:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.56 over 6 call(s); agent $0.33, judge $0.23, guard $0.00; last agent call $0.07

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.7/7 | 8.8 (8.8 to 8.8, 3 judged) | 0.1110 / 0.3329 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1110 / 0.0749 |
| num_turns | 5.7 / 6 |
| duration_ms | 21448.7 / 18712 |
| input_tokens | 10 / 10 |
| output_tokens | 1275.7 / 1301 |
| cache_creation_input_tokens | 20345 / 10875 |
| cache_read_input_tokens | 168215 / 177384 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| failing-log-read-without-writes | 1/3 |
| feature-comparison-read | 1/3 |
| main-differs-from-feature | 3/3 |
| merge-existing-fix | 3/3 |
| obsolete-command-diagnosed | 3/3 |
| repository-files-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
