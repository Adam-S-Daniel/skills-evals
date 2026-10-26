# Eval report: debug-github-workflows

- Timestamp: 20261026T143650Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T143650Z-8fa1bd; started 2026-10-26T14:36:50Z, ended 2026-10-26T14:42:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.52 to 0.55, seven_day 0.77 to 0.77, from 7 snapshots

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/7 | 7.3 (5.0 to 8.8, 3 judged) | 0.0988 / 0.2964 |
| without_skill | 3 | 0 | 6.3/7 | 6.1 (4.2 to 8.8, 3 judged) | 0.0739 / 0.2218 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0988 / 0.0979 | 0.0739 / 0.0739 | +0.0249 | +0.0240 |
| num_turns | 9.3 / 9 | 6 / 6 | +3.3 | +3 |
| duration_ms | 41772.3 / 44491 | 34288.7 / 35556 | +7483.7 | +8935 |
| input_tokens | 14.7 / 14 | 10.7 / 10 | +4 | +4 |
| output_tokens | 1809.7 / 1746 | 1225.7 / 1191 | +584 | +555 |
| cache_creation_input_tokens | 13293 / 13582 | 10706 / 10978 | +2587 | +2604 |
| cache_read_input_tokens | 273766.3 / 259326 | 187142.3 / 175465 | +86624 | +83861 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 2/3 | 2/3 |
| feature-comparison-read | 1/3 | 2/3 |
| main-differs-from-feature | 2/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
