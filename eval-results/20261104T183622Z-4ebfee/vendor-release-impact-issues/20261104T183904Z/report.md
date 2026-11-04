# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T183904Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T183622Z-4ebfee; started 2026-11-04T18:39:04Z, ended 2026-11-04T18:40:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.74 over 4 call(s); agent $0.37, judge $0.37, guard $0.00; last agent call $0.15

## Fixture: closed-duplicate (n=1)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 9.2 (9.2 to 9.2, 1 judged) | 0.2206 / 0.2206 |
| without_skill | 1 | 0 | 5/6 | 9.4 (9.4 to 9.4, 1 judged) | 0.1480 / 0.1480 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2206 / 0.2206 | 0.1480 / 0.1480 | +0.0726 | +0.0726 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 56178 / 56178 | 21670 / 21670 | +34508 | +34508 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 5031 / 5031 | 2460 / 2460 | +2571 | +2571 |
| cache_creation_input_tokens | 35781 / 35781 | 26783 / 26783 | +8998 | +8998 |
| cache_read_input_tokens | 271266 / 271266 | 162509 / 162509 | +108757 | +108757 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 0/1 | 0/1 |
| closed-issue-57-linked | 1/1 | 1/1 |
| no-duplicate-of-57 | 1/1 | 1/1 |
| synced-skill-issue-drafted | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
