# Eval report: debug-github-workflows

- Timestamp: 20261026T143427Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143427Z-1d39ad; started 2026-10-26T14:34:27Z, ended 2026-10-26T14:40:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.5 to 0.53, seven_day 0.76 to 0.77, from 8 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.7/7 | 6.4 (5.4 to 8.2, 3 judged) | 0.0917 / 0.2751 |
| without_skill | 3 | 0 | 5/7 | 7.6 (6.0 to 8.8, 3 judged) | 0.0798 / 0.2393 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0917 / 0.0905 | 0.0798 / 0.0799 | +0.0119 | +0.0106 |
| num_turns | 9.3 / 9 | 6.3 / 6 | +3 | +3 |
| duration_ms | 48066.7 / 45682 | 33681 / 34863 | +14385.7 | +10819 |
| input_tokens | 12 / 12 | 11.3 / 10 | +0.7 | +2 |
| output_tokens | 1677 / 1646 | 1416.7 / 1446 | +260.3 | +200 |
| cache_creation_input_tokens | 13196.3 / 13318 | 11333 / 11381 | +1863.3 | +1937 |
| cache_read_input_tokens | 219976 / 221297 | 201123.7 / 176460 | +18852.3 | +44837 |
| tool_errors | 0.3 / 0 | 1.3 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/3 | 1/3 |
| feature-comparison-read | 0/3 | 1/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 2/3 |
| obsolete-command-diagnosed | 3/3 | 2/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
