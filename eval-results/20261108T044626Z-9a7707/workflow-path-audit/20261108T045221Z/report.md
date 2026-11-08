# Eval report: workflow-path-audit

- Timestamp: 20261108T045221Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T044626Z-9a7707; started 2026-11-08T04:52:21Z, ended 2026-11-08T04:53:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1538 / 0.1538 |
| without_skill | 1 | 0 | 5/8 | skipped (objective-decided) | 0.0778 / 0.0778 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1538 / 0.1538 | 0.0778 / 0.0778 | +0.0759 | +0.0759 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 20785 / 20785 | 18641 / 18641 | +2144 | +2144 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2137 / 2137 | 1441 / 1441 | +696 | +696 |
| cache_creation_input_tokens | 28775 / 28775 | 12580 / 12580 | +16195 | +16195 |
| cache_read_input_tokens | 172924 / 172924 | 130949 / 130949 | +41975 | +41975 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

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
