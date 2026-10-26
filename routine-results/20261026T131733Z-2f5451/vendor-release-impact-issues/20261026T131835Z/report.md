# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T131835Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T131733Z-2f5451; started 2026-10-26T13:18:35Z, ended 2026-10-26T13:23:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.04 to 0.06, seven_day 0.67 to 0.67, from 8 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1669 / 0.5006 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.0946 / 0.2838 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1669 / 0.1723 | 0.0946 / 0.0950 | +0.0722 | +0.0773 |
| num_turns | 8 / 8 | 4.7 / 5 | +3.3 | +3 |
| duration_ms | 54953 / 57236 | 31382 / 31451 | +23571 | +25785 |
| input_tokens | 12 / 12 | 9.3 / 10 | +2.7 | +2 |
| output_tokens | 5317.7 / 5634 | 2554.7 / 2611 | +2763 | +3023 |
| cache_creation_input_tokens | 22334.3 / 22702 | 13064.7 / 13219 | +9269.7 | +9483 |
| cache_read_input_tokens | 241338.7 / 241138 | 166029.7 / 179262 | +75309 | +61876 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 3/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
