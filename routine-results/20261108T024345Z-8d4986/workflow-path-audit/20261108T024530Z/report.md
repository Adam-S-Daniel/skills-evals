# Eval report: workflow-path-audit

- Timestamp: 20261108T024530Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T024345Z-8d4986; started 2026-11-08T02:45:30Z, ended 2026-11-08T02:46:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.22, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: required-gate-salience (n=1)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 12/12 | 9.4 (9.4 to 9.4, 1 judged) | 0.1371 / 0.1371 |
| without_skill | 1 | 0 | 12/12 | 8.6 (8.6 to 8.6, 1 judged) | 0.0858 / 0.0858 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1371 / 0.1371 | 0.0858 / 0.0858 | +0.0513 | +0.0513 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 21204 / 21204 | 17630 / 17630 | +3574 | +3574 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1926 / 1926 | 1583 / 1583 | +343 | +343 |
| cache_creation_input_tokens | 25441 / 25441 | 13241 / 13241 | +12200 | +12200 |
| cache_read_input_tokens | 160383 / 160383 | 169860 / 169860 | -9477 | -9477 |
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
