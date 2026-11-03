# Eval report: workflow-path-audit

- Timestamp: 20261103T075901Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T075713Z-b07547; started 2026-11-03T07:59:01Z, ended 2026-11-03T08:00:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 4 call(s); agent $0.32, judge $0.19, guard $0.00; last agent call $0.14

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.1 (6.1 to 6.1, 1 judged) | 0.1741 / 0.1741 |
| without_skill | 1 | 0 | 6/10 | 6.9 (6.9 to 6.9, 1 judged) | 0.1447 / 0.1447 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1741 / 0.1741 | 0.1447 / 0.1447 | +0.0294 | +0.0294 |
| num_turns | 8 / 8 | 4 / 4 | +4 | +4 |
| duration_ms | 43574 / 43574 | 39201 / 39201 | +4373 | +4373 |
| input_tokens | 16 / 16 | 8 / 8 | +8 | +8 |
| output_tokens | 3805 / 3805 | 3277 / 3277 | +528 | +528 |
| cache_creation_input_tokens | 26983 / 26983 | 24918 / 24918 | +2065 | +2065 |
| cache_read_input_tokens | 280882 / 280882 | 122192 / 122192 | +158690 | +158690 |
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
