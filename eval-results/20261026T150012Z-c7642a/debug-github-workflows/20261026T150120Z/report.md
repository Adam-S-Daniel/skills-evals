# Eval report: debug-github-workflows

- Timestamp: 20261026T150120Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T150012Z-c7642a; started 2026-10-26T15:01:20Z, ended 2026-10-26T15:07:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.72 to 0.74, seven_day 0.81 to 0.81, from 7 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 8.6 (8.0 to 9.0, 3 judged) | 0.1977 / 0.5930 |
| without_skill | 3 | 0 | 5.7/7 | 6.5 (5.0 to 8.8, 3 judged) | 0.1929 / 0.5787 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1977 / 0.2038 | 0.1929 / 0.1979 | +0.0048 | +0.0060 |
| num_turns | 6.3 / 6 | 6 / 6 | +0.3 | 0 |
| duration_ms | 29291.7 / 28907 | 28386 / 29938 | +905.7 | -1031 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2227.3 / 2255 | 1988.7 / 2115 | +238.7 | +140 |
| cache_creation_input_tokens | 13577.7 / 14219 | 13566.3 / 13770 | +11.3 | +449 |
| cache_read_input_tokens | 221557 / 222379 | 222018 / 222410 | -461 | -31 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 1/3 |
| feature-comparison-read | 0/3 | 1/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
