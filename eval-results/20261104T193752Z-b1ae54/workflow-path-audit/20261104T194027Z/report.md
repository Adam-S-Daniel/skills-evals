# Eval report: workflow-path-audit

- Timestamp: 20261104T194027Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T193752Z-b1ae54; started 2026-11-04T19:40:27Z, ended 2026-11-04T19:41:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.04 to 0.04, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 2 call(s); agent $0.31, judge $0.00, guard $0.00; last agent call $0.16

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | skipped (objective-decided) | 0.1463 / 0.1463 |
| without_skill | 1 | 0 | 5/10 | skipped (objective-decided) | 0.1624 / 0.1624 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1463 / 0.1463 | 0.1624 / 0.1624 | -0.0161 | -0.0161 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 32428 / 32428 | 41476 / 41476 | -9048 | -9048 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3051 / 3051 | 3785 / 3785 | -734 | -734 |
| cache_creation_input_tokens | 24909 / 24909 | 26076 / 26076 | -1167 | -1167 |
| cache_read_input_tokens | 160922 / 160922 | 201756 / 201756 | -40834 | -40834 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
| no-second-workflow-doc | 1/1 | 0/1 |
