# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T154529Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T154338Z-6ec7e4; started 2026-11-07T15:45:29Z, ended 2026-11-07T15:53:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.51, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.38 over 12 call(s); agent $2.50, judge $0.88, guard $0.00; last agent call $0.34

## Fixture: closed-duplicate (n=3)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | 9.0 (8.8 to 9.2, 3 judged) | 0.4970 / 1.4910 |
| without_skill | 3 | 0 | 6/6 | 9.7 (9.6 to 9.8, 3 judged) | 0.3363 / 1.0088 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4970 / 0.4937 | 0.3363 / 0.3356 | +0.1607 | +0.1581 |
| num_turns | 11 / 10 | 6 / 6 | +5 | +4 |
| duration_ms | 68045.3 / 68203 | 48059.3 / 48055 | +19986 | +20148 |
| input_tokens | 20.7 / 20 | 12 / 12 | +8.7 | +8 |
| output_tokens | 6532.7 / 6823 | 3989.3 / 3862 | +2543.3 | +2961 |
| cache_creation_input_tokens | 36434.7 / 36629 | 27070 / 27147 | +9364.7 | +9482 |
| cache_read_input_tokens | 373900 / 355428 | 199329 / 199314 | +174571 | +156114 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 3/3 | 3/3 |
| closed-issue-57-linked | 3/3 | 3/3 |
| no-duplicate-of-57 | 3/3 | 3/3 |
| synced-skill-issue-drafted | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
