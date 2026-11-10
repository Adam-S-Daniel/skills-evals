# Eval report: workflow-path-audit

- Timestamp: 20261110T101122Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T100943Z-3b18ed; started 2026-11-10T10:11:22Z, ended 2026-11-10T10:13:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.2 to 0.2, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.68, judge $0.23, guard $0.00; last agent call $0.17

## Fixture: required-by-unseen-ruleset (n=3)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 9/11 | 6.4 (6.0 to 6.6, 3 judged) | 0.2252 / 0.6756 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2252 / 0.1729 |
| num_turns | 6.3 / 6 |
| duration_ms | 31799.3 / 31010 |
| input_tokens | 12.7 / 12 |
| output_tokens | 2495.7 / 2424 |
| cache_creation_input_tokens | 25624.3 / 15742 |
| cache_read_input_tokens | 235502.7 / 229881 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| docs-change-still-reports-ci | 3/3 |
| readme-change-reports-ci-and-skips-docs | 3/3 |
| source-change-skips-docs | 3/3 |
| unit-reports-and-skips-on-docs-only | 0/3 |
| lint-reports-and-skips-on-readme-only | 0/3 |
| unit-runs-on-lockfile-bump | 3/3 |
| lint-runs-on-config-change | 3/3 |
| workflows-still-parse | 3/3 |
| event-only-workflows-unfiltered | 3/3 |
| rules-left-alone | 3/3 |
| project-files-unchanged | 3/3 |
