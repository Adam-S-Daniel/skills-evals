# Eval report: workflow-path-audit

- Timestamp: 20261125T093059Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T092938Z-a5acad; started 2026-11-25T09:30:59Z, ended 2026-11-25T09:32:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.11
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: required-by-unseen-ruleset (n=1)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 11/11 | skipped: the version with the skill passed more checks (11 of 11 vs 9 of 11) | 0.1764 / 0.1764 |
| without_skill | 1 | 0 | 9/11 | skipped: the version with the skill passed more checks (11 of 11 vs 9 of 11) | 0.1125 / 0.1125 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1764 / 0.1764 | 0.1125 / 0.1125 | +0.0639 | +0.0639 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 30442 / 30442 | 27714 / 27714 | +2728 | +2728 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3594 / 3594 | 3617 / 3617 | -23 | -23 |
| cache_creation_input_tokens | 28923 / 28923 | 14710 / 14710 | +14213 | +14213 |
| cache_read_input_tokens | 247070 / 247070 | 174234 / 174234 | +72836 | +72836 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 1/1 | 1/1 |
| readme-change-reports-ci-and-skips-docs | 1/1 | 0/1 |
| source-change-skips-docs | 1/1 | 0/1 |
| unit-reports-and-skips-on-docs-only | 1/1 | 1/1 |
| lint-reports-and-skips-on-readme-only | 1/1 | 1/1 |
| unit-runs-on-lockfile-bump | 1/1 | 1/1 |
| lint-runs-on-config-change | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| rules-left-alone | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
