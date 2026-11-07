# Eval report: workflow-path-audit

- Timestamp: 20261107T164700Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T163349Z-4eb301; started 2026-11-07T16:47:00Z, ended 2026-11-07T16:50:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.55 to 0.56, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 6 call(s); agent $0.63, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: companion-skip-pair (n=3)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.1276 / 0.3829 |
| without_skill | 3 | 0 | 5/8 | skipped (objective-decided) | 0.0819 / 0.2457 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1276 / 0.1146 | 0.0819 / 0.0836 | +0.0457 | +0.0310 |
| num_turns | 6.7 / 7 | 4.3 / 4 | +2.3 | +3 |
| duration_ms | 27869 / 30266 | 32857.7 / 22765 | -4988.7 | +7501 |
| input_tokens | 12 / 12 | 8.7 / 8 | +3.3 | +4 |
| output_tokens | 2242.7 / 2243 | 1616 / 1605 | +626.7 | +638 |
| cache_creation_input_tokens | 21804 / 18341 | 12838.7 / 12837 | +8965.3 | +5504 |
| cache_read_input_tokens | 179811.7 / 183838 | 143757.3 / 131662 | +36054.3 | +52176 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 3/3 | 0/3 |
| companion-skip-workflow-removed | 3/3 | 0/3 |
| docs-change-still-reports-the-required-check | 3/3 | 0/3 |
| source-change-skips-the-docs-site | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 3/3 |
