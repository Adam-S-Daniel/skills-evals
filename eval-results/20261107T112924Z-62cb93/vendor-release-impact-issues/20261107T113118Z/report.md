# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T113118Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T112924Z-62cb93; started 2026-11-07T11:31:18Z, ended 2026-11-07T11:33:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.83 over 8 call(s); agent $0.65, judge $0.18, guard $0.00; last agent call $0.15

## Fixture: closed-duplicate (n=2)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 5/6 | 9.0 (8.6 to 9.4, 2 judged) | 0.1831 / 0.3662 |
| without_skill | 2 | 0 | 5/6 | 9.4 (9.4 to 9.4, 2 judged) | 0.1416 / 0.2832 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1831 / 0.1831 | 0.1416 / 0.1416 | +0.0415 | +0.0415 |
| num_turns | 7 / 7 | 4.5 / 4.5 | +2.5 | +2.5 |
| duration_ms | 34766 / 34766 | 25706.5 / 25706.5 | +9059.5 | +9059.5 |
| input_tokens | 12 / 12 | 9 / 9 | +3 | +3 |
| output_tokens | 3686.5 / 3686.5 | 2542.5 / 2542.5 | +1144 | +1144 |
| cache_creation_input_tokens | 32178 / 32178 | 25501 / 25501 | +6677 | +6677 |
| cache_read_input_tokens | 175113 / 175113 | 141685 / 141685 | +33428 | +33428 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 0/2 | 0/2 |
| closed-issue-57-linked | 2/2 | 2/2 |
| no-duplicate-of-57 | 2/2 | 2/2 |
| synced-skill-issue-drafted | 2/2 | 2/2 |
| seed-repo-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
