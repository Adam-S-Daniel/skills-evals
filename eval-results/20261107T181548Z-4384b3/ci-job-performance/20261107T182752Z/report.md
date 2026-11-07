# Eval report: ci-job-performance

- Timestamp: 20261107T182752Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T181548Z-4384b3; started 2026-11-07T18:27:52Z, ended 2026-11-07T18:30:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 6 call(s); agent $0.90, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: fast-suite-sharding (n=3)

- Prompt: Our `e2e` check takes almost two minutes on every pull request and is always the last check to finish. We were thinking of splitting the Playwright suite across three or four parallel jobs. You can't reach GitHub from here, so I exported the workflow's recent runs into ci-runs/ (`gh run view <id> --json jobs` and `gh run view <id> --log` for each, plus the run list). Make the check faster. `e2e` is a required status check on main, so it has to keep reporting under that name.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/5 | skipped (objective-decided) | 0.1576 / 0.4728 |
| without_skill | 3 | 0 | 4.7/5 | skipped (objective-decided) | 0.1434 / 0.4302 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1576 / 0.1459 | 0.1434 / 0.1513 | +0.0142 | -0.0054 |
| num_turns | 8.3 / 8 | 6.7 / 7 | +1.7 | +1 |
| duration_ms | 25971 / 24526 | 29034.3 / 28884 | -3063.3 | -4358 |
| input_tokens | 14.7 / 14 | 12.7 / 12 | +2 | +2 |
| output_tokens | 2479 / 2480 | 2462.7 / 2608 | +16.3 | -128 |
| cache_creation_input_tokens | 27029.7 / 24991 | 23550.7 / 24583 | +3479 | +408 |
| cache_read_input_tokens | 246536.7 / 239383 | 245336.7 / 232634 | +1200 | +6749 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| suite-is-not-sharded | 3/3 | 3/3 |
| installs-only-chromium | 3/3 | 3/3 |
| tests-not-pinned-to-one-worker | 3/3 | 2/3 |
| required-e2e-check-is-published | 3/3 | 3/3 |
| only-the-workflow-changed | 3/3 | 3/3 |
