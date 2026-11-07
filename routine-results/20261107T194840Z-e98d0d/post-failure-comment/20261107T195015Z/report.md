# Eval report: post-failure-comment

- Timestamp: 20261107T195015Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T194840Z-e98d0d; started 2026-11-07T19:50:15Z, ended 2026-11-07T20:03:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.66, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $4.22 over 12 call(s); agent $3.28, judge $0.95, guard $0.00; last agent call $0.52

## Fixture: post-failure-comment (n=3)

- Prompt: Make CI failures in these workflows self-report to the PR the way the platform's failure-comment action expects.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.3/12 | 5.7 (5.2 to 6.3, 3 judged) | 0.5317 / 1.5952 |
| without_skill | 3 | 0 | 9/12 | 6.3 (6.1 to 6.5, 3 judged) | 0.5611 / 1.6833 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5317 / 0.4716 | 0.5611 / 0.5668 | -0.0294 | -0.0952 |
| num_turns | 10 / 10 | 11 / 10 | -1 | 0 |
| duration_ms | 96257.7 / 95929 | 130726.3 / 134795 | -34468.7 | -38866 |
| input_tokens | 21.3 / 20 | 23.3 / 22 | -2 | -2 |
| output_tokens | 6817.7 / 7073 | 8354.3 / 7541 | -1536.7 | -468 |
| cache_creation_input_tokens | 34208.3 / 31401 | 36219.7 / 34197 | -2011.3 | -2796 |
| cache_read_input_tokens | 377297 / 353787 | 486017.3 / 470495 | -108720.3 | -116708 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| workflows-still-parse | 3/3 | 3/3 |
| schedule-only-workflow-untouched | 3/3 | 3/3 |
| e2e-inline-block-removed | 2/3 | 3/3 |
| e2e-post-step | 2/3 | 3/3 |
| e2e-resolve-step | 2/3 | 3/3 |
| visual-regression-report-job-shape | 0/3 | 0/3 |
| visual-regression-post-step | 0/3 | 0/3 |
| visual-regression-resolve-step | 0/3 | 0/3 |
| post-failure-comment-reference-valid | 2/3 | 3/3 |
| markers-unique-per-workflow | 3/3 | 3/3 |
| no-event-or-input-interpolation-in-run | 2/3 | 3/3 |
| cms-platform-vendored-contract-unchanged | 3/3 | 3/3 |
