# Eval report: debug-github-workflows

- Timestamp: 20261107T191404Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T190544Z-ab0d2b; started 2026-11-07T19:14:04Z, ended 2026-11-07T19:17:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.63, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.84 over 12 call(s); agent $0.58, judge $0.26, guard $0.00; last agent call $0.09

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/7 | 8.4 (8.2 to 8.8, 3 judged) | 0.1008 / 0.3024 |
| without_skill | 3 | 0 | 6/7 | 7.5 (5.0 to 8.8, 3 judged) | 0.0910 / 0.2730 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1008 / 0.0843 | 0.0910 / 0.0894 | +0.0098 | -0.0052 |
| num_turns | 5.7 / 5 | 6 / 6 | -0.3 | -1 |
| duration_ms | 21613.3 / 21571 | 21733 / 20801 | -119.7 | +770 |
| input_tokens | 10.7 / 10 | 10.7 / 10 | 0 | 0 |
| output_tokens | 1522 / 1505 | 1649.7 / 1609 | -127.7 | -104 |
| cache_creation_input_tokens | 16972.3 / 13291 | 14088.7 / 14071 | +2883.7 | -780 |
| cache_read_input_tokens | 176839.3 / 168415 | 181167.7 / 168820 | -4328.3 | -405 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 2/3 | 1/3 |
| feature-comparison-read | 1/3 | 2/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
