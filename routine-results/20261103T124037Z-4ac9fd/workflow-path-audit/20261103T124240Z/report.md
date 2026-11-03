# Eval report: workflow-path-audit

- Timestamp: 20261103T124240Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T124037Z-4ac9fd; started 2026-11-03T12:42:40Z, ended 2026-11-03T12:47:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.41, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.69 over 4 call(s); agent $1.00, judge $0.69, guard $0.00; last agent call $0.52

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.4825 / 0.4825 |
| without_skill | 1 | 0 | 8/8 | 8.6 (8.6 to 8.6, 1 judged) | 0.5158 / 0.5158 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4825 / 0.4825 | 0.5158 / 0.5158 | -0.0333 | -0.0333 |
| num_turns | 11 / 11 | 8 / 8 | +3 | +3 |
| duration_ms | 78807 / 78807 | 107734 / 107734 | -28927 | -28927 |
| input_tokens | 24 / 24 | 18 / 18 | +6 | +6 |
| output_tokens | 5451 / 5451 | 7055 / 7055 | -1604 | -1604 |
| cache_creation_input_tokens | 35611 / 35611 | 24428 / 24428 | +11183 | +11183 |
| cache_read_input_tokens | 411977 / 411977 | 307170 / 307170 | +104807 | +104807 |
| tool_errors | 0 / 0 | 2 / 2 | -2 | -2 |

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
