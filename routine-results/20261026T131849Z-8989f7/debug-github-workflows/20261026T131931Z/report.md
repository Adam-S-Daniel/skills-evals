# Eval report: debug-github-workflows

- Timestamp: 20261026T131931Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T131849Z-8989f7; started 2026-10-26T13:19:31Z, ended 2026-10-26T13:22:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.05 to 0.06, seven_day 0.67 to 0.67, from 7 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.1957 / 0.5870 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1939 / 0.5817 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1957 / 0.1886 | 0.1939 / 0.1888 | +0.0018 | -0.0002 |
| num_turns | 5.7 / 5 | 6 / 6 | -0.3 | -1 |
| duration_ms | 29577 / 28385 | 28272.3 / 27406 | +1304.7 | +979 |
| input_tokens | 11.3 / 10 | 12 / 12 | -0.7 | -2 |
| output_tokens | 2108 / 2116 | 2046.7 / 2045 | +61.3 | +71 |
| cache_creation_input_tokens | 13959.7 / 13758 | 13549 / 12980 | +410.7 | +778 |
| cache_read_input_tokens | 208250.7 / 180360 | 221926.3 / 219505 | -13675.7 | -39145 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 0/3 |
| feature-comparison-read | 1/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
