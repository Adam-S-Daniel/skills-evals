# Eval report: workflow-path-audit

- Timestamp: 20261110T035508Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T035337Z-e10520; started 2026-11-10T03:55:08Z, ended 2026-11-10T03:58:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.05 over 6 call(s); agent $0.78, judge $0.27, guard $0.00; last agent call $0.18

## Fixture: required-gate-salience (n=3)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 12/12 | 7.3 (6.8 to 7.6, 3 judged) | 0.2597 / 0.7792 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2597 / 0.2255 |
| num_turns | 6.3 / 7 |
| duration_ms | 42861.7 / 45927 |
| input_tokens | 12.7 / 14 |
| output_tokens | 3946.3 / 3972 |
| cache_creation_input_tokens | 26652.7 / 18096 |
| cache_read_input_tokens | 237546 / 247370 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| lockfile-bump-builds | 3/3 |
| compiler-config-builds | 3/3 |
| node-version-file-builds | 3/3 |
| own-workflow-edit-builds | 3/3 |
| docs-only-reports-and-skips | 3/3 |
| source-change-builds | 3/3 |
| required-check-gates-inside | 3/3 |
| source-change-skips-docs | 3/3 |
| docs-change-builds-docs | 3/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| project-files-unchanged | 3/3 |
