# Eval report: debug-github-workflows

- Timestamp: 20261101T132513Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T132423Z-4b12e0; started 2026-11-01T13:25:13Z, ended 2026-11-01T13:26:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.85 to 0.85, from 4 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 7.0 (7.0 to 7.0, 1 judged) | 0.1015 / 0.1015 |
| without_skill | 1 | 0 | 5/7 | 4.8 (4.8 to 4.8, 1 judged) | 0.0696 / 0.0696 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1015 / 0.1015 | 0.0696 / 0.0696 | +0.0319 | +0.0319 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 29621 / 29621 | 21097 / 21097 | +8524 | +8524 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 1929 / 1929 | 1148 / 1148 | +781 | +781 |
| cache_creation_input_tokens | 13928 / 13928 | 10084 / 10084 | +3844 | +3844 |
| cache_read_input_tokens | 262967 / 262967 | 176093 / 176093 | +86874 | +86874 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 0/1 |
| feature-comparison-read | 0/1 | 0/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
