# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T154454Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T153628Z-574e37; started 2026-11-07T15:44:54Z, ended 2026-11-07T15:48:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.97 over 6 call(s); agent $0.97, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: issue-hygiene (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.1864 / 0.5592 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.1377 / 0.4132 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1864 / 0.1852 | 0.1377 / 0.1377 | +0.0487 | +0.0475 |
| num_turns | 6.7 / 6 | 4.7 / 5 | +2 | +1 |
| duration_ms | 37580.3 / 38177 | 31635 / 32187 | +5945.3 | +5990 |
| input_tokens | 11.3 / 10 | 8.7 / 8 | +2.7 | +2 |
| output_tokens | 4509 / 4494 | 2714.7 / 2677 | +1794.3 | +1817 |
| cache_creation_input_tokens | 31339 / 31116 | 24309.7 / 24291 | +7029.3 | +6825 |
| cache_read_input_tokens | 159468.7 / 129166 | 133241.7 / 121271 | +26227 | +7895 |
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
