# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T022116Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T021938Z-591f6a; started 2026-11-03T02:21:16Z, ended 2026-11-03T02:22:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 4 call(s); agent $0.34, judge $0.16, guard $0.00; last agent call $0.14

## Fixture: closed-duplicate (n=1)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.2003 / 0.2003 |
| without_skill | 1 | 0 | 5/6 | 9.2 (9.2 to 9.2, 1 judged) | 0.1394 / 0.1394 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2003 / 0.2003 | 0.1394 / 0.1394 | +0.0610 | +0.0610 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 40883 / 40883 | 28975 / 28975 | +11908 | +11908 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4520 / 4520 | 2355 / 2355 | +2165 | +2165 |
| cache_creation_input_tokens | 33270 / 33270 | 24975 / 24975 | +8295 | +8295 |
| cache_read_input_tokens | 220169 / 220169 | 159025 / 159025 | +61144 | +61144 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 0/1 | 0/1 |
| closed-issue-57-linked | 1/1 | 1/1 |
| no-duplicate-of-57 | 1/1 | 1/1 |
| synced-skill-issue-drafted | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
