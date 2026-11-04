# Eval report: workflow-path-audit

- Timestamp: 20261104T004345Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T004209Z-f7a50b; started 2026-11-04T00:43:45Z, ended 2026-11-04T00:45:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 4 call(s); agent $0.30, judge $0.19, guard $0.00; last agent call $0.15

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.4 (6.4 to 6.4, 1 judged) | 0.1470 / 0.1470 |
| without_skill | 1 | 0 | 6/10 | 5.5 (5.5 to 5.5, 1 judged) | 0.1510 / 0.1510 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1470 / 0.1470 | 0.1510 / 0.1510 | -0.0040 | -0.0040 |
| num_turns | 4 / 4 | 6 / 6 | -2 | -2 |
| duration_ms | 28255 / 28255 | 29620 / 29620 | -1365 | -1365 |
| input_tokens | 8 / 8 | 12 / 12 | -4 | -4 |
| output_tokens | 3545 / 3545 | 3056 / 3056 | +489 | +489 |
| cache_creation_input_tokens | 24839 / 24839 | 25118 / 25118 | -279 | -279 |
| cache_read_input_tokens | 121839 / 121839 | 199098 / 199098 | -77259 | -77259 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 0/1 |
| source-change-runs-only-the-tests | 0/1 | 0/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 0/1 |
| agents-md-change-runs-nothing | 0/1 | 0/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
