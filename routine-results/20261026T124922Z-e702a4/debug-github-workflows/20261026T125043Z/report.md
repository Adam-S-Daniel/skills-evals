# Eval report: debug-github-workflows

- Timestamp: 20261026T125043Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T124922Z-e702a4; started 2026-10-26T12:50:43Z, ended 2026-10-26T12:52:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.41 to 0.42, seven_day 0.66 to 0.66, from 7 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.0751 / 0.2253 |
| without_skill | 3 | 0 | 4.3/7 | skipped (objective-decided) | 0.0684 / 0.2053 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0751 / 0.0731 | 0.0684 / 0.0696 | +0.0067 | +0.0035 |
| num_turns | 5.7 / 6 | 5 / 5 | +0.7 | +1 |
| duration_ms | 18280 / 17025 | 14835.3 / 14694 | +3444.7 | +2331 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1123 / 1074 | 1054.7 / 1007 | +68.3 | +67 |
| cache_creation_input_tokens | 11484.7 / 11288 | 10038.7 / 10435 | +1446 | +853 |
| cache_read_input_tokens | 177793 / 175957 | 175684.3 / 175617 | +2108.7 | +340 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 2/3 | 1/3 |
| feature-comparison-read | 0/3 | 0/3 |
| main-differs-from-feature | 3/3 | 2/3 |
| merge-existing-fix | 3/3 | 2/3 |
| obsolete-command-diagnosed | 3/3 | 2/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
