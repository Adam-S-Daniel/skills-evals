# Eval report: post-failure-comment

- Timestamp: 20261107T153440Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T153258Z-0779a2; started 2026-11-07T15:34:40Z, ended 2026-11-07T15:43:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.5, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.93 over 6 call(s); agent $2.93, judge $0.00, guard $0.00; last agent call $0.50

## Fixture: post-failure-comment (n=3)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/12 | skipped (objective-decided) | 0.4669 / 1.4006 |
| without_skill | 3 | 0 | 7.3/12 | skipped (objective-decided) | 0.5111 / 1.5332 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4669 / 0.4857 | 0.5111 / 0.4986 | -0.0442 | -0.0129 |
| num_turns | 8.3 / 8 | 9 / 9 | -0.7 | -1 |
| duration_ms | 78717 / 76735 | 100717.7 / 110554 | -22000.7 | -33819 |
| input_tokens | 17.3 / 16 | 19.3 / 20 | -2 | -4 |
| output_tokens | 5411.3 / 5594 | 6158 / 5860 | -746.7 | -266 |
| cache_creation_input_tokens | 31930.3 / 28119 | 30756 / 29773 | +1174.3 | -1654 |
| cache_read_input_tokens | 279684.7 / 252292 | 349009 / 344837 | -69324.3 | -92545 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflows-still-parse | 3/3 | 3/3 |
| schedule-only-workflow-untouched | 3/3 | 3/3 |
| e2e-inline-block-removed | 3/3 | 2/3 |
| e2e-post-step | 3/3 | 2/3 |
| e2e-resolve-step | 3/3 | 2/3 |
| visual-regression-report-job-shape | 0/3 | 0/3 |
| visual-regression-post-step | 0/3 | 0/3 |
| visual-regression-resolve-step | 0/3 | 0/3 |
| post-failure-comment-reference-valid | 3/3 | 2/3 |
| markers-unique-per-workflow | 3/3 | 3/3 |
| no-event-or-input-interpolation-in-run | 3/3 | 2/3 |
| cms-platform-vendored-contract-unchanged | 3/3 | 3/3 |
