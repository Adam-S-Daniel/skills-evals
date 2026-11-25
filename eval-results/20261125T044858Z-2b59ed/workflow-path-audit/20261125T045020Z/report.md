# Eval report: workflow-path-audit

- Timestamp: 20261125T045020Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T044858Z-2b59ed; started 2026-11-25T04:50:20Z, ended 2026-11-25T04:51:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.11
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped: the version with the skill passed more checks (8 of 8 vs 3 of 8) | 0.1605 / 0.1605 |
| without_skill | 1 | 0 | 3/8 | skipped: the version with the skill passed more checks (8 of 8 vs 3 of 8) | 0.1133 / 0.1133 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1605 / 0.1605 | 0.1133 / 0.1133 | +0.0472 | +0.0472 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 20182 / 20182 | 29768 / 29768 | -9586 | -9586 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2169 / 2169 | 3534 / 3534 | -1365 | -1365 |
| cache_creation_input_tokens | 29214 / 29214 | 15150 / 15150 | +14064 | +14064 |
| cache_read_input_tokens | 219180 / 219180 | 172901 / 172901 | +46279 | +46279 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 0/1 |
| companion-skip-workflow-removed | 1/1 | 0/1 |
| docs-change-still-reports-the-required-check | 1/1 | 0/1 |
| source-change-skips-the-docs-site | 1/1 | 0/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 0/1 |
| project-files-unchanged | 1/1 | 1/1 |
