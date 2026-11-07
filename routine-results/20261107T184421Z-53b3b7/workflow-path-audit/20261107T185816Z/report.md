# Eval report: workflow-path-audit

- Timestamp: 20261107T185816Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T184421Z-53b3b7; started 2026-11-07T18:58:16Z, ended 2026-11-07T19:00:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.62, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.65 over 6 call(s); agent $0.65, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: companion-skip-pair (n=3)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.1286 / 0.3859 |
| without_skill | 3 | 0 | 5/8 | skipped (objective-decided) | 0.0890 / 0.2671 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1286 / 0.1188 | 0.0890 / 0.0878 | +0.0396 | +0.0310 |
| num_turns | 6.7 / 7 | 5 / 5 | +1.7 | +2 |
| duration_ms | 22731.3 / 23472 | 22053.7 / 20897 | +677.7 | +2575 |
| input_tokens | 12.7 / 12 | 10 / 10 | +2.7 | +2 |
| output_tokens | 2213 / 2281 | 1813 / 1668 | +400 | +613 |
| cache_creation_input_tokens | 21802.3 / 18406 | 13511 / 13582 | +8291.3 | +4824 |
| cache_read_input_tokens | 192834.7 / 181527 | 168243.7 / 167833 | +24591 | +13694 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

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
