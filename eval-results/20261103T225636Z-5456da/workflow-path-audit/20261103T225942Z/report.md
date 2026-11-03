# Eval report: workflow-path-audit

- Timestamp: 20261103T225942Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T225636Z-5456da; started 2026-11-03T22:59:42Z, ended 2026-11-03T23:01:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.79 to 0.79, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 4 call(s); agent $0.28, judge $0.18, guard $0.00; last agent call $0.14

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.1 (6.1 to 6.1, 1 judged) | 0.1435 / 0.1435 |
| without_skill | 1 | 0 | 6/10 | 5.4 (5.4 to 5.4, 1 judged) | 0.1384 / 0.1384 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1435 / 0.1435 | 0.1384 / 0.1384 | +0.0051 | +0.0051 |
| num_turns | 5 / 5 | 4 / 4 | +1 | +1 |
| duration_ms | 25800 / 25800 | 25680 / 25680 | +120 | +120 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 2859 / 2859 | 2772 / 2772 | +87 | +87 |
| cache_creation_input_tokens | 24727 / 24727 | 24612 / 24612 | +115 | +115 |
| cache_read_input_tokens | 159444 / 159444 | 121941 / 121941 | +37503 | +37503 |
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
