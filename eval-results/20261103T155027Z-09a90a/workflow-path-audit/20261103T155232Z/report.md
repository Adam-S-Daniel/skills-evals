# Eval report: workflow-path-audit

- Timestamp: 20261103T155232Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T155027Z-09a90a; started 2026-11-03T15:52:32Z, ended 2026-11-03T15:53:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.54, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1559 / 0.1559 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0926 / 0.0926 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1559 / 0.1559 | 0.0926 / 0.0926 | +0.0633 | +0.0633 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 40320 / 40320 | 19366 / 19366 | +20954 | +20954 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2249 / 2249 | 1625 / 1625 | +624 | +624 |
| cache_creation_input_tokens | 29002 / 29002 | 14755 / 14755 | +14247 | +14247 |
| cache_read_input_tokens | 173667 / 173667 | 173348 / 173348 | +319 | +319 |
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
