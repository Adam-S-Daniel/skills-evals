# Eval report: workflow-path-audit

- Timestamp: 20261108T040047Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T035854Z-36d7e2; started 2026-11-08T04:00:47Z, ended 2026-11-08T04:04:42Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.39 over 4 call(s); agent $1.08, judge $0.31, guard $0.00; last agent call $0.51

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.5678 / 0.5678 |
| without_skill | 1 | 0 | 8/8 | 8.2 (8.2 to 8.2, 1 judged) | 0.5095 / 0.5095 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5678 / 0.5678 | 0.5095 / 0.5095 | +0.0583 | +0.0583 |
| num_turns | 10 / 10 | 9 / 9 | +1 | +1 |
| duration_ms | 88701 / 88701 | 100983 / 100983 | -12282 | -12282 |
| input_tokens | 22 / 22 | 20 / 20 | +2 | +2 |
| output_tokens | 5644 / 5644 | 7131 / 7131 | -1487 | -1487 |
| cache_creation_input_tokens | 34940 / 34940 | 26525 / 26525 | +8415 | +8415 |
| cache_read_input_tokens | 361762 / 361762 | 368032 / 368032 | -6270 | -6270 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 1/1 |
| companion-skip-workflow-removed | 1/1 | 1/1 |
| docs-change-still-reports-the-required-check | 1/1 | 1/1 |
| source-change-skips-the-docs-site | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
