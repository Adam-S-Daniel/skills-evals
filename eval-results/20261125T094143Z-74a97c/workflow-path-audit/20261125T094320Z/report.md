# Eval report: workflow-path-audit

- Timestamp: 20261125T094320Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T094143Z-74a97c; started 2026-11-25T09:43:20Z, ended 2026-11-25T09:47:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.30 over 4 call(s); agent $1.06, judge $0.24, guard $0.00; last agent call $0.54
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.07 points of the weekly meter (0.06 to 0.10); Fable meter 0.03 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.2 (9.2 to 9.2, 1 judged) | 0.5195 / 0.5195 |
| without_skill | 1 | 0 | 8/8 | 8.4 (8.4 to 8.4, 1 judged) | 0.5406 / 0.5406 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5195 / 0.5195 | 0.5406 / 0.5406 | -0.0211 | -0.0211 |
| num_turns | 11 / 11 | 11 / 11 | 0 | 0 |
| duration_ms | 76277 / 76277 | 115334 / 115334 | -39057 | -39057 |
| input_tokens | 22 / 22 | 24 / 24 | -2 | -2 |
| output_tokens | 5858 / 5858 | 10524 / 10524 | -4666 | -4666 |
| cache_creation_input_tokens | 38507 / 38507 | 28762 / 28762 | +9745 | +9745 |
| cache_read_input_tokens | 435494 / 435494 | 461110 / 461110 | -25616 | -25616 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 1/1 |
| companion-skip-workflow-removed | 1/1 | 1/1 |
| docs-change-still-reports-the-required-check | 1/1 | 1/1 |
| source-change-skips-the-docs-site | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
