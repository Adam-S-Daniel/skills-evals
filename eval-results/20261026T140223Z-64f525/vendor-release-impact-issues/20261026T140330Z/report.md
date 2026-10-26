# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T140330Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140223Z-64f525; started 2026-10-26T14:03:30Z, ended 2026-10-26T14:07:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.25 to 0.31, seven_day 0.71 to 0.72, from 11 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1649 / 0.4948 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.0915 / 0.2746 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1649 / 0.1693 | 0.0915 / 0.0848 | +0.0734 | +0.0845 |
| num_turns | 7.7 / 8 | 4.3 / 4 | +3.3 | +4 |
| duration_ms | 51458.7 / 53843 | 27501.7 / 24952 | +23957 | +28891 |
| input_tokens | 11.3 / 12 | 8.7 / 8 | +2.7 | +4 |
| output_tokens | 5172.7 / 5374 | 2542 / 2253 | +2630.7 | +3121 |
| cache_creation_input_tokens | 22544 / 22650 | 12640.3 / 12005 | +9903.7 | +10645 |
| cache_read_input_tokens | 227707.3 / 244690 | 152297.3 / 138869 | +75410 | +105821 |
| tool_errors | 0.7 / 0 | 0 / 0 | +0.7 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 2/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
