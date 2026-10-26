# Eval report: debug-github-workflows

- Timestamp: 20261026T122225Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T122117Z-b6afa8; started 2026-10-26T12:22:25Z, ended 2026-10-26T12:28:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.28 to 0.29, seven_day 0.63 to 0.63, from 7 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/7 | 7.6 (5.0 to 9.0, 3 judged) | 0.1921 / 0.5764 |
| without_skill | 3 | 0 | 6.3/7 | 8.8 (8.8 to 8.8, 3 judged) | 0.1936 / 0.5807 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1921 / 0.1878 | 0.1936 / 0.1922 | -0.0014 | -0.0044 |
| num_turns | 5.7 / 5 | 6.3 / 6 | -0.7 | -1 |
| duration_ms | 27699.3 / 25098 | 29552.7 / 30247 | -1853.3 | -5149 |
| input_tokens | 11.3 / 10 | 11.3 / 12 | 0 | -2 |
| output_tokens | 2005 / 1977 | 2098.7 / 2163 | -93.7 | -186 |
| cache_creation_input_tokens | 13792.3 / 13965 | 13745.7 / 13767 | +46.7 | +198 |
| cache_read_input_tokens | 207620.7 / 181997 | 207272.7 / 221783 | +348 | -39786 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 2/3 |
| feature-comparison-read | 2/3 | 2/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
