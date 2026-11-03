# Eval report: workflow-path-audit

- Timestamp: 20261103T224321Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T223925Z-627649; started 2026-11-03T22:43:21Z, ended 2026-11-03T22:44:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.78 to 0.78, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.19, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | 9.1 (9.1 to 9.1, 1 judged) | 0.1130 / 0.1130 |
| without_skill | 1 | 0 | 10/10 | 10.0 (10.0 to 10.0, 1 judged) | 0.0754 / 0.0754 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1130 / 0.1130 | 0.0754 / 0.0754 | +0.0376 | +0.0376 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 24658 / 24658 | 14081 / 14081 | +10577 | +10577 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 2026 / 2026 | 1316 / 1316 | +710 | +710 |
| cache_creation_input_tokens | 18225 / 18225 | 12011 / 12011 | +6214 | +6214 |
| cache_read_input_tokens | 197684 / 197684 | 141504 / 141504 | +56180 | +56180 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 1/1 | 1/1 |
| source-change-runs-only-the-tests | 1/1 | 1/1 |
| lockfile-change-runs-only-the-tests | 1/1 | 1/1 |
| agents-md-change-runs-nothing | 1/1 | 1/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
