# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T200109Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T195927Z-ef6ea3; started 2026-11-07T20:01:09Z, ended 2026-11-07T20:08:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.67, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.38 over 12 call(s); agent $2.53, judge $0.85, guard $0.00; last agent call $0.37

## Fixture: closed-duplicate (n=3)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | 9.5 (8.8 to 9.8, 3 judged) | 0.4923 / 1.4768 |
| without_skill | 3 | 0 | 6/6 | 9.5 (9.0 to 9.8, 3 judged) | 0.3496 / 1.0489 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4923 / 0.4833 | 0.3496 / 0.3475 | +0.1426 | +0.1358 |
| num_turns | 10.3 / 10 | 6 / 6 | +4.3 | +4 |
| duration_ms | 71408.7 / 68452 | 47752.7 / 46445 | +23656 | +22007 |
| input_tokens | 18.7 / 18 | 12 / 12 | +6.7 | +6 |
| output_tokens | 6401.3 / 6280 | 3966.7 / 3869 | +2434.7 | +2411 |
| cache_creation_input_tokens | 37188 / 36752 | 28722.7 / 28711 | +8465.3 | +8041 |
| cache_read_input_tokens | 333265.3 / 318077 | 202404 / 202039 | +130861.3 | +116038 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 3/3 | 3/3 |
| closed-issue-57-linked | 3/3 | 3/3 |
| no-duplicate-of-57 | 3/3 | 3/3 |
| synced-skill-issue-drafted | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
