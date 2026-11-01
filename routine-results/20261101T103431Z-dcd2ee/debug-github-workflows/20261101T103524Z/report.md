# Eval report: debug-github-workflows

- Timestamp: 20261101T103524Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T103431Z-dcd2ee; started 2026-11-01T10:35:24Z, ended 2026-11-01T10:36:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 2 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2062 / 0.2062 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0682 / 0.0682 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2062 / 0.2062 | 0.0682 / 0.0682 | +0.1381 | +0.1381 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 19829 / 19829 | 17970 / 17970 | +1859 | +1859 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1501 / 1501 | 1068 / 1068 | +433 | +433 |
| cache_creation_input_tokens | 43833 / 43833 | 9930 / 9930 | +33903 | +33903 |
| cache_read_input_tokens | 157442 / 157442 | 176165 / 176165 | -18723 | -18723 |
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
