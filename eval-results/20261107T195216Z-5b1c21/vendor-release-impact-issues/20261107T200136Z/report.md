# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T200136Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T195216Z-5b1c21; started 2026-11-07T20:01:36Z, ended 2026-11-07T20:04:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.66, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 6 call(s); agent $0.99, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: issue-hygiene (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1987 / 0.5960 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1324 / 0.3971 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1987 / 0.2055 | 0.1324 / 0.1306 | +0.0663 | +0.0749 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 41817 / 41272 | 22173.7 / 22199 | +19643.3 | +19073 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 5104.7 / 5537 | 2387.7 / 2268 | +2717 | +3269 |
| cache_creation_input_tokens | 32488.7 / 33114 | 24087.3 / 23944 | +8401.3 | +9170 |
| cache_read_input_tokens | 176269 / 176347 | 121349.7 / 121346 | +54919.3 | +55001 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 3/3 |
| no-placeholder-in-title | 3/3 | 0/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
