# Eval report: workflow-path-audit

- Timestamp: 20261103T233833Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T233723Z-93f468; started 2026-11-03T23:38:33Z, ended 2026-11-03T23:39:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.81, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.18 over 2 call(s); agent $0.18, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1105 / 0.1105 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0685 / 0.0685 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1105 / 0.1105 | 0.0685 / 0.0685 | +0.0421 | +0.0421 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 20915 / 20915 | 13308 / 13308 | +7607 | +7607 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2327 / 2327 | 1181 / 1181 | +1146 | +1146 |
| cache_creation_input_tokens | 17022 / 17022 | 10654 / 10654 | +6368 | +6368 |
| cache_read_input_tokens | 191578 / 191578 | 140158 / 140158 | +51420 | +51420 |
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
