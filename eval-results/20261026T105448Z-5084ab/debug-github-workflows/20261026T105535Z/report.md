# Eval report: debug-github-workflows

- Timestamp: 20261026T105535Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T105448Z-5084ab; started 2026-10-26T10:55:35Z, ended 2026-10-26T11:00:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.13 to 0.13, seven_day 0.6 to 0.6, from 6 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 8.9 (8.8 to 9.0, 3 judged) | 0.1839 / 0.5517 |
| without_skill | 3 | 0 | 5/7 | 8.9 (8.8 to 9.2, 3 judged) | 0.1994 / 0.5982 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1839 / 0.1887 | 0.1994 / 0.2005 | -0.0155 | -0.0118 |
| num_turns | 5.7 / 6 | 6 / 6 | -0.3 | 0 |
| duration_ms | 27663.7 / 27401 | 27210.7 / 27289 | +453 | +112 |
| input_tokens | 11.3 / 12 | 12 / 12 | -0.7 | 0 |
| output_tokens | 1931.3 / 1986 | 2024.3 / 2018 | -93 | -32 |
| cache_creation_input_tokens | 12983.3 / 12908 | 14298 / 14458 | -1314.7 | -1550 |
| cache_read_input_tokens | 206225.3 / 218577 | 221769 / 221687 | -15543.7 | -3110 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 0/3 |
| feature-comparison-read | 0/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
