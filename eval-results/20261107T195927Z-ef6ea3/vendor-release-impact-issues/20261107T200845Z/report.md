# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T200845Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T195927Z-ef6ea3; started 2026-11-07T20:08:45Z, ended 2026-11-07T20:11:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.98 over 6 call(s); agent $0.98, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: closed-duplicate (n=3)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/6 | skipped (objective-decided) | 0.1853 / 0.5560 |
| without_skill | 3 | 0 | 5/6 | skipped (objective-decided) | 0.1402 / 0.4207 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1853 / 0.1883 | 0.1402 / 0.1387 | +0.0451 | +0.0497 |
| num_turns | 8 / 8 | 4.3 / 4 | +3.7 | +4 |
| duration_ms | 38892.3 / 41478 | 21937 / 21944 | +16955.3 | +19534 |
| input_tokens | 14 / 14 | 8.7 / 8 | +5.3 | +6 |
| output_tokens | 3832.7 / 3877 | 2188 / 2234 | +1644.7 | +1643 |
| cache_creation_input_tokens | 31341.3 / 30972 | 26150.3 / 25977 | +5191 | +4995 |
| cache_read_input_tokens | 216203 / 215149 | 137192.3 / 124023 | +79010.7 | +91126 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 2/3 | 0/3 |
| closed-issue-57-linked | 3/3 | 3/3 |
| no-duplicate-of-57 | 3/3 | 3/3 |
| synced-skill-issue-drafted | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
