# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T040200Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T040014Z-1d23f2; started 2026-11-04T04:02:00Z, ended 2026-11-04T04:03:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.9 to 0.9, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 2 call(s); agent $0.33, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1931 / 0.1931 |
| without_skill | 1 | 0 | 4/7 | skipped (objective-decided) | 0.1393 / 0.1393 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1931 / 0.1931 | 0.1393 / 0.1393 | +0.0537 | +0.0537 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 35482 / 35482 | 26016 / 26016 | +9466 | +9466 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4579 / 4579 | 2914 / 2914 | +1665 | +1665 |
| cache_creation_input_tokens | 32435 / 32435 | 24522 / 24522 | +7913 | +7913 |
| cache_read_input_tokens | 175365 / 175365 | 121019 / 121019 | +54346 | +54346 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 0/1 |
| no-placeholder-in-title | 1/1 | 0/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
