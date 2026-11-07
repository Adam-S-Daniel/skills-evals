# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T052927Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052753Z-31ab03; started 2026-11-07T05:29:27Z, ended 2026-11-07T05:30:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 2 call(s); agent $0.32, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.1937 / 0.1937 |
| without_skill | 1 | 0 | 5/7 | skipped (objective-decided) | 0.1303 / 0.1303 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1937 / 0.1937 | 0.1303 / 0.1303 | +0.0634 | +0.0634 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 38786 / 38786 | 21460 / 21460 | +17326 | +17326 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4766 / 4766 | 2293 / 2293 | +2473 | +2473 |
| cache_creation_input_tokens | 32134 / 32134 | 23815 / 23815 | +8319 | +8319 |
| cache_read_input_tokens | 174611 / 174611 | 120728 / 120728 | +53883 | +53883 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 1/1 |
| no-placeholder-in-title | 1/1 | 0/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
