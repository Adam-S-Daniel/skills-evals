# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T153803Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T153628Z-574e37; started 2026-11-07T15:38:03Z, ended 2026-11-07T15:44:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.50 over 6 call(s); agent $2.50, judge $0.00, guard $0.00; last agent call $0.40

## Fixture: issue-hygiene (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4850 / 1.4550 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.3496 / 1.0489 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4850 / 0.4736 | 0.3496 / 0.3357 | +0.1354 | +0.1379 |
| num_turns | 8.7 / 9 | 5 / 5 | +3.7 | +4 |
| duration_ms | 75654 / 68586 | 57057.3 / 52031 | +18596.7 | +16555 |
| input_tokens | 16.7 / 18 | 10 / 10 | +6.7 | +8 |
| output_tokens | 7318 / 6661 | 4935.7 / 4375 | +2382.3 | +2286 |
| cache_creation_input_tokens | 35413.3 / 34948 | 27302.3 / 26956 | +8111 | +7992 |
| cache_read_input_tokens | 276370.7 / 303762 | 162294 / 162466 | +114076.7 | +141296 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 2/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
