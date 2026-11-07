# Eval report: workflow-path-audit

- Timestamp: 20261107T163536Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T163349Z-4eb301; started 2026-11-07T16:35:36Z, ended 2026-11-07T16:46:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.55, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.18 over 6 call(s); agent $3.18, judge $0.00, guard $0.00; last agent call $0.51

## Fixture: companion-skip-pair (n=3)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 8/8 | skipped (objective-decided) | 0.4861 / 1.4582 |
| without_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.5729 / 1.7187 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4861 / 0.5287 | 0.5729 / 0.5142 | -0.0868 | +0.0145 |
| num_turns | 10.7 / 11 | 12 / 11 | -1.3 | 0 |
| duration_ms | 88834.3 / 86576 | 135607 / 133707 | -46772.7 | -47131 |
| input_tokens | 22.7 / 24 | 24.7 / 24 | -2 | 0 |
| output_tokens | 6131.7 / 6221 | 10166.3 / 10672 | -4034.7 | -4451 |
| cache_creation_input_tokens | 31697.3 / 29731 | 29177 / 27530 | +2520.3 | +2201 |
| cache_read_input_tokens | 402864 / 433346 | 506830 / 469478 | -103966 | -36132 |
| tool_errors | 0 / 0 | 1.3 / 1 | -1.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 3/3 | 2/3 |
| companion-skip-workflow-removed | 3/3 | 2/3 |
| docs-change-still-reports-the-required-check | 3/3 | 2/3 |
| source-change-skips-the-docs-site | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| ruleset-unchanged | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 2/3 |
