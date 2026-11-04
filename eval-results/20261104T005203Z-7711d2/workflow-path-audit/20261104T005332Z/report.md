# Eval report: workflow-path-audit

- Timestamp: 20261104T005332Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T005203Z-7711d2; started 2026-11-04T00:53:32Z, ended 2026-11-04T00:54:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1566 / 0.1566 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0794 / 0.0794 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1566 / 0.1566 | 0.0794 / 0.0794 | +0.0772 | +0.0772 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 23350 / 23350 | 16409 / 16409 | +6941 | +6941 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2379 / 2379 | 1431 / 1431 | +948 | +948 |
| cache_creation_input_tokens | 28906 / 28906 | 12985 / 12985 | +15921 | +15921 |
| cache_read_input_tokens | 171684 / 171684 | 131277 / 131277 | +40407 | +40407 |
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
