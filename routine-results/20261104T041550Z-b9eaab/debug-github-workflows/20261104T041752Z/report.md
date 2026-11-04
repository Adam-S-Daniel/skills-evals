# Eval report: debug-github-workflows

- Timestamp: 20261104T041752Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T041550Z-b9eaab; started 2026-11-04T04:17:52Z, ended 2026-11-04T04:19:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.91 to 0.91, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.22, judge $0.16, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1245 / 0.1245 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0912 / 0.0912 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1245 / 0.1245 | 0.0912 / 0.0912 | +0.0333 | +0.0333 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 16627 / 16627 | 20630 / 20630 | -4003 | -4003 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1375 / 1375 | 1688 / 1688 | -313 | -313 |
| cache_creation_input_tokens | 23722 / 23722 | 13428 / 13428 | +10294 | +10294 |
| cache_read_input_tokens | 157962 / 157962 | 205742 / 205742 | -47780 | -47780 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 1/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
