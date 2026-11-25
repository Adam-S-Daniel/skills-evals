# Eval report: workflow-path-audit

- Timestamp: 20261125T074557Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T074421Z-88acf2; started 2026-11-25T07:45:57Z, ended 2026-11-25T07:47:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.28, judge $0.09, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 10.0 (10.0 to 10.0, 1 judged) | 0.1611 / 0.1611 |
| without_skill | 1 | 0 | 8/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.1182 / 0.1182 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1611 / 0.1611 | 0.1182 / 0.1182 | +0.0429 | +0.0429 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 22225 / 22225 | 32871 / 32871 | -10646 | -10646 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2410 / 2410 | 3437 / 3437 | -1027 | -1027 |
| cache_creation_input_tokens | 29785 / 29785 | 15637 / 15637 | +14148 | +14148 |
| cache_read_input_tokens | 178366 / 178366 | 212203 / 212203 | -33837 | -33837 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

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
