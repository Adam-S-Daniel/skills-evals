# Eval report: workflow-path-audit

- Timestamp: 20261125T114557Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T114435Z-9f882a; started 2026-11-25T11:45:57Z, ended 2026-11-25T11:47:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.25, judge $0.09, guard $0.00; last agent call $0.11
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: required-gate-salience (n=1)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 12/12 | 8.0 (8.0 to 8.0, 1 judged) | 0.1356 / 0.1356 |
| without_skill | 1 | 0 | 12/12 | 7.4 (7.4 to 7.4, 1 judged) | 0.1120 / 0.1120 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1356 / 0.1356 | 0.1120 / 0.1120 | +0.0235 | +0.0235 |
| num_turns | 5 / 5 | 7 / 7 | -2 | -2 |
| duration_ms | 18896 / 18896 | 25006 / 25006 | -6110 | -6110 |
| input_tokens | 10 / 10 | 14 / 14 | -4 | -4 |
| output_tokens | 1836 / 1836 | 2426 / 2426 | -590 | -590 |
| cache_creation_input_tokens | 25187 / 25187 | 15562 / 15562 | +9625 | +9625 |
| cache_read_input_tokens | 164520 / 164520 | 255068 / 255068 | -90548 | -90548 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| lockfile-bump-builds | 1/1 | 1/1 |
| compiler-config-builds | 1/1 | 1/1 |
| node-version-file-builds | 1/1 | 1/1 |
| own-workflow-edit-builds | 1/1 | 1/1 |
| docs-only-reports-and-skips | 1/1 | 1/1 |
| source-change-builds | 1/1 | 1/1 |
| required-check-gates-inside | 1/1 | 1/1 |
| source-change-skips-docs | 1/1 | 1/1 |
| docs-change-builds-docs | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
