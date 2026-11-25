# Eval report: workflow-path-audit

- Timestamp: 20261125T094703Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T094143Z-74a97c; started 2026-11-25T09:47:03Z, ended 2026-11-25T09:48:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.29, judge $0.09, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.4 (9.4 to 9.4, 1 judged) | 0.1680 / 0.1680 |
| without_skill | 1 | 0 | 8/8 | 7.8 (7.8 to 7.8, 1 judged) | 0.1236 / 0.1236 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1680 / 0.1680 | 0.1236 / 0.1236 | +0.0445 | +0.0445 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 22020 / 22020 | 33209 / 33209 | -11189 | -11189 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 2386 / 2386 | 3711 / 3711 | -1325 | -1325 |
| cache_creation_input_tokens | 30523 / 30523 | 16231 / 16231 | +14292 | +14292 |
| cache_read_input_tokens | 220397 / 220397 | 215114 / 215114 | +5283 | +5283 |
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
