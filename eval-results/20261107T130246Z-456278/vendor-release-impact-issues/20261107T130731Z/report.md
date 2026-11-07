# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T130731Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T130246Z-456278; started 2026-11-07T13:07:31Z, ended 2026-11-07T13:09:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.44, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.44 over 6 call(s); agent $0.28, judge $0.16, guard $0.00; last agent call $0.09

## Fixture: issue-hygiene (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.3/7 | 4.6 (4.4 to 5.1, 3 judged) | 0.0932 / 0.2797 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0932 / 0.0944 |
| num_turns | 4.3 / 4 |
| duration_ms | 31192 / 31555 |
| input_tokens | 8.7 / 8 |
| output_tokens | 2655.7 / 2599 |
| cache_creation_input_tokens | 12833.3 / 12860 |
| cache_read_input_tokens | 153340.7 / 139959 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| at-least-one-issue-drafted | 3/3 |
| publish-times-source-and-version-bound | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 |
| no-upstream-issue-backlink | 1/3 |
| no-placeholder-in-title | 0/3 |
| seed-repo-unchanged | 3/3 |
| hook-matcher-surface-named | 3/3 |
