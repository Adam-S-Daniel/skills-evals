# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T090021Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T085925Z-5af1f8; started 2026-11-07T09:00:21Z, ended 2026-11-07T09:01:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 6 call(s); agent $0.20, judge $0.08, guard $0.00; last agent call $0.07

## Fixture: paths-required (n=3)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3/3 | 9.4 (9.3 to 9.5, 3 judged) | 0.0667 / 0.2002 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0667 / 0.0664 |
| num_turns | 5 / 5 |
| duration_ms | 15454.3 / 15837 |
| input_tokens | 10 / 10 |
| output_tokens | 1241.7 / 1226 |
| cache_creation_input_tokens | 9203 / 9003 |
| cache_read_input_tokens | 175009.7 / 175228 |
| tool_errors | 1.7 / 2 |

| Check (passed / scored) | without_skill |
| --- | --- |
| no-paths-filter | 3/3 |
| still-gated | 3/3 |
| site-untouched | 3/3 |
