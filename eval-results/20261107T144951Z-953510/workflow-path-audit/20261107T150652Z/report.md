# Eval report: workflow-path-audit

- Timestamp: 20261107T150652Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T144951Z-953510; started 2026-11-07T15:06:52Z, ended 2026-11-07T15:10:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.85 over 12 call(s); agent $0.60, judge $0.25, guard $0.00; last agent call $0.10

## Fixture: required-gate-salience (n=3)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11.3/12 | 7.8 (5.0 to 9.2, 3 judged) | 0.1067 / 0.3202 |
| without_skill | 3 | 0 | 11.3/12 | 7.4 (5.0 to 9.2, 3 judged) | 0.0938 / 0.2814 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1067 / 0.0909 | 0.0938 / 0.0902 | +0.0129 | +0.0006 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 27756.7 / 24792 | 21371 / 23498 | +6385.7 | +1294 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1979 / 1816 | 2101.3 / 1809 | -122.3 | +7 |
| cache_creation_input_tokens | 17539.3 / 13883 | 13927.3 / 13757 | +3612 | +126 |
| cache_read_input_tokens | 167586.3 / 171096 | 170727 / 170793 | -3140.7 | +303 |
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
| source-change-skips-docs | 2/3 | 2/3 |
| docs-change-builds-docs | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| project-files-unchanged | 2/3 | 2/3 |
