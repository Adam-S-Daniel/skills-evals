# Eval report: post-failure-comment

- Timestamp: 20261107T154348Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T153258Z-0779a2; started 2026-11-07T15:43:48Z, ended 2026-11-07T15:48:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.18 over 12 call(s); agent $0.88, judge $0.30, guard $0.00; last agent call $0.12

## Fixture: post-failure-comment (n=3)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/12 | 5.6 (5.3 to 6.1, 3 judged) | 0.1590 / 0.4771 |
| without_skill | 3 | 0 | 9/12 | 5.1 (4.9 to 5.3, 3 judged) | 0.1333 / 0.3998 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1590 / 0.1508 | 0.1333 / 0.1302 | +0.0258 | +0.0206 |
| num_turns | 8.7 / 9 | 6.7 / 6 | +2 | +3 |
| duration_ms | 32558.7 / 34184 | 39607.3 / 33998 | -7048.7 | +186 |
| input_tokens | 16.7 / 18 | 13.3 / 12 | +3.3 | +6 |
| output_tokens | 2604.3 / 2682 | 3556 / 3615 | -951.7 | -933 |
| cache_creation_input_tokens | 25838 / 22756 | 18181.3 / 17967 | +7656.7 | +4789 |
| cache_read_input_tokens | 295964.7 / 328754 | 249584 / 221576 | +46380.7 | +107178 |
| tool_errors | 0 / 0 | 1 / 0 | -1 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflows-still-parse | 3/3 | 3/3 |
| schedule-only-workflow-untouched | 3/3 | 3/3 |
| e2e-inline-block-removed | 3/3 | 3/3 |
| e2e-post-step | 3/3 | 3/3 |
| e2e-resolve-step | 3/3 | 3/3 |
| visual-regression-report-job-shape | 0/3 | 0/3 |
| visual-regression-post-step | 0/3 | 0/3 |
| visual-regression-resolve-step | 0/3 | 0/3 |
| post-failure-comment-reference-valid | 3/3 | 3/3 |
| markers-unique-per-workflow | 3/3 | 3/3 |
| no-event-or-input-interpolation-in-run | 3/3 | 3/3 |
| cms-platform-vendored-contract-unchanged | 3/3 | 3/3 |
