# Eval report: debug-github-workflows

- Timestamp: 20261026T094214Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T094122Z-fe0d1b; started 2026-10-26T09:42:14Z, ended 2026-10-26T09:46:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.07 to 0.07, seven_day 0.58 to 0.58, from 6 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/7 | 5.6 (4.0 to 8.0, 3 judged) | 0.1268 / 0.3803 |
| without_skill | 3 | 0 | 5/7 | 5.9 (4.4 to 9.0, 3 judged) | 0.0688 / 0.2065 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1268 / 0.0977 | 0.0688 / 0.0682 | +0.0579 | +0.0295 |
| num_turns | 8.3 / 8 | 5 / 5 | +3.3 | +3 |
| duration_ms | 28000.7 / 26404 | 20565.3 / 20209 | +7435.3 | +6195 |
| input_tokens | 12 / 12 | 9.3 / 10 | +2.7 | +2 |
| output_tokens | 1654.7 / 1585 | 1077.3 / 1095 | +577.3 | +490 |
| cache_creation_input_tokens | 22221.3 / 14055 | 10404.7 / 10615 | +11816.7 | +3440 |
| cache_read_input_tokens | 211843 / 221398 | 163010 / 175299 | +48833 | +46099 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 2/3 |
| feature-comparison-read | 1/3 | 1/3 |
| main-differs-from-feature | 2/3 | 2/3 |
| merge-existing-fix | 2/3 | 1/3 |
| obsolete-command-diagnosed | 2/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
