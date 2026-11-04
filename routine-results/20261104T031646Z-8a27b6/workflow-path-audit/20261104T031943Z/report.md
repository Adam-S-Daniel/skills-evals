# Eval report: workflow-path-audit

- Timestamp: 20261104T031943Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T031646Z-8a27b6; started 2026-11-04T03:19:43Z, ended 2026-11-04T03:21:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.88 to 0.88, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 4 call(s); agent $0.33, judge $0.17, guard $0.00; last agent call $0.15

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.4 (6.4 to 6.4, 1 judged) | 0.1777 / 0.1777 |
| without_skill | 1 | 0 | 10/10 | 9.1 (9.1 to 9.1, 1 judged) | 0.1535 / 0.1535 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1777 / 0.1777 | 0.1535 / 0.1535 | +0.0242 | +0.0242 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 38237 / 38237 | 27047 / 27047 | +11190 | +11190 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 3952 / 3952 | 2497 / 2497 | +1455 | +1455 |
| cache_creation_input_tokens | 27495 / 27495 | 25250 / 25250 | +2245 | +2245 |
| cache_read_input_tokens | 281527 / 281527 | 274498 / 274498 | +7029 | +7029 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 1/1 |
| source-change-runs-only-the-tests | 0/1 | 1/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 1/1 |
| agents-md-change-runs-nothing | 0/1 | 1/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
