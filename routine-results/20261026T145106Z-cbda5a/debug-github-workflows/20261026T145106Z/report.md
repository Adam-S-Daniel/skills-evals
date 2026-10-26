# Eval report: debug-github-workflows

- Timestamp: 20261026T145106Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T145106Z-cbda5a; started 2026-10-26T14:51:06Z, ended 2026-10-26T14:55:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.63 to 0.65, seven_day 0.79 to 0.79, from 7 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 7.8 (5.4 to 9.0, 3 judged) | 0.0845 / 0.2536 |
| without_skill | 3 | 0 | 5.7/7 | 6.6 (5.4 to 9.0, 3 judged) | 0.0801 / 0.2404 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0845 / 0.0807 | 0.0801 / 0.0826 | +0.0044 | -0.0019 |
| num_turns | 7.7 / 7 | 6.3 / 7 | +1.3 | 0 |
| duration_ms | 21927.3 / 18907 | 22077.7 / 22373 | -150.3 | -3466 |
| input_tokens | 11.3 / 10 | 11.3 / 12 | 0 | -2 |
| output_tokens | 1351 / 1309 | 1353.3 / 1355 | -2.3 | -46 |
| cache_creation_input_tokens | 12545.3 / 12567 | 11552 / 11760 | +993.3 | +807 |
| cache_read_input_tokens | 206920 / 181186 | 202399 / 215598 | +4521 | -34412 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 2/3 |
| feature-comparison-read | 0/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
