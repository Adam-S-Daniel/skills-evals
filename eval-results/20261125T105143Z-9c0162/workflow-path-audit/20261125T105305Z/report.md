# Eval report: workflow-path-audit

- Timestamp: 20261125T105305Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T105143Z-9c0162; started 2026-11-25T10:53:05Z, ended 2026-11-25T10:54:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.22, judge $0.08, guard $0.00; last agent call $0.09
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: required-gate-salience (n=1)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 12/12 | 9.2 (9.2 to 9.2, 1 judged) | 0.1346 / 0.1346 |
| without_skill | 1 | 0 | 12/12 | 8.4 (8.4 to 8.4, 1 judged) | 0.0896 / 0.0896 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1346 / 0.1346 | 0.0896 / 0.0896 | +0.0450 | +0.0450 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 17508 / 17508 | 16028 / 16028 | +1480 | +1480 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1713 / 1713 | 1649 / 1649 | +64 | +64 |
| cache_creation_input_tokens | 25244 / 25244 | 13898 / 13898 | +11346 | +11346 |
| cache_read_input_tokens | 164400 / 164400 | 174655 / 174655 | -10255 | -10255 |
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
