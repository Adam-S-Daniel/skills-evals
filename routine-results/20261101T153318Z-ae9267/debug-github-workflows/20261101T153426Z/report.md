# Eval report: debug-github-workflows

- Timestamp: 20261101T153426Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T153318Z-ae9267; started 2026-11-01T15:34:26Z, ended 2026-11-01T15:35:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.87 to 0.87, from 2 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.0771 / 0.0771 |
| without_skill | 1 | 0 | 4/7 | skipped (objective-decided) | 0.0758 / 0.0758 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0771 / 0.0771 | 0.0758 / 0.0758 | +0.0013 | +0.0013 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 24395 / 24395 | 36550 / 36550 | -12155 | -12155 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1133 / 1133 | 1227 / 1227 | -94 | -94 |
| cache_creation_input_tokens | 12847 / 12847 | 10496 / 10496 | +2351 | +2351 |
| cache_read_input_tokens | 142398 / 142398 | 214261 / 214261 | -71863 | -71863 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 0/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
