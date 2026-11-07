# Eval report: debug-github-workflows

- Timestamp: 20261107T133219Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T133122Z-7583be; started 2026-11-07T13:32:19Z, ended 2026-11-07T13:34:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 6 call(s); agent $0.56, judge $0.34, guard $0.00; last agent call $0.19

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.3/7 | 8.9 (8.8 to 9.2, 3 judged) | 0.1874 / 0.5621 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1874 / 0.1877 |
| num_turns | 6 / 6 |
| duration_ms | 32094.3 / 32216 |
| input_tokens | 11.3 / 12 |
| output_tokens | 2074 / 2123 |
| cache_creation_input_tokens | 13032 / 13053 |
| cache_read_input_tokens | 207889 / 221924 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| failing-log-read-without-writes | 1/3 |
| feature-comparison-read | 0/3 |
| main-differs-from-feature | 3/3 |
| merge-existing-fix | 3/3 |
| obsolete-command-diagnosed | 3/3 |
| repository-files-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
