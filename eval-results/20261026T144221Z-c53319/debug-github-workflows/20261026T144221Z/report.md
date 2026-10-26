# Eval report: debug-github-workflows

- Timestamp: 20261026T144221Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144221Z-c53319; started 2026-10-26T14:42:21Z, ended 2026-10-26T14:46:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.55 to 0.58, seven_day 0.78 to 0.78, from 8 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.1836 / 0.5507 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.2066 / 0.6197 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1836 / 0.1807 | 0.2066 / 0.2094 | -0.0230 | -0.0286 |
| num_turns | 6 / 5 | 6.7 / 7 | -0.7 | -2 |
| duration_ms | 35933.7 / 35288 | 41946 / 43838 | -6012.3 | -8550 |
| input_tokens | 11.3 / 10 | 13.3 / 14 | -2 | -4 |
| output_tokens | 2136 / 2070 | 2335.7 / 2355 | -199.7 | -285 |
| cache_creation_input_tokens | 12505.7 / 12745 | 13794.3 / 13689 | -1288.7 | -944 |
| cache_read_input_tokens | 203195.3 / 178828 | 246629.3 / 257892 | -43434 | -79064 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 1/3 |
| feature-comparison-read | 1/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
