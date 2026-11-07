# Eval report: workflow-path-audit

- Timestamp: 20261107T084015Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T083753Z-ab08d3; started 2026-11-07T08:40:15Z, ended 2026-11-07T08:41:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1564 / 0.1564 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0813 / 0.0813 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1564 / 0.1564 | 0.0813 / 0.0813 | +0.0752 | +0.0752 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 24685 / 24685 | 19644 / 19644 | +5041 | +5041 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2280 / 2280 | 1641 / 1641 | +639 | +639 |
| cache_creation_input_tokens | 29053 / 29053 | 12919 / 12919 | +16134 | +16134 |
| cache_read_input_tokens | 173792 / 173792 | 131585 / 131585 | +42207 | +42207 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 0/1 |
| companion-skip-workflow-removed | 1/1 | 0/1 |
| docs-change-still-reports-the-required-check | 1/1 | 0/1 |
| source-change-skips-the-docs-site | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
