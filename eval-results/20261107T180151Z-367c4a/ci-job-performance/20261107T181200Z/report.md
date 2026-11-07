# Eval report: ci-job-performance

- Timestamp: 20261107T181200Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T180151Z-367c4a; started 2026-11-07T18:12:00Z, ended 2026-11-07T18:13:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 6 call(s); agent $0.51, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: sharded-required-check (n=3)

- Prompt: Our e2e workflow takes about nine minutes on every pull request. Split the Playwright suite across three parallel jobs so it finishes sooner. The `e2e` check is required on main by .github/rulesets/main.json, and pull requests must still be able to merge once the tests pass. Edit the workflow only; do not change the ruleset or the tests.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/5 | skipped (objective-decided) | 0.1010 / 0.3029 |
| without_skill | 3 | 0 | 3/5 | skipped (objective-decided) | 0.0693 / 0.2079 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1010 / 0.0875 | 0.0693 / 0.0694 | +0.0317 | +0.0181 |
| num_turns | 5 / 5 | 3 / 3 | +2 | +2 |
| duration_ms | 14396 / 14721 | 13967.7 / 14105 | +428.3 | +616 |
| input_tokens | 8 / 8 | 6 / 6 | +2 | +2 |
| output_tokens | 1599 / 1580 | 1469 / 1483 | +130 | +97 |
| cache_creation_input_tokens | 18833.7 / 15245 | 11255 / 11243 | +7578.7 | +4002 |
| cache_read_input_tokens | 96397 / 99971 | 95868 / 95830 | +529 | +4141 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-sharded-three-ways-without-fail-fast | 3/3 | 3/3 |
| required-e2e-check-is-published-by-a-gate | 1/3 | 3/3 |
| gate-cannot-be-cancelled | 3/3 | 0/3 |
| no-matrix-value-in-a-run-body | 3/3 | 0/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
