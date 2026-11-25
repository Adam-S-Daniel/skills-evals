# Eval report: workflow-path-audit

- Timestamp: 20261125T082731Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T082438Z-569efe; started 2026-11-25T08:27:31Z, ended 2026-11-25T08:28:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.23, judge $0.09, guard $0.00; last agent call $0.10
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: required-by-unseen-ruleset (n=1)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/11 | 3.2 (3.2 to 3.2, 1 judged) | 0.1293 / 0.1293 |
| without_skill | 1 | 0 | 9/11 | 6.0 (6.0 to 6.0, 1 judged) | 0.1030 / 0.1030 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1293 / 0.1293 | 0.1030 / 0.1030 | +0.0263 | +0.0263 |
| num_turns | 5 / 5 | 4 / 4 | +1 | +1 |
| duration_ms | 19497 / 19497 | 27681 / 27681 | -8184 | -8184 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 1680 / 1680 | 3283 / 3283 | -1603 | -1603 |
| cache_creation_input_tokens | 24034 / 24034 | 14162 / 14162 | +9872 | +9872 |
| cache_read_input_tokens | 163474 / 163474 | 135434 / 135434 | +28040 | +28040 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 0/1 | 1/1 |
| readme-change-reports-ci-and-skips-docs | 0/1 | 0/1 |
| source-change-skips-docs | 1/1 | 0/1 |
| unit-reports-and-skips-on-docs-only | 0/1 | 1/1 |
| lint-reports-and-skips-on-readme-only | 0/1 | 1/1 |
| unit-runs-on-lockfile-bump | 1/1 | 1/1 |
| lint-runs-on-config-change | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| rules-left-alone | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
