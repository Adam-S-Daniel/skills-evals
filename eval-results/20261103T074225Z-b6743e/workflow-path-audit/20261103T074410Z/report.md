# Eval report: workflow-path-audit

- Timestamp: 20261103T074410Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T074225Z-b6743e; started 2026-11-03T07:44:10Z, ended 2026-11-03T07:45:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1594 / 0.1594 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0886 / 0.0886 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1594 / 0.1594 | 0.0886 / 0.0886 | +0.0708 | +0.0708 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 27361 / 27361 | 25423 / 25423 | +1938 | +1938 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2203 / 2203 | 1905 / 1905 | +298 | +298 |
| cache_creation_input_tokens | 28989 / 28989 | 13169 / 13169 | +15820 | +15820 |
| cache_read_input_tokens | 213862 / 213862 | 168697 / 168697 | +45165 | +45165 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
