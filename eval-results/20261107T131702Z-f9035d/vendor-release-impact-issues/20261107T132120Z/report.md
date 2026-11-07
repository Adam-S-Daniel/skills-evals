# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T132120Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T131702Z-f9035d; started 2026-11-07T13:21:20Z, ended 2026-11-07T13:23:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 6 call(s); agent $0.36, judge $0.14, guard $0.00; last agent call $0.14

## Fixture: closed-duplicate (n=3)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.7/6 | 8.7 (8.4 to 9.2, 3 judged) | 0.1190 / 0.3571 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1190 / 0.1075 |
| num_turns | 7.3 / 6 |
| duration_ms | 37471.7 / 31325 |
| input_tokens | 14 / 12 |
| output_tokens | 2945.7 / 2389 |
| cache_creation_input_tokens | 15764.7 / 15697 |
| cache_read_input_tokens | 264760.7 / 225599 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| searched-closed-issues-without-writing | 2/3 |
| closed-issue-57-linked | 3/3 |
| no-duplicate-of-57 | 3/3 |
| synced-skill-issue-drafted | 3/3 |
| seed-repo-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
