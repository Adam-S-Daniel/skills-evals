# Eval report: post-failure-comment

- Timestamp: 20261107T112321Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T112155Z-955d3a; started 2026-11-07T11:23:21Z, ended 2026-11-07T11:25:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.61 over 4 call(s); agent $0.61, judge $0.00, guard $0.00; last agent call $0.17

## Fixture: post-failure-comment (n=2)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 9/12 | skipped (objective-decided) | 0.1555 / 0.3110 |
| without_skill | 2 | 0 | 8.5/12 | skipped (objective-decided) | 0.1515 / 0.3029 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1555 / 0.1555 | 0.1515 / 0.1515 | +0.0040 | +0.0040 |
| num_turns | 7.5 / 7.5 | 7 / 7 | +0.5 | +0.5 |
| duration_ms | 24071 / 24071 | 39546.5 / 39546.5 | -15475.5 | -15475.5 |
| input_tokens | 14 / 14 | 13 / 13 | +1 | +1 |
| output_tokens | 2287 / 2287 | 3863 / 3863 | -1576 | -1576 |
| cache_creation_input_tokens | 27296 / 27296 | 22016 / 22016 | +5280 | +5280 |
| cache_read_input_tokens | 234121.5 / 234121.5 | 247411 / 247411 | -13289.5 | -13289.5 |
| tool_errors | 0.5 / 0.5 | 0 / 0 | +0.5 | +0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflows-still-parse | 2/2 | 2/2 |
| schedule-only-workflow-untouched | 2/2 | 2/2 |
| e2e-inline-block-removed | 2/2 | 2/2 |
| e2e-post-step | 2/2 | 2/2 |
| e2e-resolve-step | 2/2 | 2/2 |
| visual-regression-report-job-shape | 0/2 | 0/2 |
| visual-regression-post-step | 0/2 | 0/2 |
| visual-regression-resolve-step | 0/2 | 0/2 |
| post-failure-comment-reference-valid | 2/2 | 1/2 |
| markers-unique-per-workflow | 2/2 | 2/2 |
| no-event-or-input-interpolation-in-run | 2/2 | 2/2 |
| cms-platform-vendored-contract-unchanged | 2/2 | 2/2 |
