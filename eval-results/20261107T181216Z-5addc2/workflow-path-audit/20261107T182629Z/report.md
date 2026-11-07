# Eval report: workflow-path-audit

- Timestamp: 20261107T182629Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T181216Z-5addc2; started 2026-11-07T18:26:29Z, ended 2026-11-07T18:30:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.94 over 12 call(s); agent $0.67, judge $0.27, guard $0.00; last agent call $0.08

## Fixture: required-by-unseen-ruleset (n=3)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.7/11 | 6.9 (3.2 to 9.0, 3 judged) | 0.1157 / 0.3471 |
| without_skill | 3 | 0 | 9.7/11 | 7.1 (4.0 to 9.0, 3 judged) | 0.1071 / 0.3214 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1157 / 0.1127 | 0.1071 / 0.1154 | +0.0085 | -0.0028 |
| num_turns | 5.7 / 6 | 6 / 6 | -0.3 | 0 |
| duration_ms | 26980.3 / 27962 | 28979.7 / 33113 | -1999.3 | -5151 |
| input_tokens | 11.3 / 12 | 12 / 12 | -0.7 | 0 |
| output_tokens | 2468.3 / 2615 | 2707.3 / 3213 | -239 | -598 |
| cache_creation_input_tokens | 17942 / 14734 | 14772 / 15564 | +3170 | -830 |
| cache_read_input_tokens | 192100.7 / 198358 | 209515 / 210002 | -17414.3 | -11644 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 2/3 | 2/3 |
| readme-change-reports-ci-and-skips-docs | 2/3 | 2/3 |
| source-change-skips-docs | 3/3 | 3/3 |
| unit-reports-and-skips-on-docs-only | 2/3 | 2/3 |
| lint-reports-and-skips-on-readme-only | 2/3 | 2/3 |
| unit-runs-on-lockfile-bump | 3/3 | 3/3 |
| lint-runs-on-config-change | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| rules-left-alone | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 3/3 |
