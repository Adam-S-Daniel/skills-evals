# Eval report: workflow-path-audit

- Timestamp: 20261103T124621Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T124420Z-99a9f2; started 2026-11-03T12:46:21Z, ended 2026-11-03T12:50:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.35 over 4 call(s); agent $0.89, judge $0.46, guard $0.00; last agent call $0.43

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | 8.8 (8.8 to 8.8, 1 judged) | 0.4622 / 0.4622 |
| without_skill | 1 | 0 | 10/10 | 8.8 (8.8 to 8.8, 1 judged) | 0.4272 / 0.4272 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4622 / 0.4622 | 0.4272 / 0.4272 | +0.0350 | +0.0350 |
| num_turns | 11 / 11 | 7 / 7 | +4 | +4 |
| duration_ms | 75302 / 75302 | 80348 / 80348 | -5046 | -5046 |
| input_tokens | 22 / 22 | 16 / 16 | +6 | +6 |
| output_tokens | 4763 / 4763 | 5068 / 5068 | -305 | -305 |
| cache_creation_input_tokens | 35729 / 35729 | 33268 / 33268 | +2461 | +2461 |
| cache_read_input_tokens | 375122 / 375122 | 262662 / 262662 | +112460 | +112460 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

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
