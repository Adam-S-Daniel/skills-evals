# Eval report: workflow-path-audit

- Timestamp: 20261125T072833Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T072713Z-359093; started 2026-11-25T07:28:33Z, ended 2026-11-25T07:30:00Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 4 call(s); agent $0.33, judge $0.10, guard $0.00; last agent call $0.18
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.03 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.3 (6.3 to 6.3, 1 judged) | 0.1436 / 0.1436 |
| without_skill | 1 | 0 | 6/10 | 7.6 (7.6 to 7.6, 1 judged) | 0.1825 / 0.1825 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1436 / 0.1436 | 0.1825 / 0.1825 | -0.0389 | -0.0389 |
| num_turns | 5 / 5 | 8 / 8 | -3 | -3 |
| duration_ms | 22443 / 22443 | 35421 / 35421 | -12978 | -12978 |
| input_tokens | 10 / 10 | 16 / 16 | -6 | -6 |
| output_tokens | 2589 / 2589 | 3898 / 3898 | -1309 | -1309 |
| cache_creation_input_tokens | 25320 / 25320 | 28570 / 28570 | -3250 | -3250 |
| cache_read_input_tokens | 164019 / 164019 | 292276 / 292276 | -128257 | -128257 |
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
