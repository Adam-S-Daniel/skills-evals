# Eval report: workflow-path-audit

- Timestamp: 20261125T063824Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T063639Z-3138b5; started 2026-11-25T06:38:24Z, ended 2026-11-25T06:40:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.41 over 4 call(s); agent $0.29, judge $0.12, guard $0.00; last agent call $0.11
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: required-by-unseen-ruleset (n=1)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/11 | 5.8 (5.8 to 5.8, 1 judged) | 0.1790 / 0.1790 |
| without_skill | 1 | 0 | 9/11 | 5.6 (5.6 to 5.6, 1 judged) | 0.1098 / 0.1098 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1790 / 0.1790 | 0.1098 / 0.1098 | +0.0692 | +0.0692 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 37157 / 37157 | 27595 / 27595 | +9562 | +9562 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 4559 / 4559 | 3201 / 3201 | +1358 | +1358 |
| cache_creation_input_tokens | 28191 / 28191 | 16050 / 16050 | +12141 | +12141 |
| cache_read_input_tokens | 205971 / 205971 | 135752 / 135752 | +70219 | +70219 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 1/1 | 1/1 |
| readme-change-reports-ci-and-skips-docs | 0/1 | 0/1 |
| source-change-skips-docs | 0/1 | 0/1 |
| unit-reports-and-skips-on-docs-only | 1/1 | 1/1 |
| lint-reports-and-skips-on-readme-only | 1/1 | 1/1 |
| unit-runs-on-lockfile-bump | 1/1 | 1/1 |
| lint-runs-on-config-change | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| rules-left-alone | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
