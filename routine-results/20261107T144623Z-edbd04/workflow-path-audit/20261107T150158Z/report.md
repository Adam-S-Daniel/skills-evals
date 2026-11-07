# Eval report: workflow-path-audit

- Timestamp: 20261107T150158Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T144623Z-edbd04; started 2026-11-07T15:01:58Z, ended 2026-11-07T15:07:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.48, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.11 over 12 call(s); agent $0.79, judge $0.32, guard $0.00; last agent call $0.12

## Fixture: required-by-unseen-ruleset (n=3)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.7/11 | 6.8 (5.6 to 9.0, 3 judged) | 0.1385 / 0.4156 |
| without_skill | 3 | 0 | 9.7/11 | 7.7 (4.8 to 9.2, 3 judged) | 0.1238 / 0.3715 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1385 / 0.1192 | 0.1238 / 0.1234 | +0.0147 | -0.0042 |
| num_turns | 6.3 / 6 | 6.3 / 7 | 0 | -1 |
| duration_ms | 38048 / 37398 | 45980.7 / 40161 | -7932.7 | -2763 |
| input_tokens | 12.7 / 12 | 12.7 / 14 | 0 | -2 |
| output_tokens | 3713 / 3557 | 3854.7 / 3683 | -141.7 | -126 |
| cache_creation_input_tokens | 19786.7 / 15644 | 15756.7 / 15864 | +4030 | -220 |
| cache_read_input_tokens | 222400.7 / 210486 | 222226.7 / 246849 | +174 | -36363 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 3/3 | 3/3 |
| readme-change-reports-ci-and-skips-docs | 1/3 | 2/3 |
| source-change-skips-docs | 1/3 | 2/3 |
| unit-reports-and-skips-on-docs-only | 3/3 | 2/3 |
| lint-reports-and-skips-on-readme-only | 3/3 | 2/3 |
| unit-runs-on-lockfile-bump | 3/3 | 3/3 |
| lint-runs-on-config-change | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| rules-left-alone | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 3/3 |
