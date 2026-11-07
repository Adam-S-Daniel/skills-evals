# Eval report: workflow-path-audit

- Timestamp: 20261107T180656Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T180508Z-16e075; started 2026-11-07T18:06:56Z, ended 2026-11-07T18:21:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.59, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.52 over 6 call(s); agent $3.52, judge $0.00, guard $0.00; last agent call $0.96

## Fixture: required-gate-salience (n=3)

- Prompt: Review how this repo's CI workflows decide when to do their work, and fix any that run when they don't need to or skip when they shouldn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11.7/12 | skipped (objective-decided) | 0.4029 / 1.2086 |
| without_skill | 3 | 0 | 10.7/12 | skipped (objective-decided) | 0.7720 / 2.3159 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4029 / 0.4107 | 0.7720 / 0.7183 | -0.3691 | -0.3076 |
| num_turns | 9.7 / 8 | 10 / 11 | -0.3 | -3 |
| duration_ms | 75680 / 75195 | 210395.7 / 193525 | -134715.7 | -118330 |
| input_tokens | 20 / 16 | 23.3 / 28 | -3.3 | -12 |
| output_tokens | 4800.7 / 5047 | 12187 / 10129 | -7386.3 | -5082 |
| cache_creation_input_tokens | 28989.7 / 25056 | 34110.7 / 33149 | -5121 | -8093 |
| cache_read_input_tokens | 345435 / 278656 | 454198.7 / 493818 | -108763.7 | -215162 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| lockfile-bump-builds | 3/3 | 3/3 |
| compiler-config-builds | 3/3 | 3/3 |
| node-version-file-builds | 3/3 | 3/3 |
| own-workflow-edit-builds | 3/3 | 3/3 |
| docs-only-reports-and-skips | 3/3 | 3/3 |
| source-change-builds | 3/3 | 3/3 |
| required-check-gates-inside | 2/3 | 3/3 |
| source-change-skips-docs | 3/3 | 2/3 |
| docs-change-builds-docs | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 0/3 |
