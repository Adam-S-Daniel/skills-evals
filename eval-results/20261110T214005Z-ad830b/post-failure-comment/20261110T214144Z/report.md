# Eval report: post-failure-comment

- Timestamp: 20261110T214144Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T214005Z-ad830b; started 2026-11-10T21:41:44Z, ended 2026-11-10T21:44:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.28 to 0.29, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.05 over 6 call(s); agent $0.75, judge $0.30, guard $0.00; last agent call $0.17

## Fixture: post-failure-comment (n=3)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 8.3/12 | 5.4 (5.3 to 5.5, 3 judged) | 0.2497 / 0.7490 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2497 / 0.2730 |
| num_turns | 5.3 / 5 |
| duration_ms | 47537 / 41294 |
| input_tokens | 10.7 / 10 |
| output_tokens | 4352.3 / 3908 |
| cache_creation_input_tokens | 24910.3 / 19590 |
| cache_read_input_tokens | 190202.7 / 153586 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| workflows-still-parse | 3/3 |
| schedule-only-workflow-untouched | 3/3 |
| e2e-inline-block-removed | 3/3 |
| e2e-post-step | 1/3 |
| e2e-resolve-step | 3/3 |
| visual-regression-report-job-shape | 0/3 |
| visual-regression-post-step | 0/3 |
| visual-regression-resolve-step | 0/3 |
| post-failure-comment-reference-valid | 3/3 |
| markers-unique-per-workflow | 3/3 |
| no-event-or-input-interpolation-in-run | 3/3 |
| cms-platform-vendored-contract-unchanged | 3/3 |
