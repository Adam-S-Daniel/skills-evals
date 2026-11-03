# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T231145Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T230954Z-84526b; started 2026-11-03T23:11:45Z, ended 2026-11-03T23:13:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.79 to 0.79, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 4 call(s); agent $0.35, judge $0.16, guard $0.00; last agent call $0.15

## Fixture: closed-duplicate (n=1)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 9.0 (9.0 to 9.0, 1 judged) | 0.1984 / 0.1984 |
| without_skill | 1 | 0 | 6/6 | 9.4 (9.4 to 9.4, 1 judged) | 0.1507 / 0.1507 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1984 / 0.1984 | 0.1507 / 0.1507 | +0.0477 | +0.0477 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 43869 / 43869 | 34527 / 34527 | +9342 | +9342 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 4257 / 4257 | 2744 / 2744 | +1513 | +1513 |
| cache_creation_input_tokens | 32424 / 32424 | 26745 / 26745 | +5679 | +5679 |
| cache_read_input_tokens | 260696 / 260696 | 162192 / 162192 | +98504 | +98504 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 0/1 | 1/1 |
| closed-issue-57-linked | 1/1 | 1/1 |
| no-duplicate-of-57 | 1/1 | 1/1 |
| synced-skill-issue-drafted | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
