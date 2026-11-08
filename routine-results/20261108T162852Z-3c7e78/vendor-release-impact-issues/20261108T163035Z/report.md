# Eval report: vendor-release-impact-issues

- Timestamp: 20261108T163035Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T162852Z-3c7e78; started 2026-11-08T16:30:35Z, ended 2026-11-08T16:33:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.81 to 0.81, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 2 call(s); agent $0.73, judge $0.00, guard $0.00; last agent call $0.24

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.4908 / 0.4908 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2380 / 0.2380 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4908 / 0.4908 | 0.2380 / 0.2380 | +0.2527 | +0.2527 |
| num_turns | 10 / 10 | 4 / 4 | +6 | +6 |
| duration_ms | 109264 / 109264 | 50034 / 50034 | +59230 | +59230 |
| input_tokens | 20 / 20 | 8 / 8 | +12 | +12 |
| output_tokens | 8368 / 8368 | 4167 / 4167 | +4201 | +4201 |
| cache_creation_input_tokens | 51247 / 51247 | 26028 / 26028 | +25219 | +25219 |
| cache_read_input_tokens | 335382 / 335382 | 122493 / 122493 | +212889 | +212889 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 1/1 |
| no-placeholder-in-title | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
