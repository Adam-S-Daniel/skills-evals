# Eval report: workflow-path-audit

- Timestamp: 20261125T101610Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T101117Z-e77bc8; started 2026-11-25T10:16:10Z, ended 2026-11-25T10:17:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.27, judge $0.08, guard $0.00; last agent call $0.10
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 10.0 (10.0 to 10.0, 1 judged) | 0.1651 / 0.1651 |
| without_skill | 1 | 0 | 8/8 | 9.2 (9.2 to 9.2, 1 judged) | 0.1018 / 0.1018 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1651 / 0.1651 | 0.1018 / 0.1018 | +0.0634 | +0.0634 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 23175 / 23175 | 24481 / 24481 | -1306 | -1306 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2494 / 2494 | 2626 / 2626 | -132 | -132 |
| cache_creation_input_tokens | 30560 / 30560 | 14538 / 14538 | +16022 | +16022 |
| cache_read_input_tokens | 179094 / 179094 | 173223 / 173223 | +5871 | +5871 |
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
