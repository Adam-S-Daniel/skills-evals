# Eval report: workflow-path-audit

- Timestamp: 20261125T101248Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T101117Z-e77bc8; started 2026-11-25T10:12:48Z, ended 2026-11-25T10:16:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.96 over 2 call(s); agent $0.96, judge $0.00, guard $0.00; last agent call $0.51
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.05 points of the weekly meter (0.04 to 0.08); Fable meter 0.00 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped: the version with the skill passed more checks (8 of 8 vs 5 of 8) | 0.4521 / 0.4521 |
| without_skill | 1 | 0 | 5/8 | skipped: the version with the skill passed more checks (8 of 8 vs 5 of 8) | 0.5067 / 0.5067 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4521 / 0.4521 | 0.5067 / 0.5067 | -0.0546 | -0.0546 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 66442 / 66442 | 124879 / 124879 | -58437 | -58437 |
| input_tokens | 20 / 20 | 14 / 14 | +6 | +6 |
| output_tokens | 5148 / 5148 | 9866 / 9866 | -4718 | -4718 |
| cache_creation_input_tokens | 34829 / 34829 | 30267 / 30267 | +4562 | +4562 |
| cache_read_input_tokens | 316585 / 316585 | 280467 / 280467 | +36118 | +36118 |
| tool_errors | 0 / 0 | 4 / 4 | -4 | -4 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 0/1 |
| companion-skip-workflow-removed | 1/1 | 0/1 |
| docs-change-still-reports-the-required-check | 1/1 | 0/1 |
| source-change-skips-the-docs-site | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
