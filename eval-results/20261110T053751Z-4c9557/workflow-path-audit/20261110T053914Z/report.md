# Eval report: workflow-path-audit

- Timestamp: 20261110T053914Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T053751Z-4c9557; started 2026-11-10T05:39:14Z, ended 2026-11-10T05:41:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.95 over 6 call(s); agent $0.74, judge $0.21, guard $0.00; last agent call $0.17

## Fixture: companion-skip-pair (n=3)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 8/8 | 9.2 (9.2 to 9.2, 3 judged) | 0.2471 / 0.7413 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2471 / 0.2560 |
| num_turns | 6.7 / 6 |
| duration_ms | 46361 / 43172 |
| input_tokens | 12.7 / 12 |
| output_tokens | 3924.7 / 3502 |
| cache_creation_input_tokens | 24414.7 / 17984 |
| cache_read_input_tokens | 232420.3 / 195927 |
| tool_errors | 0.7 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| required-check-gates-inside-one-workflow | 3/3 |
| companion-skip-workflow-removed | 3/3 |
| docs-change-still-reports-the-required-check | 3/3 |
| source-change-skips-the-docs-site | 3/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| ruleset-unchanged | 3/3 |
| project-files-unchanged | 3/3 |
