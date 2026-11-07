# Eval report: workflow-path-audit

- Timestamp: 20261107T144804Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T144623Z-edbd04; started 2026-11-07T14:48:04Z, ended 2026-11-07T15:01:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.46 to 0.47, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.80 over 6 call(s); agent $3.80, judge $0.00, guard $0.00; last agent call $0.70

## Fixture: required-by-unseen-ruleset (n=3)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11/11 | skipped (objective-decided) | 0.5567 / 1.6701 |
| without_skill | 3 | 0 | 9.3/11 | skipped (objective-decided) | 0.7093 / 2.1279 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5567 / 0.6215 | 0.7093 / 0.6958 | -0.1526 | -0.0743 |
| num_turns | 11.3 / 12 | 11.3 / 11 | 0 | +1 |
| duration_ms | 113239.3 / 115589 | 159419.7 / 151258 | -46180.3 | -35669 |
| input_tokens | 25.3 / 28 | 24 / 22 | +1.3 | +6 |
| output_tokens | 7831 / 8581 | 12217 / 11482 | -4386 | -2901 |
| cache_creation_input_tokens | 33690.3 / 31259 | 31987 / 30265 | +1703.3 | +994 |
| cache_read_input_tokens | 455355.7 / 483775 | 479569.7 / 440503 | -24214 | +43272 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 3/3 | 3/3 |
| readme-change-reports-ci-and-skips-docs | 3/3 | 1/3 |
| source-change-skips-docs | 3/3 | 1/3 |
| unit-reports-and-skips-on-docs-only | 3/3 | 3/3 |
| lint-reports-and-skips-on-readme-only | 3/3 | 3/3 |
| unit-runs-on-lockfile-bump | 3/3 | 3/3 |
| lint-runs-on-config-change | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| rules-left-alone | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 2/3 |
