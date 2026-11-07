# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T135016Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T134906Z-7f4691; started 2026-11-07T13:50:16Z, ended 2026-11-07T13:52:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 6 call(s); agent $0.46, judge $0.29, guard $0.00; last agent call $0.15

## Fixture: paths-required (n=3)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 2.7/3 | 8.9 (8.5 to 9.3, 3 judged) | 0.1527 / 0.4582 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1527 / 0.1524 |
| num_turns | 5 / 5 |
| duration_ms | 25795.3 / 24334 |
| input_tokens | 10 / 10 |
| output_tokens | 1802 / 1815 |
| cache_creation_input_tokens | 10160 / 10173 |
| cache_read_input_tokens | 176934.7 / 177188 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| no-paths-filter | 3/3 |
| still-gated | 2/3 |
| site-untouched | 3/3 |
