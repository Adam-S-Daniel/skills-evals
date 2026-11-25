# Eval report: workflow-path-audit

- Timestamp: 20261125T091640Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T091511Z-a871df; started 2026-11-25T09:16:40Z, ended 2026-11-25T09:20:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.44 over 4 call(s); agent $1.21, judge $0.23, guard $0.00; last agent call $0.70
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.08 points of the weekly meter (0.06 to 0.11); Fable meter 0.03 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.8 (9.8 to 9.8, 1 judged) | 0.5059 / 0.5059 |
| without_skill | 1 | 0 | 8/8 | 8.6 (8.6 to 8.6, 1 judged) | 0.7032 / 0.7032 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5059 / 0.5059 | 0.7032 / 0.7032 | -0.1973 | -0.1973 |
| num_turns | 12 / 12 | 12 / 12 | 0 | 0 |
| duration_ms | 80177 / 80177 | 113988 / 113988 | -33811 | -33811 |
| input_tokens | 26 / 26 | 26 / 26 | 0 | 0 |
| output_tokens | 5709 / 5709 | 9558 / 9558 | -3849 | -3849 |
| cache_creation_input_tokens | 36236 / 36236 | 29123 / 29123 | +7113 | +7113 |
| cache_read_input_tokens | 469542 / 469542 | 538664 / 538664 | -69122 | -69122 |
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
