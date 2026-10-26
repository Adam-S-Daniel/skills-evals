# Eval report: debug-github-workflows

- Timestamp: 20261026T113337Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T113239Z-7c08c0; started 2026-10-26T11:33:37Z, ended 2026-10-26T11:38:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.18 to 0.18, seven_day 0.61 to 0.61, from 6 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.7/7 | 6.2 (4.8 to 8.0, 3 judged) | 0.0881 / 0.2643 |
| without_skill | 3 | 0 | 7/7 | 8.8 (8.2 to 9.2, 3 judged) | 0.1089 / 0.3267 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0881 / 0.0859 | 0.1089 / 0.0821 | -0.0208 | +0.0039 |
| num_turns | 7.7 / 7 | 6 / 6 | +1.7 | +1 |
| duration_ms | 29529 / 25273 | 32019.7 / 34052 | -2490.7 | -8779 |
| input_tokens | 11.3 / 10 | 10.7 / 10 | +0.7 | 0 |
| output_tokens | 1482.3 / 1375 | 1332 / 1280 | +150.3 | +95 |
| cache_creation_input_tokens | 13064.7 / 12961 | 18915.7 / 11421 | -5851 | +1540 |
| cache_read_input_tokens | 208714.3 / 182651 | 197710.3 / 199069 | +11004 | -16418 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 3/3 |
| feature-comparison-read | 1/3 | 3/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 2/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
