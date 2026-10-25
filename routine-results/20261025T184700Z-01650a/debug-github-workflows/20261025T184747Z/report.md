# Eval report: debug-github-workflows

- Timestamp: 20261025T184747Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T184700Z-01650a; started 2026-10-25T18:47:47Z, ended 2026-10-25T18:51:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.05 to 0.05, seven_day 0.42 to 0.42, from 6 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.2641 / 0.7923 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1947 / 0.5842 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2641 / 0.1987 | 0.1947 / 0.1930 | +0.0694 | +0.0057 |
| num_turns | 5.7 / 6 | 6 / 6 | -0.3 | 0 |
| duration_ms | 38325.7 / 40256 | 38101.7 / 37203 | +224 | +3053 |
| input_tokens | 11.3 / 12 | 12 / 12 | -0.7 | 0 |
| output_tokens | 2030.7 / 1988 | 2169.7 / 2097 | -139 | -109 |
| cache_creation_input_tokens | 22938.3 / 13931 | 13389 / 13403 | +9549.3 | +528 |
| cache_read_input_tokens | 199074.3 / 192659 | 220292 / 220806 | -21217.7 | -28147 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 0/3 |
| feature-comparison-read | 0/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
