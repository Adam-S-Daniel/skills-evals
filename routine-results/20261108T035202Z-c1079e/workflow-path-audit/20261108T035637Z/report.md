# Eval report: workflow-path-audit

- Timestamp: 20261108T035637Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T035202Z-c1079e; started 2026-11-08T03:56:37Z, ended 2026-11-08T03:57:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.30, judge $0.11, guard $0.00; last agent call $0.15

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 5.5 (5.5 to 5.5, 1 judged) | 0.1505 / 0.1505 |
| without_skill | 1 | 0 | 6/10 | 6.4 (6.4 to 6.4, 1 judged) | 0.1464 / 0.1464 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1505 / 0.1505 | 0.1464 / 0.1464 | +0.0040 | +0.0040 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 25776 / 25776 | 28426 / 28426 | -2650 | -2650 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3177 / 3177 | 3073 / 3073 | +104 | +104 |
| cache_creation_input_tokens | 25629 / 25629 | 24892 / 24892 | +737 | +737 |
| cache_read_input_tokens | 161650 / 161650 | 161275 / 161275 | +375 | +375 |
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
