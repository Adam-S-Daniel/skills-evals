# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T024521Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T024324Z-8aa141; started 2026-11-03T02:45:21Z, ended 2026-11-03T02:46:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 2 call(s); agent $0.34, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1973 / 0.1973 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1477 / 0.1477 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1973 / 0.1973 | 0.1477 / 0.1477 | +0.0496 | +0.0496 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 41455 / 41455 | 27657 / 27657 | +13798 | +13798 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 5047 / 5047 | 3011 / 3011 | +2036 | +2036 |
| cache_creation_input_tokens | 32325 / 32325 | 25405 / 25405 | +6920 | +6920 |
| cache_read_input_tokens | 174786 / 174786 | 159451 / 159451 | +15335 | +15335 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 1/1 |
| no-placeholder-in-title | 1/1 | 0/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
