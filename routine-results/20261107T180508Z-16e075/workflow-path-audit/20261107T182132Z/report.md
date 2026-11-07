# Eval report: workflow-path-audit

- Timestamp: 20261107T182132Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T180508Z-16e075; started 2026-11-07T18:21:32Z, ended 2026-11-07T18:24:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.6, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.84 over 12 call(s); agent $0.60, judge $0.24, guard $0.00; last agent call $0.09

## Fixture: required-gate-salience (n=3)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 12/12 | 8.3 (7.2 to 9.4, 3 judged) | 0.1096 / 0.3288 |
| without_skill | 3 | 0 | 12/12 | 9.0 (9.0 to 9.0, 3 judged) | 0.0919 / 0.2758 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1096 / 0.1052 | 0.0919 / 0.0918 | +0.0177 | +0.0135 |
| num_turns | 5.7 / 5 | 5.7 / 6 | 0 | -1 |
| duration_ms | 17609.7 / 17852 | 19805.7 / 19277 | -2196 | -1425 |
| input_tokens | 10.7 / 10 | 11.3 / 12 | -0.7 | -2 |
| output_tokens | 1689.3 / 1509 | 1780 / 1810 | -90.7 | -301 |
| cache_creation_input_tokens | 18872 / 18067 | 13642.3 / 13756 | +5229.7 | +4311 |
| cache_read_input_tokens | 171866.3 / 170696 | 195393.3 / 207475 | -23527 | -36779 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| lockfile-bump-builds | 3/3 | 3/3 |
| compiler-config-builds | 3/3 | 3/3 |
| node-version-file-builds | 3/3 | 3/3 |
| own-workflow-edit-builds | 3/3 | 3/3 |
| docs-only-reports-and-skips | 3/3 | 3/3 |
| source-change-builds | 3/3 | 3/3 |
| required-check-gates-inside | 3/3 | 3/3 |
| source-change-skips-docs | 3/3 | 3/3 |
| docs-change-builds-docs | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 3/3 |
