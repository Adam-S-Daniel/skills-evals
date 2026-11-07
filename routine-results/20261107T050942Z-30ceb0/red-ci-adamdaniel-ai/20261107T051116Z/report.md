# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T051116Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T050942Z-30ceb0; started 2026-11-07T05:11:16Z, ended 2026-11-07T05:12:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | skipped (objective-decided) | 0.1355 / 0.1355 |
| without_skill | 1 | 0 | 1/3 | skipped (objective-decided) | 0.0938 / 0.0938 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1355 / 0.1355 | 0.0938 / 0.0938 | +0.0417 | +0.0417 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 23714 / 23714 | 19140 / 19140 | +4574 | +4574 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1685 / 1685 | 1839 / 1839 | -154 | -154 |
| cache_creation_input_tokens | 25475 / 25475 | 14438 / 14438 | +11037 | +11037 |
| cache_read_input_tokens | 167009 / 167009 | 176497 / 176497 | -9488 | -9488 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 0/1 |
