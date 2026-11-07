# Eval report: workflow-path-audit

- Timestamp: 20261107T181349Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T181216Z-5addc2; started 2026-11-07T18:13:49Z, ended 2026-11-07T18:26:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.59 to 0.6, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $3.34 over 6 call(s); agent $3.34, judge $0.00, guard $0.00; last agent call $0.61

## Fixture: required-by-unseen-ruleset (n=3)

- Prompt: Go through this repository's GitHub Actions workflows and make sure each one's triggers and path filters are right for what it does. Fix anything that isn't.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 11/11 | skipped (objective-decided) | 0.5284 / 1.5851 |
| without_skill | 3 | 0 | 9.7/11 | skipped (objective-decided) | 0.5838 / 1.7514 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5284 / 0.5062 | 0.5838 / 0.5984 | -0.0554 | -0.0922 |
| num_turns | 10.7 / 10 | 10.7 / 11 | 0 | -1 |
| duration_ms | 106120 / 104549 | 142355.3 / 152985 | -36235.3 | -48436 |
| input_tokens | 23.3 / 22 | 22.7 / 24 | +0.7 | -2 |
| output_tokens | 7189.7 / 7186 | 10298.7 / 11160 | -3109 | -3974 |
| cache_creation_input_tokens | 32911.3 / 30114 | 30666 / 32831 | +2245.3 | -2717 |
| cache_read_input_tokens | 421567.3 / 393105 | 467276 / 456273 | -45708.7 | -63168 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-still-reports-ci | 3/3 | 3/3 |
| readme-change-reports-ci-and-skips-docs | 3/3 | 2/3 |
| source-change-skips-docs | 3/3 | 2/3 |
| unit-reports-and-skips-on-docs-only | 3/3 | 2/3 |
| lint-reports-and-skips-on-readme-only | 3/3 | 2/3 |
| unit-runs-on-lockfile-bump | 3/3 | 3/3 |
| lint-runs-on-config-change | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| event-only-workflows-unfiltered | 3/3 | 3/3 |
| rules-left-alone | 3/3 | 3/3 |
| project-files-unchanged | 3/3 | 3/3 |
