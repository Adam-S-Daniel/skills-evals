# Eval report: workflow-path-audit

- Timestamp: 20261107T145130Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T144951Z-953510; started 2026-11-07T14:51:30Z, ended 2026-11-07T15:06:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.48, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.92 over 6 call(s); agent $3.92, judge $0.00, guard $0.00; last agent call $0.76

## Fixture: required-gate-salience (n=3)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 12/12 | skipped (objective-decided) | 0.4454 / 1.3363 |
| without_skill | 3 | 0 | 8.3/12 | skipped (objective-decided) | 0.8625 / 2.5874 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4454 / 0.4371 | 0.8625 / 0.8894 | -0.4170 | -0.4523 |
| num_turns | 9.7 / 10 | 11.3 / 9 | -1.7 | +1 |
| duration_ms | 88500 / 93914 | 212795.3 / 220165 | -124295.3 | -126251 |
| input_tokens | 20 / 20 | 24.7 / 22 | -4.7 | -2 |
| output_tokens | 5800.7 / 5524 | 13416 / 12551 | -7615.3 | -7027 |
| cache_creation_input_tokens | 31112.3 / 31003 | 36606.7 / 35197 | -5494.3 | -4194 |
| cache_read_input_tokens | 369724.3 / 400798 | 513938.7 / 407913 | -144214.3 | -7115 |
| tool_errors | 0.3 / 0 | 1.7 / 1 | -1.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| lockfile-bump-builds | 3/3 | 2/3 |
| compiler-config-builds | 3/3 | 2/3 |
| node-version-file-builds | 3/3 | 2/3 |
| own-workflow-edit-builds | 3/3 | 2/3 |
| docs-only-reports-and-skips | 3/3 | 3/3 |
| source-change-builds | 3/3 | 3/3 |
| required-check-gates-inside | 3/3 | 1/3 |
| source-change-skips-docs | 3/3 | 0/3 |
| docs-change-builds-docs | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 1/3 |
