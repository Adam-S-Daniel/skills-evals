# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261103T045455Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T045259Z-ab5842; started 2026-11-03T04:54:55Z, ended 2026-11-03T04:55:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.23, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.1327 / 0.1327 |
| without_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.0927 / 0.0927 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1327 / 0.1327 | 0.0927 / 0.0927 | +0.0400 | +0.0400 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 17207 / 17207 | 16630 / 16630 | +577 | +577 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1638 / 1638 | 1609 / 1609 | +29 | +29 |
| cache_creation_input_tokens | 24908 / 24908 | 14736 / 14736 | +10172 | +10172 |
| cache_read_input_tokens | 167019 / 167019 | 176550 / 176550 | -9531 | -9531 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
