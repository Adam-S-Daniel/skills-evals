# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T155311Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T154338Z-6ec7e4; started 2026-11-07T15:53:11Z, ended 2026-11-07T15:57:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.51, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.04 over 6 call(s); agent $1.04, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: closed-duplicate (n=3)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.2009 / 0.6028 |
| without_skill | 3 | 0 | 5/6 | skipped (objective-decided) | 0.1453 / 0.4360 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2009 / 0.1951 | 0.1453 / 0.1454 | +0.0556 | +0.0497 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 48203.7 / 51912 | 33154 / 32115 | +15049.7 | +19797 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 4508 / 4112 | 2458 / 2511 | +2050 | +1601 |
| cache_creation_input_tokens | 32483.3 / 32044 | 26159.3 / 26171 | +6324 | +5873 |
| cache_read_input_tokens | 258883.7 / 258101 | 160984.3 / 161170 | +97899.3 | +96931 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 3/3 | 0/3 |
| closed-issue-57-linked | 3/3 | 3/3 |
| no-duplicate-of-57 | 3/3 | 3/3 |
| synced-skill-issue-drafted | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
