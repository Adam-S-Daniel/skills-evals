# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T001635Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T001546Z-6d3170; started 2026-10-26T00:16:35Z, ended 2026-10-26T00:20:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.12 to 0.14, seven_day 0.5 to 0.5, from 8 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.2015 / 0.6046 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.0887 / 0.2661 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2015 / 0.1663 | 0.0887 / 0.0884 | +0.1128 | +0.0780 |
| num_turns | 8.3 / 8 | 4 / 4 | +4.3 | +4 |
| duration_ms | 49708 / 49283 | 25971.7 / 25184 | +23736.3 | +24099 |
| input_tokens | 12.7 / 12 | 8 / 8 | +4.7 | +4 |
| output_tokens | 5235 / 5407 | 2500.3 / 2449 | +2734.7 | +2958 |
| cache_creation_input_tokens | 31024 / 22027 | 12385.7 / 12416 | +18638.3 | +9611 |
| cache_read_input_tokens | 249102.7 / 240078 | 139071.3 / 139173 | +110031.3 | +100905 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 3/3 |
| no-placeholder-in-title | 3/3 | 0/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
