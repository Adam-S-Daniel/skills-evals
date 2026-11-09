# Eval report: workflow-path-audit

- Timestamp: 20261109T212622Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T212241Z-6c7559; started 2026-11-09T21:26:22Z, ended 2026-11-09T21:27:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.36 over 6 call(s); agent $0.27, judge $0.09, guard $0.00; last agent call $0.06

## Fixture: required-by-unseen-ruleset (n=3)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 9/11 | 6.7 (6.4 to 7.0, 3 judged) | 0.0903 / 0.2710 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0903 / 0.0667 |
| num_turns | 5.3 / 5 |
| duration_ms | 17139.7 / 17109 |
| input_tokens | 10.7 / 10 |
| output_tokens | 1610.7 / 1619 |
| cache_creation_input_tokens | 22260.3 / 12935 |
| cache_read_input_tokens | 185587.7 / 181713 |
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
