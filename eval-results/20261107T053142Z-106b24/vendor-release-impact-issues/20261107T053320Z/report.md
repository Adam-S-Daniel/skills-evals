# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T053320Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T053142Z-106b24; started 2026-11-07T05:33:20Z, ended 2026-11-07T05:34:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.34, judge $0.09, guard $0.00; last agent call $0.16

## Fixture: closed-duplicate (n=1)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 9.0 (9.0 to 9.0, 1 judged) | 0.1758 / 0.1758 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1598 / 0.1598 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1758 / 0.1758 | 0.1598 / 0.1598 | +0.0159 | +0.0159 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 37126 / 37126 | 30981 / 30981 | +6145 | +6145 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3651 / 3651 | 3280 / 3280 | +371 | +371 |
| cache_creation_input_tokens | 30488 / 30488 | 27657 / 27657 | +2831 | +2831 |
| cache_read_input_tokens | 172688 / 172688 | 163773 / 163773 | +8915 | +8915 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 0/1 | 0/1 |
| closed-issue-57-linked | 1/1 | 1/1 |
| no-duplicate-of-57 | 1/1 | 1/1 |
| synced-skill-issue-drafted | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
