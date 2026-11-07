# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T073850Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T073704Z-0b81de; started 2026-11-07T07:38:50Z, ended 2026-11-07T07:40:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 2 call(s); agent $0.34, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: closed-duplicate (n=1)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1853 / 0.1853 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.1526 / 0.1526 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1853 / 0.1853 | 0.1526 / 0.1526 | +0.0327 | +0.0327 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 38884 / 38884 | 30450 / 30450 | +8434 | +8434 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3995 / 3995 | 2679 / 2679 | +1316 | +1316 |
| cache_creation_input_tokens | 30977 / 30977 | 26467 / 26467 | +4510 | +4510 |
| cache_read_input_tokens | 214048 / 214048 | 199233 / 199233 | +14815 | +14815 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 1/1 | 0/1 |
| closed-issue-57-linked | 1/1 | 1/1 |
| no-duplicate-of-57 | 1/1 | 1/1 |
| synced-skill-issue-drafted | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
