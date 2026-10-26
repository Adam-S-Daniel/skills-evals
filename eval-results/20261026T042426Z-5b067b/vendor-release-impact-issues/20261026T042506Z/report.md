# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T042506Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T042426Z-5b067b; started 2026-10-26T04:25:06Z, ended 2026-10-26T04:29:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.07 to 0.08, seven_day 0.55 to 0.55, from 7 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1973 / 0.5920 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.0843 / 0.2528 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1973 / 0.1842 | 0.0843 / 0.0848 | +0.1131 | +0.0994 |
| num_turns | 11.7 / 8 | 4 / 4 | +7.7 | +4 |
| duration_ms | 51872.7 / 43396 | 22996.3 / 22769 | +28876.3 | +20627 |
| input_tokens | 14.7 / 12 | 8 / 8 | +6.7 | +4 |
| output_tokens | 4776.7 / 4910 | 2227.7 / 2268 | +2549 | +2642 |
| cache_creation_input_tokens | 30137 / 22230 | 11960.3 / 12000 | +18176.7 | +10230 |
| cache_read_input_tokens | 288202 / 211543 | 138826 / 138804 | +149376 | +72739 |
| tool_errors | 2.7 / 1 | 0.3 / 0 | +2.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 3/3 |
| no-placeholder-in-title | 3/3 | 0/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
