# Eval report: workflow-path-audit

- Timestamp: 20261125T111959Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T111820Z-1d78b2; started 2026-11-25T11:19:59Z, ended 2026-11-25T11:21:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.26, judge $0.09, guard $0.00; last agent call $0.10
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.03); Fable meter 0.00 points

## Fixture: required-gate-salience (n=1)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/12 | 5.8 (5.8 to 5.8, 1 judged) | 0.1603 / 0.1603 |
| without_skill | 1 | 0 | 12/12 | 9.2 (9.2 to 9.2, 1 judged) | 0.1010 / 0.1010 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1603 / 0.1603 | 0.1010 / 0.1010 | +0.0593 | +0.0593 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 28621 / 28621 | 18550 / 18550 | +10071 | +10071 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3490 / 3490 | 1966 / 1966 | +1524 | +1524 |
| cache_creation_input_tokens | 26238 / 26238 | 14953 / 14953 | +11285 | +11285 |
| cache_read_input_tokens | 204516 / 204516 | 215414 / 215414 | -10898 | -10898 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| lockfile-bump-builds | 1/1 | 1/1 |
| compiler-config-builds | 1/1 | 1/1 |
| node-version-file-builds | 1/1 | 1/1 |
| own-workflow-edit-builds | 1/1 | 1/1 |
| docs-only-reports-and-skips | 1/1 | 1/1 |
| source-change-builds | 1/1 | 1/1 |
| required-check-gates-inside | 0/1 | 1/1 |
| source-change-skips-docs | 0/1 | 1/1 |
| docs-change-builds-docs | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| project-files-unchanged | 0/1 | 1/1 |
