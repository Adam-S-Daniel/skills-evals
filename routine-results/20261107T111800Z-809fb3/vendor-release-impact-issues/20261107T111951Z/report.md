# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T111951Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T111800Z-809fb3; started 2026-11-07T11:19:51Z, ended 2026-11-07T11:22:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 4 call(s); agent $0.66, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: issue-hygiene (n=2)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 7/7 | skipped (objective-decided) | 0.1954 / 0.3908 |
| without_skill | 2 | 0 | 5/7 | skipped (objective-decided) | 0.1333 / 0.2666 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1954 / 0.1954 | 0.1333 / 0.1333 | +0.0621 | +0.0621 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 44239.5 / 44239.5 | 21783 / 21783 | +22456.5 | +22456.5 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4968 / 4968 | 2472 / 2472 | +2496 | +2496 |
| cache_creation_input_tokens | 32082 / 32082 | 24112 / 24112 | +7970 | +7970 |
| cache_read_input_tokens | 173688 / 173688 | 121065.5 / 121065.5 | +52622.5 | +52622.5 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 2/2 | 2/2 |
| publish-times-source-and-version-bound | 2/2 | 0/2 |
| pr-refs-fenced-not-quoted | 2/2 | 2/2 |
| no-upstream-issue-backlink | 2/2 | 2/2 |
| no-placeholder-in-title | 2/2 | 0/2 |
| seed-repo-unchanged | 2/2 | 2/2 |
| hook-matcher-surface-named | 2/2 | 2/2 |
