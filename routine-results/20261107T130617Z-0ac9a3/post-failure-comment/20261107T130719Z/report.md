# Eval report: post-failure-comment

- Timestamp: 20261107T130719Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T130617Z-0ac9a3; started 2026-11-07T13:07:19Z, ended 2026-11-07T13:09:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.44, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.48 over 6 call(s); agent $0.33, judge $0.16, guard $0.00; last agent call $0.11

## Fixture: post-failure-comment (n=3)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.7/12 | 4.2 (2.3 to 5.3, 3 judged) | 0.1084 / 0.3252 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1084 / 0.1078 |
| num_turns | 5.7 / 6 |
| duration_ms | 38740.7 / 38769 |
| input_tokens | 11.3 / 12 |
| output_tokens | 3162.7 / 3221 |
| cache_creation_input_tokens | 13965.3 / 13493 |
| cache_read_input_tokens | 208944.3 / 228277 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflows-still-parse | 3/3 |
| schedule-only-workflow-untouched | 3/3 |
| e2e-inline-block-removed | 2/3 |
| e2e-post-step | 2/3 |
| e2e-resolve-step | 2/3 |
| visual-regression-report-job-shape | 0/3 |
| visual-regression-post-step | 0/3 |
| visual-regression-resolve-step | 0/3 |
| post-failure-comment-reference-valid | 2/3 |
| markers-unique-per-workflow | 3/3 |
| no-event-or-input-interpolation-in-run | 3/3 |
| cms-platform-vendored-contract-unchanged | 3/3 |
