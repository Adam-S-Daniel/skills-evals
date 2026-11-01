# Eval report: debug-github-workflows

- Timestamp: 20261101T134318Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T134218Z-530999; started 2026-11-01T13:43:18Z, ended 2026-11-01T13:44:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 4 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0986 / 0.0986 |
| without_skill | 1 | 0 | 5/7 | 8.6 (8.6 to 8.6, 1 judged) | 0.0658 / 0.0658 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0986 / 0.0986 | 0.0658 / 0.0658 | +0.0328 | +0.0328 |
| num_turns | 9 / 9 | 4 / 4 | +5 | +5 |
| duration_ms | 22300 / 22300 | 11937 / 11937 | +10363 | +10363 |
| input_tokens | 16 / 16 | 8 / 8 | +8 | +8 |
| output_tokens | 1696 / 1696 | 974 / 974 | +722 | +722 |
| cache_creation_input_tokens | 13802 / 13802 | 10514 / 10514 | +3288 | +3288 |
| cache_read_input_tokens | 262437 / 262437 | 138571 / 138571 | +123866 | +123866 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
