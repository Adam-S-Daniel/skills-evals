# Eval report: post-failure-comment

- Timestamp: 20261107T200349Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T194840Z-e98d0d; started 2026-11-07T20:03:49Z, ended 2026-11-07T20:08:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.67, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.21 over 12 call(s); agent $0.90, judge $0.31, guard $0.00; last agent call $0.13

## Fixture: post-failure-comment (n=3)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/12 | 5.4 (5.0 to 5.8, 3 judged) | 0.1650 / 0.4951 |
| without_skill | 3 | 0 | 9/12 | 5.5 (4.9 to 6.1, 3 judged) | 0.1362 / 0.4087 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1650 / 0.1566 | 0.1362 / 0.1309 | +0.0288 | +0.0256 |
| num_turns | 8.3 / 8 | 6.3 / 6 | +2 | +2 |
| duration_ms | 30186.3 / 27800 | 36095.3 / 34492 | -5909 | -6692 |
| input_tokens | 16 / 16 | 12.7 / 12 | +3.3 | +4 |
| output_tokens | 3009.3 / 2966 | 3993 / 3695 | -983.7 | -729 |
| cache_creation_input_tokens | 26651.3 / 23049 | 18181 / 17941 | +8470.3 | +5108 |
| cache_read_input_tokens | 282878 / 286598 | 235678.7 / 221806 | +47199.3 | +64792 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

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
