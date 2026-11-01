# Eval report: debug-github-workflows

- Timestamp: 20261101T124205Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T124116Z-3cdc91; started 2026-11-01T12:42:05Z, ended 2026-11-01T12:42:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 2 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/7 | skipped (objective-decided) | 0.2091 / 0.2091 |
| without_skill | 1 | 0 | 3/7 | skipped (objective-decided) | 0.0599 / 0.0599 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2091 / 0.2091 | 0.0599 / 0.0599 | +0.1491 | +0.1491 |
| num_turns | 9 / 9 | 4 / 4 | +5 | +5 |
| duration_ms | 25726 / 25726 | 13023 / 13023 | +12703 | +12703 |
| input_tokens | 16 / 16 | 8 / 8 | +8 | +8 |
| output_tokens | 1757 / 1757 | 797 / 797 | +960 | +960 |
| cache_creation_input_tokens | 41964 / 41964 | 9489 / 9489 | +32475 | +32475 |
| cache_read_input_tokens | 234698 / 234698 | 138546 / 138546 | +96152 | +96152 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 0/1 | 0/1 |
| obsolete-command-diagnosed | 1/1 | 0/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
