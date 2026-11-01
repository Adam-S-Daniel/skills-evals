# Eval report: debug-github-workflows

- Timestamp: 20261101T151114Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T151006Z-ad7d1c; started 2026-11-01T15:11:14Z, ended 2026-11-01T15:12:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.86 to 0.86, from 4 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1032 / 0.1032 |
| without_skill | 1 | 0 | 7/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.0735 / 0.0735 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1032 / 0.1032 | 0.0735 / 0.0735 | +0.0297 | +0.0297 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 40980 / 40980 | 33064 / 33064 | +7916 | +7916 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 1876 / 1876 | 1182 / 1182 | +694 | +694 |
| cache_creation_input_tokens | 14441 / 14441 | 10957 / 10957 | +3484 | +3484 |
| cache_read_input_tokens | 265118 / 265118 | 177253 / 177253 | +87865 | +87865 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 0/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
