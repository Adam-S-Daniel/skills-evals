# Eval report: debug-github-workflows

- Timestamp: 20261026T135247Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135153Z-626182; started 2026-10-26T13:52:47Z, ended 2026-10-26T13:55:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.15 to 0.19, seven_day 0.69 to 0.69, from 9 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.0962 / 0.2887 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1045 / 0.3136 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0962 / 0.0980 | 0.1045 / 0.0728 | -0.0083 | +0.0253 |
| num_turns | 9 / 9 | 5.3 / 5 | +3.7 | +4 |
| duration_ms | 21302.3 / 21959 | 18087.3 / 18007 | +3215 | +3952 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 1606.7 / 1695 | 1261 / 1279 | +345.7 | +416 |
| cache_creation_input_tokens | 13457.3 / 13332 | 18350.3 / 10566 | -4893 | +2766 |
| cache_read_input_tokens | 261866.7 / 261960 | 183601.3 / 176189 | +78265.3 | +85771 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 0/3 |
| feature-comparison-read | 1/3 | 0/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
