# Eval report: workflow-path-audit

- Timestamp: 20261108T044116Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T043932Z-c648ea; started 2026-11-08T04:41:16Z, ended 2026-11-08T04:43:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 4 call(s); agent $0.77, judge $0.23, guard $0.00; last agent call $0.34

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | 10.0 (10.0 to 10.0, 1 judged) | 0.4276 / 0.4276 |
| without_skill | 1 | 0 | 10/10 | 9.0 (9.0 to 9.0, 1 judged) | 0.3391 / 0.3391 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4276 / 0.4276 | 0.3391 / 0.3391 | +0.0885 | +0.0885 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 71579 / 71579 | 42830 / 42830 | +28749 | +28749 |
| input_tokens | 18 / 18 | 12 / 12 | +6 | +6 |
| output_tokens | 4063 / 4063 | 3224 / 3224 | +839 | +839 |
| cache_creation_input_tokens | 35327 / 35327 | 29020 / 29020 | +6307 | +6307 |
| cache_read_input_tokens | 280810 / 280810 | 211896 / 211896 | +68914 | +68914 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

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
